"""
models/user.py — модель пользователя
"""

from sqlalchemy import (
    Column, BigInteger, String, Date, Time, Float, DateTime,
    Integer, Boolean, Index, func
)
from sqlalchemy.dialects.postgresql import JSON
from models.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    # ======================================================================
    # Основные данные
    # ======================================================================
    id = Column(BigInteger, primary_key=True)  # telegram_id
    name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=True, unique=True)  # @username в Telegram

    # ======================================================================
    # Данные для натальной карты
    # ======================================================================
    birth_date = Column(Date, nullable=False, index=True)
    birth_time = Column(Time, nullable=True)  # NULL = неизвестно время
    birth_place = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timezone = Column(String(50), nullable=False, default="Europe/Moscow")

    # ======================================================================
    # Вычисленные знаки (кэш для быстрого доступа)
    # ======================================================================
    sun_sign = Column(String(20), nullable=True)  # "Овен", "Телец", ...
    moon_sign = Column(String(20), nullable=True)
    rising_sign = Column(String(20), nullable=True)  # Асцендент (может быть NULL если не знаем время)

    # ======================================================================
    # Полная натальная карта (как JSON для полноты)
    # ======================================================================
    natal_chart = Column(JSON, nullable=True)  # {sun: {...}, moon: {...}, ...}

    # ======================================================================
    # Статистика использования
    # ======================================================================
    streak_days = Column(Integer, default=0)  # Сколько дней подряд заходил
    last_active = Column(DateTime(timezone=True), nullable=True)  # Последний визит
    total_visits = Column(Integer, default=1)  # Всего визитов

    # ======================================================================
    # Premium подписка
    # ======================================================================
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime(timezone=True), nullable=True)  # Когда закончится

    # ======================================================================
    # Реферальная система
    # ======================================================================
    referral_code = Column(String(10), unique=True, index=True)  # Уникальный код
    referred_by = Column(BigInteger, nullable=True, index=True)  # Кто пригласил
    referral_count = Column(Integer, default=0)  # Сколько человек пригласил

    # ======================================================================
    # Метаданные
    # ======================================================================
    language = Column(String(10), default="ru")  # Язык интерфейса
    timezone_aware = Column(Boolean, default=True)  # Знает ли время рождения?
    data_complete = Column(Boolean, default=False)  # Все ли данные заполнены?

    # ======================================================================
    # Уведомления
    # ======================================================================
    push_enabled = Column(Boolean, default=True)  # Получать ли push-уведомления?
    push_time = Column(String(5), default="09:00")  # Время утреннего push (HH:MM)

    # ======================================================================
    # Сервис
    # ======================================================================
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ======================================================================
    # Индексы для быстрого поиска
    # ======================================================================
    __table_args__ = (
        Index("idx_user_created", "created_at"),
        Index("idx_user_referral", "referral_code"),
        Index("idx_user_referred_by", "referred_by"),
    )

    # ======================================================================
    # Методы
    # ======================================================================
    def __repr__(self):
        return f"<User id={self.id} name='{self.name}' sign='{self.sun_sign}'>"

    @property
    def full_name_with_sign(self):
        """Имя и знак для красивого вывода"""
        return f"{self.name} ({self.sun_sign})" if self.sun_sign else self.name

    @property
    def is_premium_active(self):
        """Активна ли premium подписка сейчас?"""
        if not self.is_premium or not self.premium_until:
            return False
        return self.premium_until > datetime.utcnow()

    def has_complete_birth_data(self) -> bool:
        """Есть ли всё необходимое для натальной карты?"""
        return bool(
            self.birth_date
            and self.birth_time  # ВАЖНО: время обязательно для Асцендента
            and self.birth_place
            and self.latitude
            and self.longitude
        )

    def has_approximate_birth_data(self) -> bool:
        """Есть ли хотя бы дата и место (без времени)?"""
        return bool(
            self.birth_date
            and self.birth_place
            and self.latitude
            and self.longitude
        )
