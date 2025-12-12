# Руководство по массовой рассылке

## Описание функционала

Функционал массовой рассылки позволяет отправлять сообщения пользователям через Telegram бота с фильтрацией по условиям из Supabase базы данных.

## Настройка

### 1. Переменные окружения

Добавьте в ваш `.env` файл:

```bash
# Supabase настройки для массовой рассылки
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

**Где взять эти значения:**
- `SUPABASE_URL` - URL вашего Supabase проекта (Project Settings → API → Project URL)
- `SUPABASE_KEY` - Anon/Public key (Project Settings → API → Project API keys)

### 2. Структура таблицы пользователей

Ваша таблица `users` в Supabase должна содержать поле `tg_user_id` - это Telegram ID пользователя.

Пример структуры:
```sql
CREATE TABLE users (
  id uuid PRIMARY KEY,
  email text,
  username text,
  full_name text,
  tg_user_id bigint,  -- Telegram User ID
  created_at timestamp
);
```

## API Endpoints

### 1. Предпросмотр списка пользователей

**Endpoint:** `POST /api/broadcast/preview`

**Описание:** Получить список пользователей, которые получат сообщение (без отправки)

**Headers:**
```
Authorization: Bearer YOUR_ADMIN_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "supabase_query": "select=tg_user_id,username,email,full_name&tg_user_id=not.is.null"
}
```

**Параметр `supabase_query`:**
Это PostgREST query string для фильтрации пользователей. Формат соответствует [Supabase REST API](https://postgrest.org/en/stable/api.html).

**Примеры запросов:**

1. Все пользователи с привязанным Telegram:
```
select=tg_user_id,username,email&tg_user_id=not.is.null
```

2. Пользователи с определенным email доменом:
```
select=tg_user_id,username,email&tg_user_id=not.is.null&email=like.*@example.com
```

3. Пользователи созданные после определенной даты:
```
select=tg_user_id,username,email&tg_user_id=not.is.null&created_at=gte.2024-01-01
```

4. Комбинация условий:
```
select=tg_user_id,username,email&tg_user_id=not.is.null&created_at=gte.2024-01-01&email=like.*@gmail.com
```

**Response:**
```json
{
  "success": true,
  "users": [
    {
      "tg_user_id": "123456789",
      "username": "john_doe",
      "email": "john@example.com",
      "full_name": "John Doe"
    }
  ],
  "count": 1,
  "message": "Найдено 1 пользователей с привязанным Telegram"
}
```

### 2. Отправка массовой рассылки

**Endpoint:** `POST /api/broadcast/send`

**Описание:** Отправить сообщение всем пользователям, удовлетворяющим условию

**Headers:**
```
Authorization: Bearer YOUR_ADMIN_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "Привет! Это тестовое сообщение от бота.",
  "supabase_query": "select=tg_user_id,username&tg_user_id=not.is.null",
  "parse_mode": "HTML"
}
```

**Параметры:**
- `message` (обязательный) - текст сообщения для отправки
- `supabase_query` (обязательный) - PostgREST запрос для фильтрации пользователей
- `parse_mode` (опциональный) - режим форматирования: `"HTML"`, `"Markdown"` или `null`

**Примеры форматированных сообщений:**

HTML:
```json
{
  "message": "<b>Важное уведомление!</b>\n\nВаш аккаунт <i>активирован</i>",
  "parse_mode": "HTML"
}
```

Markdown:
```json
{
  "message": "**Важное уведомление!**\n\nВаш аккаунт _активирован_",
  "parse_mode": "Markdown"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Рассылка завершена: отправлено 45, ошибок 2",
  "data": {
    "total": 47,
    "success": 45,
    "failed": 2,
    "failed_users": [
      {
        "tg_user_id": "987654321",
        "username": "blocked_user",
        "error": "Forbidden: bot was blocked by the user"
      }
    ]
  }
}
```

## Примеры использования

### Пример 1: curl

Предпросмотр:
```bash
curl -X POST http://localhost:8000/api/broadcast/preview \
  -H "Authorization: Bearer your_admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "supabase_query": "select=tg_user_id,username,email&tg_user_id=not.is.null&created_at=gte.2024-01-01"
  }'
```

Отправка:
```bash
curl -X POST http://localhost:8000/api/broadcast/send \
  -H "Authorization: Bearer your_admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Привет! Это тестовое сообщение.",
    "supabase_query": "select=tg_user_id,username&tg_user_id=not.is.null&created_at=gte.2024-01-01",
    "parse_mode": "HTML"
  }'
