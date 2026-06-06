"""
bot/handlers/onboarding.py — сбор данных пользователя (имя, дата, время, место)
Использует ConversationHandler для управления состояниями диалога
"""

import re
import logging
from datetime import date, time
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters

from bot.messages import (
    WELCOME_MESSAGE, ASK_NAME, ASK_BIRTH_DATE, ASK_BIRTH_TIME, ASK_BIRTH_PLACE,
    INVALID_DATE, INVALID_PLACE, CALCULATING_CHART, CHART_READY
)
from bot.keyboards import skip_time_keyboard, main_menu_keyboard
from services.geocoding import get_location_data
from services.astrology import build_natal_chart
from services.user import create_or_update_user, update_streak

logger = logging.getLogger(__name__)

# ============================================================================
# СОСТОЯНИЯ ConversationHandler
# ============================================================================
NAME, BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE = range(4)


# ============================================================================
# ОБРАБОТЧИКИ
# ============================================================================

async def start_onboarding(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начало онбординга: кнопка start_onboarding
    Выводим приветствие и просим имя
    """
    if update.callback_query:
        await update.callback_query.answer()

    msg = update.effective_message
    if not msg:
        logger.warning("start_onboarding: no effective_message")
        return NAME

    user = update.effective_user
    logger.info(f"User {user.id} started onboarding")

    await msg.reply_text(WELCOME_MESSAGE, parse_mode="Markdown")
    await msg.reply_text(ASK_NAME)

    return NAME


async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем имя пользователя"""

    if not update.message or not update.message.text:
        logger.warning("get_name: no message text")
        return NAME

    text = update.message.text.strip()

    if not text or text.startswith('/'):
        await update.message.reply_text("Напиши пожалуйста своё имя 🌟")
        return NAME

    name = text.split()[0]
    ctx.user_data['name'] = name

    logger.info(f"User {update.effective_user.id} provided name: {name}")

    await update.message.reply_text(
        ASK_BIRTH_DATE.format(name=name),
        parse_mode="Markdown"
    )

    return BIRTH_DATE


async def get_birth_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем дату рождения в формате дд.мм.гггг"""

    if not update.message or not update.message.text:
        logger.warning("get_birth_date: no message text")
        return BIRTH_DATE

    text = update.message.text.strip()

    match = re.search(r'(\d{1,2})[.\s/](\d{1,2})[.\s/](\d{4})', text)

    if not match:
        await update.message.reply_text(INVALID_DATE, parse_mode="Markdown")
        return BIRTH_DATE

    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))

    try:
        birth_date = date(year, month, day)
    except ValueError:
        await update.message.reply_text(INVALID_DATE, parse_mode="Markdown")
        return BIRTH_DATE

    if birth_date > date.today():
        await update.message.reply_text(
            "Дата не может быть в будущем! 🌙",
            parse_mode="Markdown"
        )
        return BIRTH_DATE

    ctx.user_data['birth_date'] = birth_date
    logger.info(f"User {update.effective_user.id} provided birth date: {birth_date}")

    await update.message.reply_text(
        ASK_BIRTH_TIME,
        parse_mode="Markdown",
        reply_markup=skip_time_keyboard()
    )

    return BIRTH_TIME


async def get_birth_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем время рождения в формате HH:MM"""

    if not update.message or not update.message.text:
        logger.warning("get_birth_time: no message text")
        return BIRTH_TIME

    text = update.message.text.strip()

    match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', text)

    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            await update.message.reply_text(
                "Неправильное время. Попробуй ещё раз в формате 14:30",
                parse_mode="Markdown"
            )
            return BIRTH_TIME

        ctx.user_data['birth_time'] = time(hour, minute)
        logger.info(f"User {update.effective_user.id} provided birth time: {hour}:{minute}")
    else:
        await update.message.reply_text(
            "Не могу распознать время. Попробуй формат 14:30",
            parse_mode="Markdown"
        )
        return BIRTH_TIME

    await update.message.reply_text(ASK_BIRTH_PLACE)

    return BIRTH_PLACE


async def skip_birth_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропускаем время рождения (если не знает)"""

    if not update.callback_query:
        logger.warning("skip_birth_time: no callback_query")
        return BIRTH_TIME

    await update.callback_query.answer()
    ctx.user_data['birth_time'] = None

    logger.info(f"User {update.effective_user.id} skipped birth time")

    await update.effective_message.reply_text(ASK_BIRTH_PLACE)

    return BIRTH_PLACE


async def get_birth_place(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получаем место рождения и геокодируем его (место -> координаты)
    Потом строим натальную карту
    БЕЗ генерации прогноза (чтобы не требовались деньги на Claude API)
    """

    if not update.message or not update.message.text:
        logger.warning("get_birth_place: no message text")
        return BIRTH_PLACE

    place_name = update.message.text.strip()
    user = update.effective_user

    await update.message.reply_text(CALCULATING_CHART)

    location = await get_location_data(place_name)

    if not location:
        await update.message.reply_text(INVALID_PLACE, parse_mode="Markdown")
        return BIRTH_PLACE

    ctx.user_data['location'] = location
    logger.info(f"User {user.id} provided birth place: {location['place']}")

    try:
        natal = build_natal_chart(
            name=ctx.user_data['name'],
            birth_date=ctx.user_data['birth_date'],
            birth_time=ctx.user_data.get('birth_time'),
            lat=location['latitude'],
            lng=location['longitude'],
            tz=location['timezone'],
        )

        logger.info(f"Natal chart calculated for user {user.id}")

        await create_or_update_user(
            telegram_id=user.id,
            username=user.username,
            name=ctx.user_data['name'],
            birth_date=ctx.user_data['birth_date'],
            birth_time=ctx.user_data.get('birth_time'),
            birth_place=location['place'],
            latitude=location['latitude'],
            longitude=location['longitude'],
            timezone=location['timezone'],
            natal=natal,
        )

        await update_streak(user.id)

        rising_str = f"↑ Асцендент **{natal['rising']['sign']}**\n" if natal.get('rising', {}).get('sign') else ""

        chart_text = (
            f"🌟 *Твоя натальная карта готова, {ctx.user_data['name']}!*\n\n"
            f"☀️ **Солнце** в {natal['sun']['sign']} ({natal['sun']['degree']}°)\n"
            f"🌙 **Луна** в {natal['moon']['sign']}\n"
            f"{rising_str}"
            f"\n☿️ Меркурий в {natal['mercury']['sign']}\n"
            f"♀️ Венера в {natal['venus']['sign']}\n"
            f"♂️ Марс в {natal['mars']['sign']}\n"
            f"♃ Юпитер в {natal['jupiter']['sign']}"
        )

        await update.message.reply_text(chart_text, parse_mode="Markdown")

        await update.message.reply_text(
            "✓ Натальная карта готова!\n\n"
            "Твой персональный прогноз смотри командой /forecast когда будешь готов.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

        logger.info(f"Onboarding completed for user {user.id}")

    except Exception as e:
        logger.error(f"Error in onboarding for user {user.id}: {e}")
        await update.message.reply_text(
            "Ошибка при расчёте карты 😔\n\nПопробуй позже.",
            parse_mode="Markdown"
        )

    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога"""
    if update.callback_query:
        await update.callback_query.answer()

    msg = update.effective_message
    if msg:
        await msg.reply_text(
            "Отмена. Напиши /start чтобы начать заново.",
            reply_markup=main_menu_keyboard()
        )
    return ConversationHandler.END


# ============================================================================
# CONVERSATION HANDLER (для использования в main.py)
# ============================================================================

def get_onboarding_handler() -> ConversationHandler:
    """
    Создаёт и возвращает ConversationHandler для онбординга
    """
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_onboarding, pattern="^start_onboarding$"),
        ],
        states={
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
            ],
            BIRTH_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_birth_date)
            ],
            BIRTH_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_birth_time),
                CallbackQueryHandler(skip_birth_time, pattern="^skip_time$"),
            ],
            BIRTH_PLACE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_birth_place)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        allow_reentry=True,
    )
