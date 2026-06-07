"""
config.py — конфигурация Celesté Bot
Все переменные окружения загружаются сюда
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня проекта
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# ============================================================================
# TELEGRAM
# ============================================================================
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()

# ============================================================================
# DEEPSEEK API
# ============================================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek-V3
DEEPSEEK_MAX_TOKENS = 1024

# ============================================================================
# DATABASE
# ============================================================================
DATABASE_URL = (os.getenv("DATABASE_URL") or "postgresql+asyncpg://postgres:password@localhost:5432/celeste").strip()
# Railway даёт postgresql://, SQLAlchemy async требует postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Для alembic (синхронное подключение)
SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

# ============================================================================
# REDIS
# ============================================================================
REDIS_URL = (os.getenv("REDIS_URL") or "redis://localhost:6379/0").strip()

# Времена жизни кэша (в секундах)
CACHE_TTL_FORECAST = 24 * 3600  # 24 часа
CACHE_TTL_CHART = 7 * 24 * 3600  # 7 дней
CACHE_TTL_TRANSITS = 6 * 3600  # 6 часов

# ============================================================================
# ENVIRONMENT
# ============================================================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================================================
# TIMEZONE & LOCALE
# ============================================================================
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")

# ============================================================================
# LOGGING
# ============================================================================
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "simple": {
            "format": "%(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": LOG_LEVEL,
            "formatter": "verbose",
            "filename": "celeste.log",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console", "file"],
    },
}

# ============================================================================
# BOT SETTINGS
# ============================================================================
BOT_USERNAME = "CelesteAstroBot"

# Команды, которые поддерживает бот
BOT_COMMANDS = [
    ("start", "Начать знакомство с Celesté"),
    ("forecast", "✦ Прогноз на неделю"),
    ("day", "☽ Карта дня"),
    ("menu", "Главное меню"),
    ("help", "Помощь и FAQ"),
    ("cancel", "Отмена"),
]

# ============================================================================
# PUSH-NOTIFICATIONS (для Celery)
# ============================================================================
CELERY_BROKER = REDIS_URL
CELERY_BACKEND = REDIS_URL

# Время для daily-pushes (в формате HH:MM UTC)
PUSH_TIME_MORNING = "07:00"  # 9:00 по московскому (UTC+2)
PUSH_TIME_WEEKLY = "08:00"   # Понедельник 10:00 по московскому
PUSH_TIME_RETURN = "16:00"   # 18:00 по московскому

# ============================================================================
# FEATURE FLAGS
# ============================================================================
ENABLE_PREMIUM = True  # Функции premium доступны?
ENABLE_PUSH_NOTIFICATIONS = True  # Отправлять ли push'и?
ENABLE_SHARING = True  # Делиться прогнозом?

# ============================================================================
# ASTROLOGY SETTINGS
# ============================================================================
# Зодиакальные знаки на русском
ZODIAC_SIGNS_RU = {
    "Ari": "♈ Овен",
    "Tau": "♉ Телец",
    "Gem": "♊ Близнецы",
    "Can": "♋ Рак",
    "Leo": "♌ Лев",
    "Vir": "♍ Дева",
    "Lib": "♎ Весы",
    "Sco": "♏ Скорпион",
    "Sag": "♐ Стрелец",
    "Cap": "♑ Козерог",
    "Aqu": "♒ Водолей",
    "Pis": "♓ Рыбы",
}

# Планеты на русском
PLANETS_RU = {
    "Sun": "☀️ Солнце",
    "Moon": "🌙 Луна",
    "Mercury": "☿️ Меркурий",
    "Venus": "♀️ Венера",
    "Mars": "♂️ Марс",
    "Jupiter": "♃ Юпитер",
    "Saturn": "♄ Сатурн",
    "Uranus": "♅ Уран",
    "Neptune": "♆ Нептун",
    "Pluto": "♇ Плутон",
}

# Фазы луны
MOON_PHASES_RU = [
    "🌑 Новолуние",
    "🌒 Растущий серп",
    "🌓 Первая четверть",
    "🌔 Растущая луна",
    "🌕 Полнолуние",
    "🌖 Убывающая луна",
    "🌗 Последняя четверть",
    "🌘 Убывающий серп",
]

# ============================================================================
# VALIDATION
# ============================================================================
def validate_config():
    """Проверяем, что все критические переменные установлены"""
    critical_vars = [BOT_TOKEN, DEEPSEEK_API_KEY]
    missing = [v for v in critical_vars if not v]
    if missing:
        raise RuntimeError(f"❌ Критические переменные не установлены: {missing}")

# validate_config() вызывается явно при запуске бота (в main.py)

if DEBUG:
    print("✓ Config loaded successfully")
    print(f"  Environment: {ENVIRONMENT}")
    print(f"  Database: {DATABASE_URL}")
    print(f"  Redis: {REDIS_URL}")
