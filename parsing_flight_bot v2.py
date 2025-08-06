from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import os
from flask import Flask
from threading import Thread
from telegram.ext import Updater, CommandHandler, ApplicationBuilder
from telegram import Update
import asyncio

TOKEN = os.getenv("BOT_TOKEN")

app = Flask(__name__)

@app.route('/')
def index():
    return "Бот работает! (Flask сервер жив)"

def get_flight_status():
    url = "https://www.vnukovo.ru/ru/for-passengers/reysi/online-tablo/?bound=departure&search=UT+785"

    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = "/nix/store/qa9cnw4v5xkxyip6mb9kxqfq1z4x2dx1-chromium-138.0.7204.100/bin/chromium"
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--remote-debugging-port=9222")    

    service = Service("/nix/store/8zj50jw4w0hby47167kqqsaqw4mm5bkd-chromedriver-unwrapped-138.0.7204.100/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)

    # Ожидание загрузки динамического контента
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    # Находим блок со всем датами нужного рейса
    flights_block = soup.find("div", class_="timetable _scrolltop")

    # Парсим все доступные рейсы
    all_statuses = ""
    all_flights = flights_block.find_all("a", class_="timetable__row")
    if len(all_flights) > 1:
        for flight in all_flights:
            time_block = flight.find('span', {'class': 'fl-time'})
            scheduled_time = time_block.find('time').get_text(strip=True) if time_block else "Н/Д"
            time_spans = time_block.find_all("span", class_="screen-reader-only")
            if len(time_spans) > 1:
                date_text = time_spans[1].get_text(strip=True) if time_spans else "Н/Д"

            status_block = flight.find("span", class_="timetable__row__td _status")
            try:
                if status_block:
                    main_status = status_block.find("span", class_="fl-status__content").contents[0].strip()
                    try:
                        small_status = status_block.find("span", class_="fl-status__content__small").get_text(strip=True)
                    except Exception as e:
                        small_status = ""
                    if small_status == "":
                        status_now = f"{main_status}"
                    else:
                        status_now = f"{main_status}, {small_status}"
                else:
                    status_now = "Н/Д"
                # status_now = status_block.find("span", class_="fl-status__content").get_text() if status_block else "Н/Д"
            except Exception as e:
                status_now = "Пока нет данных по этому рейсу"
            all_statuses = all_statuses + f"По расписанию: Вылет {date_text} в {scheduled_time}\nТекущий статус: {status_now}\n\n" 

            # print("\n")
            # print(f"По расписанию: Вылет {date_text} в {scheduled_time}")
            # print(f"Текущий статус: {status_now}")
    return all_statuses


async def start(update, context):
    await update.message.reply_text("Привет! Отправь /flight чтобы узнать статус рейса.")

async def flight(update, context):
    user = update.effective_user
    username = user.username if user.username else "неизвестно"
    if username.lower() == 'vimaltsev':
        await update.message.reply_text("Пошел ка ты, Виталик! Сам иди на сайт и смотри статус рейса!")
        return

    status = get_flight_status()
    await update.message.reply_text(status)
    return

async def run_bot():
    app_telegram = ApplicationBuilder().token(TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("flight", flight))
    await app_telegram.initialize()
    await app_telegram.start()
    await app_telegram.updater.start_polling()

    await asyncio.Event().wait()

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    asyncio.run(run_bot())