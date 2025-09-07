#!/bin/bash

# Скрипт для настройки ADMIN_URL и FRONTEND_URL

echo "🌐 Настройка URL адресов"
echo

# Проверяем существование .env файла
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл..."
    touch .env
fi

# Проверяем, есть ли уже настроенные URL
ADMIN_EXISTS=$(grep -q "^ADMIN_URL=" .env && echo "yes" || echo "no")
FRONTEND_EXISTS=$(grep -q "^FRONTEND_URL=" .env && echo "yes" || echo "no")

if [[ "$ADMIN_EXISTS" == "yes" || "$FRONTEND_EXISTS" == "yes" ]]; then
    echo "⚠️ URL уже настроены в .env"
    echo
    echo "Текущие значения:"
    [[ "$ADMIN_EXISTS" == "yes" ]] && grep "^ADMIN_URL=" .env
    [[ "$FRONTEND_EXISTS" == "yes" ]] && grep "^FRONTEND_URL=" .env
    echo
    read -p "Хотите изменить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✅ Оставляем текущие значения"
        exit 0
    fi
    
    # Удаляем старые значения
    sed -i.bak '/^ADMIN_URL=/d' .env
    sed -i.bak '/^FRONTEND_URL=/d' .env
fi

echo "Выберите тип настройки:"
echo "1) Локальная разработка"
echo "2) Docker контейнер"
echo "3) Внешние серверы"
echo "4) Ввести свои URL"
echo

read -p "Ваш выбор (1-4): " -n 1 -r choice
echo

case $choice in
    1)
        ADMIN_URL="http://localhost:8000"
        FRONTEND_URL="http://localhost:3000"
        echo "🏠 Выбрана локальная разработка:"
        echo "   ADMIN_URL: $ADMIN_URL"
        echo "   FRONTEND_URL: $FRONTEND_URL"
        ;;
    2)
        ADMIN_URL="http://admin:8000"
        FRONTEND_URL="http://localhost:3000"
        echo "🐳 Выбран Docker контейнер:"
        echo "   ADMIN_URL: $ADMIN_URL (внутренний)"
        echo "   FRONTEND_URL: $FRONTEND_URL (внешний)"
        ;;
    3)
        echo "Введите домен админки (без http/https):"
        read -r admin_domain
        echo "Введите домен фронтенда (без http/https):"
        read -r frontend_domain
        
        if [ -z "$admin_domain" ] || [ -z "$frontend_domain" ]; then
            echo "❌ Домены не могут быть пустыми"
            exit 1
        fi
        
        # Определяем протокол
        echo "Выберите протокол:"
        echo "1) HTTPS (рекомендуется для продакшена)"
        echo "2) HTTP"
        read -p "Протокол (1-2): " -n 1 -r protocol
        echo
        
        case $protocol in
            1)
                ADMIN_URL="https://$admin_domain"
                FRONTEND_URL="https://$frontend_domain"
                ;;
            2)
                ADMIN_URL="http://$admin_domain"
                FRONTEND_URL="http://$frontend_domain"
                ;;
            *)
                echo "❌ Неверный выбор, используем HTTPS"
                ADMIN_URL="https://$admin_domain"
                FRONTEND_URL="https://$frontend_domain"
                ;;
        esac
        
        echo "🌍 Выбраны внешние серверы:"
        echo "   ADMIN_URL: $ADMIN_URL"
        echo "   FRONTEND_URL: $FRONTEND_URL"
        ;;
    4)
        echo "Введите ADMIN_URL (с http:// или https://):"
        read -r admin_url
        echo "Введите FRONTEND_URL (с http:// или https://):"
        read -r frontend_url
        
        if [ -z "$admin_url" ] || [ -z "$frontend_url" ]; then
            echo "❌ URL не могут быть пустыми"
            exit 1
        fi
        
        # Проверяем формат URL
        if [[ ! $admin_url =~ ^https?:// ]] || [[ ! $frontend_url =~ ^https?:// ]]; then
            echo "❌ URL должны начинаться с http:// или https://"
            exit 1
        fi
        
        ADMIN_URL="$admin_url"
        FRONTEND_URL="$frontend_url"
        echo "🔗 Выбраны пользовательские URL:"
        echo "   ADMIN_URL: $ADMIN_URL"
        echo "   FRONTEND_URL: $FRONTEND_URL"
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac

# Добавляем в .env
echo "ADMIN_URL=$ADMIN_URL" >> .env
echo "FRONTEND_URL=$FRONTEND_URL" >> .env

echo
echo "✅ URL настроены!"
echo
echo "💡 Эти URL будут использоваться ботом для:"
echo "   • ADMIN_URL: отправка данных о реакциях (/api/telegram/reaction)"
echo "   • FRONTEND_URL: привязка аккаунтов (/api/telegram/link)"
echo
echo "🔧 Настройки сохранены в .env файле"

# Показываем итоговый .env
echo
echo "📄 Текущие настройки:"
grep "^ADMIN_URL=" .env
grep "^FRONTEND_URL=" .env

# Дополнительные советы в зависимости от выбора
case $choice in
    1)
        echo
        echo "💡 Для локальной разработки:"
        echo "   • Админка должна быть запущена на порту 8000"
        echo "   • Фронтенд должен быть запущен на порту 3000"
        echo "   • Используйте: ./start.sh"
        ;;
    2)
        echo
        echo "💡 Для Docker:"
        echo "   • ADMIN_URL - внутренний URL между контейнерами"
        echo "   • FRONTEND_URL - внешний URL для привязки аккаунтов"
        echo "   • Контейнер 'admin' должен быть запущен"
        echo "   • Используйте: ./start.sh"
        ;;
    3|4)
        echo
        echo "💡 Для внешних серверов:"
        echo "   • Убедитесь что серверы доступны по указанным URL"
        echo "   • Проверьте настройки CORS если нужно"
        echo "   • Для HTTPS убедитесь в валидности сертификатов"
        echo "   • ADMIN_URL - для получения данных о реакциях"
        echo "   • FRONTEND_URL - для привязки аккаунтов пользователей"
        ;;
esac
