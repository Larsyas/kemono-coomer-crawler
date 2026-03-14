import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_THREADS = 10
MAX_RETRIES = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/css"
}

session = requests.Session()
session.headers.update(HEADERS)

VIDEO_EXT = (".mp4", ".mkv", ".webm", ".mov", ".hevc")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")


def sanitize_filename(name):
    name = name.strip()
    return re.sub(r'[\\/*?:"<>|]', "", name)


def choose_source():
    print("Escolha a fonte:")
    print("1 - Kemono")
    print("2 - Coomer")

    option = input("Opção: ").strip()

    if option == "1":
        return "kemono.cr"
    elif option == "2":
        return "coomer.st"
    else:
        print("Opção inválida.")
        exit()


def detect_extension(filepath):

    with open(filepath, "rb") as f:
        header = f.read(64)

    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"

    if header.startswith(b"\x89PNG"):
        return ".png"

    if header.startswith(b"GIF"):
        return ".gif"

    if header.startswith(b"RIFF") and b"WEBP" in header:
        return ".webp"

    if b"ftyp" in header:
        return ".mp4"

    if header.startswith(b"PK"):
        return ".zip"

    return None


def fetch_creators(domain):

    print("\nBaixando lista de criadores...")

    url = f"https://{domain}/api/v1/creators"

    r = session.get(url, timeout=30)

    if r.status_code != 200:
        print("Erro ao baixar creators:", r.status_code)
        exit()

    creators = r.json()

    print(f"Creators carregados: {len(creators)}")

    return creators


def find_creator(creators, name):

    name = name.lower().strip()

    for creator in creators:

        creator_name = str(creator.get("name", "")).lower().strip()

        if name in creator_name:
            return (
                creator["service"],
                creator["id"],
                creator["name"].strip()
            )

    return None, None, None


def fetch_posts(domain, service, creator_id):

    posts = []
    offset = 0

    print("\nBuscando posts...")

    while True:

        url = f"https://{domain}/api/v1/{service}/user/{creator_id}/posts?o={offset}"

        r = session.get(url, timeout=30)

        if r.status_code != 200:
            break

        data = r.json()

        if not data:
            break

        posts.extend(data)
        offset += 50

        print(f"Posts coletados: {len(posts)}")

    return posts


def collect_files(posts, domain):

    files = []

    for post in posts:

        if post.get("file"):
            path = post["file"]["path"]
            files.append(f"https://{domain}/data{path}")

        if post.get("attachments"):
            for att in post["attachments"]:
                path = att["path"]
                files.append(f"https://{domain}/data{path}")

    return files


def download_file(url, folder):

    filename = url.split("/")[-1]
    filepath = os.path.join(folder, filename)

    if os.path.exists(filepath):
        return

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            r = session.get(url, stream=True, timeout=(10, 120))

            if r.status_code != 200:
                raise Exception(f"HTTP {r.status_code}")

            with open(filepath, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            # detectar extensão real
            ext_detected = detect_extension(filepath)

            if ext_detected:

                name, old_ext = os.path.splitext(filepath)

                if old_ext.lower() != ext_detected:

                    new_path = name + ext_detected

                    if not os.path.exists(new_path):
                        try:
                            os.rename(filepath, new_path)
                            filepath = new_path
                        except OSError:
                            pass

            print("Baixado:", os.path.basename(filepath))
            return

        except Exception as e:

            print(f"Erro tentativa {attempt}: {e}")

            if attempt < MAX_RETRIES:
                wait = attempt * 2
                print(f"Tentando novamente em {wait}s...")
                time.sleep(wait)
            else:
                print("Falha definitiva:", url)


def worker(url):

    lower = url.lower()

    if lower.endswith(VIDEO_EXT):
        download_file(url, VIDEOS_DIR)

    elif lower.endswith(IMAGE_EXT):
        download_file(url, IMAGES_DIR)

    else:
        download_file(url, FILES_DIR)


def download_all(files):

    print("\nArquivos encontrados:", len(files))
    print("Iniciando downloads...\n")

    with ThreadPoolExecutor(MAX_THREADS) as executor:

        futures = [executor.submit(worker, url) for url in files]

        for future in as_completed(futures):
            future.result()


# ============================
# EXECUÇÃO
# ============================

domain = choose_source()

creator_input = input("\nDigite o nome do criador: ").strip()

creators = fetch_creators(domain)

service, creator_id, creator_name = find_creator(creators, creator_input)

if not creator_id:
    print("Criador não encontrado.")
    exit()

print("\nCreator encontrado:")
print("Nome:", creator_name)
print("Service:", service)
print("ID:", creator_id)

creator_name = sanitize_filename(creator_name)

BASE_DIR = os.path.join("downloads", creator_name)

VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
FILES_DIR = os.path.join(BASE_DIR, "files")

os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)

posts = fetch_posts(domain, service, creator_id)

files = collect_files(posts, domain)

download_all(files)

print("\nDownload finalizado.")