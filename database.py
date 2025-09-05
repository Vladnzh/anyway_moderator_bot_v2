#!/usr/bin/env python3
"""
База данных SQLite для модератор-бота
Заменяет JSON файлы на полноценную БД
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Возвращать результаты как словари
        return conn
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        with self.get_connection() as conn:
            # Таблица тегов
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id TEXT PRIMARY KEY,
                    tag TEXT UNIQUE NOT NULL,
                    emoji TEXT NOT NULL,
                    delay INTEGER DEFAULT 0,
                    match_mode TEXT DEFAULT 'equals',
                    require_photo BOOLEAN DEFAULT TRUE,
                    reply_ok TEXT DEFAULT '',
                    reply_need_photo TEXT DEFAULT '',
                    thread_name TEXT DEFAULT '',
                    reply_duplicate TEXT DEFAULT '',
                    moderation_enabled BOOLEAN DEFAULT FALSE,
                    reply_pending TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица логов
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    trigger TEXT NOT NULL,
                    emoji TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    thread_name TEXT DEFAULT '',
                    media_type TEXT DEFAULT '',
                    caption TEXT DEFAULT ''
                )
            """)
            
            # Таблица модерации
            conn.execute("""
                CREATE TABLE IF NOT EXISTS moderation_queue (
                    id TEXT PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    tag TEXT NOT NULL,
                    emoji TEXT NOT NULL,
                    text TEXT DEFAULT '',
                    caption TEXT DEFAULT '',
                    media_info TEXT DEFAULT '{}',
                    thread_name TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица хэшей медиафайлов
            conn.execute("""
                CREATE TABLE IF NOT EXISTS media_hashes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE NOT NULL,
                    file_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица очереди реакций
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reaction_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    moderation_id TEXT NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    emoji TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Индексы для производительности
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_trigger ON logs(trigger)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_moderation_status ON moderation_queue(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_media_hash ON media_hashes(file_hash)")
            
            conn.commit()
            logger.info("✅ База данных инициализирована")

    # === ТЕГИ ===
    def get_tags(self) -> List[Dict[str, Any]]:
        """Получить все теги"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tags ORDER BY created_at")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_tag_by_id(self, tag_id: str) -> Optional[Dict[str, Any]]:
        """Получить тег по ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_tag(self, tag_data: Dict[str, Any]) -> str:
        """Создать новый тег"""
        tag_id = str(uuid.uuid4())[:8]
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO tags (id, tag, emoji, delay, match_mode, require_photo, 
                                reply_ok, reply_need_photo, thread_name, reply_duplicate,
                                moderation_enabled, reply_pending)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tag_id, tag_data['tag'], tag_data['emoji'], tag_data.get('delay', 0),
                tag_data.get('match_mode', 'equals'), tag_data.get('require_photo', True),
                tag_data.get('reply_ok', ''), tag_data.get('reply_need_photo', ''),
                tag_data.get('thread_name', ''), tag_data.get('reply_duplicate', ''),
                tag_data.get('moderation_enabled', False), tag_data.get('reply_pending', '')
            ))
            conn.commit()
        return tag_id
    
    def update_tag(self, tag_id: str, tag_data: Dict[str, Any]) -> bool:
        """Обновить тег"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE tags SET 
                    tag = ?, emoji = ?, delay = ?, match_mode = ?, require_photo = ?,
                    reply_ok = ?, reply_need_photo = ?, thread_name = ?, reply_duplicate = ?,
                    moderation_enabled = ?, reply_pending = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                tag_data['tag'], tag_data['emoji'], tag_data.get('delay', 0),
                tag_data.get('match_mode', 'equals'), tag_data.get('require_photo', True),
                tag_data.get('reply_ok', ''), tag_data.get('reply_need_photo', ''),
                tag_data.get('thread_name', ''), tag_data.get('reply_duplicate', ''),
                tag_data.get('moderation_enabled', False), tag_data.get('reply_pending', ''),
                tag_id
            ))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_tag(self, tag_id: str) -> bool:
        """Удалить тег"""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            conn.commit()
            return cursor.rowcount > 0

    # === ЛОГИ ===
    def add_log(self, log_data: Dict[str, Any]):
        """Добавить запись в лог"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO logs (user_id, username, chat_id, message_id, trigger, emoji, 
                                thread_name, media_type, caption)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_data['user_id'], log_data.get('username', ''),
                log_data['chat_id'], log_data['message_id'],
                log_data['trigger'], log_data['emoji'],
                log_data.get('thread_name', ''), log_data.get('media_type', ''),
                log_data.get('caption', '')
            ))
            conn.commit()
    
    def get_logs(self, tag: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        """Получить логи с фильтрацией"""
        with self.get_connection() as conn:
            if tag:
                cursor = conn.execute("""
                    SELECT * FROM logs WHERE trigger = ? 
                    ORDER BY timestamp DESC LIMIT ?
                """, (tag, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        with self.get_connection() as conn:
            # Общая статистика
            total_logs = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
            total_tags = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
            
            # Статистика по тегам
            tag_stats = conn.execute("""
                SELECT trigger, COUNT(*) as count 
                FROM logs 
                GROUP BY trigger 
                ORDER BY count DESC 
                LIMIT 10
            """).fetchall()
            
            # Статистика модерации
            moderation_stats = conn.execute("""
                SELECT 
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
                    COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected,
                    COUNT(*) as total
                FROM moderation_queue
            """).fetchone()
            
            return {
                'total_logs': total_logs,
                'total_tags': total_tags,
                'tag_stats': [{'tag': row[0], 'count': row[1]} for row in tag_stats],
                'moderation': {
                    'pending': moderation_stats[0] or 0,
                    'approved': moderation_stats[1] or 0,
                    'rejected': moderation_stats[2] or 0,
                    'total': moderation_stats[3] or 0
                }
            }

    # === МОДЕРАЦИЯ ===
    def add_moderation_item(self, item_data: Dict[str, Any]) -> str:
        """Добавить элемент в очередь модерации"""
        item_id = str(uuid.uuid4())[:8]
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO moderation_queue (id, chat_id, message_id, user_id, username,
                                            tag, emoji, text, caption, media_info, thread_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, item_data['chat_id'], item_data['message_id'],
                item_data['user_id'], item_data.get('username', ''),
                item_data['tag'], item_data['emoji'],
                item_data.get('text', ''), item_data.get('caption', ''),
                json.dumps(item_data.get('media_info', {})),
                item_data.get('thread_name', '')
            ))
            conn.commit()
        return item_id
    
    def get_pending_moderation(self) -> List[Dict[str, Any]]:
        """Получить элементы ожидающие модерации"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM moderation_queue 
                WHERE status = 'pending' 
                ORDER BY created_at
            """)
            items = []
            for row in cursor.fetchall():
                item = dict(row)
                item['media_info'] = json.loads(item['media_info'] or '{}')
                items.append(item)
            return items
    
    def update_moderation_status(self, item_id: str, status: str) -> bool:
        """Обновить статус модерации"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE moderation_queue 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (status, item_id))
            conn.commit()
            return cursor.rowcount > 0

    # === ХЭШИ МЕДИАФАЙЛОВ ===
    def add_media_hash(self, file_hash: str, file_id: str, file_type: str, 
                      user_id: int, chat_id: int, message_id: int) -> bool:
        """Добавить хэш медиафайла"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO media_hashes (file_hash, file_id, file_type, user_id, chat_id, message_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (file_hash, file_id, file_type, user_id, chat_id, message_id))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Хэш уже существует
    
    def check_media_hash(self, file_hash: str) -> bool:
        """Проверить существование хэша медиафайла"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM media_hashes WHERE file_hash = ?", (file_hash,))
            return cursor.fetchone() is not None

    # === ОЧЕРЕДЬ РЕАКЦИЙ ===
    def add_reaction_queue(self, moderation_id: str, chat_id: int, message_id: int, emoji: str):
        """Добавить в очередь реакций"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO reaction_queue (moderation_id, chat_id, message_id, emoji)
                VALUES (?, ?, ?, ?)
            """, (moderation_id, chat_id, message_id, emoji))
            conn.commit()
    
    def get_reaction_queue(self) -> List[Dict[str, Any]]:
        """Получить очередь реакций"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM reaction_queue ORDER BY created_at")
            return [dict(row) for row in cursor.fetchall()]
    
    def remove_reaction_from_queue(self, reaction_id: int):
        """Удалить реакцию из очереди"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM reaction_queue WHERE id = ?", (reaction_id,))
            conn.commit()
    
    def clear_reaction_queue(self):
        """Очистить очередь реакций"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM reaction_queue")
            conn.commit()

# Глобальный экземпляр базы данных
db = Database()
