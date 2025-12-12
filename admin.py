# -*- coding: utf-8 -*-
import os, json, datetime, asyncio, uuid, logging, hmac, hashlib
try:
    from typing import Literal, List, Dict, Any, Optional
except ImportError:
    # Для старых версий Python
    pass
from pathlib import Path
import httpx
import aiohttp
from database import db
from logger_config import setup_logging, log_bot_event
from supabase_client import SupabasePool, query_users_for_broadcast
from fastapi import FastAPI, Request, Form, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Глобальный семафор для ограничения параллельных реакций (исправляет баг с быстрым апрувом)
reaction_semaphore = asyncio.Semaphore(3)  # Максимум 3 одновременные реакции

# Загружаем переменные окружения
load_dotenv()

# Получаем токены из переменных окружения
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_SHARED_SECRET = os.getenv("BOT_SHARED_SECRET")
ADMIN_URL = os.getenv("ADMIN_URL", "http://localhost:8000")

if not ADMIN_TOKEN:
    print("⚠️ ADMIN_TOKEN не установлен, используется 'changeme'")
    ADMIN_TOKEN = "changeme"
else:
    print("🔑 ADMIN_TOKEN найден: {}...{}".format(ADMIN_TOKEN[:6], ADMIN_TOKEN[-4:]))

if not BOT_TOKEN:
    print("⚠️ BOT_TOKEN не установлен! Установите его в .env файле или переменной окружения")

# Настраиваем красивое логирование
setup_logging("ADMIN PANEL", "INFO")
logger = logging.getLogger('ADMIN')

# ---- Функции для работы с Supabase через asyncpg ----
# Старая функция удалена, теперь используем supabase_client.query_users_for_broadcast()

# ---- модели ----
class TagConfig(BaseModel):
    id: str = ""  # Уникальный ID тега
    tag: str
    emoji: str
    delay: int = 0
    match_mode: Literal["equals", "prefix"] = "equals"
    require_photo: bool = True  # Требовать медиафайл (фото или видео)
    reply_ok: str = "Зараховано! 🦋"
    reply_need_photo: str = "Щоб зарахувати — додай фото і повтори з хештегом."
    thread_name: str = ""  # Название треда (пустое = любой тред)
    reply_duplicate: str = ""  # Сообщение при дублировании фото (пустое = без сообщения)
    moderation_enabled: bool = False  # Требовать подтверждение модератора
    reply_pending: str = ""  # Сообщение о постановке в очередь модерации
    counter_name: str = ""  # Название счетчика для отображения в модерации

class ModerationItem(BaseModel):
    id: str  # Уникальный ID записи модерации
    chat_id: int
    message_id: int
    user_id: int
    username: str
    tag: str
    emoji: str
    text: str
    caption: str
    media_info: Optional[Dict[str, Any]] = None
    thread_name: str
    counter_name: str = ""  # Название счетчика тега
    created_at: str
    status: Literal["pending", "approved", "rejected"] = "pending"

class Config(BaseModel):
    tags: List[TagConfig] = []

class TagUpdate(BaseModel):
    tag: str
    emoji: str
    delay: int = 0
    match_mode: Literal["equals", "prefix"] = "equals"
    require_photo: bool = True
    reply_ok: str = ""
    reply_need_photo: str = ""
    thread_name: str = ""
    reply_duplicate: str = ""
    moderation_enabled: bool = False
    reply_pending: str = ""
    counter_name: str = ""

class ApiResponse(BaseModel):
    success: bool
    message: str = ""
    data: Any = None

# ---- FastAPI приложение ----
app = FastAPI(title="Moderator Bot Admin API", version="2.0")

# Авторизация
def require_admin(token: str = Form(...)):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

def require_api_admin(request: Request):
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = authorization[7:]  # Убираем "Bearer "
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# ---- API Endpoints ----

