"""
services/user.py — операции с пользователями в БД
Создание/обновление пользователя, стрик посещений
"""

import logging
import random
import string
from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models.database import AsyncSessionLocal
from models.user import User

logger = logging.getLogger(__name__)


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def _generate_referral_code(length: int = 8) -> str:
    """Генерировать уникальный реферальный код из букв и цифр."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


# ============================================================================
# ОСНОВНЫЕ ОПЕРАЦИИ
# ============================================================================

async def create_or_update_user(
    telegram_id: int,
    username: Optional[str],
    name: str,
    birth_date: date,
    birth_time: Optional[time],
    birth_place: str,
    latitude: float,
    longitude: float,
    timezone: str,
    natal: dict,
) -> User:
    """
    Создать нового пользователя или обновить существующего.

    При обновлении перезаписываются все данные онбординга
    (пользователь мог пройти его повторно с новыми данными).

    Returns:
        Объект User (уже сохранённый в БД)
    """
    async with AsyncSessionLocal() as session:
        # Пробуем найти существующего пользователя
        result = await session.execute(select(User).where(User.id == telegram_id))
        user = result.scalar_one_or_none()

        if user is None:
            # Новый пользователь
            user = User(id=telegram_id)
            user.referral_code = _generate_referral_code()
            user.total_visits = 1
            user.streak_days = 1
            logger.info(f"Creating new user {telegram_id}")
        else:
            logger.info(f"Updating existing user {telegram_id}")

        # Обновляем все поля
        user.username = username
        user.name = name
        user.birth_date = birth_date
        user.birth_time = birth_time
        user.birth_place = birth_place
        user.latitude = latitude
        user.longitude = longitude
        user.timezone = timezone

        # Кэшируем знаки для быстрого доступа
        user.sun_sign = natal.get("sun", {}).get("sign")
        user.moon_sign = natal.get("moon", {}).get("sign")
        user.rising_sign = natal.get("rising", {}).get("sign")
        user.natal_chart = natal

        # Отмечаем данные как заполненные
        user.data_complete = True
        user.last_active = datetime.now(tz=ZoneInfo("UTC"))

        try:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"User {telegram_id} saved successfully")
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"IntegrityError saving user {telegram_id}: {e}")
            raise

        return user


async def update_streak(user_id: int) -> int:
    """
    Обновить стрик (счётчик дней подряд).

    Логика:
    - Если последний визит был вчера → стрик +1
    - Если последний визит сегодня → стрик не меняется
    - Если пропустил день(и) → стрик сбрасывается до 1

    Returns:
        Текущее значение стрика
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            logger.warning(f"update_streak: user {user_id} not found")
            return 0

        today = datetime.now(tz=ZoneInfo("UTC")).date()

        if user.last_active is not None:
            last_date = user.last_active.date()

            if last_date == today:
                # Уже заходил сегодня — ничего не меняем
                return user.streak_days or 1

            elif last_date == today - timedelta(days=1):
                # Вчера заходил — продолжаем стрик
                user.streak_days = (user.streak_days or 0) + 1
            else:
                # Пропустил — сбрасываем
                user.streak_days = 1
        else:
            user.streak_days = 1

        user.last_active = datetime.now(tz=ZoneInfo("UTC"))
        user.total_visits = (user.total_visits or 0) + 1

        await session.commit()
        logger.debug(f"User {user_id} streak: {user.streak_days}")
        return user.streak_days


async def get_user(user_id: int) -> Optional[User]:
    """
    Получить пользователя по telegram_id.

    Returns:
        User или None если не найден
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def update_push_settings(user_id: int, enabled: bool, push_time: Optional[str] = None) -> None:
    """Обновить настройки push-уведомлений пользователя."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.push_enabled = enabled
            if push_time is not None:
                user.push_time = push_time
            await session.commit()
            logger.debug(f"Push settings updated for {user_id}: enabled={enabled}")


async def get_user_by_referral(referral_code: str) -> Optional[User]:
    """Найти пользователя по реферальному коду."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.referral_code == referral_code)
        )
        return result.scalar_one_or_none()
