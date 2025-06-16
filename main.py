import os
import nest_asyncio
import aiohttp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.request import HTTPXRequest
from rarfile import RarFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

nest_asyncio.apply()

BOT_TOKEN = '8058971937:AAFjf3Gc9tCX5jpl3-0eM6qfCf7TEW10SsU'
USERS_FILE = "users.txt"
OPENWEATHER_API_KEY = '1e7c14d84797330a8636a5b6fdee8f36'
LOCATION = "polyarny,ru"  # город для OpenWeatherMap, маленькими буквами

menu_keyboard = [
    ["График мастеров", "График диспетчеров"],
    ["Полезные номера", "Полезная информация"],
    ["Прошивки оборудования", "Прогноз погоды"]
]
reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)

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

async def get_weather_full():
    url = (f"https://api.openweathermap.org/data/2.5/forecast?q={LOCATION}"
           f"&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru")

    proxy = os.getenv("http_proxy") or os.getenv("https_proxy")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy) as resp:
                data = await resp.json()
                if resp.status != 200 or "list" not in data:
                    return f"⚠️ Не удалось получить погоду. Код {resp.status}"

                morning = None
                day = None
                evening = None

                utc_offset = timedelta(hours=3)  # Местное смещение времени (GMT+3)

                for entry in data["list"]:
                    dt_utc = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
                    dt = dt_utc + utc_offset
                    hour = dt.hour
                    desc = entry["weather"][0]["description"].capitalize()
                    temp = entry["main"]["temp"]

                    if 6 <= hour <= 11 and morning is None:
                        morning = (desc, temp)
                    elif 12 <= hour <= 17 and day is None:
                        day = (desc, temp)
                    elif 18 <= hour <= 23 and evening is None:
                        evening = (desc, temp)

                    if morning and day and evening:
                        break

                def format_part(name, data):
                    return f"{name}: {data[0]}, {data[1]:+.1f}°C" if data else f"{name}: нет данных"

                return (
                    f"🌦 Прогноз погоды:\n"
                    f"{format_part('Утро', morning)}\n"
                    f"{format_part('День', day)}\n"
                    f"{format_part('Вечер', evening)}"
                )
    except Exception as e:
        return f"⚠️ Ошибка при получении погоды: {e}"

async def send_weather_to_all(app):
    weather = await get_weather_full()
    message = f"🌅 Доброе утро!\nСегодня нас ожидает такая погода:\n{weather}"
    for user_id in load_users():
        try:
            await app.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Не удалось отправить сообщение {user_id}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_chat.id)
    await update.message.reply_text("Выберите пункт меню:", reply_markup=reply_markup)

async def extract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rar_path = "firmware.rar"
    extract_dir = "extracted_firmware"

    try:
        if not os.path.exists(rar_path):
            await update.message.reply_text("❌ Архив не найден.")
            return

        os.makedirs(extract_dir, exist_ok=True)

        with RarFile(rar_path) as rf:
            rf.extractall(path=extract_dir)

        files = os.listdir(extract_dir)
        msg = "✅ Архив успешно распакован. Файлы:\n" + "\n".join(files)
        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при распаковке: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    text_responses = {
        "Полезные номера": """☎️ АКТУАЛЬНЫЕ НОМЕРА ДИСПЕТЧЕРОВ
...твой текст с номерами...""",
    }

    photo_mapping = {
        "График мастеров": "masters.jpg",
        "График диспетчеров": "dispatchers.jpg",
        "Полезная информация": "info.jpg"
    }

    if text == "Прогноз погоды":
        weather = await get_weather_full()
        await update.message.reply_text(weather)
    elif text in text_responses:
        await update.message.reply_text(text_responses[text])
    elif text in photo_mapping:
        filename = photo_mapping[text]
        try:
            with open(filename, 'rb') as photo:
                await update.message.reply_photo(photo=photo, caption=text)
        except FileNotFoundError:
            await update.message.reply_text("❌ Картинка не найдена.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка при отправке: {e}")
    elif text == "Прошивки оборудования":
        rar_file = "D-link 1.0.7.tar"
        try:
            if not os.path.exists(rar_file):
                raise FileNotFoundError

            size_mb = os.path.getsize(rar_file) / (1024 * 1024)
            if size_mb > 50:
                await update.message.reply_text(f"⚠️ Файл слишком большой ({size_mb:.2f} MB). Максимальный размер — 50MB.")
                return

            with open(rar_file, 'rb') as doc:
                await update.message.reply_document(document=doc, filename=rar_file, caption="Прошивки оборудования")
        except FileNotFoundError:
            await update.message.reply_text("❌ Файл прошивок не найден.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка при отправке архива: {e}")
    else:
        await update.message.reply_text("❓ Неизвестная команда. Пожалуйста, выберите из меню.")

async def main():
    request = HTTPXRequest(connect_timeout=10.0, read_timeout=20.0)
    app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("extract", extract))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_weather_to_all, 'cron', hour=8, minute=0, args=[app])
    scheduler.start()

    # Для Render: используем webhook
    PORT = int(os.environ.get("PORT", 8000))
    WEBHOOK_URL = f"https://srv-d17ttj6mcj7s73ca5brg.onrender.com/{BOT_TOKEN}"

    print(f"Запуск webhook на порту {PORT}, URL: {WEBHOOK_URL}")

    await app.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_path=f"/{BOT_TOKEN}",
        url_path=f"/{BOT_TOKEN}",
        webhook_url=WEBHOOK_URL,
    )

    # Чтобы бот не завершался
    await app.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())
