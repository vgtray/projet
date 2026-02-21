import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# --- API Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# --- Reddit ---
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "trade_bot/1.0")

# --- PostgreSQL ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "trade")
DB_USER = os.getenv("DB_USER", "adam")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# --- MetaTrader 5 ---
MT5_HOST = os.getenv("MT5_HOST", "localhost")
MT5_PORT = int(os.getenv("MT5_PORT", "8001"))

# --- n8n ---
N8N_URL = os.getenv("N8N_URL", "https://n8n.vjuya.me")

# --- Constantes métier ---
ASSETS = ["XAUUSD", "NAS100"]
TIMEFRAME = "M5"
RISK_PERCENT = 0.01
MAX_TRADES_PER_DAY = 2
CANDLE_CHECK_INTERVAL = 10
MONITOR_INTERVAL = 30

# Sessions (heure Paris)
NY_SESSION_START = "14:30"
NY_SESSION_END = "21:00"
ASIA_START = "00:00"
ASIA_END = "09:00"
LONDON_START = "09:00"
LONDON_END = "14:30"

TIMEZONE = "Europe/Paris"

DEDUP_WINDOW_MINUTES = 15
CANDLES_COUNT = 20
RETRY_MAX = 3
RETRY_BACKOFF = [30, 60, 120]
