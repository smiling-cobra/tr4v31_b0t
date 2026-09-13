"""Telegram conversation handlers.

Everything here runs on the single asyncio event loop that python-telegram-bot
v20+ uses, so any blocking call — Anthropic over HTTP, pymongo over the wire —
would stall every other user for its duration. The services stay synchronous
(the scheduler calls them too), so each blocking call is handed to a worker
thread with `asyncio.to_thread` at the call site. That boundary is deliberate
and visible: if you add a service call here, wrap it.
"""
import asyncio
import logging
import re
from collections import Counter
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from timezonefinder import TimezoneFinder

from bot.keyboards import (
    CHECK_IN, GUIDANCE_YES, HELP, HISTORY, STATS, WEEKLY_SUMMARY,
    get_guidance_keyboard, get_main_menu_keyboard, get_mood_keyboard, get_timezone_keyboard,
)
from messages.markdown import escape_md
from messages.strings import (
    CANCEL_MESSAGE,
    CHECK_IN_DONE,
    CHECK_IN_MOOD_PROMPT,
    CHECK_IN_TEXT_PROMPT,
    ERROR_GENERIC,
    GUIDANCE_CRISIS_RESOURCES,
    GUIDANCE_DECLINED,
    GUIDANCE_OFFER_LOW,
    GUIDANCE_OFFER_VERY_LOW,
    HELP_MESSAGE,
    HISTORY_EMPTY,
    HISTORY_ENTRY,
    HISTORY_HEADER,
    MAIN_MENU_MESSAGE,
    MOOD_LOST,
    ONBOARDING_DONE,
    ONBOARDING_TIME as ONBOARDING_TIME_MSG,
    ONBOARDING_TIMEZONE as ONBOARDING_TIMEZONE_MSG,
    ONBOARDING_WELCOME,
    PRIVACY_ACCEPTED_PROMPT,
    PRIVACY_NOTICE,
    STATS_EMPTY,
    STATS_MESSAGE,
    WEEKLY_SUMMARY_EMPTY,
    WEEKLY_SUMMARY_HEADER,
    WEEKLY_SUMMARY_LLM_INTRO,
    WEEKLY_SUMMARY_TAGS,
    WEEKLY_SUMMARY_TOO_FEW,
    WEEKLY_SUMMARY_TREND_ROW,
    TIMEZONE_DETECTED,
    TIMEZONE_DETECTION_FAILED,
    TIMEZONE_SUGGESTIONS,
    WRONG_MOOD,
    WRONG_TIME,
    WRONG_TIMEZONE,
)
from services.journal_service import JournalService, MIN_ENTRIES_FOR_WEEKLY_SUMMARY
from services.llm_service import LlmService
from services.time_utils import resolve_timezone, to_local
from services.user_service import UserService

logger = logging.getLogger(__name__)

_tf = TimezoneFinder()
_ALL_TIMEZONES = sorted(available_timezones())


def _search_timezones(query: str) -> list:
    """Return IANA timezone names that contain the query (case-insensitive, spaces→underscores)."""
    needle = query.strip().replace(' ', '_').lower()
    return [tz for tz in _ALL_TIMEZONES if needle in tz.lower()]


(
    ONBOARDING_NAME,
    ONBOARDING_TIMEZONE,
    ONBOARDING_TIME,
    MAIN_MENU,
    CHECK_IN_MOOD,
    CHECK_IN_TEXT,
    CHECK_IN_GUIDANCE_OFFER,
) = range(7)

LOW_MOOD_THRESHOLD = 4
CRISIS_MOOD_THRESHOLD = 2

_user_svc = UserService()
_journal_svc = JournalService()
_llm_svc = LlmService()


