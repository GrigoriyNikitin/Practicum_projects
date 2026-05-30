import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from rest_framework.exceptions import APIException
from telebot import TeleBot

from exceptions import (ExceedCountHomeworkException, NotNecessaryKeyException,
                        ResponseStructureException, ResponseTypeException,
                        SendTelegramMessageException,
                        ServerAvailabilityException, VarAvailabilityException)         

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
EVALUATION_PERIOD_IN_SECONDS = RETRY_PERIOD
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
LEN_RESPONSE_TEXT = 300


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger('my_logger')
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Функция для проверки доступности переменных окружения.

    Если отсутствует хотя бы одна переменная окружения, необходимая
    для работы программы, продолжать работу бота нет смысла.
    """
    if PRACTICUM_TOKEN is None:
        raise VarAvailabilityException(
            'Отсутствует обязательная переменная окружения: PRACTICUM_TOKEN.')
    # Вариант с циклом и словарём я хотел использовать изначально,
    # но тесты не пропустили такой вариант (могу это "МОЖНО ЛУЧШЕ"):(
    if TELEGRAM_TOKEN is None:
        raise VarAvailabilityException(
            'Отсутствует обязательная переменная окружения: TELEGRAM_TOKEN.')
    if TELEGRAM_CHAT_ID is None:
        raise VarAvailabilityException(
            'Отсутствует обязательная переменная окружения: TELEGRAM_CHAT_ID.')


def send_message(bot, message):
    """Функция для отправки сообщения в Telegram-чат.

    Функция принимает на вход два параметра:
    - экземпляр класса TeleBot;
    - строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except (APIException, requests.RequestException) as err:
        raise SendTelegramMessageException(
            f'Ошибка при отправке сообщения в Telegram: {err}') from err
    logger.debug(f'В Telegram отправлено следущее сообщение: {message}')
    return True


def get_api_answer(timestamp):
    """Функция делает запрос к единственному эндпоинту API-сервиса.

    В качестве параметра в функцию передаётся временная метка.
    В случае успешного запроса должна вернуть ответ API,
    приведя его из формата JSON к типам данных Python.
    """
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
    except requests.RequestException as err:
        raise ResponseTypeException(
            f'Сбой при запросе к эндпоинту (не связанный '
            f'с его доступностью) {err}') from err
    else:
        type_homework_statuses = type(homework_statuses.text)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise ServerAvailabilityException(
                f'Ответ от сервера не получен! Адрес запроса: {ENDPOINT}, '
                f'параметры запроса: headers - {HEADERS}, from_date - '
                f'{timestamp}. Код ошибки: {homework_statuses.status_code}. '
                f'Тело ответа: {homework_statuses.text[:LEN_RESPONSE_TEXT]}')
        if not isinstance(homework_statuses.text, str):
            raise ResponseTypeException(
                f'Ответ сервера не соответствует ожидаемому формату (JSON)! '
                f'Фактический формат ответа: {type_homework_statuses}!')
    return homework_statuses.json()


def check_response(response_content):
    """Функция проверяет ответ API на соответствие документации.

    В качестве параметра функция получает ответ API,
    приведённый к типам данных Python.
    """
    type_response_content = type(response_content)
    if not isinstance(response_content, dict):
        raise TypeError(
            f'Информация в ответе на запрос не соответствует ожидаемому типу!'
            f' Фактический тип инофрмации ответа: {type_response_content},'
            f' ожидаемый: <class dict>.')
    if 'homeworks' not in list(response_content.keys()):
        raise NotNecessaryKeyException(
            'В ответе API отсутствует необходимый ключ "homeworks"')
    homeworks = response_content.get('homeworks')
    type_homeworks = type(homeworks)
    lenght_homeworks = len(homeworks)
    if not isinstance(homeworks, list):
        raise TypeError(
            f'Информация в ответе на запрос не соответствует ожидаемому типу!'
            f' Фактический тип информации в словаре под ключом "homeworks": '
            f'{type_homeworks}, ожидаемый: <class list>.')
    if len(response_content.get('homeworks')) > 1:
        raise ExceedCountHomeworkException(
            f'Фактическое число домашних работ, о которых приведена информация'
            f' в ответе API: {lenght_homeworks}, ожидаемое число: 1')


def parse_status(homework):
    """Функция извлекает статус домашней работы.

    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха функция возвращает подготовленную
    для отправки в Telegram строку.
    """
    test_keys = ('status', 'homework_name')
    for key in test_keys:
        if key not in list(homework.keys()):
            raise NotNecessaryKeyException(
                f'В ответе API отсутствуют ожидаемые ключи '
                f'(в частности ключ <{key}>)!')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    list_of_keys_HOMEWORK_VERDICTS = list(HOMEWORK_VERDICTS.keys())
    if verdict is None:
        raise ResponseStructureException(
            f'Неожиданный статус домашней работы: {status}. '
            f'Ожидался один из следующий статусов: '
            f'{list_of_keys_HOMEWORK_VERDICTS}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    sending_message = ''

    try:
        check_tokens()
    except VarAvailabilityException as error:
        logger.critical(error)
        message = (f'Сбой в работе программы: {error}.'
                   f'Программа принудительно остановлена!')
        send_message(bot, message)
        sys.exit()

    while True:
        try:
            response_content = get_api_answer(timestamp)
            check_response(response_content)
            homeworks = response_content.get('homeworks')
            if not len(homeworks):
                message = None
                logger.debug('Статус домашней работы не обновился')
                continue
            homework = homeworks[0]
            message = parse_status(homework)
            send_message(bot, message)
            timestamp = homework.get('current_date', timestamp)
        except Exception as err:
            message = f'Сбой в работе программы: {err}'
            logger.exception(err)
            if sending_message != message:
                if send_message(bot, message):
                    sending_message = message
        finally:
            time.sleep(EVALUATION_PERIOD_IN_SECONDS)


if __name__ == '__main__':
    main()
