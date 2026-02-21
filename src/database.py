import logging
import time
from datetime import date

import psycopg2
import psycopg2.extras

from . import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

def get_connection():
    """Retourne une connexion psycopg2. Retry avec backoff si échec."""
    for attempt in range(config.RETRY_MAX):
        try:
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
            )
            return conn
        except psycopg2.Error as exc:
            wait = config.RETRY_BACKOFF[attempt] if attempt < len(config.RETRY_BACKOFF) else config.RETRY_BACKOFF[-1]
            logger.error("Connexion PostgreSQL échouée (tentative %d/%d) : %s — retry dans %ds",
                         attempt + 1, config.RETRY_MAX, exc, wait)
            if attempt < config.RETRY_MAX - 1:
                time.sleep(wait)
    logger.critical("Impossible de se connecter à PostgreSQL après %d tentatives", config.RETRY_MAX)
    return None


def get_cursor(conn):
    """Retourne un cursor DictCursor."""
    return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


# ---------------------------------------------------------------------------
# Initialisation du schéma
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    direction VARCHAR(10),
    scenario VARCHAR(20),
    confidence INTEGER,
    entry_price DECIMAL(12,5),
    sl_price DECIMAL(12,5),
    tp_price DECIMAL(12,5),
    rr_ratio DECIMAL(5,2),
    confluences_used TEXT[],
    sweep_level VARCHAR(20),
    news_sentiment VARCHAR(10),
    social_sentiment VARCHAR(10),
    trade_valid BOOLEAN,
    reason TEXT,
    executed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_asset_timestamp ON signals(asset, timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_trade_valid ON signals(trade_valid);
CREATE INDEX IF NOT EXISTS idx_signals_recent_dedup ON signals(asset, direction, sweep_level, timestamp)
    WHERE timestamp > NOW() - INTERVAL '15 minutes';

CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    asset VARCHAR(10) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    direction VARCHAR(10) NOT NULL,
    entry_price DECIMAL(12,5) NOT NULL,
    exit_price DECIMAL(12,5),
    sl_price DECIMAL(12,5),
    tp_price DECIMAL(12,5),
    lot_size DECIMAL(10,5),
    pnl DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'open',
    closed_reason VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_signal_id ON trades(signal_id);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_asset_entry ON trades(asset, entry_time);

CREATE TABLE IF NOT EXISTS performance_stats (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    asset VARCHAR(10),
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2),
    avg_rr DECIMAL(5,2),
    total_pnl DECIMAL(15,2),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pattern_type, asset)
);

CREATE INDEX IF NOT EXISTS idx_perf_pattern_asset ON performance_stats(pattern_type, asset);

