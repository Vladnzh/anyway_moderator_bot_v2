# Массовая рассылка - Краткая инструкция

## Быстрый старт

### 1. Настройка переменных окружения

Добавьте в `.env`:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

### 2. Основные эндпоинты

#### Предпросмотр получателей
```bash
POST /api/broadcast/preview
```
Показывает список пользователей, которые получат сообщение

#### Отправка рассылки
```bash
POST /api/broadcast/send
```
Отправляет сообщение всем отфильтрованным пользователям

### 3. Примеры использования

#### Простой пример (curl)

**Шаг 1: Предпросмотр**
```bash
curl -X POST http://localhost:8000/api/broadcast/preview \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "supabase_query": "select=tg_user_id,username,email&tg_user_id=not.is.null"
  }'
```

**Шаг 2: Отправка (если все ок)**
```bash
curl -X POST http://localhost:8000/api/broadcast/send \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Привет! Это сообщение от бота.",
    "supabase_query": "select=tg_user_id,username&tg_user_id=not.is.null",
    "parse_mode": "HTML"
  }'
```

## Формат Supabase Query

Используется PostgREST синтаксис:

### Базовые примеры

**Все пользователи с Telegram:**
```
select=tg_user_id,username,email&tg_user_id=not.is.null
```

**Пользователи с email от gmail:**
```
select=tg_user_id,username&tg_user_id=not.is.null&email=like.*@gmail.com
```

**Новые пользователи (с 1 января 2024):**
```
select=tg_user_id,username&tg_user_id=not.is.null&created_at=gte.2024-01-01
```

### Операторы фильтрации

| Оператор | Описание | Пример |
|----------|----------|--------|
| `eq` | Равно | `status=eq.active` |
| `neq` | Не равно | `status=neq.banned` |
| `gt` | Больше | `age=gt.18` |
| `gte` | Больше или равно | `created_at=gte.2024-01-01` |
| `lt` | Меньше | `age=lt.65` |
| `lte` | Меньше или равно | `created_at=lte.2024-12-31` |
| `like` | SQL LIKE | `email=like.*@gmail.com` |
| `ilike` | LIKE без учета регистра | `name=ilike.*john*` |
| `is` | NULL проверка | `deleted_at=is.null` |
| `not.is` | NOT NULL | `tg_user_id=not.is.null` |

## Форматирование сообщений

### HTML (рекомендуется)
```json
{
  "message": "<b>Важно!</b>\n\nВаш аккаунт <i>активирован</i>.",
  "parse_mode": "HTML"
}
```

**Доступные теги:**
- `<b>текст</b>` - жирный
- `<i>текст</i>` - курсив
- `<u>текст</u>` - подчеркнутый
- `<code>код</code>` - моноширинный
- `<a href="url">ссылка</a>` - ссылка

### Markdown
```json
{
  "message": "**Важно!**\n\nВаш аккаунт _активирован_.",
  "parse_mode": "Markdown"
}
```

### Обычный текст
```json
{
  "message": "Простое сообщение без форматирования",
  "parse_mode": null
}
```

## Примеры реальных сценариев

### Уведомление всех активных пользователей
```bash
curl -X POST http://localhost:8000/api/broadcast/send \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "<b>Обновление платформы!</b>\n\nМы добавили новые функции. Проверьте их в личном кабинете.",
    "supabase_query": "select=tg_user_id&tg_user_id=not.is.null&status=eq.active",
    "parse_mode": "HTML"
  }'
```

### Напоминание неактивным пользователям (не заходили >30 дней)
```bash
curl -X POST http://localhost:8000/api/broadcast/send \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Скучаем по вам! 😊\n\nВернитесь на платформу и получите бонус.",
    "supabase_query": "select=tg_user_id&tg_user_id=not.is.null&last_login=lt.2024-11-01",
    "parse_mode": null
  }'
```

### Специальное предложение для VIP пользователей
```bash
curl -X POST http://localhost:8000/api/broadcast/send \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "🎉 <b>Эксклюзивно для VIP!</b>\n\nСпециальное предложение только для вас.",
    "supabase_query": "select=tg_user_id&tg_user_id=not.is.null&subscription_tier=eq.vip",
    "parse_mode": "HTML"
  }'
```

## Проверка результатов

Response содержит полную статистику:
```json
{
  "success": true,
  "message": "Рассылка завершена: отправлено 95, ошибок 5",
  "data": {
    "total": 100,
    "success": 95,
    "failed": 5,
    "failed_users": [
      {
        "tg_user_id": "123456",
        "username": "user1",
        "error": "Forbidden: bot was blocked by the user"
      }
    ]
  }
}
```

## Важные замечания

1. **Всегда используйте preview** перед отправкой!
2. **Проверяйте количество** получателей
3. **Учитывайте rate limits** Telegram (не более 30 сообщений в секунду)
4. **Анализируйте failed_users** для понимания проблем

## Полная документация

Подробная документация с расширенными примерами: [BROADCAST_GUIDE.md](./BROADCAST_GUIDE.md)

## Поддержка

При возникновении проблем проверьте:
1. Корректность `SUPABASE_URL` и `SUPABASE_KEY`
2. Наличие поля `tg_user_id` в таблице users
3. Права доступа к таблице (RLS policies)
4. Логи админ-панели: `docker logs moderator-bot-admin`