```

### Пример 2: Python

```python
import requests

ADMIN_URL = "http://localhost:8000"
ADMIN_TOKEN = "your_admin_token"

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}

# 1. Предпросмотр
preview_data = {
    "supabase_query": "select=tg_user_id,username,email&tg_user_id=not.is.null"
}

response = requests.post(
    f"{ADMIN_URL}/api/broadcast/preview",
    headers=headers,
    json=preview_data
)

preview = response.json()
print(f"Будет отправлено: {preview['count']} пользователям")

# 2. Отправка (если устраивает количество)
if preview['count'] > 0:
    broadcast_data = {
        "message": "<b>Важное сообщение!</b>\n\nВаш аккаунт был обновлен.",
        "supabase_query": "select=tg_user_id,username&tg_user_id=not.is.null",
        "parse_mode": "HTML"
    }

    response = requests.post(
        f"{ADMIN_URL}/api/broadcast/send",
        headers=headers,
        json=broadcast_data
    )

    result = response.json()
    print(f"Отправлено: {result['data']['success']}")
    print(f"Ошибок: {result['data']['failed']}")
```

### Пример 3: JavaScript (fetch)

```javascript
const ADMIN_URL = "http://localhost:8000";
const ADMIN_TOKEN = "your_admin_token";

async function sendBroadcast() {
  // 1. Предпросмотр
  const previewResponse = await fetch(`${ADMIN_URL}/api/broadcast/preview`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${ADMIN_TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      supabase_query: "select=tg_user_id,username,email&tg_user_id=not.is.null"
    })
  });

  const preview = await previewResponse.json();
  console.log(`Будет отправлено: ${preview.count} пользователям`);

  // 2. Отправка
  if (preview.count > 0) {
    const sendResponse = await fetch(`${ADMIN_URL}/api/broadcast/send`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${ADMIN_TOKEN}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: "Привет! Это сообщение от бота.",
        supabase_query: "select=tg_user_id,username&tg_user_id=not.is.null",
        parse_mode: "HTML"
      })
    });

    const result = await sendResponse.json();
    console.log(`Отправлено: ${result.data.success}, Ошибок: ${result.data.failed}`);
  }
}

sendBroadcast();
```

## Безопасность и ограничения

### Rate Limiting
- Между отправкой сообщений добавлена задержка 50ms для избежания блокировки Telegram API
- Для больших рассылок (>100 пользователей) рекомендуется разбивать на части

### Ошибки отправки
Типичные ошибки:
- `Forbidden: bot was blocked by the user` - пользователь заблокировал бота
- `Bad Request: chat not found` - неверный tg_user_id
- `Too Many Requests: retry after X` - превышен лимит запросов

### Рекомендации по использованию

1. **Всегда используйте предпросмотр** перед отправкой для проверки количества получателей
2. **Тестируйте на небольших группах** перед массовой рассылкой
3. **Следите за логами** - все операции логируются в админ-панели
4. **Проверяйте failed_users** в ответе для анализа ошибок

## Troubleshooting

### Проблема: "Supabase не настроен"
**Решение:** Проверьте наличие `SUPABASE_URL` и `SUPABASE_KEY` в `.env` файле

### Проблема: "Не найдено пользователей с привязанным Telegram"
**Решение:**
- Проверьте что в таблице `users` есть поле `tg_user_id`
- Убедитесь что у пользователей указан Telegram ID (не null)
- Проверьте правильность Supabase query

### Проблема: "Ошибка Supabase: 404"
**Решение:**
- Проверьте правильность `SUPABASE_URL`
- Убедитесь что таблица `users` существует
- Проверьте права доступа к таблице (RLS policies)

### Проблема: Высокий процент ошибок отправки
**Решение:**
- Проверьте что `tg_user_id` содержит корректные Telegram ID
- Часть пользователей могла заблокировать бота - это нормально
- Проверьте что бот запущен и токен действителен

## Логирование

Все операции массовой рассылки логируются:

```
📤 Начинаем массовую рассылку для 50 пользователей
✅ Сообщение отправлено пользователю 123456789
❌ Не удалось отправить пользователю 987654321: Forbidden: bot was blocked by the user
📊 Массовая рассылка завершена: успешно=48, ошибок=2
```

Логи можно просматривать через:
```bash
docker logs moderator-bot-admin
```
