from playwright.sync_api import sync_playwright, Page
from time import sleep
import json
import re
import math
import os


site_list = {
    'coomer': 'https://coomer.st/artists',
    'kemono': 'https://kemono.cr/artists',
    'coomer_raw': 'https://coomer.st',
    'kemono_raw': 'https://kemono.cr'
}


website_base_url = None

# Escolhe site
while website_base_url not in ['0', '1']:

    website_base_url = input('which website? (0 = coomer, 1 = kemono) ')

    if website_base_url == '0':
        website_base_url = site_list['coomer']
        break

    elif website_base_url == '1':
        website_base_url = site_list['kemono']
        break

    else:
        print('invalid option')


user = input('who? ')

USER_DIR = f"downloads/{user}"
os.makedirs(USER_DIR, exist_ok=True)


def build_page_numbered_url(base_url, page_number):

    if page_number == 1:
        return base_url

    offset = (page_number - 1) * 50
    return f"{base_url}?o={offset}"


def progress_bar(current, total, bar_length=30):

    progress = current / total
    filled = int(bar_length * progress)

    bar = "█" * filled + "░" * (bar_length - filled)

    print(f"\r[{bar}] {current}/{total} posts", end="")


def download_loop(page_content: Page, page_posts):

    user_post_links = []

    total_posts_page = len(page_posts)

    for index, j in enumerate(page_posts, start=1):

        progress_bar(index, total_posts_page)

        post_url = website_base_url + j['href']

        print(f"\nOpening post {index}/{total_posts_page}: {post_url}")

        page_content.goto(post_url)
        page_content.wait_for_load_state('domcontentloaded')
        sleep(1)

        try:

            # ---------------------------------------
            # EXTRAI ID DO POST PARA CRIAR DIRETÓRIOS
            # ---------------------------------------

            post_id = post_url.split("/")[-1]

            post_dir = os.path.join(USER_DIR, post_id)
            images_dir = os.path.join(post_dir, "images")
            videos_dir = os.path.join(post_dir, "videos")

            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(videos_dir, exist_ok=True)


            # ---------------------------------------
            # DETECTA VIDEOS
            # ---------------------------------------

            video_locator = page_content.locator("video source")
            video_count = video_locator.count()

            # fallback caso source não exista
            if video_count == 0:
                video_locator = page_content.locator("video")
                video_count = video_locator.count()

            print(f"{video_count} videos found")


            # ---------------------------------------
            # BAIXA VIDEOS SE EXISTIREM
            # ---------------------------------------

            for v in range(video_count):

                video_url = video_locator.nth(v).get_attribute("src")

                if not video_url:
                    continue

                filename = video_url.split("/")[-1].split("?")[0]
                file_path = os.path.join(videos_dir, filename)

                if os.path.exists(file_path):
                    print("video already downloaded:", filename)
                    continue

                print("downloading video:", filename)

                try:

                    response = page_content.request.get(video_url, timeout=60000)

                    with open(file_path, "wb") as f:
                        f.write(response.body())

                except Exception as video_error:
                    print("video download failed:", video_error)


            # ---------------------------------------
            # DETECTA IMAGENS
            # ---------------------------------------

            page_content.wait_for_selector('.post__thumbnail figure a', timeout=5000)

            post_img_files_locator = page_content.locator('.post__thumbnail figure a')
            img_count = post_img_files_locator.count()

            print(f"{img_count} images found")


            # ---------------------------------------
            # BAIXA IMAGENS SE EXISTIREM
            # ---------------------------------------

            for img in range(img_count):

                actual_img_tbd = post_img_files_locator.nth(img)
                img_url = actual_img_tbd.get_attribute('href')

                if not img_url:
                    continue

                filename = img_url.split("/")[-1].split("?")[0]
                file_path = os.path.join(images_dir, filename)

                if os.path.exists(file_path):
                    print("already downloaded:", filename)
                    continue

                print("downloading:", filename)

                try:

                    response = page_content.request.get(img_url, timeout=30000)

                    with open(file_path, "wb") as f:
                        f.write(response.body())

                except Exception as img_error:

                    print("download failed:", img_error)
                    continue


            user_post_links.append({
                'imgs': img_count,
                'videos': video_count,
                'post_url': post_url
            })

        except Exception as e:

            print("error reading post:", e)


        # salva lista de posts analisados
        with open('lista.json', 'w', encoding='utf-8') as f:
            json.dump(user_post_links, f, indent=4, ensure_ascii=False)



with sync_playwright() as pw:

    nav = pw.chromium.launch(headless=False)

    page = nav.new_page()

    page.goto(url=website_base_url, timeout=100000)


    if website_base_url == site_list['coomer']:
        website_base_url = site_list['coomer_raw']
    else:
        website_base_url = site_list['kemono_raw']


    page.get_by_placeholder('Search...').fill(user)

    sleep(3)

    user_profile = page.get_by_text(user).first

    if user_profile:

        user_profile.click()
        page.wait_for_url("**/user/**")

    else:

        print(f"Couldn't find {user}")
        nav.close()
        exit()


    sleep(2)

    user_profile_url = page.url.split("?")[0]

    print("Profile URL:", user_profile_url)


    small_locator = page.locator('#paginator-top small')
    has_page_info = small_locator.count() > 0


    if has_page_info:

        user_posts_data_raw = small_locator.inner_text()

        user_posts_num = int(re.findall(r'\d+', user_posts_data_raw)[-1])

        print(f'{user} has {user_posts_num} posts')

        num_user_pages = math.ceil(user_posts_num / 50)

        print(f'{num_user_pages} pages total')

    else:

        print('no paginator found')

        num_user_pages = 1


    for p in range(1, num_user_pages + 1):

        page_url = build_page_numbered_url(user_profile_url, p)

        print("\n====================")
        print("Page", p, "of", num_user_pages)
        print(page_url)

        page.goto(page_url)
        page.wait_for_load_state('domcontentloaded')

        sleep(2)

        page_posts = []

        page_posts_tags_locator = page.locator('.card-list__items article a')
        page_post_count = page_posts_tags_locator.count()

        print(page_post_count, "posts on this page")

        for i in range(page_post_count):

            actual_post_tbd = page_posts_tags_locator.nth(i)

            post_title = actual_post_tbd.locator('header').inner_text()

            page_posts.append({
                "title": post_title,
                "href": actual_post_tbd.get_attribute('href')
            })


        download_loop(page, page_posts)

    print("\n\nFinished.")

    sleep(10)

    nav.close()