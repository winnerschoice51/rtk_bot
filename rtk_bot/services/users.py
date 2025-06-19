from config import USERS_FILE

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
