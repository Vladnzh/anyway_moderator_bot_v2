#!/bin/bash

echo "🔄 Безопасное обновление проекта с сохранением данных"
echo "===================================================="
echo "⏰ Начало обновления: $(date)"
echo ""

# Проверяем что мы в правильной директории
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Ошибка: docker-compose.yml не найден!"
    echo "Запустите скрипт из корня проекта"
    exit 1
fi

# Проверяем доступность Git
if ! command -v git &> /dev/null; then
    echo "❌ Ошибка: Git не установлен!"
    exit 1
fi

# Проверяем доступность Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Ошибка: Docker не установлен!"
    exit 1
fi

echo ""
echo "💾 1. Создаём резервную копию базы данных..."
if [ -f "data/bot_data.db" ]; then
    cp data/bot_data.db data/bot_data.db.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Резервная копия создана"
else
    echo "⚠️ База данных не найдена (будет создана новая)"
fi

echo ""
echo "📥 2. Получаем обновления из Git..."
echo "📋 Текущая ветка: $(git branch --show-current)"
echo "📋 Последний коммит: $(git log -1 --oneline)"

# Сохраняем локальные изменения
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "💾 Сохраняем локальные изменения..."
    git stash push -m "Auto-stash before update $(date)"
fi

# Получаем обновления
echo "📥 Получаем обновления..."
if git pull origin main; then
    echo "✅ Обновления получены успешно"
else
    echo "❌ Ошибка получения обновлений!"
    exit 1
fi

echo ""
echo "🛑 3. Останавливаем контейнеры..."
docker compose down

echo ""
echo "📁 4. Проверяем и настраиваем права доступа к данным..."
# Создаём папку data если её нет
mkdir -p data

# Устанавливаем правильные права
chmod 755 data
if [ -f "data/bot_data.db" ]; then
    chmod 644 data/bot_data.db
    echo "✅ Права на существующую базу данных обновлены"
else
    touch data/bot_data.db
    chmod 644 data/bot_data.db
    echo "✅ Создана новая база данных"
fi

# Устанавливаем владельца (UID 1000 из Docker контейнера)
chown -R 1000:1000 data/ 2>/dev/null || {
    echo "⚠️ Не удалось изменить владельца (нужны права root)"
    echo "   Выполните: sudo chown -R 1000:1000 data/"
}

echo ""
echo "🏗️ 5. Пересобираем образы..."
docker compose build

echo ""
echo "🚀 6. Запускаем обновлённые контейнеры..."
docker compose up -d

echo ""
echo "⏳ 7. Ждём запуска (15 секунд)..."
sleep 15

echo ""
echo "📊 8. Проверяем статус..."
docker compose ps

echo ""
echo "🧪 9. Тестируем API..."
if curl -s -f -H "Authorization: Bearer ${ADMIN_TOKEN:-w6CGVQzZYcAUsxj4Mz7HajGk}" \
   "http://localhost:8000/api/stats" > /dev/null; then
    echo "✅ API работает"
else
    echo "❌ API недоступен"
fi

echo ""
echo "📋 10. Показываем логи (последние 10 строк)..."
docker compose logs --tail=10 bot

echo ""
echo "✅ Обновление завершено!"
echo "⏰ Время завершения: $(date)"
echo ""

# Показываем информацию о новых коммитах
echo "📋 Информация об обновлении:"
git log --oneline -5

echo ""
echo "💡 Полезные команды:"
echo "   docker compose logs -f bot     # Логи бота"
echo "   docker compose logs -f admin   # Логи админки"
echo "   docker compose ps              # Статус контейнеров"
echo "   docker compose restart bot     # Перезапуск бота"
echo ""
echo "🌐 Админка: http://localhost:8000"
echo "🗄️ База данных: ./data/bot_data.db (сохраняется при обновлениях)"

# Показываем резервные копии
echo ""
echo "💾 Доступные резервные копии:"
ls -la data/*.backup* 2>/dev/null | tail -5 || echo "   Резервных копий не найдено"
