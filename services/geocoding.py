"""
services/geocoding.py — геокодирование (название города → координаты + таймзона)
Использует geopy (Nominatim) и timezonefinder
"""

import logging
from typing import Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)

# Инициализируем геокодер и поиск таймзон один раз
_geolocator = Nominatim(user_agent="celeste_astro_bot")
_tf = TimezoneFinder()


async def get_location_data(place_name: str) -> Optional[dict]:
    """
    Геокодировать название города/места в координаты и таймзону.

    Args:
        place_name: название места (например, "Москва", "New York", "Paris, France")

    Returns:
        Словарь вида:
            {
                "place":     "Москва, Россия",  # нормализованное название
                "latitude":  55.7558,
                "longitude": 37.6173,
                "timezone":  "Europe/Moscow",
            }
        или None, если место не найдено.
    """
    try:
        # geopy — синхронная библиотека, запускаем в executor чтобы не блокировать loop
        import asyncio
        loop = asyncio.get_event_loop()

        location = await loop.run_in_executor(
            None,
            lambda: _geolocator.geocode(place_name, language="ru", timeout=10)
        )

        if location is None:
            logger.warning(f"Geocoding: место не найдено — '{place_name}'")
            return None

        lat = location.latitude
        lng = location.longitude

        # Определяем таймзону по координатам
        timezone = _tf.timezone_at(lat=lat, lng=lng)
        if timezone is None:
            # Запасной вариант: UTC
            timezone = "UTC"
            logger.warning(f"Timezone not found for {lat},{lng}, using UTC")

        result = {
            "place":     location.address,
            "latitude":  lat,
            "longitude": lng,
            "timezone":  timezone,
        }

        logger.info(f"Geocoded '{place_name}' → {lat:.4f}, {lng:.4f} ({timezone})")
        return result

    except GeocoderTimedOut:
        logger.error(f"Geocoding timeout for '{place_name}'")
        return None
    except GeocoderUnavailable as e:
        logger.error(f"Geocoder unavailable: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected geocoding error for '{place_name}': {e}")
        return None
