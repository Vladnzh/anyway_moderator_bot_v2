#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенный тест workflow без async/await
Проверяет основную функциональность бота и админки
"""

import requests
import json
import time
import random
import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db

# Конфигурация
ADMIN_URL = "http://localhost:8000"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")

class SimpleWorkflowTester:
    def __init__(self):
        self.results = {
            'created_tags': 0,
            'moderation_items': 0,
            'approvals': 0,
            'rejections': 0,
            'errors': []
        }
        self.headers = {
            "Authorization": "Bearer {}".format(ADMIN_TOKEN),
            "Content-Type": "application/json"
        }
    
    def test_admin_connection(self):
        """Тест подключения к админке"""
        print("🔌 Проверяем подключение к админке...")
        
        try:
            response = requests.get(ADMIN_URL, timeout=5)
            if response.status_code in [200, 302]:
                print("✅ Админка доступна")
                return True
            else:
                print("❌ Админка недоступна: HTTP {}".format(response.status_code))
                return False
        except Exception as e:
            print("❌ Ошибка подключения к админке: {}".format(e))
            return False
    
    def create_test_tag(self, tag_data):
        """Создание тестового тега"""
        try:
            response = requests.post(
                "{}/api/tags".format(ADMIN_URL),
                headers=self.headers,
                json=tag_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.results['created_tags'] += 1
                    print("✅ Создан тег: {}".format(tag_data['tag']))
                    return result.get('data', {}).get('id')
                else:
                    error_msg = "Не удалось создать тег {}: {}".format(tag_data['tag'], result.get('message'))
                    self.results['errors'].append(error_msg)
                    print("❌ {}".format(error_msg))
                    return None
            else:
                error_msg = "HTTP {} при создании тега {}: {}".format(response.status_code, tag_data['tag'], response.text)
                self.results['errors'].append(error_msg)
                print("❌ {}".format(error_msg))
                return None
                
        except Exception as e:
            error_msg = "Исключение при создании тега {}: {}".format(tag_data['tag'], e)
            self.results['errors'].append(error_msg)
            print("❌ {}".format(error_msg))
            return None
    
    def setup_test_tags(self):
        """Создание тестовых тегов"""
        print("🏷️ Создаем тестовые теги...")
        
        test_tags = [
            {
                "tag": "тест_простой",
                "emoji": "✅",
                "delay": 0,
                "match_mode": "equals",
                "require_photo": False,
                "reply_ok": "Простой тест зачтен!",
                "moderation_enabled": False,
                "counter_name": "Простые тесты"
            },
            {
                "tag": "тест_модер",
                "emoji": "👨‍💼", 
                "delay": 0,
                "match_mode": "equals",
                "require_photo": True,
                "reply_ok": "Одобрено модератором!",
                "reply_need_photo": "Нужно фото для модерации",
                "moderation_enabled": True,
                "reply_pending": "Отправлено на модерацию",
                "counter_name": "Модерируемые тесты"
            }
        ]
        
        created_tag_ids = []
        for tag_data in test_tags:
            tag_id = self.create_test_tag(tag_data)
            if tag_id:
                created_tag_ids.append(tag_id)
        
        print("✅ Создано {} тегов".format(len(created_tag_ids)))
        return created_tag_ids
    
    def create_moderation_items(self, count=20):
        """Создание элементов модерации"""
        print("📝 Создаем {} элементов модерации...".format(count))
        
        created_items = []
        
        for i in range(count):
            item_data = {
                'chat_id': -1001234567890,
                'message_id': 4000 + i,
                'user_id': 200000 + i,
                'username': 'simple_test_user_{}'.format(i),
                'tag': 'тест_модер',
                'emoji': '👨‍💼',
                'text': 'Простой тест сообщение #{}'.format(i),
                'caption': 'Тестовая подпись к медиа',
                'media_info': {
                    'has_photo': True,
                    'has_video': False,
                    'media_file_ids': ['simple_test_photo_{}'.format(i)]
                },
                'thread_name': 'Простой тест тред',
                'counter_name': 'Модерируемые тесты'
            }
            
            try:
                item_id = db.add_moderation_item(item_data)
                if item_id:
                    created_items.append(item_id)
                    self.results['moderation_items'] += 1
                else:
                    self.results['errors'].append("Не удалось создать элемент модерации #{}".format(i))
            except Exception as e:
                self.results['errors'].append("Ошибка создания элемента #{}: {}".format(i, e))
        
        print("✅ Создано {} элементов модерации".format(len(created_items)))
        return created_items
    
    def get_moderation_queue(self):
        """Получение очереди модерации"""
        try:
            response = requests.get(
                "{}/api/moderation".format(ADMIN_URL),
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('data', [])
            else:
                error_msg = "Ошибка получения очереди: HTTP {}".format(response.status_code)
                self.results['errors'].append(error_msg)
                return []
                
        except Exception as e:
            error_msg = "Исключение при получении очереди: {}".format(e)
            self.results['errors'].append(error_msg)
            return []
    
    def approve_item(self, item_id):
        """Одобрение элемента модерации"""
        try:
            response = requests.post(
                "{}/api/moderation/{}/approve".format(ADMIN_URL, item_id),
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.results['approvals'] += 1
                    return True
                else:
                    self.results['errors'].append("Не удалось одобрить {}: {}".format(item_id, result.get('message')))
                    return False
            else:
                self.results['errors'].append("HTTP {} при одобрении {}: {}".format(response.status_code, item_id, response.text))
                return False
                
        except Exception as e:
            self.results['errors'].append("Исключение при одобрении {}: {}".format(item_id, e))
            return False
    
    def reject_item(self, item_id):
        """Отклонение элемента модерации"""
        try:
            response = requests.post(
                "{}/api/moderation/{}/reject".format(ADMIN_URL, item_id),
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.results['rejections'] += 1
                    return True
                else:
                    self.results['errors'].append("Не удалось отклонить {}: {}".format(item_id, result.get('message')))
                    return False
            else:
                self.results['errors'].append("HTTP {} при отклонении {}: {}".format(response.status_code, item_id, response.text))
                return False
                
        except Exception as e:
            self.results['errors'].append("Исключение при отклонении {}: {}".format(item_id, e))
            return False
    
    def process_moderation_queue(self, approve_count=10, reject_count=10):
        """Обработка очереди модерации"""
        print("⚖️ Обрабатываем очередь модерации ({} одобрений, {} отклонений)...".format(approve_count, reject_count))
        
        queue = self.get_moderation_queue()
        
        if not queue:
            print("❌ Очередь модерации пуста!")
            return False
        
        print("📋 В очереди {} элементов".format(len(queue)))
        
        # Перемешиваем для случайности
        random.shuffle(queue)
        
        approved = 0
        rejected = 0
        
        for item in queue:
            if approved < approve_count:
                print("✅ Одобряем: {} (сообщение {})".format(item['id'], item['message_id']))
                if self.approve_item(item['id']):
                    approved += 1
                time.sleep(0.3)  # Задержка между запросами
                
            elif rejected < reject_count:
                print("❌ Отклоняем: {} (сообщение {})".format(item['id'], item['message_id']))
                if self.reject_item(item['id']):
                    rejected += 1
                time.sleep(0.3)
                
            else:
                break
        
        print("✅ Обработано: {} одобрений, {} отклонений".format(approved, rejected))
        return True
    
    def verify_results(self):
        """Проверка результатов"""
        print("🔍 Проверяем результаты...")
        
        # Проверяем логи
        logs = db.get_logs(limit=100)
        print("📊 Всего логов в базе: {}".format(len(logs)))
        
        # Проверяем статистику модерации
        stats = db.get_stats()
        moderation_stats = stats.get('moderation', {})
        
        print("📈 Статистика модерации:")
        print("  - Одобрено: {}".format(moderation_stats.get('approved', 0)))
        print("  - Отклонено: {}".format(moderation_stats.get('rejected', 0)))
        print("  - В ожидании: {}".format(moderation_stats.get('pending', 0)))
        
        # Проверяем очередь реакций
        reaction_queue = db.get_reaction_queue()
        print("🔄 Элементов в очереди реакций: {}".format(len(reaction_queue)))
        
        return {
            'logs_count': len(logs),
            'moderation_stats': moderation_stats,
            'reaction_queue_size': len(reaction_queue)
        }
    
    def run_test(self):
        """Запуск полного теста"""
        print("🚀 ПРОСТОЙ ТЕСТ WORKFLOW")
        print("Проверяем: создание тегов -> модерация -> одобрение/отклонение")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # 1. Проверяем подключение
            if not self.test_admin_connection():
                return False
            
            # 2. Создаем тестовые теги
            tag_ids = self.setup_test_tags()
            if not tag_ids:
                print("❌ Не удалось создать тестовые теги")
                return False
            
            # 3. Создаем элементы модерации
            item_ids = self.create_moderation_items(20)
            if not item_ids:
                print("❌ Не удалось создать элементы модерации")
                return False
            
            # 4. Пауза для обработки
            print("⏳ Пауза 2 секунды...")
            time.sleep(2)
            
            # 5. Обрабатываем модерацию
            if not self.process_moderation_queue(10, 10):
                print("❌ Ошибка обработки модерации")
                return False
            
            # 6. Пауза для реакций
            print("⏳ Пауза 3 секунды для реакций...")
            time.sleep(3)
            
            # 7. Проверяем результаты
            verification = self.verify_results()
            
            # 8. Финальный отчет
            self.print_report(verification, time.time() - start_time)
            
            return True
            
        except Exception as e:
            print("❌ Критическая ошибка: {}".format(e))
            return False
    
    def print_report(self, verification, duration):
        """Печать отчета"""
        print("\n" + "=" * 60)
        print("📊 ОТЧЕТ ПРОСТОГО ТЕСТА")
        print("=" * 60)
        
        print("⏱️ Время выполнения: {:.2f} секунд".format(duration))
        print()
        
        print("📝 Созданные данные:")
        print("  - Теги: {}".format(self.results['created_tags']))
        print("  - Элементы модерации: {}".format(self.results['moderation_items']))
        print()
        
        print("⚖️ Обработка модерации:")
        print("  - Одобрено: {}".format(self.results['approvals']))
        print("  - Отклонено: {}".format(self.results['rejections']))
        print()
        
        print("📊 Результаты в базе:")
        print("  - Всего логов: {}".format(verification['logs_count']))
        print("  - Одобренных в БД: {}".format(verification['moderation_stats'].get('approved', 0)))
        print("  - Отклоненных в БД: {}".format(verification['moderation_stats'].get('rejected', 0)))
        print("  - В очереди реакций: {}".format(verification['reaction_queue_size']))
        print()
        
        if self.results['errors']:
            print("❌ Ошибки ({} шт.):".format(len(self.results['errors'])))
            for i, error in enumerate(self.results['errors'][:3], 1):
                print("  {}. {}".format(i, error))
            if len(self.results['errors']) > 3:
                print("  ... и еще {} ошибок".format(len(self.results['errors']) - 3))
        else:
            print("✅ Ошибок не обнаружено!")
        
        print()
        
        # Оценка успешности
        success_rate = self.calculate_success_rate()
        if success_rate >= 80:
            print("🎉 ТЕСТ ПРОЙДЕН УСПЕШНО! ({:.1f}% успешности)".format(success_rate))
        elif success_rate >= 60:
            print("⚠️ ТЕСТ ПРОЙДЕН С ЗАМЕЧАНИЯМИ ({:.1f}% успешности)".format(success_rate))
        else:
            print("❌ ТЕСТ ПРОВАЛЕН ({:.1f}% успешности)".format(success_rate))
        
        print("=" * 60)
    
    def calculate_success_rate(self):
        """Расчет успешности"""
        expected_total = 2 + 20 + 10 + 10  # теги + элементы + одобрения + отклонения
        actual_total = (self.results['created_tags'] + 
                       self.results['moderation_items'] + 
                       self.results['approvals'] + 
                       self.results['rejections'])
        
        if expected_total == 0:
            return 0
        
        success_rate = (actual_total / expected_total) * 100
        error_penalty = min(len(self.results['errors']) * 3, 20)
        
        return max(0, success_rate - error_penalty)

def main():
    """Главная функция"""
    print("🧪 ПРОСТОЕ ТЕСТИРОВАНИЕ WORKFLOW БОТА")
    print("Совместимо со старыми версиями Python")
    print()
    
    tester = SimpleWorkflowTester()
    success = tester.run_test()
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Тест прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print("💥 Неожиданная ошибка: {}".format(e))
        sys.exit(1)
