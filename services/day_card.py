"""
services/day_card.py — генерация карты дня (Card of the Day)
"""

import logging
from datetime import datetime

from openai import AsyncOpenAI

from config import DEEPSEEK_API_KEY

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
    return _client


SYSTEM_PROMPT = """Ты — Celesté, астрологический ассистент для женщин.
Создаёшь красивые карты дня на русском языке.

Структура карты дня:
- Луна (знак, фаза, энергия)
- Основные аспекты дня (максимум 3-5)
- Совет на день
- Слово дня (одно вдохновляющее слово)

Стиль:
- Тёплый, вдохновляющий
- Практические советы
- Длина: 150-200 слов
- Используй символы (🌙☽⚡♀️♂️)

Говори кратко и ясно."""


async def generate_day_card(name: str, natal: dict, transits: dict, aspects: list) -> str:
    """
    Генерировать карту дня через DeepSeek.

    Args:
        name:     имя пользователя
        natal:    натальная карта
        transits: текущие планеты
        aspects:  список аспектов между планетами

    Returns:
        Текст карты дня
    """
    transits_text = _format_transits(transits)
    aspects_text = _format_aspects(aspects)

    today = datetime.now().date()

    user_message = (
        f"Имя: {name}\n\n"
        f"Натальное Солнце: {natal.get('sun', {}).get('sign', 'неизвестно')}\n"
        f"Натальная Луна: {natal.get('moon', {}).get('sign', 'неизвестно')}\n\n"
        f"Сегодня ({today.strftime('%d.%m.%Y')}):\n"
        f"{transits_text}\n\n"
        f"Аспекты дня:\n{aspects_text}\n\n"
        f"Создай красивую карту дня для {name}."
    )

    client = _get_client()

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=600,
        )
        day_card = response.choices[0].message.content
        logger.info(f"Day card generated for {name}, tokens: {response.usage.total_tokens}")
        return day_card

    except Exception as e:
        logger.error(f"DeepSeek error generating day card: {e}")
        raise


def _format_transits(transits: dict) -> str:
    if not transits:
        return "Данные недоступны"
    lines = [
        f"🌙 Луна в {transits.get('moon', {}).get('sign', '?')}",
        f"☀️ Солнце в {transits.get('sun', {}).get('sign', '?')}",
        f"♀️ Венера в {transits.get('venus', {}).get('sign', '?')}",
        f"♂️ Марс в {transits.get('mars', {}).get('sign', '?')}",
    ]
    return "\n".join(lines)


def _format_aspects(aspects: list) -> str:
    if not aspects:
        return "Нет значимых аспектов"
    lines = [
        f"  • {a['planet1']} {a['type']} {a['planet2']}"
        for a in aspects[:5]
    ]
    return "\n".join(lines)
