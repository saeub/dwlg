import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from time import sleep
from urllib.parse import parse_qs

import requests
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from seleniumwire import webdriver


def get_pqhash(menu_item: str) -> str:
    service = ChromeService("/usr/local/bin/chromedriver")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(
        f"https://learngerman.dw.com/de/singlereisen-liegen-im-trend/l-64273452/x"
    )
    try:
        driver.find_element(
            By.CSS_SELECTOR, "button[data-testid='gdprAcceptButton']"
        ).click()
    except NoSuchElementException:
        pass
    driver.find_element(
        By.CSS_SELECTOR, "button[data-target='#lecture-nav-user-menu']"
    ).click()
    driver.find_element(By.LINK_TEXT, menu_item).click()
    request = driver.wait_for_request("/graphql")
    del driver.requests
    graphql_extensions = json.loads(parse_qs(request.querystring)["extensions"][0])
    return graphql_extensions["persistedQuery"]["sha256Hash"]

print("Fetching PQHASHES...", file=sys.stderr)
PQHASHES = {
    menu_item: get_pqhash(menu_item)
    for menu_item in [
        "Information",
        "Übungen",
        "Manuskript",
        "Extras",
    ]
}
print(f"{PQHASHES = }", file=sys.stderr)


def graphql_get(url):
    sleepsecs = 10
    while True:
        try:
            response = requests.get(url, headers={"Content-Type": "application/json"})
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error ({e}): {url}", file=sys.stderr)
            print(f"Waiting {sleepsecs} seconds before retrying...", file=sys.stderr)
            sleep(sleepsecs)
            sleepsecs += 10
            continue
        if response.status_code != 200:
            print(f"Request failed (status {response.status_code}): {url}", file=sys.stderr)
            print(f"Waiting {sleepsecs} seconds before retrying...", file=sys.stderr)
            sleep(sleepsecs)
            continue
        data = response.json()
        if "data" not in data:
            print(f"Invalid data received: {url}", file=sys.stderr)
            print(f"Waiting {sleepsecs} seconds before retrying...", file=sys.stderr)
            sleep(sleepsecs)
            sleepsecs += 10
            continue
        return data["data"]["content"]


def get_lesson(lesson_id):
    pqhash = PQHASHES["Information"]
    url = f"https://learngerman.dw.com/graphql?operationName=LessonInformation&variables=%7B%22lessonId%22%3A{lesson_id}%2C%22lang%22%3A%22GERMAN%22%2C%22appName%22%3A%22mdl%22%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{pqhash}%22%7D%7D"
    date = datetime.now().isoformat()
    data = graphql_get(url)
    data["__fetch_url"] = url
    data["__fetch_date"] = date
    return data


def get_manuscript(lesson_id):
    pqhash = PQHASHES["Manuskript"]
    url = f"https://learngerman.dw.com/graphql?operationName=ManuscriptPage&variables=%7B%22id%22%3A{lesson_id}%2C%22lang%22%3A%22GERMAN%22%2C%22appName%22%3A%22mdl%22%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{pqhash}%22%7D%7D"
    date = datetime.now().isoformat()
    data = graphql_get(url)
    data["__fetch_url"] = url
    data["__fetch_date"] = date
    return data


# def get_vocabulary(lesson_id):
#     url = f"https://learngerman.dw.com/graphql?operationName=LessonVocabulary&variables=%7B%22lessonId%22%3A{lesson_id}%2C%22lessonLang%22%3A%22GERMAN%22%2C%22appName%22%3A%22mdl%22%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{pqhash}%22%7D%7D"
#     date = datetime.now().isoformat()
#     data = graphql_get(url)
#     data["__fetch_url"] = url
#     data["__fetch_date"] = date
#     return data


def get_exercise(lesson_id, exercise_id):
    pqhash = PQHASHES["Übungen"]
    url = f"https://learngerman.dw.com/graphql?operationName=LessonExercise&variables=%7B%22exerciseId%22%3A{exercise_id}%2C%22lessonLang%22%3A%22GERMAN%22%2C%22contextId%22%3A{lesson_id}%2C%22appName%22%3A%22mdl%22%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{pqhash}%22%7D%7D"
    date = datetime.now().isoformat()
    data = graphql_get(url)
    if data is None or data["__typename"] != "Exercise":
        return None
    data["__fetch_url"] = url
    data["__fetch_date"] = date
    return data


def get_extras(lesson_id):
    pqhash = PQHASHES["Extras"]
    url = f"https://learngerman.dw.com/graphql?operationName=LessonExtrasPage&variables=%7B%22id%22%3A{lesson_id}%2C%22lang%22%3A%22GERMAN%22%2C%22appName%22%3A%22mdl%22%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{pqhash}%22%7D%7D"
    date = datetime.now().isoformat()
    data = graphql_get(url)
    data["__fetch_url"] = url
    data["__fetch_date"] = date
    return data


lesson_ids = defaultdict(list)


