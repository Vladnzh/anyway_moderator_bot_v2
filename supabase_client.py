# -*- coding: utf-8 -*-
"""
Клиент для подключения к Supabase PostgreSQL через asyncpg
Используется для массовой рассылки сообщений и работы с аудиториями
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

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


# ==================== АУДИТОРИИ ====================

async def get_audiences() -> List[Dict[str, Any]]:
    """
    Получить список всех активных аудиторий.

    Returns:
        Список аудиторий с их настройками
    """
    pool = SupabasePool.get_pool()
    if not pool:
        logger.error("❌ Пул Supabase недоступен")
        return []

    query = """
        SELECT
            id,
            name,
            description,
            filters,
            last_user_count,
            last_calculated_at,
            created_at,
            updated_at,
            is_active
        FROM broadcast_audiences
        WHERE is_active = true
        ORDER BY created_at DESC
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)
            audiences = []
            for row in rows:
                audience = dict(row)
                # Конвертируем UUID в строку
                audience['id'] = str(audience['id'])
                # Конвертируем datetime в ISO строку
                for key in ['last_calculated_at', 'created_at', 'updated_at']:
                    if audience.get(key):
                        audience[key] = audience[key].isoformat()
                audiences.append(audience)

            logger.info(f"📊 Получено {len(audiences)} аудиторий")
            return audiences

    except Exception as e:
        logger.error(f"❌ Ошибка получения аудиторий: {e}")
        return []


async def get_audience_by_id(audience_id: str) -> Optional[Dict[str, Any]]:
    """
    Получить аудиторию по ID.

    Args:
        audience_id: UUID аудитории

    Returns:
        Данные аудитории или None
    """
    pool = SupabasePool.get_pool()
    if not pool:
        return None

    query = """
        SELECT
            id,
            name,
            description,
            filters,
            last_user_count,
            last_calculated_at,
            created_at,
            updated_at,
            is_active
        FROM broadcast_audiences
        WHERE id = $1
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, audience_id)
            if row:
                audience = dict(row)
                audience['id'] = str(audience['id'])
                for key in ['last_calculated_at', 'created_at', 'updated_at']:
                    if audience.get(key):
                        audience[key] = audience[key].isoformat()
                return audience
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка получения аудитории {audience_id}: {e}")
        return None


async def create_audience(
    name: str,
    filters: Dict[str, Any],
    description: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Создать новую аудиторию.

    Args:
        name: Название аудитории
        filters: Фильтры для выборки пользователей
        description: Описание аудитории

    Returns:
        Созданная аудитория или None
    """
    pool = SupabasePool.get_pool()
    if not pool:
        return None

    query = """
        INSERT INTO broadcast_audiences (name, description, filters)
        VALUES ($1, $2, $3)
        RETURNING id, name, description, filters, last_user_count, last_calculated_at, created_at, updated_at, is_active
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, name, description, json.dumps(filters))
            if row:
                audience = dict(row)
                audience['id'] = str(audience['id'])
                for key in ['last_calculated_at', 'created_at', 'updated_at']:
                    if audience.get(key):
                        audience[key] = audience[key].isoformat()
                logger.info(f"✅ Создана аудитория: {name} (ID: {audience['id']})")
                return audience
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка создания аудитории: {e}")
        return None


async def update_audience(
    audience_id: str,
    name: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Обновить аудиторию.

    Args:
        audience_id: UUID аудитории
        name: Новое название (опционально)
        filters: Новые фильтры (опционально)
        description: Новое описание (опционально)

    Returns:
        Обновленная аудитория или None
    """
    pool = SupabasePool.get_pool()
    if not pool:
        return None

    # Строим динамический запрос
    updates = []
    params = []
    param_idx = 1

    if name is not None:
        updates.append(f"name = ${param_idx}")
        params.append(name)
        param_idx += 1

    if filters is not None:
        updates.append(f"filters = ${param_idx}")
        params.append(json.dumps(filters))
        param_idx += 1

    if description is not None:
        updates.append(f"description = ${param_idx}")
        params.append(description)
        param_idx += 1

    if not updates:
        return await get_audience_by_id(audience_id)

    params.append(audience_id)

    query = f"""
        UPDATE broadcast_audiences
        SET {', '.join(updates)}
        WHERE id = ${param_idx}
        RETURNING id, name, description, filters, last_user_count, last_calculated_at, created_at, updated_at, is_active
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            if row:
                audience = dict(row)
                audience['id'] = str(audience['id'])
                for key in ['last_calculated_at', 'created_at', 'updated_at']:
                    if audience.get(key):
                        audience[key] = audience[key].isoformat()
                logger.info(f"✅ Обновлена аудитория: {audience['name']} (ID: {audience_id})")
                return audience
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка обновления аудитории {audience_id}: {e}")
        return None


async def delete_audience(audience_id: str) -> bool:
    """
    Удалить аудиторию (мягкое удаление - установка is_active = false).

    Args:
        audience_id: UUID аудитории

    Returns:
        True если успешно, False если ошибка
    """
    pool = SupabasePool.get_pool()
    if not pool:
        return False

    query = """
        UPDATE broadcast_audiences
        SET is_active = false
        WHERE id = $1
        RETURNING id
    """

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, audience_id)
            if row:
                logger.info(f"✅ Аудитория {audience_id} удалена (деактивирована)")
                return True
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка удаления аудитории {audience_id}: {e}")
        return False


async def get_marathons_list() -> List[Dict[str, Any]]:
    """
    Получить список доступных марафонов для фильтрации.

    Returns:
        Список марафонов с их reference_id
    """
    pool = SupabasePool.get_pool()
    if not pool:
        return []

    query = """
        SELECT DISTINCT
            mi.reference_id,
            m.title,
            m.start_date,
            m.end_date
        FROM marathon_invoices mi
        JOIN marathons m ON mi.marathon_id = m.id
        WHERE mi.is_enabled = true
        ORDER BY m.start_date DESC
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)
            marathons = []
            for row in rows:
                marathon = dict(row)
                for key in ['start_date', 'end_date']:
                    if marathon.get(key):
                        marathon[key] = marathon[key].isoformat()
                marathons.append(marathon)
            return marathons

    except Exception as e:
        logger.error(f"❌ Ошибка получения списка марафонов: {e}")
        return []


