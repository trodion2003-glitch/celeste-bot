"""
bot/handlers/payments.py — обработка платежей через Telegram Stars
"""

import logging

from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes

from services.premium import get_premium_price, get_premium_info, activate_premium, is_premium
from services.user import get_user
from bot.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /premium — показать информацию и инвойс"""
    user_id = update.effective_user.id
    msg = update.effective_message

    user = await get_user(user_id)
    if not user:
        await msg.reply_text("Сначала пройди онбординг! 👋\n\nНапиши /start")
        return

    if is_premium(user):
        await msg.reply_text(
            "✨ У тебя уже есть Premium!\n\nСпасибо за поддержку! 💝",
            reply_markup=main_menu_keyboard(),
        )
        return

    await msg.reply_text(get_premium_info())

    await context.bot.send_invoice(
        chat_id=user_id,
        title="Celesté Premium",
        description="30 дней неограниченного доступа",
        payload="premium_30_days",
        currency="XTR",
        prices=[LabeledPrice("Premium 30 дней", get_premium_price())],
        provider_token="",
        start_parameter="premium",
    )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка перед платежом"""
    query = update.pre_checkout_query
    if query.payload == "premium_30_days":
        await query.answer(ok=True)
        logger.info(f"Pre-checkout OK for user {query.from_user.id}")
    else:
        await query.answer(ok=False, error_message="Неверный платёж")
        logger.error(f"Invalid payload: {query.payload}")


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Успешный платёж"""
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment
    logger.info(f"Successful payment from user {user_id}: {payment_info.total_amount} XTR")

    from models.database import AsyncSessionLocal
    from sqlalchemy import select
    from models.user import User

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user:
            await activate_premium(db_user)
            await session.commit()

    from services.analytics import track_premium_purchase
    await track_premium_purchase(user_id)

    await update.message.reply_text(
        "✨ Спасибо за покупку!\n\n"
        "🎉 Твой Premium активирован на 30 дней!\n\n"
        "Теперь ты можешь использовать все функции без ограничений.",
        reply_markup=main_menu_keyboard(),
    )
    logger.info(f"Premium activated for user {user_id}")
