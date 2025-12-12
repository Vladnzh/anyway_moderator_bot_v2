# TODO: Настройка массовой рассылки

## Что нужно сделать

### 1. Определить структуру таблицы users в Supabase

Текущий код ожидает следующие поля в таблице `users`:

```sql
CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Telegram данные (ОБЯЗАТЕЛЬНО для рассылки)
  tg_user_id bigint UNIQUE,  -- Telegram User ID

  -- Дополнительные поля (опционально, но рекомендуется)
  username text,              -- Telegram username (@username)
  email text,                 -- Email пользователя
  full_name text,             -- Полное имя

  -- Служебные поля
  created_at timestamp DEFAULT NOW(),
  updated_at timestamp DEFAULT NOW(),
  status text DEFAULT 'active'  -- active, banned, inactive и т.д.
);

-- Индекс для быстрого поиска
CREATE INDEX idx_users_tg_user_id ON users(tg_user_id);
```

### 2. Добавить тестовые данные

Добавьте тестовых пользователей в вашу таблицу:

```sql
-- Пример вставки тестового пользователя
INSERT INTO users (tg_user_id, username, email, full_name)
VALUES
  (123456789, 'test_user1', 'test1@example.com', 'Test User 1'),
  (987654321, 'test_user2', 'test2@example.com', 'Test User 2');
```

**ВАЖНО:** Используйте реальные Telegram ID для тестирования!

Чтобы получить свой Telegram ID:
1. Напишите боту @userinfobot в Telegram
2. Он пришлет ваш ID
3. Используйте этот ID для тестовых данных

### 3. Реализовать фильтры (ОПЦИОНАЛЬНО, но рекомендуется)

Сейчас код выбирает ВСЕХ пользователей с tg_user_id. В будущем можно добавить фильтры:

#### В файле `supabase_client.py`:

Раскомментируйте и доработайте секцию с фильтрами (строки ~120-140):

```python
# TODO: Добавить поддержку фильтров
# Пример:
if filters:
    conditions = []
    params = []

    # Фильтр по дате создания
    if "created_at_gte" in filters:
        conditions.append(f"created_at >= ${len(params) + 1}")
        params.append(filters["created_at_gte"])

    # Фильтр по email домену
    if "email_like" in filters:
        conditions.append(f"email LIKE ${len(params) + 1}")
        params.append(filters["email_like"])

    # Фильтр по статусу
    if "status" in filters:
        conditions.append(f"status = ${len(params) + 1}")
        params.append(filters["status"])

    if conditions:
        query += " AND " + " AND ".join(conditions)

    rows = await conn.fetch(query, *params)
```

#### Примеры использования фильтров в API:

```json
{
  "message": "Привет!",
  "filters": {
    "created_at_gte": "2024-01-01",
    "status": "active"
  }
}
```

### 4. Обновить API endpoint (после реализации фильтров)

В `admin.py` передавайте фильтры в `query_users_for_broadcast()`:

```python
users = await query_users_for_broadcast(filters=request.filters)
```

Это уже сделано, но фильтры пока игнорируются.

### 5. Настроить Row Level Security (RLS) в Supabase

Убедитесь что у вашего PostgreSQL пользователя есть доступ к таблице `users`:

```sql
-- Разрешить SELECT для роли postgres
GRANT SELECT ON users TO postgres;

-- Или отключить RLS для таблицы users (НЕ РЕКОМЕНДУЕТСЯ для продакшена)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
```

### 6. Тестирование

#### Шаг 1: Проверьте подключение к базе

```bash
# Добавьте в .env файл:
DB_HOST=db.your-project.supabase.co
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_database_password
DB_NAME=postgres

# Перезапустите админ-панель
docker restart moderator-bot-admin

# Проверьте логи
docker logs moderator-bot-admin
```

Вы должны увидеть:
```
✅ Пул подключений к Supabase создан: db.your-project.supabase.co:5432/postgres
```

#### Шаг 2: Протестируйте предпросмотр

```bash
curl -X POST http://localhost:8000/api/broadcast/preview \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Должно вернуть список пользователей с tg_user_id.

#### Шаг 3: Протестируйте отправку (ОСТОРОЖНО!)

```bash
curl -X POST http://localhost:8000/api/broadcast/send \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Тестовое сообщение",
    "parse_mode": null
  }'
```

### 7. Примеры реальных SQL запросов для Supabase

#### Активные пользователи за последний месяц:
```sql
SELECT tg_user_id, username, email, full_name
FROM users
WHERE tg_user_id IS NOT NULL
  AND created_at >= NOW() - INTERVAL '30 days'
  AND status = 'active';
```

#### Пользователи с определенным доменом email:
```sql
SELECT tg_user_id, username, email, full_name
FROM users
WHERE tg_user_id IS NOT NULL
  AND email LIKE '%@gmail.com';
```

#### VIP пользователи:
```sql
SELECT tg_user_id, username, email, full_name
FROM users
WHERE tg_user_id IS NOT NULL
  AND subscription_tier = 'vip';
```

## Что уже сделано

✅ Добавлен asyncpg в зависимости
✅ Создан модуль supabase_client.py с пулом подключений
✅ Обновлен admin.py для использования asyncpg
✅ Обновлен env.example с PostgreSQL настройками
✅ Добавлены API endpoints /api/broadcast/preview и /api/broadcast/send
✅ Реализована базовая логика отправки сообщений

## Что нужно доделать

⏳ Определить финальную структуру таблицы users
⏳ Добавить тестовых пользователей
⏳ Реализовать фильтры (опционально)
⏳ Протестировать на реальных данных
⏳ Настроить RLS/права доступа в Supabase

## Полезные ссылки

- [Supabase Database Settings](https://supabase.com/dashboard/project/_/settings/database)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [PostgreSQL Filters](https://www.postgresql.org/docs/current/functions.html)
