#!/usr/bin/env python3
"""
Конфигурация красивого логирования для бота и админки
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Any

class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для логов"""
    
    # ANSI цвета
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    # Эмодзи для разных типов
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '💥'
    }
    
    def format(self, record):
        # Получаем цвет и эмодзи для уровня
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        emoji = self.EMOJIS.get(record.levelname, '📝')
        
        # Форматируем время
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Сокращаем имя логгера
        logger_name = record.name
        if logger_name.startswith('telegram.'):
            logger_name = 'TG'
        elif logger_name.startswith('httpx'):
            logger_name = 'HTTP'
        elif logger_name.startswith('apscheduler'):
            logger_name = 'SCHED'
        elif logger_name.startswith('uvicorn'):
            logger_name = 'WEB'
        elif logger_name == '__main__':
            logger_name = 'BOT'
        
        # Форматируем сообщение
        message = record.getMessage()
        
        # Специальная обработка для разных типов сообщений
        if 'process_reaction_queue' in message and record.levelname == 'INFO':
            return f"{color}{emoji} {timestamp} [{logger_name}]{reset} 🔄 Обработка очереди реакций"
        elif 'getUpdates' in message and record.levelname == 'INFO':
            return f"{color}{emoji} {timestamp} [{logger_name}]{reset} 📡 Проверка обновлений Telegram"
        elif 'HTTP/1.1 200 OK' in message:
            return f"{color}{emoji} {timestamp} [{logger_name}]{reset} 🌐 API запрос выполнен"
        elif record.levelname in ['ERROR', 'CRITICAL']:
            return f"{color}{emoji} {timestamp} [{logger_name}]{reset} {message}"
        elif record.levelname == 'WARNING':
            return f"{color}{emoji} {timestamp} [{logger_name}]{reset} {message}"
        else:
            # Для обычных INFO сообщений показываем только важные
            if any(keyword in message.lower() for keyword in ['ошибка', 'error', 'реакция', 'модерация', 'тег']):
                return f"{color}{emoji} {timestamp} [{logger_name}]{reset} {message}"
            else:
                # Скрываем рутинные сообщения
                return None

def setup_logging(app_name: str = "BOT", level: str = "INFO"):
    """Настройка красивого логирования"""
    
    # Создаем основной логгер
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Создаем консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Устанавливаем цветной форматтер
    formatter = ColoredFormatter()
    console_handler.setFormatter(formatter)
    
    # Добавляем фильтр для скрытия None сообщений
    def filter_none(record):
        formatted = formatter.format(record)
        return formatted is not None
    
    console_handler.addFilter(filter_none)
    
    # Добавляем обработчик к логгеру
    logger.addHandler(console_handler)
    
    # Настраиваем уровни для внешних библиотек
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
    logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext').setLevel(logging.WARNING)
    
    # Приветственное сообщение
    print(f"""
🤖 {app_name} запущен
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Уровень логирования: {level.upper()}
🎨 Цветное логирование включено
""")

def log_bot_event(event_type: str, details: Dict[str, Any]):
    """Логирование событий бота"""
    logger = logging.getLogger('BOT')
    
    if event_type == 'reaction_set':
        logger.info(f"🎯 Реакция {details['emoji']} поставлена | Пользователь: {details['user']} | Тег: {details['tag']}")
    elif event_type == 'moderation_added':
        logger.info(f"📝 Сообщение добавлено в модерацию | Пользователь: {details['user']} | Тег: {details['tag']}")
    elif event_type == 'moderation_approved':
        logger.info(f"✅ Сообщение одобрено | ID: {details['id']} | Тег: {details['tag']}")
    elif event_type == 'moderation_rejected':
        logger.info(f"❌ Сообщение отклонено | ID: {details['id']} | Тег: {details['tag']}")
    elif event_type == 'duplicate_media':
        logger.warning(f"🔄 Дублирующееся медиа отклонено | Пользователь: {details['user']}")
    elif event_type == 'error':
        logger.error(f"💥 Ошибка: {details['message']}")
