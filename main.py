from playwright.sync_api import sync_playwright, Page
from time import sleep
import json
import re
import math
import os


user = input('who? ')

USER_DIR = f"downloads/{user}"
os.makedirs(USER_DIR, exist_ok=True)


def get_paginator_status(page: Page):

    sleep(1)
    page.wait_for_selector('#paginator-top menu a')

    paginator_items = page.locator('#paginator-top menu a')
    count = paginator_items.count()

    user_pages = []

    for i in range(count):
        paginator_locator = paginator_items.nth(i)

        text = paginator_locator.inner_text().strip()
        href = paginator_locator.get_attribute("href")

        if text.isdigit():
            user_pages.append({
                "text": int(text),
                "href": href,
                "locator": paginator_locator
            })

    return user_pages


def download_loop(page: Page):
    page_posts = []

    page_posts_tags_locator = page.locator('.card-list__items article a')

    page_post_count = page_posts_tags_locator.count()
    print(page_post_count)

    for i in range(page_post_count):
        actual_post_tbd = page_posts_tags_locator.nth(i)
        post_title = actual_post_tbd.locator('header').inner_text()
        

        page_posts.append({
            "title": post_title,
            "href": actual_post_tbd.get_attribute('href'),
            "locator": actual_post_tbd
        })


    # GET POSTS LIST
    #######################
    # PROCEED
    user_url = page.url
    user_post_links = []

    x = 1
    for j in page_posts:
        # OPENS POST[j]

        j['locator'].click()
        page.wait_for_load_state('domcontentloaded')
        sleep(2)


        try:
            post_img_files_locator = page.locator('.post__thumbnail figure a')
            post_url = HTTP_USER + j['href']

            img_count = post_img_files_locator.count()

            print(f"There is {img_count} img files to be downloaded at post {j['title']}, url {post_url}")

            for img in range(img_count):

                actual_img_tbd = post_img_files_locator.nth(img)
                img_url = actual_img_tbd.get_attribute('href')

                if img_url is None:
                    continue

                filename = img_url.split("/")[-1].split("?")[0]
                file_path = os.path.join(USER_DIR, filename)

                if os.path.exists(file_path):
                    print('already downloaded:', filename)
                    continue

                print('downloading:', img_url)

                response = page.request.get(img_url)

                with open(file_path, "wb") as f:
                    f.write(response.body())

                # sleep(2)

            
            user_post_links.append({
                'imgs': img_count,
                'post_url': post_url
            })
            


        except Exception as e:
            return print(e)

        sleep(2)
        page.goto(url=user_url)
        page.wait_for_load_state('domcontentloaded')
        x += 1

        with open('lista.json', 'w', encoding='utf-8') as f:
            json.dump(user_post_links, f, indent=4, ensure_ascii=False)

        if x > 50:
            print('cabeii')
            sleep(1208312)





HTTP_USER = 'https://kemono.cr'

with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)

    page = nav.new_page()
    page.goto(url='https://kemono.cr/artists', timeout=100000)
    # print(page.content())

    # Searches for user
    page.get_by_placeholder(text='Search...').fill(user)
    sleep(3)

    # Finds the search result
    user_profile = page.get_by_text(user).first

    if user_profile:
        user_profile.click()
    else:
        print(f"Couldn't find any {user}.")
        nav.close()

    # Necessary time for the page to load completely
    sleep(3)


    # Locates paginator
    try:
        has_paginator = page.locator(selector='small')

        # If paginator exists
        if has_paginator.count() > 0:


            page.wait_for_selector('#paginator-top small')
            user_posts_data_locator = page.locator('#paginator-top small')
            user_posts_data_raw = user_posts_data_locator.inner_html()

            # Separates correct number of user posts from page string
            user_posts_num = int(re.findall(r'\d+', user_posts_data_raw)[-1])
            print(f'{user} has {user_posts_num} posts, you can check..')

            # Determinates the number os pages based on posts number
            page_number = math.ceil(user_posts_num / 50)
            last_page_posts_num = user_posts_num % 50 or 50
            print(f'Also, this one has {page_number} pages to go through, and youll find {last_page_posts_num} posts os last page.')


            # Waits for element to load on page
            page.wait_for_selector('#paginator-top menu a')

            paginator_menu = page.locator('#paginator-top menu')

            paginator_items = paginator_menu.locator('a')
            page_count = paginator_items.count()

            user_pages = []

            for i in range(page_count):
                paginator_locator = paginator_items.nth(i)
                paginator_text_raw = paginator_locator.inner_html()
                page_link = paginator_locator.get_attribute('href')

                # 1. Busca o padrão <b>numero</b>
                # \d+ captura um ou mais dígitos
                match = re.search(r'<b>(\d+)</b>', paginator_text_raw)

                # Verifica se o padrão foi encontrado
                if match:
                    # 2. Extrai apenas o que está dentro dos parênteses (\d+)
                    clean_text = match.group(1)

                    user_pages.append({
                        "text": clean_text,
                        "href": page_link,
                        "locator": paginator_locator,
                    })
                
            page.wait_for_load_state('domcontentloaded')

            # THIS IS HOW IT CLICKS OTHER PAGES
            # user_pages[9]["locator"].click()

            # THIS IS HOW THE PAGINATOR GETS UPLOADED
            # user_pages = get_paginator_status(page)


            ### STARTING DOWNLOAD PROCESS
            # AT FIRST PAGE:
            download_loop(page)

        



        else:
            print('theres no paginator')
            pass




    except Exception as e:
        print(e)



    sleep(300)
    nav.close()