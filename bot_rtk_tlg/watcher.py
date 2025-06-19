import subprocess
import time
import os
import logging
import sys

# Файл-флаг, наличие которого сигнализирует о необходимости перезапуска бота
RESTART_FLAG_FILE = 'restart.flag'

# Имя скрипта основного бота, который будет запускаться и перезапускаться
BOT_SCRIPT = 'main_telebot.py'

# Настройка логирования в консоль с уровнем INFO и форматом сообщения
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def git_pull():
    """
    Выполняет команду `git pull` для обновления кода из репозитория.
    Логирует вывод и ошибки.
    """
    logging.info("Обновляем код из git...")
    result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
    if result.stdout:
        logging.info(f"git pull output:\n{result.stdout.strip()}")
    if result.returncode != 0:
        logging.error(f"Ошибка git pull:\n{result.stderr.strip()}")
    else:
        logging.info("Обновление прошло успешно.")



python_executable = sys.executable  # это текущий интерпретатор, которым запускается watcher

def run_bot():
        logging.info(f"Запускаем бота: {python_executable} {BOT_SCRIPT}")
        return subprocess.Popen([python_executable, BOT_SCRIPT])


def main():
    bot_process = run_bot()
    logging.info(f"Бот запущен, PID: {bot_process.pid}")

    while True:
        time.sleep(5)

        if os.path.exists(RESTART_FLAG_FILE):
            logging.info("Обнаружен запрос на перезапуск (файл restart.flag найден)")
            os.remove(RESTART_FLAG_FILE)

            logging.info("Останавливаем бота...")
            bot_process.terminate()
            try:
                bot_process.wait(timeout=10)
                logging.info("main_telebot.py завершился, продолжаем.")
                logging.info("Бот успешно остановлен.")
            except subprocess.TimeoutExpired:
                logging.warning("Бот не завершился за 10 секунд, убиваем процесс.")
                bot_process.kill()
                bot_process.wait()

            # 🧼 Удаляем PID-файл, чтобы новый бот мог стартануть
            pidfile = os.path.join(os.getenv('TEMP', '.'), 'telegram_bot.pid')
            if os.path.exists(pidfile):
                logging.info("Удаляем устаревший PID-файл.")
                os.remove(pidfile)

            git_pull()
            bot_process = run_bot()
            logging.info(f"Бот перезапущен, PID: {bot_process.pid}")


if __name__ == '__main__':
    main()
