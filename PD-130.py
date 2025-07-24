# Импорт библиотек
import requests
import json
from urllib.parse import urlparse
import os
from tqdm import tqdm
import time
import configparser

# Чтение конфигурации
config = configparser.ConfigParser()
config.read('settings.ini')

# Настройки
try:
    YANDEX_TOKEN = config['tokens']['yd_token']
except KeyError:
    print("Ошибка: Не найден токен в файле settings.ini")
    exit(1)

BREED = "spaniel"
YA_DISK_FOLDER = "/PD-130"


class YandexDiskUploader:
    def __init__(self, token):
        self.base_url = "https://cloud-api.yandex.net/v1/disk/resources"
        self.headers = {"Authorization": f"OAuth {token}"}
        self.upload_timeout = 30

    def create_folder(self, path):
        response = requests.put(
            self.base_url,
            headers=self.headers,
            params={"path": path}
        )
        return response.status_code in (201, 409)

    def upload_from_url(self, url, save_path):
        # 1. Запрашиваем URL для загрузки
        upload_response = requests.post(
            f"{self.base_url}/upload",
            headers=self.headers,
            params={
                "url": url,
                "path": save_path,
                "disable_redirects": True
            }
        )

        if upload_response.status_code != 202:
            print(f"Ошибка начала загрузки: {upload_response.status_code}")
            return False

        # 2. Проверяем статус загрузки
        start_time = time.time()
        while time.time() - start_time < self.upload_timeout:
            status_response = requests.get(
                upload_response.json().get("href", ""),
                headers=self.headers
            )

            if status_response.status_code == 200:
                status = status_response.json().get("status")
                if status == "success":
                    return True
                elif status == "failed":
                    print(f"Ошибка загрузки: {status_response.json().get('error')}")
                    return False

            time.sleep(1)  # Проверяем статус каждую секунду

        print("Таймаут загрузки")
        return False


def get_dog_images(breed, sub_breed=None):
    base_url = "https://dog.ceo/api/breed"
    if sub_breed:
        url = f"{base_url}/{breed}/{sub_breed}/images"
    else:
        url = f"{base_url}/{breed}/images"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("message", [])
    except Exception as e:
        print(f"Ошибка получения изображений: {e}")
        return []

def main():
    print(f"Используемый токен: Ваш токен для яндекс диска")

    yandex = YandexDiskUploader(YANDEX_TOKEN)

    # Создаем папки
    if not yandex.create_folder(YA_DISK_FOLDER):
        print("Не удалось создать папку PD-130!")
        return

    breed_folder = f"{YA_DISK_FOLDER}/{BREED}"
    if not yandex.create_folder(breed_folder):
        print(f"Не удалось создать {breed_folder}!")
        return

    # Получаем данные
    try:
        sub_breeds = requests.get(
            f"https://dog.ceo/api/breed/{BREED}/list",
            timeout=10
        ).json().get("message", [])
    except Exception as e:
        print(f"Ошибка получения подпород: {e}")
        sub_breeds = []

    results = {"uploaded": [], "failed": []}

    # Обрабатываем подпороды
    for sub_breed in tqdm(sub_breeds, desc="Загрузка"):
        images = get_dog_images(BREED, sub_breed)
        if not images:
            continue

        img_url = images[0]
        filename = f"{sub_breed}_{os.path.basename(urlparse(img_url).path)}"
        save_path = f"{breed_folder}/{filename}"

        if yandex.upload_from_url(img_url, save_path):
            results["uploaded"].append(filename)
        else:
            results["failed"].append(filename)

    # Сохраняем отчет
    with open("upload_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nРезультаты:")
    print(f"Успешно: {len(results['uploaded'])}")
    print(f"Ошибки: {len(results['failed'])}")
    print(f"Папка: https://disk.yandex.ru/client/disk{YA_DISK_FOLDER}")


if __name__ == "__main__":
    main()




