import docker
import telebot
import requests
from __init__ import *
from telebot import types
from typing import Optional
from datetime import datetime
from docker import DockerClient
from telebot.types import Message
from dadata.sync import DadataClient
from requests import exceptions, Response


client: DockerClient = docker.from_env()
bot: telebot.TeleBot = telebot.TeleBot(TOKEN_TELEGRAM)
logger: getLogger = get_logger(os.path.basename(__file__).replace(".py", "_") + str(datetime.now().date()))


class TelegramBotManager:
    def __init__(self, message):
        self.message: Message = message

    def check_connect_db(self) -> None:
        """
        Проверяем подключение к базе.
        :return:
        """
        try:
            response: Response = requests.get(f"http://{IP_ADDRESS_DB}:8123", timeout=30)
            response.raise_for_status()
            if "Ok" in response.text:
                bot.send_message(self.message.from_user.id, "Подключение к базе стабильно")
            else:
                bot.send_message(self.message.from_user.id, "Подключение к базе отсутствует")
        except exceptions.RequestException as e:
            logger.error(f"Во время запроса API произошла ошибка - {e}")
            bot.send_message(self.message.from_user.id, 'Не удалось получить ответ от сервера')

    def check_balance_xml_river(self) -> None:
        """
        Проверяем баланс в Яндекс Кошельке.
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

    def check_num_requests_dadata(self) -> None:
        """
        Проверяем оставшиеся количество запросов в Dadata.
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

    def check_logs_containers(self) -> None:
        """
        Проверяем логи всех контейнеров.
        :return:
        """
        keyboard: types.InlineKeyboardMarkup = callback_worker(types.CallbackQuery(
            id=self.message.from_user.id,
            from_user=self.message.from_user,
            chat_instance=TOKEN_TELEGRAM,
            json_string='',
            data='get_logs_docker',
            message=self.message
        ))
        bot.send_message(self.message.from_user.id, text='Список контейнеров', reply_markup=keyboard)

    @staticmethod
    def get_log_container(message: Message, container_name: str) -> None:
        """
        Получаем логи выбранного в боте контейнера.
        :param message: Данные о пользователе.
        :param container_name: Наименование контейнера.
        :return:
        """
        logs: bytes = client.containers.get(container_name).logs(tail=10)
        lines: list = logs.decode('utf-8').split("\n")
        last_lines: str = "\n".join(lines)
        bot.reply_to(message, f'Логи контейнера {container_name}:\n{last_lines}')


@bot.message_handler(commands=['start'])
def start_bot(message: Message) -> None:
    first_mess: str = f"<b>{message.from_user.first_name} {message.from_user.last_name}</b>, " \
                      f"привет!\nЗдесь представлены на выбор проверка сервисов."
    markup: types.ReplyKeyboardMarkup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons: list = [types.KeyboardButton(text=button_text) for button_text in BUTTONS_TELEGRAM_BOT]
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.add(buttons[i], buttons[i + 1])
        else:
            markup.add(buttons[i])
    bot.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)


@bot.message_handler(content_types=['text'])
def bot_message(message: Message) -> None:
    telegram_bot_manager: TelegramBotManager = TelegramBotManager(message)
    if method_name := BUTTONS_TELEGRAM_BOT.get(message.text):
        getattr(telegram_bot_manager, method_name)()


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call: types.CallbackQuery) -> Optional[types.InlineKeyboardMarkup]:
    if call.data == 'get_logs_docker':
        markup: types.InlineKeyboardMarkup = types.InlineKeyboardMarkup()
        for container in [container.name for container in client.containers.list()]:
            markup.add(types.InlineKeyboardButton(container, callback_data=f'get_log_container_{container}'))
        markup.add(types.InlineKeyboardButton('Закрыть меню', callback_data='close'))
        return markup
    elif call.data == 'close':
        bot.edit_message_text('Меню закрыто', call.message.chat.id, call.message.message_id)
    elif call.data.startswith('get_log_container'):
        TelegramBotManager.get_log_container(call.message, call.data[len('get_log_container_'):])


if __name__ == "__main__":
    bot.infinity_polling()
