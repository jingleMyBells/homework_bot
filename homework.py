import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from exceptions import NoEnvVar

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

BOT = telegram.Bot(token=TELEGRAM_TOKEN)


def send_message(bot, message):
    """Отправка любых сообщений из остальных функций."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.info('Отправлено сообщение в телеграм')


def get_api_answer(current_timestamp):
    """Запрос к API на предмет изменений статусов с заданной даты."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        error = 'Запрос к эндпоинту вернул не HTTP 200'
        logging.error(error)
        send_message(BOT, error)
    elif response.status_code == 200:
        logging.info('Запрос к эндпоинту вернул HTTP 200')
        return response.json()
    return None


def check_response(response):
    """Проверка ответа API на соответствие ожиданиям."""
    print(f'check_response: response = {response}')
    if type(response) is not dict:
        raise TypeError('API отетил не словарем')
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
        send_message(BOT, error)
    if len(homeworks) == 0:
        logging.debug('Нет изменений статусов домашек')

    return homeworks


def parse_status(homework):
    """Распаковка информации по конкретной домашке."""
    if homework:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status:
            verdict = HOMEWORK_STATUSES[homework_status] or None
        if verdict:
            logging.info(f'Статус домашки {homework_status} обнаружен')
        else:
            error = (f'Статус домашки "{homework_status}" '
                     f'не соответствует ожидаемому')
            logging.error(error)
            send_message(BOT, error)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise TypeError('Заглушил')


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
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response:
                homeworks = check_response(response)
                if homeworks:
                    for homework in homeworks:
                        status = parse_status(homework)
                        send_message(BOT, status)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(BOT, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
