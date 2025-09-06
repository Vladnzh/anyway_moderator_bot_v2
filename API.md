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
      "reply_ok": "Зараховано! 🦋",
      "reply_need_photo": "Щоб зарахувати — додай фото і повтори з хештегом.",
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
  "require_photo": true,
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
    "total_logs": 150,
    "total_tags": 5,
    "tag_stats": [
      {"tag": "#рецепт", "count": 45},
      {"tag": "#новость", "count": 32},
      {"tag": "#фото", "count": 28}
    ],
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

## 📸 Структура медиафайлов

Объект `media_info` содержит информацию о всех типах медиафайлов в сообщении:

### Поля медиа-информации:
- `has_photo` - есть ли фото (boolean)
- `has_video` - есть ли видео (boolean)  
- `has_document` - есть ли документ (boolean)
- `has_audio` - есть ли аудио (boolean)
- `has_sticker` - есть ли стикер (boolean)
- `photo_file_id` - ID фото в Telegram (string или null)
- `video_file_id` - ID видео в Telegram (string или null)
- `document_file_id` - ID документа в Telegram (string или null)
- `audio_file_id` - ID аудио в Telegram (string или null)
- `sticker_file_id` - ID стикера в Telegram (string или null)
- `media_file_ids` - массив всех ID медиафайлов (array)
- `photo_file_ids` - массив ID фото (array)
- `video_file_ids` - массив ID видео (array)
- `document_file_ids` - массив ID документов (array)
- `audio_file_ids` - массив ID аудио (array)
- `sticker_file_ids` - массив ID стикеров (array)
- `media_group_id` - ID медиагруппы (альбома) или null (string или null)
- `media_type` - строка с типами медиа через запятую (string)

### Примеры значений `media_type`:
- `"photo"` - только фото
- `"video"` - только видео
- `"photo, video"` - фото и видео в одном сообщении
- `"document"` - документ
- `"audio"` - аудиофайл
- `"sticker"` - стикер
- `""` - нет медиафайлов

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
        "has_video": false,
        "has_document": false,
        "has_audio": false,
        "has_sticker": false,
        "photo_file_id": "AgACAgIAAxkBAAIBYmXvZ...",
        "video_file_id": null,
        "document_file_id": null,
        "audio_file_id": null,
        "sticker_file_id": null,
        "media_file_ids": ["AgACAgIAAxkBAAIBYmXvZ..."],
        "photo_file_ids": ["AgACAgIAAxkBAAIBYmXvZ..."],
        "video_file_ids": [],
        "document_file_ids": [],
        "audio_file_ids": [],
        "sticker_file_ids": [],
        "media_group_id": null,
        "media_type": "photo"
      },
      "thread_name": "Кулинария",
      "status": "pending",
      "created_at": "2025-09-05T18:30:00",
      "updated_at": "2025-09-05T18:30:00"
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
      "id": 1,
      "moderation_id": "abc123",
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
    "require_photo": True,
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
     -d '{"tag":"#тест","emoji":"🧪","delay":0,"match_mode":"prefix","require_photo":true,"moderation_enabled":false}' \
     http://localhost:8000/api/tags

# Одобрить модерацию
curl -X POST \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
     http://localhost:8000/api/moderation/abc123/approve
```

---

## 🚀 Развертывание

Для развертывания в продакшен режиме см. файл `DEPLOYMENT.md`.
