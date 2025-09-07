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
setup_logging("MODERATOR BOT", "INFO")
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
else:
    logger.warning("⚠️ BOT_SHARED_SECRET не найден - функция привязки аккаунтов недоступна")

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

async def send_reaction_data(message, matched_tag: Dict[str, Any], media_info: Dict[str, Any], thread_name: str) -> Dict[str, Any]:
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
        "timestamp": datetime.now().isoformat()
    }
    
    # Создаем JSON строку и подпись
    json_data = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    signature = create_hmac_signature(json_data, BOT_SHARED_SECRET)
    
    # Отправляем запрос
    try:
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
                    logger.info(f"✅ Данные о реакции отправлены: user_id={message.from_user.id}, tag={matched_tag['tag']}")
                    return {
                        "success": True,
                        "status_code": response.status,
                        "data": response_data
                    }
                else:
                    logger.warning(f"⚠️ Бэкенд вернул код {response.status} для реакции")
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
        return False
    
    for file_id in media_info["media_file_ids"]:
        try:
            # Получаем файл и вычисляем хэш
            file = await context.bot.get_file(file_id)
            file_content = await file.download_as_bytearray()
            file_hash = get_file_hash(bytes(file_content))
            
            # Проверяем, есть ли уже такой хэш
            if db.check_media_hash(file_hash):
                return True
            
            # Добавляем новый хэш
            file_type = "photo" if file_id in media_info["photo_file_ids"] else "video"
            db.add_media_hash(
                file_hash, file_id, file_type,
                message.from_user.id, message.chat_id, message.message_id
            )
            
        except Exception as e:
            print(f"❌ Ошибка обработки медиафайла {file_id}: {e}")
    
    return False

