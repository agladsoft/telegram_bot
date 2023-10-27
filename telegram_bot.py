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


class TelegramBotManager:
    def __init__(self, message):
        self.message = message

    def check_connect_db(self):
        """

        :return:
        """
        try:
            response = requests.get(f"http://{IP_ADDRESS_DB}:8123", timeout=30)
            response.raise_for_status()
            if "Ok" in response.text:
                bot.send_message(self.message.from_user.id, "Подключение к базе стабильно")
            else:
                bot.send_message(self.message.from_user.id, "Подключение к базе отсутствует")
        except exceptions.RequestException as e:
            logger.error(f"Во время запроса API произошла ошибка - {e}")
            bot.send_message(self.message.from_user.id, 'Не удалось получить ответ от сервера')

    def check_balance_xml_river(self):
        """

        :return:
        """
        try:
            response: Response = requests.get(f"https://xmlriver.com/api/get_balance/yandex/"
                                              f"?user={USER_XML_RIVER}&key={KEY_XML_RIVER}", timeout=120)
            response.raise_for_status()
            bot.send_message(self.message.from_user.id,
                             f"Баланс на Яндекс.Кошельке составляет {float(response.text)} рублей")
        except exceptions.RequestException as e:
            logger.error(f"Во время запроса API произошла ошибка - {e}")
            bot.send_message(self.message.from_user.id, 'Не удалось получить ответ от Яндекс.Кошелька')

    def check_num_requests_dadata(self):
        """

        :return:
        """
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
        bot.send_message(self.message.from_user.id, message_response)

    def check_logs_containers(self):
        """

        :return:
        """
        keyboard = callback_worker(types.CallbackQuery(
            id=self.message.from_user.id,
            from_user=self.message.from_user,
            chat_instance=TOKEN_TELEGRAM,
            json_string='',
            data='get_logs_docker',
            message=self.message
        ))
        bot.send_message(self.message.from_user.id, text='Список контейнеров', reply_markup=keyboard)

    def get_log_container(self, container_name):
        """

        :param container_name:
        :return:
        """
        logs = client.containers.get(container_name).logs()
        lines = logs.decode('utf-8').split("\n")
        last_lines = "\n".join(lines[-50:])
        bot.send_message(self.message, f'Логи контейнера {container_name}:\n{last_lines}')


@bot.message_handler(commands=['start'])
def start_bot(message):
    first_mess = f"<b>{message.from_user.first_name} {message.from_user.last_name}</b>, " \
                 f"привет!\nЗдесь представлены на выбор проверка сервисов."
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [types.KeyboardButton(text=button_text) for button_text in BUTTONS_TELEGRAM_BOT]
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.add(buttons[i], buttons[i + 1])
        else:
            markup.add(buttons[i])
    bot.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)


@bot.message_handler(content_types=['text'])
def bot_message(message):
    telegram_bot_manager = TelegramBotManager(message)
    if message.text in BUTTONS_TELEGRAM_BOT:
        method_name = BUTTONS_TELEGRAM_BOT[message.text]
        method_to_call = getattr(telegram_bot_manager, method_name)
        method_to_call()


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    if call.data == 'get_logs_docker':
        markup = types.InlineKeyboardMarkup()
        for container in [container.name for container in client.containers.list()]:
            log_container = types.InlineKeyboardButton(container, callback_data=f'get_log_container_{container}')
            markup.add(log_container)
        markup.add(types.InlineKeyboardButton('Закрыть меню', callback_data='close'))
        return markup
    elif call.data == 'close':
        bot.edit_message_text('Меню закрыто', call.message.chat.id, call.message.message_id)
    elif call.data.startswith('get_log_container'):
        TelegramBotManager.get_log_container(call.data[len('get_log_container_'):])


if __name__ == "__main__":
    bot.infinity_polling()
