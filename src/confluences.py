"""Détection des confluences SMC/ICT : FVG, iFVG, OB, BB.

Travaille sur des bougies M5 (DataFrame OHLCV).
Ref: SPEC.md section 4 — Confluences valides.
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ConfluenceDetector:
    """Détecte les zones de confluence sur les bougies M5."""

    def detect_all(self, candles_df: pd.DataFrame) -> dict:
        """Détecte toutes les confluences sur le jeu de bougies.

        Args:
            candles_df: DataFrame OHLCV (colonnes: time, open, high, low, close, volume).

        Returns:
            Dictionnaire avec les listes de FVG, iFVG, OB, BB détectés.
        """
        fvg_list = self.detect_fvg(candles_df)
        ob_list = self.detect_ob(candles_df)

        return {
            "fvg": fvg_list,
            "ifvg": self.detect_ifvg(candles_df, fvg_list),
            "ob": ob_list,
            "bb": self.detect_bb(candles_df, ob_list),
        }

    def detect_fvg(self, candles_df: pd.DataFrame) -> list[dict]:
        """Détecte les Fair Value Gaps (FVG) sur 3 bougies consécutives.

        Un FVG est un gap entre la bougie i-2 et la bougie i, créé par le
        mouvement rapide de la bougie i-1.

        - Bullish FVG : candles[i-2].high < candles[i].low
        - Bearish FVG : candles[i-2].low > candles[i].high

        Args:
            candles_df: DataFrame OHLCV.

        Returns:
            Liste de dicts FVG avec type, top, bottom, index, time.
        """
        results = []
        if len(candles_df) < 3:
            return results

        highs = candles_df["high"].values
        lows = candles_df["low"].values
        times = candles_df["time"].values

        for i in range(2, len(candles_df)):
            if highs[i - 2] < lows[i]:
                results.append({
                    "type": "bullish_fvg",
                    "top": float(lows[i]),
                    "bottom": float(highs[i - 2]),
                    "index": i,
                    "time": pd.Timestamp(times[i]).to_pydatetime(),
                })
            elif lows[i - 2] > highs[i]:
                results.append({
                    "type": "bearish_fvg",
                    "top": float(lows[i - 2]),
                    "bottom": float(highs[i]),
                    "index": i,
                    "time": pd.Timestamp(times[i]).to_pydatetime(),
                })

        if results:
            logger.info("%d FVG détectés", len(results))
        return results

    def detect_ifvg(
        self, candles_df: pd.DataFrame, fvg_list: list[dict]
    ) -> list[dict]:
        """Détecte les Inverse FVG (iFVG) — FVG cassés par le prix.

        - Bullish FVG cassé vers le bas → bearish iFVG (résistance)
        - Bearish FVG cassé vers le haut → bullish iFVG (support)

        Args:
            candles_df: DataFrame OHLCV.
            fvg_list: Liste des FVG précédemment détectés.

        Returns:
            Liste de dicts iFVG avec type, top, bottom, original_fvg_index.
        """
        results = []
        if not fvg_list or candles_df.empty:
            return results

        for fvg in fvg_list:
            fvg_idx = fvg["index"]
            candles_after = candles_df.iloc[fvg_idx + 1:] if fvg_idx + 1 < len(candles_df) else pd.DataFrame()

            if candles_after.empty:
                continue

            if fvg["type"] == "bullish_fvg":
                if candles_after["low"].min() < fvg["bottom"]:
                    results.append({
                        "type": "bearish_ifvg",
                        "top": fvg["top"],
                        "bottom": fvg["bottom"],
                        "original_fvg_index": fvg_idx,
                    })
            elif fvg["type"] == "bearish_fvg":
                if candles_after["high"].max() > fvg["top"]:
                    results.append({
                        "type": "bullish_ifvg",
                        "top": fvg["top"],
                        "bottom": fvg["bottom"],
                        "original_fvg_index": fvg_idx,
                    })

        if results:
            logger.info("%d iFVG détectés", len(results))
        return results

    def detect_ob(self, candles_df: pd.DataFrame) -> list[dict]:
        """Détecte les Order Blocks (OB).

        - Bullish OB : dernière bougie rouge avant un fort mouvement haussier
          (3+ bougies vertes consécutives ou mouvement > 2x ATR).
        - Bearish OB : dernière bougie verte avant un fort mouvement baissier.

        Args:
            candles_df: DataFrame OHLCV.

        Returns:
            Liste de dicts OB avec type, high, low, index, time.
        """
        results = []
        if len(candles_df) < 4:
            return results

        opens = candles_df["open"].values
        closes = candles_df["close"].values
        highs = candles_df["high"].values
        lows = candles_df["low"].values
        times = candles_df["time"].values

        atr = self._calculate_atr(candles_df)

        for i in range(len(candles_df) - 3):
            is_red = closes[i] < opens[i]
            is_green = closes[i] > opens[i]

            if is_red:
                consecutive_green = 0
                move_high = highs[i]
                for j in range(i + 1, len(candles_df)):
                    if closes[j] > opens[j]:
                        consecutive_green += 1
                        move_high = max(move_high, highs[j])
                    else:
                        break

                move_size = move_high - lows[i]
                if consecutive_green >= 3 or (atr > 0 and move_size > 2 * atr):
                    results.append({
                        "type": "bullish_ob",
                        "high": float(highs[i]),
                        "low": float(lows[i]),
                        "index": i,
                        "time": pd.Timestamp(times[i]).to_pydatetime(),
                    })

            if is_green:
                consecutive_red = 0
                move_low = lows[i]
                for j in range(i + 1, len(candles_df)):
                    if closes[j] < opens[j]:
                        consecutive_red += 1
                        move_low = min(move_low, lows[j])
                    else:
                        break

                move_size = highs[i] - move_low
                if consecutive_red >= 3 or (atr > 0 and move_size > 2 * atr):
                    results.append({
                        "type": "bearish_ob",
                        "high": float(highs[i]),
                        "low": float(lows[i]),
                        "index": i,
                        "time": pd.Timestamp(times[i]).to_pydatetime(),
                    })

        if results:
            logger.info("%d OB détectés", len(results))
        return results

    def detect_bb(
        self, candles_df: pd.DataFrame, ob_list: list[dict]
    ) -> list[dict]:
        """Détecte les Breaker Blocks (BB) — anciens OB cassés qui changent de rôle.

        - Bullish OB cassé vers le bas → bearish BB.
        - Bearish OB cassé vers le haut → bullish BB.

        Args:
            candles_df: DataFrame OHLCV.
            ob_list: Liste des OB précédemment détectés.

        Returns:
            Liste de dicts BB avec type, high, low, original_ob_index.
        """
        results = []
        if not ob_list or candles_df.empty:
            return results

        for ob in ob_list:
            ob_idx = ob["index"]
            candles_after = candles_df.iloc[ob_idx + 1:] if ob_idx + 1 < len(candles_df) else pd.DataFrame()

            if candles_after.empty:
                continue

            if ob["type"] == "bullish_ob":
                if candles_after["close"].min() < ob["low"]:
                    results.append({
                        "type": "bearish_bb",
                        "high": ob["high"],
                        "low": ob["low"],
                        "original_ob_index": ob_idx,
                    })
            elif ob["type"] == "bearish_ob":
                if candles_after["close"].max() > ob["high"]:
                    results.append({
                        "type": "bullish_bb",
                        "high": ob["high"],
                        "low": ob["low"],
                        "original_ob_index": ob_idx,
                    })

        if results:
            logger.info("%d BB détectés", len(results))
        return results

    @staticmethod
    def is_price_in_confluence(
        price: float, confluences: dict
    ) -> Optional[dict]:
        """Vérifie si le prix actuel est dans une zone de confluence.

        Parcourt FVG, iFVG, OB, BB et retourne la première confluence touchée.

        Args:
            price: Prix actuel de l'asset.
            confluences: Dictionnaire de confluences (output de detect_all).

        Returns:
            La confluence touchée ou None.
        """
        for zone_type in ("fvg", "ifvg", "ob", "bb"):
            zones = confluences.get(zone_type, [])
            for zone in zones:
                top = zone.get("top") or zone.get("high")
                bottom = zone.get("bottom") or zone.get("low")
                if top is not None and bottom is not None and bottom <= price <= top:
                    logger.info(
                        "Prix %.5f dans confluence %s [%.5f - %.5f]",
                        price, zone.get("type", zone_type), bottom, top,
                    )
                    return zone
        return None

    @staticmethod
    def _calculate_atr(candles_df: pd.DataFrame, period: int = 14) -> float:
        """Calcule l'Average True Range sur la période donnée.

        Args:
            candles_df: DataFrame OHLCV.
            period: Nombre de bougies pour le calcul ATR.

        Returns:
            Valeur ATR moyenne. 0.0 si pas assez de données.
        """
        if len(candles_df) < 2:
            return 0.0

        highs = candles_df["high"].values
        lows = candles_df["low"].values
        closes = candles_df["close"].values

        true_ranges = []
        for i in range(1, len(candles_df)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

        if not true_ranges:
            return 0.0

        window = true_ranges[-period:] if len(true_ranges) >= period else true_ranges
        return sum(window) / len(window)
