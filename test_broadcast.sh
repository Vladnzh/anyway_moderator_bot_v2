#!/bin/bash

# Скрипт для тестирования массовой рассылки

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Загружаем переменные окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Проверяем наличие необходимых переменных
if [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${RED}❌ ADMIN_TOKEN не найден в .env${NC}"
    exit 1
fi

if [ -z "$SUPABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  SUPABASE_URL не найден в .env${NC}"
    echo "Для работы массовой рассылки необходимо настроить Supabase"
    exit 1
fi

if [ -z "$SUPABASE_KEY" ]; then
    echo -e "${YELLOW}⚠️  SUPABASE_KEY не найден в .env${NC}"
    echo "Для работы массовой рассылки необходимо настроить Supabase"
    exit 1
fi

ADMIN_URL=${ADMIN_URL:-"http://localhost:8000"}

echo -e "${GREEN}🧪 Тестирование массовой рассылки${NC}"
echo "----------------------------------------"

# 1. Тест предпросмотра
echo -e "\n${YELLOW}📋 Шаг 1: Предпросмотр получателей${NC}"

PREVIEW_RESPONSE=$(curl -s -X POST "$ADMIN_URL/api/broadcast/preview" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "supabase_query": "select=tg_user_id,username,email,full_name&tg_user_id=not.is.null"
  }')

echo "Ответ сервера:"
echo "$PREVIEW_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PREVIEW_RESPONSE"

# Проверяем успешность
if echo "$PREVIEW_RESPONSE" | grep -q '"success": true'; then
    USER_COUNT=$(echo "$PREVIEW_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null)
    echo -e "\n${GREEN}✅ Предпросмотр успешен!${NC}"
    echo -e "Найдено пользователей: ${GREEN}$USER_COUNT${NC}"

    # 2. Спрашиваем подтверждение
    if [ "$USER_COUNT" -gt 0 ]; then
        echo -e "\n${YELLOW}⚠️  ВНИМАНИЕ! Это тестовая отправка.${NC}"
        echo "Для реальной отправки раскомментируйте код ниже в скрипте."
        echo ""
        echo "# Пример отправки:"
        echo "# curl -X POST \"$ADMIN_URL/api/broadcast/send\" \\"
        echo "#   -H \"Authorization: Bearer \$ADMIN_TOKEN\" \\"
        echo "#   -H \"Content-Type: application/json\" \\"
        echo "#   -d '{"
        echo "#     \"message\": \"Тестовое сообщение от бота\","
        echo "#     \"supabase_query\": \"select=tg_user_id&tg_user_id=not.is.null\","
        echo "#     \"parse_mode\": null"
        echo "#   }'"
    else
        echo -e "\n${YELLOW}⚠️  Пользователи не найдены${NC}"
    fi
else
    echo -e "\n${RED}❌ Ошибка при предпросмотре${NC}"
    exit 1
fi

echo -e "\n${GREEN}🎉 Тест завершен!${NC}"
echo "----------------------------------------"
echo "Для отправки реальных сообщений используйте API endpoint /api/broadcast/send"
echo "Подробнее: BROADCAST_README.md"
