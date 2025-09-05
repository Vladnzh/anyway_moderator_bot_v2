.PHONY: help install run-bot run-admin run-admin-bg run-both clean test logs open-admin open-legacy api-test stop status set-token

VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

help:
	@echo "🤖 Anyway Moderator Bot v2 - Команды:"
	@echo ""
	@echo "⚡ Быстрый старт:"
	@echo "  make setup       - Полная настройка (venv + зависимости + .env)"
	@echo ""
	@echo "📦 Установка:"
	@echo "  make install     - Создать виртуальное окружение и установить зависимости"
	@echo ""
	@echo "🚀 Запуск:"
	@echo "  make run-bot     - Запустить бота"
	@echo "  make run-admin   - Запустить админку (с авто-перезагрузкой)"
	@echo "  make run-admin-bg- Запустить админку в фоне"
	@echo "  make run-both    - Запустить бота и админку одновременно"
	@echo ""
	@echo "🌐 Веб-интерфейсы:"
	@echo "  make open-admin  - Открыть новую админку в браузере"
	@echo "  make open-legacy - Открыть legacy админку в браузере"
	@echo "  make api-test    - Протестировать API"
	@echo ""
	@echo "🧹 Очистка:"
	@echo "  make clean       - Очистить Python кэш и временные файлы"
	@echo ""
	@echo "📊 Информация:"
	@echo "  make test        - Протестировать конфигурацию"
	@echo "  make logs        - Показать последние логи"
	@echo "  make status      - Показать статус сервисов"
	@echo ""
	@echo "🛑 Управление:"
	@echo "  make stop        - Остановить все процессы"
	@echo "  make set-token   - Установить токен администратора"
	@echo ""

install: setup

setup:
	@echo "🔧 Настройка виртуального окружения..."
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt
	@echo "✅ Окружение готово!"
	@echo ""
	@echo "📝 Настройка .env файла..."
	python3 start.py

run-bot:
	@echo "🤖 Запуск бота..."
	$(PYTHON) bot.py

