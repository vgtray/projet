import logging
from datetime import datetime, timedelta

from zoneinfo import ZoneInfo

from . import config
from . import database

logger = logging.getLogger(__name__)

PARIS_TZ = ZoneInfo(config.TIMEZONE)
UTC_TZ = ZoneInfo("UTC")

# Tolérance pour déterminer si exit_price correspond au TP ou SL (0.1%)
PRICE_TOLERANCE = 0.001


class TradeMonitor:

    def __init__(self, mt5_client, db=None):
        self.mt5 = mt5_client
        self.db = db or database

    # ------------------------------------------------------------------
    # Point d'entrée
    # ------------------------------------------------------------------

    def check_open_trades(self):
        """Vérifie les trades ouverts et détecte les fermetures (TP/SL)."""
        try:
            open_trades_db = self.db.get_open_trades()
        except Exception as exc:
            logger.error("DB indisponible pour récupérer les trades ouverts : %s", exc)
            return

        if not open_trades_db:
            return

        try:
            mt5_positions = self.mt5.get_open_positions()
        except Exception as exc:
            logger.error("MT5 indisponible pour récupérer les positions : %s", exc)
            return

        mt5_tickets = {p["ticket"] for p in mt5_positions}

        for trade_db in open_trades_db:
            try:
                self._process_trade(trade_db, mt5_tickets)
            except Exception as exc:
                logger.error(
                    "Erreur traitement trade #%s : %s",
                    trade_db.get("id"), exc,
                )

    # ------------------------------------------------------------------
    # Traitement d'un trade
    # ------------------------------------------------------------------

    def _process_trade(self, trade_db: dict, mt5_tickets: set):
        """Vérifie si un trade DB est encore ouvert côté MT5 (matching par ticket)."""
        symbol = trade_db["asset"]
        direction = trade_db["direction"]
        trade_id = trade_db["id"]
        mt5_ticket = trade_db.get("mt5_ticket")

        # Matching fiable par ticket MT5
        if mt5_ticket and mt5_ticket in mt5_tickets:
            return  # Position encore ouverte, rien à faire

        # Fallback si pas de ticket (anciens trades sans mt5_ticket)
        if mt5_ticket is None:
            logger.warning(
                "Trade #%d sans mt5_ticket — impossible de matcher fiablement, skip",
                trade_id,
            )
            return

        # La position n'existe plus → trade fermé
        closed_info = self._get_closed_trade_info(symbol, trade_db["entry_time"])

        if closed_info is None:
            # Pas d'info dans l'historique, utiliser les données DB
            logger.warning(
                "Trade #%d fermé mais infos historique MT5 introuvables, estimation depuis DB",
                trade_id,
            )
            exit_price = float(trade_db.get("tp_price") or trade_db["entry_price"])
            profit = 0.0
        else:
            exit_price = closed_info["exit_price"]
            profit = closed_info["profit"]

        closed_reason = self._determine_close_reason(trade_db, exit_price, profit)

        # Mettre à jour en DB
        self.db.update_trade_closed(trade_id, exit_price, profit, closed_reason)

        # Incrémenter le compteur journalier
        today = datetime.now(PARIS_TZ).date()
        self.db.increment_daily_trade_count(symbol, today)

        # Mettre à jour les stats de performance
        self._update_performance_stats(trade_db, profit, closed_reason)

        pnl_sign = "+" if profit >= 0 else ""
        logger.info(
            "Trade fermé: %s %s | Entry: %.5f | Exit: %.5f | PnL: %s%.2f$ | Raison: %s",
            symbol, direction.upper(),
            float(trade_db["entry_price"]), exit_price,
            pnl_sign, profit, closed_reason,
        )

    # ------------------------------------------------------------------
    # Historique MT5
    # ------------------------------------------------------------------

    def _get_closed_trade_info(self, symbol: str, open_time: datetime) -> dict | None:
        """Récupère les infos d'un trade fermé depuis l'historique MT5."""
        try:
            if not self.mt5._ensure_connected():
                return None

            # Chercher dans l'historique depuis l'ouverture du trade
            if open_time.tzinfo is None:
                dt_from = open_time.replace(tzinfo=PARIS_TZ).astimezone(UTC_TZ)
            else:
                dt_from = open_time.astimezone(UTC_TZ)

            dt_to = datetime.now(UTC_TZ) + timedelta(hours=1)

            deals = self.mt5.mt5.history_deals_get(dt_from, dt_to, group=f"*{symbol}*")
            if deals is None or len(deals) == 0:
                return None

            # Chercher le deal de sortie le plus récent (DEAL_ENTRY_OUT = 1)
            for deal in reversed(deals):
                entry_type = getattr(deal, "entry", None)
                # entry == 1 → sortie de position
                if entry_type == 1:
                    close_time_utc = datetime.fromtimestamp(deal.time, tz=UTC_TZ)
                    return {
                        "exit_price": float(deal.price),
                        "profit": float(deal.profit),
                        "close_time": close_time_utc.astimezone(PARIS_TZ),
                    }

            return None

        except Exception as exc:
            logger.error("Erreur récupération historique MT5 pour %s : %s", symbol, exc)
            return None

    # ------------------------------------------------------------------
    # Raison de fermeture
    # ------------------------------------------------------------------

    def _determine_close_reason(self, trade_db: dict, exit_price: float, profit: float) -> str:
        """Détermine la raison de fermeture : tp, sl, ou manual."""
        tp_price = trade_db.get("tp_price")
        sl_price = trade_db.get("sl_price")

        if tp_price is not None:
            tp_float = float(tp_price)
            if tp_float != 0 and abs(exit_price - tp_float) / tp_float <= PRICE_TOLERANCE:
                return "tp"

        if sl_price is not None:
            sl_float = float(sl_price)
            if sl_float != 0 and abs(exit_price - sl_float) / sl_float <= PRICE_TOLERANCE:
                return "sl"

        # Fallback basé sur le profit
        if profit > 0:
            return "tp"
        if profit <= 0:
            return "sl"

        return "manual"

    # ------------------------------------------------------------------
    # Stats de performance
    # ------------------------------------------------------------------

    def _update_performance_stats(self, trade_db: dict, profit: float, closed_reason: str):
        """Met à jour les stats de performance pour le pattern utilisé."""
        signal_id = trade_db.get("signal_id")
        symbol = trade_db["asset"]
        entry_price = float(trade_db["entry_price"])
        sl_price = float(trade_db.get("sl_price") or 0)
        tp_price = float(trade_db.get("tp_price") or 0)

        # Calculer le RR réalisé
        risk = abs(sl_price - entry_price)
        rr = abs(profit) / risk if risk > 0 and profit > 0 else 0.0

        won = closed_reason == "tp"

        # Récupérer le pattern_type depuis le signal associé
        pattern_type = self._get_pattern_type(signal_id)
        if not pattern_type:
            pattern_type = "unknown"

        self.db.update_performance_stats(
            asset=symbol,
            pattern_type=pattern_type,
            won=won,
            rr=rr,
            pnl=profit,
        )

    def _get_pattern_type(self, signal_id: int | None) -> str:
        """Récupère les confluences utilisées depuis la table signals."""
        if signal_id is None:
            return "unknown"

        conn = self.db.get_connection()
        if conn is None:
            return "unknown"
        try:
            with self.db.get_cursor(conn) as cur:
                cur.execute(
                    "SELECT confluences_used FROM signals WHERE id = %s",
                    (signal_id,),
                )
                row = cur.fetchone()
                if row and row["confluences_used"]:
                    confluences = row["confluences_used"]
                    if isinstance(confluences, list):
                        return "+".join(sorted(confluences))
                    return str(confluences)
                return "unknown"
        except Exception as exc:
            logger.error("Erreur récupération pattern_type (signal #%s) : %s", signal_id, exc)
            return "unknown"
        finally:
            conn.close()
