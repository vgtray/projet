import logging
from datetime import date, datetime, time, timedelta

from zoneinfo import ZoneInfo

from . import config

logger = logging.getLogger(__name__)

PARIS_TZ = ZoneInfo(config.TIMEZONE)


class LevelsCalculator:
    def __init__(self, mt5_client):
        self.mt5 = mt5_client
        self._cache: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def get_levels(self, symbol: str) -> dict:
        """Retourne les niveaux du jour pour le symbole (cache journalier)."""
        if self._is_cache_valid(symbol):
            return self._cache[symbol]

        today = datetime.now(PARIS_TZ).date()
        levels = self._calculate_levels(symbol, today)
        self._cache[symbol] = levels
        return levels

    def invalidate_cache(self, symbol: str = None):
        """Invalide le cache. Si symbol=None, invalide tout."""
        if symbol is None:
            self._cache.clear()
            logger.info("Cache niveaux invalidé (tous les symboles)")
        else:
            self._cache.pop(symbol, None)
            logger.info("Cache niveaux invalidé pour %s", symbol)

    # ------------------------------------------------------------------
    # Calcul
    # ------------------------------------------------------------------

    def _calculate_levels(self, symbol: str, today: date) -> dict:
        """Calcule les niveaux en récupérant les bougies via MT5."""
        empty = {
            "asia_high": None, "asia_low": None,
            "london_high": None, "london_low": None,
            "prev_day_high": None, "prev_day_low": None,
            "date": today.isoformat(),
        }

        # --- Asia : aujourd'hui 00:00 → 09:00 Paris ---
        asia_start = datetime.combine(today, time(0, 0), tzinfo=PARIS_TZ)
        asia_end = datetime.combine(today, time(9, 0), tzinfo=PARIS_TZ)
        asia_high, asia_low = self._session_high_low(symbol, asia_start, asia_end, "Asia")

        # --- London : aujourd'hui 09:00 → 14:30 Paris ---
        london_start = datetime.combine(today, time(9, 0), tzinfo=PARIS_TZ)
        london_end = datetime.combine(today, time(14, 30), tzinfo=PARIS_TZ)
        london_high, london_low = self._session_high_low(symbol, london_start, london_end, "London")

        # --- Previous Day : J-1 00:00 → 23:59 Paris ---
        yesterday = today - timedelta(days=1)
        prev_start = datetime.combine(yesterday, time(0, 0), tzinfo=PARIS_TZ)
        prev_end = datetime.combine(yesterday, time(23, 59), tzinfo=PARIS_TZ)
        prev_high, prev_low = self._session_high_low(symbol, prev_start, prev_end, "PrevDay")

        levels = {
            "asia_high": asia_high,
            "asia_low": asia_low,
            "london_high": london_high,
            "london_low": london_low,
            "prev_day_high": prev_high,
            "prev_day_low": prev_low,
            "date": today.isoformat(),
        }

        logger.info(
            "Niveaux calculés %s [%s] — Asia H/L: %s/%s | London H/L: %s/%s | PrevDay H/L: %s/%s",
            symbol, today,
            asia_high, asia_low,
            london_high, london_low,
            prev_high, prev_low,
        )
        return levels

    def _session_high_low(
        self, symbol: str, dt_from: datetime, dt_to: datetime, label: str
    ) -> tuple[float | None, float | None]:
        """Récupère high/low d'une session via MT5. Retourne (high, low) ou (None, None)."""
        try:
            candles = self.mt5.get_candles_range(symbol, dt_from, dt_to)
            if not candles:
                logger.warning("Pas de données %s pour %s (%s → %s)", label, symbol, dt_from, dt_to)
                return None, None

            high = max(c["high"] for c in candles)
            low = min(c["low"] for c in candles)
            return high, low
        except Exception as exc:
            logger.error("Erreur calcul %s pour %s : %s", label, symbol, exc)
            return None, None

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _is_cache_valid(self, symbol: str) -> bool:
        """Vérifie si le cache est encore valide (même jour Paris)."""
        if symbol not in self._cache:
            return False
        cached_date = self._cache[symbol].get("date")
        if cached_date is None:
            return False
        today_str = datetime.now(PARIS_TZ).date().isoformat()
        return cached_date == today_str