run-admin:
	@echo "🎛️ Запуск админки с API..."
	@if [ -z "$$ADMIN_TOKEN" ]; then \
		if [ -f .env ] && grep -q "ADMIN_TOKEN=" .env; then \
			echo "📄 Загружаю токен из .env файла..."; \
			export $$(grep ADMIN_TOKEN .env | xargs) && $(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0; \
		else \
			echo "🔐 Введите токен администратора:"; \
			read -s token; \
			if [ -n "$$token" ]; then \
				echo "✅ Токен установлен"; \
				ADMIN_TOKEN=$$token $(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0; \
			else \
				echo "⚠️  Токен не введен, используется 'changeme'"; \
				ADMIN_TOKEN=changeme $(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0; \
			fi; \
		fi; \
	else \
		$(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0; \
	fi

run-admin-bg:
	@echo "🎛️ Запуск админки в фоне..."
	@if [ -z "$$ADMIN_TOKEN" ]; then \
		echo "⚠️  ADMIN_TOKEN не установлен, используется 'changeme'"; \
		ADMIN_TOKEN=changeme $(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0 & \
	else \
		$(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0 & \
	fi

clean:
	@echo "🧹 Очистка..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✅ Очищено!"

clean-db:
	@echo "🗄️ Полная очистка SQLite базы данных..."
	@rm -f bot_data.db
	@python3 -c "from database import db; print('✅ Чистая SQLite база создана')"
	@echo "🎉 База данных очищена! Можете создавать теги с нуля."

test:
	@echo "🧪 Тестирование SQLite базы данных..."
	@$(PYTHON) -c "from database import db; stats = db.get_stats(); print(f'📊 Тегов в базе: {stats[\"total_tags\"]}'); tags = db.get_tags(); [print(f'🏷️  {tag[\"tag\"]} -> {tag[\"emoji\"]} (ID: {tag[\"id\"]})') for tag in tags]; print('✅ SQLite база работает корректно!')"

logs:
	@echo "📋 Последние логи из SQLite базы:"
	@$(PYTHON) -c "from database import db; logs = db.get_logs(limit=5); [print(f'{l[\"timestamp\"]} [{l[\"username\"]}] {l[\"trigger\"]} -> {l[\"emoji\"]}') for l in logs] if logs else print('📝 Логов пока нет')" 2>/dev/null || echo "❌ Ошибка чтения логов из SQLite"

run-both:
	@echo "🚀 Запуск бота и админки одновременно..."
	@echo "🤖 Запуск бота в фоне..."
	@$(PYTHON) bot.py &
	@echo "🎛️ Запуск админки..."
	@if [ -z "$$ADMIN_TOKEN" ]; then \
		if [ -f .env ] && grep -q "ADMIN_TOKEN=" .env; then \
			echo "📄 Загружаю токен из .env файла..."; \
			export $$(grep ADMIN_TOKEN .env | xargs) && $(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0; \
		else \
			echo "🔐 Введите токен администратора:"; \
			read -s token; \
			if [ -n "$$token" ]; then \
				echo "✅ Токен установлен"; \
				ADMIN_TOKEN=$$token $(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0; \
			else \
				echo "⚠️  Токен не введен, используется 'changeme'"; \
				ADMIN_TOKEN=changeme $(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0; \
			fi; \
		fi; \
	else \
		$(VENV)/bin/uvicorn admin:app --reload --port 8000 --host 0.0.0.0; \
	fi

open-admin:
	@echo "🌐 Открытие новой админки..."
	@open http://localhost:8000/ 2>/dev/null || echo "❌ Не удалось открыть браузер. Перейдите на http://localhost:8000/"

open-legacy:
	@echo "🌐 Открытие legacy админки..."
	@open "http://localhost:8000/legacy?token=$${ADMIN_TOKEN:-changeme}" 2>/dev/null || echo "❌ Не удалось открыть браузер. Перейдите на http://localhost:8000/legacy?token=$${ADMIN_TOKEN:-changeme}"

api-test:
	@echo "🧪 Тестирование API..."
	@echo "📡 Проверка конфигурации..."
	@curl -s -H "Authorization: Bearer $${ADMIN_TOKEN:-changeme}" http://localhost:8000/api/config | $(PYTHON) -m json.tool 2>/dev/null || echo "❌ API недоступно. Запустите админку: make run-admin"
	@echo ""
	@echo "📊 Проверка статистики..."
	@curl -s -H "Authorization: Bearer $${ADMIN_TOKEN:-changeme}" http://localhost:8000/api/stats | $(PYTHON) -m json.tool 2>/dev/null || echo "❌ Статистика недоступна"

stop:
	@echo "🛑 Остановка всех процессов..."
	@echo "🔍 Поиск процессов бота..."
	@pids=$$(ps aux | grep -E "(bot\.py|python.*bot)" | grep -v grep | awk '{print $$2}' || true); \
	if [ -n "$$pids" ]; then \
		echo "🤖 Найдены процессы бота: $$pids"; \
		kill $$pids 2>/dev/null || true; \
		sleep 2; \
		remaining=$$(ps aux | grep -E "(bot\.py|python.*bot)" | grep -v grep | awk '{print $$2}' || true); \
		if [ -n "$$remaining" ]; then \
			echo "⚠️  Принудительная остановка: $$remaining"; \
			kill -9 $$remaining 2>/dev/null || true; \
		fi; \
		echo "✅ Бот остановлен"; \
	else \
		echo "🤖 Бот не запущен"; \
	fi
	@echo "🔍 Поиск процессов админки..."
	@pkill -f "uvicorn.*admin:app" 2>/dev/null && echo "✅ Админка остановлена" || echo "🎛️ Админка не запущена"
	@echo "✅ Все процессы остановлены"

status:
	@echo "📊 Статус сервисов:"
	@printf "🤖 Бот: "
	@ps aux | grep -E "(bot\.py|python.*bot)" | grep -v grep >/dev/null && echo "✅ Запущен" || echo "❌ Остановлен"
	@printf "🎛️ Админка: "
	@pgrep -f "uvicorn.*admin:app" >/dev/null && echo "✅ Запущена (http://localhost:8000/)" || echo "❌ Остановлена"

set-token:
	@echo "🔐 Настройка токена администратора"
	@echo ""
	@if [ -f .env ]; then \
		echo "📄 Найден существующий .env файл"; \
		if grep -q "ADMIN_TOKEN=" .env; then \
			current_token=$$(grep ADMIN_TOKEN .env | cut -d'=' -f2); \
			echo "🔑 Текущий токен: $$current_token"; \
		else \
			echo "⚠️  ADMIN_TOKEN не найден в .env"; \
		fi; \
		echo ""; \
	else \
		echo "📝 Файл .env не найден, будет создан"; \
		echo ""; \
	fi; \
	echo "🔐 Введите новый токен администратора (или Enter для генерации):"; \
	read token; \
	if [ -z "$$token" ]; then \
		echo "🎲 Генерирую безопасный токен..."; \
		token=$$($(PYTHON) -c "import secrets; print(secrets.token_urlsafe(32))"); \
		echo "✨ Сгенерирован токен: $$token"; \
	fi; \
	if [ -f .env ]; then \
		if grep -q "ADMIN_TOKEN=" .env; then \
			sed -i.bak "s/ADMIN_TOKEN=.*/ADMIN_TOKEN=$$token/" .env && rm .env.bak; \
			echo "✅ Токен обновлен в .env файле"; \
		else \
			echo "ADMIN_TOKEN=$$token" >> .env; \
			echo "✅ Токен добавлен в .env файл"; \
		fi; \
	else \
		echo "# Токен Telegram бота (получите у @BotFather)" > .env; \
		echo "BOT_TOKEN=your_bot_token_here" >> .env; \
		echo "" >> .env; \
		echo "# Токен администратора" >> .env; \
		echo "ADMIN_TOKEN=$$token" >> .env; \
		echo "" >> .env; \
		echo "# Пути к файлам конфигурации" >> .env; \
		echo "CONFIG_PATH=config_json" >> .env; \
		echo "LOGS_PATH=logs.json" >> .env; \
		echo "✅ Создан .env файл с токеном"; \
	fi; \
	echo ""; \
	echo "🎉 Готово! Теперь можете запустить админку: make run-admin"

# ===== DOCKER КОМАНДЫ =====

# Сборка образов
docker-build:
	@echo "🐳 Сборка Docker образов..."
	docker-compose -p moderator-bot build

# Development запуск (без Nginx)
docker-dev:
	@echo "🔧 Запуск в development режиме..."
	docker-compose -p moderator-bot up -d bot admin

# Production запуск (с Nginx)
docker-prod:
	@echo "🌐 Запуск в production режиме..."
	docker-compose -p moderator-bot --profile production up -d

# Остановка всех сервисов
docker-stop:
	@echo "🛑 Остановка всех сервисов..."
	docker-compose -p moderator-bot down

# Логи всех сервисов
docker-logs:
	@echo "📋 Логи всех сервисов..."
	docker-compose -p moderator-bot logs -f

# Статус сервисов
docker-status:
	@echo "📊 Статус сервисов..."
	docker-compose -p moderator-bot ps

# Быстрое развертывание
deploy-dev:
	@echo "🚀 Быстрое развертывание (development)..."
	./deploy.sh staging

deploy-prod:
	@echo "🌐 Быстрое развертывание (production)..."
	./deploy.sh production