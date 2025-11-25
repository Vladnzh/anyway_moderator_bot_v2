#!/bin/bash

echo "🧪 Тестирование в разработческой среде"
echo "====================================="

# Проверяем что мы в правильной директории
if [ ! -f "test_simple.py" ]; then
    echo "❌ test_simple.py не найден!"
    echo "Запустите скрипт из корня проекта"
    exit 1
fi

# Проверяем .env.dev
if [ ! -f ".env.dev" ]; then
    echo "❌ .env.dev не найден!"
    echo "Сначала запустите: ./start-dev.sh"
    exit 1
fi

# Загружаем переменные разработки
echo "📄 Загружаем конфигурацию разработки..."
export $(grep -v '^#' .env.dev | xargs)

# Проверяем что админка запущена
echo "🔍 Проверяем доступность админки..."
if ! curl -s http://localhost:8000 > /dev/null; then
    echo "❌ Админка недоступна на http://localhost:8000"
    echo "Запустите разработческую среду: ./start-dev.sh"
    exit 1
fi

echo "✅ Админка доступна"

# Активируем виртуальное окружение если есть
if [ -d "venv" ]; then
    echo "🐍 Активируем виртуальное окружение..."
    source venv/bin/activate
fi

# Показываем конфигурацию
echo ""
echo "⚙️ Конфигурация тестирования:"
echo "  🌐 ADMIN_URL: ${ADMIN_URL:-http://localhost:8000}"
echo "  🔑 ADMIN_TOKEN: ${ADMIN_TOKEN:0:8}...${ADMIN_TOKEN: -4}"
echo "  🗄️ DATABASE: ${DATABASE_PATH:-dev_bot_data.db}"
echo "  🤖 BOT_TOKEN: ${BOT_TOKEN:0:10}...${BOT_TOKEN: -4}"

# Выбор типа теста
echo ""
echo "Выберите тип теста:"
echo "1) Быстрый тест (test_simple.py)"
echo "2) Полный workflow тест (если поддерживается)"
echo "3) Проверка оптимизаций"
echo "4) 🔥 ХАРДКОРНЫЙ СТРЕСС-ТЕСТ (test_hardcore.py)"
echo "5) Очистка тестовых данных"
echo "6) Показать статистику БД"
echo ""

read -p "Выберите (1-6): " choice

case "$choice" in
    1)
        echo ""
        echo "🚀 Запуск быстрого теста..."
        echo "=========================="
        python3 test_simple.py
        ;;
    2)
        echo ""
        echo "🚀 Запуск полного workflow теста..."
        echo "================================="
        if [ -f "test_workflow.py" ]; then
            python3 test_workflow.py
        else
            echo "❌ test_workflow.py не найден"
            echo "Используем простой тест:"
            python3 test_simple.py
        fi
        ;;
    3)
        echo ""
        echo "🔧 Проверка оптимизаций..."
        echo "========================="
        python3 -c "
import sys
sys.path.insert(0, '.')
from database import db
import time

print('🗄️ Проверка WAL mode...')
with db.get_connection() as conn:
    result = conn.execute('PRAGMA journal_mode').fetchone()
    if result and result[0].upper() == 'WAL':
        print('✅ WAL mode активен')
    else:
        print('❌ WAL mode не активен')

print('🏷️ Проверка кэширования тегов...')
start = time.time()
tags1 = db.get_tags()
time1 = time.time() - start

start = time.time()
tags2 = db.get_tags()
time2 = time.time() - start

print(f'  Первый запрос: {time1:.4f}с')
print(f'  Второй запрос: {time2:.4f}с')
if time2 < time1 * 0.8:
    print('✅ Кэширование работает')
else:
    print('⚠️ Кэширование может работать неоптимально')

