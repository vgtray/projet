import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfluenceDetector:
    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Point d'entrée
    # ------------------------------------------------------------------

    def detect_all(self, candles: list[dict], levels: dict, current_price: float) -> dict:
        """Détecte toutes les confluences SMC/ICT sur les bougies M5."""
        fvgs = self.detect_fvg(candles)
        obs = self.detect_ob(candles)
        ifvgs = self.detect_ifvg(candles, fvgs)
        bbs = self.detect_bb(candles, obs)
        sweep = self.detect_sweep(candles, levels, current_price)

        # Filtrer les confluences actives (prix dans la zone)
        active: list[str] = []
        if any(self._is_active(z, current_price) for z in fvgs):
            active.append("FVG")
        if any(self._is_active(z, current_price) for z in ifvgs):
            active.append("iFVG")
        if any(self._is_active(z, current_price) for z in obs):
            active.append("OB")
        if any(self._is_active(z, current_price) for z in bbs):
            active.append("BB")
        if sweep is not None:
            active.append("sweep")

        logger.info(
            "Confluences détectées — FVG: %d | iFVG: %d | OB: %d | BB: %d | Sweep: %s | Actives: %s",
            len(fvgs), len(ifvgs), len(obs), len(bbs),
            sweep is not None, active,
        )

        return {
            "fvg": fvgs,
            "ifvg": ifvgs,
            "ob": obs,
            "bb": bbs,
            "sweep": sweep,
            "active_confluences": active,
        }

    # ------------------------------------------------------------------
    # FVG
    # ------------------------------------------------------------------

    def detect_fvg(self, candles: list[dict]) -> list[dict]:
        """
        Fair Value Gap : gap entre bougie i-1 et i+1.
        Bullish : candle[i-1].high < candle[i+1].low
        Bearish : candle[i-1].low  > candle[i+1].high
        Ne retourne que les FVGs non comblés par les bougies suivantes.
        """
        if len(candles) < 3:
            return []

        fvgs: list[dict] = []

        for i in range(1, len(candles) - 1):
            prev = candles[i - 1]
            curr = candles[i]
            nxt = candles[i + 1]

            # Bullish FVG
            if prev["high"] < nxt["low"]:
                fvg = {
                    "type": "bullish",
                    "top": nxt["low"],
                    "bottom": prev["high"],
                    "candle_index": i,
                    "time": curr["time"],
                }
                if not self._is_filled(fvg, candles[i + 1:]):
                    fvgs.append(fvg)

            # Bearish FVG
            if prev["low"] > nxt["high"]:
                fvg = {
                    "type": "bearish",
                    "top": prev["low"],
                    "bottom": nxt["high"],
                    "candle_index": i,
                    "time": curr["time"],
                }
                if not self._is_filled(fvg, candles[i + 1:]):
                    fvgs.append(fvg)

        return fvgs

    # ------------------------------------------------------------------
    # Order Block
    # ------------------------------------------------------------------

    def detect_ob(self, candles: list[dict]) -> list[dict]:
        """
        OB bullish : bougie bearish suivie d'un fort mouvement haussier (≥ 2x la taille).
        OB bearish : bougie bullish suivie d'un fort mouvement baissier.
        Ne retourne que les OBs non cassés.
        """
        if len(candles) < 2:
            return []

        obs: list[dict] = []

        for i in range(len(candles) - 1):
            curr = candles[i]
            nxt = candles[i + 1]

            curr_body = abs(curr["close"] - curr["open"])
            nxt_body = abs(nxt["close"] - nxt["open"])

            if curr_body == 0:
                continue

            is_curr_bearish = curr["close"] < curr["open"]
            is_curr_bullish = curr["close"] > curr["open"]
            is_nxt_bullish = nxt["close"] > nxt["open"]
            is_nxt_bearish = nxt["close"] < nxt["open"]

            # OB bullish : bougie bearish → fort mouvement haussier
            if is_curr_bearish and is_nxt_bullish and nxt_body >= 2 * curr_body:
                ob = {
                    "type": "bullish",
                    "top": curr["high"],
                    "bottom": curr["low"],
                    "time": curr["time"],
                }
                if not self._is_ob_broken(ob, candles[i + 1:]):
                    obs.append(ob)

            # OB bearish : bougie bullish → fort mouvement baissier
            if is_curr_bullish and is_nxt_bearish and nxt_body >= 2 * curr_body:
                ob = {
                    "type": "bearish",
                    "top": curr["high"],
                    "bottom": curr["low"],
                    "time": curr["time"],
                }
                if not self._is_ob_broken(ob, candles[i + 1:]):
                    obs.append(ob)

        return obs

    # ------------------------------------------------------------------
    # iFVG (Inverse FVG)
    # ------------------------------------------------------------------

    def detect_ifvg(self, candles: list[dict], fvgs: list[dict]) -> list[dict]:
        """
        FVGs qui ont été cassés (prix a traversé la zone) → deviennent iFVG.
        Re-scanne les FVGs potentiels et garde ceux qui ont été comblés.
        """
        if len(candles) < 3:
            return []

        ifvgs: list[dict] = []

        for i in range(1, len(candles) - 1):
            prev = candles[i - 1]
            curr = candles[i]
            nxt = candles[i + 1]

            # Bullish FVG candidat
            if prev["high"] < nxt["low"]:
                fvg = {
                    "type": "bullish",
                    "top": nxt["low"],
                    "bottom": prev["high"],
                    "candle_index": i,
                    "time": curr["time"],
                }
                if self._is_filled(fvg, candles[i + 1:]):
                    ifvgs.append(fvg)

            # Bearish FVG candidat
            if prev["low"] > nxt["high"]:
                fvg = {
                    "type": "bearish",
                    "top": prev["low"],
                    "bottom": nxt["high"],
                    "candle_index": i,
                    "time": curr["time"],
                }
                if self._is_filled(fvg, candles[i + 1:]):
                    ifvgs.append(fvg)

        return ifvgs

    # ------------------------------------------------------------------
    # Breaker Block
    # ------------------------------------------------------------------

    def detect_bb(self, candles: list[dict], obs: list[dict]) -> list[dict]:
        """
        OBs cassés qui changent de rôle.
        OB bullish cassé (prix passe en dessous) → BB bearish.
        OB bearish cassé (prix passe au dessus) → BB bullish.
        """
        if len(candles) < 2:
            return []

        bbs: list[dict] = []

        # Scanner tous les OBs potentiels (y compris ceux déjà cassés)
        for i in range(len(candles) - 1):
            curr = candles[i]
            nxt = candles[i + 1]

            curr_body = abs(curr["close"] - curr["open"])
            nxt_body = abs(nxt["close"] - nxt["open"])

            if curr_body == 0:
                continue

            is_curr_bearish = curr["close"] < curr["open"]
            is_curr_bullish = curr["close"] > curr["open"]
            is_nxt_bullish = nxt["close"] > nxt["open"]
            is_nxt_bearish = nxt["close"] < nxt["open"]

            # OB bullish cassé → BB bearish
            if is_curr_bearish and is_nxt_bullish and nxt_body >= 2 * curr_body:
                ob = {"type": "bullish", "top": curr["high"], "bottom": curr["low"], "time": curr["time"]}
                if self._is_ob_broken(ob, candles[i + 1:]):
                    bbs.append({
                        "type": "bearish",
                        "top": ob["top"],
                        "bottom": ob["bottom"],
                        "time": ob["time"],
                    })

            # OB bearish cassé → BB bullish
            if is_curr_bullish and is_nxt_bearish and nxt_body >= 2 * curr_body:
                ob = {"type": "bearish", "top": curr["high"], "bottom": curr["low"], "time": curr["time"]}
                if self._is_ob_broken(ob, candles[i + 1:]):
                    bbs.append({
                        "type": "bullish",
                        "top": ob["top"],
                        "bottom": ob["bottom"],
                        "time": ob["time"],
                    })

        return bbs

    # ------------------------------------------------------------------
    # Liquidity Sweep
    # ------------------------------------------------------------------

    def detect_sweep(self, candles: list[dict], levels: dict, current_price: float) -> dict | None:
        """
        Détecte si un niveau clé a été dépassé récemment (5 dernières bougies)
        puis le prix est revenu de l'autre côté.
        """
        level_map = {
            "asia_high": levels.get("asia_high"),
            "asia_low": levels.get("asia_low"),
            "london_high": levels.get("london_high"),
            "london_low": levels.get("london_low"),
            "prev_high": levels.get("prev_day_high"),
            "prev_low": levels.get("prev_day_low"),
        }

        recent = candles[-5:] if len(candles) >= 5 else candles

        for level_name, level_price in level_map.items():
            if level_price is None:
                continue

            # Sweep au dessus (prix a dépassé le niveau par le haut puis est revenu en dessous)
            swept_above = any(c["high"] > level_price for c in recent)
            if swept_above and current_price < level_price:
                sweep_candle = next(c for c in reversed(recent) if c["high"] > level_price)
                return {
                    "level_name": level_name,
                    "level_price": level_price,
                    "direction": "above",
                    "candle_time": sweep_candle["time"],
                }

            # Sweep en dessous (prix a dépassé le niveau par le bas puis est revenu au dessus)
            swept_below = any(c["low"] < level_price for c in recent)
            if swept_below and current_price > level_price:
                sweep_candle = next(c for c in reversed(recent) if c["low"] < level_price)
                return {
                    "level_name": level_name,
                    "level_price": level_price,
                    "direction": "below",
                    "candle_time": sweep_candle["time"],
                }

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _price_in_zone(self, price: float, top: float, bottom: float, tolerance: float = 0.0) -> bool:
        """Vérifie si le prix est dans une zone (avec tolérance optionnelle)."""
        return (bottom - tolerance) <= price <= (top + tolerance)

    def _is_active(self, zone: dict, current_price: float) -> bool:
        """Vérifie si le prix actuel est dans la zone de la confluence."""
        return self._price_in_zone(current_price, zone["top"], zone["bottom"])

    def _is_filled(self, fvg: dict, subsequent_candles: list[dict]) -> bool:
        """Vérifie si un FVG a été comblé par les bougies suivantes."""
        for c in subsequent_candles:
            if fvg["type"] == "bullish" and c["low"] <= fvg["bottom"]:
                return True
            if fvg["type"] == "bearish" and c["high"] >= fvg["top"]:
                return True
        return False

    def _is_ob_broken(self, ob: dict, subsequent_candles: list[dict]) -> bool:
        """Vérifie si un OB a été cassé par les bougies suivantes."""
        for c in subsequent_candles:
            if ob["type"] == "bullish" and c["close"] < ob["bottom"]:
                return True
            if ob["type"] == "bearish" and c["close"] > ob["top"]:
                return True
        return False
