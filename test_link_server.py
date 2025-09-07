#!/usr/bin/env python3
"""
Простой тестовый сервер для демонстрации функционала привязки аккаунтов
"""

import hmac
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uvicorn

# Конфигурация
BOT_SHARED_SECRET = "test_secret_key_123456789"  # Используйте тот же секрет что и в боте
TEST_CODES = {}  # Хранилище тестовых кодов

app = FastAPI(title="Test Account Linking Server")

class LinkRequest(BaseModel):
    code: str
    tg_user_id: str
    username: str = ""
    first_name: str = ""
    last_name: str = ""

def verify_signature(body: str, signature: str) -> bool:
    """Проверить HMAC подпись"""
    expected = hmac.new(
        BOT_SHARED_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@app.get("/")
async def root():
    """Главная страница с информацией"""
    return {
        "message": "Test Account Linking Server",
        "endpoints": {
            "POST /api/telegram/link": "Привязка Telegram аккаунта",
            "POST /api/telegram/reaction": "Обработка данных о реакциях",
            "POST /generate-code": "Генерация тестового кода",
            "GET /codes": "Список активных кодов"
        }
    }

@app.post("/generate-code")
async def generate_test_code(user_id: str = "test_user_123"):
    """Генерация тестового кода привязки"""
    code = str(uuid.uuid4())[:8].upper()
    expires_at = datetime.now() + timedelta(minutes=5)
    
    TEST_CODES[code] = {
        "user_id": user_id,
        "expires_at": expires_at,
        "used": False
    }
    
    return {
        "code": code,
        "user_id": user_id,
        "expires_at": expires_at.isoformat(),
        "message": f"Отправьте боту: /start {code}"
    }

@app.get("/codes")
async def list_codes():
    """Список активных кодов"""
    now = datetime.now()
    active_codes = {}
    
    for code, data in TEST_CODES.items():
        if not data["used"] and data["expires_at"] > now:
            active_codes[code] = {
                "user_id": data["user_id"],
                "expires_at": data["expires_at"].isoformat(),
                "expires_in_seconds": int((data["expires_at"] - now).total_seconds())
            }
    
    return {
        "active_codes": active_codes,
        "total": len(active_codes)
    }

@app.post("/api/telegram/link")
async def link_telegram(
    data: LinkRequest,
    x_signature: str = Header(alias="X-Signature")
):
    """Привязка Telegram аккаунта"""
    
    # Проверяем подпись
    body = json.dumps(data.dict(), separators=(',', ':'), ensure_ascii=False)
    if not verify_signature(body, x_signature):
        print(f"❌ Неверная подпись: {x_signature}")
        print(f"📝 Тело запроса: {body}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    print(f"✅ Подпись проверена успешно")
    print(f"📝 Данные: {data.dict()}")
    
    # Проверяем код
    if data.code not in TEST_CODES:
        print(f"❌ Код не найден: {data.code}")
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_or_expired_code"}
        )
    
    code_data = TEST_CODES[data.code]
    
    # Проверяем срок действия
    if datetime.now() > code_data["expires_at"]:
        print(f"❌ Код истек: {data.code}")
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_or_expired_code"}
        )
    
    # Проверяем, не использован ли код
    if code_data["used"]:
        print(f"❌ Код уже использован: {data.code}")
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_or_expired_code"}
        )
    
    # Помечаем код как использованный
    code_data["used"] = True
    code_data["linked_tg_user"] = {
        "tg_user_id": data.tg_user_id,
        "username": data.username,
        "first_name": data.first_name,
        "last_name": data.last_name,
        "linked_at": datetime.now().isoformat()
    }
    
    print(f"✅ Аккаунт привязан: {data.tg_user_id} -> {code_data['user_id']}")
    
    return {"status": "linked"}

@app.post("/api/telegram/reaction")
async def handle_reaction(
    data: dict,
    x_signature: str = Header(alias="X-Signature")
):
    """Обработка данных о реакции"""
    
    # Проверяем подпись
    body = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    if not verify_signature(body, x_signature):
        print(f"❌ Неверная подпись для реакции: {x_signature}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    print(f"✅ Получена реакция от пользователя {data.get('tg_user_id')}")
    print(f"📝 Данные реакции:")
    print(f"   👤 Пользователь: {data.get('username', 'N/A')} ({data.get('first_name', '')} {data.get('last_name', '')})")
    print(f"   🏷️ Тег: {data.get('tag')}")
    print(f"   📊 Счетчик: {data.get('counter_name')}")
    print(f"   😀 Эмодзи: {data.get('emoji')}")
    print(f"   💬 Чат: {data.get('chat_id')}")
    print(f"   📝 Текст: {data.get('text', 'N/A')}")
    print(f"   🖼️ Медиа: фото={data.get('has_photo')}, видео={data.get('has_video')}")
    print(f"   🕐 Время: {data.get('timestamp')}")
    print("---")
    
    return {"status": "processed"}

if __name__ == "__main__":
    print("🚀 Запуск тестового сервера для привязки аккаунтов")
    print(f"🔐 Секрет: {BOT_SHARED_SECRET}")
    print()
    print("📋 Как тестировать:")
    print("1. Запустите этот сервер")
    print("2. Откройте http://localhost:3000/generate-code в браузере")
    print("3. Скопируйте сгенерированный код")
    print("4. Отправьте боту: /start <КОД>")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=3000)