CREATE TABLE IF NOT EXISTS daily_trade_counts (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    closed_trades INTEGER DEFAULT 0,
    UNIQUE(asset, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_counts ON daily_trade_counts(asset, trade_date);

CREATE TABLE IF NOT EXISTS bot_state (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    value TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO bot_state (key, value) VALUES ('last_analyzed_XAUUSD', '')
ON CONFLICT (key) DO NOTHING;
INSERT INTO bot_state (key, value) VALUES ('last_analyzed_NAS100', '')
ON CONFLICT (key) DO NOTHING;
"""


def init_db():
    """Crée toutes les tables si elles n'existent pas."""
    conn = get_connection()
    if conn is None:
        return
    try:
        with get_cursor(conn) as cur:
            cur.execute(_SCHEMA_SQL)
        conn.commit()
        logger.info("Schéma DB initialisé avec succès")
    except psycopg2.Error as exc:
        logger.error("Erreur lors de l'initialisation du schéma : %s", exc)
        conn.rollback()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def save_signal(signal_data: dict) -> int | None:
    """Sauvegarde un signal en DB, retourne l'id créé."""
    conn = get_connection()
    if conn is None:
        return None
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                """INSERT INTO signals
                    (asset, timestamp, direction, scenario, confidence,
                     entry_price, sl_price, tp_price, rr_ratio,
                     confluences_used, sweep_level,
                     news_sentiment, social_sentiment,
                     trade_valid, reason, executed)
                   VALUES
                    (%(asset)s, %(timestamp)s, %(direction)s, %(scenario)s, %(confidence)s,
                     %(entry_price)s, %(sl_price)s, %(tp_price)s, %(rr_ratio)s,
                     %(confluences_used)s, %(sweep_level)s,
                     %(news_sentiment)s, %(social_sentiment)s,
                     %(trade_valid)s, %(reason)s, %(executed)s)
                   RETURNING id""",
                signal_data,
            )
            signal_id = cur.fetchone()[0]
        conn.commit()
        logger.info("Signal #%d sauvegardé (%s %s)", signal_id, signal_data.get("asset"), signal_data.get("direction"))
        return signal_id
    except psycopg2.Error as exc:
        logger.error("Erreur save_signal : %s", exc)
        conn.rollback()
        return None
    finally:
        conn.close()


def get_daily_trade_count(asset: str, trade_date: date) -> int:
    """Retourne le nombre de trades fermés aujourd'hui pour cet asset."""
    conn = get_connection()
    if conn is None:
        return 0
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                "SELECT closed_trades FROM daily_trade_counts WHERE asset = %s AND trade_date = %s",
                (asset, trade_date),
            )
            row = cur.fetchone()
            return row["closed_trades"] if row else 0
    except psycopg2.Error as exc:
        logger.error("Erreur get_daily_trade_count : %s", exc)
        return 0
    finally:
        conn.close()


def increment_daily_trade_count(asset: str, trade_date: date):
    """Incrémente le compteur journalier (INSERT ON CONFLICT DO UPDATE)."""
    conn = get_connection()
    if conn is None:
        return
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                """INSERT INTO daily_trade_counts (asset, trade_date, closed_trades)
                   VALUES (%s, %s, 1)
                   ON CONFLICT (asset, trade_date)
                   DO UPDATE SET closed_trades = daily_trade_counts.closed_trades + 1""",
                (asset, trade_date),
            )
        conn.commit()
        logger.info("Compteur journalier incrémenté pour %s le %s", asset, trade_date)
    except psycopg2.Error as exc:
        logger.error("Erreur increment_daily_trade_count : %s", exc)
        conn.rollback()
    finally:
        conn.close()


def get_last_analyzed_timestamp(asset: str) -> str:
    """Récupère le timestamp de la dernière bougie analysée depuis bot_state."""
    conn = get_connection()
    if conn is None:
        return ""
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                "SELECT value FROM bot_state WHERE key = %s",
                (f"last_analyzed_{asset}",),
            )
            row = cur.fetchone()
            return row["value"] if row else ""
    except psycopg2.Error as exc:
        logger.error("Erreur get_last_analyzed_timestamp : %s", exc)
        return ""
    finally:
        conn.close()


def set_last_analyzed_timestamp(asset: str, timestamp: str):
    """Met à jour le timestamp dans bot_state."""
    conn = get_connection()
    if conn is None:
        return
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                """UPDATE bot_state SET value = %s, updated_at = NOW()
                   WHERE key = %s""",
                (timestamp, f"last_analyzed_{asset}"),
            )
        conn.commit()
    except psycopg2.Error as exc:
        logger.error("Erreur set_last_analyzed_timestamp : %s", exc)
        conn.rollback()
    finally:
        conn.close()


def check_duplicate_signal(asset: str, direction: str, sweep_level: str) -> bool:
    """Vérifie si un signal identique existe dans les 15 dernières minutes."""
    conn = get_connection()
    if conn is None:
        return False
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                """SELECT COUNT(*) AS cnt FROM signals
                   WHERE asset = %s
                     AND direction = %s
                     AND sweep_level = %s
                     AND timestamp > NOW() - INTERVAL '%s minutes'""",
                (asset, direction, sweep_level, config.DEDUP_WINDOW_MINUTES),
            )
            row = cur.fetchone()
            return row["cnt"] > 0
    except psycopg2.Error as exc:
        logger.error("Erreur check_duplicate_signal : %s", exc)
        return False
    finally:
        conn.close()


def get_performance_stats(asset: str, pattern_type: str) -> dict | None:
    """Récupère les stats de performance pour un pattern donné."""
    conn = get_connection()
    if conn is None:
        return None
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                """SELECT total_trades, winning_trades, losing_trades,
                          win_rate, avg_rr, total_pnl
                   FROM performance_stats
                   WHERE asset = %s AND pattern_type = %s""",
                (asset, pattern_type),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except psycopg2.Error as exc:
        logger.error("Erreur get_performance_stats : %s", exc)
        return None
    finally:
        conn.close()


