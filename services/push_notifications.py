"""
services/push_notifications.py — отправка push-уведомлений пользователям
"""

import logging
from datetime import datetime

from telegram import Bot
from zoneinfo import ZoneInfo
from sqlalchemy import select

from config import BOT_TOKEN
from models.database import AsyncSessionLocal
from models.user import User
from bot.messages import PUSH_MORNING, PUSH_WEEKLY_FORECAST
from services.astrology import get_current_transits

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def _get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=BOT_TOKEN)
    return _bot


DAY_ADVICES = {
    "♈ Овен":     "Используй энергию инициативы и мужества. День для действия!",
    "♉ Телец":    "Фокусируйся на стабильности и материальных делах.",
    "♊ Близнецы": "День для общения, обучения и обмена информацией.",
    "♋ Рак":      "Вслушайся в свои эмоции. Уделись семье и близким.",
    "♌ Лев":      "Дай волю творчеству и самовыражению. День для блеска!",
    "♍ Дева":     "Время для организации, планирования и совершенствования.",
    "♎ Весы":     "Фокус на отношениях, гармонии и балансе.",
    "♏ Скорпион": "День трансформации и глубокого исследования.",
    "♐ Стрелец":  "Расширяй горизонты, ищи новые возможности.",
    "♑ Козерог":  "Время серьёзной работы и ответственности.",
    "♒ Водолей":  "День для инноваций и новых идей.",
    "♓ Рыбы":    "Погрузись в творчество и интуицию.",
}


async def send_morning_notifications() -> int:
    """
    Отправить ежедневные утренние уведомления.
    Запускается каждый час; проверяет для каждого пользователя,
    совпадает ли его push_time с текущим временем (±5 мин).

    Returns:
        Количество отправленных уведомлений
    """
    sent = 0
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.push_enabled == True, User.data_complete == True)
            )
            users = result.scalars().all()

        transits = get_current_transits()
        moon_sign = transits.get("moon", {}).get("sign", "🌙")
        day_advice = DAY_ADVICES.get(moon_sign, "Звёзды с тобой!")

        bot = _get_bot()
        for user in users:
            try:
                if not _is_push_time(user.timezone, user.push_time or "08:00"):
                    continue
                text = PUSH_MORNING.format(
                    name=user.name,
                    moon_sign=moon_sign,
                    day_advice=day_advice,
                )
                await bot.send_message(chat_id=user.id, text=text)
                sent += 1
                logger.debug(f"Morning push sent to {user.id}")
            except Exception as e:
                logger.warning(f"Failed to send morning push to {user.id}: {e}")

        logger.info(f"Morning notifications sent: {sent}/{len(users)}")
    except Exception as e:
        logger.error(f"send_morning_notifications error: {e}")
    return sent


async def send_weekly_forecast_notifications() -> int:
    """
    Отправить еженедельные напоминания (по понедельникам в 9:00).

    Returns:
        Количество отправленных уведомлений
    """
    sent = 0
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.push_enabled == True, User.data_complete == True)
            )
            users = result.scalars().all()

        bot = _get_bot()
        for user in users:
            try:
                if not _is_push_time(user.timezone, "09:00"):
                    continue
                text = PUSH_WEEKLY_FORECAST.format(name=user.name)
                await bot.send_message(chat_id=user.id, text=text)
                sent += 1
                logger.debug(f"Weekly push sent to {user.id}")
            except Exception as e:
                logger.warning(f"Failed to send weekly push to {user.id}: {e}")

        logger.info(f"Weekly notifications sent: {sent}/{len(users)}")
    except Exception as e:
        logger.error(f"send_weekly_forecast_notifications error: {e}")
    return sent


def _is_push_time(user_timezone: str, push_time: str) -> bool:
    """True если текущее время в часовом поясе пользователя совпадает с push_time (±5 мин)."""
    try:
        tz = ZoneInfo(user_timezone)
        now = datetime.now(tz=tz)
        push_hour, push_minute = map(int, push_time.split(":"))
        target = now.replace(hour=push_hour, minute=push_minute, second=0, microsecond=0)
        return abs((now - target).total_seconds()) < 300
    except Exception as e:
        logger.error(f"_is_push_time error for tz={user_timezone}: {e}")
        return False
