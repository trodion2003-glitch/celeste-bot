"""
services/astrology.py — расчёт натальной карты и текущих транзитов
Использует kerykeion (обёртка над Swiss Ephemeris / pyswisseph)
"""

import logging
from datetime import date, time, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from kerykeion import AstrologicalSubject
from kerykeion.aspects import NatalAspects

from config import ZODIAC_SIGNS_RU

logger = logging.getLogger(__name__)

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def _sign_ru(sign_name: str) -> str:
    """
    Перевести английское название знака зодиака в русское.
    kerykeion возвращает полные имена ('Aries', 'Taurus' …), поэтому
    пробуем сопоставить и через трёхбуквенный код, и по первым 3 буквам.
    """
    # Карта полных английских имён → русских (с символами)
    full_map = {
        "Aries":       "♈ Овен",
        "Taurus":      "♉ Телец",
        "Gemini":      "♊ Близнецы",
        "Cancer":      "♋ Рак",
        "Leo":         "♌ Лев",
        "Virgo":       "♍ Дева",
        "Libra":       "♎ Весы",
        "Scorpio":     "♏ Скорпион",
        "Sagittarius": "♐ Стрелец",
        "Capricorn":   "♑ Козерог",
        "Aquarius":    "♒ Водолей",
        "Pisces":      "♓ Рыбы",
    }
    if sign_name in full_map:
        return full_map[sign_name]
    # Запасной вариант — 3-буквенный код из config.py
    key = sign_name[:3].capitalize()
    return ZODIAC_SIGNS_RU.get(key, sign_name)


def _planet_dict(planet) -> dict:
    """Преобразовать объект планеты kerykeion в простой словарь."""
    return {
        "sign":   _sign_ru(planet.sign),
        "degree": round(planet.position, 2),
        "house":  getattr(planet, "house", None),
    }


# ============================================================================
# НАТАЛЬНАЯ КАРТА
# ============================================================================

def build_natal_chart(
    name: str,
    birth_date: date,
    birth_time: Optional[time],
    lat: float,
    lng: float,
    tz: str,
) -> dict:
    """
    Рассчитать натальную карту.

    Args:
        name:        имя пользователя (произвольная строка)
        birth_date:  дата рождения
        birth_time:  время рождения (None → полдень 12:00)
        lat:         широта места рождения
        lng:         долгота места рождения
        tz:          IANA-таймзона (например, "Europe/Moscow")

    Returns:
        Словарь с планетами и асцендентом:
        {
            "sun":     {"sign": "♌ Лев",   "degree": 15.42, "house": 1},
            "moon":    {...},
            "mercury": {...},
            ...
            "rising":  {"sign": "♎ Весы"}   # только если есть время
        }
    """
    if birth_time is None:
        hour, minute = 12, 0
        has_time = False
    else:
        hour, minute = birth_time.hour, birth_time.minute
        has_time = True

    try:
        subject = AstrologicalSubject(
            name=name,
            year=birth_date.year,
            month=birth_date.month,
            day=birth_date.day,
            hour=hour,
            minute=minute,
            lat=lat,
            lng=lng,
            tz_str=tz,
            zodiac_type="Tropic",   # западная астрология
            online=False,            # не обращаться к сети
        )

        natal = {
            "sun":     _planet_dict(subject.sun),
            "moon":    _planet_dict(subject.moon),
            "mercury": _planet_dict(subject.mercury),
            "venus":   _planet_dict(subject.venus),
            "mars":    _planet_dict(subject.mars),
            "jupiter": _planet_dict(subject.jupiter),
            "saturn":  _planet_dict(subject.saturn),
            "uranus":  _planet_dict(subject.uranus),
            "neptune": _planet_dict(subject.neptune),
            "pluto":   _planet_dict(subject.pluto),
        }

        # Асцендент — только если знаем точное время
        if has_time:
            natal["rising"] = {
                "sign":   _sign_ru(subject.first_house.sign),
                "degree": round(subject.first_house.position, 2),
            }
        else:
            natal["rising"] = {}

        logger.debug(f"Natal chart built for '{name}': Sun in {natal['sun']['sign']}")
        return natal

    except Exception as e:
        logger.error(f"Error building natal chart for '{name}': {e}")
        raise


# ============================================================================
# ТЕКУЩИЕ ТРАНЗИТЫ
# ============================================================================

