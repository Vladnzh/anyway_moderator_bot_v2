# 🔗 Привязка аккаунтов Telegram

Функционал привязки аккаунтов позволяет связывать Telegram пользователей с аккаунтами в вашей внешней системе через специальные коды.

## 🚀 Как это работает

1. **Ваш бэкенд** генерирует уникальный код привязки для пользователя
2. **Пользователь** отправляет код боту через команду `/start <КОД>` или просто текстовым сообщением
3. **Бот** отправляет запрос на ваш бэкенд с данными пользователя и HMAC подписью
4. **Ваш бэкенд** проверяет подпись и привязывает аккаунты

## 🔧 Настройка

### 1. Настройте секретный ключ

```bash
./setup-shared-secret.sh
```

Этот ключ будет использоваться для создания HMAC-SHA256 подписи запросов.

### 2. Настройте URL серверов

```bash
./setup-urls.sh
```

Выберите подходящий вариант:
- **Локальная разработка** - ADMIN: `http://localhost:8000`, FRONTEND: `http://localhost:3000`
- **Docker контейнер** - ADMIN: `http://admin:8000`, FRONTEND: `http://localhost:3000`
- **Внешние серверы** - укажите свои домены

### 3. Настройте переменные окружения

Или настройте вручную в `.env` файле:

```env
BOT_SHARED_SECRET=your_secret_key_here
ADMIN_URL=https://your-admin.com      # Для данных о реакциях
FRONTEND_URL=https://your-frontend.com # Для привязки аккаунтов
```

> 💡 **Рекомендуется использовать скрипты** для автоматической настройки

## 📡 API Endpoints

### Привязка аккаунта (FRONTEND_URL)

Бот отправляет POST запрос на ваш фронтенд:

```
POST {FRONTEND_URL}/api/telegram/link
```

### Данные о реакциях (ADMIN_URL)

Бот отправляет POST запрос на админку **только при реальной постановке реакции**:
- При автоматической реакции (status: "approved")
- При одобрении модератором и успешной постановке реакции (status: "approved")
- При постановке реакции из очереди после одобрения (status: "approved")

**НЕ отправляется:**
- При добавлении в модерацию (без реакции)
- При отклонении модератором (реакция не ставится)

```
POST {ADMIN_URL}/api/telegram/reaction
```


### Заголовки

```
Content-Type: application/json
X-Signature: hmac_sha256_signature
```

### Тело запроса для привязки

```json
{
  "code": "user_link_code",
  "tg_user_id": "123456789",
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Тело запроса для реакции

```json
{
  "tg_user_id": "123456789",
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe",
  "tag": "#рецепт",
  "counter_name": "Рецепты",
  "emoji": "🔥",
  "chat_id": "-1001234567890",
  "message_id": "12345",
  "text": "Вот мой #рецепт торта",
  "caption": "",
  "thread_name": "Кулинария",
  "has_photo": true,
  "has_video": false,
  "media_file_ids": ["BAADBAADrwADBREAAYag2eLPt_OAAI"],
  "timestamp": "2024-01-15T10:30:00.123456"
}
```

### Поле status в запросах

Все запросы содержат поле `status` со значением:
- **"approved"** - реакция поставлена (автоматически или после одобрения модератором)

```json
{
  "tg_user_id": "123456789",
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe",
  "tag": "#рецепт",
  "counter_name": "Рецепты",
  "emoji": "🔥",
  "chat_id": "-1001234567890",
  "message_id": "12345",
  "text": "Вот мой #рецепт торта",
  "caption": "",
  "thread_name": "Кулинария",
  "has_photo": true,
  "has_video": false,
  "media_file_ids": ["BAADBAADrwADBREAAYag2eLPt_OAAI"],
  "status": "approved",
  "timestamp": "2024-01-15T10:30:00.123456"
}
```

### Проверка подписи

```python
import hmac
import hashlib
import json

