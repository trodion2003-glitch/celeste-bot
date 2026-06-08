"""
services/analytics.py — отслеживание аналитики и событий
"""

import logging
from datetime import datetime, date
from typing import Optional

from services.redis_cache import get_redis

logger = logging.getLogger(__name__)


async def track_command(user_id: int, command: str) -> None:
    try:
        redis = await get_redis()
        today = date.today().isoformat()

        key_command = f"analytics:command:{command}:{today}"
        await redis.incr(key_command)
        await redis.expire(key_command, 86400)

        key_total = f"analytics:total_commands:{today}"
        await redis.incr(key_total)
        await redis.expire(key_total, 86400)

        key_users = f"analytics:unique_users:{today}"
        await redis.sadd(key_users, user_id)
        await redis.expire(key_users, 86400)

        logger.debug(f"Tracked command: {command} by user {user_id}")

    except Exception as e:
        logger.error(f"Error tracking command: {e}")


async def track_premium_purchase(user_id: int) -> None:
    try:
        redis = await get_redis()
        today = date.today().isoformat()

        key = f"analytics:premium_purchases:{today}"
        await redis.incr(key)
        await redis.expire(key, 86400)

        await redis.incr("analytics:total_premium_purchases")

        logger.info(f"Premium purchased by user {user_id}")

    except Exception as e:
        logger.error(f"Error tracking premium purchase: {e}")


async def get_analytics_today() -> dict:
    try:
        redis = await get_redis()
        today = date.today().isoformat()

        total_commands = await redis.get(f"analytics:total_commands:{today}")
        total_commands = int(total_commands) if total_commands else 0

        unique_users = await redis.scard(f"analytics:unique_users:{today}")

        premium_purchases = await redis.get(f"analytics:premium_purchases:{today}")
        premium_purchases = int(premium_purchases) if premium_purchases else 0

        commands = ["forecast", "day", "moon", "compat", "settings"]
        top_commands = {}
        for cmd in commands:
            count = await redis.get(f"analytics:command:{cmd}:{today}")
            top_commands[cmd] = int(count) if count else 0

        return {
            "date": today,
            "total_commands": total_commands,
            "unique_users": unique_users,
            "premium_purchases": premium_purchases,
            "commands": top_commands,
        }

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return {}


async def log_error(user_id: Optional[int], command: Optional[str], error: str) -> None:
    try:
        redis = await get_redis()
        today = date.today().isoformat()
        timestamp = datetime.now().isoformat()

        key = f"analytics:errors:{today}"
        error_entry = f"[{timestamp}] user={user_id} cmd={command} error={error}"
        await redis.lpush(key, error_entry)
        await redis.expire(key, 86400 * 7)

        key_count = f"analytics:error_count:{today}"
        await redis.incr(key_count)
        await redis.expire(key_count, 86400)

    except Exception as e:
        logger.error(f"Error logging error: {e}")