print('📊 Статистика базы данных:')
stats = db.get_stats()
print(f'  Теги: {stats[\"total_tags\"]}')
print(f'  Логи: {stats[\"total_logs\"]}')
print(f'  Модерация: {stats[\"moderation\"][\"total\"]}')
"
        ;;
    4)
        echo ""
        echo "🔥 ХАРДКОРНЫЙ СТРЕСС-ТЕСТ"
        echo "========================"
        echo "⚠️ ВНИМАНИЕ: Максимальная нагрузка на систему!"
        echo "• 15 активных пользователей"
        echo "• ~30 сообщений в секунду"
        echo "• Параллельные API запросы"
        echo "• Модерация под нагрузкой"
        echo "• Привязка аккаунтов"
        echo ""
        read -p "Продолжить хардкорный тест? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            if [ -f "test_hardcore.py" ]; then
                python3 test_hardcore.py
            else
                echo "❌ test_hardcore.py не найден"
            fi
        else
            echo "❌ Хардкорный тест отменен"
        fi
        ;;
    5)
        echo ""
        echo "🗑️ Очистка тестовых данных..."
        echo "============================"
        
        read -p "Очистить тестовые данные? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            python3 -c "
import sys
sys.path.insert(0, '.')
from database import db

print('🧹 Очищаем тестовые данные...')

with db.get_connection() as conn:
    # Удаляем тестовые теги
    cursor = conn.execute(\"DELETE FROM tags WHERE tag LIKE 'тест_%'\")
    deleted_tags = cursor.rowcount
    
    # Очищаем логи
    cursor = conn.execute('DELETE FROM logs')
    deleted_logs = cursor.rowcount
    
    # Очищаем модерацию
    cursor = conn.execute('DELETE FROM moderation_queue')
    deleted_moderation = cursor.rowcount
    
    # Очищаем очередь реакций
    cursor = conn.execute('DELETE FROM reaction_queue')
    deleted_reactions = cursor.rowcount
    
    # Очищаем медиа хэши
    cursor = conn.execute('DELETE FROM media_hashes')
    deleted_media = cursor.rowcount
    
    conn.commit()

print(f'✅ Очищено:')
print(f'  Тестовые теги: {deleted_tags}')
print(f'  Логи: {deleted_logs}')
print(f'  Модерация: {deleted_moderation}')
print(f'  Реакции: {deleted_reactions}')
print(f'  Медиа хэши: {deleted_media}')
"
            echo "✅ Тестовые данные очищены"
        else
            echo "❌ Отменено"
        fi
        ;;
    6)
        echo ""
        echo "📊 Статистика базы данных..."
        echo "============================"
        python3 -c "
import sys
sys.path.insert(0, '.')
from database import db

stats = db.get_stats()
print('📈 Общая статистика:')
print(f'  Всего тегов: {stats[\"total_tags\"]}')
print(f'  Всего логов: {stats[\"total_logs\"]}')

print(f'\\n📊 Модерация:')
mod_stats = stats['moderation']
print(f'  Всего: {mod_stats[\"total\"]}')
print(f'  В ожидании: {mod_stats[\"pending\"]}')
print(f'  Одобрено: {mod_stats[\"approved\"]}')
print(f'  Отклонено: {mod_stats[\"rejected\"]}')

print(f'\\n🏷️ Топ тегов:')
for tag_stat in stats['tag_stats'][:5]:
    print(f'  {tag_stat[\"tag\"]}: {tag_stat[\"count\"]}')

# Дополнительная информация
with db.get_connection() as conn:
    reaction_queue = conn.execute('SELECT COUNT(*) FROM reaction_queue').fetchone()[0]
    media_hashes = conn.execute('SELECT COUNT(*) FROM media_hashes').fetchone()[0]
    
print(f'\\n🔄 Очереди:')
print(f'  Реакции: {reaction_queue}')
print(f'  Медиа хэши: {media_hashes}')
"
        ;;
    *)
        echo "❌ Неверный выбор (1-6)"
        exit 1
        ;;
esac

echo ""
echo "💡 Полезные команды для разработки:"
echo "  • Перезапуск: ./stop-dev.sh && ./start-dev.sh"
echo "  • Логи админки: curl http://localhost:8000/api/logs"
echo "  • Статус модерации: curl -H 'Authorization: Bearer $ADMIN_TOKEN' http://localhost:8000/api/moderation"
echo "  • Очистка БД: rm ${DATABASE_PATH:-dev_bot_data.db}"

echo ""
echo "✅ Тестирование завершено"
