"""
services/tasks.py — асинхронные задачи (Celery)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import Celery
from config import CELERY_BROKER, CELERY_BACKEND
import asyncio
from services.forecast import generate_weekly_forecast
from services.redis_cache import cache_forecast
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

celery_app = Celery('celeste', broker=CELERY_BROKER, backend=CELERY_BACKEND)
celery_app.conf.broker_connection_retry_on_startup = True

@celery_app.task(bind=True)
def generate_forecast_task(self, user_id: int, user_name: str, natal: dict):
    """
    Фоновая задача: генерируем прогноз и кэшируем его
    
    Вызывается асинхронно, не блокирует бота
    """
    try:
        logger.info(f"Generating forecast for user {user_id}")
        
        # Запускаем async функцию из sync контекста
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        forecast_text = loop.run_until_complete(
            generate_weekly_forecast(user_name, natal, user_id)
        )
        
        # Кэшируем
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_start_str = week_start.isoformat()
        
        loop.run_until_complete(
            cache_forecast(user_id, week_start_str, forecast_text)
        )
        
        logger.info(f"Forecast generated for user {user_id}")
        return forecast_text
        
    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        self.retry(exc=e, countdown=60)  # Повторить через 60 секунд