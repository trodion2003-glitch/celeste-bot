"""
services/forecast.py — генерация астрологического прогноза через DeepSeek API
"""

import logging
from datetime import datetime, timedelta

from openai import AsyncOpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_MAX_TOKENS
from services.astrology import get_current_transits

logger = logging.getLogger(__name__)

# Клиент DeepSeek (ленивая инициализация)
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
    return _client


# ============================================================================
# СИСТЕМНЫЙ ПРОМПТ
# ============================================================================

SYSTEM_PROMPT = """Ты — Celesté, нежный и мудрый астрологический ассистент.
Ты пишешь персональные недельные прогнозы на русском языке.

Стиль:
• Тёплый, поэтичный, вдохновляющий — как письмо от мудрого друга
• Конкретные практические советы, не общие фразы
• Используй астрологические символы (☀️🌙✨) умеренно, без перегрузки
• Длина: 250–350 слов
• Структура:
  — Краткое астрологическое введение (1–2 предложения)
  — Энергия недели (2–3 предложения)
  — Отношения и общение
  — Работа и финансы
  — Здоровье и энергия
  — Слово недели (одно вдохновляющее слово + пояснение)

Не упоминай названия планет как "транзит X квадратура Y" — говори образно и понятно."""


# ============================================================================
# ГЕНЕРАЦИЯ ПРОГНОЗА
# ============================================================================

async def generate_weekly_forecast(name: str, natal: dict, user_id: int) -> str:
    """
    Сгенерировать персональный недельный прогноз через DeepSeek.

    Args:
        name:    имя пользователя
        natal:   натальная карта (dict из build_natal_chart)
        user_id: ID пользователя (для логирования)

    Returns:
        Текст прогноза (Markdown)
    """
    try:
        transits = get_current_transits()
    except Exception as e:
        logger.warning(f"Could not get transits: {e}, using empty transits")
        transits = {}

    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    natal_summary = _format_natal_for_prompt(natal)
    transits_summary = _format_transits_for_prompt(transits)

    user_prompt = (
        f"Имя: {name}\n\n"
        f"Натальная карта:\n{natal_summary}\n\n"
        f"Текущие транзиты (положение планет сейчас):\n{transits_summary}\n\n"
        f"Напиши персональный прогноз на неделю "
        f"{week_start.strftime('%d.%m')}–{week_end.strftime('%d.%m.%Y')}."
    )

    client = _get_client()

    try:
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            max_tokens=DEEPSEEK_MAX_TOKENS,
            temperature=0.85,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
        )
        forecast_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        logger.info(f"Forecast generated for user {user_id}, tokens: {tokens_used}")
        return forecast_text

    except Exception as e:
        logger.error(f"DeepSeek API error for user {user_id}: {e}")
        raise


# ============================================================================
# ФОРМАТИРОВАНИЕ ДЛЯ ПРОМПТА
# ============================================================================

def _format_natal_for_prompt(natal: dict) -> str:
    lines = []
    planet_labels = {
        "sun":     "Солнце",
        "moon":    "Луна",
        "mercury": "Меркурий",
        "venus":   "Венера",
        "mars":    "Марс",
        "jupiter": "Юпитер",
        "saturn":  "Сатурн",
        "uranus":  "Уран",
        "neptune": "Нептун",
        "pluto":   "Плутон",
    }
    for key, label in planet_labels.items():
        if key in natal:
            p = natal[key]
            house = f", дом {p['house']}" if p.get("house") else ""
            lines.append(f"  {label}: {p['sign']} {p['degree']}°{house}")

    if natal.get("rising", {}).get("sign"):
        lines.append(f"  Асцендент: {natal['rising']['sign']}")

    return "\n".join(lines)


def _format_transits_for_prompt(transits: dict) -> str:
    if not transits:
        return "  (данные транзитов недоступны)"

    lines = []
    planet_labels = {
        "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий",
        "venus": "Венера", "mars": "Марс", "jupiter": "Юпитер",
        "saturn": "Сатурн",
    }
    for key, label in planet_labels.items():
        if key in transits:
            p = transits[key]
            lines.append(f"  {label}: {p['sign']} {p['degree']}°")

    return "\n".join(lines)
