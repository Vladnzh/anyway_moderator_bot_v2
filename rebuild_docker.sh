#!/bin/bash

echo "🔄 Пересборка и перезапуск Docker контейнеров"
echo "============================================="

echo ""
echo "🛑 Остановка всех контейнеров..."
docker compose -p moderator-bot down

echo ""
echo "🏗️ Пересборка образов..."
docker compose -p moderator-bot build --no-cache

echo ""
echo "🚀 Запуск контейнеров..."
docker compose -p moderator-bot up -d

echo ""
echo "⏳ Ожидание 10 секунд для запуска..."
sleep 10

echo ""
echo "📊 Статус контейнеров:"
docker compose -p moderator-bot ps

echo ""
echo "📋 Логи бота (последние 20 строк):"
docker compose -p moderator-bot logs --tail=20 bot

echo ""
echo "📋 Логи админки (последние 10 строк):"
docker compose -p moderator-bot logs --tail=10 admin

echo ""
echo "✅ Пересборка завершена!"
echo ""
echo "💡 Для мониторинга логов в реальном времени:"
echo "   docker compose -p moderator-bot logs -f"