async def process_reaction_queue(context: ContextTypes.DEFAULT_TYPE):
    """Обработать очередь реакций"""
    try:
        queue = db.get_reaction_queue()
        
        for item in queue:
            try:
                # Ставим реакцию
                await context.bot.set_message_reaction(
                    chat_id=item['chat_id'],
                    message_id=item['message_id'],
                    reaction=ReactionTypeEmoji(emoji=item['emoji'])
                )
                
                print(f"✅ Реакция {item['emoji']} поставлена к сообщению {item['message_id']}")
                
                # Удаляем из очереди
                db.remove_reaction_from_queue(item['id'])
                
            except Exception as e:
                print(f"❌ Не удалось поставить реакцию для {item['message_id']}: {e}")
                # Оставляем в очереди для повторной попытки
    
    except Exception as e:
        print(f"❌ Ошибка обработки очереди реакций: {e}")

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
        return
    
    # Получаем все теги из БД
    tags = db.get_tags()
    if not tags:
        return
    
    # Получаем текст сообщения
    text = (message.text or message.caption or "").lower()
    
    # Получаем название треда
    thread_name = ""
    if message.is_topic_message and message.reply_to_message:
        try:
            thread_name = message.reply_to_message.forum_topic_created.name
        except:
            thread_name = "Unknown Thread"
    
    # Ищем подходящий тег
    matched_tag = None
    for tag in tags:
        tag_text = tag['tag'].lower()
        
        # Проверяем соответствие режима поиска
        if tag['match_mode'] == 'equals':
            # Режим 1: Точное совпадение - тег должен быть отдельным словом
            pattern = r'(?:^|\s)' + re.escape(tag_text) + r'(?=\s|$)'
            if re.search(pattern, text):
                matched_tag = tag
                break
        elif tag['match_mode'] == 'prefix':
            # Режим 2: Префикс - ищем слова которые начинаются с тега
            words = text.split()
            for word in words:
                if word.startswith(tag_text):
                    matched_tag = tag
                    break
            if matched_tag:
                break
    
    if not matched_tag:
        return
    
    # Проверяем название треда если указано
    if matched_tag['thread_name'] and thread_name.lower() != matched_tag['thread_name'].lower():
        return
    
    # Получаем информацию о медиафайлах
    media_info = await get_media_info(message)
    
    # Проверяем требование медиафайла
    if matched_tag['require_photo'] and not (media_info['has_photo'] or media_info['has_video']):
        if matched_tag['reply_need_photo']:
            await message.reply_text(matched_tag['reply_need_photo'])
        return
    
    # Проверяем дублирование медиафайлов
    if media_info['has_photo'] or media_info['has_video']:
        is_duplicate = await check_media_duplicates(context, message, media_info)
        if is_duplicate:
            if matched_tag['reply_duplicate']:
                await message.reply_text(matched_tag['reply_duplicate'])
            return
    
    # Проверяем режим модерации
    if matched_tag['moderation_enabled']:
        # Добавляем в очередь модерации
        add_to_moderation_queue(message, matched_tag, media_info, thread_name)
        
        # Отправляем сообщение о постановке в очередь
        if matched_tag['reply_pending']:
            await message.reply_text(matched_tag['reply_pending'])
        
        return
    
    # Обычный режим - ставим реакцию с задержкой
    delay = matched_tag['delay']
    
    if delay > 0:
        print(f"⏳ Ожидание {delay}с перед реакцией...")
        await asyncio.sleep(delay)
    
    # Ставим реакцию
    try:
        await message.set_reaction(ReactionTypeEmoji(emoji=matched_tag['emoji']))
        log_bot_event('reaction_set', {
            'emoji': matched_tag['emoji'],
            'user': message.from_user.username or message.from_user.first_name,
            'tag': matched_tag['tag']
        })
        
        # Отправляем данные о реакции на бэкенд
        await send_reaction_data(message, matched_tag, media_info, thread_name)
        
        # Отправляем сообщение об успехе
        if matched_tag['reply_ok']:
            await message.reply_text(matched_tag['reply_ok'])
        
        # Записываем в лог
        append_log(message, matched_tag, thread_name, media_info)
        
    except Exception as e:
        log_bot_event('error', {'message': f"Ошибка постановки реакции: {e}"})

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    # Проверяем, есть ли код в аргументах команды
    if context.args and len(context.args) > 0:
        code = context.args[0].strip()
        await handle_link_code(update, code)
    else:
        # Обычное приветствие
        await update.message.reply_text(
            "👋 Привіт! Я Anyway bot.\n\n"
            "Я створений щоб прив'язати твій телеграм акаунт до профілю на платформі.\n\n"
            "Щоб прив'язати акаунт, перейди в редагування профілю на [платформі](https://anywayfit.com/profile/edit) і натисніть на кнопку 'Прив'язати Telegram'",
            parse_mode='Markdown'
        )

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
    
    # Проверяем, является ли сообщение кодом привязки
    # Код должен быть коротким (до 100 символов) и не содержать хештегов
    if (len(text) <= 100 and 
        not text.startswith('/') and 
        '#' not in text and 
        len(text.split()) == 1):  # Один токен без пробелов
        
        # Проверяем, что это не обычное слово (коды обычно содержат цифры или специальные символы)
        if any(c.isdigit() or c in '-_' for c in text):
            await handle_link_code(update, text)
            return
    
    # Если это не код привязки, передаем в обычный обработчик
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
    print("🚀 Запуск бота с SQLite базой данных...")
    print(f"📁 Путь к базе данных: {db.db_path}")
    
    # Инициализируем базу данных
    try:
        db.init_database()
        print("✅ База данных успешно инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        exit(1)
    
    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.ALL & ~filters.TEXT, handle_any))
    
    # Добавляем обработчик ошибок
    app.add_error_handler(error_handler)
    
    # Настраиваем периодическую обработку очереди реакций
    try:
        job_queue = app.job_queue
        if job_queue:
            job_queue.run_repeating(process_reaction_queue, interval=5, first=1)
            print("✅ Периодическая обработка очереди реакций настроена")
        else:
            print("⚠️ JobQueue недоступен, используется фоллбэк")
    except Exception as e:
        print(f"⚠️ JobQueue недоступен ({e}), используется фоллбэк при каждом сообщении")
    
    print("✅ Бот запущен и готов к работе!")
    
    # Запускаем бота
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
