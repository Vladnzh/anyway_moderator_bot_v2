# 🤖 Moderator Bot API Documentation

Полная документация API для управления Telegram модератор-ботом.

## 🔐 Авторизация

Все API запросы требуют авторизации через заголовок:
```
Authorization: Bearer YOUR_ADMIN_TOKEN
```

## 📋 Базовый URL

```
http://localhost:8000/api
```

---

## 🏷️ Управление тегами

### GET /api/tags
Получить все настроенные теги.

**Ответ:**
```json
{
  "success": true,
  "data": [
    {
      "id": "abc123",
      "tag": "#рецепт",
      "emoji": "🍓",
      "delay": 0,
      "match_mode": "prefix",
      "require_photo": true,
      "thread_name": "",
      "reply_ok": "Спасибо за рецепт!",
      "reply_need_photo": "Добавьте фото к рецепту",
      "reply_duplicate": "Такое фото уже было",
      "reply_pending": "Рецепт отправлен на модерацию",
      "moderation_enabled": true
    }
  ]
}
```

### POST /api/tags
Создать новый тег.

**Тело запроса:**
```json
{
  "tag": "#новый_тег",
  "emoji": "✨",
  "delay": 5,
  "match_mode": "prefix",
  "require_photo": false,
  "thread_name": "",
  "reply_ok": "",
  "reply_need_photo": "",
  "reply_duplicate": "",
  "reply_pending": "",
  "moderation_enabled": false
}
```

### PUT /api/tags/{tag_id}
Обновить существующий тег по ID.

**Параметры:**
- `tag_id` - уникальный ID тега

**Тело запроса:** аналогично POST /api/tags

### DELETE /api/tags/{tag_id}
Удалить тег по ID.

**Параметры:**
- `tag_id` - уникальный ID тега

---

## 📝 Журнал событий

### GET /api/logs
Получить логи событий бота.

**Параметры запроса:**
- `tag` (optional) - фильтр по тегу
- `limit` (optional) - количество записей (по умолчанию 50)

**Пример:**
```
GET /api/logs?tag=#рецепт&limit=10
```

**Ответ:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "user_id": 123456789,
      "username": "user123",
      "chat_id": -1001234567890,
      "message_id": 1001,
      "trigger": "#рецепт",
      "emoji": "🍓",
      "timestamp": "2025-09-05T18:30:00",
      "thread_name": "Кулинария",
      "media_type": "photo",
      "caption": "Вкусный рецепт"
    }
  ]
}
```

### DELETE /api/logs
Очистить все логи и связанные очереди.

**Ответ:**
```json
{
  "success": true,
  "message": "Очищено: 10 логов, 2 реакций, 1 модераций",
  "data": {
    "deleted_logs": 10,
    "deleted_reactions": 2,
    "deleted_moderation": 1
  }
}
```

---

## 📊 Статистика

### GET /api/stats
Получить общую статистику бота.

**Ответ:**
```json
{
  "success": true,
  "data": {
    "total_tags": 5,
    "total_logs": 150,
    "moderation": {
      "pending": 3,
      "approved": 45,
      "rejected": 12,
      "total": 60
    }
  }
}
```

---

## 🔍 Модерация сообщений

### GET /api/moderation
Получить очередь модерации.

**Ответ:**
```json
{
  "success": true,
  "data": [
    {
      "id": "abc123",
      "chat_id": -1001234567890,
      "message_id": 1001,
      "user_id": 123456789,
      "username": "user123",
      "tag": "#рецепт",
      "emoji": "🍓",
      "text": "Посмотрите на мой рецепт!",
      "caption": "Домашняя паста",
      "media_info": {
        "has_photo": true,
        "photo_file_id": "AgACAgIAAxkBAAIBYmXvZ...",
        "has_video": false
      },
      "thread_name": "Кулинария",
      "status": "pending",
      "created_at": "2025-09-05T18:30:00"
    }
  ]
}
```

### POST /api/moderation/{item_id}/approve
Одобрить элемент модерации.

**Параметры:**
- `item_id` - ID элемента модерации

**Ответ:**
```json
{
  "success": true,
  "message": "Элемент одобрен, реакция поставлена"
}
```

### POST /api/moderation/{item_id}/reject
Отклонить элемент модерации.

**Параметры:**
- `item_id` - ID элемента модерации

**Ответ:**
```json
{
  "success": true,
  "message": "Элемент отклонен"
}
```

---

## 🖼️ Медиафайлы

### GET /api/media/file/{file_id}
Получить медиафайл по file_id из Telegram.

**Параметры:**
- `file_id` - Telegram file_id медиафайла

**Ответ:**
```json
{
  "success": true,
  "file_url": "https://api.telegram.org/file/bot.../photo.jpg",
  "file_path": "photos/file_123.jpg",
  "media_type": "photo",
  "file_size": 1024000
}
```

---

## ⚡ Прямое управление реакциями

### POST /api/reactions/set
Поставить реакцию к сообщению.

**Тело запроса:**
```json
{
  "chat_id": -1001234567890,
  "message_id": 1001,
  "emoji": "🍓"
}
```

### DELETE /api/reactions/remove
Удалить реакцию с сообщения.

**Тело запроса:**
```json
{
  "chat_id": -1001234567890,
  "message_id": 1001,
  "emoji": "🍓"
}
```

### GET /api/reactions/queue
Получить текущую очередь реакций.

**Ответ:**
```json
{
  "success": true,
  "data": [
    {
      "id": "queue123",
      "chat_id": -1001234567890,
      "message_id": 1001,
      "emoji": "🍓",
      "created_at": "2025-09-05T18:30:00"
    }
  ]
}
```

### DELETE /api/reactions/queue
Очистить очередь реакций.

---

## 🔧 Коды ошибок

- `200` - Успешный запрос
- `400` - Неверные параметры запроса
- `401` - Неавторизованный доступ (неверный токен)
- `404` - Ресурс не найден
- `500` - Внутренняя ошибка сервера

## 📝 Примеры использования

### Python
```python
import requests

headers = {"Authorization": "Bearer YOUR_ADMIN_TOKEN"}
base_url = "http://localhost:8000/api"

# Получить все теги
response = requests.get(f"{base_url}/tags", headers=headers)
tags = response.json()

# Создать новый тег
new_tag = {
    "tag": "#новость",
    "emoji": "📰",
    "delay": 0,
    "match_mode": "prefix",
    "require_photo": False,
    "moderation_enabled": False
}
response = requests.post(f"{base_url}/tags", json=new_tag, headers=headers)

# Одобрить модерацию
response = requests.post(f"{base_url}/moderation/abc123/approve", headers=headers)
```

### cURL
```bash
# Получить статистику
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     http://localhost:8000/api/stats

# Создать тег
curl -X POST \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"tag":"#тест","emoji":"🧪","delay":0,"match_mode":"prefix","require_photo":false,"moderation_enabled":false}' \
     http://localhost:8000/api/tags

# Одобрить модерацию
curl -X POST \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     http://localhost:8000/api/moderation/abc123/approve
```

---

## 🚀 Развертывание

Для развертывания в продакшен режиме см. файл `DEPLOYMENT.md`.
