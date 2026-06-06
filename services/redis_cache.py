"""
services/redis_cache.py — помощник для работы с Redis кэшем
Используется для кэширования прогнозов, натальных карт, транзитов
"""

import redis.asyncio as redis
import json
import logging
from typing import Any, Optional
from config import REDIS_URL, CACHE_TTL_FORECAST, CACHE_TTL_CHART

logger = logging.getLogger(__name__)

# Глобальный инстанс Redis (ленивая инициализация)
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """
    Получить Redis клиент (синглтон).
    Инициализируется при первом использовании.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
        logger.info("✓ Redis connected")
    return _redis_client


async def close_redis():
    """Закрыть Redis соединение (вызвать при выходе)"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("✓ Redis closed")


# ============================================================================
# КЭШИРОВАНИЕ ПРОГНОЗОВ
# ============================================================================

async def cache_forecast(user_id: int, week_start: str, forecast_text: str, ttl: int = CACHE_TTL_FORECAST):
    """
    Сохранить прогноз в кэш.
    
    Args:
        user_id: ID пользователя
        week_start: начало недели (YYYY-MM-DD)
        forecast_text: текст прогноза
        ttl: время жизни в секундах
    """
    redis_client = await get_redis()
    key = f"forecast:{user_id}:{week_start}"
    
    try:
        await redis_client.setex(key, ttl, forecast_text)
        logger.debug(f"Cached forecast for user {user_id}")
    except Exception as e:
        logger.error(f"Redis cache error: {e}")


async def get_cached_forecast(user_id: int, week_start: str) -> Optional[str]:
    """
    Получить прогноз из кэша.
    
    Returns:
        Текст прогноза или None, если не найден или истёк
    """
    redis_client = await get_redis()
    key = f"forecast:{user_id}:{week_start}"
    
    try:
        value = await redis_client.get(key)
        if value:
            logger.debug(f"Cache hit for forecast {user_id}:{week_start}")
            return value
    except Exception as e:
        logger.error(f"Redis get error: {e}")
    
    return None


async def invalidate_forecast_cache(user_id: int, week_start: str = None):
    """
    Очистить кэш прогноза для пользователя.
    
    Args:
        user_id: ID пользователя
        week_start: конкретная неделя (если None, очищает все)
    """
    redis_client = await get_redis()
    
    try:
        if week_start:
            key = f"forecast:{user_id}:{week_start}"
            await redis_client.delete(key)
            logger.debug(f"Invalidated forecast for {user_id}:{week_start}")
        else:
            # Очищаем все прогнозы пользователя
            pattern = f"forecast:{user_id}:*"
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)
                logger.debug(f"Invalidated all forecasts for {user_id}")
    except Exception as e:
        logger.error(f"Redis delete error: {e}")


# ============================================================================
# КЭШИРОВАНИЕ НАТАЛЬНЫХ КАРТ
# ============================================================================

async def cache_natal_chart(user_id: int, chart_data: dict, ttl: int = CACHE_TTL_CHART):
    """
    Сохранить натальную карту в кэш (редко меняется).
    """
    redis_client = await get_redis()
    key = f"chart:{user_id}"
    
    try:
        await redis_client.setex(key, ttl, json.dumps(chart_data))
        logger.debug(f"Cached natal chart for user {user_id}")
    except Exception as e:
        logger.error(f"Redis cache chart error: {e}")


async def get_cached_natal_chart(user_id: int) -> Optional[dict]:
    """
    Получить натальную карту из кэша.
    """
    redis_client = await get_redis()
    key = f"chart:{user_id}"
    
    try:
        value = await redis_client.get(key)
        if value:
            logger.debug(f"Cache hit for chart {user_id}")
            return json.loads(value)
    except Exception as e:
        logger.error(f"Redis get chart error: {e}")
    
    return None


# ============================================================================
# КЭШИРОВАНИЕ ТРАНЗИТОВ (часто используется)
# ============================================================================

CACHE_TTL_TRANSITS = 6 * 3600  # 6 часов

async def cache_current_transits(transits_data: dict, ttl: int = CACHE_TTL_TRANSITS):
    """
    Сохранить текущее положение планет (актуально для всех пользователей).
    """
    redis_client = await get_redis()
    key = "transits:current"
    
    try:
        await redis_client.setex(key, ttl, json.dumps(transits_data))
        logger.debug("Cached current transits")
    except Exception as e:
        logger.error(f"Redis cache transits error: {e}")


async def get_cached_current_transits() -> Optional[dict]:
    """
    Получить кэшированное положение планет.
    """
    redis_client = await get_redis()
    key = "transits:current"
    
    try:
        value = await redis_client.get(key)
        if value:
            logger.debug("Cache hit for transits")
            return json.loads(value)
    except Exception as e:
        logger.error(f"Redis get transits error: {e}")
    
    return None


# ============================================================================
# СЧЁТЧИКИ И ФЛАГИ (для rate-limiting, уникальности и т.д.)
# ============================================================================

async def increment_counter(key: str, ttl: int = 3600) -> int:
    """
    Увеличить счётчик на 1.
    Используется для rate-limiting (сколько раз генерировал прогноз в день).
    """
    redis_client = await get_redis()
    
    try:
        count = await redis_client.incr(key)
        if count == 1:  # Первый раз увеличили
            await redis_client.expire(key, ttl)
        return count
    except Exception as e:
        logger.error(f"Redis counter error: {e}")
        return 0


async def get_counter(key: str) -> int:
    """
    Получить значение счётчика.
    """
    redis_client = await get_redis()
    
    try:
        value = await redis_client.get(key)
        return int(value) if value else 0
    except Exception as e:
        logger.error(f"Redis get counter error: {e}")
        return 0


async def set_flag(key: str, value: bool, ttl: int = 3600):
    """
    Установить флаг (например, "уже генерировал прогноз сегодня").
    """
    redis_client = await get_redis()
    
    try:
        await redis_client.setex(key, ttl, "1" if value else "0")
    except Exception as e:
        logger.error(f"Redis set flag error: {e}")


async def get_flag(key: str) -> bool:
    """
    Получить флаг.
    """
    redis_client = await get_redis()
    
    try:
        value = await redis_client.get(key)
        return value == "1"
    except Exception as e:
        logger.error(f"Redis get flag error: {e}")
        return False


# ============================================================================
# УТИЛИТЫ
# ============================================================================

async def clear_all_cache():
    """
    ОСТОРОЖНО! Полностью очистить Redis.
    Используется только для отладки.
    """
    redis_client = await get_redis()
    
    try:
        await redis_client.flushdb()
        logger.warning("⚠️  Redis cache completely cleared!")
    except Exception as e:
        logger.error(f"Redis flush error: {e}")


async def get_redis_stats() -> dict:
    """
    Получить статистику Redis (для мониторинга).
    """
    redis_client = await get_redis()
    
    try:
        info = await redis_client.info()
        return {
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "total_commands_processed": info.get("total_commands_processed"),
        }
    except Exception as e:
        logger.error(f"Redis stats error: {e}")
        return {}
