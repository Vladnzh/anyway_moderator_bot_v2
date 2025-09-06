#!/bin/bash

echo "🛑 Остановка бота (база данных сохраняется)"
echo "=========================================="

# Проверяем что мы в правильной директории
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Ошибка: docker-compose.yml не найден!"
    echo "Запустите скрипт из корня проекта"
    exit 1
fi

echo "🛑 Останавливаем контейнеры..."
docker compose down

echo "🧹 Очищаем неиспользуемые Docker образы..."
docker system prune -f

echo "📊 Статус после остановки:"
docker compose ps

echo ""
echo "✅ Бот остановлен!"
echo "📁 База данных сохранена в: ./data/bot_data.db"
echo ""
echo "💡 Для запуска используйте: ./start.sh"
