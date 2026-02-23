"""Calcul des niveaux clés de la journée (Asia, London, Previous Day).

Niveaux fixes calculés une fois au début de la session NY et cachés.
Ref: SPEC.md section 3 — Niveaux clés.
"""

import logging
from datetime import date as date_type, datetime, timedelta, time as dtime
from typing import Optional, Union

import pandas as pd
import pytz

logger = logging.getLogger(__name__)

PARIS_TZ = pytz.timezone("Europe/Paris")

ASIA_START = dtime(0, 0)
ASIA_END = dtime(9, 0)
LONDON_START = dtime(9, 0)
LONDON_END = dtime(14, 30)


class KeyLevels:
    """Calcule et cache les niveaux clés fixes de la journée."""

    def __init__(self):
        self._cache: dict = {}
        self._cache_date: Optional[date_type] = None

    def calculate_all(self, candles_df: pd.DataFrame, current_time_paris: datetime) -> dict:
        """Calcule tous les niveaux clés pour la journée courante.

        Les niveaux sont cachés : un seul calcul par jour.

        Args:
            candles_df: DataFrame OHLCV avec colonne 'time' aware Europe/Paris.
            current_time_paris: Heure actuelle en Europe/Paris.

        Returns:
            Dictionnaire avec asia_high, asia_low, london_high, london_low,
            prev_day_high, prev_day_low. None si données insuffisantes.
        """
        today = current_time_paris.date()

        if self._cache_date == today and self._cache:
            logger.debug("Niveaux clés servis depuis le cache pour %s", today)
            return self._cache

        logger.info("Calcul des niveaux clés pour %s", today)

        asia = self._get_asia_range(candles_df, today)
        london = self._get_london_range(candles_df, today)
        prev_day = self._get_previous_day_range(candles_df, today)

        asia_high, asia_low = self._extract_high_low(asia, "Asia")
        london_high, london_low = self._extract_high_low(london, "London")
        prev_high, prev_low = self._extract_high_low(prev_day, "Previous Day")

        self._cache = {
            "asia_high": asia_high,
            "asia_low": asia_low,
            "london_high": london_high,
            "london_low": london_low,
            "prev_day_high": prev_high,
            "prev_day_low": prev_low,
        }
        self._cache_date = today

        logger.info(
            "Niveaux clés calculés — Asia H/L: %s/%s | London H/L: %s/%s | PrevDay H/L: %s/%s",
            asia_high, asia_low, london_high, london_low, prev_high, prev_low,
        )

        return self._cache

    def _get_asia_range(self, candles_df: pd.DataFrame, date) -> pd.DataFrame:
        """Filtre les bougies de la session Asia (00:00-09:00 Paris).

        Args:
            candles_df: DataFrame OHLCV.
            date: Date du jour.

        Returns:
            DataFrame filtré sur la plage Asia.
        """
        start = PARIS_TZ.localize(datetime.combine(date, ASIA_START))
        end = PARIS_TZ.localize(datetime.combine(date, ASIA_END))
        return self._filter_range(candles_df, start, end)

    def _get_london_range(self, candles_df: pd.DataFrame, date) -> pd.DataFrame:
        """Filtre les bougies de la session London (09:00-14:30 Paris).

        Args:
            candles_df: DataFrame OHLCV.
            date: Date du jour.

        Returns:
            DataFrame filtré sur la plage London.
        """
        start = PARIS_TZ.localize(datetime.combine(date, LONDON_START))
        end = PARIS_TZ.localize(datetime.combine(date, LONDON_END))
        return self._filter_range(candles_df, start, end)

    def _get_previous_day_range(self, candles_df: pd.DataFrame, date) -> pd.DataFrame:
        """Filtre les bougies de la veille complète (00:00-23:59:59).

        Args:
            candles_df: DataFrame OHLCV.
            date: Date du jour (la veille sera date - 1 jour).

        Returns:
            DataFrame filtré sur la veille.
        """
        prev_date = date - timedelta(days=1)
        start = PARIS_TZ.localize(datetime.combine(prev_date, dtime(0, 0)))
        end = PARIS_TZ.localize(datetime.combine(prev_date, dtime(23, 59, 59)))
        return self._filter_range(candles_df, start, end)

    def detect_sweep(
        self, current_price: float, key_levels: dict, candles_df: pd.DataFrame
    ) -> dict:
        """Détecte si le prix a dépassé un niveau clé (sweep de liquidité).

        Un sweep se produit quand le prix dépasse un high ou un low clé,
        prenant les stops des traders piégés.

        Args:
            current_price: Prix actuel de l'asset.
            key_levels: Dictionnaire des niveaux clés (output de calculate_all).
            candles_df: DataFrame OHLCV récent pour vérifier le dépassement.

        Returns:
            {"swept": bool, "level": str|None, "direction": "above"|"below"|None}
        """
        no_sweep = {"swept": False, "level": None, "direction": None}

        if not candles_df.empty and len(candles_df) >= 2:
            recent_high = candles_df["high"].iloc[-3:].max() if len(candles_df) >= 3 else candles_df["high"].max()
            recent_low = candles_df["low"].iloc[-3:].min() if len(candles_df) >= 3 else candles_df["low"].min()
        else:
            recent_high = current_price
            recent_low = current_price

        high_levels = {
            "asia_high": key_levels.get("asia_high"),
            "london_high": key_levels.get("london_high"),
            "prev_day_high": key_levels.get("prev_day_high"),
        }

        low_levels = {
            "asia_low": key_levels.get("asia_low"),
            "london_low": key_levels.get("london_low"),
            "prev_day_low": key_levels.get("prev_day_low"),
        }

        for level_name, level_value in high_levels.items():
            if level_value is None:
                continue
            if recent_high > level_value >= candles_df["high"].iloc[0] if len(candles_df) > 0 else False:
                logger.info("Sweep détecté au-dessus de %s (%.5f)", level_name, level_value)
                return {"swept": True, "level": level_name, "direction": "above"}

        for level_name, level_value in low_levels.items():
            if level_value is None:
                continue
            if recent_low < level_value <= candles_df["low"].iloc[0] if len(candles_df) > 0 else False:
                logger.info("Sweep détecté en dessous de %s (%.5f)", level_name, level_value)
                return {"swept": True, "level": level_name, "direction": "below"}

        return no_sweep

    @staticmethod
    def _filter_range(
        candles_df: pd.DataFrame, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Filtre un DataFrame de bougies sur une plage horaire.

        Args:
            candles_df: DataFrame avec colonne 'time' datetime aware.
            start: Début de la plage (inclus).
            end: Fin de la plage (exclus).

        Returns:
            DataFrame filtré.
        """
        if candles_df.empty:
            return candles_df
        mask = (candles_df["time"] >= start) & (candles_df["time"] < end)
        return candles_df.loc[mask]

    @staticmethod
    def _extract_high_low(
        range_df: pd.DataFrame, label: str
    ) -> tuple[Optional[float], Optional[float]]:
        """Extrait le high et le low d'un DataFrame filtré.

        Args:
            range_df: DataFrame filtré sur une session.
            label: Nom de la session pour le logging.

        Returns:
            Tuple (high, low) ou (None, None) si pas de données.
        """
        if range_df.empty:
            logger.warning("Pas de données pour la session %s — niveaux à None", label)
            return None, None
        return float(range_df["high"].max()), float(range_df["low"].min())
