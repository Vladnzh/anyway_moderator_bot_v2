#!/bin/bash

# Скрипт для настройки BACKEND_URL

echo "🌐 Настройка BACKEND_URL"
echo

# Проверяем существование .env файла
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл..."
    touch .env
fi

# Проверяем, есть ли уже BACKEND_URL
if grep -q "^BACKEND_URL=" .env; then
    echo "⚠️ BACKEND_URL уже настроен в .env"
    echo
    echo "Текущее значение:"
    grep "^BACKEND_URL=" .env
    echo
    read -p "Хотите изменить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✅ Оставляем текущее значение"
        exit 0
    fi
    
    # Удаляем старое значение
    sed -i.bak '/^BACKEND_URL=/d' .env
fi

echo "Выберите тип настройки:"
echo "1) Локальная разработка (http://localhost:8000)"
echo "2) Docker контейнер (http://admin:8000)"
echo "3) Внешний сервер (https://your-domain.com)"
echo "4) Ввести свой URL"
echo

read -p "Ваш выбор (1-4): " -n 1 -r choice
echo

case $choice in
    1)
        BACKEND_URL="http://localhost:8000"
        echo "🏠 Выбрана локальная разработка: $BACKEND_URL"
        ;;
    2)
        BACKEND_URL="http://admin:8000"
        echo "🐳 Выбран Docker контейнер: $BACKEND_URL"
        ;;
    3)
        echo "Введите ваш домен (без http/https):"
        read -r domain
        
        if [ -z "$domain" ]; then
            echo "❌ Домен не может быть пустым"
            exit 1
        fi
        
        # Проверяем, начинается ли с http
        if [[ $domain == http* ]]; then
            BACKEND_URL="$domain"
        else
            # Определяем протокол
            echo "Выберите протокол:"
            echo "1) HTTPS (рекомендуется для продакшена)"
            echo "2) HTTP"
            read -p "Протокол (1-2): " -n 1 -r protocol
            echo
            
            case $protocol in
                1)
                    BACKEND_URL="https://$domain"
                    ;;
                2)
                    BACKEND_URL="http://$domain"
                    ;;
                *)
                    echo "❌ Неверный выбор, используем HTTPS"
                    BACKEND_URL="https://$domain"
                    ;;
            esac
        fi
        
        echo "🌍 Выбран внешний сервер: $BACKEND_URL"
        ;;
    4)
        echo "Введите полный URL (с http:// или https://):"
        read -r custom_url
        
        if [ -z "$custom_url" ]; then
            echo "❌ URL не может быть пустым"
            exit 1
        fi
        
        # Проверяем формат URL
        if [[ ! $custom_url =~ ^https?:// ]]; then
            echo "❌ URL должен начинаться с http:// или https://"
            exit 1
        fi
        
        BACKEND_URL="$custom_url"
        echo "🔗 Выбран пользовательский URL: $BACKEND_URL"
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac

# Добавляем в .env
echo "BACKEND_URL=$BACKEND_URL" >> .env

echo
echo "✅ BACKEND_URL настроен!"
echo
echo "💡 Этот URL будет использоваться ботом для:"
echo "   • Привязки аккаунтов Telegram (/api/telegram/link)"
echo "   • Других API запросов к вашему бэкенду"
echo
echo "🔧 Настройка сохранена в .env файле"

# Показываем итоговый .env (только BACKEND_URL)
echo
echo "📄 Текущая настройка:"
grep "^BACKEND_URL=" .env

# Дополнительные советы в зависимости от выбора
case $choice in
    1)
        echo
        echo "💡 Для локальной разработки:"
        echo "   • Убедитесь что админка запущена на порту 8000"
        echo "   • Используйте: ./start.sh"
        ;;
    2)
        echo
        echo "💡 Для Docker:"
        echo "   • Это внутренний URL между контейнерами"
        echo "   • Контейнер 'admin' должен быть запущен"
        echo "   • Используйте: ./start.sh"
        ;;
    3|4)
        echo
        echo "💡 Для внешнего сервера:"
        echo "   • Убедитесь что сервер доступен по этому URL"
        echo "   • Проверьте настройки CORS если нужно"
        echo "   • Для HTTPS убедитесь в валидности сертификата"
        ;;
esac
