"""First-time setup: name, timezone, daily reminder time.

Service calls go through `asyncio.to_thread` — see the package docstring.
"""
import asyncio
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from bot.handlers.journal import deps
from bot.handlers.journal.states import MAIN_MENU, ONBOARDING_NAME, ONBOARDING_TIME, ONBOARDING_TIMEZONE
from bot.handlers.journal.timezones import detect_timezone, search_timezones
from bot.keyboards import get_main_menu_keyboard, get_timezone_keyboard
from messages.markdown import escape_md
from messages.strings import (
    ONBOARDING_DONE,
    ONBOARDING_TIME as ONBOARDING_TIME_MSG,
    ONBOARDING_TIMEZONE as ONBOARDING_TIMEZONE_MSG,
    ONBOARDING_WELCOME,
    PRIVACY_ACCEPTED_PROMPT,
    PRIVACY_NOTICE,
    MAIN_MENU_MESSAGE,
    TIMEZONE_DETECTED,
    TIMEZONE_DETECTION_FAILED,
    TIMEZONE_SUGGESTIONS,
    WRONG_TIME,
    WRONG_TIMEZONE,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    user = await asyncio.to_thread(deps.user_svc.get, telegram_id)
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
    tz_str = detect_timezone(loc.latitude, loc.longitude)
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
    matches = search_timezones(tz_str)
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
        deps.user_svc.create_or_update,
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
