"""
bot/handlers/settings.py — управление настройками (уведомления)
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.messages import (
    SETTINGS_MESSAGE, PUSH_ENABLED, PUSH_DISABLED, PUSH_SETTINGS_MENU,
)
from bot.keyboards import main_menu_keyboard
from services.user import get_user, update_push_settings

logger = logging.getLogger(__name__)

_SETTINGS_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔔 Уведомления", callback_data="settings_push")],
    [InlineKeyboardButton("↩ Меню",         callback_data="main_menu")],
])


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /settings"""
    msg = update.effective_message

    from services.analytics import track_command
    await track_command(update.effective_user.id, "settings")

    user = await get_user(update.effective_user.id)
    if not user:
        await msg.reply_text("Сначала пройди онбординг! 👋\n\nНапиши /start")
        return

    await msg.reply_text(SETTINGS_MESSAGE, reply_markup=_SETTINGS_KB)


async def settings_push_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Кнопка 'Уведомления' → показываем статус и переключатели"""
    query = update.callback_query
    await query.answer()

    user = await get_user(update.effective_user.id)
    if not user:
        await query.edit_message_text("Ошибка при загрузке данных")
        return

    status = "✓ Включены" if user.push_enabled else "✗ Отключены"
    text = (
        f"{PUSH_SETTINGS_MENU}\n\n"
        f"Текущий статус: {status}\n"
        f"Время отправки: {user.push_time or '08:00'}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✓ Включить",  callback_data="push_enable")],
        [InlineKeyboardButton("✗ Отключить", callback_data="push_disable")],
        [InlineKeyboardButton("↩ Назад",     callback_data="settings_back")],
    ])
    await query.edit_message_text(text, reply_markup=kb)


async def push_enable_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Включить push-уведомления"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    await update_push_settings(user_id, enabled=True)

    user = await get_user(user_id)
    push_time = (user.push_time if user else None) or "08:00"

    await query.edit_message_text(
        PUSH_ENABLED.format(push_time=push_time),
        reply_markup=main_menu_keyboard(),
    )
    logger.info(f"Push enabled for user {user_id}")


async def push_disable_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отключить push-уведомления"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    await update_push_settings(user_id, enabled=False)

    await query.edit_message_text(PUSH_DISABLED, reply_markup=main_menu_keyboard())
    logger.info(f"Push disabled for user {user_id}")


async def settings_back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вернуться в меню настроек"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(SETTINGS_MESSAGE, reply_markup=_SETTINGS_KB)
