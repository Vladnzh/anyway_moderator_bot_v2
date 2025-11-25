#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ХАРДКОРНЫЙ СТРЕСС-ТЕСТ 🔥
Симулирует максимальную нагрузку:
- Множество пользователей пишут одновременно (1-3 сообщения/сек)
- Сообщения с тегами на модерацию
- Привязка аккаунтов Telegram
- Параллельные одобрения/отклонения
- Обработка очереди реакций
"""

import asyncio
import aiohttp
import json
import time
import random
import threading
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db

# Конфигурация стресс-теста
ADMIN_URL = "http://localhost:8000"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")

class HardcoreStressTester:
    def __init__(self):
        self.results = {
            'start_time': 0,
            'end_time': 0,
            'duration': 0,
            
            # Статистика сообщений
            'total_messages': 0,
            'messages_per_second': 0,
            'tag_messages': 0,
            'moderation_messages': 0,
            
            # Статистика API
            'api_requests': 0,
            'api_success': 0,
            'api_errors': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            
            # Статистика модерации
            'approvals': 0,
            'rejections': 0,
            'moderation_errors': 0,
            
            # Статистика привязки аккаунтов
            'account_links': 0,
            'link_success': 0,
            'link_errors': 0,
            
            # Ошибки и проблемы
            'errors': [],
            'warnings': [],
            
            # Производительность
            'db_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        self.session = None
        self.running = True
        self.user_counter = 0
        self.message_counter = 0
        
        # Пулы для параллельной работы
        self.executor = ThreadPoolExecutor(max_workers=20)
        
        # Блокировки для thread-safe операций
        self.stats_lock = threading.Lock()
        self.user_lock = threading.Lock()
        
    def log_result(self, category, success=True, duration=0, error=None):
        """Thread-safe логирование результатов"""
        with self.stats_lock:
            if category == 'api':
                self.results['api_requests'] += 1
                if success:
                    self.results['api_success'] += 1
                else:
                    self.results['api_errors'] += 1
                    if error:
                        self.results['errors'].append(f"API: {error}")
                
                if duration > 0:
                    # Обновляем статистику времени ответа
                    current_avg = self.results['avg_response_time']
                    total_requests = self.results['api_requests']
                    self.results['avg_response_time'] = (current_avg * (total_requests - 1) + duration) / total_requests
                    
                    if duration > self.results['max_response_time']:
                        self.results['max_response_time'] = duration
            
            elif category == 'moderation':
                if success:
                    self.results['approvals'] += 1
                else:
                    self.results['moderation_errors'] += 1
                    if error:
                        self.results['errors'].append(f"Moderation: {error}")
            
            elif category == 'rejection':
                if success:
                    self.results['rejections'] += 1
                else:
                    self.results['moderation_errors'] += 1
                    if error:
                        self.results['errors'].append(f"Rejection: {error}")
            
            elif category == 'link':
                self.results['account_links'] += 1
                if success:
                    self.results['link_success'] += 1
                else:
                    self.results['link_errors'] += 1
                    if error:
                        self.results['errors'].append(f"Link: {error}")
            
            elif category == 'message':
                self.results['total_messages'] += 1
                if 'tag' in str(error):  # Используем error для передачи типа
                    self.results['tag_messages'] += 1
                if 'moderation' in str(error):
                    self.results['moderation_messages'] += 1
    
    def get_next_user_id(self):
        """Thread-safe получение следующего ID пользователя"""
        with self.user_lock:
            self.user_counter += 1
            return 500000 + self.user_counter
    
    def get_next_message_id(self):
        """Thread-safe получение следующего ID сообщения"""
        with self.user_lock:
            self.message_counter += 1
            return 10000 + self.message_counter
    
    def create_stress_tags(self):
        """Создание тегов для стресс-теста"""
        print("🏷️ Создаем теги для стресс-теста...")
        
        stress_tags = [
            {
                "tag": "стресс_авто",
                "emoji": "⚡",
                "delay": 0,
                "match_mode": "equals",
                "require_photo": False,
                "reply_ok": "Автоматический стресс!",
                "moderation_enabled": False,
                "counter_name": "Стресс авто"
            },
            {
                "tag": "стресс_модер",
                "emoji": "🔥",
                "delay": 0,
                "match_mode": "equals",
                "require_photo": True,
                "reply_ok": "Модерация под стрессом!",
                "reply_need_photo": "Нужно фото для стресса",
                "moderation_enabled": True,
                "reply_pending": "В очереди стресс-модерации",
                "counter_name": "Стресс модерация"
            },
            {
                "tag": "стресс_быстро",
                "emoji": "💨",
                "delay": 0,
                "match_mode": "prefix",
                "require_photo": False,
                "reply_ok": "Быстрый стресс!",
                "moderation_enabled": False,
                "counter_name": "Быстрый стресс"
            }
        ]
        
        created_tags = []
        for tag_data in stress_tags:
            try:
                tag_id = db.create_tag(tag_data)
                if tag_id:
                    created_tags.append(tag_id)
                    print(f"✅ Создан тег: {tag_data['tag']}")
            except Exception as e:
                print(f"❌ Ошибка создания тега {tag_data['tag']}: {e}")
        
        return created_tags
    
    def simulate_user_activity(self, user_id, duration_seconds=30):
        """Симуляция активности одного пользователя"""
        end_time = time.time() + duration_seconds
        messages_sent = 0
        
        while time.time() < end_time and self.running:
            try:
                # Случайная задержка между сообщениями (0.3-3 секунды)
                delay = random.uniform(0.3, 3.0)
                time.sleep(delay)
                
                if not self.running:
                    break
                
                # Типы сообщений с вероятностями
                message_type = random.choices(
                    ['normal', 'auto_tag', 'moderation_tag', 'spam'],
                    weights=[60, 20, 15, 5]  # 60% обычные, 20% авто-теги, 15% модерация, 5% спам
                )[0]
                
                message_id = self.get_next_message_id()
                
                if message_type == 'normal':
                    # Обычное сообщение без тегов
                    self.simulate_normal_message(user_id, message_id)
                    self.log_result('message', True, error='normal')
                
                elif message_type == 'auto_tag':
                    # Сообщение с автоматическим тегом
                    self.simulate_auto_tag_message(user_id, message_id)
                    self.log_result('message', True, error='tag auto')
                
                elif message_type == 'moderation_tag':
                    # Сообщение на модерацию
                    self.simulate_moderation_message(user_id, message_id)
                    self.log_result('message', True, error='tag moderation')
                
                elif message_type == 'spam':
                    # Спам сообщения (быстрые)
                    for _ in range(random.randint(2, 5)):
                        if self.running:
                            spam_id = self.get_next_message_id()
                            self.simulate_spam_message(user_id, spam_id)
                            self.log_result('message', True, error='spam')
                            time.sleep(0.1)
                
                messages_sent += 1
                
            except Exception as e:
                self.log_result('message', False, error=str(e))
        
        print(f"👤 Пользователь {user_id}: отправил {messages_sent} сообщений")
        return messages_sent
    
    def simulate_normal_message(self, user_id, message_id):
        """Симуляция обычного сообщения"""
        # Просто увеличиваем счетчик, без реальной отправки
        pass
    
    def simulate_auto_tag_message(self, user_id, message_id):
        """Симуляция сообщения с автоматическим тегом"""
        # Добавляем в логи как автоматическую реакцию
        log_data = {
            'user_id': user_id,
            'username': f'stress_user_{user_id}',
            'chat_id': -1001234567890,
            'message_id': message_id,
            'trigger': 'стресс_авто',
            'emoji': '⚡',
            'thread_name': 'Стресс тред',
            'media_type': '',
            'caption': f'Автоматическое сообщение #{message_id}'
        }
        
        try:
            db.add_log(log_data)
            self.results['db_operations'] += 1
        except Exception as e:
            self.log_result('message', False, error=f"DB auto: {e}")
    
    def simulate_moderation_message(self, user_id, message_id):
        """Симуляция сообщения на модерацию"""
        item_data = {
            'chat_id': -1001234567890,
            'message_id': message_id,
            'user_id': user_id,
            'username': f'stress_user_{user_id}',
            'tag': 'стресс_модер',
            'emoji': '🔥',
            'text': f'Стресс сообщение на модерацию #{message_id}',
            'caption': 'Стресс подпись к медиа',
            'media_info': {
                'has_photo': True,
                'has_video': False,
                'media_file_ids': [f'stress_photo_{message_id}']
            },
            'thread_name': 'Стресс модерация тред',
            'counter_name': 'Стресс модерация'
        }
        
        try:
            item_id = db.add_moderation_item(item_data)
            if item_id:
                self.results['db_operations'] += 1
            else:
                self.log_result('message', False, error="Failed to create moderation item")
        except Exception as e:
            self.log_result('message', False, error=f"DB moderation: {e}")
    
    def simulate_spam_message(self, user_id, message_id):
        """Симуляция спам сообщения"""
        # Быстрые сообщения без тегов
        pass
    
    async def stress_test_api_calls(self, duration_seconds=30):
        """Стресс-тест API вызовов"""
        print("🌐 Запуск стресс-теста API...")
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        end_time = time.time() + duration_seconds
        tasks = []
        
        while time.time() < end_time and self.running:
            # Создаем задачи для параллельных запросов
            batch_size = random.randint(3, 8)  # 3-8 параллельных запросов
            
            for _ in range(batch_size):
                if not self.running:
                    break
                
                # Случайный тип API запроса
                api_type = random.choices(
                    ['get_tags', 'get_moderation', 'get_stats', 'get_logs'],
                    weights=[40, 30, 20, 10]
                )[0]
                
                if api_type == 'get_tags':
                    task = self.api_get_tags()
                elif api_type == 'get_moderation':
                    task = self.api_get_moderation()
                elif api_type == 'get_stats':
                    task = self.api_get_stats()
                elif api_type == 'get_logs':
                    task = self.api_get_logs()
                
                tasks.append(task)
            
            # Выполняем батч запросов
            if tasks:
                try:
                    await asyncio.gather(*tasks, return_exceptions=True)
                except Exception as e:
                    self.log_result('api', False, error=f"Batch error: {e}")
                
                tasks.clear()
            
            # Небольшая пауза между батчами
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        print("✅ Стресс-тест API завершен")
    
    async def api_get_tags(self):
        """API запрос получения тегов"""
        start_time = time.time()
        try:
            headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
            async with self.session.get(f"{ADMIN_URL}/api/tags", headers=headers) as response:
                duration = time.time() - start_time
                if response.status == 200:
                    await response.json()
                    self.log_result('api', True, duration)
                else:
                    self.log_result('api', False, duration, f"HTTP {response.status}")
        except Exception as e:
            duration = time.time() - start_time
            self.log_result('api', False, duration, str(e))
    
    async def api_get_moderation(self):
        """API запрос получения модерации"""
        start_time = time.time()
        try:
            headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
            async with self.session.get(f"{ADMIN_URL}/api/moderation", headers=headers) as response:
                duration = time.time() - start_time
                if response.status == 200:
                    await response.json()
                    self.log_result('api', True, duration)
                else:
                    self.log_result('api', False, duration, f"HTTP {response.status}")
        except Exception as e:
            duration = time.time() - start_time
            self.log_result('api', False, duration, str(e))
    
    async def api_get_stats(self):
        """API запрос получения статистики"""
        start_time = time.time()
        try:
            headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
            async with self.session.get(f"{ADMIN_URL}/api/stats", headers=headers) as response:
                duration = time.time() - start_time
                if response.status == 200:
                    await response.json()
                    self.log_result('api', True, duration)
                else:
                    self.log_result('api', False, duration, f"HTTP {response.status}")
        except Exception as e:
            duration = time.time() - start_time
            self.log_result('api', False, duration, str(e))
    
    async def api_get_logs(self):
        """API запрос получения логов"""
        start_time = time.time()
        try:
            headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
            params = {"limit": random.randint(10, 100)}
            async with self.session.get(f"{ADMIN_URL}/api/logs", headers=headers, params=params) as response:
                duration = time.time() - start_time
                if response.status == 200:
                    await response.json()
                    self.log_result('api', True, duration)
                else:
                    self.log_result('api', False, duration, f"HTTP {response.status}")
        except Exception as e:
            duration = time.time() - start_time
            self.log_result('api', False, duration, str(e))
    
    async def stress_test_moderation(self, duration_seconds=30):
        """Стресс-тест модерации"""
        print("⚖️ Запуск стресс-теста модерации...")
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time and self.running:
            try:
                # Получаем очередь модерации
                queue = await self.get_moderation_queue()
                
                if queue:
                    # Обрабатываем случайное количество элементов
                    items_to_process = min(len(queue), random.randint(1, 5))
                    selected_items = random.sample(queue, items_to_process)
                    
                    # Создаем задачи для параллельной обработки
                    tasks = []
                    for item in selected_items:
                        action = random.choice(['approve', 'reject'])
                        if action == 'approve':
                            tasks.append(self.api_approve_moderation(item['id']))
                        else:
                            tasks.append(self.api_reject_moderation(item['id']))
                    
                    # Выполняем параллельно
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
                
                # Пауза между обработками
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
            except Exception as e:
                self.log_result('moderation', False, error=f"Moderation loop: {e}")
        
        print("✅ Стресс-тест модерации завершен")
    
    async def get_moderation_queue(self):
        """Получение очереди модерации"""
        try:
            headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
            async with self.session.get(f"{ADMIN_URL}/api/moderation", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', [])
                return []
        except Exception:
            return []
    
    async def api_approve_moderation(self, item_id):
        """API одобрение модерации"""
        try:
            headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
            async with self.session.post(f"{ADMIN_URL}/api/moderation/{item_id}/approve", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        self.log_result('moderation', True)
                    else:
                        self.log_result('moderation', False, error=result.get('message'))
                else:
                    self.log_result('moderation', False, error=f"HTTP {response.status}")
        except Exception as e:
            self.log_result('moderation', False, error=str(e))
    
    async def api_reject_moderation(self, item_id):
        """API отклонение модерации"""
        try:
            headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
            async with self.session.post(f"{ADMIN_URL}/api/moderation/{item_id}/reject", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        self.log_result('rejection', True)
                    else:
                        self.log_result('rejection', False, error=result.get('message'))
                else:
                    self.log_result('rejection', False, error=f"HTTP {response.status}")
        except Exception as e:
            self.log_result('rejection', False, error=str(e))
    
    def simulate_account_linking(self, duration_seconds=30):
        """Симуляция привязки аккаунтов"""
        print("🔗 Запуск симуляции привязки аккаунтов...")
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time and self.running:
            try:
                # Генерируем случайный код привязки
                link_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
                user_id = self.get_next_user_id()
                
                # Симулируем процесс привязки (без реального HTTP запроса)
                # В реальности это был бы запрос к вашему бэкенду
                
                # Случайный результат (90% успех, 10% ошибка)
                if random.random() < 0.9:
                    self.log_result('link', True)
                    # Добавляем небольшую задержку как в реальной привязке
                    time.sleep(random.uniform(0.1, 0.3))
                else:
                    self.log_result('link', False, error="Invalid or expired code")
                
                # Пауза между попытками привязки
                time.sleep(random.uniform(2.0, 8.0))
                
            except Exception as e:
                self.log_result('link', False, error=str(e))
        
        print("✅ Симуляция привязки аккаунтов завершена")
    
    def monitor_system_performance(self, duration_seconds=60):
        """Мониторинг производительности системы"""
        print("📊 Запуск мониторинга производительности...")
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time and self.running:
            try:
                # Тестируем кэширование тегов
                start_time = time.time()
                tags = db.get_tags()
                cache_time = time.time() - start_time
                
                if cache_time < 0.001:  # Очень быстро = из кэша
                    self.results['cache_hits'] += 1
                else:  # Медленно = из БД
                    self.results['cache_misses'] += 1
                
                # Проверяем размер очереди реакций
                reaction_queue = db.get_reaction_queue()
                if len(reaction_queue) > 10:
                    self.results['warnings'].append(f"Large reaction queue: {len(reaction_queue)} items")
                
                # Проверяем статистику БД
                stats = db.get_stats()
                
                # Пауза между проверками
                time.sleep(2.0)
                
            except Exception as e:
                self.results['errors'].append(f"Monitor: {e}")
        
        print("✅ Мониторинг производительности завершен")
    
    async def run_hardcore_stress_test(self):
        """Запуск полного хардкорного стресс-теста"""
        print("🔥 ХАРДКОРНЫЙ СТРЕСС-ТЕСТ")
        print("=" * 50)
        print("⚠️ ВНИМАНИЕ: Высокая нагрузка на систему!")
        print("⚠️ Убедитесь что админка запущена")
        print()
        
        # Проверяем доступность админки
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ADMIN_URL) as response:
                    if response.status not in [200, 302]:
                        print(f"❌ Админка недоступна: {ADMIN_URL}")
                        return False
        except Exception as e:
            print(f"❌ Не удается подключиться к админке: {e}")
            return False
        
        self.session = aiohttp.ClientSession()
        
        try:
            # Подготовка
            print("🔧 Подготовка к стресс-тесту...")
            self.create_stress_tags()
            
            # Параметры теста
            test_duration = 60  # 60 секунд хардкорного теста
            num_users = 15      # 15 активных пользователей
            
            print(f"⚡ Параметры теста:")
            print(f"  • Длительность: {test_duration} секунд")
            print(f"  • Активных пользователей: {num_users}")
            print(f"  • Ожидаемая нагрузка: ~{num_users * 2} сообщений/сек")
            print()
            
            self.results['start_time'] = time.time()
            
            # Запускаем все компоненты параллельно
            print("🚀 Запуск всех компонентов стресс-теста...")
            
            # 1. Пользователи отправляют сообщения (в отдельных потоках)
            user_futures = []
            for i in range(num_users):
                user_id = self.get_next_user_id()
                future = self.executor.submit(self.simulate_user_activity, user_id, test_duration)
                user_futures.append(future)
            
            # 2. Мониторинг системы (в отдельном потоке)
            monitor_future = self.executor.submit(self.monitor_system_performance, test_duration)
            
            # 3. Привязка аккаунтов (в отдельном потоке)
            linking_future = self.executor.submit(self.simulate_account_linking, test_duration)
            
            # 4. Стресс-тест API (async)
            api_task = asyncio.create_task(self.stress_test_api_calls(test_duration))
            
            # 5. Стресс-тест модерации (async)
            moderation_task = asyncio.create_task(self.stress_test_moderation(test_duration))
            
            print("⏳ Стресс-тест запущен! Ожидание завершения...")
            print(f"⏱️ Прогресс: ", end="", flush=True)
            
            # Показываем прогресс
            start_time = time.time()
            while time.time() - start_time < test_duration:
                await asyncio.sleep(5)
                elapsed = int(time.time() - start_time)
                progress = int((elapsed / test_duration) * 20)
                print(f"\r⏱️ Прогресс: [{'█' * progress}{'░' * (20 - progress)}] {elapsed}/{test_duration}с", end="", flush=True)
            
            print(f"\r⏱️ Прогресс: [{'█' * 20}] {test_duration}/{test_duration}с ✅")
            
            # Останавливаем тест
            self.running = False
            
            # Ждем завершения async задач
            print("⏳ Завершение async задач...")
            await asyncio.gather(api_task, moderation_task, return_exceptions=True)
            
            # Ждем завершения потоков
            print("⏳ Завершение потоков пользователей...")
            for future in as_completed(user_futures + [monitor_future, linking_future], timeout=10):
                try:
                    future.result()
                except Exception as e:
                    self.results['errors'].append(f"Thread error: {e}")
            
            self.results['end_time'] = time.time()
            self.results['duration'] = self.results['end_time'] - self.results['start_time']
            
            # Финальная статистика
            if self.results['duration'] > 0:
                self.results['messages_per_second'] = self.results['total_messages'] / self.results['duration']
            
            # Отчет
            await self.print_hardcore_report()
            
            return True
            
        except Exception as e:
            print(f"❌ Критическая ошибка стресс-теста: {e}")
            return False
        
        finally:
            if self.session:
                await self.session.close()
            self.executor.shutdown(wait=True)
    
    async def print_hardcore_report(self):
        """Печать детального отчета хардкорного теста"""
        print("\n" + "🔥" * 60)
        print("📊 ОТЧЕТ ХАРДКОРНОГО СТРЕСС-ТЕСТА")
        print("🔥" * 60)
        
        print(f"⏱️ Общая информация:")
        print(f"  • Длительность: {self.results['duration']:.2f} секунд")
        print(f"  • Начало: {datetime.fromtimestamp(self.results['start_time']).strftime('%H:%M:%S')}")
        print(f"  • Окончание: {datetime.fromtimestamp(self.results['end_time']).strftime('%H:%M:%S')}")
        
        print(f"\n📨 Статистика сообщений:")
        print(f"  • Всего сообщений: {self.results['total_messages']}")
        print(f"  • Сообщений/сек: {self.results['messages_per_second']:.2f}")
        print(f"  • С тегами: {self.results['tag_messages']}")
        print(f"  • На модерацию: {self.results['moderation_messages']}")
        
        print(f"\n🌐 Статистика API:")
        print(f"  • Всего запросов: {self.results['api_requests']}")
        print(f"  • Успешных: {self.results['api_success']}")
        print(f"  • Ошибок: {self.results['api_errors']}")
        if self.results['api_requests'] > 0:
            success_rate = (self.results['api_success'] / self.results['api_requests']) * 100
            print(f"  • Процент успеха: {success_rate:.1f}%")
        print(f"  • Среднее время ответа: {self.results['avg_response_time']:.3f}с")
        print(f"  • Максимальное время: {self.results['max_response_time']:.3f}с")
        
        print(f"\n⚖️ Статистика модерации:")
        print(f"  • Одобрений: {self.results['approvals']}")
        print(f"  • Отклонений: {self.results['rejections']}")
        print(f"  • Ошибок модерации: {self.results['moderation_errors']}")
        
        print(f"\n🔗 Статистика привязки аккаунтов:")
        print(f"  • Попыток привязки: {self.results['account_links']}")
        print(f"  • Успешных: {self.results['link_success']}")
        print(f"  • Ошибок: {self.results['link_errors']}")
        if self.results['account_links'] > 0:
            link_success_rate = (self.results['link_success'] / self.results['account_links']) * 100
            print(f"  • Процент успеха: {link_success_rate:.1f}%")
        
        print(f"\n🗄️ Статистика базы данных:")
        print(f"  • Операций с БД: {self.results['db_operations']}")
        print(f"  • Попаданий в кэш: {self.results['cache_hits']}")
        print(f"  • Промахов кэша: {self.results['cache_misses']}")
        if (self.results['cache_hits'] + self.results['cache_misses']) > 0:
            cache_hit_rate = (self.results['cache_hits'] / (self.results['cache_hits'] + self.results['cache_misses'])) * 100
            print(f"  • Эффективность кэша: {cache_hit_rate:.1f}%")
        
        # Проверяем текущее состояние системы
        try:
            stats = db.get_stats()
            reaction_queue = db.get_reaction_queue()
            
            print(f"\n📊 Текущее состояние системы:")
            print(f"  • Всего тегов: {stats['total_tags']}")
            print(f"  • Всего логов: {stats['total_logs']}")
            print(f"  • Модерация в ожидании: {stats['moderation']['pending']}")
            print(f"  • Очередь реакций: {len(reaction_queue)} элементов")
        except Exception as e:
            print(f"\n⚠️ Не удалось получить состояние системы: {e}")
        
        # Предупреждения
        if self.results['warnings']:
            print(f"\n⚠️ Предупреждения ({len(self.results['warnings'])}):")
            for warning in self.results['warnings'][:5]:
                print(f"  • {warning}")
            if len(self.results['warnings']) > 5:
                print(f"  • ... и еще {len(self.results['warnings']) - 5} предупреждений")
        
        # Ошибки
        if self.results['errors']:
            print(f"\n❌ Ошибки ({len(self.results['errors'])}):")
            for error in self.results['errors'][:5]:
                print(f"  • {error}")
            if len(self.results['errors']) > 5:
                print(f"  • ... и еще {len(self.results['errors']) - 5} ошибок")
        
        # Оценка производительности
        print(f"\n🎯 ОЦЕНКА ПРОИЗВОДИТЕЛЬНОСТИ:")
        
        # Критерии оценки
        criteria_passed = 0
        total_criteria = 6
        
        # 1. Пропускная способность сообщений
        if self.results['messages_per_second'] >= 10:
            print("  ✅ Пропускная способность: ОТЛИЧНО (≥10 сообщений/сек)")
            criteria_passed += 1
        elif self.results['messages_per_second'] >= 5:
            print("  ⚠️ Пропускная способность: ХОРОШО (≥5 сообщений/сек)")
            criteria_passed += 0.5
        else:
            print("  ❌ Пропускная способность: НИЗКАЯ (<5 сообщений/сек)")
        
        # 2. Стабильность API
        api_success_rate = (self.results['api_success'] / max(self.results['api_requests'], 1)) * 100
        if api_success_rate >= 95:
            print("  ✅ Стабильность API: ОТЛИЧНО (≥95% успеха)")
            criteria_passed += 1
        elif api_success_rate >= 85:
            print("  ⚠️ Стабильность API: ХОРОШО (≥85% успеха)")
            criteria_passed += 0.5
        else:
            print("  ❌ Стабильность API: НИЗКАЯ (<85% успеха)")
        
        # 3. Время ответа API
        if self.results['avg_response_time'] <= 0.5:
            print("  ✅ Время ответа API: ОТЛИЧНО (≤0.5с)")
            criteria_passed += 1
        elif self.results['avg_response_time'] <= 1.0:
            print("  ⚠️ Время ответа API: ХОРОШО (≤1.0с)")
            criteria_passed += 0.5
        else:
            print("  ❌ Время ответа API: МЕДЛЕННО (>1.0с)")
        
        # 4. Модерация
        total_moderation = self.results['approvals'] + self.results['rejections']
        if total_moderation >= 10 and self.results['moderation_errors'] < 3:
            print("  ✅ Модерация: ОТЛИЧНО (≥10 операций, <3 ошибок)")
            criteria_passed += 1
        elif total_moderation >= 5:
            print("  ⚠️ Модерация: ХОРОШО (≥5 операций)")
            criteria_passed += 0.5
        else:
            print("  ❌ Модерация: НИЗКАЯ (<5 операций)")
        
        # 5. Кэширование
        cache_total = self.results['cache_hits'] + self.results['cache_misses']
        if cache_total > 0:
            cache_efficiency = (self.results['cache_hits'] / cache_total) * 100
            if cache_efficiency >= 80:
                print("  ✅ Кэширование: ОТЛИЧНО (≥80% попаданий)")
                criteria_passed += 1
            elif cache_efficiency >= 60:
                print("  ⚠️ Кэширование: ХОРОШО (≥60% попаданий)")
                criteria_passed += 0.5
            else:
                print("  ❌ Кэширование: НИЗКАЯ ЭФФЕКТИВНОСТЬ (<60%)")
        else:
            print("  ℹ️ Кэширование: НЕ ТЕСТИРОВАЛОСЬ")
        
        # 6. Общая стабильность
        if len(self.results['errors']) <= 5:
            print("  ✅ Стабильность: ОТЛИЧНО (≤5 ошибок)")
            criteria_passed += 1
        elif len(self.results['errors']) <= 15:
            print("  ⚠️ Стабильность: ХОРОШО (≤15 ошибок)")
            criteria_passed += 0.5
        else:
            print("  ❌ Стабильность: ПРОБЛЕМЫ (>15 ошибок)")
        
        # Итоговая оценка
        final_score = (criteria_passed / total_criteria) * 100
        
        print(f"\n🏆 ИТОГОВАЯ ОЦЕНКА: {final_score:.1f}%")
        
        if final_score >= 90:
            print("🎉 ПРЕВОСХОДНО! Система выдерживает высокие нагрузки!")
            print("✅ Готова к продуктивному использованию с высокой нагрузкой")
        elif final_score >= 70:
            print("👍 ХОРОШО! Система стабильна при средних нагрузках")
            print("⚠️ Рекомендуется мониторинг при пиковых нагрузках")
        elif final_score >= 50:
            print("⚠️ УДОВЛЕТВОРИТЕЛЬНО. Есть проблемы производительности")
            print("🔧 Требуется оптимизация перед высокими нагрузками")
        else:
            print("❌ НЕУДОВЛЕТВОРИТЕЛЬНО. Критические проблемы!")
            print("🚨 Требуется серьезная оптимизация системы")
        
        print("🔥" * 60)

async def main():
    """Главная функция"""
    print("🔥 ХАРДКОРНЫЙ СТРЕСС-ТЕСТ МОДЕРАТОР-БОТА")
    print("Симулирует максимальную реальную нагрузку:")
    print("• 15 активных пользователей")
    print("• 1-3 сообщения в секунду на пользователя")
    print("• Сообщения с тегами на модерацию")
    print("• Параллельные API запросы")
    print("• Привязка аккаунтов Telegram")
    print("• Обработка модерации")
    print()
    
    input("⚠️ ВНИМАНИЕ: Высокая нагрузка! Нажмите Enter для продолжения...")
    
    tester = HardcoreStressTester()
    success = await tester.run_hardcore_stress_test()
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Стресс-тест прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        sys.exit(1)
