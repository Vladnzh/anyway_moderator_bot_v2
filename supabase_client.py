# -*- coding: utf-8 -*-
"""
Клиент для подключения к Supabase PostgreSQL через asyncpg
Используется для массовой рассылки сообщений
"""

import os
import logging
from typing import Optional, List, Dict, Any

import asyncpg
from asyncpg import Pool

logger = logging.getLogger(__name__)


class SupabasePool:
    """Менеджер пула подключений к Supabase PostgreSQL."""

    _pool: Optional[Pool] = None

    @classmethod
    async def initialize(cls) -> None:
        """Инициализировать пул подключений к Supabase."""
        if cls._pool is not None:
            logger.debug("Пул Supabase уже инициализирован")
            return

        # Получаем параметры подключения из переменных окружения
        db_host = os.getenv("DB_HOST")
        db_port = int(os.getenv("DB_PORT", "5432"))
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME", "postgres")

        if not db_host or not db_password:
            logger.warning("⚠️ DB_HOST или DB_PASSWORD не настроены - функция массовой рассылки недоступна")
            return

        try:
            cls._pool = await asyncpg.create_pool(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
                min_size=1,
                max_size=5,
                command_timeout=60
            )
            logger.info(f"✅ Пул подключений к Supabase создан: {db_host}:{db_port}/{db_name}")
        except Exception as e:
            logger.error(f"❌ Ошибка создания пула Supabase: {e}")
            cls._pool = None

    @classmethod
    async def close(cls) -> None:
        """Закрыть пул подключений."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("🔌 Пул подключений к Supabase закрыт")

    @classmethod
    def get_pool(cls) -> Optional[Pool]:
        """Получить пул подключений."""
        return cls._pool

    @classmethod
    def is_available(cls) -> bool:
        """Проверить доступность пула подключений."""
        return cls._pool is not None


async def query_users_for_broadcast(
    filters: Optional[Dict[str, Any]] = None,
    select_fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Запросить пользователей для массовой рассылки.

    Args:
        filters: Словарь с условиями фильтрации (пока не реализовано, заглушка)
        select_fields: Список полей для выборки

    Returns:
        Список пользователей с tg_user_id

    # TODO: Реализовать фильтрацию пользователей
    # Примеры фильтров:
    # - По дате регистрации: {"created_at_gte": "2024-01-01"}
    # - По email домену: {"email_like": "%@gmail.com"}
    # - По статусу: {"status": "active"}
    # - Комбинированные фильтры

    # TODO: Определить структуру таблицы users в Supabase
    # Обязательные поля:
    # - tg_user_id (bigint) - Telegram User ID
    # Опциональные поля:
    # - username (text)
    # - email (text)
    # - full_name (text)
    # - created_at (timestamp)
    # - status (text)
    """

    pool = SupabasePool.get_pool()
    if not pool:
        logger.error("❌ Пул Supabase недоступен")
        return []

    # Выбираем поля (по умолчанию только необходимые для рассылки)
    if select_fields is None:
        select_fields = ["tg_user_id", "username", "email", "full_name"]

    fields = ", ".join(select_fields)

    # TODO: Добавить поддержку фильтров
    # Сейчас просто выбираем всех пользователей с tg_user_id
    query = f"""
        SELECT {fields}
        FROM users
        WHERE tg_user_id IS NOT NULL
    """

    # TODO: Добавить параметризованные фильтры
    # Пример:
    # if filters:
    #     conditions = []
    #     params = []
    #     for key, value in filters.items():
    #         if key == "created_at_gte":
    #             conditions.append("created_at >= $" + str(len(params) + 1))
    #             params.append(value)
    #         elif key == "email_like":
    #             conditions.append("email LIKE $" + str(len(params) + 1))
    #             params.append(value)
    #
    #     if conditions:
    #         query += " AND " + " AND ".join(conditions)

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)

            # Преобразуем результаты в список словарей
            users = [dict(row) for row in rows]

            logger.info(f"📊 Получено {len(users)} пользователей из Supabase")
            return users

    except Exception as e:
        logger.error(f"❌ Ошибка запроса пользователей: {e}")
        return []


async def get_users_count(filters: Optional[Dict[str, Any]] = None) -> int:
    """
    Получить количество пользователей удовлетворяющих условиям.

    Args:
        filters: Словарь с условиями фильтрации

    Returns:
        Количество пользователей
    """
    pool = SupabasePool.get_pool()
    if not pool:
        return 0

    query = "SELECT COUNT(*) FROM users WHERE tg_user_id IS NOT NULL"

    # TODO: Добавить поддержку фильтров

    try:
        async with pool.acquire() as conn:
            count = await conn.fetchval(query)
            return count or 0
    except Exception as e:
        logger.error(f"❌ Ошибка подсчета пользователей: {e}")
        return 0
