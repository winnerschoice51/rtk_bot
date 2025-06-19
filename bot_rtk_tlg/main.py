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
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from get_weather_from_accu import ACCUWEATHER_API_KEY
from get_weather_accu_sunc import *
from get_weather_from_openweathermap import *

nest_asyncio.apply()

BOT_TOKEN = '8058971937:AAFjf3Gc9tCX5jpl3-0eM6qfCf7TEW10SsU'
USERS_FILE = "users.txt"
import sys

# Список админов (тебя и, возможно, других)
ADMINS = {7606152113}  # сюда впиши свои ID Telegram


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return

    await update.message.reply_text("♻️ Перезапускаю бота...")

    # Завершаем процесс, чтобы watcher мог запустить заново
    sys.exit(0)


menu_keyboard = [
    ["График мастеров", "График диспетчеров"],
    ["Полезные номера", "Полезная информация"],
    ["Прошивки оборудования", "Прогноз погоды"],

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


def format_entry(name, entry):
    if not entry:
        return f"🕒 <b>{name}</b>: <i>нет данных</i>"

    weather_id = entry["weather"][0]["id"]
    icon = weather_icon(weather_id)
    weather_desc = entry["weather"][0]["description"].capitalize()
    temp = entry["main"]["temp"]
    feels = entry["main"]["feels_like"]
    humidity = entry["main"]["humidity"]
    wind_mps = entry["wind"]["speed"]
    wind_kph = wind_mps * 3.6
    wind_deg = entry["wind"].get("deg", 0)
    wind_dir = wind_direction(wind_deg)
    rain = entry.get("rain", {}).get("3h", 0.0)
    snow = entry.get("snow", {}).get("3h", 0.0)

    rain_snow = ""
    if rain:
        rain_snow += f", 🌧 {rain} мм"
    if snow:
        rain_snow += f", ❄️ {snow} мм"

    return (
        f"🕒 <b>{name}</b>: {icon} {weather_desc}\n"
        f"🌡 Температура: {temp:+.1f}°C (ощущается как {feels:+.1f}°C)\n"
        f"💨 Ветер: {wind_kph:.1f} км/ч, {wind_dir}\n"
        f"💧 Влажность: {humidity}%{rain_snow}"
    )


TARGET_HOURS = [1, 8, 14, 19]


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

                utc_offset = timedelta(hours=3)  # скорректируй, если у тебя другой часовой пояс

                now = datetime.utcnow() + utc_offset

                results = {}

                for target_hour in TARGET_HOURS:
                    closest_entry = None
                    min_diff = timedelta(days=10)  # большое значение для инициализации

                    for entry in data["list"]:
                        dt_utc = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
                        dt_local = dt_utc + utc_offset

                        # Пропускаем даты раньше текущего времени
                        if dt_local < now:
                            continue

                        # Ищем ближайшее время с целевым часом или позже
                        # Если час совпадает или больше целевого часа в этот день, считаем разницу
                        # чтобы выбрать минимальную положительную разницу по времени
                        if dt_local.hour == target_hour or dt_local.hour > target_hour:
                            diff = dt_local - now
                            if diff < min_diff:
                                min_diff = diff
                                closest_entry = entry

                    # Если не нашли ни одного, попробуем просто ближайшее без ограничений (на всякий)
                    if not closest_entry:
                        for entry in data["list"]:
                            dt_utc = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
                            dt_local = dt_utc + utc_offset
                            diff = abs(dt_local.hour - target_hour)
                            if diff < min_diff:
                                min_diff = diff
                                closest_entry = entry

                    if closest_entry:
                        weather = closest_entry["weather"][0]["description"].capitalize()
                        temp = closest_entry["main"]["temp"]
                        feels_like = closest_entry["main"]["feels_like"]
                        wind_speed = closest_entry["wind"]["speed"] * 3.6  # м/с в км/ч
                        wind_deg = closest_entry["wind"].get("deg", 0)
                        humidity = closest_entry["main"]["humidity"]

                        def deg_to_dir(deg):
                            dirs = ['северный', 'северо-восточный', 'восточный', 'юго-восточный',
                                    'южный', 'юго-западный', 'западный', 'северо-западный']
                            ix = int((deg + 22.5) // 45) % 8
                            return dirs[ix]

                        wind_dir = deg_to_dir(wind_deg)

                        results[target_hour] = {
                            "desc": weather,
                            "temp": temp,
                            "feels_like": feels_like,
                            "wind_speed": wind_speed,
                            "wind_dir": wind_dir,
                            "humidity": humidity
                        }
                    else:
                        results[target_hour] = None

                time_labels = {
                    1: "🌙 Ночь (01:00)",
                    8: "🌅 Утро (08:00)",
                    14: "☀️ День (14:00)",
                    19: "🌇 Вечер (19:00)"
                }

                parts = []
                for hour in TARGET_HOURS:
                    r = results.get(hour)
                    if r:
                        part = (f"{time_labels[hour]}:\n"
                                f"  {r['desc']}\n"
                                f"  🌡 Температура: {r['temp']:+.1f}°C (ощущается как {r['feels_like']:+.1f}°C)\n"
                                f"  💨 Ветер: {r['wind_speed']:.1f} км/ч, {r['wind_dir']}\n"
                                f"  💧 Влажность: {r['humidity']}%")
                    else:
                        part = f"{time_labels[hour]}: нет данных"
                    parts.append(part)

                return "🌦 Прогноз погоды:\n\n" + "\n\n".join(parts)

    except Exception as e:
        return f"⚠️ Ошибка при получении погоды: {e}"


async def send_weather_to_all(app):
    # weather = await get_weather_full()
    weather = await get_weather_accu_sunc()

    message = f"🌅 Доброе утро мир! Сегодня нас ожидает такая погода:\n\n{weather}"
    for user_id in load_users():
        try:
            await app.bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")
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
        await update.message.reply_text(msg, parse_mode='HTML')

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при распаковке: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

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

Маныч Марина:
+79916702834
+79210353530 (личный)
8(81554)63499

Ольгейзер Татьяна:
+79533005533 (личный)
8(81554)51556

Слепова Дарья:
+79118059964

Ковалева Мирана:
+79211552334

Скребцова Юлия:
+79913839831
8(81554)51299
8(81554)51556

Степанова Полина:
+79965617975 (личный)

Феофанова Ксения:
+79052943744 (личный)

Якимова Елена:
+7(991)6680982
8(81554)63499

🔆 ПО ВОПРОСАМ О ТАРИФАХ, ПРОДАЖАХ, ОБОРУДОВАНИЮ, СТОИМОСТИ :
Ивкина Александра
+79916702839
+79533075572

Булатова Ольга +79913839859

Михельсон Александр
+79113293009
+79215153009

☣ ПОЛЕЗНЫЕ НОМЕРА ☣️
Светенко Н.А. +79212866836
Хазова Н.В. +79212730712
Дубик А.Е. +79113223779

ГФС: <a href="tel:+78003013638">+78003013638</a>
(доб.625 ДЕНИС ЕВГЕНЬЕВИЧ МИШИН)
ПОДДЕРЖКА КИТ: <a href="tel:+78001000107">+78001000107</a> (КМУТ)
ПОДДЕРЖКА ЦКИЗ: <a href="tel:+78003019927">+78003019927</a> (КРИПТОШЛЮЗ)
ПОДДЕРЖКА: <a href="tel:+78003010212">+7800-301-02-12</a>
ПОДДЕРЖКА Т2: <a href="tel:+78003006611">+7800-300-6611</a> (доб.6611)
"""
    }

    photo_mapping = {
        "График мастеров": "masters.jpg",
        "График диспетчеров": "dispatchers.jpg",
        "Полезная информация": "info.jpg"
    }


    if text == "Прогноз погоды":
        weather = await get_weather_full()
        await update.message.reply_text(weather, parse_mode="HTML")
    elif text in text_responses:
        # Здесь добавлен parse_mode='HTML' для корректного отображения ссылок
        await update.message.reply_text(text_responses[text], parse_mode='HTML')
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
                await update.message.reply_text(
                    f"⚠️ Файл слишком большой ({size_mb:.2f} MB). Максимальный размер — 50MB.")
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
    app.add_handler(CommandHandler("restart", restart))

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_weather_to_all, 'cron', hour=7, minute=30, args=[app])
    scheduler.start()

    print("Бот запущен!")
    await app.run_polling(poll_interval=2.0)


if __name__ == "__main__":
    import os
    import sys

    pid_dir = os.getenv('TEMP', '.')  # или можно указать другую папку, например '.' — текущую
    pidfile = os.path.join(pid_dir, 'telegram_bot.pid')

    if os.path.exists(pidfile):
        print("Already running.")
        sys.exit()

    with open(pidfile, "w") as f:
        f.write(str(os.getpid()))

    try:
        import asyncio

        asyncio.run(main())
    finally:
        os.remove(pidfile)