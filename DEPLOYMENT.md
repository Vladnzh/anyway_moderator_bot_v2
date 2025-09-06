# 🚀 Руководство по развертыванию на Hetzner

## 📋 Предварительные требования

### На локальной машине:
- Docker и Docker Compose
- Git
- SSH доступ к серверу Hetzner

### На сервере Hetzner:
- Ubuntu 20.04+ или Debian 11+
- Docker и Docker Compose
- Минимум 1GB RAM, 10GB диска
- Открытые порты: 80, 443, 8000

## 🛠️ Подготовка сервера

### 1. Подключение к серверу
```bash
ssh root@your-server-ip
```

### 2. Установка Docker
```bash
# Обновляем систему
apt update && apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Устанавливаем Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Проверяем установку
docker --version
docker-compose --version
```

### 3. Настройка файрвола (UFW)
```bash
# Устанавливаем UFW
apt install ufw -y

# Базовые правила
ufw default deny incoming
ufw default allow outgoing

# Разрешаем SSH
ufw allow ssh

# Разрешаем HTTP/HTTPS
ufw allow 80
ufw allow 443

# Разрешаем админку (опционально, для прямого доступа)
ufw allow 8000

# Включаем файрвол
ufw enable
```

## 📦 Развертывание проекта

### 1. Клонирование репозитория
```bash
# Создаем директорию для проекта
mkdir -p /opt/moderator-bot
cd /opt/moderator-bot

# Клонируем репозиторий
git clone https://github.com/your-username/anyway-moderator-bot-v2.git .

# Или загружаем архив
# wget https://github.com/your-username/anyway-moderator-bot-v2/archive/main.zip
# unzip main.zip && mv anyway-moderator-bot-v2-main/* .
```

### 2. Настройка переменных окружения
```bash
# Копируем пример конфигурации
cp env.example .env

# Редактируем конфигурацию
nano .env
```

Заполните файл `.env`:
```bash
# Токен бота от @BotFather
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Безопасный токен для админки (сгенерируйте случайный)
ADMIN_TOKEN=your_very_secure_random_token_here

# Путь к базе данных
DATABASE_PATH=/app/data/bot_data.db
```

### 3. Подготовка SSL сертификатов (для production)

#### Вариант A: Let's Encrypt (рекомендуется)
```bash
# Устанавливаем Certbot
apt install certbot -y

# Получаем сертификат
certbot certonly --standalone -d your-domain.com

# Создаем директорию для SSL
mkdir -p ssl

# Копируем сертификаты
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

#### Вариант B: Самоподписанный сертификат (для тестирования)
```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### 4. Миграция существующих данных (если есть)
```bash
# Если у вас есть JSON файлы от старой версии
# Скопируйте их в корень проекта:
# config_json, logs.json, moderation_queue.json и т.д.

# Миграция будет выполнена автоматически при первом запуске
```

## 🚀 Запуск

### Development режим (без Nginx)
```bash
chmod +x deploy.sh
./deploy.sh staging
```

### Production режим (с Nginx и SSL)
```bash
chmod +x deploy.sh
./deploy.sh production
```

## 📊 Мониторинг и управление

### Проверка статуса
```bash
# Статус контейнеров
docker-compose -p moderator-bot ps

# Логи всех сервисов
docker-compose -p moderator-bot logs -f

# Логи конкретного сервиса
docker-compose -p moderator-bot logs -f bot
docker-compose -p moderator-bot logs -f admin
```

### Управление сервисами
```bash
# Перезапуск
docker-compose -p moderator-bot restart

# Остановка
docker-compose -p moderator-bot down

# Обновление (пересборка образов)
docker-compose -p moderator-bot build --no-cache
docker-compose -p moderator-bot up -d
```

### Резервное копирование
```bash
# Создание бэкапа базы данных
docker run --rm \
    -v moderator-bot_bot_data:/data \
    -v $(pwd):/backup \
    alpine tar czf /backup/backup-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

# Восстановление из бэкапа
docker run --rm \
    -v moderator-bot_bot_data:/data \
    -v $(pwd):/backup \
    alpine tar xzf /backup/backup-YYYYMMDD-HHMMSS.tar.gz -C /data
```

