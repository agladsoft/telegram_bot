import telebot
import requests
from __init__ import *
from telebot import types
from datetime import datetime
from dadata.sync import DadataClient
from requests import exceptions, Response

bot = telebot.TeleBot(TOKEN_TELEGRAM)
logger: getLogger = get_logger(os.path.basename(__file__).replace(".py", "_") + str(datetime.now().date()))


@bot.message_handler(commands=['start'])
def start_bot(message):
    first_mess = f"<b>{message.from_user.first_name} {message.from_user.last_name}</b>, " \
                 f"привет!\nЗдесь представлены на выбор проверка сервисов."
    markup = types.InlineKeyboardMarkup()
    button_check_db = types.InlineKeyboardButton(text='Проверить подключение к базе данных', callback_data='check_db')
    button_check_yandex = types.InlineKeyboardButton(text='Проверить баланс на Яндекс.Кошельке',
                                                     callback_data='check_yandex')
    button_check_dadata = types.InlineKeyboardButton(text='Получить оставшиеся количество запросов в Dadata',
                                                     callback_data='check_dadata')
    button_get_chat_id = types.InlineKeyboardButton(text='Получить Chat ID', callback_data='get_chat_id')
    markup.row(button_check_db)
    markup.row(button_check_yandex)
    markup.row(button_check_dadata)
    markup.row(button_get_chat_id)

    bot.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)


@bot.message_handler(commands=['check_connect_db'])
def check_connect_db(message):
    try:
        response = requests.get(f"http://{IP_ADDRESS_DB}:8123", timeout=120)
        response.raise_for_status()
        if "Ok" in response.text:
            bot.reply_to(message, "Подключение к базе стабильно")
        else:
            bot.reply_to(message, "Подключение к базе отсутствует")
    except exceptions.RequestException as e:
        logger.error(f"Во время запроса API произошла ошибка - {e}")
        bot.reply_to(message, 'Не удалось получить ответ от сервера')


@bot.message_handler(commands=['check_balance_xml_river'])
def check_balance_xml_river(message):
    try:
        response: Response = requests.get(f"https://xmlriver.com/api/get_balance/yandex/"
                                          f"?user={USER_XML_RIVER}&key={KEY_XML_RIVER}", timeout=120)
        response.raise_for_status()
        bot.reply_to(message, f"Баланс на Яндекс.Кошельке составляет {float(response.text)} рублей")
    except exceptions.RequestException as e:
        logger.error(f"Во время запроса API произошла ошибка - {e}")
        bot.reply_to(message, 'Не удалось получить ответ от Яндекс.Кошелька')


@bot.message_handler(commands=['check_num_requests_dadata'])
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
    bot.reply_to(message, message_response)


@bot.message_handler(commands=['get_chat_id'])
def get_chat_id(message):
    chat_id = message.chat.id
    bot.reply_to(message, f'Chat ID этого чата: {chat_id}')


# Обработчик для кнопок на клавиатуре
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.data == 'check_db':
        check_connect_db(call.message)
    elif call.data == 'check_yandex':
        check_balance_xml_river(call.message)
    elif call.data == 'check_dadata':
        check_num_requests_dadata(call.message)
    elif call.data == 'get_chat_id':
        get_chat_id(call.message)


bot.polling()
