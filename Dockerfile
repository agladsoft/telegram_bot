FROM python:3.8

# Копируем python-файлы
COPY *.py /app/

# Копируем файл requirements.txt в контейнер
COPY requirements.txt /app/

# Переключаемся в рабочую директорию /app
WORKDIR /app

# Устанавливаем зависимости из requirements.txt
RUN pip install -r requirements.txt

# Запускаем скрипт при запуске контейнера
CMD ["python3", "main.py"]
