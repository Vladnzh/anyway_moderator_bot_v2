#!/bin/bash

echo "🤖 Настройка BOT_TOKEN"
echo "====================="

# Проверяем что мы в правильной директории
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Ошибка: docker-compose.yml не найден!"
    echo "Запустите скрипт из корня проекта"
    exit 1
fi

# Функция для проверки токена бота
validate_bot_token() {
    local token="$1"
    if [[ ! "$token" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
        echo "❌ Неверный формат BOT_TOKEN"
        echo "Формат должен быть: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
        return 1
    fi
    return 0
}

# Читаем существующий .env если есть
ADMIN_TOKEN=""
if [ -f ".env" ]; then
    source .env
    echo "📄 Найден существующий .env файл"
    if [ -n "$BOT_TOKEN" ]; then
        echo "Текущий BOT_TOKEN: ${BOT_TOKEN:0:10}...${BOT_TOKEN: -4}"
    fi
fi

echo ""
echo "🔑 Получите токен у @BotFather в Telegram:"
echo "1. Отправьте /newbot"
echo "2. Следуйте инструкциям"
echo "3. Скопируйте токен"
echo ""

# Запрашиваем новый токен
while true; do
    read -p "Введите BOT_TOKEN: " NEW_BOT_TOKEN
    if [ -n "$NEW_BOT_TOKEN" ] && validate_bot_token "$NEW_BOT_TOKEN"; then
        break
    fi
done

# Генерируем ADMIN_TOKEN если его нет
if [ -z "$ADMIN_TOKEN" ]; then
    ADMIN_TOKEN=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
    echo "🔑 Сгенерирован новый ADMIN_TOKEN"
fi

# Сохраняем .env
cat > .env << EOF
# Токен бота от @BotFather
BOT_TOKEN=$NEW_BOT_TOKEN

# Безопасный токен для админки
ADMIN_TOKEN=$ADMIN_TOKEN

# Путь к базе данных
DATABASE_PATH=/app/data/bot_data.db
EOF

echo ""
echo "✅ BOT_TOKEN сохранён!"
echo "📋 Токены:"
echo "  BOT_TOKEN: ${NEW_BOT_TOKEN:0:10}...${NEW_BOT_TOKEN: -4}"
echo "  ADMIN_TOKEN: $ADMIN_TOKEN"
echo ""
echo "💡 Для запуска бота используйте: ./start.sh"
