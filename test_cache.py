#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест кэширования тегов
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import db

def test_cache_invalidation():
    """Тест автоматической инвалидации кэша"""
    print("🧪 Тест кэширования тегов")
    print("=" * 30)
    
    # 1. Очищаем кэш
    db.invalidate_tags_cache()
    print("🗑️ Кэш очищен")
    
    # 2. Первый запрос (загрузка из БД)
    start = time.time()
    tags1 = db.get_tags()
    time1 = time.time() - start
    print("📊 Первый запрос: {:.4f}с ({} тегов)".format(time1, len(tags1)))
    
    # 3. Второй запрос (из кэша)
    start = time.time()
    tags2 = db.get_tags()
    time2 = time.time() - start
    print("⚡ Второй запрос: {:.4f}с (из кэша)".format(time2))
    
    # 4. Создаем тестовый тег
    print("\n🏷️ Создаем тестовый тег...")
    tag_data = {
        'tag': 'тест_кэш',
        'emoji': '🧪',
        'delay': 0,
        'match_mode': 'equals',
        'require_photo': False,
        'reply_ok': 'Тест кэша!',
        'reply_need_photo': '',
        'thread_name': '',
        'reply_duplicate': '',
        'moderation_enabled': False,
        'reply_pending': '',
        'counter_name': 'Тест кэша'
    }
    
    tag_id = db.create_tag(tag_data)
    print("✅ Тег создан: {}".format(tag_id))
    
    # 5. Запрос после создания (кэш должен обновиться)
    start = time.time()
    tags3 = db.get_tags()
    time3 = time.time() - start
    print("🔄 После создания: {:.4f}с ({} тегов)".format(time3, len(tags3)))
    
    # 6. Проверяем что новый тег есть
    new_tag = next((t for t in tags3 if t['tag'] == 'тест_кэш'), None)
    if new_tag:
        print("✅ Новый тег найден в кэше: {}".format(new_tag['tag']))
    else:
        print("❌ Новый тег НЕ найден в кэше!")
    
    # 7. Обновляем тег
    print("\n🔧 Обновляем тег...")
    tag_data['emoji'] = '🚀'
    tag_data['reply_ok'] = 'Обновленный тест!'
    
    success = db.update_tag(tag_id, tag_data)
    print("✅ Тег обновлен: {}".format(success))
    
    # 8. Запрос после обновления
    start = time.time()
    tags4 = db.get_tags()
    time4 = time.time() - start
    print("🔄 После обновления: {:.4f}с".format(time4))
    
    # 9. Проверяем обновление
    updated_tag = next((t for t in tags4 if t['tag'] == 'тест_кэш'), None)
    if updated_tag and updated_tag['emoji'] == '🚀':
        print("✅ Обновление применилось: {} {}".format(updated_tag['emoji'], updated_tag['reply_ok']))
    else:
        print("❌ Обновление НЕ применилось!")
    
    # 10. Удаляем тестовый тег
    print("\n🗑️ Удаляем тестовый тег...")
    success = db.delete_tag(tag_id)
    print("✅ Тег удален: {}".format(success))
    
    # 11. Финальная проверка
    tags5 = db.get_tags()
    deleted_tag = next((t for t in tags5 if t['tag'] == 'тест_кэш'), None)
    if not deleted_tag:
        print("✅ Тег удален из кэша")
    else:
        print("❌ Тег НЕ удален из кэша!")
    
    print("\n📊 Результаты:")
    print("  Первый запрос (БД): {:.4f}с".format(time1))
    print("  Второй запрос (кэш): {:.4f}с".format(time2))
    print("  После создания: {:.4f}с".format(time3))
    print("  После обновления: {:.4f}с".format(time4))
    
    if time2 < time1 * 0.5:
        print("✅ Кэширование работает эффективно!")
    else:
        print("⚠️ Кэширование может работать неоптимально")
    
    print("\n🎉 Тест завершен!")

if __name__ == "__main__":
    test_cache_invalidation()
