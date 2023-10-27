FROM python:3.8

LABEL container_name="telegram_bot"

CMD ["echo", "Running Telegram Bot!"]

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN python3 telegram_bot.py