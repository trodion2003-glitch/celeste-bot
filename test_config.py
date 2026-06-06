"""Быстрая проверка конфига и подключения к БД"""
import asyncio
import sys

print("🔍 Проверяем config.py...")
try:
    from config import (
        BOT_TOKEN, DEEPSEEK_API_KEY, DATABASE_URL, REDIS_URL, DEBUG
    )
    print(f"  ✓ BOT_TOKEN:         {'SET' if BOT_TOKEN else '❌ НЕТ'}")
    print(f"  ✓ DEEPSEEK_API_KEY:  {'SET' if DEEPSEEK_API_KEY else '❌ НЕТ'}")
    print(f"  ✓ DATABASE_URL:     {DATABASE_URL}")
    print(f"  ✓ REDIS_URL:        {REDIS_URL}")
    print(f"  ✓ DEBUG:            {DEBUG}")
except Exception as e:
    print(f"  ❌ Ошибка конфига: {e}")
    sys.exit(1)

print("\n🔍 Проверяем models/database.py...")
try:
    from models.database import Base, engine
    print(f"  ✓ Base:   {Base}")
    print(f"  ✓ Engine: {engine}")
except Exception as e:
    print(f"  ❌ Ошибка models: {e}")
    sys.exit(1)

print("\n🔍 Проверяем подключение к PostgreSQL...")
async def test_db():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(__import__('sqlalchemy').text("SELECT 1"))
            print(f"  ✓ PostgreSQL: OK")
    except Exception as e:
        print(f"  ❌ PostgreSQL недоступен: {e}")

asyncio.run(test_db())

print("\n✅ Всё готово!")
