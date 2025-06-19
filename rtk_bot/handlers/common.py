import os
import signal
from config import ADMINS
from services.users import save_user

def register(bot):
    @bot.message_handler(commands=['start'])
    def start(message):
        save_user(message.chat.id)
        from handlers.messages import menu_keyboard
        bot.send_message(message.chat.id, "Выберите пункт меню:", reply_markup=menu_keyboard)

    @bot.message_handler(commands=['stop'])
    def stop(message):
        if message.chat.id not in ADMINS:
            bot.send_message(message.chat.id, "❌ У вас нет прав.")
            return
        bot.send_message(message.chat.id, "🛑 Остановка бота...")
        os.remove(os.path.join(os.getenv('TEMP', '.'), 'telegram_bot.pid'))
        os.kill(os.getpid(), signal.SIGINT)

    @bot.message_handler(commands=['restart'])
    def restart(message):
        bot.send_message(message.chat.id, "♻️ Перезапуск...")
        with open("restart.flag", "w") as f:
            f.write("1")
        os.kill(os.getpid(), signal.SIGINT)
