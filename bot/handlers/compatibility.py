"""
bot/handlers/compatibility.py — ConversationHandler для анализа совместимости
"""

import re
import logging
from datetime import date, time

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CommandHandler, MessageHandler, CallbackQueryHandler, filters,
)

from bot.messages import (
    ASK_PARTNER_NAME, ASK_PARTNER_BIRTH_DATE, ASK_PARTNER_BIRTH_TIME,
    ASK_PARTNER_BIRTH_PLACE, CALCULATING_COMPATIBILITY,
    COMPATIBILITY_HEADER, COMPATIBILITY_SCORE,
    INVALID_DATE, INVALID_PLACE,
)
from bot.keyboards import skip_time_keyboard, main_menu_keyboard
from services.geocoding import get_location_data
from services.astrology import build_natal_chart
from services.compatibility import generate_compatibility_analysis
from services.user import get_user

logger = logging.getLogger(__name__)

PARTNER_NAME, PARTNER_BIRTH_DATE, PARTNER_BIRTH_TIME, PARTNER_BIRTH_PLACE = range(4)


async def start_compatibility(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    msg = update.effective_message

    user = await get_user(update.effective_user.id)

    if not user or not user.data_complete:
        await msg.reply_text("Сначала пройди онбординг! 👋\n\nНапиши /start")
        return ConversationHandler.END

    from services.premium import check_limit
    allowed, limit_msg = await check_limit(user, "compat_per_day")
    if not allowed:
        await msg.reply_text(limit_msg)
        return ConversationHandler.END

    natal = user.natal_chart
    if not natal:
        natal = build_natal_chart(
            name=user.name,
            birth_date=user.birth_date,
            birth_time=user.birth_time,
            lat=user.latitude,
            lng=user.longitude,
            tz=user.timezone,
        )

    ctx.user_data["user_name"]  = user.name
    ctx.user_data["user_natal"] = natal

    logger.info(f"User {update.effective_user.id} started compatibility")
    await msg.reply_text(ASK_PARTNER_NAME)
    return PARTNER_NAME


async def get_partner_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        await update.message.reply_text("Напиши пожалуйста имя партнёра 🌟")
        return PARTNER_NAME

    ctx.user_data["partner_name"] = text.split()[0]
    await update.message.reply_text(
        ASK_PARTNER_BIRTH_DATE.format(partner_name=ctx.user_data["partner_name"])
    )
    return PARTNER_BIRTH_DATE


async def get_partner_birth_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    match = re.search(r"(\d{1,2})[.\s/](\d{1,2})[.\s/](\d{4})", text)

    if not match:
        await update.message.reply_text(INVALID_DATE, parse_mode="Markdown")
        return PARTNER_BIRTH_DATE

    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        birth_date = date(year, month, day)
    except ValueError:
        await update.message.reply_text(INVALID_DATE, parse_mode="Markdown")
        return PARTNER_BIRTH_DATE

    if birth_date > date.today():
        await update.message.reply_text("Дата не может быть в будущем! 🌙")
        return PARTNER_BIRTH_DATE

    ctx.user_data["partner_birth_date"] = birth_date
    await update.message.reply_text(
        ASK_PARTNER_BIRTH_TIME.format(partner_name=ctx.user_data["partner_name"]),
        reply_markup=skip_time_keyboard(),
    )
    return PARTNER_BIRTH_TIME


async def get_partner_birth_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    match = re.search(r"(\d{1,2}):(\d{2})", text)

    if not match:
        await update.message.reply_text("Не могу распознать время. Попробуй формат 14:30")
        return PARTNER_BIRTH_TIME

    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await update.message.reply_text("Неправильное время. Попробуй формат 14:30")
        return PARTNER_BIRTH_TIME

    ctx.user_data["partner_birth_time"] = time(hour, minute)
    await update.message.reply_text(
        ASK_PARTNER_BIRTH_PLACE.format(partner_name=ctx.user_data["partner_name"])
    )
    return PARTNER_BIRTH_PLACE


async def skip_partner_birth_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    ctx.user_data["partner_birth_time"] = None
    await update.callback_query.message.reply_text(
        ASK_PARTNER_BIRTH_PLACE.format(partner_name=ctx.user_data["partner_name"])
    )
    return PARTNER_BIRTH_PLACE


async def get_partner_birth_place(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    place_name = (update.message.text or "").strip()
    user_tg = update.effective_user

    await update.message.reply_text(CALCULATING_COMPATIBILITY)

    location = await get_location_data(place_name)
    if not location:
        await update.message.reply_text(INVALID_PLACE, parse_mode="Markdown")
        return PARTNER_BIRTH_PLACE

    try:
        partner_natal = build_natal_chart(
            name=ctx.user_data["partner_name"],
            birth_date=ctx.user_data["partner_birth_date"],
            birth_time=ctx.user_data.get("partner_birth_time"),
            lat=location["latitude"],
            lng=location["longitude"],
            tz=location["timezone"],
        )

        analysis, score = await generate_compatibility_analysis(
            name1=ctx.user_data["user_name"],
            natal1=ctx.user_data["user_natal"],
            name2=ctx.user_data["partner_name"],
            natal2=partner_natal,
        )

        header = COMPATIBILITY_HEADER.format(
            name=ctx.user_data["user_name"],
            partner_name=ctx.user_data["partner_name"],
        )
        score_line = COMPATIBILITY_SCORE.format(score=score)
        full_message = f"{header}\n\n{score_line}\n\n{analysis}"

        try:
            await update.message.reply_text(
                full_message,
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(),
            )
        except Exception:
            await update.message.reply_text(full_message, reply_markup=main_menu_keyboard())

        logger.info(f"Compatibility sent to user {user_tg.id}, score={score}%")

    except Exception as e:
        logger.error(f"Error in compatibility for user {user_tg.id}: {e}")
        await update.message.reply_text(
            "Ошибка при анализе совместимости 😔\n\nПопробуй позже.",
        )

    return ConversationHandler.END


async def cancel_compat(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Отмена. Напиши /compat чтобы начать заново.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


def get_compatibility_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("compat", start_compatibility),
            CallbackQueryHandler(start_compatibility, pattern="^compatibility$"),
        ],
        states={
            PARTNER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_partner_name),
            ],
            PARTNER_BIRTH_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_partner_birth_date),
            ],
            PARTNER_BIRTH_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_partner_birth_time),
                CallbackQueryHandler(skip_partner_birth_time, pattern="^skip_time$"),
            ],
            PARTNER_BIRTH_PLACE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_partner_birth_place),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_compat)],
        allow_reentry=True,
    )
