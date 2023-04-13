import requests

import os
import logging

import time

import telegram

from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='log.log',
    filemode='w',
    encoding='utf-8',
)


def check_tokens():
    """Функция проверки переменных окружения."""
    """Если хотя бы одна переменная отсутствует,
    выдаст ошибку."""
    if (PRACTICUM_TOKEN is None or
            TELEGRAM_TOKEN is None or
            TELEGRAM_CHAT_ID is None):
        logging.critical('Один из токенов или несколько не определены')
        raise Exception('Один из токенов или несколько не определены')
    else:
        return True


def send_message(bot, message):
    """Функция отправки сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение успешно отправлено')
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(timestamp):
    """Функция запроса к API Яндекс.Практикум."""
    """Отправляет запрос к единственному эндпоинту.
    При успешном ответе возвращает статусы домашней работы."""
    payload = {
        'from_date': timestamp
    }
    try:
        homework_statuses = requests.get(
                                        ENDPOINT,
                                        headers=HEADERS,
                                        params=payload
                                        )
        if homework_statuses.status_code != 200:
            raise Exception(f'Сервер вернул ответ с кодом, отличным'
                            f' от 200: {homework_statuses.status_code}')
        return homework_statuses.json()
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к API Яндекс.Практикум: {error}')


def check_response(response):
    """Функция проверки соответствия ответа документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ сервера приходит не в виде словаря')
    if 'homeworks' not in response:
        raise exceptions.EmptyResponseError('Ответ сервера'
                                            ' не содержит ключ homeworks')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Значение с ключом homeworks не является списком')
    return homeworks


def parse_status(homework):
    """Функция проверки статуса домашки."""
    if 'homework_name' not in homework:
        raise KeyError('Ответ сервера не содержит ключ homework_name')
    homework_name = homework['homework_name']
    verdict = homework['status']
    if verdict not in HOMEWORK_VERDICTS:
        raise ValueError(f'Сервер передал некорректный'
                         f' или пустой статус: {verdict}')
    return (
        f'Изменился статус проверки работы "{homework_name}".'
        f' {HOMEWORK_VERDICTS[verdict]}'
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        SystemExit
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = ''
    while True:
        try:
            response = get_api_answer(timestamp=timestamp)
            homeworks = check_response(response)
            if homeworks:
                current_status = parse_status(homeworks[0])
            else:
                current_status = 'Статус отсутствует'
            if current_status != last_status:
                send_message(bot, current_status)
                logging.DEBUG(f'Сообщение успешно отправлено:'
                              f' {current_status}')
                last_status = current_status

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