## 🔧 Настройка домена и DNS

### 1. Настройка DNS записей
В панели управления доменом создайте A-запись:
```
A    your-domain.com    your-server-ip
A    www.your-domain.com    your-server-ip
```

### 2. Обновление Nginx конфигурации
```bash
# Редактируем nginx.conf
nano nginx.conf

# Заменяем server_name _ на ваш домен
server_name your-domain.com www.your-domain.com;
```

### 3. Перезапуск с новой конфигурацией
```bash
docker-compose -p moderator-bot restart nginx
```

## 🔒 Безопасность

### 1. Настройка автоматического обновления SSL
```bash
# Создаем скрипт обновления
cat > /etc/cron.daily/ssl-renew << 'EOF'
#!/bin/bash
certbot renew --quiet
if [ $? -eq 0 ]; then
    cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/moderator-bot/ssl/cert.pem
    cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/moderator-bot/ssl/key.pem
    cd /opt/moderator-bot
    docker-compose -p moderator-bot restart nginx
fi
EOF

chmod +x /etc/cron.daily/ssl-renew
```

### 2. Настройка логирования
```bash
# Настройка ротации логов Docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

systemctl restart docker
```

### 3. Мониторинг ресурсов
```bash
# Установка htop для мониторинга
apt install htop -y

# Просмотр использования ресурсов Docker
docker stats

# Просмотр дискового пространства
df -h
docker system df
```

## 🚨 Устранение неполадок

### Проблемы с запуском
```bash
# Проверка логов
docker-compose -p moderator-bot logs

# Проверка конфигурации
docker-compose -p moderator-bot config

# Пересборка образов
docker-compose -p moderator-bot build --no-cache
```

### Проблемы с базой данных
```bash
# Проверка базы данных
docker run --rm \
    -v moderator-bot_bot_data:/data \
    alpine ls -la /data

# Подключение к базе данных
docker run --rm -it \
    -v moderator-bot_bot_data:/data \
    alpine sqlite3 /data/bot_data.db ".tables"
```

### Проблемы с SSL
```bash
# Проверка сертификатов
openssl x509 -in ssl/cert.pem -text -noout

# Тест SSL соединения
openssl s_client -connect your-domain.com:443
```

## 📈 Масштабирование

### Увеличение ресурсов
```yaml
# В docker-compose.yml добавьте ограничения ресурсов:
services:
  bot:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### Мониторинг производительности
```bash
# Установка Prometheus и Grafana (опционально)
# Для продвинутого мониторинга
```

## 🔄 Обновление проекта

### 🚀 Автоматическое обновление (рекомендуется)

#### На сервере:
```bash
cd /opt/moderator-bot/anyway_moderator_bot_v2
./update_project.sh
```

#### Удалённо через SSH:
```bash
# Простое обновление
ssh root@your-server-ip "cd /opt/moderator-bot/anyway_moderator_bot_v2 && ./update_project.sh"

# С выводом логов в реальном времени
ssh -t root@your-server-ip "cd /opt/moderator-bot/anyway_moderator_bot_v2 && ./update_project.sh"

# Через алиас (настройте один раз)
alias update-bot="ssh -t root@your-server-ip 'cd /opt/moderator-bot/anyway_moderator_bot_v2 && ./update_project.sh'"
update-bot
```

### 🛡️ Что делает скрипт обновления:

1. **💾 Создаёт резервную копию** базы данных с временной меткой
2. **📥 Получает обновления** из Git репозитория  
3. **🛑 Останавливает** контейнеры
4. **🏗️ Пересобирает** Docker образы
5. **🚀 Запускает** обновлённые контейнеры
6. **🧪 Проверяет** работоспособность API
7. **📋 Показывает** статус и логи

### 📁 Сохранение данных

✅ **Сохраняется при обновлениях:**
- 🏷️ Все созданные теги и настройки
- 📊 История логов и статистика  
- 🔄 Очередь модерации
- 🗄️ База данных SQLite (`./data/bot_data.db`)

❌ **Обновляется:**
- 🔧 Код приложения
- 🐳 Docker образы
- 📝 Конфигурационные файлы

### 🔧 Ручное обновление

Если автоматический скрипт недоступен:

```bash
# На сервере
cd /opt/moderator-bot/anyway_moderator_bot_v2

