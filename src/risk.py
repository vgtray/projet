import logging
import math

from . import config

logger = logging.getLogger(__name__)


class RiskManager:

    def __init__(self, mt5_client):
        self.mt5 = mt5_client

    # ------------------------------------------------------------------
    # Lot size
    # ------------------------------------------------------------------

    def calculate_lot_size(self, symbol: str, entry_price: float, sl_price: float) -> float:
        """Calcule le lot size pour risquer exactement 1 % du capital."""
        try:
            account = self.mt5.get_account_info()
            if account is None:
                raise ValueError("Impossible de récupérer les infos du compte")

            sym_info = self.mt5.get_symbol_info(symbol)
            if sym_info is None:
                raise ValueError(f"Impossible de récupérer les infos du symbole {symbol}")

            capital = account["balance"]
            tick_size = sym_info["trade_tick_size"]
            pip_value = sym_info["trade_tick_value"]
            volume_min = sym_info["volume_min"]
            volume_max = sym_info["volume_max"]
            volume_step = sym_info["volume_step"]

            distance_sl_pips = abs(entry_price - sl_price) / tick_size

            if distance_sl_pips == 0 or pip_value == 0:
                logger.warning("Distance SL ou pip_value nul pour %s, fallback volume_min", symbol)
                return volume_min

            lot_size = (capital * config.RISK_PERCENT) / (distance_sl_pips * pip_value)
            lot_size = self._round_to_step(lot_size, volume_step)
            lot_size = max(volume_min, min(volume_max, lot_size))

            logger.info(
                "Lot size calculé pour %s : %.5f lots — capital=%.2f, SL_pips=%.1f, pip_value=%.4f",
                symbol, lot_size, capital, distance_sl_pips, pip_value,
            )
            return lot_size

        except Exception as exc:
            logger.error("Erreur calcul lot size pour %s : %s — fallback safe", symbol, exc)
            # Fallback : tenter de récupérer volume_min
            try:
                info = self.mt5.get_symbol_info(symbol)
                if info is not None:
                    return info["volume_min"]
            except Exception:
                pass
            return 0.01

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _round_to_step(self, value: float, step: float) -> float:
        """Arrondit une valeur au step le plus proche (arrondi inférieur)."""
        if step <= 0:
            return value
        return math.floor(value / step) * step

    def validate_rr(self, entry_price: float, sl_price: float, tp_price: float) -> float:
        """Calcule et retourne le ratio Risk/Reward."""
        risk = abs(sl_price - entry_price)
        if risk == 0:
            return 0.0
        reward = abs(tp_price - entry_price)
        return reward / risk

    def is_trade_viable(self, entry_price: float, sl_price: float, tp_price: float,
                        min_rr: float = 1.5) -> bool:
        """Vérifie si le trade est viable (RR >= min_rr)."""
        rr = self.validate_rr(entry_price, sl_price, tp_price)
        return rr >= min_rr
