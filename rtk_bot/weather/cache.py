import os
import time
import pickle
from .config import CACHE_DIR
from .logger import log

def cache_load(name, max_age_sec, use_cache=True):
    if not use_cache:
        log(f"⏭ Пропуск кеша для {name}")
        return None
    path = os.path.join(CACHE_DIR, f"{name}.pkl")
    if not os.path.exists(path):
        return None
    if time.time() - os.path.getmtime(path) > max_age_sec:
        log(f"📛 Кеш устарел: {name}")
        return None
    try:
        with open(path, "rb") as f:
            log(f"📥 Загрузка из кеша: {name}")
            return pickle.load(f)
    except Exception as e:
        log(f"⚠️ Ошибка при чтении кеша {name}: {e}")
        return None

def cache_save(name, data):
    path = os.path.join(CACHE_DIR, f"{name}.pkl")
    try:
        with open(path, "wb") as f:
            pickle.dump(data, f)
        log(f"📦 Сохранено в кеш: {name}")
    except Exception as e:
        log(f"⚠️ Ошибка при сохранении кеша {name}: {e}")

def clear_cache():
    if not os.path.exists(CACHE_DIR):
        return
    for file in os.listdir(CACHE_DIR):
        os.remove(os.path.join(CACHE_DIR, file))
    log("🧹 Кеш очищен")
