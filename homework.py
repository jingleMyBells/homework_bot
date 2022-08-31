import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from exceptions import NoEnvVar
from hw_settings import ENDPOINT, HEADERS, HOMEWORK_STATUSES, RETRY_TIME

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT')


def send_message(bot, message):
    """Отправка любых сообщений из остальных функций."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info('Отправлено сообщение в телеграм')
    except Exception as error:
        logging.error(error)


def get_api_answer(current_timestamp):
    """Запрос к API на предмет изменений статусов с заданной даты."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            error = 'Запрос к эндпоинту вернул не HTTP 200'
            logging.error(error)
            send_message(bot, error)
        elif response.status_code == HTTPStatus.OK:
            logging.info('Запрос к эндпоинту вернул HTTP 200')
            return response.json()
        return None
    except requests.exceptions.HTTPError:
        error = 'HTTP Error'
        logging.error(error)
        send_message(bot, error)
        return None
    except requests.exceptions.ConnectionError:
        error = 'Connection Error'
        logging.error(error)
        send_message(bot, error)
        return None
    except json.decoder.JSONDecodeError:
        error = 'Invalid JSON'
        logging.error(error)
        send_message(bot, error)
        return None


def check_response(response):
    """Проверка ответа API на соответствие ожиданиям."""
    if response:
        if type(response) is not dict:
            raise TypeError('API ответил не словарем')
        curr_date = response.get('current_date')
        homeworks = response.get('homeworks')
        if type(homeworks) is not list:
            raise TypeError('API вернул домашки не списком')
        if curr_date:
            logging.info('Ответ API содержит ожидаемые поля')
        else:
            error = (
                f'API вернул неожиданное содержимое поля: '
                f'current_date = {curr_date}'
            )
            logging.error(error)
            send_message(bot, error)
        if len(homeworks) == 0:
            logging.debug('Нет изменений статусов домашек')

        return homeworks
    else:
        raise TypeError('None вместо ответа API')


def parse_status(homework):
    """Распаковка информации по конкретной домашке."""
    if homework:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status:
            verdict = HOMEWORK_STATUSES[homework_status]
        if verdict:
            logging.info(f'Статус домашки {homework_status} обнаружен')
        else:
            error = (f'Статус домашки "{homework_status}" '
                     f'не соответствует ожидаемому')
            logging.error(error)
            send_message(bot, error)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise TypeError('None вместо конкретной домашки')


def check_tokens():
    """Проверка наличия всех переменных окружения."""
    env_vars = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for env_var in env_vars.keys():
        if env_vars[env_var] is None:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: '
                f'{env_var}'
            )
            return False
    logging.info('Все переменные окружения обнаружены')
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        raise NoEnvVar('Нет переменных окружения')
    global bot
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response:
                homeworks = check_response(response)
                if homeworks:
                    for homework in homeworks:
                        status = parse_status(homework)
                        send_message(bot, status)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
