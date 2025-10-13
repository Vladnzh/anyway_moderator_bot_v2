#!/bin/bash

# Скрипт для очистки базы данных бота

echo "🗑️ Очистка базы данных бота..."

# Проверяем существование базы данных
if [ ! -f "bot_data.db" ]; then
    echo "❌ Файл bot_data.db не найден!"
    exit 1
fi

# Создаем резервную копию
BACKUP_FILE="bot_data_backup_$(date +%Y%m%d_%H%M%S).db"
cp bot_data.db "$BACKUP_FILE"
echo "💾 Создана резервная копия: $BACKUP_FILE"

# Очищаем таблицы
echo "🧹 Очищаем таблицы..."

sqlite3 bot_data.db << EOF
-- Очищаем логи
DELETE FROM logs;
VACUUM;

-- Очищаем очередь модерации
DELETE FROM moderation_queue;

-- Очищаем очередь реакций
DELETE FROM reaction_queue;

-- Очищаем хэши медиафайлов
DELETE FROM media_hashes;

-- Сбрасываем автоинкремент
DELETE FROM sqlite_sequence WHERE name IN ('logs', 'media_hashes', 'reaction_queue');

-- Показываем статистику
SELECT 'Теги:' as table_name, COUNT(*) as count FROM tags
UNION ALL
SELECT 'Логи:', COUNT(*) FROM logs
UNION ALL
SELECT 'Модерация:', COUNT(*) FROM moderation_queue
UNION ALL
SELECT 'Реакции:', COUNT(*) FROM reaction_queue
UNION ALL
SELECT 'Медиа хэши:', COUNT(*) FROM media_hashes;
EOF

echo "✅ База данных очищена!"
echo "📊 Статистика после очистки:"
sqlite3 bot_data.db "SELECT 'Теги: ' || COUNT(*) FROM tags; SELECT 'Логи: ' || COUNT(*) FROM logs; SELECT 'Модерация: ' || COUNT(*) FROM moderation_queue;"

echo ""
echo "🔄 Для полной очистки включая теги используйте:"
echo "   ./clear_database.sh --full"

# Опция полной очистки
if [ "$1" = "--full" ]; then
    echo ""
    echo "⚠️ ПОЛНАЯ ОЧИСТКА - удаляем ВСЕ данные включая теги!"
    read -p "Вы уверены? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sqlite3 bot_data.db << EOF
DELETE FROM tags;
DELETE FROM sqlite_sequence WHERE name = 'tags';
VACUUM;
EOF
        echo "🗑️ ВСЕ данные удалены!"
    else
        echo "❌ Отменено"
    fi
fi
