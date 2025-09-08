e vty#!/usr/bin/env python3
"""
Простой тестовый сервер для проверки запросов от бота
"""
import json
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Test Backend Server")

# Секрет для проверки подписи (тот же, что в .env)
BOT_SHARED_SECRET = "9cc435be827c05862919e4a7534fb1d659570aa7bc873c6f138cb60204de7457"

def verify_signature(data: str, signature: str) -> bool:
    """Проверить HMAC подпись"""
    expected = hmac.new(
        BOT_SHARED_SECRET.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/api/telegram/reaction")
async def receive_reaction(request: Request):
    """Получить данные о реакции от бота"""
    try:
        # Получаем тело запроса
        body = await request.body()
        data = body.decode('utf-8')
        
        # Получаем подпись из заголовка
        signature = request.headers.get('X-Signature', '')
        
        print(f"\n🔥 ПОЛУЧЕН ЗАПРОС О РЕАКЦИИ:")
        print(f"📝 Данные: {data}")
        print(f"🔐 Подпись: {signature[:16]}...")
        
        # Проверяем подпись
        if not verify_signature(data, signature):
            print("❌ Неверная подпись!")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        print("✅ Подпись верна!")
        
        # Парсим JSON
        reaction_data = json.loads(data)
        
        print(f"👤 Пользователь: {reaction_data.get('username', 'N/A')} (ID: {reaction_data.get('tg_user_id', 'N/A')})")
        print(f"🏷️ Тег: {reaction_data.get('tag', 'N/A')}")
        print(f"📊 Счетчик: {reaction_data.get('counter_name', 'N/A')}")
        print(f"😀 Эмодзи: {reaction_data.get('emoji', 'N/A')}")
        print(f"💬 Чат: {reaction_data.get('chat_id', 'N/A')}")
        print(f"📨 Сообщение: {reaction_data.get('message_id', 'N/A')}")
        print(f"📄 Текст: {reaction_data.get('text', 'N/A')}")
        print(f"🎭 Статус: {reaction_data.get('status', 'N/A')}")
        print(f"📷 Фото: {reaction_data.get('has_photo', False)}")
        print(f"🎥 Видео: {reaction_data.get('has_video', False)}")
        print(f"⏰ Время: {reaction_data.get('timestamp', 'N/A')}")
        
        return JSONResponse({
            "status": "success",
            "message": "Данные о реакции получены",
            "received_data": reaction_data
        })
        
    except json.JSONDecodeError:
        print("❌ Ошибка парсинга JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Test Backend Server для проверки запросов от бота"}

if __name__ == "__main__":
    print("🚀 Запуск тестового бэкенд сервера на http://localhost:3002")
    print("📡 Endpoint: POST /api/telegram/reaction")
    print("🔐 Проверка HMAC подписи включена")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=3002, log_level="info")
