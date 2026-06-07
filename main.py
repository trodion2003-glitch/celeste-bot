"""
main.py — запуск Celesté Bot (ИСПРАВЛЕННАЯ ВЕРСИЯ)
"""

import logging
import warnings
from telegram import Update, BotCommand
from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", message=".*per_message=False.*", category=PTBUserWarning)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PreCheckoutQueryHandler, filters, ContextTypes
)

from config import BOT_TOKEN, DEBUG
from logger_config import setup_logging, get_logger
from models.database import init_db
from services.redis_cache import close_redis, get_redis
from bot.keyboards import main_menu_keyboard
from bot.messages import WELCOME_MESSAGE, MAIN_MENU_MESSAGE

# ИМПОРТИРУЕМ ВСЁ ИЗ ONBOARDING
from bot.handlers.onboarding import (
    NAME, BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE,
    get_name, get_birth_date, get_birth_time, get_birth_place, skip_birth_time, cancel
)
from bot.handlers.compatibility import get_compatibility_handler
from bot.handlers.payments import (
    premium_command, precheckout_callback, successful_payment_callback,
)
from bot.handlers.settings import (
    settings_command, settings_push_handler,
    push_enable_handler, push_disable_handler, settings_back_handler,
)
from services.push_notifications import (
    send_morning_notifications, send_weekly_forecast_notifications,
)

setup_logging()
logger = get_logger(__name__)


async def _safe_reply(msg, text: str, **kwargs):
    """Отправить текст с Markdown, при ошибке парсинга — без форматирования."""
    try:
        await msg.reply_text(text, parse_mode="Markdown", **kwargs)
    except Exception:
        await msg.reply_text(text, **kwargs)


# ============================================================================
# ПРОСТЫЕ HANDLERS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда /start"""
    user = update.effective_user
    
    from services.user import get_user
    existing_user = await get_user(user.id)
    
    if existing_user:
        logger.info(f"Returning user {user.id}")
        await update.message.reply_text(
            f"✦ Привет снова! 🌙\n\nЧто хочешь узнать?",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END
    else:
        logger.info(f"New user {user.id}")
        await update.message.reply_text(
            WELCOME_MESSAGE,
            parse_mode="Markdown"
        )
        await update.message.reply_text("Как тебя зовут? Напиши только имя 🌟")
        return NAME


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /menu"""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            MAIN_MENU_MESSAGE,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            MAIN_MENU_MESSAGE,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help"""
    from bot.messages import HELP_MESSAGE
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode="Markdown"
    )


async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /forecast — прогноз на неделю через Gemini"""
    user_id = update.effective_user.id
    msg = update.effective_message

    if update.callback_query:
        await update.callback_query.answer()

    from services.user import get_user, update_streak
    user = await get_user(user_id)

    if not user or not user.data_complete:
        await msg.reply_text(
            "Сначала пройди онбординг! 👋\n\nНапиши /start",
            parse_mode="Markdown"
        )
        return

    from services.astrology import build_natal_chart
    from services.forecast import generate_weekly_forecast
    from bot.keyboards import main_menu_keyboard
    from datetime import timedelta, date

    await msg.reply_text("⏳ Генерирую твой прогноз...")

    try:
        from services.redis_cache import get_cached_forecast, cache_forecast
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_start_str = week_start.isoformat()

        cached = await get_cached_forecast(user_id, week_start_str)

        if cached:
            logger.info(f"Forecast for user {user_id} from cache")
            forecast_text = cached
        else:
            natal = build_natal_chart(
                name=user.name,
                birth_date=user.birth_date,
                birth_time=user.birth_time,
                lat=user.latitude,
                lng=user.longitude,
                tz=user.timezone,
            )

            forecast_text = await generate_weekly_forecast(user.name, natal, user_id)

            await cache_forecast(user_id, week_start_str, forecast_text)
            logger.info(f"Forecast for user {user_id} generated via Gemini")

        await _safe_reply(msg, forecast_text, reply_markup=main_menu_keyboard())

        await update_streak(user_id)

    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        await msg.reply_text(
            "Ошибка при генерации прогноза 😔\n\nПопробуй позже.",
            parse_mode="Markdown"
        )


async def day_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /day — карта дня"""
    user_id = update.effective_user.id
    msg = update.effective_message

    if update.callback_query:
        await update.callback_query.answer()

    from services.user import get_user
    user = await get_user(user_id)

    if not user or not user.data_complete:
        await msg.reply_text(
            "Сначала пройди онбординг! 👋\n\nНапиши /start",
            parse_mode="Markdown"
        )
        return

    await msg.reply_text("☽ Строю карту дня...")

    try:
        from services.redis_cache import get_redis
        from services.astrology import build_natal_chart, get_current_transits, calculate_aspects
        from services.day_card import generate_day_card
        from datetime import date

        redis = await get_redis()
        cache_key = f"day_card:{user_id}:{date.today().isoformat()}"
        cached = await redis.get(cache_key)

        if cached:
            logger.info(f"Day card for user {user_id} from cache")
            day_card_text = cached
        else:
            natal = build_natal_chart(
                name=user.name,
                birth_date=user.birth_date,
                birth_time=user.birth_time,
                lat=user.latitude,
                lng=user.longitude,
                tz=user.timezone,
            )
            transits = get_current_transits()
            aspects = calculate_aspects(transits)
            day_card_text = await generate_day_card(user.name, natal, transits, aspects)

            await redis.setex(cache_key, 86400, day_card_text)
            logger.info(f"Day card generated for user {user_id}")

        await _safe_reply(msg, day_card_text, reply_markup=main_menu_keyboard())

    except Exception as e:
        logger.error(f"Error generating day card: {e}")
        await msg.reply_text(
            "Ошибка при генерации карты дня 😔\n\nПопробуй позже.",
            parse_mode="Markdown"
        )


