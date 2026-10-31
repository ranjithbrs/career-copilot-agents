import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory for the career copilot project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if it exists
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

# LLM Configurations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Email Configurations
EMAIL_HOST = os.getenv("EMAIL_HOST", "imap.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "993"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

# Database
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "data/hub.db")

# Telegram / Notifications (Phase 2)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# General
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
