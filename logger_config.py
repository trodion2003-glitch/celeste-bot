"""
logger_config.py — конфигурация логирования для Celesté Bot
"""

import logging
import logging.config
from config import LOGGING_CONFIG

def setup_logging():
    """
    Инициализирует логирование согласно конфигу.
    Вызывается в main.py при старте.
    """
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.info("✓ Logging configured")


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер для модуля.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Привет мир")
    """
    return logging.getLogger(name)
