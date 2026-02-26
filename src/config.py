"""Configuration centralisée du bot de trading SMC/ICT.

Charge les variables depuis .env et expose les constantes de la spec.
"""

import os
from datetime import time, datetime

import pytz
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


class Config:
    """Constantes et paramètres du bot, chargés depuis .env et la spec."""

    # --- Assets & Timeframe ---
    ASSETS = ["XAUUSD", "US100"]
    TIMEFRAME = "M5"

    # --- Risque ---
    RISK_PERCENT = 0.01
    MAX_TRADES_PER_DAY = 5

    # --- Timezone ---
    TIMEZONE = "Europe/Paris"
    TZ = pytz.timezone(TIMEZONE)

    # --- Sessions horaires (Europe/Paris) ---
    SESSION_ASIA_START = time(0, 0)
    SESSION_ASIA_END = time(9, 0)
    SESSION_LONDON_START = time(9, 0)
    SESSION_LONDON_END = time(14, 30)
    SESSION_NY_START = time(14, 30)
    SESSION_NY_END = time(21, 0)

    # --- Déduplication ---
    DEDUP_WINDOW_MINUTES = 15

    # --- LLM ---
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "10"))

    # --- Retry ---
    RETRY_MAX = 3
    RETRY_BACKOFF = [30, 60, 120]

    # --- MT5 ---
    BOT_MAGIC = 123456
    MAX_SLIPPAGE = 20

    # --- Claude API (principal) ---
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    # --- Groq API (fallback) ---
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # --- NewsAPI ---
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

    # --- Reddit ---
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "trade_bot/1.0")

    # --- Twitter/X (twscrape) ---
    TWITTER_USERNAME = os.getenv("TWITTER_USERNAME", "")
    TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "")
    TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", "")

    # --- PostgreSQL ---
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "trade")
    DB_USER = os.getenv("DB_USER", "adam")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # --- MetaTrader 5 ---
    MT5_HOST = os.getenv("MT5_HOST", "localhost")
    MT5_PORT = int(os.getenv("MT5_PORT", "8001"))

    @classmethod
    def is_ny_session(cls, dt: datetime) -> bool:
        """Retourne True si l'heure est dans la session New York (14h30-21h00 Paris)."""
        paris_dt = dt.astimezone(cls.TZ) if dt.tzinfo else cls.TZ.localize(dt)
        t = paris_dt.time()
        return cls.SESSION_NY_START <= t < cls.SESSION_NY_END

    @classmethod
    def get_session(cls, dt: datetime) -> str:
        """Retourne la session active : 'asia', 'london', 'new_york' ou 'closed'."""
        paris_dt = dt.astimezone(cls.TZ) if dt.tzinfo else cls.TZ.localize(dt)
        t = paris_dt.time()
        if cls.SESSION_ASIA_START <= t < cls.SESSION_ASIA_END:
            return "asia"
        if cls.SESSION_LONDON_START <= t < cls.SESSION_LONDON_END:
            return "london"
        if cls.SESSION_NY_START <= t < cls.SESSION_NY_END:
            return "new_york"
        return "closed"
