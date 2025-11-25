#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексные тесты workflow бота и админки
Тестирует полный цикл: сообщения -> модерация -> одобрение/отклонение -> реакции
"""

import asyncio
import aiohttp
import json
import time
import random
import os
import sys
from datetime import datetime

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db

# Конфигурация для тестов
ADMIN_URL = "http://localhost:8000"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")

class WorkflowTester:
    def __init__(self):
        self.session = None
        self.test_results = {
            'messages_created': 0,
            'moderation_items': 0,
            'approvals': 0,
            'rejections': 0,
            'automatic_reactions': 0,
            'errors': []
        }
    
    async def setup(self):
        """Настройка тестовой среды"""
        print("🔧 Настройка тестовой среды...")
        
        # Создаем HTTP сессию
        self.session = aiohttp.ClientSession()
        
        # Очищаем старые тестовые данные
        await self.cleanup_test_data()
        
        # Создаем тестовые теги
        await self.create_test_tags()
        
        print("✅ Тестовая среда готова")
    
    async def cleanup_test_data(self):
        """Очистка тестовых данных"""
        try:
            # Очищаем логи и модерацию
            headers = {"Authorization": "Bearer {}".format(ADMIN_TOKEN)}
            
            async with self.session.delete("{}/api/logs".format(ADMIN_URL), headers=headers) as response:
                if response.status == 200:
                    print("🗑️ Старые логи очищены")
                else:
                    print("⚠️ Не удалось очистить логи: {}".format(response.status))
                    
        except Exception as e:
            print("⚠️ Ошибка очистки данных: {}".format(e))
    
    async def create_test_tags(self):
        """Создание тестовых тегов"""
        print("🏷️ Создаем тестовые теги...")
        
        test_tags = [
            {
                "tag": "тест_авто",
                "emoji": "🤖",
                "delay": 0,
                "match_mode": "equals",
                "require_photo": False,
                "reply_ok": "Автоматически зачтено!",
                "moderation_enabled": False,
                "counter_name": "Авто тесты"
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
        
        headers = {
            "Authorization": "Bearer {}".format(ADMIN_TOKEN),
            "Content-Type": "application/json"
        }
        
        for tag_data in test_tags:
            try:
                async with self.session.post(
                    "{}/api/tags".format(ADMIN_URL), 
                    headers=headers,
                    json=tag_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        print("✅ Создан тег: {}".format(tag_data['tag']))
                    else:
                        error_text = await response.text()
                        print("❌ Ошибка создания тега {}: {}".format(tag_data['tag'], error_text))
                        
            except Exception as e:
                print("❌ Исключение при создании тега {}: {}".format(tag_data['tag'], e))
    
    def simulate_message_data(self, message_id, tag, has_photo=False, user_id=None):
        """Симуляция данных сообщения"""
        if user_id is None:
            user_id = random.randint(100000, 999999)
            
        return {
            'chat_id': -1001234567890,
            'message_id': message_id,
            'user_id': user_id,
            'username': 'test_user_{}'.format(user_id),
            'tag': tag,
            'emoji': '🤖' if tag == 'тест_авто' else '👨‍💼',
            'text': 'Тестовое сообщение #{} с тегом {}'.format(message_id, tag),
            'caption': 'Подпись к медиа' if has_photo else '',
            'media_info': {
                'has_photo': has_photo,
                'has_video': False,
                'media_file_ids': ['test_photo_id_{}'.format(message_id)] if has_photo else []
            } if has_photo else {},
            'thread_name': 'Тестовый тред',
            'counter_name': 'Авто тесты' if tag == 'тест_авто' else 'Модерируемые тесты'
        }
    
    async def simulate_automatic_messages(self, count=10):
        """Симуляция автоматических сообщений (без модерации)"""
        print("🤖 Симулируем {} автоматических сообщений...".format(count))
        
        for i in range(count):
            message_id = 2000 + i
            message_data = self.simulate_message_data(message_id, 'тест_авто', has_photo=False)
            
            # Добавляем сразу в логи (имитируем автоматическую обработку)
            log_data = {
                'user_id': message_data['user_id'],
                'username': message_data['username'],
                'chat_id': message_data['chat_id'],
                'message_id': message_data['message_id'],
                'trigger': message_data['tag'],
                'emoji': message_data['emoji'],
                'thread_name': message_data['thread_name'],
                'media_type': '',
                'caption': message_data['caption']
            }
            
            db.add_log(log_data)
            self.test_results['automatic_reactions'] += 1
            
            # Небольшая задержка для реалистичности
            await asyncio.sleep(0.1)
        
        print("✅ Создано {} автоматических сообщений".format(count))
    
    async def simulate_moderation_messages(self, count=20):
        """Симуляция сообщений для модерации"""
        print("👨‍💼 Симулируем {} сообщений для модерации...".format(count))
        
        for i in range(count):
            message_id = 3000 + i
            has_photo = random.choice([True, False])  # Случайно с фото или без
            message_data = self.simulate_message_data(message_id, 'тест_модер', has_photo=has_photo)
            
            # Добавляем в очередь модерации
            item_id = db.add_moderation_item(message_data)
            if item_id:
                self.test_results['moderation_items'] += 1
                print("📝 Создан элемент модерации: {} (ID: {})".format(message_id, item_id))
            else:
                self.test_results['errors'].append("Не удалось создать элемент модерации для сообщения {}".format(message_id))
            
            await asyncio.sleep(0.05)
        
        print("✅ Создано {} элементов модерации".format(self.test_results['moderation_items']))
    
    async def get_moderation_queue(self):
        """Получение очереди модерации через API"""
        try:
            headers = {"Authorization": "Bearer {}".format(ADMIN_TOKEN)}
            
            async with self.session.get("{}/api/moderation".format(ADMIN_URL), headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', [])
                else:
                    error_text = await response.text()
                    self.test_results['errors'].append("Ошибка получения очереди модерации: {}".format(error_text))
                    return []
                    
        except Exception as e:
            self.test_results['errors'].append("Исключение при получении очереди: {}".format(e))
            return []
    
    async def approve_moderation(self, item_id):
        """Одобрение элемента модерации"""
        try:
            headers = {"Authorization": "Bearer {}".format(ADMIN_TOKEN)}
            
            async with self.session.post(
                "{}/api/moderation/{}/approve".format(ADMIN_URL, item_id), 
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        self.test_results['approvals'] += 1
                        return True
                    else:
                        self.test_results['errors'].append("Не удалось одобрить {}: {}".format(item_id, result.get('message')))
                        return False
                else:
                    error_text = await response.text()
                    self.test_results['errors'].append("Ошибка одобрения {}: {}".format(item_id, error_text))
                    return False
                    
        except Exception as e:
            self.test_results['errors'].append("Исключение при одобрении {}: {}".format(item_id, e))
            return False
    
    async def reject_moderation(self, item_id):
        """Отклонение элемента модерации"""
        try:
            headers = {"Authorization": "Bearer {}".format(ADMIN_TOKEN)}
            
            async with self.session.post(
                "{}/api/moderation/{}/reject".format(ADMIN_URL, item_id), 
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        self.test_results['rejections'] += 1
                        return True
                    else:
                        self.test_results['errors'].append("Не удалось отклонить {}: {}".format(item_id, result.get('message')))
                        return False
                else:
                    error_text = await response.text()
                    self.test_results['errors'].append("Ошибка отклонения {}: {}".format(item_id, error_text))
                    return False
                    
        except Exception as e:
            self.test_results['errors'].append("Исключение при отклонении {}: {}".format(item_id, e))
            return False
    
    async def process_moderation_queue(self, approve_count=10, reject_count=10):
        """Обработка очереди модерации"""
        print("⚖️ Обрабатываем очередь модерации ({} одобрений, {} отклонений)...".format(approve_count, reject_count))
        
        # Получаем очередь
        queue = await self.get_moderation_queue()
        
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
                success = await self.approve_moderation(item['id'])
                if success:
                    approved += 1
                await asyncio.sleep(0.2)  # Задержка между запросами
                
            elif rejected < reject_count:
                print("❌ Отклоняем: {} (сообщение {})".format(item['id'], item['message_id']))
                success = await self.reject_moderation(item['id'])
                if success:
                    rejected += 1
                await asyncio.sleep(0.2)
                
            else:
                break
        
        print("✅ Обработано: {} одобрений, {} отклонений".format(approved, rejected))
        return True
    
    async def verify_results(self):
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
    
    async def run_full_test(self):
        """Запуск полного теста workflow"""
        print("🚀 Запуск полного теста workflow...")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # 1. Настройка
            await self.setup()
            
            # 2. Симуляция автоматических сообщений
            await self.simulate_automatic_messages(10)
            
            # 3. Симуляция сообщений для модерации
            await self.simulate_moderation_messages(20)
            
            # 4. Небольшая пауза для обработки
            print("⏳ Пауза 2 секунды для обработки...")
            await asyncio.sleep(2)
            
            # 5. Обработка модерации
            await self.process_moderation_queue(approve_count=10, reject_count=10)
            
            # 6. Еще одна пауза для реакций
            print("⏳ Пауза 3 секунды для постановки реакций...")
            await asyncio.sleep(3)
            
            # 7. Проверка результатов
            verification = await self.verify_results()
            
            # 8. Итоговый отчет
            await self.print_final_report(verification, time.time() - start_time)
            
            return True
            
        except Exception as e:
            print("❌ Критическая ошибка теста: {}".format(e))
            self.test_results['errors'].append("Критическая ошибка: {}".format(e))
            return False
        
        finally:
            if self.session:
                await self.session.close()
    
    async def print_final_report(self, verification, duration):
        """Печать финального отчета"""
        print("\n" + "=" * 60)
        print("📊 ФИНАЛЬНЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        
        print("⏱️ Время выполнения: {:.2f} секунд".format(duration))
        print()
        
        print("📝 Созданные данные:")
        print("  - Автоматические сообщения: {}".format(self.test_results['automatic_reactions']))
        print("  - Элементы модерации: {}".format(self.test_results['moderation_items']))
        print()
        
        print("⚖️ Обработка модерации:")
        print("  - Одобрено: {}".format(self.test_results['approvals']))
        print("  - Отклонено: {}".format(self.test_results['rejections']))
        print()
        
        print("📊 Результаты в базе данных:")
        print("  - Всего логов: {}".format(verification['logs_count']))
        print("  - Одобренных в БД: {}".format(verification['moderation_stats'].get('approved', 0)))
        print("  - Отклоненных в БД: {}".format(verification['moderation_stats'].get('rejected', 0)))
        print("  - Ожидающих: {}".format(verification['moderation_stats'].get('pending', 0)))
        print("  - В очереди реакций: {}".format(verification['reaction_queue_size']))
        print()
        
        if self.test_results['errors']:
            print("❌ Ошибки ({} шт.):".format(len(self.test_results['errors'])))
            for i, error in enumerate(self.test_results['errors'][:5], 1):
                print("  {}. {}".format(i, error))
            if len(self.test_results['errors']) > 5:
                print("  ... и еще {} ошибок".format(len(self.test_results['errors']) - 5))
        else:
            print("✅ Ошибок не обнаружено!")
        
        print()
        
        # Оценка успешности
        success_rate = self.calculate_success_rate(verification)
        if success_rate >= 90:
            print("🎉 ТЕСТ ПРОЙДЕН УСПЕШНО! ({:.1f}% успешности)".format(success_rate))
        elif success_rate >= 70:
            print("⚠️ ТЕСТ ПРОЙДЕН С ЗАМЕЧАНИЯМИ ({:.1f}% успешности)".format(success_rate))
        else:
            print("❌ ТЕСТ ПРОВАЛЕН ({:.1f}% успешности)".format(success_rate))
        
        print("=" * 60)
    
    def calculate_success_rate(self, verification):
        """Расчет процента успешности"""
        expected_approvals = 10
        expected_rejections = 10
        expected_automatic = 10
        
        actual_approvals = self.test_results['approvals']
        actual_rejections = self.test_results['rejections']
        actual_automatic = self.test_results['automatic_reactions']
        
        total_expected = expected_approvals + expected_rejections + expected_automatic
        total_actual = actual_approvals + actual_rejections + actual_automatic
        
        if total_expected == 0:
            return 0
        
        success_rate = (total_actual / total_expected) * 100
        
        # Штраф за ошибки
        error_penalty = min(len(self.test_results['errors']) * 5, 30)
        
        return max(0, success_rate - error_penalty)

async def main():
    """Главная функция"""
    print("🧪 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ WORKFLOW БОТА")
    print("Проверяем: сообщения -> модерация -> одобрение/отклонение -> реакции")
    print()
    
    # Проверяем что админка доступна
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ADMIN_URL) as response:
                if response.status not in [200, 302]:  # 302 для редиректа
                    print("❌ Админка недоступна по адресу: {}".format(ADMIN_URL))
                    print("   Убедитесь что админка запущена!")
                    return False
    except Exception as e:
        print("❌ Не удается подключиться к админке: {}".format(e))
        print("   Убедитесь что админка запущена на {}".format(ADMIN_URL))
        return False
    
    # Запускаем тест
    tester = WorkflowTester()
    success = await tester.run_full_test()
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Тест прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print("💥 Неожиданная ошибка: {}".format(e))
        sys.exit(1)
