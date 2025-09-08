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

# Показываем конфигурацию если есть .env
if [ -f ".env" ]; then
    source .env
    if [ -n "$ADMIN_TOKEN" ]; then
        echo "🔑 Токен для входа: $ADMIN_TOKEN"
    fi
    
    echo ""
    echo "🔧 Конфигурация бэкенда:"
    if [ -n "$ADMIN_URL" ]; then
        echo "📊 Admin URL: $ADMIN_URL"
    else
        echo "📊 Admin URL: не настроен"
    fi
    
    if [ -n "$FRONTEND_URL" ]; then
        echo "🌐 Frontend URL: $FRONTEND_URL"
    else
        echo "🌐 Frontend URL: не настроен"
    fi
    
    if [ -n "$BOT_SHARED_SECRET" ]; then
        # Показываем только первые и последние 8 символов секрета
        secret_masked="${BOT_SHARED_SECRET:0:8}...${BOT_SHARED_SECRET: -8}"
        echo "🔐 Shared Secret: $secret_masked"
    else
        echo "🔐 Shared Secret: не настроен"
    fi
fi
