#!/bin/bash

echo "🔍 Проверка разработческой среды"
echo "==============================="

# Проверяем основные файлы
echo "📁 Проверка файлов..."

required_files=("bot.py" "admin.py" "database.py" "requirements.txt")
missing_files=()

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file - НЕ НАЙДЕН"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo ""
    echo "❌ Отсутствуют критические файлы: ${missing_files[*]}"
    echo "Убедитесь что вы в корне проекта"
    exit 1
fi

# Проверяем Python
echo ""
echo "🐍 Проверка Python..."

if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    echo "  ✅ $python_version"
else
    echo "  ❌ Python3 не найден"
    echo "  Установите Python 3.6+: sudo apt install python3"
    exit 1
fi

# Проверяем синтаксис Python файлов
echo ""
echo "📝 Проверка синтаксиса Python..."

python_files=("bot.py" "admin.py" "database.py" "test_simple.py")
syntax_errors=()

for file in "${python_files[@]}"; do
    if [ -f "$file" ]; then
        if python3 -m py_compile "$file" 2>/dev/null; then
            echo "  ✅ $file"
        else
            echo "  ❌ $file - СИНТАКСИЧЕСКАЯ ОШИБКА"
            syntax_errors+=("$file")
        fi
    fi
done

if [ ${#syntax_errors[@]} -gt 0 ]; then
    echo ""
    echo "❌ Синтаксические ошибки в файлах: ${syntax_errors[*]}"
    echo "Исправьте ошибки перед запуском"
    exit 1
fi

# Проверяем зависимости
echo ""
echo "📦 Проверка зависимостей..."

if [ -f "requirements.txt" ]; then
    echo "  ✅ requirements.txt найден"
    
    # Показываем основные зависимости
    echo "  📋 Основные зависимости:"
    grep -E "(telegram|fastapi|aiohttp|requests)" requirements.txt | head -5 | while read line; do
        echo "    - $line"
    done
else
    echo "  ❌ requirements.txt не найден"
    exit 1
fi

# Проверяем порты
echo ""
echo "🌐 Проверка портов..."

if command -v lsof &> /dev/null; then
    port_8000=$(lsof -ti:8000 2>/dev/null | wc -l)
    if [ "$port_8000" -gt 0 ]; then
        echo "  ⚠️ Порт 8000 занят (возможно админка уже запущена)"
        echo "     Процессы: $(lsof -ti:8000 2>/dev/null | tr '\n' ' ')"
    else
        echo "  ✅ Порт 8000 свободен"
    fi
else
    echo "  ℹ️ lsof не найден, не могу проверить порты"
fi

# Проверяем существующую разработческую среду
echo ""
echo "🛠️ Проверка разработческой среды..."

if [ -f ".env.dev" ]; then
    echo "  ✅ .env.dev найден"
    source .env.dev
    if [ -n "$BOT_TOKEN" ]; then
        echo "    🤖 BOT_TOKEN: ${BOT_TOKEN:0:10}...${BOT_TOKEN: -4}"
    fi
    if [ -n "$ADMIN_TOKEN" ]; then
        echo "    🔑 ADMIN_TOKEN: ${ADMIN_TOKEN:0:8}...${ADMIN_TOKEN: -4}"
    fi
else
    echo "  ℹ️ .env.dev не найден (будет создан при первом запуске)"
fi

if [ -d "venv" ]; then
    echo "  ✅ Виртуальное окружение найдено"
    if [ -f "venv/bin/activate" ]; then
        echo "    🐍 Активация: source venv/bin/activate"
    fi
else
    echo "  ℹ️ Виртуальное окружение не найдено (будет создано)"
fi

if [ -f "dev_bot_data.db" ]; then
    db_size=$(du -h dev_bot_data.db 2>/dev/null | cut -f1)
    echo "  ✅ База данных разработки: dev_bot_data.db ($db_size)"
else
    echo "  ℹ️ База данных разработки не найдена (будет создана)"
fi

# Проверяем скрипты разработки
echo ""
echo "📜 Проверка скриптов разработки..."

dev_scripts=("start-dev.sh" "stop-dev.sh" "test-dev.sh")
for script in "${dev_scripts[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "  ✅ $script (исполняемый)"
        else
            echo "  ⚠️ $script (не исполняемый)"
            echo "    Исправить: chmod +x $script"
        fi
    else
        echo "  ❌ $script - НЕ НАЙДЕН"
    fi
done

# Итоговая оценка
echo ""
echo "📊 ИТОГОВАЯ ОЦЕНКА"
echo "=================="

if [ ${#missing_files[@]} -eq 0 ] && [ ${#syntax_errors[@]} -eq 0 ]; then
    echo "🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!"
    echo ""
    echo "✅ Готово к разработке:"
    echo "  • Все файлы на месте"
    echo "  • Синтаксис корректен"
    echo "  • Python доступен"
    echo ""
    echo "🚀 Следующие шаги:"
    echo "  1. ./start-dev.sh  # Запуск разработческой среды"
    echo "  2. ./test-dev.sh   # Тестирование"
    echo "  3. ./stop-dev.sh   # Остановка"
    echo ""
    echo "📖 Документация: cat DEV_README.md"
else
    echo "❌ ЕСТЬ ПРОБЛЕМЫ!"
    echo ""
    if [ ${#missing_files[@]} -gt 0 ]; then
        echo "🚫 Отсутствующие файлы: ${missing_files[*]}"
    fi
    if [ ${#syntax_errors[@]} -gt 0 ]; then
        echo "🐛 Синтаксические ошибки: ${syntax_errors[*]}"
    fi
    echo ""
    echo "🔧 Исправьте проблемы перед запуском"
fi

echo ""
echo "💡 Полезные команды:"
echo "  • Проверка: ./check-dev.sh"
echo "  • Запуск: ./start-dev.sh"
echo "  • Тесты: ./test-dev.sh"
echo "  • Остановка: ./stop-dev.sh"