def _name(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get('name', 'there')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    user = await asyncio.to_thread(_user_svc.get, telegram_id)
    if user and user.get('onboarded'):
        context.user_data['name'] = user['name']
        await update.message.reply_text(
            MAIN_MENU_MESSAGE.format(name=user['name']),
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU
    await update.message.reply_text(ONBOARDING_WELCOME)
    await update.message.reply_text(PRIVACY_NOTICE, parse_mode='Markdown')
    await update.message.reply_text(PRIVACY_ACCEPTED_PROMPT)
    return ONBOARDING_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    context.user_data['name'] = name
    await update.message.reply_text(
        ONBOARDING_TIMEZONE_MSG.format(name=name),
        reply_markup=get_timezone_keyboard(),
    )
    return ONBOARDING_TIMEZONE


async def handle_timezone_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    loc = update.message.location
    tz_str = _tf.timezone_at(lat=loc.latitude, lng=loc.longitude)
    if not tz_str:
        await update.message.reply_text(TIMEZONE_DETECTION_FAILED, reply_markup=get_timezone_keyboard())
        return ONBOARDING_TIMEZONE
    context.user_data['timezone'] = tz_str
    await update.message.reply_text(
        TIMEZONE_DETECTED.format(timezone=escape_md(tz_str)),
        parse_mode='Markdown',
        reply_markup=get_timezone_keyboard(),
    )
    await update.message.reply_text(ONBOARDING_TIME_MSG, reply_markup=ReplyKeyboardRemove())
    return ONBOARDING_TIME


async def handle_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tz_str = update.message.text.strip()

    # Exact IANA match
    try:
        ZoneInfo(tz_str)
        context.user_data['timezone'] = tz_str
        await update.message.reply_text(ONBOARDING_TIME_MSG, reply_markup=ReplyKeyboardRemove())
        return ONBOARDING_TIME
    except (ZoneInfoNotFoundError, KeyError):
        pass

    # Fuzzy substring search
    matches = _search_timezones(tz_str)
    if len(matches) == 1:
        context.user_data['timezone'] = matches[0]
        await update.message.reply_text(
            TIMEZONE_DETECTED.format(timezone=escape_md(matches[0])),
            parse_mode='Markdown',
        )
        await update.message.reply_text(ONBOARDING_TIME_MSG, reply_markup=ReplyKeyboardRemove())
        return ONBOARDING_TIME
    if 1 < len(matches) <= 5:
        kb = ReplyKeyboardMarkup([[m] for m in matches], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(TIMEZONE_SUGGESTIONS.format(query=tz_str), reply_markup=kb)
        return ONBOARDING_TIMEZONE

    await update.message.reply_text(WRONG_TIMEZONE)
    return ONBOARDING_TIMEZONE


async def handle_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    time_str = update.message.text.strip()
    if not re.match(r'^\d{2}:\d{2}$', time_str):
        await update.message.reply_text(WRONG_TIME)
        return ONBOARDING_TIME
    h, m = int(time_str[:2]), int(time_str[3:])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        await update.message.reply_text(WRONG_TIME)
        return ONBOARDING_TIME

    name = context.user_data['name']
    timezone = context.user_data['timezone']
    await asyncio.to_thread(
        _user_svc.create_or_update,
        update.effective_user.id,
        name=name,
        timezone=timezone,
        reminder_time=time_str,
        onboarded=True,
    )
    await update.message.reply_text(
        ONBOARDING_DONE.format(name=escape_md(name), reminder_time=time_str, timezone=timezone),
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown',
    )
    return MAIN_MENU


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    name = _name(context)

    if choice == CHECK_IN:
        await update.message.reply_text(
            CHECK_IN_MOOD_PROMPT.format(name=name),
            reply_markup=get_mood_keyboard()
        )
        return CHECK_IN_MOOD

    if choice == HISTORY:
        return await show_history(update, context)

    if choice == STATS:
        return await show_stats(update, context)

    if choice == WEEKLY_SUMMARY:
        return await show_weekly_summary(update, context)

    if choice == HELP:
        await update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')
        return MAIN_MENU

    return MAIN_MENU


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
        tags = await asyncio.to_thread(_llm_svc.extract_tags, text)
        await asyncio.to_thread(_journal_svc.save_entry, telegram_id, mood_score, text, tags)
        stats = await asyncio.to_thread(_journal_svc.get_stats, telegram_id)
        llm_response = await asyncio.to_thread(_llm_svc.get_empathetic_response, mood_score, text)
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
        offer = GUIDANCE_OFFER_VERY_LOW if mood_score <= 2 else GUIDANCE_OFFER_LOW
        await update.message.reply_text(offer, reply_markup=get_guidance_keyboard())
        return CHECK_IN_GUIDANCE_OFFER

    return MAIN_MENU


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    try:
        entries = await asyncio.to_thread(_journal_svc.get_recent_entries, telegram_id)
        tz = await _user_timezone(telegram_id)
    except Exception:
        logger.exception('Failed to load history for user %s', telegram_id)
        await update.message.reply_text(ERROR_GENERIC, reply_markup=get_main_menu_keyboard())
        return MAIN_MENU

    if not entries:
        await update.message.reply_text(
            HISTORY_EMPTY, parse_mode='Markdown', reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU

    body = HISTORY_HEADER.format(count=len(entries))
    for e in entries:
        date_str = to_local(e['created_at'], tz).strftime('%d %b %Y')
        body += HISTORY_ENTRY.format(date=date_str, score=e['mood_score'], text=escape_md(e['text'][:200]))

    await update.message.reply_text(body, parse_mode='Markdown', reply_markup=get_main_menu_keyboard())
    return MAIN_MENU


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    try:
        stats = await asyncio.to_thread(_journal_svc.get_stats, telegram_id)
        entries = await asyncio.to_thread(_journal_svc.get_recent_entries, telegram_id, 7)
    except Exception:
        logger.exception('Failed to load stats for user %s', telegram_id)
        await update.message.reply_text(ERROR_GENERIC, reply_markup=get_main_menu_keyboard())
        return MAIN_MENU

    if stats['total'] == 0:
        await update.message.reply_text(STATS_EMPTY, reply_markup=get_main_menu_keyboard())
        return MAIN_MENU

    all_tags = [tag for e in entries for tag in e.get('tags', [])]
    top_tags = ', '.join(f'#{escape_md(t)}' for t, _ in Counter(all_tags).most_common(3)) or 'none yet'

    await update.message.reply_text(
        STATS_MESSAGE.format(
            streak=stats['streak'],
            total=stats['total'],
            avg_mood=stats['avg_mood'],
            tags=top_tags,
        ),
        parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard(),
    )
    return MAIN_MENU


async def _user_timezone(telegram_id: int):
    """The user's timezone for date labels, so a stored UTC instant is shown as
    the day they experienced it."""
    user = await asyncio.to_thread(_user_svc.get, telegram_id) or {}
    return resolve_timezone(user.get('timezone'), telegram_id)


def _mood_bar(score: int) -> str:
    n = max(0, min(10, score))
    return '▓' * n + '░' * (10 - n)


async def show_weekly_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    try:
        user = await asyncio.to_thread(_user_svc.get, telegram_id) or {}
        user_timezone = user.get('timezone')
        tz = resolve_timezone(user_timezone, telegram_id)
        entries = await asyncio.to_thread(
            _journal_svc.get_weekly_entries, telegram_id, user_timezone
        )
    except Exception:
        logger.exception('Failed to load weekly entries for user %s', telegram_id)
        await update.message.reply_text(ERROR_GENERIC, reply_markup=get_main_menu_keyboard())
        return MAIN_MENU

    if not entries:
        await update.message.reply_text(
            WEEKLY_SUMMARY_EMPTY, parse_mode='Markdown', reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU

    date_from = to_local(entries[0]['created_at'], tz).strftime('%d %b')
    date_to = to_local(entries[-1]['created_at'], tz).strftime('%d %b')
    body = WEEKLY_SUMMARY_HEADER.format(date_from=date_from, date_to=date_to, count=len(entries))

    for e in entries:
        body += WEEKLY_SUMMARY_TREND_ROW.format(
            score=e['mood_score'],
            bar=_mood_bar(e['mood_score']),
            day=to_local(e['created_at'], tz).strftime('%a %d %b'),
        )

    all_tags = [tag for e in entries for tag in e.get('tags', [])]
    top_tags = ', '.join(f'#{escape_md(t)}' for t, _ in Counter(all_tags).most_common(5)) or 'none yet'
    body += WEEKLY_SUMMARY_TAGS.format(tags=top_tags)

    if len(entries) >= MIN_ENTRIES_FOR_WEEKLY_SUMMARY:
        body += WEEKLY_SUMMARY_LLM_INTRO
        body += escape_md(await asyncio.to_thread(_llm_svc.get_weekly_summary, entries))
    else:
        body += WEEKLY_SUMMARY_TOO_FEW

    await update.message.reply_text(body, parse_mode='Markdown', reply_markup=get_main_menu_keyboard())
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

    guidance = await asyncio.to_thread(_llm_svc.get_psychological_guidance, mood_score, entry_text)

    await update.message.reply_text(guidance, reply_markup=get_main_menu_keyboard())
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        CANCEL_MESSAGE.format(name=_name(context)),
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def register(application: Application) -> None:
    handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('history', show_history),
            CommandHandler('stats', show_stats),
            CommandHandler('summary', show_weekly_summary),
        ],
        states={
            ONBOARDING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            ONBOARDING_TIMEZONE: [
                MessageHandler(filters.LOCATION, handle_timezone_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_timezone),
            ],
            ONBOARDING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reminder_time)],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu),
                CommandHandler('history', show_history),
                CommandHandler('stats', show_stats),
                CommandHandler('summary', show_weekly_summary),
            ],
            CHECK_IN_MOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mood)],
            CHECK_IN_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_entry_text)],
            CHECK_IN_GUIDANCE_OFFER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guidance_offer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    application.add_handler(handler)
