#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск всех тестов для проверки работоспособности бота
"""

import subprocess
import sys
import os
import time

def run_test(test_name, test_file):
    """Запуск одного теста"""
    print("🧪 Запуск теста: {}".format(test_name))
    print("-" * 50)
    
    start_time = time.time()
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, 
                              text=True, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        
        duration = time.time() - start_time
        
        print("⏱️ Время выполнения: {:.2f} секунд".format(duration))
        
        if result.returncode == 0:
            print("✅ Тест пройден успешно!")
            print("\n📄 Вывод теста:")
            print(result.stdout)
            return True
        else:
            print("❌ Тест провален!")
            print("\n📄 Вывод теста:")
            print(result.stdout)
            if result.stderr:
                print("\n🚨 Ошибки:")
                print(result.stderr)
            return False
            
    except Exception as e:
        print("💥 Ошибка запуска теста: {}".format(e))
        return False

def main():
    """Главная функция"""
    print("🚀 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ БОТА")
    print("=" * 60)
    print()
    
    # Проверяем что мы в правильной директории
    if not os.path.exists("admin.py") or not os.path.exists("bot.py"):
        print("❌ Запустите скрипт из директории с ботом!")
        return False
    
    tests = [
        ("Простой workflow тест (совместимый)", "test_simple.py"),
        ("Полный workflow тест (требует Python 3.5+)", "test_workflow.py"),
        ("Performance тест (требует Python 3.5+)", "test_performance.py")
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_file in tests:
        if not os.path.exists(test_file):
            print("⚠️ Файл теста не найден: {}".format(test_file))
            continue
            
        success = run_test(test_name, test_file)
        
        if success:
            passed_tests += 1
        
        print("\n" + "=" * 60 + "\n")
        
        # Пауза между тестами
        if test_file != tests[-1][1]:  # Не последний тест
            print("⏳ Пауза 5 секунд между тестами...")
            time.sleep(5)
    
    # Итоговый отчет
    print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print("✅ Пройдено тестов: {}/{}".format(passed_tests, total_tests))
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Бот готов к продуктивному использованию")
        success_rate = 100
    elif passed_tests >= total_tests * 0.7:
        print("⚠️ БОЛЬШИНСТВО ТЕСТОВ ПРОЙДЕНО")
        print("🔧 Есть замечания, но основной функционал работает")
        success_rate = (passed_tests / total_tests) * 100
    else:
        print("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ")
        print("🚨 Требуется исправление ошибок перед использованием")
        success_rate = (passed_tests / total_tests) * 100
    
    print("📈 Процент успешности: {:.1f}%".format(success_rate))
    print("=" * 60)
    
    return passed_tests == total_tests

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print("💥 Критическая ошибка: {}".format(e))
        sys.exit(1)