def verify_signature(body: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

# Пример использования
request_body = json.dumps(request_data, separators=(',', ':'), ensure_ascii=False)
is_valid = verify_signature(request_body, signature, BOT_SHARED_SECRET)
```

## 📋 Ответы бэкенда

### ✅ Успешная привязка (200)

```json
{
  "status": "linked"
}
```

**Ответ бота:** "✅ Акаунт прив'язано"

### ❌ Неверный или истекший код (400)

```json
{
  "error": "invalid_or_expired_code"
}
```

**Ответ бота:** "❌ Код невірний або строк дії минув"

### ⚠️ Telegram уже привязан (409)

```json
{
  "error": "tg_already_linked_to_another_user"
}
```

**Ответ бота:** "⚠️ Цей Telegram вже прив'язаний до іншого акаунта"

### 🚫 Другие ошибки

**Ответ бота:** "🚫 Сталася помилка. Спробуй ще раз"

## 💡 Примеры использования

### Команда /start с кодом

```
/start ABC123DEF456
```

### Текстовое сообщение с кодом

```
ABC123DEF456
```

Бот автоматически определяет коды по следующим критериям:
- Длина до 100 символов
- Один токен без пробелов
- Содержит цифры или символы `-`, `_`
- Не содержит хештеги
- Не является командой

## 🔒 Безопасность

- Все запросы подписываются HMAC-SHA256
- Секретный ключ должен быть одинаковым у бота и бэкенда
- Рекомендуется использовать HTTPS для бэкенда
- Коды должны иметь ограниченное время жизни
- Коды должны быть одноразовыми

## 🛠️ Пример бэкенда (FastAPI)

```python
from fastapi import FastAPI, HTTPException, Header
import hmac
import hashlib
import json

app = FastAPI()

BOT_SHARED_SECRET = "your_secret_key"

def verify_signature(body: str, signature: str) -> bool:
    expected = hmac.new(
        BOT_SHARED_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@app.post("/api/telegram/link")
async def link_telegram(
    data: dict,
    x_signature: str = Header(alias="X-Signature")
):
    # Проверяем подпись
    body = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    if not verify_signature(body, x_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    code = data.get("code")
    tg_user_id = data.get("tg_user_id")
    
    # Ваша логика проверки кода и привязки аккаунта
    if not is_valid_code(code):
        raise HTTPException(
            status_code=400, 
            detail={"error": "invalid_or_expired_code"}
        )
    
    if is_telegram_already_linked(tg_user_id):
        raise HTTPException(
            status_code=409,
            detail={"error": "tg_already_linked_to_another_user"}
        )
    
    # Привязываем аккаунт
    link_account(code, tg_user_id, data)
    
    return {"status": "linked"}

@app.post("/api/telegram/reaction")
async def handle_reaction(
    data: dict,
    x_signature: str = Header(alias="X-Signature")
):
    # Проверяем подпись
    body = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    if not verify_signature(body, x_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Обрабатываем данные о реакции
    tg_user_id = data.get("tg_user_id")
    tag = data.get("tag")
    counter_name = data.get("counter_name")
    emoji = data.get("emoji")
    
    # Ваша логика обработки реакции
    # Например: начисление очков, обновление статистики и т.д.
    process_user_reaction(tg_user_id, tag, counter_name, emoji, data)
    
    return {"status": "processed"}
```

## 🧪 Тестирование

### Быстрый тест с готовым сервером

1. **Запустите тестовый сервер:**
   ```bash
   python test_link_server.py
   ```

2. **Сгенерируйте код:**
   Откройте http://localhost:3000/generate-code

3. **Настройте бота для тестирования:**
   ```bash
   # Используйте скрипты
   ./setup-shared-secret.sh  # Выберите "2" и введите: test_secret_key_123456789
   ./setup-urls.sh          # Выберите "4" и введите URL тестового сервера
   
   # Или вручную в .env файле
   BOT_SHARED_SECRET=test_secret_key_123456789
   ADMIN_URL=http://localhost:3000
   FRONTEND_URL=http://localhost:3000
   ```

4. **Отправьте код боту:**
   `/start <СГЕНЕРИРОВАННЫЙ_КОД>`

5. **Проверьте результат:**
   - Сначала появится "⏳ Обробляю запит..."
   - Затем бот должен ответить "✅ Акаунт прив'язано"
   - В логах сервера появится информация о привязке

### Ручное тестирование

1. Настройте тестовый бэкенд
2. Создайте тестовый код привязки
3. Отправьте код боту: `/start TEST123`
4. Проверьте логи бота и бэкенда

## 📝 Логирование

Бот логирует все попытки привязки:

```
🔗 Попытка привязки аккаунта: user_id=123456789, code=ABC123DE...
✅ Аккаунт успешно привязан: user_id=123456789
❌ Ошибка привязки: invalid_or_expired_code
```

## 🎯 Процесс привязки

1. **Пользователь отправляет код:** `/start ABC123` или `ABC123`
2. **Бот показывает индикатор:** "⏳ Обробляю запит..."
3. **Бот отправляет запрос** на ваш бэкенд с HMAC подписью
4. **Бот удаляет индикатор** и показывает результат
5. **Результат отображается** на украинском языке