def update_performance_stats(asset: str, pattern_type: str, won: bool, rr: float, pnl: float):
    """Met à jour les stats de performance (INSERT ON CONFLICT DO UPDATE)."""
    conn = get_connection()
    if conn is None:
        return
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                """INSERT INTO performance_stats
                       (pattern_type, asset, total_trades, winning_trades, losing_trades,
                        win_rate, avg_rr, total_pnl, last_updated)
                   VALUES (%s, %s, 1, %s, %s, %s, %s, %s, NOW())
                   ON CONFLICT (pattern_type, asset) DO UPDATE SET
                       total_trades    = performance_stats.total_trades + 1,
                       winning_trades  = performance_stats.winning_trades + EXCLUDED.winning_trades,
                       losing_trades   = performance_stats.losing_trades + EXCLUDED.losing_trades,
                       win_rate        = ROUND(
                           (performance_stats.winning_trades + EXCLUDED.winning_trades)::numeric
                           / (performance_stats.total_trades + 1) * 100, 2),
                       avg_rr          = ROUND(
                           ((performance_stats.avg_rr * performance_stats.total_trades) + %s)
                           / (performance_stats.total_trades + 1), 2),
                       total_pnl       = performance_stats.total_pnl + %s,
                       last_updated    = NOW()""",
                (
                    pattern_type, asset,
                    1 if won else 0,
                    0 if won else 1,
                    100.0 if won else 0.0,
                    rr, pnl,
                    rr, pnl,
                ),
            )
        conn.commit()
        logger.info("Stats performance mises à jour : %s / %s (won=%s, rr=%.2f)", asset, pattern_type, won, rr)
    except psycopg2.Error as exc:
        logger.error("Erreur update_performance_stats : %s", exc)
        conn.rollback()
    finally:
        conn.close()


def save_trade(signal_id: int, trade_data: dict) -> int | None:
    """Sauvegarde un trade en DB, retourne l'id créé."""
    conn = get_connection()
    if conn is None:
        return None
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                """INSERT INTO trades
                    (signal_id, asset, entry_time, direction,
                     entry_price, sl_price, tp_price, lot_size, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'open')
                   RETURNING id""",
                (
                    signal_id,
                    trade_data["asset"],
                    trade_data["entry_time"],
                    trade_data["direction"],
                    trade_data["entry_price"],
                    trade_data["sl_price"],
                    trade_data["tp_price"],
                    trade_data["lot_size"],
                ),
            )
            trade_id = cur.fetchone()[0]
        conn.commit()
        logger.info("Trade #%d sauvegardé (signal #%d, %s %s)", trade_id, signal_id,
                     trade_data.get("asset"), trade_data.get("direction"))
        return trade_id
    except psycopg2.Error as exc:
        logger.error("Erreur save_trade : %s", exc)
        conn.rollback()
        return None
    finally:
        conn.close()


def update_trade_closed(trade_id: int, exit_price: float, pnl: float, closed_reason: str):
    """Met à jour un trade fermé (TP/SL/manuel)."""
    conn = get_connection()
    if conn is None:
        return
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                """UPDATE trades
                   SET exit_time = NOW(), exit_price = %s, pnl = %s,
                       status = 'closed', closed_reason = %s
                   WHERE id = %s""",
                (exit_price, pnl, closed_reason, trade_id),
            )
        conn.commit()
        logger.info("Trade #%d fermé (%s) — PnL : %.2f", trade_id, closed_reason, pnl)
    except psycopg2.Error as exc:
        logger.error("Erreur update_trade_closed : %s", exc)
        conn.rollback()
    finally:
        conn.close()


def get_open_trades() -> list:
    """Retourne tous les trades avec status='open'."""
    conn = get_connection()
    if conn is None:
        return []
    try:
        with get_cursor(conn) as cur:
            cur.execute(
                """SELECT id, signal_id, asset, entry_time, direction,
                          entry_price, sl_price, tp_price, lot_size
                   FROM trades WHERE status = 'open'"""
            )
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.Error as exc:
        logger.error("Erreur get_open_trades : %s", exc)
        return []
    finally:
        conn.close()
