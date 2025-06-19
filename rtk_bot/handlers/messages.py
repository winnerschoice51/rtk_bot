import os
from telebot import types
from services.weather import get_weather_full

menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
buttons = [
    ["График мастеров", "График диспетчеров"],
    ["Полезные номера", "Полезная информация"],
    ["Прошивки оборудования", "Прогноз погоды"],
]
for row in buttons:
    menu_keyboard.row(*row)

def register(bot):
    @bot.message_handler(func=lambda m: True)
    def respond(message):
        text = message.text
        if text == "Прогноз погоды":
            bot.send_message(message.chat.id, get_weather_full(), parse_mode="HTML")
        elif text == "Полезные номера":
            bot.send_message(message.chat.id, """
☎️ АКТУАЛЬНЫЕ НОМЕРА ДИСПЕТЧЕРОВ

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
""")
        elif text == "График мастеров":
            for i in [1, 2]:
                path = f"masters{i}.jpg"
                if os.path.exists(path):
                    with open(path, 'rb') as photo:
                        bot.send_photo(message.chat.id, photo, caption=f"График мастеров ({i}/2)")
        elif text in {"График диспетчеров", "Полезная информация"}:
            name = {"График диспетчеров": "dispatchers.jpg", "Полезная информация": "info.jpg"}[text]
            if os.path.exists(name):
                with open(name, 'rb') as photo:
                    bot.send_photo(message.chat.id, photo, caption=text)
        elif text == "Прошивки оборудования":
            from handlers.firmware import send_firmware
            send_firmware(bot, message)
        else:
            bot.send_message(message.chat.id, "❓ Неизвестная команда.")