@app.get("/api/tags")
def get_tags(request: Request, _: bool = Depends(require_api_admin)):
    """Получить все теги"""
    try:
        tags = db.get_tags()
        return ApiResponse(success=True, data=tags)
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.post("/api/tags")
def create_tag(tag: TagUpdate, _: bool = Depends(require_api_admin)):
    """Создать новый тег"""
    try:
        # Проверяем, что тег не существует
        existing_tags = db.get_tags()
        if any(t['tag'].lower() == tag.tag.strip().lower() for t in existing_tags):
            return ApiResponse(success=False, message="Тег уже существует")
        
        tag_data = {
            'tag': tag.tag.strip().lower(),
            'emoji': tag.emoji.strip(),
            'delay': max(0, min(60, tag.delay)),
            'match_mode': tag.match_mode,
            'require_photo': tag.require_photo,
            'reply_ok': tag.reply_ok.strip(),
            'reply_need_photo': tag.reply_need_photo.strip(),
            'thread_name': tag.thread_name.strip(),
            'reply_duplicate': tag.reply_duplicate.strip(),
            'moderation_enabled': tag.moderation_enabled,
            'reply_pending': tag.reply_pending.strip(),
            'counter_name': tag.counter_name.strip()
        }
        
        tag_id = db.create_tag(tag_data)
        created_tag = db.get_tag_by_id(tag_id)
        return ApiResponse(success=True, message="Тег создан", data=created_tag)
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.put("/api/tags/{tag_id}")
def update_tag(tag_id: str, tag: TagUpdate, _: bool = Depends(require_api_admin)):
    """Обновить существующий тег по ID"""
    try:
        # Проверяем существование тега
        existing_tag = db.get_tag_by_id(tag_id)
        if not existing_tag:
            return ApiResponse(success=False, message=f"Тег с ID {tag_id} не найден")
        
        tag_data = {
            'tag': tag.tag.strip().lower(),
            'emoji': tag.emoji.strip(),
            'delay': max(0, min(60, tag.delay)),
            'match_mode': tag.match_mode,
            'require_photo': tag.require_photo,
            'reply_ok': tag.reply_ok.strip(),
            'reply_need_photo': tag.reply_need_photo.strip(),
            'thread_name': tag.thread_name.strip(),
            'reply_duplicate': tag.reply_duplicate.strip(),
            'moderation_enabled': tag.moderation_enabled,
            'reply_pending': tag.reply_pending.strip(),
            'counter_name': tag.counter_name.strip()
        }
        
        success = db.update_tag(tag_id, tag_data)
        if success:
            updated_tag = db.get_tag_by_id(tag_id)
            return ApiResponse(success=True, message="Тег обновлен", data=updated_tag)
        else:
            return ApiResponse(success=False, message="Не удалось обновить тег")
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.delete("/api/tags/{tag_id}")
def delete_tag(tag_id: str, _: bool = Depends(require_api_admin)):
    """Удалить тег по ID"""
    try:
        # Получаем тег перед удалением для сообщения
        existing_tag = db.get_tag_by_id(tag_id)
        if not existing_tag:
            return ApiResponse(success=False, message=f"Тег с ID {tag_id} не найден")
        
        success = db.delete_tag(tag_id)
        if success:
            return ApiResponse(success=True, message=f"Тег {existing_tag['tag']} удален")
        else:
            return ApiResponse(success=False, message="Не удалось удалить тег")
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.get("/api/logs")
def get_logs(
    tag: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    _: bool = Depends(require_api_admin)
):
    """Получить логи с фильтрацией"""
    try:
        logs = db.get_logs(tag=tag, limit=limit)
        return ApiResponse(success=True, data=logs)
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.delete("/api/logs")
def clear_logs(_: bool = Depends(require_api_admin)):
    """Очистить все логи и связанные очереди"""
    try:
        with db.get_connection() as conn:
            # Очищаем логи
            cursor = conn.execute("DELETE FROM logs")
            deleted_logs = cursor.rowcount
            
            # Очищаем очередь реакций
            cursor = conn.execute("DELETE FROM reaction_queue")
            deleted_reactions = cursor.rowcount
            
            # Очищаем завершенные элементы модерации (оставляем pending)
            cursor = conn.execute("DELETE FROM moderation_queue WHERE status != 'pending'")
            deleted_moderation = cursor.rowcount
            
            conn.commit()
        
        return ApiResponse(
            success=True, 
            message=f"Очищено: {deleted_logs} логов, {deleted_reactions} реакций, {deleted_moderation} модераций",
            data={
                "deleted_logs": deleted_logs,
                "deleted_reactions": deleted_reactions,
                "deleted_moderation": deleted_moderation
            }
        )
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.get("/api/stats")
def get_stats(_: bool = Depends(require_api_admin)):
    """Получить статистику"""
    try:
        stats = db.get_stats()
        return ApiResponse(success=True, data=stats)
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

