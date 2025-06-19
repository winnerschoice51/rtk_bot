import os
import sys
import signal
from config import BOT_TOKEN, ADMINS
from telebot import TeleBot
from apscheduler.schedulers.background import BackgroundScheduler
from services.users import load_users
from services.weather import get_weather_full
from handlers import common, messages, firmware

bot = TeleBot(BOT_TOKEN)
common.register(bot)
messages.register(bot)
firmware.register(bot)

def send_weather_to_all():
    weather = get_weather_full()
    message = f"🌅 Доброе утро мир! Сегодня нас ожидает такая погода:\n\n{weather}"
    for user_id in load_users():
        try:
            bot.send_message(user_id, message, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка при отправке {user_id}: {e}")

if __name__ == "__main__":
    pidfile = os.path.join(os.getenv('TEMP', '.'), 'telegram_bot.pid')
    if os.path.exists(pidfile):
        print("Уже запущен.")
    else:
        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))

        scheduler = BackgroundScheduler(timezone="Europe/Moscow")
        scheduler.add_job(send_weather_to_all, 'cron', hour=7, minute=30)
        scheduler.start()

        print("Бот запущен!")
        try:
            bot.infinity_polling()
        except KeyboardInterrupt:
            print("Бот остановлен.")
        finally:
            if os.path.exists(pidfile):
                os.remove(pidfile)
