import docker
import telebot
import requests
from __init__ import *
from telebot import types
from datetime import datetime
from dadata.sync import DadataClient
from requests import exceptions, Response

client = docker.from_env()
bot = telebot.TeleBot(TOKEN_TELEGRAM)
logger: getLogger = get_logger(os.path.basename(__file__).replace(".py", "_") + str(datetime.now().date()))


@bot.message_handler(commands=['start'])
def start_bot(message):
    first_mess = f"<b>{message.from_user.first_name} {message.from_user.last_name}</b>, " \
                 f"привет!\nЗдесь представлены на выбор проверка сервисов."
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_check_db = types.KeyboardButton(text='Проверить подключение к базе данных')
    button_check_yandex = types.KeyboardButton(text='Проверить баланс на Яндекс.Кошельке')
    button_check_dadata = types.KeyboardButton(text='Получить оставшиеся количество запросов в Dadata')
    button_get_logs_docker = types.KeyboardButton(text='Получить логи контейнеров')
    markup.add(button_check_db, button_check_yandex, button_check_dadata, button_get_logs_docker)

    bot.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)


@bot.message_handler(content_types=['text'])
def bot_message(message):
    if message.text == 'Проверить подключение к базе данных':
        keyboard = types.InlineKeyboardMarkup()
        key = types.InlineKeyboardButton(text='Проверить подключение к базе данных', callback_data='check_connect_db')
        keyboard.add(key)
        bot.send_message(message.from_user.id, text='Проверить подключение к базе данных', reply_markup=keyboard)
    elif message.text == 'Проверить баланс на Яндекс.Кошельке':
        keyboard = types.InlineKeyboardMarkup()
        key = types.InlineKeyboardButton(text='Проверить баланс на Яндекс.Кошельке',
                                         callback_data='check_balance_xml_river')
        keyboard.add(key)
        bot.send_message(message.from_user.id, text='Проверить баланс на Яндекс.Кошельке', reply_markup=keyboard)
    elif message.text == 'Получить оставшиеся количество запросов в Dadata':
        keyboard = types.InlineKeyboardMarkup()
        key = types.InlineKeyboardButton(text='Получить оставшиеся количество запросов в Dadata',
                                         callback_data='check_num_requests_dadata')
        keyboard.add(key)
        bot.send_message(message.from_user.id, text='Получить оставшиеся количество запросов в Dadata',
                         reply_markup=keyboard)
    elif message.text == 'Получить логи контейнеров':
        keyboard = types.InlineKeyboardMarkup()
        key = types.InlineKeyboardButton(text='Получить логи контейнеров',
                                         callback_data='get_logs_docker')
        keyboard.add(key)
        bot.send_message(message.from_user.id, text='Получить логи контейнеров', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    if call.data == "check_connect_db":
        check_connect_db(call.from_user.id)
    elif call.data == "check_balance_xml_river":
        check_balance_xml_river(call.from_user.id)
    elif call.data == "check_num_requests_dadata":
        check_num_requests_dadata(call.from_user.id)
    elif call.data == 'get_logs_docker':
        markup = types.InlineKeyboardMarkup()
        for container in DOCKER_CONTAINER:
            log_container = types.InlineKeyboardButton(container, callback_data=f'get_log_container_{container}')
            markup.add(log_container)
        close_menu = types.InlineKeyboardButton('Закрыть меню', callback_data='close')
        markup.add(close_menu)
        bot.edit_message_text('Выберите контейнер для получения логов:', call.message.chat.id, call.message.message_id,
                              reply_markup=markup)
    elif call.data == 'close':
        bot.edit_message_text('Меню закрыто', call.message.chat.id, call.message.message_id)
    elif call.data.startswith('get_log_container'):
        container_name = call.data[len('get_log_container_'):]
        get_log_container(call.from_user.id, container_name)


def check_connect_db(message):
    try:
        response = requests.get(f"http://{IP_ADDRESS_DB}:8123", timeout=30)
        response.raise_for_status()
        if "Ok" in response.text:
            bot.send_message(message, "Подключение к базе стабильно")
        else:
            bot.send_message(message, "Подключение к базе отсутствует")
    except exceptions.RequestException as e:
        logger.error(f"Во время запроса API произошла ошибка - {e}")
        bot.send_message(message, 'Не удалось получить ответ от сервера')


def check_balance_xml_river(message):
    try:
        response: Response = requests.get(f"https://xmlriver.com/api/get_balance/yandex/"
                                          f"?user={USER_XML_RIVER}&key={KEY_XML_RIVER}", timeout=120)
        response.raise_for_status()
        bot.send_message(message, f"Баланс на Яндекс.Кошельке составляет {float(response.text)} рублей")
    except exceptions.RequestException as e:
        logger.error(f"Во время запроса API произошла ошибка - {e}")
        bot.send_message(message, 'Не удалось получить ответ от Яндекс.Кошелька')


def check_num_requests_dadata(message):
    token_and_secrets: list = list(ACCOUNTS_SERVICE_INN.items())
    dict_statistics: dict = {}
    for index, token_and_secret in enumerate(token_and_secrets, 1):
        dadata: DadataClient = DadataClient(token=token_and_secret[0], secret=token_and_secret[1])
        dict_statistics[f"ACCOUNT_NUMBER_{index}"] = dadata.get_daily_stats(datetime.now().date())
    message_response: str = ''.join(
        f'Количество оставшиеся запросов за {data["date"]} на аккаунте {account} составляет '
        f'{data["remaining"]["suggestions"]}\n'
        for account, data in dict_statistics.items()
    )
    bot.send_message(message, message_response)


def get_log_container(message, container_name):
    logs = client.containers.get(container_name).logs()
    lines = logs.decode('utf-8').split("\n")
    last_lines = "\n".join(lines[-50:])
    bot.send_message(message, f'Логи контейнера {container_name}:\n{last_lines}')


if __name__ == "__main__":
    bot.infinity_polling()
