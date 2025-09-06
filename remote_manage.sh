#!/bin/bash

# 🌐 Скрипт для удалённого управления ботом
# Настройте переменные ниже под ваш сервер

# ⚙️ Конфигурация сервера
SERVER_IP="your-server-ip"
SERVER_USER="root"
PROJECT_PATH="/opt/moderator-bot/anyway_moderator_bot_v2"

# 🎨 Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 📋 Функции
show_help() {
    echo -e "${BLUE}🤖 Удалённое управление модератор-ботом${NC}"
    echo ""
    echo "Использование: $0 [команда]"
    echo ""
    echo "Команды:"
    echo -e "  ${GREEN}update${NC}     - Обновить бот с сохранением данных"
    echo -e "  ${GREEN}status${NC}     - Показать статус контейнеров"
    echo -e "  ${GREEN}logs${NC}       - Показать логи бота в реальном времени"
    echo -e "  ${GREEN}restart${NC}    - Перезапустить бот"
    echo -e "  ${GREEN}stop${NC}       - Остановить бот"
    echo -e "  ${GREEN}start${NC}      - Запустить бот"
    echo -e "  ${GREEN}backup${NC}     - Создать резервную копию базы данных"
    echo -e "  ${GREEN}shell${NC}      - Подключиться к серверу по SSH"
    echo -e "  ${GREEN}setup${NC}      - Настроить алиасы для быстрого доступа"
    echo ""
    echo "Примеры:"
    echo "  $0 update      # Обновить бот"
    echo "  $0 logs        # Смотреть логи"
    echo "  $0 status      # Проверить статус"
}

run_remote() {
    local cmd="$1"
    echo -e "${BLUE}🔗 Выполняем на сервере: ${YELLOW}$cmd${NC}"
    ssh -t "$SERVER_USER@$SERVER_IP" "cd $PROJECT_PATH && $cmd"
}

run_remote_quiet() {
    local cmd="$1"
    ssh "$SERVER_USER@$SERVER_IP" "cd $PROJECT_PATH && $cmd"
}

# 🚀 Основные команды
case "$1" in
    "update")
        echo -e "${GREEN}🔄 Обновление бота...${NC}"
        run_remote "./update_project.sh"
        ;;
    
    "status")
        echo -e "${GREEN}📊 Статус контейнеров:${NC}"
        run_remote "docker compose ps"
        ;;
    
    "logs")
        echo -e "${GREEN}📋 Логи бота (Ctrl+C для выхода):${NC}"
        run_remote "docker compose logs -f bot"
        ;;
    
    "restart")
        echo -e "${GREEN}🔄 Перезапуск бота...${NC}"
        run_remote "docker compose restart bot admin"
        ;;
    
    "stop")
        echo -e "${YELLOW}🛑 Остановка бота...${NC}"
        run_remote "docker compose down"
        ;;
    
    "start")
        echo -e "${GREEN}🚀 Запуск бота...${NC}"
        run_remote "docker compose up -d"
        ;;
    
    "backup")
        echo -e "${GREEN}💾 Создание резервной копии...${NC}"
        BACKUP_NAME="bot_data.db.manual.$(date +%Y%m%d_%H%M%S)"
        run_remote "cp data/bot_data.db data/$BACKUP_NAME && echo '✅ Резервная копия создана: $BACKUP_NAME'"
        ;;
    
    "shell")
        echo -e "${GREEN}🖥️ Подключение к серверу...${NC}"
        ssh -t "$SERVER_USER@$SERVER_IP" "cd $PROJECT_PATH && bash"
        ;;
    
    "setup")
        echo -e "${GREEN}⚙️ Настройка алиасов...${NC}"
        cat >> ~/.bashrc << EOF

# 🤖 Алиасы для управления модератор-ботом
alias bot-update="$0 update"
alias bot-status="$0 status"
alias bot-logs="$0 logs"
alias bot-restart="$0 restart"
alias bot-backup="$0 backup"
alias bot-shell="$0 shell"
EOF
        echo -e "${GREEN}✅ Алиасы добавлены в ~/.bashrc${NC}"
        echo "Выполните: source ~/.bashrc"
        echo ""
        echo "Теперь доступны команды:"
        echo "  bot-update, bot-status, bot-logs, bot-restart, bot-backup, bot-shell"
        ;;
    
    "config")
        echo -e "${BLUE}⚙️ Текущая конфигурация:${NC}"
        echo "Сервер: $SERVER_USER@$SERVER_IP"
        echo "Путь: $PROJECT_PATH"
        echo ""
        echo "Для изменения отредактируйте переменные в начале скрипта:"
        echo "  SERVER_IP, SERVER_USER, PROJECT_PATH"
        ;;
    
    "test")
        echo -e "${GREEN}🧪 Тестирование соединения...${NC}"
        if ssh -o ConnectTimeout=5 "$SERVER_USER@$SERVER_IP" "echo 'Соединение успешно'"; then
            echo -e "${GREEN}✅ SSH соединение работает${NC}"
            
            if run_remote_quiet "test -f docker-compose.yml"; then
                echo -e "${GREEN}✅ Проект найден на сервере${NC}"
                
                if run_remote_quiet "docker compose ps >/dev/null 2>&1"; then
                    echo -e "${GREEN}✅ Docker Compose работает${NC}"
                else
                    echo -e "${RED}❌ Docker Compose недоступен${NC}"
                fi
            else
                echo -e "${RED}❌ Проект не найден по пути: $PROJECT_PATH${NC}"
            fi
        else
            echo -e "${RED}❌ SSH соединение не удалось${NC}"
        fi
        ;;
    
    "")
        show_help
        ;;
    
    *)
        echo -e "${RED}❌ Неизвестная команда: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
