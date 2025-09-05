#!/bin/bash
set -e

# Скрипт развертывания на Hetzner
# Использование: ./deploy.sh [production|staging]

ENVIRONMENT=${1:-production}
PROJECT_NAME="moderator-bot"
COMPOSE_FILE="docker-compose.yml"

echo "🚀 Развертывание $PROJECT_NAME в режиме $ENVIRONMENT"

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env с переменными:"
    echo "BOT_TOKEN=your_bot_token"
    echo "ADMIN_TOKEN=your_admin_token"
    exit 1
fi

# Загружаем переменные окружения
source .env

# Проверяем обязательные переменные
if [ -z "$BOT_TOKEN" ] || [ -z "$ADMIN_TOKEN" ]; then
    echo "❌ Не установлены обязательные переменные BOT_TOKEN и ADMIN_TOKEN в .env"
    exit 1
fi

echo "✅ Переменные окружения загружены"

# Останавливаем старые контейнеры
echo "🛑 Остановка старых контейнеров..."
docker-compose -p $PROJECT_NAME down --remove-orphans || true

# Собираем образы
echo "🔨 Сборка Docker образов..."
docker-compose -p $PROJECT_NAME build --no-cache

# Выполняем миграцию данных если нужно
if [ -f "config_json" ] || [ -f "logs.json" ]; then
    echo "📦 Обнаружены JSON файлы, выполняем миграцию..."
    
    # Создаем временный контейнер для миграции
    docker run --rm \
        -v $(pwd):/app \
        -v ${PROJECT_NAME}_bot_data:/app/data \
        --workdir /app \
        ${PROJECT_NAME}_admin:latest \
        python migrate_to_sqlite.py
    
    echo "✅ Миграция завершена"
fi

# Запускаем сервисы
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🌐 Запуск в production режиме с Nginx..."
    docker-compose -p $PROJECT_NAME --profile production up -d
else
    echo "🔧 Запуск в development режиме..."
    docker-compose -p $PROJECT_NAME up -d bot admin
fi

# Ждем запуска сервисов
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверяем статус
echo "📊 Проверка статуса сервисов..."
docker-compose -p $PROJECT_NAME ps

# Проверяем здоровье админки
echo "🏥 Проверка здоровья админки..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Админка работает: http://localhost:8000"
else
    echo "⚠️ Админка может быть еще не готова, проверьте логи:"
    echo "docker-compose -p $PROJECT_NAME logs admin"
fi

# Показываем полезную информацию
echo ""
echo "🎉 Развертывание завершено!"
echo ""
echo "📋 Полезные команды:"
echo "  Логи:           docker-compose -p $PROJECT_NAME logs -f"
echo "  Статус:         docker-compose -p $PROJECT_NAME ps"
echo "  Остановка:      docker-compose -p $PROJECT_NAME down"
echo "  Перезапуск:     docker-compose -p $PROJECT_NAME restart"
echo ""
echo "🌐 Доступ:"
echo "  Админка:        http://localhost:8000"
if [ "$ENVIRONMENT" = "production" ]; then
    echo "  Nginx:          http://localhost (HTTP -> HTTPS redirect)"
    echo "  Nginx HTTPS:    https://localhost (требуется SSL сертификат)"
fi
echo ""
echo "🔧 Настройка SSL (для production):"
echo "  1. Поместите сертификаты в папку ./ssl/"
echo "  2. cert.pem - сертификат"
echo "  3. key.pem - приватный ключ"
echo ""
echo "📊 Мониторинг:"
echo "  docker stats"
echo "  docker-compose -p $PROJECT_NAME top"
