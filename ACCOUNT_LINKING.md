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

### 2. Настройте URL бэкенда

```bash
./setup-backend-url.sh
```

Выберите подходящий вариант:
- **Локальная разработка** - `http://localhost:8000`
- **Docker контейнер** - `http://admin:8000`
- **Внешний сервер** - `https://your-domain.com`

### 3. Настройте переменные окружения

Или настройте вручную в `.env` файле:

```env
BOT_SHARED_SECRET=your_secret_key_here
BACKEND_URL=https://your-backend.com  # По умолчанию http://localhost:8000
```

> 💡 **Рекомендуется использовать скрипты** для автоматической настройки

## 📡 API Endpoint

Бот отправляет POST запрос на ваш endpoint:

```
POST /api/telegram/link
```

### Заголовки

```
Content-Type: application/json
X-Signature: hmac_sha256_signature
```

### Тело запроса

```json
{
  "code": "user_link_code",
  "tg_user_id": "123456789",
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe"
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

**Ответ бота:** "✅ Аккаунт привязан"

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
   ./setup-backend-url.sh    # Выберите "4" и введите: http://localhost:3000
   
   # Или вручную в .env файле
   BOT_SHARED_SECRET=test_secret_key_123456789
   BACKEND_URL=http://localhost:3000
   ```

4. **Отправьте код боту:**
   `/start <СГЕНЕРИРОВАННЫЙ_КОД>`

5. **Проверьте результат:**
   - Бот должен ответить "✅ Аккаунт привязан"
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
