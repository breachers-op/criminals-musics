import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///criminals_musics.db")

SUDO_USERS = list(map(int, os.getenv("SUDO_USERS", "").split(","))) if os.getenv("SUDO_USERS") else []

BOT_OWNER = int(os.getenv("BOT_OWNER", 0))

# Userbot String Session (for voice chat streaming)
STRING_SESSION = os.getenv("STRING_SESSION", "")

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
os.makedirs(CACHE_DIR, exist_ok=True)

AUDIO_QUALITY = os.getenv("AUDIO_QUALITY", "192")

def check_config():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set in .env file")
    if not API_ID or API_ID == 0:
        raise ValueError("API_ID not set in .env file")
    if not API_HASH:
        raise ValueError("API_HASH not set in .env file")
    if not BOT_OWNER or BOT_OWNER == 0:
        raise ValueError("BOT_OWNER not set in .env file")
        STRING_SESSION = os.getenv("STRING_SESSION", "")
