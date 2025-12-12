#!/bin/bash

# Скрипт для настройки подключения к базе данных

echo "🗄️  Настройка подключения к базе данных"
echo

# Проверяем существование .env файла
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл..."
    touch .env
fi

# Проверяем, есть ли уже настроенные параметры БД
DB_EXISTS=$(grep -q "^DB_HOST=" .env && echo "yes" || echo "no")

if [[ "$DB_EXISTS" == "yes" ]]; then
    echo "⚠️  Параметры БД уже настроены в .env"
    echo
    echo "Текущие значения:"
    grep "^DB_HOST=" .env 2>/dev/null
    grep "^DB_PORT=" .env 2>/dev/null
    grep "^DB_USER=" .env 2>/dev/null
    grep "^DB_PASSWORD=" .env 2>/dev/null | sed 's/=.*/=********/'
    grep "^DB_NAME=" .env 2>/dev/null
    echo
    read -p "Хотите изменить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✅ Оставляем текущие значения"
        exit 0
    fi

    # Удаляем старые значения
    sed -i.bak '/^DB_HOST=/d' .env
    sed -i.bak '/^DB_PORT=/d' .env
    sed -i.bak '/^DB_USER=/d' .env
    sed -i.bak '/^DB_PASSWORD=/d' .env
    sed -i.bak '/^DB_NAME=/d' .env
    sed -i.bak '/^# Database/d' .env
fi

echo "Выберите тип базы данных:"
echo "1) Supabase PostgreSQL"
echo "2) Локальный PostgreSQL"
echo "3) Docker PostgreSQL"
echo "4) Ввести свои параметры"
echo

read -p "Ваш выбор (1-4): " -n 1 -r choice
echo

case $choice in
    1)
        echo "🌐 Настройка Supabase PostgreSQL"
        echo
        echo "Получите данные подключения в Supabase Dashboard:"
        echo "Project Settings -> Database -> Connection string"
        echo

        read -p "Введите хост (например: aws-0-eu-central-1.pooler.supabase.com): " DB_HOST

        read -p "Введите порт [5432]: " DB_PORT
        DB_PORT=${DB_PORT:-5432}

        read -p "Введите пользователя (например: postgres.xxxxx): " DB_USER

        read -s -p "Введите пароль: " DB_PASSWORD
        echo

        read -p "Введите имя базы данных [postgres]: " DB_NAME
        DB_NAME=${DB_NAME:-postgres}
        ;;
    2)
        echo "🏠 Настройка локального PostgreSQL"
        echo

        read -p "Введите хост [localhost]: " DB_HOST
        DB_HOST=${DB_HOST:-localhost}

        read -p "Введите порт [5432]: " DB_PORT
        DB_PORT=${DB_PORT:-5432}

        read -p "Введите пользователя [postgres]: " DB_USER
        DB_USER=${DB_USER:-postgres}

        read -s -p "Введите пароль: " DB_PASSWORD
        echo

        read -p "Введите имя базы данных [postgres]: " DB_NAME
        DB_NAME=${DB_NAME:-postgres}
        ;;
    3)
        echo "🐳 Настройка Docker PostgreSQL"
        echo

        read -p "Введите имя контейнера или хост [postgres]: " DB_HOST
        DB_HOST=${DB_HOST:-postgres}

        read -p "Введите порт [5432]: " DB_PORT
        DB_PORT=${DB_PORT:-5432}

        read -p "Введите пользователя [postgres]: " DB_USER
        DB_USER=${DB_USER:-postgres}

        read -s -p "Введите пароль: " DB_PASSWORD
        echo

        read -p "Введите имя базы данных [postgres]: " DB_NAME
        DB_NAME=${DB_NAME:-postgres}
        ;;
    4)
        echo "🔧 Ввод параметров вручную"
        echo

        read -p "Введите DB_HOST: " DB_HOST
        read -p "Введите DB_PORT: " DB_PORT
        read -p "Введите DB_USER: " DB_USER
        read -s -p "Введите DB_PASSWORD: " DB_PASSWORD
        echo
        read -p "Введите DB_NAME: " DB_NAME
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac

# Валидация
if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo "❌ Все параметры обязательны для заполнения"
    exit 1
fi

# Проверка порта
if ! [[ "$DB_PORT" =~ ^[0-9]+$ ]]; then
    echo "❌ Порт должен быть числом"
    exit 1
fi

# Добавляем в .env
echo "" >> .env
echo "# Database (PostgreSQL)" >> .env
echo "DB_HOST=$DB_HOST" >> .env
echo "DB_PORT=$DB_PORT" >> .env
echo "DB_USER=$DB_USER" >> .env
echo "DB_PASSWORD=$DB_PASSWORD" >> .env
echo "DB_NAME=$DB_NAME" >> .env

echo
echo "✅ Параметры базы данных настроены!"
echo
echo "📄 Сохраненные настройки:"
echo "   DB_HOST: $DB_HOST"
echo "   DB_PORT: $DB_PORT"
echo "   DB_USER: $DB_USER"
echo "   DB_PASSWORD: ********"
echo "   DB_NAME: $DB_NAME"
echo
echo "🔧 Настройки сохранены в .env файле"

# Дополнительные советы
case $choice in
    1)
        echo
        echo "💡 Для Supabase:"
        echo "   • Убедитесь что включен режим Pooler (Session mode)"
        echo "   • Проверьте IP-адреса в настройках безопасности"
        echo "   • Используйте SSL для продакшена"
        ;;
    2)
        echo
        echo "💡 Для локального PostgreSQL:"
        echo "   • Убедитесь что PostgreSQL запущен"
        echo "   • Проверьте настройки pg_hba.conf"
        ;;
    3)
        echo
        echo "💡 Для Docker PostgreSQL:"
        echo "   • Контейнер должен быть в той же сети"
        echo "   • Используйте имя контейнера как хост"
        ;;
esac
