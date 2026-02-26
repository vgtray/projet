"""Module de persistance PostgreSQL pour le bot de trading SMC/ICT.

Gère toutes les opérations CRUD sur les tables signals, trades,
performance_stats, daily_trade_counts et bot_state.
"""

import os
import time
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

from src.config import Config

logger = logging.getLogger(__name__)


class Database:
    """Connexion et opérations PostgreSQL avec retry et backoff exponentiel."""

    def __init__(self):
        self.conn = None

    def connect(self) -> None:
        """Ouvre la connexion PostgreSQL avec retry (3 tentatives, backoff exponentiel)."""
        for attempt in range(Config.RETRY_MAX):
            try:
                self.conn = psycopg2.connect(
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    dbname=Config.DB_NAME,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                )
                self.conn.autocommit = True
                logger.info("Connexion PostgreSQL établie")
                return
            except psycopg2.Error as e:
                wait = Config.RETRY_BACKOFF[attempt]
                logger.error("Connexion PostgreSQL échouée (tentative %d/%d) : %s — retry dans %ds",
                             attempt + 1, Config.RETRY_MAX, e, wait)
                if attempt < Config.RETRY_MAX - 1:
                    time.sleep(wait)
        logger.error("Connexion PostgreSQL impossible après %d tentatives", Config.RETRY_MAX)

    def disconnect(self) -> None:
        """Ferme la connexion PostgreSQL."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("Connexion PostgreSQL fermée")

    def init_schema(self) -> None:
        """Exécute le fichier sql/init.sql pour créer les tables."""
        sql_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sql", "init.sql")
        try:
            with open(sql_path, "r", encoding="utf-8") as f:
                sql = f.read()
            with self.conn.cursor() as cur:
                cur.execute(sql)
            logger.info("Schéma PostgreSQL initialisé")
        except Exception as e:
            logger.error("Erreur lors de l'initialisation du schéma : %s", e)

    def save_signal(self, signal: dict) -> Optional[int]:
        """Insère un signal dans la table signals et retourne l'id."""
        sql = """
            INSERT INTO signals
                (asset, timestamp, direction, scenario, confidence,
                 entry_price, sl_price, tp_price, rr_ratio,
                 confluences_used, sweep_level, news_sentiment,
                 social_sentiment, trade_valid, reason, executed, llm_used)
            VALUES
                (%(asset)s, %(timestamp)s, %(direction)s, %(scenario)s, %(confidence)s,
                 %(entry_price)s, %(sl_price)s, %(tp_price)s, %(rr_ratio)s,
                 %(confluences_used)s, %(sweep_level)s, %(news_sentiment)s,
                 %(social_sentiment)s, %(trade_valid)s, %(reason)s, %(executed)s, %(llm_used)s)
            RETURNING id
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, signal)
                row = cur.fetchone()
                signal_id = row[0] if row else None
                logger.info("Signal sauvegardé id=%s asset=%s direction=%s",
                            signal_id, signal.get("asset"), signal.get("direction"))
                return signal_id
        except Exception as e:
            logger.error("Erreur sauvegarde signal : %s", e)
            return None

    def save_trade(self, trade: dict) -> Optional[int]:
        """Insère un trade dans la table trades et retourne l'id."""
        sql = """
            INSERT INTO trades
                (signal_id, asset, entry_time, direction,
                 entry_price, sl_price, tp_price, lot_size, mt5_ticket, status)
            VALUES
                (%(signal_id)s, %(asset)s, %(entry_time)s, %(direction)s,
                 %(entry_price)s, %(sl_price)s, %(tp_price)s, %(lot_size)s, %(mt5_ticket)s, %(status)s)
            RETURNING id
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, trade)
                row = cur.fetchone()
                trade_id = row[0] if row else None
                logger.info("Trade sauvegardé id=%s asset=%s direction=%s",
                            trade_id, trade.get("asset"), trade.get("direction"))
                return trade_id
        except Exception as e:
            logger.error("Erreur sauvegarde trade : %s", e)
            return None

    def update_trade(self, trade_id: int, updates: dict) -> None:
        """Met à jour un trade existant (exit_price, pnl, status, etc.)."""
        if not updates:
            return
        set_clauses = ", ".join(f"{k} = %({k})s" for k in updates)
        sql = f"UPDATE trades SET {set_clauses} WHERE id = %(trade_id)s"
        updates["trade_id"] = trade_id
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, updates)
            logger.info("Trade id=%s mis à jour : %s", trade_id, list(updates.keys()))
        except Exception as e:
            logger.error("Erreur mise à jour trade id=%s : %s", trade_id, e)

    def get_daily_trade_count(self, asset: str, trade_date: date) -> int:
        """Retourne le nombre de trades fermés pour un asset à une date donnée."""
        sql = """
            SELECT closed_trades FROM daily_trade_counts
            WHERE asset = %s AND trade_date = %s
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (asset, trade_date))
                row = cur.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error("Erreur lecture daily_trade_count : %s", e)
            return 0

    def increment_daily_trade_count(self, asset: str, trade_date: date) -> None:
        """Incrémente le compteur de trades fermés pour un asset à une date."""
        sql = """
            INSERT INTO daily_trade_counts (asset, trade_date, closed_trades)
            VALUES (%s, %s, 1)
            ON CONFLICT (asset, trade_date)
            DO UPDATE SET closed_trades = daily_trade_counts.closed_trades + 1
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (asset, trade_date))
            logger.info("Compteur journalier incrémenté pour %s le %s", asset, trade_date)
        except Exception as e:
            logger.error("Erreur incrément daily_trade_count : %s", e)

    def check_duplicate_trade(self, asset: str, direction: str,
                               window_minutes: int = 15) -> bool:
        """Retourne True si un trade exécuté existe dans la fenêtre de déduplication.

        Vérifie deux conditions (OR) :
        1. Même asset + direction dans les X dernières minutes (status='open')
        2. Même asset + direction + sweep_level dans les X dernières minutes
        """
        sql_open_trade = """
            SELECT COUNT(*) FROM trades
            WHERE asset = %s
              AND direction = %s
              AND status = 'open'
        """
        sql_dedup = """
            SELECT COUNT(*) FROM signals
            WHERE asset = %s
              AND direction = %s
              AND executed = TRUE
              AND timestamp > NOW() - (%s * INTERVAL '1 minute')
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql_open_trade, (asset, direction))
                row = cur.fetchone()
                if row and row[0] > 0:
                    logger.info("Duplicate détecté (trade ouvert même direction) — %s %s", asset, direction)
                    return True

                cur.execute(sql_dedup, (asset, direction, window_minutes))
                row = cur.fetchone()
                if row and row[0] > 0:
                    logger.info("Duplicate détecté (signal exécuté récent) — %s %s", asset, direction)
                    return True

                return False
        except Exception as e:
            logger.error("Erreur vérification doublon trade : %s", e)
            return False

    def get_performance_stats(self, pattern_type: str, asset: str) -> Optional[dict]:
        """Retourne les stats de performance pour un pattern et un asset."""
        sql = """
            SELECT total_trades, winning_trades, losing_trades,
                   win_rate, avg_rr, total_pnl
            FROM performance_stats
            WHERE pattern_type = %s AND asset = %s
        """
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (pattern_type, asset))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error("Erreur lecture performance_stats : %s", e)
            return None

    def update_performance_stats(self, pattern_type: str, asset: str,
                                 won: bool, rr: float, pnl: float) -> None:
        """Met à jour les stats de performance après la clôture d'un trade."""
        sql = """
            INSERT INTO performance_stats
                (pattern_type, asset, total_trades, winning_trades, losing_trades,
                 win_rate, avg_rr, total_pnl, last_updated)
            VALUES
                (%s, %s, 1,
                 CASE WHEN %s THEN 1 ELSE 0 END,
                 CASE WHEN %s THEN 0 ELSE 1 END,
                 CASE WHEN %s THEN 100.0 ELSE 0.0 END,
                 %s, %s, NOW())
            ON CONFLICT (pattern_type, asset)
            DO UPDATE SET
                total_trades = performance_stats.total_trades + 1,
                winning_trades = performance_stats.winning_trades + CASE WHEN %s THEN 1 ELSE 0 END,
                losing_trades = performance_stats.losing_trades + CASE WHEN %s THEN 0 ELSE 1 END,
                win_rate = (
                    (performance_stats.winning_trades + CASE WHEN %s THEN 1 ELSE 0 END)::DECIMAL
                    / (performance_stats.total_trades + 1) * 100
                ),
                avg_rr = (
                    (performance_stats.avg_rr * performance_stats.total_trades + %s)
                    / (performance_stats.total_trades + 1)
                ),
                total_pnl = performance_stats.total_pnl + %s,
                last_updated = NOW()
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (
                    pattern_type, asset,
                    won, won, won, rr, pnl,
                    won, won, won, rr, pnl,
                ))
            logger.info("Performance stats mises à jour : pattern=%s asset=%s won=%s", pattern_type, asset, won)
        except Exception as e:
            logger.error("Erreur mise à jour performance_stats : %s", e)

    def get_bot_state(self, key: str) -> Optional[str]:
        """Retourne la valeur d'une clé dans bot_state."""
        sql = "SELECT value FROM bot_state WHERE key = %s"
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (key,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error("Erreur lecture bot_state key=%s : %s", key, e)
            return None

    def set_bot_state(self, key: str, value: str) -> None:
        """Insère ou met à jour une clé dans bot_state."""
        sql = """
            INSERT INTO bot_state (key, value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (key)
            DO UPDATE SET value = %s, updated_at = NOW()
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (key, value, value))
            logger.info("bot_state mis à jour : %s", key)
        except Exception as e:
            logger.error("Erreur écriture bot_state key=%s : %s", key, e)

    def get_open_trades(self) -> List[dict]:
        """Retourne tous les trades avec status='open'."""
        sql = """
            SELECT id, signal_id, asset, entry_time, direction,
                   entry_price, sl_price, tp_price, lot_size, mt5_ticket, status
            FROM trades
            WHERE status = 'open'
        """
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error("Erreur lecture trades ouverts : %s", e)
            return []

    def save_log(self, level: str, message: str) -> None:
        """Insère une ligne de log dans bot_logs."""
        if not self.conn or self.conn.closed:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO bot_logs (level, message) VALUES (%s, %s)",
                    (level, message)
                )
        except Exception:
            pass  # Ne jamais crasher à cause du logging
