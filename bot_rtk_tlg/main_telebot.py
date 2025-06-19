import os
import signal
import sys
import time
import telebot
from telebot import types
from rarfile import RarFile
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from datetime import datetime, timedelta
from get_weather_from_accu import get_weather_full
from get_weather_from_openweathermap_sync import get_weather_full

BOT_TOKEN = '8058971937:AAFjf3Gc9tCX5jpl3-0eM6qfCf7TEW10SsU'
USERS_FILE = "users.txt"
LOCATION = "polyarny,ru"
ADMINS = {7606152113}

bot = telebot.TeleBot(BOT_TOKEN)

menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
buttons = [
    ["График мастеров", "График диспетчеров"],
    ["Полезные номера", "Полезная информация"],
    ["Прошивки оборудования", "Прогноз погоды"],
]
for row in buttons:
    menu_keyboard.row(*row)


def load_users():
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip().isdigit())


def save_user(user_id: int):
    users = load_users()
    if user_id not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")


def wind_direction(deg):
    dirs = [
        "северный", "северо-восточный", "восточный", "юго-восточный",
        "южный", "юго-западный", "западный", "северо-западный"
    ]
    ix = round(deg / 45) % 8
    return dirs[ix]


def weather_icon(weather_id):
    if 200 <= weather_id < 300:
        return "⛈️"
    elif 300 <= weather_id < 400:
        return "🌦️"
    elif 500 <= weather_id < 600:
        return "🌧️"
    elif 600 <= weather_id < 700:
        return "❄️"
    elif 700 <= weather_id < 800:
        return "🌫️"
    elif weather_id == 800:
        return "☀️"
    elif weather_id == 801:
        return "🌤️"
    elif 802 <= weather_id <= 804:
        return "☁️"
    else:
        return "🌈"


TARGET_HOURS = [1, 8, 14, 19]


def send_weather_to_all():
    weather = get_weather_full()
    message = f"🌅 Доброе утро мир! Сегодня нас ожидает такая погода:\n\n{weather}"
    users = load_users()
    for user_id in users:
        try:
            bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")
        except Exception as e:
            print(f"Не удалось отправить сообщение {user_id}: {e}")


@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    bot.send_message(message.chat.id, "Выберите пункт меню:", reply_markup=menu_keyboard)


@bot.message_handler(commands=['extract'])
def extract(message):
    rar_path = "firmware.rar"
    extract_dir = "extracted_firmware"

    try:
        if not os.path.exists(rar_path):
            bot.send_message(message.chat.id, "❌ Архив не найден.")
            return

        os.makedirs(extract_dir, exist_ok=True)

        with RarFile(rar_path) as rf:
            rf.extractall(path=extract_dir)

        files = os.listdir(extract_dir)
        msg = "✅ Архив успешно распакован. Файлы:\n" + "\n".join(files)
        bot.send_message(message.chat.id, msg)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка при распаковке: {e}")


@bot.message_handler(commands=['restart'])
def restart(message):
    bot.send_message(message.chat.id, "♻️ Перезапускаю бота...")

    # Создаем флаг-файл для watcher
    with open("restart.flag", "w") as f:
        f.write("1")

    # Завершаем процесс корректно через сигнал SIGINT
    os.kill(os.getpid(), signal.SIGINT)


@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text

    text_responses = {
        "Полезные номера": """☎️ АКТУАЛЬНЫЕ НОМЕРА ДИСПЕТЧЕРОВ

Васильева Екатерина:
+79212822470
+79916702832
8(81556)31008

Лодыгина Галина:
+79215162580 (личный)
+79020356086
8(81551)72512

... (оставим как есть для краткости)
"""
    }

    photo_mapping = {
        "График мастеров": "masters.jpg",
        "График диспетчеров": "dispatchers.jpg",
        "Полезная информация": "info.jpg"
    }

    if text == "Прогноз погоды":
        weather = get_weather_full()
        bot.send_message(message.chat.id, weather, parse_mode="HTML")

    elif text in text_responses:
        bot.send_message(message.chat.id, text_responses[text], parse_mode="HTML")

    elif text in photo_mapping:
        filename = photo_mapping[text]
        if os.path.exists(filename):
            with open(filename, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=text)
        else:
            bot.send_message(message.chat.id, "❌ Картинка не найдена.")

    elif text == "Прошивки оборудования":
        rar_file = "D-link 1.0.7.tar"
        try:
            if not os.path.exists(rar_file):
                raise FileNotFoundError

            size_mb = os.path.getsize(rar_file) / (1024 * 1024)
            if size_mb > 50:
                bot.send_message(message.chat.id,
                                 f"⚠️ Файл слишком большой ({size_mb:.2f} MB). Максимальный размер — 50MB.")
                return

            with open(rar_file, 'rb') as doc:
                bot.send_document(message.chat.id, doc, caption="Прошивки оборудования")

        except FileNotFoundError:
            bot.send_message(message.chat.id, "❌ Файл прошивок не найден.")
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Ошибка при отправке архива: {e}")

    else:
        bot.send_message(message.chat.id, "❓ Неизвестная команда. Пожалуйста, выберите из меню.")



if __name__ == "__main__":
    pid_dir = os.getenv('TEMP', '.')
    pidfile = os.path.join(pid_dir, 'telegram_bot.pid')

    if os.path.exists(pidfile):
        print("Already running.")
        sys.exit()

    with open(pidfile, "w") as f:
        f.write(str(os.getpid()))

    scheduler = BackgroundScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_weather_to_all, 'cron', hour=7, minute=30)
    scheduler.start()

    print("Бот запущен!")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Бот остановлен по сигналу.")
    finally:
        if os.path.exists(pidfile):
            os.remove(pidfile)