"""
models/forecast.py — модель сохранённых прогнозов
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Date, DateTime, Float, Index, func
)
from sqlalchemy.dialects.postgresql import JSON
from models.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    # ======================================================================
    # Основные данные
    # ======================================================================
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # FK на users.id

    # ======================================================================
    # Период прогноза
    # ======================================================================
    forecast_type = Column(String(20), nullable=False)  # "weekly", "daily", "monthly"
    week_start = Column(Date, nullable=False, index=True)  # Начало недели (пн.)
    week_end = Column(Date, nullable=True)  # Конец недели (вс.)

    # ======================================================================
    # Содержание прогноза
    # ======================================================================
    # Структурированный прогноз (для парсинга и анализа)
    content = Column(JSON, nullable=True)
    # Например: {
    #   "relationships": "...",
    #   "money": "...",
    #   "energy": "...",
    #   "word_of_week": "..."
    # }

    # Полный текст от Claude (как он сгенерировал)
    raw_text = Column(String, nullable=False)

    # Количество использованных токенов (для учёта стоимости)
    tokens_used = Column(Integer, nullable=True)

    # ======================================================================
    # Мета
    # ======================================================================
    model_version = Column(String(50), default="claude-sonnet-4-5")  # Какая модель использовалась
    
    # Параметры генерации (для воспроизводимости)
    temperature = Column(Float, default=0.7)
    tone_style = Column(String(50), nullable=True)  # "нежный", "мотивирующий" и т.д.

    # ======================================================================
    # Служебные поля
    # ======================================================================
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Был ли этот прогноз отправлен пользователю?
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # ======================================================================
    # Индексы
    # ======================================================================
    __table_args__ = (
        Index("idx_forecast_user_date", "user_id", "week_start"),
        Index("idx_forecast_created", "created_at"),
    )

    # ======================================================================
    # Методы
    # ======================================================================
    def __repr__(self):
        return f"<Forecast user_id={self.user_id} week={self.week_start}>"

    @property
    def is_sent(self) -> bool:
        """Был ли отправлен пользователю?"""
        return self.sent_at is not None


class DayCard(Base):
    """Карта дня — быстрый снимок астроэнергии на конкретный день"""
    __tablename__ = "day_cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    card_date = Column(Date, nullable=False, index=True)

    # Содержание (структурированное)
    content = Column(JSON, nullable=True)
    raw_text = Column(String, nullable=False)

    # Какие главные аспекты этого дня?
    moon_sign = Column(String(20), nullable=True)
    moon_phase = Column(String(50), nullable=True)
    main_aspects = Column(JSON, nullable=True)  # [{planet: "...", type: "...", sign: "..."}]

    # Служба
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_daycard_user_date", "user_id", "card_date"),
    )
