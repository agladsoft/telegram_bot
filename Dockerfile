# Используем базовый образ Python 3.8
FROM python:3.8

# Устанавливаем имя контейнера
LABEL container_name="telegram_bot"

# Копируем файл requirements.txt в контейнер
COPY requirements.txt /app/requirements.txt

# Переключаемся в рабочую директорию /app
WORKDIR /app

# Устанавливаем зависимости из requirements.txt
RUN pip install -r requirements.txt

# Копируем файл telegram_bot.py в контейнер
COPY telegram_bot.py /app/telegram_bot.py

# Запускаем скрипт при запуске контейнера
CMD ["python", "telegram_bot.py"]