# Top-Thema

print("Top-Thema: Fetching lesson IDs...", file=sys.stderr)
archive_urls = [
    "https://learngerman.dw.com/de/top-thema-mit-vokabeln-archiv-2019/a-63194575",  # 2019
    "https://learngerman.dw.com/de/top-thema-mit-vokabeln-archiv-2020/a-60069246",  # 2020
    "https://learngerman.dw.com/de/top-thema-mit-vokabeln-archiv-2021/a-59401823",  # 2021
    "https://learngerman.dw.com/de/top-thema-mit-vokabeln-archiv-2022/a-60327880",  # 2022
    "https://learngerman.dw.com/de/top-thema-mit-vokabeln-archiv-2023/a-64276250",  # 2023
    "https://learngerman.dw.com/de/top-thema-mit-vokabeln-archiv-2024/a-67825522",  # 2024
]
for url in archive_urls:
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.select("a"):
        match = re.search(r"l-(\d+)/?$", link["href"])
        if match is not None:
            lesson_id = match.group(1)
            lesson_ids["top-thema"].append(lesson_id)
print(f"Top-Thema: Fetched {len(lesson_ids['top-thema'])} lesson IDs", file=sys.stderr)


# Video-Thema

print("Video-Thema: Fetching lesson IDs...", file=sys.stderr)
archive_urls = [
    "https://learngerman.dw.com/de/video-thema-archiv-2019/a-63441164",  # 2019
    "https://learngerman.dw.com/de/video-thema-archiv-2020/a-60069280",  # 2020
    "https://learngerman.dw.com/de/video-thema-archiv-2021/a-59415031",  # 2021
    "https://learngerman.dw.com/de/video-thema-archiv-2022/a-60328502",  # 2022
    "https://learngerman.dw.com/de/video-thema-archiv-2023/a-64287824",  # 2023
    "https://learngerman.dw.com/de/video-thema-archiv-2024/a-67826398",  # 2024
]
for url in archive_urls:
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.select("a"):
        match = re.search(r"l-(\d+)/?$", link["href"])
        if match is not None:
            lesson_id = match.group(1)
            lesson_ids["video-thema"].append(lesson_id)
print(
    f"Video-Thema: Fetched {len(lesson_ids['video-thema'])} lesson IDs", file=sys.stderr
)


# Nicos Weg

print("Nicos Weg: Fetching lesson IDs...", file=sys.stderr)
toc_urls = [
    "https://learngerman.dw.com/de/nicos-weg/c-36519687",  # A1
    "https://learngerman.dw.com/de/nicos-weg/c-36519709",  # A2
    "https://learngerman.dw.com/de/nicos-weg/c-36519718",  # B1
]
for url in toc_urls:
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.select("ul li a"):
        match = re.search(r"l-(\d+)/?$", link["href"])
        if match is not None:
            lesson_id = match.group(1)
            lesson_ids["nicos-weg"].append(lesson_id)
print(f"Nicos Weg: Fetched {len(lesson_ids['nicos-weg'])} lesson IDs", file=sys.stderr)


# Ticket nach Berlin

print("Ticket nach Berlin: Fetching lesson IDs...", file=sys.stderr)
toc_urls = [
    "https://learngerman.dw.com/de/ticket-nach-berlin/c-55320903",
]
for url in toc_urls:
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.select("ul li a"):
        match = re.search(r"l-(\d+)/?$", link["href"])
        if match is not None:
            lesson_id = match.group(1)
            lesson_ids["ticket-nach-berlin"].append(lesson_id)
print(
    f"Ticket nach Berlin: Fetched {len(lesson_ids['ticket-nach-berlin'])} lesson IDs",
    file=sys.stderr,
)


# Fetch data

for course, lesson_ids in lesson_ids.items():
    # Only include "Top-Thema" courses
    if course != "top-thema":
        continue

    for lesson_id in lesson_ids:
        if os.path.exists(f"data/raw/lesson-{lesson_id}.json"):
            print(f"Skipping lesson {lesson_id}...", file=sys.stderr)
            continue
        print(f"Fetching data for lesson {lesson_id}...", file=sys.stderr)
        lesson = get_lesson(lesson_id)
        manuscript = get_manuscript(lesson_id)
        # vocabulary = get_vocabulary(lesson_id)
        exercises = []
        for content_link in lesson["contentLinks"]:
            exercise_id = content_link["targetId"]
            exercise = get_exercise(lesson_id, exercise_id)
            if exercise is None:
                continue
            exercises.append(exercise)
        extras = get_extras(lesson_id)
        with open(f"data/raw/lesson-{lesson_id}.json", "w") as f:
            json.dump(
                {
                    "course": course,
                    "lesson": lesson,
                    "manuscript": manuscript,
                    # "vocabulary": vocabulary,
                    "exercises": exercises,
                    "extras": extras,
                },
                f,
                ensure_ascii=False,
            )
