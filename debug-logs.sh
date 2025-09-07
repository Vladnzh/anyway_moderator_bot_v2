#!/bin/bash

# Скрипт для просмотра подробных логов бота

echo "🔍 Подробные логи бота"
echo "====================="
echo

case "${1:-help}" in
    "live"|"follow")
        echo "📺 Логи в реальном времени (Ctrl+C для выхода):"
        echo
        docker logs moderator-bot --follow --timestamps
        ;;
    "last"|"recent")
        echo "📋 Последние 100 строк логов:"
        echo
        docker logs moderator-bot --tail 100 --timestamps
        ;;
    "errors")
        echo "🚨 Только ошибки и предупреждения:"
        echo
        docker logs moderator-bot --timestamps 2>&1 | grep -E "(ERROR|WARNING|❌|⚠️)"
        ;;
    "debug")
        echo "🐛 Отладочная информация:"
        echo
        docker logs moderator-bot --timestamps 2>&1 | grep -E "(DEBUG|🔍|📝|🏷️)"
        ;;
    "reactions")
        echo "🔥 Логи реакций:"
        echo
        docker logs moderator-bot --timestamps 2>&1 | grep -E "(реакци|reaction|🔥|✅.*поставлена)"
        ;;
    "http")
        echo "🌐 HTTP запросы и ответы:"
        echo
        docker logs moderator-bot --timestamps 2>&1 | grep -E "(📊|🔗|📥|📤|HTTP|Отправляем|Ответ)"
        ;;
    "messages")
        echo "📨 Входящие сообщения:"
        echo
        docker logs moderator-bot --timestamps 2>&1 | grep -E "(📨|Входящее|сообщение от)"
        ;;
    "tags")
        echo "🏷️ Обработка тегов:"
        echo
        docker logs moderator-bot --timestamps 2>&1 | grep -E "(🏷️|🎯|Тег сработал|Проверяем тег|совпадение)"
        ;;
    "all")
        echo "📜 Все логи с временными метками:"
        echo
        docker logs moderator-bot --timestamps
        ;;
    "save")
        FILENAME="bot_logs_$(date +%Y%m%d_%H%M%S).txt"
        echo "💾 Сохраняем логи в файл: $FILENAME"
        docker logs moderator-bot --timestamps > "$FILENAME"
        echo "✅ Логи сохранены в $FILENAME"
        ;;
    "clear")
        echo "🗑️ Очистка логов (перезапуск контейнера)..."
        docker restart moderator-bot
        echo "✅ Контейнер перезапущен, логи очищены"
        ;;
    "help"|*)
        echo "Использование: $0 [команда]"
        echo
        echo "Доступные команды:"
        echo "  live      - Логи в реальном времени"
        echo "  last      - Последние 100 строк"
        echo "  errors    - Только ошибки и предупреждения"
        echo "  debug     - Отладочная информация"
        echo "  reactions - Логи реакций"
        echo "  http      - HTTP запросы и ответы"
        echo "  messages  - Входящие сообщения"
        echo "  tags      - Обработка тегов"
        echo "  all       - Все логи"
        echo "  save      - Сохранить логи в файл"
        echo "  clear     - Очистить логи (перезапуск)"
        echo "  help      - Показать эту справку"
        echo
        echo "Примеры:"
        echo "  $0 live      # Следить за логами"
        echo "  $0 errors    # Показать только ошибки"
        echo "  $0 http      # HTTP запросы"
        echo "  $0 save      # Сохранить в файл"
        ;;
esac
