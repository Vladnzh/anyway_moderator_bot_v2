#!/usr/bin/env python3
"""
Telegram модератор-бот с SQLite базой данных
"""

import os
import asyncio
import hashlib
import uuid
import logging
import re
import hmac
import json
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv

from database import db
from logger_config import setup_logging, log_bot_event

# Загружаем переменные окружения
load_dotenv()

# Настраиваем красивое логирование
setup_logging("MODERATOR BOT", "DEBUG")  # Изменяем уровень на DEBUG
logger = logging.getLogger('BOT')

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    exit(1)

BOT_SHARED_SECRET = os.getenv("BOT_SHARED_SECRET")
ADMIN_URL = os.getenv("ADMIN_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

logger.info(f"🔑 BOT_TOKEN найден: {BOT_TOKEN[:10]}...{BOT_TOKEN[-4:]}")
logger.info(f"🔗 ADMIN_URL: {ADMIN_URL}")
logger.info(f"🌐 FRONTEND_URL: {FRONTEND_URL}")
if BOT_SHARED_SECRET:
    logger.info(f"🔐 BOT_SHARED_SECRET найден: {BOT_SHARED_SECRET[:8]}...")
    logger.debug("✅ Функции привязки аккаунтов и HTTP запросов доступны")
else:
    logger.warning("⚠️ BOT_SHARED_SECRET не найден - функция привязки аккаунтов недоступна")
    logger.warning("⚠️ HTTP запросы на бэкенд будут отключены")

# Логируем дополнительную информацию о конфигурации
logger.debug(f"🗂️ DATABASE_PATH: {os.getenv('DATABASE_PATH', 'По умолчанию')}")
logger.debug(f"🐳 Запуск в Docker: {'Да' if os.path.exists('/.dockerenv') else 'Нет'}")

def get_file_hash(file_content: bytes) -> str:
    """Вычислить хэш файла"""
    return hashlib.md5(file_content).hexdigest()

def create_hmac_signature(data: str, secret: str) -> str:
    """Создать HMAC-SHA256 подпись"""
    return hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

async def link_telegram_account(code: str, user_id: int, username: str, first_name: str, last_name: str) -> Dict[str, Any]:
    """Отправить запрос на привязку Telegram аккаунта"""
    if not BOT_SHARED_SECRET:
        return {"success": False, "error": "BOT_SHARED_SECRET не настроен"}
    
    # Подготавливаем данные для запроса
    payload = {
        "code": code,
        "tg_user_id": str(user_id),
        "username": username or "",
        "first_name": first_name or "",
        "last_name": last_name or ""
    }
    
    # Создаем JSON строку и подпись
    json_data = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    signature = create_hmac_signature(json_data, BOT_SHARED_SECRET)
    
    # Отправляем запрос
    logger.debug(f"🔗 Отправляем запрос привязки на {FRONTEND_URL}/api/telegram/link")
    logger.debug(f"📝 Данные запроса: {json_data}")
    logger.debug(f"🔐 Подпись: {signature[:16]}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{FRONTEND_URL}/api/telegram/link",
                data=json_data,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature": signature
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_data = await response.json()
                logger.debug(f"📥 Ответ сервера: status={response.status}, data={response_data}")
                return {
                    "success": response.status == 200,
                    "status_code": response.status,
                    "data": response_data
                }
    except aiohttp.ClientError as e:
        logger.error(f"❌ Ошибка HTTP запроса: {e}")
        return {"success": False, "error": f"Ошибка сети: {e}"}
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        return {"success": False, "error": f"Неожиданная ошибка: {e}"}

async def send_reaction_data(message, matched_tag: Dict[str, Any], media_info: Dict[str, Any], thread_name: str, status: str = "approved") -> Dict[str, Any]:
    """Отправить данные о реакции на бэкенд"""
    if not BOT_SHARED_SECRET:
        logger.warning("⚠️ BOT_SHARED_SECRET не настроен - данные о реакции не отправляются")
        return {"success": False, "error": "BOT_SHARED_SECRET не настроен"}
    
    # Подготавливаем данные для отправки
    payload = {
        "tg_user_id": str(message.from_user.id),
        "username": message.from_user.username or "",
        "first_name": message.from_user.first_name or "",
        "last_name": message.from_user.last_name or "",
        "tag": matched_tag['tag'],
        "counter_name": matched_tag.get('counter_name', ''),
        "emoji": matched_tag['emoji'],
        "chat_id": str(message.chat_id),
        "message_id": str(message.message_id),
        "text": message.text or "",
        "caption": message.caption or "",
        "thread_name": thread_name,
        "has_photo": media_info.get('has_photo', False),
        "has_video": media_info.get('has_video', False),
        "media_file_ids": media_info.get('media_file_ids', []),
        "status": status,  # approved, pending, rejected
        "timestamp": datetime.now().isoformat()
    }
    
    # Создаем JSON строку и подпись
    json_data = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    signature = create_hmac_signature(json_data, BOT_SHARED_SECRET)
    
    # Отправляем запрос
    url = f"{ADMIN_URL}/api/telegram/reaction"
    logger.info(f"📊 Отправляем данные о реакции на: {url}")
    logger.debug(f"📝 Данные реакции: {json_data}")
    logger.debug(f"🔐 Подпись: {signature[:16]}...")
    logger.debug(f"📋 Заголовки: Content-Type=application/json, X-Signature={signature[:16]}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            logger.debug(f"🌐 Создаем HTTP сессию для {url}")
            async with session.post(
                url,
                data=json_data,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature": signature
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                logger.debug(f"📡 HTTP запрос отправлен, ожидаем ответ...")
                if response.status == 200:
                    response_data = await response.json()
                    logger.info(f"✅ УСПЕШНО ОТПРАВЛЕНО:")
                    logger.info(f"🌐 URL: {url}")
                    logger.info(f"👤 Пользователь: {message.from_user.id}")
                    logger.info(f"🏷️ Тег: {matched_tag['tag']}")
                    logger.info(f"📊 Статус: {status}")
                    logger.debug(f"📥 Ответ бэкенда: {response_data}")
                    return {
                        "success": True,
                        "status_code": response.status,
                        "data": response_data
                    }
                else:
                    response_text = await response.text()
                    logger.error(f"❌ ОШИБКА БЭКЕНДА:")
                    logger.error(f"🌐 URL: {url}")
                    logger.error(f"📊 HTTP код: {response.status}")
                    logger.error(f"📄 Ответ бэкенда: '{response_text}'")
                    logger.error(f"📋 Заголовки ответа: {dict(response.headers)}")
                    logger.debug(f"📝 Отправленные данные: {json_data}")
                    logger.debug(f"🔐 Полная подпись: {signature}")
                    return {
                        "success": False,
                        "status_code": response.status,
                        "data": {}
                    }
    except aiohttp.ClientError as e:
        logger.error(f"❌ Ошибка HTTP запроса при отправке реакции: {e}")
        return {"success": False, "error": f"Ошибка сети: {e}"}
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при отправке реакции: {e}")
        return {"success": False, "error": f"Неожиданная ошибка: {e}"}

async def get_media_info(message) -> Dict[str, Any]:
    """Получить информацию о медиафайлах в сообщении"""
    media_info = {
        "has_photo": False,
        "has_video": False,
        "photo_file_id": None,
        "video_file_id": None,
        "media_file_ids": [],
        "photo_file_ids": [],
        "video_file_ids": []
    }
    
    # Обработка фото
    if message.photo:
        media_info["has_photo"] = True
        largest_photo = message.photo[-1]  # Берем самое большое фото
        media_info["photo_file_id"] = largest_photo.file_id
        media_info["media_file_ids"].append(largest_photo.file_id)
        media_info["photo_file_ids"].append(largest_photo.file_id)
    
    # Обработка видео
    if message.video:
        media_info["has_video"] = True
        media_info["video_file_id"] = message.video.file_id
        media_info["media_file_ids"].append(message.video.file_id)
        media_info["video_file_ids"].append(message.video.file_id)
    
    return media_info

async def check_media_duplicates(context: ContextTypes.DEFAULT_TYPE, message, media_info: Dict[str, Any]) -> bool:
    """Проверить дублирование медиафайлов"""
    if not (media_info["has_photo"] or media_info["has_video"]):
        logger.debug("🖼️ Нет медиафайлов для проверки дубликатов")
        return False
    
    logger.debug(f"🔍 Проверяем дубликаты для {len(media_info['media_file_ids'])} медиафайлов")
    
    for file_id in media_info["media_file_ids"]:
        try:
            logger.debug(f"📁 Обрабатываем файл: {file_id}")
            
            # Получаем файл и вычисляем хэш
            file = await context.bot.get_file(file_id)
            file_content = await file.download_as_bytearray()
            file_hash = get_file_hash(bytes(file_content))
            
            logger.debug(f"🔐 Хэш файла: {file_hash}")
            
            # Проверяем, есть ли уже такой хэш
            if db.check_media_hash(file_hash):
                logger.info(f"🚫 Обнаружен дубликат медиафайла: {file_hash}")
                return True
            
            # Добавляем новый хэш
            file_type = "photo" if file_id in media_info["photo_file_ids"] else "video"
            db.add_media_hash(
                file_hash, file_id, file_type,
                message.from_user.id, message.chat_id, message.message_id
            )
            logger.debug(f"✅ Новый {file_type} добавлен в базу: {file_hash}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки медиафайла {file_id}: {e}")
    
    return False

async def process_reaction_queue(context: ContextTypes.DEFAULT_TYPE):
    """Обработать очередь реакций"""
    try:
        queue = db.get_reaction_queue()
        
        if queue:
            logger.debug(f"🔄 Обрабатываем очередь реакций: {len(queue)} элементов")
        
        for item in queue:
            try:
                # Ставим реакцию
                await context.bot.set_message_reaction(
                    chat_id=item['chat_id'],
                    message_id=item['message_id'],
                    reaction=ReactionTypeEmoji(emoji=item['emoji'])
                )
                
                logger.info(f"✅ Реакция из очереди: {item['emoji']} → сообщение {item['message_id']}")
                
                # Получаем данные модерации для отправки на бэкенд
                if item.get('moderation_id'):
                    try:
                        moderation_item = db.get_moderation_by_id(item['moderation_id'])
                        if moderation_item:
                            # Создаем объект сообщения для отправки данных
                            class MockMessage:
                                def __init__(self, data):
                                    self.chat_id = data['chat_id']
                                    self.message_id = data['message_id']
                                    self.text = data.get('text', '')
                                    self.caption = data.get('caption', '')
                                    class MockUser:
                                        def __init__(self, user_data):
                                            self.id = user_data['user_id']
                                            self.username = user_data.get('username', '')
                                            self.first_name = user_data.get('first_name', '')
                                            self.last_name = user_data.get('last_name', '')
                                    self.from_user = MockUser(data)
                            
                            mock_message = MockMessage(moderation_item)
                            matched_tag = {
                                'tag': moderation_item.get('tag', ''),
                                'counter_name': moderation_item.get('counter_name', ''),
                                'emoji': moderation_item.get('emoji', '')
                            }
                            media_info = moderation_item.get('media_info', {})
                            thread_name = moderation_item.get('thread_name', '')
                            
                            # Отправляем данные на бэкенд
                            await send_reaction_data(mock_message, matched_tag, media_info, thread_name, "approved")
                            logger.debug(f"📊 Данные о реакции из очереди отправлены на бэкенд")
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки данных о реакции из очереди: {e}")
                
                # Удаляем из очереди
                db.remove_reaction_from_queue(item['id'])
                
            except Exception as e:
                logger.warning(f"❌ Не удалось поставить реакцию из очереди для {item['message_id']}: {e}")
                # Оставляем в очереди для повторной попытки
    
    except Exception as e:
        logger.error(f"❌ Ошибка обработки очереди реакций: {e}")

def add_to_moderation_queue(message, matched_tag: Dict[str, Any], media_info: Dict[str, Any], thread_name: str):
    """Добавить сообщение в очередь модерации"""
    try:
        item_data = {
            'chat_id': message.chat_id,
            'message_id': message.message_id,
            'user_id': message.from_user.id,
            'username': message.from_user.username or message.from_user.first_name or 'Unknown',
            'tag': matched_tag['tag'],
            'emoji': matched_tag['emoji'],
            'text': message.text or '',
            'caption': message.caption or '',
            'media_info': media_info,
            'thread_name': thread_name,
            'counter_name': matched_tag.get('counter_name', '')
        }
        
        item_id = db.add_moderation_item(item_data)
        log_bot_event('moderation_added', {
            'user': item_data['username'],
            'tag': item_data['tag'],
            'id': item_id
        })
        return item_id
        
    except Exception as e:
        log_bot_event('error', {'message': f"Ошибка добавления в очередь модерации: {e}"})
        return None

def append_log(message, matched_tag: Dict[str, Any], thread_name: str, media_info: Dict[str, Any]):
    """Добавить запись в лог"""
    try:
        log_data = {
            'user_id': message.from_user.id,
            'username': message.from_user.username or message.from_user.first_name or 'Unknown',
            'chat_id': message.chat_id,
            'message_id': message.message_id,
            'trigger': matched_tag['tag'],
            'emoji': matched_tag['emoji'],
            'thread_name': thread_name,
            'media_type': 'photo' if media_info['has_photo'] else ('video' if media_info['has_video'] else ''),
            'caption': message.caption or ''
        }
        
        db.add_log(log_data)
        
    except Exception as e:
        log_bot_event('error', {'message': f"Ошибка записи лога: {e}"})

async def handle_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех сообщений"""
    # Обрабатываем очередь реакций при каждом сообщении (фоллбэк)
    await process_reaction_queue(context)
    
    message = update.message
    if not message or not message.text and not message.caption:
        logger.debug("🚫 Сообщение пропущено: нет текста или подписи")
        return
    
    # Логируем входящее сообщение
    user_info = f"{message.from_user.username or message.from_user.first_name} (ID: {message.from_user.id})"
    text_preview = (message.text or message.caption or "")[:100]
    logger.info(f"📨 Входящее сообщение от {user_info}: {text_preview}")
    logger.debug(f"📍 Чат: {message.chat_id}, Сообщение: {message.message_id}")
    logger.debug(f"🔍 Полный текст: {message.text or message.caption or 'Нет текста'}")
    
    # Логируем информацию о пользователе
    logger.debug(f"👤 Пользователь: @{message.from_user.username or 'без_username'} | {message.from_user.first_name or ''} {message.from_user.last_name or ''}")
    
    # Логируем тип сообщения
    if message.photo:
        logger.debug("🖼️ Сообщение содержит фото")
    if message.video:
        logger.debug("🎥 Сообщение содержит видео")
    if message.is_topic_message:
        logger.debug("🧵 Сообщение в треде")
    
    # Получаем все теги из БД
    tags = db.get_tags()
    if not tags:
        logger.debug("🚫 Нет настроенных тегов в базе данных")
        return
    
    logger.debug(f"🏷️ Загружено {len(tags)} тегов из базы данных")
    
    # Получаем текст сообщения
    text = (message.text or message.caption or "").lower()
    logger.debug(f"📝 Обрабатываем текст: {text}")
    
    # Получаем название треда
    thread_name = ""
    if message.is_topic_message and message.reply_to_message:
        try:
            thread_name = message.reply_to_message.forum_topic_created.name
            logger.debug(f"🧵 Тред: {thread_name}")
        except:
            thread_name = "Unknown Thread"
            logger.debug("🧵 Тред: Unknown Thread")
    
    # Ищем подходящий тег
    matched_tag = None
    logger.debug(f"🔍 Начинаем поиск совпадений среди {len(tags)} тегов")
    
    for tag in tags:
        tag_text = tag['tag'].lower()
        logger.debug(f"🏷️ Проверяем тег '{tag_text}' (режим: {tag['match_mode']})")
        
        # Проверяем соответствие режима поиска
        if tag['match_mode'] == 'equals':
            # Режим 1: Точное совпадение - тег должен быть отдельным словом
            pattern = r'(?:^|\s)' + re.escape(tag_text) + r'(?=\s|$)'
            if re.search(pattern, text):
                matched_tag = tag
                logger.info(f"✅ Найдено совпадение: {tag_text} (точное совпадение)")
                break
        elif tag['match_mode'] == 'prefix':
            # Режим 2: Префикс - ищем слова которые начинаются с тега
            words = text.split()
            for word in words:
                if word.startswith(tag_text):
                    matched_tag = tag
                    logger.info(f"✅ Найдено совпадение: {tag_text} -> {word} (префикс)")
                    break
            if matched_tag:
                break
    
    if not matched_tag:
        logger.debug("🚫 Совпадений не найдено")
        return

    # Проверяем название треда если указано
    if matched_tag['thread_name'] and thread_name.lower() != matched_tag['thread_name'].lower():
        logger.debug(f"🚫 Тред не совпадает: ожидается '{matched_tag['thread_name']}', получен '{thread_name}'")
        return
    
    logger.info(f"🎯 Тег сработал: {matched_tag['tag']} | Пользователь: {user_info}")
    
    # Логируем настройки тега
    logger.debug(f"⚙️ Настройки тега:")
    logger.debug(f"   🔥 Эмодзи: {matched_tag['emoji']}")
    logger.debug(f"   📊 Счетчик: {matched_tag.get('counter_name', 'Не указан')}")
    logger.debug(f"   ⏱️ Задержка: {matched_tag.get('delay', 0)}с")
    logger.debug(f"   🔍 Модерация: {'Включена' if matched_tag.get('moderation_enabled') else 'Отключена'}")
    logger.debug(f"   🖼️ Требует медиа: {'Да' if matched_tag.get('require_photo') else 'Нет'}")
    if matched_tag.get('thread_name'):
        logger.debug(f"   🧵 Только в треде: {matched_tag['thread_name']}")
    
    # Получаем информацию о медиафайлах
    media_info = await get_media_info(message)
    logger.debug(f"🖼️ Медиа: фото={media_info['has_photo']}, видео={media_info['has_video']}")
    if media_info['media_file_ids']:
        logger.debug(f"📁 ID файлов: {media_info['media_file_ids']}")
    
    # Проверяем требование медиафайла
    if matched_tag['require_photo'] and not (media_info['has_photo'] or media_info['has_video']):
        logger.info(f"🚫 Требуется медиафайл, но его нет")
        if matched_tag['reply_need_photo']:
            await message.reply_text(matched_tag['reply_need_photo'])
            logger.debug(f"📤 Отправлено сообщение: {matched_tag['reply_need_photo']}")
        return
    
    # Проверяем дублирование медиафайлов
    if media_info['has_photo'] or media_info['has_video']:
        is_duplicate = await check_media_duplicates(context, message, media_info)
        if is_duplicate:
            logger.info(f"🚫 Обнаружен дублирующийся медиафайл")
            if matched_tag['reply_duplicate']:
                await message.reply_text(matched_tag['reply_duplicate'])
                logger.debug(f"📤 Отправлено сообщение о дубликате: {matched_tag['reply_duplicate']}")
            return
    
    # Проверяем режим модерации
    if matched_tag['moderation_enabled']:
        logger.info(f"⏳ Добавляем в очередь модерации: {matched_tag['tag']}")
        # Добавляем в очередь модерации
        item_id = add_to_moderation_queue(message, matched_tag, media_info, thread_name)
        logger.debug(f"📝 Создан элемент модерации ID: {item_id}")
        
        # Данные будут отправлены только при фактической установке реакции (после одобрения)
        logger.debug("📊 Сообщение добавлено в модерацию - данные будут отправлены после одобрения")
        
        # Отправляем сообщение о постановке в очередь
        if matched_tag['reply_pending']:
            await message.reply_text(matched_tag['reply_pending'])
            logger.debug(f"📤 Отправлено сообщение о модерации: {matched_tag['reply_pending']}")
        
        return

    # Обычный режим - ставим реакцию с задержкой
    delay = matched_tag['delay']
    logger.info(f"🔥 Автоматическая реакция: {matched_tag['emoji']} | Задержка: {delay}с")
    
    if delay > 0:
        logger.debug(f"⏳ Ожидание {delay}с перед реакцией...")
        await asyncio.sleep(delay)
    
    # Ставим реакцию
    try:
        await message.set_reaction(ReactionTypeEmoji(emoji=matched_tag['emoji']))
        logger.info(f"✅ Реакция поставлена: {matched_tag['emoji']} | Пользователь: {user_info}")
        
        log_bot_event('reaction_set', {
            'emoji': matched_tag['emoji'],
            'user': message.from_user.username or message.from_user.first_name,
            'tag': matched_tag['tag']
        })
        
        # Отправляем данные о реакции на бэкенд
        logger.debug("📊 Отправляем данные о реакции на бэкенд...")
        await send_reaction_data(message, matched_tag, media_info, thread_name)
        
        # Отправляем сообщение об успехе
        if matched_tag['reply_ok']:
            await message.reply_text(matched_tag['reply_ok'])
            logger.debug(f"📤 Отправлено сообщение об успехе: {matched_tag['reply_ok']}")
        
        # Записываем в лог
        append_log(message, matched_tag, thread_name, media_info)
        logger.debug("📝 Запись добавлена в локальный лог")
        
    except Exception as e:
        logger.error(f"❌ Ошибка постановки реакции: {e}")
        log_bot_event('error', {'message': f"Ошибка постановки реакции: {e}"})

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_info = f"{update.effective_user.username or update.effective_user.first_name} (ID: {update.effective_user.id})"
    
    # Проверяем, есть ли код в аргументах команды
    if context.args and len(context.args) > 0:
        code = context.args[0].strip()
        logger.info(f"🔗 Команда /start с кодом от {user_info}: {code[:8]}...")
        await handle_link_code(update, code)
    else:
        logger.info(f"👋 Команда /start (приветствие) от {user_info}")
        # Обычное приветствие
        await update.message.reply_text(
            "👋 Привіт! Я Anyway bot.\n\n"
            "Я створений щоб прив'язати твій телеграм акаунт до профілю на платформі.\n\n"
            "Щоб прив'язати акаунт, перейди в редагування профілю на [платформі](https://anywayfit.com/profile/edit) і натисніть на кнопку 'Прив'язати Telegram'",
            parse_mode='Markdown'
        )
        logger.debug("📤 Отправлено приветственное сообщение")

async def handle_link_code(update: Update, code: str):
    """Обработка кода привязки аккаунта"""
    user = update.effective_user
    
    if not user:
        await update.message.reply_text("🚫 Не вдалося отримати інформацію про користувача")
        return
    
    # Проверяем формат кода (должен быть не пустым)
    if not code or len(code.strip()) < 3:
        await update.message.reply_text("❌ Невірний формат коду")
        return
    
    # Показываем сообщение о обработке
    processing_message = await update.message.reply_text("⏳ Обробляю запит...")
    
    # Отправляем запрос на бэкенд
    logger.info(f"🔗 Попытка привязки аккаунта: user_id={user.id}, code={code[:8]}...")
    
    result = await link_telegram_account(
        code=code.strip(),
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        last_name=user.last_name or ""
    )
    
    # Удаляем сообщение о обработке
    try:
        await processing_message.delete()
    except:
        pass  # Игнорируем ошибки удаления
    
    # Обрабатываем результат
    if not result["success"]:
        if "error" in result:
            await update.message.reply_text("🚫 Сталася помилка. Спробуй ще раз")
            logger.error(f"❌ Ошибка привязки: {result['error']}")
        else:
            await handle_backend_response(update, result)
    else:
        await handle_backend_response(update, result)

async def handle_backend_response(update: Update, result: Dict[str, Any]):
    """Обработка ответа от бэкенда"""
    status_code = result.get("status_code", 0)
    data = result.get("data", {})
    
    if status_code == 200 and data.get("status") == "linked":
        await update.message.reply_text("✅ Акаунт прив'язано")
        logger.info(f"✅ Аккаунт успешно привязан: user_id={update.effective_user.id}")
        
    elif status_code == 400:
        error_type = data.get("error", "")
        if error_type == "invalid_or_expired_code":
            await update.message.reply_text("❌ Код невірний або строк дії минув")
        else:
            await update.message.reply_text("❌ Невірний запит")
            
    elif status_code == 409:
        error_type = data.get("error", "")
        if error_type == "tg_already_linked_to_another_user":
            await update.message.reply_text("⚠️ Цей Telegram вже прив'язаний до іншого акаунта")
        else:
            await update.message.reply_text("⚠️ Конфлікт даних")
            
    else:
        await update.message.reply_text("🚫 Сталася помилка. Спробуй ще раз")
        logger.error(f"❌ Неожиданный ответ бэкенда: status={status_code}, data={data}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (включая коды привязки)"""
    message = update.message
    if not message or not message.text:
        return
    
    text = message.text.strip()
    user_info = f"{message.from_user.username or message.from_user.first_name} (ID: {message.from_user.id})"
    
    # Проверяем, является ли сообщение кодом привязки
    # Код должен быть коротким (до 100 символов) и не содержать хештегов
    if (len(text) <= 100 and 
        not text.startswith('/') and 
        '#' not in text and 
        len(text.split()) == 1):  # Один токен без пробелов
        
        # Проверяем, что это не обычное слово (коды обычно содержат цифры или специальные символы)
        if any(c.isdigit() or c in '-_' for c in text):
            logger.info(f"🔗 Обнаружен код привязки от {user_info}: {text[:8]}...")
            await handle_link_code(update, text)
            return
    
    # Если это не код привязки, передаем в обычный обработчик
    logger.debug(f"📝 Обычное текстовое сообщение от {user_info}, передаем в handle_any")
    await handle_any(update, context)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для принудительной обработки очереди реакций"""
    await process_reaction_queue(context)
    await update.message.reply_text("🧪 Черга реакцій оброблена")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"🚨 Ошибка в боте: {context.error}")
    
    # Логируем дополнительную информацию если есть update
    if isinstance(update, Update) and update.effective_message:
        logger.error(f"📝 Сообщение: {update.effective_message.text}")
        logger.error(f"👤 Пользователь: {update.effective_user.username if update.effective_user else 'Unknown'}")
        logger.error(f"💬 Чат: {update.effective_chat.id if update.effective_chat else 'Unknown'}")
    
    # Записываем в лог событий
    log_bot_event('error', {
        'message': str(context.error),
        'update_type': type(update).__name__ if update else 'Unknown'
    })

def main():
    """Основная функция"""
    logger.info("🚀 Запуск бота с SQLite базой данных...")
    logger.info(f"📁 Путь к базе данных: {db.db_path}")
    
    # Инициализируем базу данных
    try:
        db.init_database()
        logger.info("✅ База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        exit(1)
    
    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).build()
    logger.debug("🔧 Telegram Application создан")
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.ALL & ~filters.TEXT, handle_any))
    logger.info("📋 Обработчики сообщений зарегистрированы")
    
    # Добавляем обработчик ошибок
    app.add_error_handler(error_handler)
    logger.debug("🚨 Обработчик ошибок зарегистрирован")
    
    # Настраиваем периодическую обработку очереди реакций
    try:
        job_queue = app.job_queue
        if job_queue:
            job_queue.run_repeating(process_reaction_queue, interval=5, first=1)
            logger.info("✅ Периодическая обработка очереди реакций настроена (каждые 5 секунд)")
        else:
            logger.warning("⚠️ JobQueue недоступен, используется фоллбэк")
    except Exception as e:
        logger.warning(f"⚠️ JobQueue недоступен ({e}), используется фоллбэк при каждом сообщении")
    
    logger.info("✅ Бот запущен и готов к работе!")
    logger.info("🔍 Ожидаем входящие сообщения...")
    
    # Запускаем бота
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