# ---- Модерация ----

@app.get("/api/moderation")
def get_moderation(_: bool = Depends(require_api_admin)):
    """Получить очередь модерации"""
    try:
        items = db.get_pending_moderation()
        return ApiResponse(success=True, data=items)
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

def create_hmac_signature(data: str, secret: str) -> str:
    """Создать HMAC-SHA256 подпись"""
    return hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

# Функция send_reaction_to_backend удалена - данные отправляются только ботом при фактической установке реакции

async def set_telegram_reaction(chat_id: int, message_id: int, emoji: str) -> bool:
    """Поставить реакцию через Telegram API с ограничением параллелизма"""
    async with reaction_semaphore:  # Ограничиваем параллельные запросы
        try:
            # Небольшая задержка между запросами для избежания rate limiting
            await asyncio.sleep(0.1)
            
            bot_token = os.getenv("BOT_TOKEN")
            if not bot_token:
                logger.error("❌ BOT_TOKEN not found")
                return False
                
            url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
            data = {
                "chat_id": chat_id,
                "message_id": message_id,
                "reaction": json.dumps([{"type": "emoji", "emoji": emoji}])
            }
            
            # Увеличиваем timeout для стабильности
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                response = await client.post(url, data=data)
                result = response.json()
                
                if result.get("ok"):
                    logger.info("✅ Reaction {} set directly via API for message {}".format(emoji, message_id))
                    return True
                else:
                    error_desc = result.get('description', 'Unknown error')
                    logger.warning("❌ Failed to set reaction: {}".format(error_desc))
                    
                    # Если реакция недоступна, пробуем запасную
                    if "reaction_invalid" in error_desc.lower():
                        logger.info("🔄 Trying fallback reaction ❤️ for message {}".format(message_id))
                        return await set_telegram_reaction_fallback(chat_id, message_id, "❤️")
                    
                    return False
                    
        except asyncio.TimeoutError:
            logger.error("⏰ Timeout setting reaction for message {}".format(message_id))
            return False
        except Exception as e:
            logger.error("❌ Exception setting reaction for message {}: {}".format(message_id, e))
            return False

async def set_telegram_reaction_fallback(chat_id: int, message_id: int, emoji: str) -> bool:
    """Поставить запасную реакцию без семафора (уже внутри семафора)"""
    try:
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            return False
            
        url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": json.dumps([{"type": "emoji", "emoji": emoji}])
        }
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.post(url, data=data)
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"✅ Fallback reaction {emoji} set for message {message_id}")
                return True
            else:
                logger.error(f"❌ Fallback reaction failed: {result.get('description', 'Unknown error')}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Exception setting fallback reaction: {e}")
        return False

