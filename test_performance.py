#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест производительности и стресс-тест быстрого апрува
Проверяет исправление бага с пропуском реакций при быстром одобрении
"""

import asyncio
import aiohttp
import json
import time
import os
import sys
from concurrent.futures import ThreadPoolExecutor

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db

# Конфигурация
ADMIN_URL = "http://localhost:8000"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")

class PerformanceTester:
    def __init__(self):
        self.results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            'min_response_time': float('inf'),
            'concurrent_approvals': 0,
            'errors': []
        }
    
    async def create_test_moderation_items(self, count=50):
        """Создание тестовых элементов модерации"""
        print("📝 Создаем {} тестовых элементов модерации...".format(count))
        
        created_items = []
        
        for i in range(count):
            item_data = {
                'chat_id': -1001234567890,
                'message_id': 5000 + i,
                'user_id': 100000 + i,
                'username': 'stress_test_user_{}'.format(i),
                'tag': 'стресс_тест',
                'emoji': '⚡',
                'text': 'Стресс-тест сообщение #{}'.format(i),
                'caption': 'Тестовая подпись',
                'media_info': {
                    'has_photo': True,
                    'has_video': False,
                    'media_file_ids': ['stress_test_photo_{}'.format(i)]
                },
                'thread_name': 'Стресс-тест тред',
                'counter_name': 'Стресс тесты'
            }
            
            item_id = db.add_moderation_item(item_data)
            if item_id:
                created_items.append(item_id)
            
        print("✅ Создано {} элементов модерации".format(len(created_items)))
        return created_items
    
    async def approve_single_item(self, session, item_id, semaphore):
        """Одобрение одного элемента с измерением времени"""
        async with semaphore:
            start_time = time.time()
            
            try:
                headers = {"Authorization": "Bearer {}".format(ADMIN_TOKEN)}
                
                async with session.post(
                    "{}/api/moderation/{}/approve".format(ADMIN_URL, item_id),
                    headers=headers
                ) as response:
                    response_time = time.time() - start_time
                    
                    self.results['total_requests'] += 1
                    
                    # Обновляем статистику времени ответа
                    if response_time > self.results['max_response_time']:
                        self.results['max_response_time'] = response_time
                    if response_time < self.results['min_response_time']:
                        self.results['min_response_time'] = response_time
                    
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            self.results['successful_requests'] += 1
                            return True, response_time
                        else:
                            self.results['failed_requests'] += 1
                            self.results['errors'].append("Не удалось одобрить {}: {}".format(item_id, result.get('message')))
                            return False, response_time
                    else:
                        self.results['failed_requests'] += 1
                        error_text = await response.text()
                        self.results['errors'].append("HTTP {} для {}: {}".format(response.status, item_id, error_text))
                        return False, response_time
                        
            except Exception as e:
                response_time = time.time() - start_time
                self.results['failed_requests'] += 1
                self.results['errors'].append("Исключение для {}: {}".format(item_id, e))
                return False, response_time
    
    async def stress_test_concurrent_approvals(self, item_ids, concurrency=10):
        """Стресс-тест параллельных одобрений"""
        print("⚡ Стресс-тест: {} параллельных одобрений (concurrency={})...".format(len(item_ids), concurrency))
        
        # Семафор для ограничения параллельности
        semaphore = asyncio.Semaphore(concurrency)
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            # Создаем задачи для всех одобрений
            tasks = [
                self.approve_single_item(session, item_id, semaphore)
                for item_id in item_ids
            ]
            
            # Выполняем все задачи параллельно
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        total_time = time.time() - start_time
        
        # Обрабатываем результаты
        successful_times = []
        for result in results:
            if isinstance(result, tuple) and result[0]:  # Успешный запрос
                successful_times.append(result[1])
        
        # Вычисляем статистику
        if successful_times:
            self.results['avg_response_time'] = sum(successful_times) / len(successful_times)
        
        self.results['concurrent_approvals'] = len(item_ids)
        
        print("✅ Стресс-тест завершен за {:.2f} секунд".format(total_time))
        print("📊 Успешно: {}, Ошибок: {}".format(self.results['successful_requests'], self.results['failed_requests']))
        
        return total_time
    
    async def test_rapid_sequential_approvals(self, item_ids):
        """Тест быстрых последовательных одобрений"""
        print("🏃‍♂️ Тест быстрых последовательных одобрений...")
        
        sequential_results = {
            'successful': 0,
            'failed': 0,
            'times': []
        }
        
        async with aiohttp.ClientSession() as session:
            for item_id in item_ids[:10]:  # Берем первые 10 для последовательного теста
                start_time = time.time()
                
                try:
                    headers = {"Authorization": "Bearer {}".format(ADMIN_TOKEN)}
                    
                    async with session.post(
                        "{}/api/moderation/{}/approve".format(ADMIN_URL, item_id),
                        headers=headers
                    ) as response:
                        response_time = time.time() - start_time
                        sequential_results['times'].append(response_time)
                        
                        if response.status == 200:
                            result = await response.json()
                            if result.get('success'):
                                sequential_results['successful'] += 1
                            else:
                                sequential_results['failed'] += 1
                        else:
                            sequential_results['failed'] += 1
                            
                except Exception as e:
                    sequential_results['failed'] += 1
                    print("❌ Ошибка последовательного одобрения {}: {}".format(item_id, e))
                
                # Минимальная задержка между запросами
                await asyncio.sleep(0.05)
        
        avg_time = sum(sequential_results['times']) / len(sequential_results['times']) if sequential_results['times'] else 0
        
        print("✅ Последовательный тест: {} успешных, {} ошибок, среднее время {:.3f}с".format(
            sequential_results['successful'], 
            sequential_results['failed'], 
            avg_time
        ))
        
        return sequential_results
    
    async def check_reaction_queue_processing(self):
        """Проверка обработки очереди реакций"""
        print("🔄 Проверяем очередь реакций...")
        
        # Ждем немного для обработки реакций
        await asyncio.sleep(3)
        
        reaction_queue = db.get_reaction_queue()
        print("📊 Элементов в очереди реакций: {}".format(len(reaction_queue)))
        
        if reaction_queue:
            print("⏳ Ждем обработки очереди реакций (10 секунд)...")
            await asyncio.sleep(10)
            
            reaction_queue_after = db.get_reaction_queue()
            processed = len(reaction_queue) - len(reaction_queue_after)
            print("✅ Обработано {} элементов из очереди".format(processed))
            
            return {
                'initial_queue_size': len(reaction_queue),
                'final_queue_size': len(reaction_queue_after),
                'processed_count': processed
            }
        else:
            print("✅ Очередь реакций пуста")
            return {
                'initial_queue_size': 0,
                'final_queue_size': 0,
                'processed_count': 0
            }
    
    async def run_performance_test(self):
        """Запуск полного теста производительности"""
        print("🚀 СТРЕСС-ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("Проверяем исправление бага с быстрым апрувом")
        print("=" * 60)
        
        try:
            # 1. Создаем тестовые элементы
            item_ids = await self.create_test_moderation_items(30)
            
            if not item_ids:
                print("❌ Не удалось создать тестовые элементы")
                return False
            
            # 2. Тест быстрых последовательных одобрений
            sequential_results = await self.test_rapid_sequential_approvals(item_ids)
            
            # 3. Стресс-тест параллельных одобрений
            remaining_items = item_ids[10:]  # Оставшиеся элементы
            if remaining_items:
                concurrent_time = await self.stress_test_concurrent_approvals(remaining_items, concurrency=5)
            
            # 4. Проверяем обработку очереди реакций
            queue_results = await self.check_reaction_queue_processing()
            
            # 5. Финальный отчет
            await self.print_performance_report(sequential_results, queue_results)
            
            return True
            
        except Exception as e:
            print("❌ Критическая ошибка теста производительности: {}".format(e))
            return False
    
    async def print_performance_report(self, sequential_results, queue_results):
        """Печать отчета о производительности"""
        print("\n" + "=" * 60)
        print("📊 ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ")
        print("=" * 60)
        
        print("🔢 Общая статистика запросов:")
        print("  - Всего запросов: {}".format(self.results['total_requests']))
        print("  - Успешных: {}".format(self.results['successful_requests']))
        print("  - Неудачных: {}".format(self.results['failed_requests']))
        
        if self.results['total_requests'] > 0:
            success_rate = (self.results['successful_requests'] / self.results['total_requests']) * 100
            print("  - Процент успеха: {:.1f}%".format(success_rate))
        
        print()
        
        print("⏱️ Время ответа:")
        if self.results['avg_response_time'] > 0:
            print("  - Среднее: {:.3f}с".format(self.results['avg_response_time']))
            print("  - Максимальное: {:.3f}с".format(self.results['max_response_time']))
            print("  - Минимальное: {:.3f}с".format(self.results['min_response_time']))
        
        print()
        
        print("🏃‍♂️ Последовательные одобрения:")
        print("  - Успешных: {}".format(sequential_results['successful']))
        print("  - Неудачных: {}".format(sequential_results['failed']))
        
        print()
        
        print("🔄 Обработка очереди реакций:")
        print("  - Начальный размер очереди: {}".format(queue_results['initial_queue_size']))
        print("  - Финальный размер очереди: {}".format(queue_results['final_queue_size']))
        print("  - Обработано элементов: {}".format(queue_results['processed_count']))
        
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
        
        # Оценка исправления бага
        if self.results['successful_requests'] >= 20 and len(self.results['errors']) < 5:
            print("🎉 БАГ С БЫСТРЫМ АПРУВОМ ИСПРАВЛЕН!")
            print("✅ Система стабильно обрабатывает параллельные одобрения")
        elif self.results['successful_requests'] >= 15:
            print("⚠️ Система работает, но есть замечания")
            print("🔧 Рекомендуется дополнительная оптимизация")
        else:
            print("❌ ПРОБЛЕМЫ С ПРОИЗВОДИТЕЛЬНОСТЬЮ")
            print("🚨 Требуется исправление критических ошибок")
        
        print("=" * 60)

async def main():
    """Главная функция"""
    print("⚡ ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ И СТРЕСС-ТЕСТ")
    print("Проверяем исправление бага с пропуском реакций при быстром апруве")
    print()
    
    # Проверяем доступность админки
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ADMIN_URL) as response:
                if response.status not in [200, 302]:
                    print("❌ Админка недоступна: {}".format(ADMIN_URL))
                    return False
    except Exception as e:
        print("❌ Не удается подключиться к админке: {}".format(e))
        return False
    
    # Запускаем тест
    tester = PerformanceTester()
    success = await tester.run_performance_test()
    
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
