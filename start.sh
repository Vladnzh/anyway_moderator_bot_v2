#!/bin/bash

echo "🚀 Запуск/перезапуск бота (база данных сохраняется)"
echo "================================================="

# Проверяем что мы в правильной директории
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Ошибка: docker-compose.yml не найден!"
    echo "Запустите скрипт из корня проекта"
    exit 1
fi

# Проверяем .env файл
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте .env файл или используйте скрипты setup-bot-token.sh и setup-admin-token.sh"
    exit 1
fi

echo "🛑 Останавливаем контейнеры..."
docker compose down

echo "📁 Настраиваем права доступа к базе данных..."
mkdir -p data
chmod 755 data
touch data/bot_data.db data/.gitkeep
chmod 644 data/bot_data.db
chown -R 1000:1000 data/ 2>/dev/null || echo "⚠️ Не удалось установить владельца (выполните: sudo chown -R 1000:1000 data/)"

echo "🏗️ Собираем образы..."
docker compose build

echo "🚀 Запускаем контейнеры..."
docker compose up -d

echo "⏳ Ждём запуска (10 секунд)..."
sleep 10

echo "📊 Статус контейнеров:"
docker compose ps

echo ""
echo "✅ Бот запущен!"
echo "🌐 Админка: http://localhost:8000"
echo "📁 База данных: ./data/bot_data.db (сохранена)"

# Показываем админ токен если есть
if [ -f ".env" ]; then
    source .env
    if [ -n "$ADMIN_TOKEN" ]; then
        echo "🔑 Токен для входа: $ADMIN_TOKEN"
    fi
fi
