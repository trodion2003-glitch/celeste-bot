"""
services/moon_calendar.py — генерация лунного календаря
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict

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


MOON_RECOMMENDATIONS = {
    "♈ Овен":      "Инициатива, мужество, новые начинания. Время действовать и не сомневаться.",
    "♉ Телец":     "Стабильность, материальность, чувственность. Хороший день для инвестиций и покупок.",
    "♊ Близнецы":  "Коммуникация, разговоры, информация. День для общения и обучения.",
    "♋ Рак":       "Эмоции, интуиция, дом и семья. Вслушивайтесь в свои чувства.",
    "♌ Лев":       "Творчество, выразительность, лидерство. День для самовыражения и праздника.",
    "♍ Дева":      "Анализ, работа, совершенствование. День для планирования и организации.",
    "♎ Весы":      "Отношения, гармония, баланс. Хороший день для переговоров и союзов.",
    "♏ Скорпион":  "Трансформация, глубина, страсть. День для исследования и перемен.",
    "♐ Стрелец":   "Оптимизм, путешествия, философия. День для расширения горизонтов.",
    "♑ Козерог":   "Ответственность, власть, структура. День для серьёзных дел.",
    "♒ Водолей":   "Инновация, свобода, дружба. День для новых идей и сообщества.",
    "♓ Рыбы":      "Интуиция, искусство, духовность. День для творчества и медитации.",
}

PHASE_MEANINGS = {
    "Новолуние":      "Начало нового цикла. Время для новых начинаний и установления намерений.",
    "Растущая луна":  "Луна нарастает. Энергия восходящая, время для действий, роста и притяжения.",
    "Полнолуние":     "Пик энергии. Время для завершения, осуществления и отпускания.",
    "Убывающая луна": "Луна убывает. Время для отпускания, очищения и внутренней работы.",
}

SYSTEM_PROMPT = """Ты — Celesté, астрологический ассистент.
Создаёшь красивые лунные календари на русском языке.

Структура:
- Текущая фаза луны (значение)
- Луна на ближайшие дни (7 дней)
- Рекомендации по дням
- Общий совет

Стиль:
- Практичный и вдохновляющий
- Кратко, но информативно
- Используй луну как метафору
- Длина: 250-350 слов"""


async def generate_moon_calendar(name: str, days: int = 7) -> str:
    """
    Генерировать лунный календарь на несколько дней через DeepSeek.

    Args:
        name: имя пользователя
        days: количество дней

    Returns:
        Текст календаря
    """
    from services.astrology import get_moon_for_date, get_moon_phase

    today = datetime.now().date()

    days_info: List[Dict] = []
    for i in range(days):
        d = today + timedelta(days=i)
        moon_sign = get_moon_for_date(d)
        days_info.append({
            "date":           d,
            "moon_sign":      moon_sign,
            "recommendation": MOON_RECOMMENDATIONS.get(moon_sign, ""),
        })

    current_phase = get_moon_phase()
    phase_meaning = PHASE_MEANINGS.get(current_phase, "")
    days_text = _format_days_for_prompt(days_info, today)

    user_message = (
        f"Имя: {name}\n\n"
        f"Текущая фаза луны: {current_phase}\n"
        f"Значение фазы: {phase_meaning}\n\n"
        f"Луна на ближайшие дни:\n{days_text}\n\n"
        f"Создай красивый лунный календарь для {name}. "
        f"Включи текущую фазу, луну на дни, рекомендации и совет."
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
            max_tokens=800,
        )
        calendar = response.choices[0].message.content
        logger.info(f"Moon calendar generated for {name}, tokens: {response.usage.total_tokens}")
        return calendar

    except Exception as e:
        logger.error(f"DeepSeek error generating moon calendar: {e}")
        raise


def _format_days_for_prompt(days_info: List[Dict], today) -> str:
    lines = []
    for info in days_info:
        d = info["date"]
        if d == today:
            label = "Сегодня"
        elif d == today + timedelta(days=1):
            label = "Завтра"
        elif d == today + timedelta(days=2):
            label = "Послезавтра"
        else:
            weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            label = weekdays[d.weekday()]
        lines.append(f"{label} ({d.strftime('%d.%m')}): {info['moon_sign']}")
    return "\n".join(lines)
