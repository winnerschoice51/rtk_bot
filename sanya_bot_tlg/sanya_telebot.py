import telebot
import threading
import logging
from datetime import datetime, time as dt_time, timedelta

TOKEN = '7813793130:AAGAUQuLAuhEMtYrcP_NVgiwYl2_PVfUFhQ'
bot = telebot.TeleBot(TOKEN)

# ID пользователя, которому шлём напоминания
USER_ID = 1748157760

# Флаг активности напоминаний
reminders_active = False

# Время первого напоминания (час и минута)
START_TIME = dt_time(18, 00)

# Интервал между напоминаниями
INTERVAL = timedelta(minutes=60)

# Количество напоминаний за один раз
REMINDERS_COUNT = 12

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def get_next_thursday_after(dt):
    """
    Возвращает дату следующего четверга после даты dt.
    Если сегодня четверг и время уже прошло, вернёт следующий четверг.
    """
    days_ahead = 2 - dt.weekday()  # 3 — четверг
    if days_ahead <= 0:
        days_ahead += 7
    next_thursday = dt + timedelta(days=days_ahead)
    logging.debug(f"Next Thursday after {dt.date()} is {next_thursday.date()}")
    return next_thursday

def send_reminder():
    """
    Отправляет напоминание пользователю, если напоминания активны и USER_ID задан.
    """
    global reminders_active, USER_ID

    if not reminders_active:
        logging.info("Напоминания не активны, пропускаем отправку")
        return
    if USER_ID is None:
        logging.warning("USER_ID не установлен, невозможно отправить напоминание")
        return

    keyboard = telebot.types.InlineKeyboardMarkup()
    button_done = telebot.types.InlineKeyboardButton(text='Выполнено', callback_data='done')
    keyboard.add(button_done)

    try:
        bot.send_message(USER_ID, "Необходимо Тае подкрутить пластинку на зубах", reply_markup=keyboard)
        logging.info(f"Отправлено напоминание пользователю {USER_ID}")
    except Exception as e:
        logging.error(f"Ошибка при отправке напоминания: {e}")


def schedule_reminders():
    """
    Запускает серию таймеров, которые по расписанию вызывают send_reminder().
    Первое напоминание происходит сразу после запуска,
    остальные — с интервалом INTERVAL, всего REMINDERS_COUNT раз.
    """
    global reminders_active
    reminders_active = True
    now = datetime.now()

    # Первое напоминание - сразу
    delay = 0
    logging.info(f"Запланировано первое напоминание сразу")
    threading.Timer(delay, send_reminder).start()

    # Остальные с интервалом
    for i in range(1, REMINDERS_COUNT):
        delay = i * INTERVAL.total_seconds()
        remind_time = now + timedelta(seconds=delay)
        logging.info(f"Запланировано напоминание на {remind_time} (через {int(delay)} сек)")
        threading.Timer(delay, send_reminder).start()

@bot.message_handler(commands=['start'])
def start(message):
    """
    Обработчик команды /start.
    Запоминает ID пользователя и запускает напоминания.
    """
    global USER_ID, reminders_active
    USER_ID = message.from_user.id
    reminders_active = False

    bot.send_message(USER_ID, "Бот активирован. Напоминания будут приходить по четвергам с 13:42.")
    logging.info(f"Пользователь {USER_ID} активировал бота")
    schedule_reminders()

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """
    Обработчик нажатий на inline-кнопки.
    Если пользователь нажал 'Выполнено', отключаем напоминания.
    """
    global reminders_active
    if call.data == 'done':
        reminders_active = False
        logging.info(f"Пользователь {call.from_user.id} остановил напоминания")
        bot.edit_message_text(
            "Отлично! Напоминания остановлены до следующей среды.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id, text="Напоминания остановлены.")

if __name__ == '__main__':
    logging.info("Бот запущен")
    bot.polling(none_stop=True)
