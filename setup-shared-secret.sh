#!/bin/bash

# Скрипт для настройки BOT_SHARED_SECRET

echo "🔐 Настройка BOT_SHARED_SECRET"
echo

# Проверяем существование .env файла
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл..."
    touch .env
fi

# Проверяем, есть ли уже BOT_SHARED_SECRET
if grep -q "^BOT_SHARED_SECRET=" .env; then
    echo "⚠️ BOT_SHARED_SECRET уже настроен в .env"
    echo
    echo "Текущее значение:"
    grep "^BOT_SHARED_SECRET=" .env | sed 's/BOT_SHARED_SECRET=\(.\{8\}\).*/BOT_SHARED_SECRET=\1.../'
    echo
    read -p "Хотите изменить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✅ Оставляем текущее значение"
        exit 0
    fi
    
    # Удаляем старое значение
    sed -i.bak '/^BOT_SHARED_SECRET=/d' .env
fi

echo "Выберите способ настройки:"
echo "1) Сгенерировать случайный секрет (рекомендуется)"
echo "2) Ввести свой секрет"
echo

read -p "Ваш выбор (1-2): " -n 1 -r choice
echo

case $choice in
    1)
        # Генерируем случайный секрет
        SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 64)
        
        if [ -z "$SECRET" ]; then
            echo "❌ Не удалось сгенерировать секрет"
            echo "Установите openssl или python3"
            exit 1
        fi
        
        echo "🎲 Сгенерирован случайный секрет: ${SECRET:0:8}..."
        ;;
    2)
        echo "Введите секрет (минимум 16 символов):"
        read -s SECRET
        echo
        
        if [ ${#SECRET} -lt 16 ]; then
            echo "❌ Секрет слишком короткий (минимум 16 символов)"
            exit 1
        fi
        
        echo "✅ Секрет принят: ${SECRET:0:8}..."
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac

# Добавляем в .env
echo "BOT_SHARED_SECRET=$SECRET" >> .env

echo
echo "✅ BOT_SHARED_SECRET настроен!"
echo
echo "💡 Этот секрет нужно будет использовать в вашем бэкенде"
echo "   для проверки HMAC подписи запросов от бота."
echo
echo "🔒 Секрет сохранен в .env файле"