def get_current_transits() -> dict:
    """
    Получить текущее положение планет (транзиты).
    Используется для сравнения с натальной картой при генерации прогноза.

    Returns:
        Словарь вида: {"sun": {"sign": "♋ Рак", "degree": 5.3}, ...}
    """
    try:
        now = datetime.utcnow()

        transits_subject = AstrologicalSubject(
            name="Transits",
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute,
            lat=0.0,    # экватор/гринвич — для транзитов координаты не важны
            lng=0.0,
            tz_str="UTC",
            zodiac_type="Tropic",
            online=False,
        )

        transits = {
            "sun":     _planet_dict(transits_subject.sun),
            "moon":    _planet_dict(transits_subject.moon),
            "mercury": _planet_dict(transits_subject.mercury),
            "venus":   _planet_dict(transits_subject.venus),
            "mars":    _planet_dict(transits_subject.mars),
            "jupiter": _planet_dict(transits_subject.jupiter),
            "saturn":  _planet_dict(transits_subject.saturn),
            "uranus":  _planet_dict(transits_subject.uranus),
            "neptune": _planet_dict(transits_subject.neptune),
            "pluto":   _planet_dict(transits_subject.pluto),
        }

        logger.debug(f"Transits calculated: Sun in {transits['sun']['sign']}")
        return transits

    except Exception as e:
        logger.error(f"Error calculating transits: {e}")
        raise


# ============================================================================
# РАСЧЁТ АСПЕКТОВ
# ============================================================================

def calculate_aspects(transits: dict, natal: dict = None) -> list:
    """
    Рассчитать аспекты между транзитными планетами.
    Ищет углы 0°, 60°, 90°, 120°, 180° (±8° орб).

    Returns:
        Список: [{"planet1": "☀️ Солнце", "planet2": "🌙 Луна", "type": "Трин", "angle": 120}, ...]
    """
    aspect_types = {
        0:   ("Соединение", 8),
        60:  ("Секстиль",   6),
        90:  ("Квадратура", 8),
        120: ("Трин",       8),
        180: ("Оппозиция",  8),
    }

    main_planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
    planets_list = [p for p in main_planets if p in transits and transits[p]]

    aspects = []
    for i, p1_key in enumerate(planets_list):
        for p2_key in planets_list[i + 1:]:
            deg1 = transits[p1_key]["degree"]
            deg2 = transits[p2_key]["degree"]
            diff = abs(deg1 - deg2)
            if diff > 180:
                diff = 360 - diff

            for target, (name, orb) in aspect_types.items():
                if abs(diff - target) <= orb:
                    aspects.append({
                        "planet1":     _get_planet_name_ru(p1_key),
                        "planet2":     _get_planet_name_ru(p2_key),
                        "type":        name,
                        "angle":       target,
                        "exact_angle": round(diff, 2),
                    })
                    break

    logger.info(f"Calculated {len(aspects)} aspects")
    return aspects


# ============================================================================
# ЛУНА — РАСЧЁТЫ ДЛЯ КАЛЕНДАРЯ
# ============================================================================

def get_moon_phase() -> str:
    """
    Определить текущую фазу луны через Swiss Ephemeris.

    Returns:
        "Новолуние", "Растущая луна", "Полнолуние" или "Убывающая луна"
    """
    known_new_moon = datetime(2000, 1, 6)
    lunar_month = 29.530588861
    days_since = (datetime.utcnow() - known_new_moon).total_seconds() / 86400.0
    lunar_day = days_since % lunar_month

    if lunar_day < 1.84 or lunar_day >= 27.69:
        return "Новолуние"
    elif lunar_day < 13.77:
        return "Растущая луна"
    elif lunar_day < 15.61:
        return "Полнолуние"
    else:
        return "Убывающая луна"


def get_moon_for_date(target_date) -> str:
    """
    Получить знак луны для конкретной даты (kerykeion, полдень UTC).

    Args:
        target_date: объект datetime.date

    Returns:
        Знак луны (например, "♌ Лев")
    """
    try:
        subject = AstrologicalSubject(
            name="Moon",
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            hour=12,
            minute=0,
            lat=0.0,
            lng=0.0,
            tz_str="UTC",
            zodiac_type="Tropic",
            online=False,
        )
        return _sign_ru(subject.moon.sign)
    except Exception as e:
        logger.warning(f"Error calculating moon for {target_date}: {e}")
        return "Неизвестно"


def _get_planet_name_ru(planet_key: str) -> str:
    names = {
        "sun":     "☀️ Солнце",
        "moon":    "🌙 Луна",
        "mercury": "☿️ Меркурий",
        "venus":   "♀️ Венера",
        "mars":    "♂️ Марс",
        "jupiter": "♃ Юпитер",
        "saturn":  "♄ Сатурн",
        "uranus":  "♅ Уран",
        "neptune": "♆ Нептун",
        "pluto":   "♇ Плутон",
    }
    return names.get(planet_key, planet_key)
