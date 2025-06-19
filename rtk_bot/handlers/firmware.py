import os
from rarfile import RarFile

def register(bot):
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
            bot.send_message(message.chat.id, "✅ Распаковано:\n" + "\n".join(os.listdir(extract_dir)))
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Ошибка: {e}")

def send_firmware(bot, message):
    filepath = "D-link 1.0.7.tar"
    if not os.path.exists(filepath):
        bot.send_message(message.chat.id, "❌ Файл не найден.")
        return
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    if size_mb > 50:
        bot.send_message(message.chat.id, f"⚠️ Файл слишком большой ({size_mb:.2f} MB).")
        return
    with open(filepath, 'rb') as doc:
        bot.send_document(message.chat.id, doc, caption="Прошивки оборудования")
