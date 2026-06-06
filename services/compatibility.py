"""
services/compatibility.py — анализ совместимости (синастрия) двух натальных карт
"""

import logging
from typing import Tuple, Dict, List

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


ASPECT_WEIGHTS = {
    "Соединение": 10,
    "Трин":        8,
    "Секстиль":    7,
    "Квадратура": -5,
    "Оппозиция":  -3,
}

PLANET_IMPORTANCE = {
    "☀️ Солнце":    3,
    "🌙 Луна":      3,
    "♀️ Венера":    2,
    "♂️ Марс":      2,
    "☿️ Меркурий":  1,
    "♃ Юпитер":    1,
    "♄ Сатурн":    1,
}

SYSTEM_PROMPT = """Ты — Celesté, астрологический ассистент.
Создаёшь красивые анализы совместимости на русском языке.

Структура:
- Краткое сравнение карт
- Основные аспекты между ними
- Анализ совместимости (гармония и напряжение)
- Советы для отношений

Стиль:
- Честный и конструктивный
- Практические рекомендации
- Деликатно говори о напряжении
- Подчеркивай сильные стороны
- Длина: 300-400 слов"""


async def generate_compatibility_analysis(
    name1: str,
    natal1: dict,
    name2: str,
    natal2: dict,
) -> Tuple[str, int]:
    """
    Сгенерировать анализ совместимости двух людей через DeepSeek.

    Returns:
        (текст анализа, процент совместимости)
    """
    synastry = calculate_synastry(natal1, natal2)
    score = calculate_compatibility_score(synastry)

    cards_text = _format_cards(name1, natal1, name2, natal2)
    aspects_text = _format_aspects(synastry)

    user_message = (
        f"Анализируй совместимость:\n\n"
        f"{cards_text}\n\n"
        f"Аспекты между картами:\n{aspects_text}\n\n"
        f"Совместимость: {score}%\n\n"
        f"Напиши глубокий анализ совместимости {name1} и {name2}, учитывая все аспекты."
    )

    client = _get_client()

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        analysis = response.choices[0].message.content
        logger.info(f"Compatibility generated: {name1} & {name2}, score={score}%, tokens={response.usage.total_tokens}")
        return analysis, score

    except Exception as e:
        logger.error(f"DeepSeek error in compatibility: {e}")
        raise


def calculate_synastry(natal1: dict, natal2: dict) -> List[Dict]:
    """Рассчитать аспекты между двумя натальными картами (синастрия)."""
    aspect_types = {
        0:   ("Соединение", 8),
        60:  ("Секстиль",   6),
        90:  ("Квадратура", 8),
        120: ("Трин",       8),
        180: ("Оппозиция",  8),
    }
    main_planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
    aspects = []

    for p1_key in main_planets:
        if p1_key not in natal1 or not natal1[p1_key]:
            continue
        for p2_key in main_planets:
            if p2_key not in natal2 or not natal2[p2_key]:
                continue

            deg1 = natal1[p1_key]["degree"]
            deg2 = natal2[p2_key]["degree"]
            diff = abs(deg1 - deg2)
            if diff > 180:
                diff = 360 - diff

            for target, (name, orb) in aspect_types.items():
                if abs(diff - target) <= orb:
                    aspects.append({
                        "planet1":     _planet_ru(p1_key),
                        "planet2":     _planet_ru(p2_key),
                        "type":        name,
                        "angle":       target,
                        "exact_angle": round(diff, 2),
                    })
                    break

    logger.info(f"Synastry: {len(aspects)} aspects")
    return aspects


def calculate_compatibility_score(aspects: List[Dict]) -> int:
    """Рассчитать % совместимости на основе синастрических аспектов."""
    if not aspects:
        return 50

    total = 0.0
    for a in aspects:
        weight = ASPECT_WEIGHTS.get(a["type"], 0)
        imp = (PLANET_IMPORTANCE.get(a["planet1"], 1) + PLANET_IMPORTANCE.get(a["planet2"], 1)) / 2
        total += weight * imp

    score = 50 + (total / len(aspects))
    return max(0, min(100, int(score)))


def _format_cards(name1: str, natal1: dict, name2: str, natal2: dict) -> str:
    def _card(name, natal):
        lines = [
            f"{name}:",
            f"  ☀️ Солнце в {natal.get('sun', {}).get('sign', '?')}",
            f"  🌙 Луна в {natal.get('moon', {}).get('sign', '?')}",
        ]
        if natal.get("rising", {}).get("sign"):
            lines.append(f"  ↑ Асцендент {natal['rising']['sign']}")
        return "\n".join(lines)

    return _card(name1, natal1) + "\n\n" + _card(name2, natal2)


def _format_aspects(aspects: List[Dict]) -> str:
    if not aspects:
        return "  Нет значимых аспектов"
    return "\n".join(
        f"  • {a['planet1']} {a['type']} {a['planet2']} ({a['exact_angle']}°)"
        for a in aspects[:8]
    )


def _planet_ru(key: str) -> str:
    return {
        "sun":     "☀️ Солнце",
        "moon":    "🌙 Луна",
        "mercury": "☿️ Меркурий",
        "venus":   "♀️ Венера",
        "mars":    "♂️ Марс",
        "jupiter": "♃ Юпитер",
        "saturn":  "♄ Сатурн",
    }.get(key, key)
