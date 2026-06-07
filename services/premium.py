"""
services/premium.py — проверка premium статуса и лимиты
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from models.user import User

logger = logging.getLogger(__name__)

# ============================================================================
# ЛИМИТЫ ДЛЯ БЕСПЛАТНЫХ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

LIMITS = {
    "compat_per_day": 5,
    "forecast_per_day": 1,
    "day_per_day": 10,
    "moon_per_day": 10,
}

# ============================================================================
# ПРОВЕРКА PREMIUM
# ============================================================================

def is_premium(user: User) -> bool:
    if not user or not user.is_premium:
        return False
    if user.premium_until:
        now = datetime.now(tz=ZoneInfo("UTC"))
        if user.premium_until > now:
            return True
    return False


async def check_limit(user: User, feature: str) -> tuple[bool, str]:
    if is_premium(user):
        return True, ""

    limit = LIMITS.get(feature, 0)
    if limit == 0:
        return True, ""

    counter = getattr(user, f"{feature}_today", 0) or 0
    if counter >= limit:
        message = (
            f"✨ Ты использовал лимит {feature.replace('_per_day', '')} на сегодня ({limit}).\n\n"
            f"Получи доступ ко всему в Premium! 💳\n\n"
            f"/premium"
        )
        return False, message

    return True, ""


def get_premium_price() -> int:
    return 199  # Telegram Stars


def get_premium_duration_days() -> int:
    return 30


async def activate_premium(user: User) -> None:
    now = datetime.now(tz=ZoneInfo("UTC"))
    duration = timedelta(days=get_premium_duration_days())
    user.is_premium = True
    user.premium_until = now + duration
    logger.info(f"Premium activated for user {user.id} until {user.premium_until}")


def get_premium_info() -> str:
    price = get_premium_price()
    days = get_premium_duration_days()
    return (
        f"✨ PREMIUM CELESTÉ\n\n"
        f"Цена: {price} ⭐ (примерно 2-3 USD)\n"
        f"Длительность: {days} дней\n\n"
        f"Включает:\n"
        f"• Неограниченные анализы совместимости\n"
        f"• Приоритет в обработке\n"
        f"• Расширенные функции\n\n"
        f"Отмена в любой момент."
    )
