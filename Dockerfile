FROM python:3.8

# Устанавливаем имя контейнера
LABEL container_name="telegram_bot"

# Копируем файл requirements.txt в контейнер
COPY * /app/

# Переключаемся в рабочую директорию /app
WORKDIR /app

# Устанавливаем зависимости из requirements.txt
RUN pip install -r requirements.txt

# Запускаем скрипт при запуске контейнера
CMD ["python3", "improved_interface.py"]