# 1. Резервная копия
cp data/bot_data.db data/bot_data.db.backup.$(date +%Y%m%d_%H%M%S)

# 2. Получение обновлений
git stash push -m "Auto-stash before update"
git pull origin main

# 3. Перезапуск
docker compose down
docker compose build
docker compose up -d
```

### 🌐 Удалённое обновление через веб-интерфейс

Создайте простой веб-хук для обновления:

```bash
# Создайте скрипт webhook.sh на сервере
cat > /opt/moderator-bot/webhook.sh << 'EOF'
#!/bin/bash
cd /opt/moderator-bot/anyway_moderator_bot_v2
./update_project.sh > /tmp/update.log 2>&1
EOF

chmod +x /opt/moderator-bot/webhook.sh

# Запуск через curl
curl -X POST http://your-server-ip:9000/webhook
```

### 📊 Мониторинг после обновления

```bash
# Проверка статуса
ssh root@your-server-ip "cd /opt/moderator-bot/anyway_moderator_bot_v2 && docker compose ps"

# Просмотр логов
ssh root@your-server-ip "cd /opt/moderator-bot/anyway_moderator_bot_v2 && docker compose logs -f bot"

# Проверка API
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  "http://your-server-ip:8000/api/stats"
```

### 🚨 Восстановление при проблемах

Если обновление прошло неудачно:

```bash
# 1. Остановить контейнеры
ssh root@your-server-ip "cd /opt/moderator-bot/anyway_moderator_bot_v2 && docker compose down"

# 2. Восстановить базу данных
ssh root@your-server-ip "cd /opt/moderator-bot/anyway_moderator_bot_v2 && cp data/bot_data.db.backup.* data/bot_data.db"

# 3. Откатить Git изменения
ssh root@your-server-ip "cd /opt/moderator-bot/anyway_moderator_bot_v2 && git reset --hard HEAD~1"

# 4. Запустить заново
ssh root@your-server-ip "cd /opt/moderator-bot/anyway_moderator_bot_v2 && docker compose up -d"
```

### ⚡ Быстрые команды

Добавьте в `~/.bashrc` или `~/.zshrc` для удобства:

```bash
# Алиасы для управления ботом
alias bot-status="ssh root@your-server-ip 'cd /opt/moderator-bot/anyway_moderator_bot_v2 && docker compose ps'"
alias bot-logs="ssh -t root@your-server-ip 'cd /opt/moderator-bot/anyway_moderator_bot_v2 && docker compose logs -f bot'"
alias bot-update="ssh -t root@your-server-ip 'cd /opt/moderator-bot/anyway_moderator_bot_v2 && ./update_project.sh'"
alias bot-restart="ssh root@your-server-ip 'cd /opt/moderator-bot/anyway_moderator_bot_v2 && docker compose restart'"
```

После добавления выполните: `source ~/.bashrc`

### 📋 Регулярное обновление

Настройте автоматическое обновление через cron:

```bash
# На сервере добавьте в crontab
ssh root@your-server-ip "crontab -e"

# Добавьте строку (обновление каждое воскресенье в 3:00)
0 3 * * 0 cd /opt/moderator-bot/anyway_moderator_bot_v2 && ./update_project.sh >> /var/log/bot-update.log 2>&1
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose -p moderator-bot logs`
2. Убедитесь в правильности .env файла
3. Проверьте доступность портов
4. Проверьте SSL сертификаты (для HTTPS)
