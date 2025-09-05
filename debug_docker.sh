#!/bin/bash

echo "🔍 Диагностика проблем с Docker контейнерами"
echo "============================================="

echo ""
echo "📊 1. Статус всех контейнеров:"
docker compose -p moderator-bot ps -a

echo ""
echo "🔍 2. Логи бота (последние 50 строк):"
docker compose -p moderator-bot logs --tail=50 bot

echo ""
echo "🔍 3. Логи админки (последние 20 строк):"
docker compose -p moderator-bot logs --tail=20 admin

echo ""
echo "🌐 4. Переменные окружения в контейнере админки:"
docker compose -p moderator-bot exec admin env | grep -E "(BOT_TOKEN|ADMIN_TOKEN|DATABASE_PATH)" || echo "Не удалось получить переменные"

echo ""
echo "📁 5. Проверка файлов в контейнере бота:"
docker compose -p moderator-bot exec bot ls -la /app/ || echo "Контейнер бота недоступен"

echo ""
echo "🗄️ 6. Проверка базы данных:"
docker compose -p moderator-bot exec bot ls -la /app/data/ || echo "Директория данных недоступна"

echo ""
echo "🧪 7. Тест запуска бота вручную:"
echo "Попытка запустить бот в интерактивном режиме..."
docker compose -p moderator-bot exec bot python -c "
import os
print('BOT_TOKEN:', os.getenv('BOT_TOKEN', 'НЕ УСТАНОВЛЕН'))
print('DATABASE_PATH:', os.getenv('DATABASE_PATH', 'НЕ УСТАНОВЛЕН'))

try:
    from database import db
    print('✅ Модуль database импортирован')
    db.init_database()
    print('✅ База данных инициализирована')
except Exception as e:
    print(f'❌ Ошибка базы данных: {e}')

try:
    import telegram
    print('✅ Модуль telegram импортирован')
except Exception as e:
    print(f'❌ Ошибка импорта telegram: {e}')
" || echo "Не удалось выполнить тест"

echo ""
echo "🔄 8. Перезапуск только бота:"
echo "Останавливаем бот..."
docker compose -p moderator-bot stop bot

echo "Запускаем бот заново..."
docker compose -p moderator-bot up -d bot

echo "Ждем 5 секунд..."
sleep 5

echo "Проверяем статус после перезапуска:"
docker compose -p moderator-bot ps bot

echo ""
echo "📋 9. Свежие логи бота после перезапуска:"
docker compose -p moderator-bot logs --tail=20 bot

echo ""
echo "✅ Диагностика завершена!"
echo ""
echo "💡 Если бот не запускается, проверьте:"
echo "   1. Правильность BOT_TOKEN в .env файле"
echo "   2. Доступность интернета в контейнере"
echo "   3. Права доступа к /app/data директории"
echo "   4. Логи выше на предмет ошибок Python"
