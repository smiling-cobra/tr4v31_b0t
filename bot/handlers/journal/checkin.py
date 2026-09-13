"""The check-in flow: mood rating, entry text, LLM response, optional guidance offer.

Service calls go through `asyncio.to_thread` — see the package docstring.
"""
import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.journal import deps
from bot.handlers.journal.states import (
    CHECK_IN_GUIDANCE_OFFER,
    CHECK_IN_MOOD,
    CHECK_IN_TEXT,
    CRISIS_MOOD_THRESHOLD,
    LOW_MOOD_THRESHOLD,
    MAIN_MENU,
)
from bot.keyboards import GUIDANCE_YES, get_guidance_keyboard, get_main_menu_keyboard, get_mood_keyboard
from messages.markdown import escape_md
from messages.strings import (
    CHECK_IN_DONE,
    CHECK_IN_TEXT_PROMPT,
    ERROR_GENERIC,
    GUIDANCE_CRISIS_RESOURCES,
    GUIDANCE_DECLINED,
    GUIDANCE_OFFER_LOW,
    GUIDANCE_OFFER_VERY_LOW,
    MOOD_LOST,
    WRONG_MOOD,
)

logger = logging.getLogger(__name__)


def _name(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get('name', 'there')


async def handle_mood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or not (1 <= int(text) <= 10):
        await update.message.reply_text(WRONG_MOOD, reply_markup=get_mood_keyboard())
        return CHECK_IN_MOOD
    context.user_data['mood_score'] = int(text)
    await update.message.reply_text(CHECK_IN_TEXT_PROMPT.format(score=text))
    return CHECK_IN_TEXT


async def _send_crisis_resources(update: Update) -> None:
    """Deliver crisis resources. Never gated on an opt-in, a DB call or an LLM call."""
    await update.message.reply_text(GUIDANCE_CRISIS_RESOURCES, parse_mode='Markdown')


async def handle_entry_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    telegram_id = update.effective_user.id
    mood_score = context.user_data.get('mood_score')
    name = _name(context)

    # Fail closed: without the score we cannot tell a 1 from a 9, and assuming
    # a middling default silently skips both the guidance offer and the crisis
    # path. Re-ask instead.
    if mood_score is None:
        logger.warning('handle_entry_text: mood_score missing for user %s', telegram_id)
        await update.message.reply_text(MOOD_LOST, reply_markup=get_mood_keyboard())
        return CHECK_IN_MOOD

    # Before the try block on purpose. Everything below can fail — a Mongo
    # blip, an Anthropic timeout — and the except returns to the main menu,
    # so anything downstream of it is not a guarantee.
    if mood_score <= CRISIS_MOOD_THRESHOLD:
        await _send_crisis_resources(update)

    try:
        tags = await asyncio.to_thread(deps.llm_svc.extract_tags, text)
        await asyncio.to_thread(deps.journal_svc.save_entry, telegram_id, mood_score, text, tags)
        stats = await asyncio.to_thread(deps.journal_svc.get_stats, telegram_id)
        llm_response = await asyncio.to_thread(deps.llm_svc.get_empathetic_response, mood_score, text)
    except Exception:
        logger.exception('Check-in failed for user %s', telegram_id)
        await update.message.reply_text(ERROR_GENERIC, reply_markup=get_main_menu_keyboard())
        return MAIN_MENU

    await update.message.reply_text(
        CHECK_IN_DONE.format(name=escape_md(name), llm_response=escape_md(llm_response), streak=stats['streak']),
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown',
    )

    if mood_score <= LOW_MOOD_THRESHOLD:
        context.user_data['entry_text'] = text
        offer = GUIDANCE_OFFER_VERY_LOW if mood_score <= CRISIS_MOOD_THRESHOLD else GUIDANCE_OFFER_LOW
        await update.message.reply_text(offer, reply_markup=get_guidance_keyboard())
        return CHECK_IN_GUIDANCE_OFFER

    return MAIN_MENU


async def handle_guidance_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mood_score = context.user_data.get('mood_score')

    # This state is only reachable from a low-mood check-in, so a missing score
    # means lost state, not a well user. Fail closed and show resources.
    if mood_score is None:
        logger.warning('handle_guidance_offer: mood_score missing for user %s', update.effective_user.id)
        await _send_crisis_resources(update)
        mood_score = CRISIS_MOOD_THRESHOLD

    if update.message.text != GUIDANCE_YES:
        await update.message.reply_text(GUIDANCE_DECLINED, reply_markup=get_main_menu_keyboard())
        return MAIN_MENU

    entry_text = context.user_data.get('entry_text', '')
    if not entry_text:
        logger.warning('handle_guidance_offer: entry_text missing for user %s', update.effective_user.id)

    guidance = await asyncio.to_thread(deps.llm_svc.get_psychological_guidance, mood_score, entry_text)

    await update.message.reply_text(guidance, reply_markup=get_main_menu_keyboard())
    return MAIN_MENU
