#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
try:
    from typing import Dict, Any, List, Optional
except ImportError:
    # Для старых версий Python
    pass

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

logger.info("🔑 BOT_TOKEN найден: {}...{}".format(BOT_TOKEN[:10], BOT_TOKEN[-4:]))
logger.info("🔗 ADMIN_URL: {}".format(ADMIN_URL))
logger.info("🌐 FRONTEND_URL: {}".format(FRONTEND_URL))
if BOT_SHARED_SECRET:
    logger.info("🔐 BOT_SHARED_SECRET найден: {}...".format(BOT_SHARED_SECRET[:8]))
    logger.debug("✅ Функции привязки аккаунтов и HTTP запросов доступны")
else:
    logger.warning("⚠️ BOT_SHARED_SECRET не найден - функция привязки аккаунтов недоступна")
    logger.warning("⚠️ HTTP запросы на бэкенд будут отключены")

# Логируем дополнительную информацию о конфигурации
logger.debug("🗂️ DATABASE_PATH: {}".format(os.getenv('DATABASE_PATH', 'По умолчанию')))
logger.debug("🐳 Запуск в Docker: {}".format('Да' if os.path.exists('/.dockerenv') else 'Нет'))

def get_file_hash(file_content: bytes) -> str:
    """Вычислить хэш файла"""
    return hashlib.md5(file_content).hexdigest()

def normalize_ukrainian_text(text: str) -> str:
    """Нормализация украинского текста для корректного сравнения"""
    if not text:
        return ""
    
    # Убираем лишние пробелы и приводим к нижнему регистру
    normalized = text.strip().lower()
    
    # Заменяем возможные проблемные символы
    replacements = {
        'ё': 'е',  # русская ё на украинскую е
        'ъ': '',   # твердый знак
        'ы': 'и',  # русская ы на украинскую и
    }
    
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    return normalized

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
    logger.info(f"🚀 send_reaction_data ВЫЗВАНА! status={status}")
    logger.info(f"🔍 BOT_SHARED_SECRET: {'✅ есть' if BOT_SHARED_SECRET else '❌ нет'}")
    logger.info(f"🔍 ADMIN_URL: {ADMIN_URL}")
    
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

            # Проверяем, есть ли уже такой хэш (от другого пользователя)
            if db.check_media_hash(file_hash, message.from_user.id):
                logger.info(f"🚫 Обнаружен дубликат медиафайла от другого пользователя: {file_hash}")
                return True

            # Добавляем/обновляем хэш
            file_type = "photo" if file_id in media_info["photo_file_ids"] else "video"
            db.add_media_hash(
                file_hash, file_id, file_type,
                message.from_user.id, message.chat_id, message.message_id
            )
            logger.debug(f"✅ {file_type} добавлен/обновлён в базу: {file_hash}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки медиафайла {file_id}: {e}")
    
    return False

