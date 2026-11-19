import json
import logging
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

# Папка на Я.Диске называется так же, как группа в Нетологии
GROUP_NAME = 'AIEPYAPI-160'
CATAAS_URL = 'https://cataas.com/cat/says/'
RESULT_FILE = 'result.json'


class YandexDisk:
    base_url = 'https://cloud-api.yandex.net/v1/disk/resources'

    def __init__(self, token):
        self.headers = {'Authorization': f'OAuth {token}'}

    def create_folder(self, folder_name):
        response = requests.put(self.base_url,
                                headers=self.headers,
                                params={'path': folder_name})
        if response.status_code == 201:
            logging.info(f'Папка "{folder_name}" создана')
        elif response.status_code == 409:
            logging.info(f'Папка "{folder_name}" уже есть на диске')
        else:
            response.raise_for_status()

    def upload_from_url(self, file_url, path):
        """Загрузка файла на диск по ссылке, без сохранения на компьютер"""
        response = requests.post(f'{self.base_url}/upload',
                                 headers=self.headers,
                                 params={'path': path, 'url': file_url})
        if response.status_code == 409:
            raise Exception(f'Файл "{path}" уже есть на диске')
        response.raise_for_status()
        return response.json()['href']

    def wait_for_upload(self, operation_url):
        # Я.Диск качает файл сам, поэтому ждём, пока операция завершится
        for _ in range(30):
            response = requests.get(operation_url, headers=self.headers)
            response.raise_for_status()
            status = response.json()['status']
            if status == 'success':
                return
            if status == 'failed':
                raise Exception('Я.Диск не смог загрузить картинку')
            logging.info('Загрузка ещё идёт...')
            time.sleep(1)
        raise Exception('Загрузка идёт слишком долго')

    def get_file_size(self, path):
        response = requests.get(self.base_url,
                                headers=self.headers,
                                params={'path': path})
        response.raise_for_status()
        return response.json()['size']


def get_cat(text):
    """Возвращает ссылку на картинку кота с текстом и её расширение"""
    url = CATAAS_URL + requests.utils.quote(text, safe='')
    response = requests.get(url, params={'json': 'true'})
    response.raise_for_status()
    cat = response.json()
    extension = cat['mimetype'].split('/')[1]
    return cat['url'], extension


def save_result(file_name, size):
    result = [{'file_name': file_name, 'size': size}]
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    logging.info(f'Информация о файле сохранена в {RESULT_FILE}')


def main():
    text = input('Введите текст для картинки: ').strip()
    if not text:
        print('Текст не может быть пустым')
        return
    token = input('Введите токен с Полигона Я.Диска: ').strip()

    disk = YandexDisk(token)
    disk.create_folder(GROUP_NAME)

    logging.info('Получаем картинку с котом...')
    cat_url, extension = get_cat(text)

    # слэш в имени файла Я.Диск воспримет как папку, поэтому заменяем
    file_name = f'{text.replace("/", "_")}.{extension}'
    path = f'{GROUP_NAME}/{file_name}'

    logging.info(f'Загружаем "{file_name}" на Я.Диск...')
    operation_url = disk.upload_from_url(cat_url, path)
    disk.wait_for_upload(operation_url)

    size = disk.get_file_size(path)
    logging.info(f'Готово! Размер файла: {size} байт')

    save_result(file_name, size)


if __name__ == '__main__':
    main()
