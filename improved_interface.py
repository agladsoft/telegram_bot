import docker
import telebot
import requests
from __init__ import *
from telebot import types
from datetime import datetime
from docker import DockerClient
from telebot.types import Message
from dadata.sync import DadataClient
from requests import exceptions, Response


client: DockerClient = docker.from_env()
bot: telebot.TeleBot = telebot.TeleBot(TOKEN_TELEGRAM)
logger: getLogger = get_logger(os.path.basename(__file__).replace(".py", "_") + str(datetime.now().date()))


def start_menu(message: Message, is_back: bool):
    first_mess: str = f"<b>{message.from_user.first_name} {message.from_user.last_name}</b>, " \
                      f"привет!\nЗдесь представлены на выбор проверка сервисов."

    markup: types.InlineKeyboardMarkup = types.InlineKeyboardMarkup()
    button_check_db: types.InlineKeyboardButton = \
        types.InlineKeyboardButton(text='Подключение к базе данных', callback_data='check_db')
    button_check_yandex: types.InlineKeyboardButton = \
        types.InlineKeyboardButton(text='Баланс на Яндекс.Кошельке', callback_data='check_yandex')
    button_check_dadata: types.InlineKeyboardButton = \
        types.InlineKeyboardButton(text='Оставшиеся количество запросов в Dadata', callback_data='check_dadata')
    button_get_logs_docker: types.InlineKeyboardButton = \
        types.InlineKeyboardButton(text='Логи контейнеров', callback_data='get_logs_docker')
    button_get_chat_id: types.InlineKeyboardButton = \
        types.InlineKeyboardButton(text='Chat ID', callback_data='get_chat_id')

    markup.row(button_check_db)
    markup.row(button_check_yandex)
    markup.row(button_check_dadata)
    markup.row(button_get_logs_docker)
    markup.row(button_get_chat_id)

    if is_back:
        bot.edit_message_text('Вы вернулись в меню', message.chat.id, message.message_id, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)


@bot.message_handler(commands=['start'])
def start_bot(message: Message) -> None:
    start_menu(message, is_back=False)


@bot.message_handler(commands=['check_connect_db'])
def check_connect_db(message: Message) -> None:
    try:
        response: Response = requests.get(f"http://{IP_ADDRESS_DB}:8123", timeout=30)
        response.raise_for_status()
        if "Ok" in response.text:
            bot.reply_to(message, "Подключение к базе стабильно")
        else:
            bot.reply_to(message, "Подключение к базе отсутствует")
    except exceptions.RequestException as e:
        logger.error(f"Во время запроса API произошла ошибка - {e}")
        bot.reply_to(message, 'Не удалось получить ответ от сервера')


@bot.message_handler(commands=['check_balance_xml_river'])
def check_balance_xml_river(message: Message) -> None:
    try:
        response: Response = requests.get(f"https://xmlriver.com/api/get_balance/yandex/"
                                          f"?user={USER_XML_RIVER}&key={KEY_XML_RIVER}", timeout=120)
        response.raise_for_status()
        bot.reply_to(message, f"Баланс на Яндекс.Кошельке составляет {float(response.text)} рублей")
    except exceptions.RequestException as e:
        logger.error(f"Во время запроса API произошла ошибка - {e}")
        bot.reply_to(message, 'Не удалось получить ответ от Яндекс.Кошелька')


@bot.message_handler(commands=['check_num_requests_dadata'])
def check_num_requests_dadata(message: Message) -> None:
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
def get_chat_id(message: Message) -> None:
    chat_id: int = message.chat.id
    bot.reply_to(message, f'Chat ID этого чата: {chat_id}')


@bot.message_handler(commands=['get_logs_docker'])
def get_logs_docker(message: Message) -> None:
    markup: types.InlineKeyboardMarkup = types.InlineKeyboardMarkup()
    for container in [container.name for container in client.containers.list()]:
        log_container: types.InlineKeyboardButton = \
            types.InlineKeyboardButton(container, callback_data=f'get_log_container_{container}')
        markup.add(log_container)
    markup.add(types.InlineKeyboardButton('Вернуться в меню', callback_data='back'))
    markup.add(types.InlineKeyboardButton('Закрыть меню', callback_data='close'))
    try:
        bot.edit_message_text('Выберите контейнер для получения логов:', message.chat.id, message.message_id,
                              reply_markup=markup)
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(message.chat.id, 'Выберите контейнер для получения логов:', parse_mode='html',
                         reply_markup=markup)


def get_log_container(message: Message, container_name: str) -> None:
    logs: bytes = client.containers.get(container_name).logs()
    lines: list = logs.decode('utf-8').split("\n")
    last_lines: str = "\n".join(lines[-50:])
    bot.reply_to(message, f'Логи контейнера {container_name}:\n{last_lines}')


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: types.CallbackQuery):
    if call.data.startswith('get_log_container'):
        container_name: str = call.data[len('get_log_container_'):]
        get_log_container(call.message, container_name)
    elif call.data == 'close':
        bot.edit_message_text('Меню закрыто', call.message.chat.id, call.message.message_id)
    elif call.data == 'back':
        start_menu(call.message, is_back=True)
    else:
        data_actions: dict = {
            'check_db': check_connect_db,
            'check_yandex': check_balance_xml_river,
            'check_dadata': check_num_requests_dadata,
            'get_logs_docker': get_logs_docker,
            'get_chat_id': get_chat_id
        }
        if call.data in data_actions:
            data_actions[call.data](call.message)


if __name__ == "__main__":
    bot.infinity_polling()