async def moon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /moon — лунный календарь на 7 дней"""
    user_id = update.effective_user.id
    msg = update.effective_message

    if update.callback_query:
        await update.callback_query.answer()

    from services.user import get_user
    user = await get_user(user_id)

    if not user or not user.data_complete:
        await msg.reply_text(
            "Сначала пройди онбординг! 👋\n\nНапиши /start",
            parse_mode="Markdown"
        )
        return

    await msg.reply_text("🌙 Генерирую лунный календарь...")

    try:
        from services.redis_cache import get_redis
        from services.moon_calendar import generate_moon_calendar
        from datetime import date

        redis = await get_redis()
        cache_key = f"moon_calendar:{user_id}:{date.today().isoformat()}"
        cached = await redis.get(cache_key)

        if cached:
            logger.info(f"Moon calendar for user {user_id} from cache")
            calendar_text = cached
        else:
            calendar_text = await generate_moon_calendar(user.name, days=7)
            await redis.setex(cache_key, 86400, calendar_text)
            logger.info(f"Moon calendar generated for user {user_id}")

        await _safe_reply(msg, calendar_text, reply_markup=main_menu_keyboard())

    except Exception as e:
        logger.error(f"Error generating moon calendar: {e}")
        await msg.reply_text(
            "Ошибка при генерации календаря 😔\n\nПопробуй позже.",
            parse_mode="Markdown"
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "main_menu":
        await menu_command(update, context)
    elif query.data == "forecast_week":
        await forecast_command(update, context)
    elif query.data == "day_card":
        await day_command(update, context)
    elif query.data == "moon_calendar":
        await moon_command(update, context)
    elif query.data == "compatibility":
        pass  # обрабатывается ConversationHandler в get_compatibility_handler()
    elif query.data == "my_chart":
        await query.message.reply_text(
            "👤 Личный кабинет в разработке!",
            reply_markup=main_menu_keyboard()
        )
    elif query.data == "premium":
        await premium_command(update, context)
    elif query.data == "settings":
        await settings_command(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


async def post_init(application: Application) -> None:
    """Инициализация"""
    logger.info("🌙 Initializing Celesté Bot...")

    try:
        await init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"Database init error: {e}")

    try:
        await get_redis()
        logger.info("✓ Redis connected")
    except Exception as e:
        logger.error(f"Redis init error: {e}")

    try:
        commands = [
            BotCommand("start",    "Начать / Новая регистрация"),
            BotCommand("forecast", "Прогноз на неделю"),
            BotCommand("day",      "Карта дня"),
            BotCommand("moon",     "Лунный календарь"),
            BotCommand("compat",   "Совместимость с партнёром"),
            BotCommand("settings", "Настройки"),
            BotCommand("menu",     "Главное меню"),
            BotCommand("help",     "Справка"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("✓ Bot commands set")
    except Exception as e:
        logger.error(f"Commands init error: {e}")

    # Push-уведомления
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            send_morning_notifications,
            CronTrigger(minute=0),
            name="morning_push",
        )
        scheduler.add_job(
            send_weekly_forecast_notifications,
            CronTrigger(day_of_week="mon", hour=9, minute=0),
            name="weekly_push",
        )
        scheduler.start()
        logger.info("✓ Push scheduler started")
    except Exception as e:
        logger.error(f"Scheduler init error: {e}")


async def post_stop(application: Application) -> None:
    """Очистка при выключении"""
    logger.info("🛑 Shutting down...")
    await close_redis()
    logger.info("✓ Cleanup complete")


# ============================================================================
# ЗАПУСК
# ============================================================================

def main():
    """Запуск бота"""
    
    logger.info("="*50)
    logger.info("🌙 CELESTÉ BOT STARTING 🌙")
    logger.info("="*50)
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_stop(post_stop)
        .build()
    )

    # ====================================================================
    # РЕГИСТРАЦИЯ HANDLERS
    # ====================================================================
    
    # 1. ConversationHandler для онбординга (ГЛАВНЫЙ!)
    onboarding_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
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
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    
    # 2. Остальные команды
    application.add_handler(onboarding_conv_handler)  # ← ГЛАВНОЕ!
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("forecast", forecast_command))
    application.add_handler(CommandHandler("day", day_command))
    application.add_handler(CommandHandler("moon", moon_command))
    application.add_handler(get_compatibility_handler())

    # Premium & Payments
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # Settings
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CallbackQueryHandler(settings_push_handler,  pattern="^settings_push$"))
    application.add_handler(CallbackQueryHandler(push_enable_handler,    pattern="^push_enable$"))
    application.add_handler(CallbackQueryHandler(push_disable_handler,   pattern="^push_disable$"))
    application.add_handler(CallbackQueryHandler(settings_back_handler,  pattern="^settings_back$"))

    # 3. Callback'и
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # 4. Обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("✓ All handlers registered")
    logger.info("🚀 Starting polling...")
    logger.info(f"✓ Debug mode: {DEBUG}")
    
    application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    import asyncio
    import sys

    if sys.platform == 'darwin':
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    asyncio.set_event_loop(asyncio.new_event_loop())

    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)