@app.post("/api/moderation/{item_id}/approve")
async def approve_moderation(item_id: str, _: bool = Depends(require_api_admin)):
    """Одобрить элемент модерации"""
    try:
        # Получаем элемент из очереди модерации
        items = db.get_pending_moderation()
        item = next((i for i in items if i['id'] == item_id), None)
        
        if not item:
            return ApiResponse(success=False, message="Элемент не найден")
        
        # Обновляем статус
        success = db.update_moderation_status(item_id, "approved")
        if not success:
            return ApiResponse(success=False, message="Не удалось обновить статус")
        
        # Пытаемся поставить реакцию напрямую
        logger.info(f"🎯 АДМИНКА: Попытка поставить реакцию {item['emoji']} к сообщению {item['message_id']}")
        reaction_success = await set_telegram_reaction(
            item['chat_id'], 
            item['message_id'], 
            item['emoji']
        )
        logger.info(f"🎯 АДМИНКА: Результат постановки реакции: {reaction_success}")
        
        # Добавляем запись в логи при одобрении
        log_data = {
            'user_id': item['user_id'],
            'username': item['username'],
            'chat_id': item['chat_id'],
            'message_id': item['message_id'],
            'trigger': item.get('tag', item.get('trigger', '')),  # Поддерживаем оба варианта
            'emoji': item['emoji'],
            'thread_name': item.get('thread_name', ''),
            'media_type': item.get('media_info', {}).get('media_type', '') if item.get('media_info') else '',
            'caption': item.get('caption', '')
        }
        db.add_log(log_data)
        
        # Данные о реакции будут отправлены ботом при фактической установке реакции
        logger.info("📊 Данные о реакции будут отправлены ботом после установки реакции")
        
        if reaction_success:
            logger.info("✅ АДМИНКА: Реакция поставлена напрямую - отправляем данные на бэкенд")
            
            # Отправляем данные на бэкенд при успешной прямой реакции
            try:
                if BOT_SHARED_SECRET and ADMIN_URL:
                    media_info = item.get('media_info', {})
                    payload = {
                        "tg_user_id": str(item['user_id']),
                        "username": item.get('username', ''),
                        "first_name": item.get('first_name', ''),
                        "last_name": item.get('last_name', ''),
                        "tag": item.get('tag', ''),
                        "counter_name": item.get('counter_name', ''),
                        "emoji": item.get('emoji', ''),
                        "chat_id": str(item['chat_id']),
                        "message_id": str(item['message_id']),
                        "text": item.get('text', ''),
                        "caption": item.get('caption', ''),
                        "thread_name": item.get('thread_name', ''),
                        "has_photo": media_info.get('has_photo', False),
                        "has_video": media_info.get('has_video', False),
                        "media_file_ids": media_info.get('media_file_ids', []),
                        "status": "approved",
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    
                    json_data = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
                    signature = create_hmac_signature(json_data, BOT_SHARED_SECRET)
                    
                    logger.info(f"📊 АДМИНКА: Отправляем данные о прямой реакции на {ADMIN_URL}/api/telegram/reaction")
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{ADMIN_URL}/api/telegram/reaction",
                            data=json_data,
                            headers={
                                "Content-Type": "application/json",
                                "X-Signature": signature
                            },
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status == 200:
                                response_data = await response.json()
                                logger.info(f"✅ АДМИНКА: Данные о прямой реакции отправлены успешно")
                            else:
                                response_text = await response.text()
                                logger.warning(f"⚠️ АДМИНКА: Бэкенд вернул код {response.status}: {response_text}")
                else:
                    logger.warning("⚠️ АДМИНКА: BOT_SHARED_SECRET или ADMIN_URL не настроены")
            except Exception as e:
                logger.error(f"❌ АДМИНКА: Ошибка отправки данных о прямой реакции: {e}")
            
            return ApiResponse(success=True, message="Элемент одобрен, реакция поставлена")
        else:
            # Добавляем в очередь реакций как фоллбэк
            logger.info("⏳ АДМИНКА: Реакция не поставлена, добавляем в очередь для бота")
            db.add_reaction_queue(item_id, item['chat_id'], item['message_id'], item['emoji'])
            return ApiResponse(success=True, message="Элемент одобрен, реакция будет поставлена при следующем сообщении")
            
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.post("/api/moderation/{item_id}/reject")
async def reject_moderation(item_id: str, _: bool = Depends(require_api_admin)):
    """Отклонить элемент модерации"""
    try:
        # Получаем элемент перед отклонением для логирования
        items = db.get_pending_moderation()
        item = next((i for i in items if i['id'] == item_id), None)
        
        if not item:
            return ApiResponse(success=False, message="Элемент не найден")
        
        success = db.update_moderation_status(item_id, "rejected")
        if success:
            # НЕ отправляем данные при отклонении - реакция не ставится
            
            # Добавляем запись в логи при отклонении (с эмодзи ❌)
            log_data = {
                'user_id': item['user_id'],
                'username': item['username'],
                'chat_id': item['chat_id'],
                'message_id': item['message_id'],
                'trigger': item.get('tag', item.get('trigger', '')),  # Поддерживаем оба варианта
                'emoji': '❌',  # Специальный эмодзи для отклоненных
                'thread_name': item.get('thread_name', ''),
                'media_type': item.get('media_info', {}).get('media_type', '') if item.get('media_info') else '',
                'caption': item.get('caption', '')
            }
            db.add_log(log_data)
            
            return ApiResponse(success=True, message="Элемент отклонен")
        else:
            return ApiResponse(success=False, message="Не удалось обновить статус")
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

# ---- Media API ----
@app.get("/api/media/file/{file_id}")
async def get_media_file(file_id: str, _: bool = Depends(require_api_admin)):
    """Получить медиафайл по file_id через Telegram Bot API"""
    try:
        if not BOT_TOKEN:
            return {"success": False, "message": "BOT_TOKEN не настроен"}
            
        async with httpx.AsyncClient() as client:
            # Получаем информацию о файле
            file_response = await client.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                params={"file_id": file_id}
            )
            
            if file_response.status_code != 200:
                return {"success": False, "message": "Файл не найден"}
                
            file_data = file_response.json()
            if not file_data.get("ok"):
                return {"success": False, "message": file_data.get("description", "Ошибка получения файла")}
                
            file_path = file_data["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            
            # Определяем тип медиа по расширению
            media_type = "photo"
            if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                media_type = "video"
            elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                media_type = "photo"
                
            return {
                "success": True,
                "file_url": file_url,
                "file_path": file_path,
                "media_type": media_type,
                "file_size": file_data["result"].get("file_size", 0)
            }
            
    except Exception as e:
        logger.error(f"Ошибка получения медиафайла {file_id}: {e}")
        return {"success": False, "message": str(e)}

# ---- Direct Reaction API ----
class ReactionRequest(BaseModel):
    chat_id: int
    message_id: int
    emoji: str

# ---- Модели для массовой рассылки ----
class BroadcastRequest(BaseModel):
    message: str  # Текст сообщения
    filters: Optional[Dict[str, Any]] = None  # Фильтры пользователей (TODO: добавить поддержку)
    parse_mode: Optional[str] = None  # HTML, Markdown или None

class UserFilterResponse(BaseModel):
    success: bool
    users: List[Dict[str, Any]] = []
    count: int = 0
    message: str = ""

@app.post("/api/reactions/set")
async def set_reaction_direct(request: ReactionRequest, _: bool = Depends(require_api_admin)):
    """Прямая постановка реакции к сообщению"""
    try:
        success = await set_telegram_reaction(
            chat_id=request.chat_id,
            message_id=request.message_id,
            emoji=request.emoji
        )
        
        # Данные о реакции будут отправлены ботом при фактической установке реакции
        logger.debug("📊 Данные о прямой реакции будут отправлены ботом после установки")
        
        if success:
            return ApiResponse(success=True, message=f"Реакция {request.emoji} поставлена к сообщению {request.message_id}")
        else:
            return ApiResponse(success=False, message="Не удалось поставить реакцию")
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.delete("/api/reactions/remove")
async def remove_reaction_direct(request: ReactionRequest, _: bool = Depends(require_api_admin)):
    """Прямое удаление реакции с сообщения"""
    try:
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            return ApiResponse(success=False, message="BOT_TOKEN not found")
            
        url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
        data = {
            "chat_id": request.chat_id,
            "message_id": request.message_id,
            "reaction": json.dumps([])  # Пустой массив удаляет все реакции
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            result = response.json()
            
            if result.get("ok"):
                print(f"✅ Reactions removed from message {request.message_id}")
                return ApiResponse(success=True, message=f"Реакции удалены с сообщения {request.message_id}")
            else:
                return ApiResponse(success=False, message=f"Ошибка: {result.get('description', 'Unknown error')}")
                
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.get("/api/reactions/queue")
def get_reaction_queue(_: bool = Depends(require_api_admin)):
    """Получить текущую очередь реакций"""
    try:
        queue = db.get_reaction_queue()
        return ApiResponse(success=True, data=queue)
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

@app.delete("/api/reactions/queue")
def clear_reaction_queue(_: bool = Depends(require_api_admin)):
    """Очистить очередь реакций"""
    try:
        db.clear_reaction_queue()
        return ApiResponse(success=True, message="Очередь реакций очищена")
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

# ---- API для массовой рассылки ----

@app.post("/api/broadcast/preview")
async def preview_broadcast_users(request: Request, _: bool = Depends(require_api_admin)):
    """Получить список пользователей которые получат сообщение (предпросмотр)"""
    try:
        # Проверяем доступность Supabase
        if not SupabasePool.is_available():
            return UserFilterResponse(
                success=False,
                message="Supabase не настроен. Проверьте переменные окружения DB_HOST, DB_PASSWORD и т.д.",
                users=[],
                count=0
            )

        data = await request.json()
        filters = data.get("filters", None)  # TODO: Реализовать фильтры

        # Получаем пользователей через asyncpg
        users = await query_users_for_broadcast(filters=filters)

        if not users:
            return UserFilterResponse(
                success=True,
                users=[],
                count=0,
                message="Пользователи с привязанным Telegram не найдены"
            )

        # Преобразуем в нужный формат
        telegram_users = []
        for user in users:
            telegram_users.append({
                "tg_user_id": str(user.get("tg_user_id", "")),
                "username": user.get("username", ""),
                "email": user.get("email", ""),
                "full_name": user.get("full_name", "")
            })

        return UserFilterResponse(
            success=True,
            users=telegram_users,
            count=len(telegram_users),
            message=f"Найдено {len(telegram_users)} пользователей с привязанным Telegram"
        )

    except Exception as e:
        logger.error(f"❌ Ошибка предпросмотра рассылки: {e}")
        return UserFilterResponse(
            success=False,
            message=str(e),
            users=[],
            count=0
        )

@app.post("/api/broadcast/send")
async def send_broadcast(request: BroadcastRequest, _: bool = Depends(require_api_admin)):
    """Отправить массовое сообщение пользователям"""
    try:
        if not BOT_TOKEN:
            return ApiResponse(success=False, message="BOT_TOKEN не настроен")

        # Проверяем доступность Supabase
        if not SupabasePool.is_available():
            return ApiResponse(
                success=False,
                message="Supabase не настроен. Проверьте переменные окружения DB_HOST, DB_PASSWORD и т.д."
            )

        # Получаем список пользователей через asyncpg
        users = await query_users_for_broadcast(filters=request.filters)

        if not users:
            return ApiResponse(
                success=False,
                message="Не найдено пользователей с привязанным Telegram"
            )

        logger.info(f"📤 Начинаем массовую рассылку для {len(users)} пользователей")

        # Отправляем сообщения
        success_count = 0
        failed_count = 0
        failed_users = []

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            for user in users:
                tg_user_id = user.get("tg_user_id")

                try:
                    # Небольшая задержка между сообщениями для избежания rate limiting
                    await asyncio.sleep(0.05)

                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    payload = {
                        "chat_id": tg_user_id,
                        "text": request.message
                    }

                    if request.parse_mode:
                        payload["parse_mode"] = request.parse_mode

                    response = await client.post(url, json=payload)
                    result_data = response.json()

                    if result_data.get("ok"):
                        success_count += 1
                        logger.debug(f"✅ Сообщение отправлено пользователю {tg_user_id}")
                    else:
                        failed_count += 1
                        error_desc = result_data.get("description", "Unknown error")
                        logger.warning(f"❌ Не удалось отправить пользователю {tg_user_id}: {error_desc}")
                        failed_users.append({
                            "tg_user_id": tg_user_id,
                            "username": user.get("username", ""),
                            "error": error_desc
                        })

                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Ошибка отправки пользователю {tg_user_id}: {e}")
                    failed_users.append({
                        "tg_user_id": tg_user_id,
                        "username": user.get("username", ""),
                        "error": str(e)
                    })

        logger.info(f"📊 Массовая рассылка завершена: успешно={success_count}, ошибок={failed_count}")

        return ApiResponse(
            success=True,
            message=f"Рассылка завершена: отправлено {success_count}, ошибок {failed_count}",
            data={
                "total": len(users),
                "success": success_count,
                "failed": failed_count,
                "failed_users": failed_users
            }
        )

    except Exception as e:
        logger.error(f"❌ Ошибка массовой рассылки: {e}")
        return ApiResponse(success=False, message=str(e))

# Редирект с корня на новую админку
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/static/admin.html")

@app.get("/admin")
def admin_redirect():
    return RedirectResponse(url="/static/admin.html")

# Статические файлы (должно быть в конце)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---- Startup/Shutdown Events ----
@app.on_event("startup")
async def startup_event():
    """Инициализация при старте приложения."""
    logger.info("🚀 Запуск админ-панели...")

    # Инициализируем пул подключений к Supabase
    try:
        await SupabasePool.initialize()
    except Exception as e:
        logger.warning(f"⚠️ Не удалось инициализировать Supabase: {e}")
        logger.warning("⚠️ Функция массовой рассылки будет недоступна")

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке приложения."""
    logger.info("🛑 Остановка админ-панели...")

    # Закрываем пул подключений к Supabase
    try:
        await SupabasePool.close()
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии пула Supabase: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
