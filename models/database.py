"""
models/database.py — инициализация SQLAlchemy и асинхронные сессии
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from config import DATABASE_URL, SQLALCHEMY_DATABASE_URL, DEBUG

logger = logging.getLogger(__name__)

# ============================================================================
# BASE CLASS для всех моделей
# ============================================================================
class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy моделей"""
    pass


# ============================================================================
# ASYNC ENGINE
# ============================================================================
# NullPool избегает проблем с пулом соединений в development
engine = create_async_engine(
    DATABASE_URL,
    echo=DEBUG,  # Выводить SQL-запросы в консоль, если DEBUG=True
    poolclass=NullPool if DEBUG else None,  # Не кэшировать соединения в dev
)

# ============================================================================
# ASYNC SESSION FACTORY
# ============================================================================
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)


# ============================================================================
# Хелпер для работы с сессией в Telegram handlers
# ============================================================================
async def get_db_session() -> AsyncSession:
    """
    Dependency для получения сессии БД.
    Используется в handlers:
    
    async def my_handler(update, ctx):
        async with get_db_session() as session:
            user = await session.get(User, update.effective_user.id)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            await session.close()


# ============================================================================
# Инициализация БД (создание таблиц)
# ============================================================================
async def init_db():
    """
    Создаёт все таблицы в БД.
    Вызывается в main.py при запуске бота.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✓ Database initialized")



if DEBUG:
    logger.info(f"✓ Database configured: {DATABASE_URL}")
