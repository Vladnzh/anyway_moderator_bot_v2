#!/bin/bash

echo "🔧 Исправление проблем с правами доступа к базе данных"
echo "====================================================="

# Проверяем что мы в правильной директории
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Ошибка: docker-compose.yml не найден!"
    echo "Запустите скрипт из корня проекта"
    exit 1
fi

echo ""
echo "🛑 1. Останавливаем контейнеры..."
docker compose down

echo ""
echo "📁 2. Настраиваем права доступа..."

# Создаём папку data если её нет
mkdir -p data
echo "✅ Папка data создана"

# Устанавливаем правильные права
chmod 755 data
echo "✅ Права на папку data: 755"

# Создаём файл базы данных если его нет
if [ ! -f "data/bot_data.db" ]; then
    touch data/bot_data.db
    echo "✅ Создан файл базы данных"
fi

chmod 644 data/bot_data.db
echo "✅ Права на базу данных: 644"

# Создаём .gitkeep если его нет
if [ ! -f "data/.gitkeep" ]; then
    touch data/.gitkeep
    echo "✅ Создан .gitkeep файл"
fi

# Устанавливаем владельца (UID 1000 из Docker контейнера)
if chown -R 1000:1000 data/ 2>/dev/null; then
    echo "✅ Владелец установлен: 1000:1000"
else
    echo "⚠️ Не удалось изменить владельца (нужны права root)"
    echo "   Попробуйте: sudo chown -R 1000:1000 data/"
    
    # Пробуем через sudo
    if command -v sudo >/dev/null 2>&1; then
        echo "🔧 Пробуем через sudo..."
        if sudo chown -R 1000:1000 data/ 2>/dev/null; then
            echo "✅ Владелец установлен через sudo"
        else
            echo "❌ Не удалось установить владельца"
        fi
    fi
fi

echo ""
echo "📋 3. Проверяем результат..."
ls -la data/

echo ""
echo "🚀 4. Запускаем контейнеры..."
docker compose up -d

echo ""
echo "⏳ 5. Ждём запуска (10 секунд)..."
sleep 10

echo ""
echo "📊 6. Проверяем статус..."
docker compose ps

echo ""
echo "📋 7. Проверяем логи..."
docker compose logs --tail=5 bot

echo ""
echo "✅ Исправление завершено!"
echo ""
echo "💡 Если проблема остаётся:"
echo "   1. Проверьте: ls -la data/"
echo "   2. Установите владельца: sudo chown -R 1000:1000 data/"
echo "   3. Перезапустите: docker compose restart"
