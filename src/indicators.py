"""Indicateurs techniques : RSI, MACD, EMA.

Utilise la librairie 'ta' pour les calculs.
Ref: SPEC.md section 10 — Données reçues à chaque analyse.
"""

import logging
from typing import Optional

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator

logger = logging.getLogger(__name__)


class Indicators:
    """Calcule RSI, MACD et EMA sur des bougies OHLCV."""

    def calculate_all(self, candles_df: pd.DataFrame) -> dict:
        """Calcule tous les indicateurs techniques.

        Args:
            candles_df: DataFrame OHLCV (colonnes: time, open, high, low, close, volume).

        Returns:
            Dictionnaire avec rsi, macd (dict), ema (dict).
        """
        return {
            "rsi": self.calculate_rsi(candles_df),
            "macd": self.calculate_macd(candles_df),
            "ema": self.calculate_ema(candles_df),
        }

    def calculate_rsi(self, candles_df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calcule la dernière valeur du RSI.

        Args:
            candles_df: DataFrame OHLCV.
            period: Période RSI (défaut 14).

        Returns:
            Dernière valeur RSI ou None si données insuffisantes.
        """
        if len(candles_df) < period + 1:
            logger.warning(
                "Pas assez de bougies pour RSI(%d) : %d disponibles",
                period, len(candles_df),
            )
            return None

        try:
            rsi = RSIIndicator(close=candles_df["close"], window=period)
            series = rsi.rsi()
            value = series.iloc[-1]
            if pd.isna(value):
                return None
            result = round(float(value), 2)
            logger.debug("RSI(%d) = %.2f", period, result)
            return result
        except Exception as e:
            logger.error("Erreur calcul RSI : %s", e)
            return None

    def calculate_macd(self, candles_df: pd.DataFrame) -> dict:
        """Calcule les dernières valeurs MACD (ligne, signal, histogramme).

        Args:
            candles_df: DataFrame OHLCV.

        Returns:
            {"macd": float|None, "signal": float|None, "histogram": float|None}
        """
        empty = {"macd": None, "signal": None, "histogram": None}

        if len(candles_df) < 26:
            logger.warning(
                "Pas assez de bougies pour MACD : %d disponibles (min 26)",
                len(candles_df),
            )
            return empty

        try:
            macd = MACD(close=candles_df["close"])
            macd_line = macd.macd().iloc[-1]
            signal_line = macd.macd_signal().iloc[-1]
            histogram = macd.macd_diff().iloc[-1]

            result = {
                "macd": round(float(macd_line), 5) if not pd.isna(macd_line) else None,
                "signal": round(float(signal_line), 5) if not pd.isna(signal_line) else None,
                "histogram": round(float(histogram), 5) if not pd.isna(histogram) else None,
            }
            logger.debug("MACD = %s", result)
            return result
        except Exception as e:
            logger.error("Erreur calcul MACD : %s", e)
            return empty

    def calculate_ema(
        self, candles_df: pd.DataFrame, periods: list[int] = None
    ) -> dict:
        """Calcule les dernières valeurs EMA pour les périodes demandées.

        Si le DataFrame ne contient pas assez de bougies pour une période
        donnée, la valeur correspondante est None.

        Args:
            candles_df: DataFrame OHLCV.
            periods: Liste des périodes EMA (défaut [20, 50, 200]).

        Returns:
            {"ema_20": float|None, "ema_50": float|None, "ema_200": float|None}
        """
        if periods is None:
            periods = [20, 50, 200]

        result = {}

        for period in periods:
            key = f"ema_{period}"

            if len(candles_df) < period:
                logger.warning(
                    "Pas assez de bougies pour EMA(%d) : %d disponibles",
                    period, len(candles_df),
                )
                result[key] = None
                continue

            try:
                ema = EMAIndicator(close=candles_df["close"], window=period)
                value = ema.ema_indicator().iloc[-1]
                if pd.isna(value):
                    result[key] = None
                else:
                    result[key] = round(float(value), 5)
                    logger.debug("EMA(%d) = %.5f", period, result[key])
            except Exception as e:
                logger.error("Erreur calcul EMA(%d) : %s", period, e)
                result[key] = None

        return result
