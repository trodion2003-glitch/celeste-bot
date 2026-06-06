"""
bot/keyboards.py — все inline и reply клавиатуры Celesté Bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from bot.messages import SKIP_TIME_BUTTON, SHARE_BUTTON, MENU_BUTTON, RETRY_BUTTON

# ============================================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================================

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню с основными опциями"""
    keyboard = [
        [InlineKeyboardButton("✦ Прогноз на неделю", callback_data="forecast_week")],
        [
            InlineKeyboardButton("☽ Карта дня", callback_data="day_card"),
            InlineKeyboardButton("🌙 Лунный календарь", callback_data="moon_calendar"),
        ],
        [
            InlineKeyboardButton("💫 Совместимость", callback_data="compatibility"),
            InlineKeyboardButton("👤 Моя карта", callback_data="my_chart"),
        ],
        [
            InlineKeyboardButton("✨ Premium", callback_data="premium"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# ОНБОРДИНГ
# ============================================================================

def skip_time_keyboard() -> InlineKeyboardMarkup:
    """Кнопка для пропуска времени рождения"""
    keyboard = [
        [InlineKeyboardButton(SKIP_TIME_BUTTON, callback_data="skip_time")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# ПРОГНОЗ
# ============================================================================

def share_forecast_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Кнопки после прогноза"""
    keyboard = [
        [InlineKeyboardButton(SHARE_BUTTON, callback_data=f"share_forecast_{user_id}")],
        [InlineKeyboardButton(MENU_BUTTON, callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def forecast_actions_keyboard() -> InlineKeyboardMarkup:
    """Кнопки с экшенами для прогноза"""
    keyboard = [
        [InlineKeyboardButton("📤 Поделиться", callback_data="share")],
        [InlineKeyboardButton("❤️ Сохранить", callback_data="save")],
        [InlineKeyboardButton("↩ Меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# RETRY / МЕНЮ
# ============================================================================

def retry_keyboard() -> InlineKeyboardMarkup:
    """Кнопка повторить"""
    keyboard = [
        [InlineKeyboardButton(RETRY_BUTTON, callback_data="retry")],
        [InlineKeyboardButton(MENU_BUTTON, callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Простая кнопка вернуться в меню"""
    keyboard = [
        [InlineKeyboardButton(MENU_BUTTON, callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# СОВМЕСТИМОСТЬ
# ============================================================================

def compatibility_input_keyboard() -> InlineKeyboardMarkup:
    """Для ввода данных второго человека при совместимости"""
    keyboard = [
        [InlineKeyboardButton("🔄 Попробовать ещё раз", callback_data="compatibility_retry")],
        [InlineKeyboardButton("↩ Меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# ПРЕМИУМ
# ============================================================================

def premium_upsell_keyboard() -> InlineKeyboardMarkup:
    """Предложение премиума"""
    keyboard = [
        [InlineKeyboardButton("💳 Купить Premium", callback_data="buy_premium")],
        [InlineKeyboardButton("ℹ️ Что входит?", callback_data="premium_info")],
        [InlineKeyboardButton("↩ Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def premium_info_keyboard() -> InlineKeyboardMarkup:
    """Информация о премиуме"""
    keyboard = [
        [InlineKeyboardButton("🛍️ Купить", url="https://buy.celestebot.com")],
        [InlineKeyboardButton("↩ Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# НАСТРОЙКИ
# ============================================================================

def settings_keyboard() -> InlineKeyboardMarkup:
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton("🔔 Уведомления", callback_data="settings_notifications")],
        [InlineKeyboardButton("🌍 Часовой пояс", callback_data="settings_timezone")],
        [InlineKeyboardButton("👤 Изменить данные", callback_data="settings_edit_profile")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="settings_about")],
        [InlineKeyboardButton("↩ Меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# YES / NO КЛАВИАТУРЫ
# ============================================================================

def yes_no_keyboard() -> InlineKeyboardMarkup:
    """Простой выбор да/нет"""
    keyboard = [
        [
            InlineKeyboardButton("✓ Да", callback_data="yes"),
            InlineKeyboardButton("✗ Нет", callback_data="no"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def yes_no_menu_keyboard() -> InlineKeyboardMarkup:
    """Да/Нет + меню"""
    keyboard = [
        [
            InlineKeyboardButton("✓ Да", callback_data="yes"),
            InlineKeyboardButton("✗ Нет", callback_data="no"),
        ],
        [InlineKeyboardButton("↩ Меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# РЕФЕРАЛЬНЫЕ КНОПКИ
# ============================================================================

def referral_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Кнопка для шаринга реферальной ссылки"""
    keyboard = [
        [InlineKeyboardButton("📤 Пригласить подругу", url=referral_link)],
        [InlineKeyboardButton("ℹ️ Как это работает?", callback_data="referral_info")],
        [InlineKeyboardButton("↩ Меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# ЛУННЫЙ КАЛЕНДАРЬ / СПЕЦИАЛЬНЫЕ
# ============================================================================

def moon_calendar_keyboard() -> InlineKeyboardMarkup:
    """Навигация по лунному календарю"""
    keyboard = [
        [
            InlineKeyboardButton("◀ Предыдущий месяц", callback_data="moon_prev_month"),
            InlineKeyboardButton("Следующий месяц ▶", callback_data="moon_next_month"),
        ],
        [InlineKeyboardButton("↩ Меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# РЕДКИЕ КНОПКИ
# ============================================================================

def report_bug_keyboard() -> InlineKeyboardMarkup:
    """Кнопка для репорта ошибок"""
    keyboard = [
        [InlineKeyboardButton("🐛 Сообщить об ошибке", callback_data="report_bug")],
        [InlineKeyboardButton("💡 Предложить идею", callback_data="suggest_idea")],
        [InlineKeyboardButton("↩ Меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# REPLY КЛАВИАТУРЫ (для ввода текста, а не callback'ов)
# ============================================================================

def main_menu_reply_keyboard() -> ReplyKeyboardMarkup:
    """Reply клавиатура главного меню (если будем использовать)"""
    keyboard = [
        [KeyboardButton("✦ Прогноз")],
        [KeyboardButton("☽ Карта дня"), KeyboardButton("🌙 Календарь")],
        [KeyboardButton("👤 Мои данные"), KeyboardButton("⚙️ Настройки")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,  # Кнопки сжимаются под содержимое
        one_time_keyboard=False,  # Клавиатура не исчезает после нажатия
    )


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def remove_keyboard() -> InlineKeyboardMarkup:
    """Убрать клавиатуру (пустая)"""
    return InlineKeyboardMarkup([])


def get_callback_data(query_data: str) -> str:
    """Получить данные из callback_query
    
    Используется для распарсивания callback_data вида:
    "forecast_week", "share_forecast_12345", и т.д.
    """
    return query_data
