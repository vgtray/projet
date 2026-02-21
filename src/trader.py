import logging
from datetime import datetime, time

from zoneinfo import ZoneInfo

from . import config
from . import database

logger = logging.getLogger(__name__)

PARIS_TZ = ZoneInfo(config.TIMEZONE)
NY_START = time(14, 30)
NY_END = time(21, 0)


class Trader:

    def __init__(self, mt5_client, risk_manager, db=None):
        self.mt5 = mt5_client
        self.risk = risk_manager
        self.db = db or database

    # ------------------------------------------------------------------
    # Point d'entrée
    # ------------------------------------------------------------------

    def execute_if_valid(self, signal: dict, signal_id: int) -> bool:
        """Reçoit le signal JSON de Groq + son signal_id déjà persisté, vérifie les conditions, exécute si valide."""
        symbol = signal.get("asset", "UNKNOWN")

        # 1. trade_valid
        if not signal.get("trade_valid"):
            logger.info("trade_valid: false → skip (%s)", signal.get("reason", ""))
            return False

        # 2. Session NY
        if not self._is_ny_session():
            logger.info("hors session NY → skip")
            return False

        # 3. Limite journalière
        if not self._check_daily_limit(symbol):
            count = self.db.get_daily_trade_count(symbol, datetime.now(PARIS_TZ).date())
            logger.info("limite journalière atteinte (%d/%d) → skip", count, config.MAX_TRADES_PER_DAY)
            return False

        # 4. Déduplication
        if self._check_duplicate(signal):
            logger.info("signal dupliqué → skip")
            return False

        # 5. Lot size
        entry_price = signal.get("entry_price")
        sl_price = signal.get("sl_price")
        tp_price = signal.get("tp_price")

        if entry_price is None or sl_price is None or tp_price is None:
            logger.warning("Prix manquants dans le signal (entry/sl/tp) → skip")
            return False

        # 6. RR viable
        rr = self.risk.validate_rr(entry_price, sl_price, tp_price)
        if rr < 1.5:
            logger.info("RR insuffisant (%.2f < 1.5) → skip", rr)
            return False

        lot_size = self.risk.calculate_lot_size(symbol, entry_price, sl_price)

        # 7. Placer et sauvegarder (signal déjà en DB via main.py)
        return self._place_and_save(signal, signal_id, lot_size)

    # ------------------------------------------------------------------
    # Vérifications
    # ------------------------------------------------------------------

    def _is_ny_session(self) -> bool:
        """Vérifie si on est dans la session New York (14h30-21h00 heure Paris)."""
        now_paris = datetime.now(PARIS_TZ).time()
        return NY_START <= now_paris <= NY_END

    def _check_daily_limit(self, symbol: str) -> bool:
        """Retourne True si on peut encore trader (compteur < MAX)."""
        today = datetime.now(PARIS_TZ).date()
        count = self.db.get_daily_trade_count(symbol, today)
        return count < config.MAX_TRADES_PER_DAY

    def _check_duplicate(self, signal: dict) -> bool:
        """Retourne True si c'est un doublon (ne pas trader)."""
        return self.db.check_duplicate_signal(
            asset=signal.get("asset", ""),
            direction=signal.get("direction", ""),
            sweep_level=signal.get("sweep_level", ""),
        )

    # ------------------------------------------------------------------
    # Exécution
    # ------------------------------------------------------------------

    def _place_and_save(self, signal: dict, signal_id: int, lot_size: float) -> bool:
        """Place l'ordre MT5 et sauvegarde le trade en DB."""
        symbol = signal["asset"]
        direction = signal["direction"]
        entry_price = signal["entry_price"]
        sl_price = signal["sl_price"]
        tp_price = signal["tp_price"]

        result = self.mt5.place_order(
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
        )

        if not result.get("success"):
            logger.error(
                "Ordre MT5 rejeté pour %s %s : %s",
                symbol, direction, result.get("error"),
            )
            return False

        # Sauvegarder le trade en DB (avec le ticket MT5 pour matching fiable)
        mt5_ticket = result.get("ticket")
        trade_data = {
            "asset": symbol,
            "mt5_ticket": mt5_ticket,
            "entry_time": datetime.now(PARIS_TZ),
            "direction": direction,
            "entry_price": entry_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "lot_size": lot_size,
        }
        trade_id = self.db.save_trade(signal_id, trade_data)

        logger.info(
            "Trade exécuté: %s %s | Entry: %.5f | SL: %.5f | TP: %.5f | Lot: %.5f | Trade #%s",
            symbol, direction.upper(), entry_price, sl_price, tp_price, lot_size,
            trade_id or "?",
        )
        return True