async def process_reaction_queue(context: ContextTypes.DEFAULT_TYPE):
    """Обработать очередь реакций с оптимизацией"""
    try:
        queue = db.get_reaction_queue()
        
        if not queue:
            return  # Не логируем если очередь пустая
            
        logger.info(f"🔄 Обрабатываем очередь реакций: {len(queue)} элементов")
        
        # Обрабатываем максимум 5 элементов за раз для избежания блокировки
        for i, item in enumerate(queue[:5]):
            try:
                # Добавляем небольшую задержку между реакциями
                if i > 0:
                    await asyncio.sleep(0.2)
                
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
                            logger.debug("📊 Отправляем данные о реакции из очереди на бэкенд...")
                            result = await send_reaction_data(mock_message, matched_tag, media_info, thread_name, "approved")
                            if result.get('success'):
                                logger.debug(f"📊 Данные из очереди отправлены успешно")
                            else:
                                logger.warning(f"📊 Ошибка отправки данных из очереди: {result}")
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки данных о реакции из очереди: {e}")
                
                # Удаляем из очереди
                db.remove_reaction_from_queue(item['id'])
                
            except Exception as e:
                error_message = str(e).lower()
                
                # Увеличиваем счетчик попыток
                attempts = db.increment_reaction_attempts(item['id'])
                logger.warning(f"❌ Не удалось поставить реакцию из очереди для {item['message_id']}: {e} (попытка {attempts})")
                
                # Проверяем, является ли ошибка "Reaction_invalid"
                if "reaction_invalid" in error_message:
                    logger.info(f"🔄 Обнаружена ошибка Reaction_invalid для {item['emoji']}, пробуем запасную реакцию ❤️")
                    
                    try:
                        # Пробуем поставить запасную реакцию ❤️
                        await context.bot.set_message_reaction(
                            chat_id=item['chat_id'],
                            message_id=item['message_id'],
                            reaction=ReactionTypeEmoji(emoji="❤️")
                        )
                        
                        logger.info(f"✅ Запасная реакция ❤️ поставлена → сообщение {item['message_id']}")
                        
                        # Отправляем данные на бэкенд с запасной реакцией
                        if item.get('moderation_id'):
                            try:
                                moderation_item = db.get_moderation_by_id(item['moderation_id'])
                                if moderation_item:
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
                                        'emoji': "❤️"  # Используем запасную реакцию
                                    }
                                    media_info = moderation_item.get('media_info', {})
                                    thread_name = moderation_item.get('thread_name', '')
                                    
                                    logger.info("📊 НАЧИНАЕМ отправку данных о запасной реакции на бэкенд...")
                                    result = await send_reaction_data(mock_message, matched_tag, media_info, thread_name, "approved")
                                    logger.info(f"📊 РЕЗУЛЬТАТ отправки данных запасной реакции: {result}")
                            except Exception as backend_e:
                                logger.error(f"❌ Ошибка отправки данных о запасной реакции: {backend_e}")
                        
                        # Удаляем из очереди после успешной запасной реакции
                        db.remove_reaction_from_queue(item['id'])
                        
                    except Exception as fallback_e:
                        logger.error(f"❌ Не удалось поставить запасную реакцию ❤️ для {item['message_id']}: {fallback_e}")
                        
                        # Если превышено максимальное количество попыток, удаляем из очереди
                        if attempts >= 10:
                            logger.warning(f"🗑️ Превышено максимальное количество попыток ({attempts}) для сообщения {item['message_id']}, удаляем из очереди")
                            db.remove_reaction_from_queue(item['id'])
                else:
                    # Для других ошибок проверяем лимит попыток
                    if attempts >= 10:
                        logger.warning(f"🗑️ Превышено максимальное количество попыток ({attempts}) для сообщения {item['message_id']}, удаляем из очереди")
                        db.remove_reaction_from_queue(item['id'])
    
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
    
    # Получаем все теги из БД (теперь с кэшированием)
    tags = db.get_tags()
    if not tags:
        logger.debug("🚫 Нет настроенных тегов в базе данных")
        return
    
    logger.debug(f"🏷️ Загружено {len(tags)} тегов из базы данных (кэш)")
    
    # Получаем текст сообщения
    text = (message.text or message.caption or "").lower()
    logger.debug(f"📝 Обрабатываем текст: {text}")
    
    # Получаем название треда
    thread_name = ""
    logger.debug(f"🧵 is_topic_message: {message.is_topic_message}")
    logger.debug(f"🧵 reply_to_message: {message.reply_to_message is not None}")
    
    if message.is_topic_message and message.reply_to_message:
        try:
            logger.debug("🧵 Пытаемся получить имя треда...")
            thread_name = message.reply_to_message.forum_topic_created.name
            logger.debug(f"🧵 Тред получен: '{thread_name}' (тип: {type(thread_name)})")
            logger.debug(f"🧵 Тред в байтах: {thread_name.encode('utf-8') if thread_name else 'None'}")
        except Exception as e:
            thread_name = "Unknown Thread"
            logger.debug(f"🧵 Ошибка получения треда: {e}")
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
            logger.debug(f"🔍 Слова в тексте: {words}")
            logger.debug(f"🔍 Ищем слова начинающиеся с: '{tag_text}'")
            for word in words:
                logger.debug(f"🔍 Проверяем слово: '{word}' начинается с '{tag_text}'? {word.startswith(tag_text)}")
                if word.startswith(tag_text):
                    matched_tag = tag
                    logger.info(f"✅ Найдено совпадение: {tag_text} -> {word} (префикс)")
                    break
            if matched_tag:
                break
    
    if not matched_tag:
        logger.debug("🚫 Совпадений не найдено")
        return

    try:
        logger.debug(f"✅ Тег найден: {matched_tag.get('tag', 'UNKNOWN')}")
        logger.debug(f"🔍 Тип matched_tag: {type(matched_tag)}")
        
        # Безопасное логирование содержимого
        try:
            logger.debug(f"🔍 Содержимое matched_tag: {dict(matched_tag)}")
        except Exception as log_e:
            logger.debug(f"🔍 Ошибка логирования matched_tag: {log_e}")
        
        logger.debug("🔍 Переходим к проверке треда...")
        
        tag_thread_name = matched_tag.get('thread_name', '')
        logger.debug(f"🔍 Получили thread_name: '{tag_thread_name}'")
        
        # Нормализуем строки для сравнения украинских символов
        tag_thread_normalized = normalize_ukrainian_text(tag_thread_name)
        current_thread_normalized = normalize_ukrainian_text(thread_name)
        logger.debug(f"🧵 Нормализованное сравнение: '{tag_thread_normalized}' vs '{current_thread_normalized}'")
        
        logger.debug(f"🧵 Проверяем тред: настроен='{tag_thread_name}', текущий='{thread_name}'")

        # Проверяем название треда если указано (используем нормализованные строки)
        if tag_thread_normalized and current_thread_normalized != tag_thread_normalized:
            logger.debug(f"🚫 Тред не совпадает: ожидается '{tag_thread_normalized}', получен '{current_thread_normalized}'")
            return
        
        logger.debug("✅ Проверка треда пройдена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке тега/треда: {e}")
        logger.error(f"❌ Тип ошибки: {type(e).__name__}")
        try:
            logger.error(f"❌ matched_tag: {dict(matched_tag) if matched_tag else 'None'}")
        except:
            logger.error(f"❌ matched_tag (raw): {matched_tag}")
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
    
    # Проверяем режим модерации
    if matched_tag['moderation_enabled']:
        # При модерации НЕ проверяем дубликаты - модератор сам решит
        logger.info(f"⏳ Добавляем в очередь модерации: {matched_tag['tag']}")
        # Добавляем в очередь модерации
        item_id = add_to_moderation_queue(message, matched_tag, media_info, thread_name)
        logger.debug(f"📝 Создан элемент модерации ID: {item_id}")
        
        # Данные будут отправлены только при фактической установке реакции (после одобрения)
        logger.info("📊 Сообщение добавлено в модерацию - данные будут отправлены после одобрения")
        
        # Отправляем сообщение о постановке в очередь
        if matched_tag['reply_pending']:
            await message.reply_text(matched_tag['reply_pending'])
            logger.debug(f"📤 Отправлено сообщение о модерации: {matched_tag['reply_pending']}")
        
        return

    # Обычный режим (без модерации) - проверяем дубликаты
    if media_info['has_photo'] or media_info['has_video']:
        is_duplicate = await check_media_duplicates(context, message, media_info)
        if is_duplicate:
            logger.info(f"🚫 Обнаружен дублирующийся медиафайл")
            if matched_tag['reply_duplicate']:
                await message.reply_text(matched_tag['reply_duplicate'])
            return

    # Обычный режим - ставим реакцию с задержкой
    delay = matched_tag['delay']
    logger.info(f"🔥 Автоматическая реакция: {matched_tag['emoji']} | Задержка: {delay}с")
    
    if delay > 0:
        logger.debug(f"⏳ Ожидание {delay}с перед реакцией...")
        await asyncio.sleep(delay)

    # Ставим реакцию
    try:
        logger.info(f"🎯 ПОПЫТКА поставить реакцию: {matched_tag['emoji']} | Пользователь: {user_info}")
        await message.set_reaction(ReactionTypeEmoji(emoji=matched_tag['emoji']))
        logger.info(f"✅ Реакция УСПЕШНО поставлена: {matched_tag['emoji']} | Пользователь: {user_info}")
        
        log_bot_event('reaction_set', {
            'emoji': matched_tag['emoji'],
            'user': message.from_user.username or message.from_user.first_name,
            'tag': matched_tag['tag']
        })
        
        # Отправляем данные о реакции на бэкенд
        logger.info("📊 НАЧИНАЕМ отправку данных о реакции на бэкенд...")
        result = await send_reaction_data(message, matched_tag, media_info, thread_name)
        logger.info(f"📊 РЕЗУЛЬТАТ отправки данных: {result}")
        
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
        
        # Оптимизированная проверка кода привязки:
        # Основной паттерн: 8 символов с цифрами (99% случаев)
        text_len = len(text)
        
        # Быстрая проверка основного паттерна (8 символов)
        if text_len == 8:
            # Проверяем за один проход: есть ли цифры и только ли alnum символы
            has_digit = False
            is_alnum = True
            for c in text:
                if c.isdigit():
                    has_digit = True
                elif not c.isalnum():
                    is_alnum = False
                    break
            
            if has_digit and is_alnum:
                # Основной паттерн найден - это код!
                pass  # Переходим к обработке
            else:
                # 8 символов, но не подходит под основной паттерн
                return  # Скорее всего обычное слово
        else:
            # Дополнительные проверки для нестандартных форматов
            digit_count = 0
            has_special = False
            
            for c in text:
                if c.isdigit():
                    digit_count += 1
                elif c in '-_':
                    has_special = True
            
            # Проверяем альтернативные паттерны
            if not ((digit_count > 0 and has_special) or  # цифры + спецсимволы
                    (text_len > 10 and digit_count > 0) or  # длинный с цифрами
                    digit_count > 4):  # много цифр
                return  # Не похоже на код
            logger.info(f"🔗 Обнаружен код привязки от {user_info}: {text[:8]}...")
            await handle_link_code(update, text)
            return
    
    # Если это не код привязки, передаем в обычный обработчик
    logger.debug(f"📝 Обычное текстовое сообщение от {user_info}, передаем в handle_any")
    await handle_any(update, context)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для принудительной обработки очереди реакций"""
    logger.info("🧪 ТЕСТ: Принудительная обработка очереди реакций")
    queue = db.get_reaction_queue()
    logger.info(f"🧪 ТЕСТ: В очереди {len(queue)} элементов")
    
    await process_reaction_queue(context)
    await update.message.reply_text(f"🧪 Черга реакцій оброблена\n📊 Було елементів: {len(queue)}")

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