async def query_users_by_audience(
    audience_id: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Получить пользователей по аудитории или фильтрам.

    Использует view telegram_marathon_users для выборки.

    Args:
        audience_id: UUID аудитории (если указан, берем фильтры из нее)
        filters: Прямые фильтры (если audience_id не указан)

    Returns:
        Список пользователей с telegram_id
    """
    pool = SupabasePool.get_pool()
    if not pool:
        logger.error("❌ Пул Supabase недоступен")
        return []

    # Если указан audience_id, получаем фильтры из аудитории
    if audience_id:
        audience = await get_audience_by_id(audience_id)
        if not audience:
            logger.error(f"❌ Аудитория {audience_id} не найдена")
            return []
        filters = audience.get('filters', {})

    if not filters:
        filters = {}

    # Строим WHERE условия на основе фильтров
    conditions = []
    params = []
    param_idx = 1

    # Фильтр по марафону
    if filters.get('marathon_ref_id'):
        conditions.append(f"marathon_ref_id = ${param_idx}")
        params.append(filters['marathon_ref_id'])
        param_idx += 1

    # Фильтр по покупке
    if 'is_purchased' in filters and filters['is_purchased'] is not None:
        conditions.append(f"is_purchased = ${param_idx}")
        params.append(filters['is_purchased'])
        param_idx += 1

    # Фильтр по активному доступу
    if 'has_active_access' in filters and filters['has_active_access'] is not None:
        conditions.append(f"has_active_access = ${param_idx}")
        params.append(filters['has_active_access'])
        param_idx += 1

    # Фильтр по прогрессу (минимум)
    if filters.get('progress_min') is not None:
        conditions.append(f"progress_percent >= ${param_idx}")
        params.append(filters['progress_min'])
        param_idx += 1

    # Фильтр по прогрессу (максимум)
    if filters.get('progress_max') is not None:
        conditions.append(f"progress_percent <= ${param_idx}")
        params.append(filters['progress_max'])
        param_idx += 1

    # Фильтр по выполненным дням (минимум)
    if filters.get('completed_days_min') is not None:
        conditions.append(f"completed_days_in_marathon >= ${param_idx}")
        params.append(filters['completed_days_min'])
        param_idx += 1

    # Фильтр по выполненным дням (максимум)
    if filters.get('completed_days_max') is not None:
        conditions.append(f"completed_days_in_marathon <= ${param_idx}")
        params.append(filters['completed_days_max'])
        param_idx += 1

    # Фильтр "начал заниматься"
    if 'has_started' in filters and filters['has_started'] is not None:
        if filters['has_started']:
            conditions.append("completed_days_in_marathon > 0")
        else:
            conditions.append("completed_days_in_marathon = 0")

    # Фильтр по дате регистрации
    if filters.get('registered_after'):
        conditions.append(f"user_created_at >= ${param_idx}")
        params.append(filters['registered_after'])
        param_idx += 1

    if filters.get('registered_before'):
        conditions.append(f"user_created_at <= ${param_idx}")
        params.append(filters['registered_before'])
        param_idx += 1

    # Фильтр по последней активности
    if filters.get('last_activity_after'):
        conditions.append(f"last_activity >= ${param_idx}")
        params.append(filters['last_activity_after'])
        param_idx += 1

    if filters.get('last_activity_before'):
        conditions.append(f"last_activity <= ${param_idx}")
        params.append(filters['last_activity_before'])
        param_idx += 1

    # Собираем запрос
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT DISTINCT
            telegram_id,
            telegram_username,
            first_name,
            last_name,
            display_name,
            email,
            marathon_ref_id,
            marathon_title,
            is_purchased,
            has_active_access,
            progress_percent,
            completed_days_in_marathon
        FROM telegram_marathon_users
        WHERE {where_clause}
        ORDER BY telegram_id
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            users = [dict(row) for row in rows]

            # Обновляем статистику аудитории если был указан audience_id
            if audience_id:
                await update_audience_stats(audience_id, len(users))

            logger.info(f"📊 Найдено {len(users)} пользователей по фильтрам")
            return users

    except Exception as e:
        logger.error(f"❌ Ошибка запроса пользователей по аудитории: {e}")
        return []


async def update_audience_stats(audience_id: str, user_count: int) -> None:
    """
    Обновить статистику аудитории после подсчета пользователей.

    Args:
        audience_id: UUID аудитории
        user_count: Количество найденных пользователей
    """
    pool = SupabasePool.get_pool()
    if not pool:
        return

    query = """
        UPDATE broadcast_audiences
        SET last_user_count = $1, last_calculated_at = NOW()
        WHERE id = $2
    """

    try:
        async with pool.acquire() as conn:
            await conn.execute(query, user_count, audience_id)

    except Exception as e:
        logger.error(f"❌ Ошибка обновления статистики аудитории: {e}")
