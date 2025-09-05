# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем директории для данных
RUN mkdir -p /app/data /app/static /app/json_backup

# Устанавливаем права на выполнение для скриптов
# RUN chmod +x migrate_to_sqlite.py

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Переменные окружения
ENV PYTHONPATH=/app
ENV DATABASE_PATH=/app/data/bot_data.db

# Порт для админки
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/static/admin.html || exit 1

# Команда по умолчанию (запуск админки)
CMD ["python", "admin.py"]
