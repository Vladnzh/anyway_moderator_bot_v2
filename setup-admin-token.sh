#!/bin/bash

echo "🔐 Настройка ADMIN_TOKEN"
echo "======================="

# Проверяем что мы в правильной директории
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Ошибка: docker-compose.yml не найден!"
    echo "Запустите скрипт из корня проекта"
    exit 1
fi

# Читаем существующий .env если есть
BOT_TOKEN=""
if [ -f ".env" ]; then
    source .env
    echo "📄 Найден существующий .env файл"
    if [ -n "$ADMIN_TOKEN" ]; then
        echo "Текущий ADMIN_TOKEN: ${ADMIN_TOKEN:0:6}...${ADMIN_TOKEN: -4}"
    fi
fi

echo ""
echo "🔐 Настройка токена для админки"
echo "Выберите вариант:"
echo "1. Сгенерировать случайный токен (рекомендуется)"
echo "2. Ввести свой токен"
echo ""

read -p "Выберите (1/2): " choice

case "$choice" in
    1)
        NEW_ADMIN_TOKEN=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
        echo "✅ Сгенерирован случайный токен"
        ;;
    2)
        read -p "Введите ADMIN_TOKEN: " NEW_ADMIN_TOKEN
        if [ -z "$NEW_ADMIN_TOKEN" ]; then
            echo "❌ Токен не может быть пустым!"
            exit 1
        fi
        ;;
    *)
        NEW_ADMIN_TOKEN=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
        echo "✅ Использован случайный токен по умолчанию"
        ;;
esac

# Проверяем что BOT_TOKEN есть
if [ -z "$BOT_TOKEN" ]; then
    echo ""
    echo "⚠️ BOT_TOKEN не найден!"
    echo "Сначала настройте BOT_TOKEN: ./setup-bot-token.sh"
    echo ""
    read -p "Продолжить без BOT_TOKEN? (y/N): " continue_without_bot
    if [[ ! "$continue_without_bot" =~ ^[Yy]$ ]]; then
        exit 1
    fi
    BOT_TOKEN="YOUR_BOT_TOKEN_HERE"
fi

# Сохраняем .env
cat > .env << EOF
# Токен бота от @BotFather
BOT_TOKEN=$BOT_TOKEN

# Безопасный токен для админки
ADMIN_TOKEN=$NEW_ADMIN_TOKEN

# Путь к базе данных
DATABASE_PATH=/app/data/bot_data.db
EOF

echo ""
echo "✅ ADMIN_TOKEN сохранён!"
echo "📋 Новый токен: $NEW_ADMIN_TOKEN"
echo ""
echo "🌐 Для входа в админку используйте этот токен:"
echo "   http://localhost:8000"
echo "   Токен: $NEW_ADMIN_TOKEN"
echo ""
echo "💡 Для запуска бота используйте: ./start.sh"
