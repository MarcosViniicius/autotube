import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Real Oficial API
    REAL_API_EMAIL = os.getenv("REAL_API_EMAIL")
    REAL_API_PASSWORD = os.getenv("REAL_API_PASSWORD")
    REAL_API_TOKEN = os.getenv("REAL_API_TOKEN")
    REAL_API_BASE_URL = os.getenv("REAL_API_BASE_URL", "https://api.realoficial.com.br/api/v1")

    # OpenRouter API (AI)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-001")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # YouTube API
    YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")

    # System Config
    MODO_DEFAULT = os.getenv("MODO_DEFAULT", "manual")
    CRON_INTERVAL = int(os.getenv("CRON_INTERVAL", 30))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "downloads/")
