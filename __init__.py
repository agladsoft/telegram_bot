import os
from logging import FileHandler, Formatter, INFO, getLogger

# telegram
TOKEN_TELEGRAM: str = "6557326533:AAHy6ls9LhTVTGztix8PUSK7BUSaHVEojXc"

# database
IP_ADDRESS_DB: str = "10.23.4.196"

# yandex
USER_XML_RIVER: str = "6390"
KEY_XML_RIVER: str = "e3b3ac2908b2a9e729f1671218c85e12cfe643b0"

# dadata
ACCOUNTS_SERVICE_INN: dict = {
    "3321a7103852f488c92dbbd926b2e554ad63fb49": "3c905f3b5b6291c65d323e3b774e7b8f6d1b7919",
    "baf71b4b95c986ce9148c24f5aa251d94cd9d850": "4d715bf363c1388d3f545bb37a019c7ce2c9c784"
}

# logging
LOG_FTM: str = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
DATE_FTM: str = "%d/%B/%Y %H:%M:%S"


def get_my_env_var(var_name: str) -> str:
    try:
        return os.environ[var_name]
    except KeyError as e:
        raise MissingEnvironmentVariable(f"{var_name} does not exist") from e


def get_file_handler(name: str) -> FileHandler:
    log_dir_name: str = "logging"
    if not os.path.exists(log_dir_name):
        os.mkdir(log_dir_name)
    file_handler: FileHandler = FileHandler(f"{log_dir_name}/{name}.log")
    file_handler.setFormatter(Formatter(LOG_FTM, datefmt=DATE_FTM))
    return file_handler


def get_logger(name: str) -> getLogger:
    logger: getLogger = getLogger(name)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(get_file_handler(name))
    logger.setLevel(INFO)
    return logger


class MissingEnvironmentVariable(Exception):
    pass
