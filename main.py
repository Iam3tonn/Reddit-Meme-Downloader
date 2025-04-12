import requests
import os
import random
import hashlib
import concurrent.futures
from PIL import Image

# 🔧 Настройки
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

SUBREDDITS = ["memes", "dankmemes", "funny", "wholesomememes", "PrequelMemes", "terriblefacebookmemes", 
              "cars", "carporn", "Shitty_Car_Mods", "CarMemes"]  # Авто, мемные сабреддиты

BASE_FOLDER = "Memes"
HASHES_FILE = "downloaded_hashes.txt"


def get_memes(query, limit=5, min_upvotes=100):
    """Ищет мемы по запросу (если не находит, берет горячие посты)"""
    all_images = []

    for subreddit in SUBREDDITS:
        print(f"🔍 Поиск мемов в сабреддите: {subreddit}")

        # 1️⃣ Сначала пробуем поиск по запросу
        search_url = f"https://www.reddit.com/r/{subreddit}/search.json?q={query}&restrict_sr=1&sort=relevance"
        response = requests.get(search_url, headers=HEADERS, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                title = post["data"].get("title", "").lower()
                upvotes = post["data"].get("ups", 0)
                image_url = post["data"].get("url")

                # Фильтруем по ключевому слову в заголовке
                if query.lower() in title and image_url and (".jpg" in image_url or ".png" in image_url or ".jpeg" in image_url):
                    if upvotes >= min_upvotes:
                        all_images.append(image_url)
                        if len(all_images) >= limit:
                            return all_images  # Достаточно мемов, выходим

        # 2️⃣ Если ничего не нашли, пробуем просто топовые посты
        hot_url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
        response = requests.get(hot_url, headers=HEADERS, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                upvotes = post["data"].get("ups", 0)
                image_url = post["data"].get("url")

                if image_url and (".jpg" in image_url or ".png" in image_url):
                    if upvotes >= min_upvotes:
                        all_images.append(image_url)
                        if len(all_images) >= limit:
                            return all_images  # Достаточно мемов, выходим

    return all_images


def get_image_hash(image_data):
    """Создает хеш изображения для проверки дубликатов"""
    return hashlib.md5(image_data).hexdigest()


def load_existing_hashes():
    """Загружает хеши уже скачанных мемов"""
    if not os.path.exists(HASHES_FILE):
        return set()
    with open(HASHES_FILE, "r") as f:
        return set(f.read().splitlines())


def save_new_hash(image_hash):
    """Сохраняет новый хеш в файл"""
    with open(HASHES_FILE, "a") as f:
        f.write(image_hash + "\n")


def save_image(img_url, category):
    """Скачивает и сохраняет изображение в нужную папку"""
    category_folder = os.path.join(BASE_FOLDER, category.capitalize())  # Папка с категорией
    os.makedirs(category_folder, exist_ok=True)  # Создаем папку, если её нет

    img_data = requests.get(img_url).content
    img_hash = get_image_hash(img_data)

    # Проверяем, не скачивали ли мы уже этот мем
    existing_hashes = load_existing_hashes()
    if img_hash in existing_hashes:
        print(f"⚠️ Дубликат найден, пропускаем {img_url}")
        return None

    # Генерируем имя файла
    file_name = os.path.join(category_folder, f"meme_{random.randint(1000, 9999)}.jpg")
    with open(file_name, "wb") as f:
        f.write(img_data)

    save_new_hash(img_hash)  # Сохраняем хеш нового изображения
    print(f"✅ Мем сохранен: {file_name}")
    return file_name


def save_images_multithread(image_urls, category):
    """Скачивает изображения в несколько потоков"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(save_image, img_url, category) for img_url in image_urls]
        saved_files = [f.result() for f in concurrent.futures.as_completed(futures)]
    return [file for file in saved_files if file]


def open_images(files):
    """Автооткрытие изображений"""
    for file in files:
        if file:
            img = Image.open(file)
            img.show()


# 🔥 Запуск
search_query = input("Введите тему для поиска мемов: ")
meme_count = int(input("Сколько мемов скачать? (по умолчанию 5): ") or 5)

memes = get_memes(search_query, limit=meme_count)

if memes:
    saved_files = save_images_multithread(memes, search_query)
    open_images(saved_files)  # Автооткрытие мемов
else:
    print("🚫 Мемов по запросу не найдено во всех сабреддитах.")
