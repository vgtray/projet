"""Client MetaTrader 5 via mt5linux (RPyC).

Gère toute la communication avec MT5 tournant dans un container Docker.
Connexion RPyC, données marché, exécution de trades, calcul du lot size.
Ref: SPEC.md sections 9, 12, 16 — MT5, lot size, résilience.
"""

import logging
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import pytz

from mt5linux import MetaTrader5

from src.config import Config

logger = logging.getLogger(__name__)

PARIS_TZ = pytz.timezone(Config.TIMEZONE)

SYMBOL_ALIASES = {
    "US100": ["US100.cash", "US100", "NAS100.cash", "NAS100"],
    "XAUUSD": ["XAUUSD"],
}

RETRY_MAX = 3
RETRY_BACKOFF = [30, 60, 120]


class MT5Client:
    """Client MT5 via RPyC (mt5linux).

    Gère connexion, données marché, exécution de trades et calcul lot size.
    """

    def __init__(self, host: str = Config.MT5_HOST, port: int = Config.MT5_PORT):
        self._host = host
        self._port = port
        self._mt5: Optional[MetaTrader5] = None
        self._connected = False
        self._symbol_cache: dict[str, str] = {}

    def connect(self) -> bool:
        """Connexion RPyC à MT5 avec retry (3 tentatives, backoff 30/60/120s).

        Returns:
            True si connecté, False sinon.
        """
        for attempt in range(RETRY_MAX):
            try:
                logger.info(
                    "Connexion MT5 RPyC %s:%d (tentative %d/%d)",
                    self._host, self._port, attempt + 1, RETRY_MAX,
                )
                self._mt5 = MetaTrader5(host=self._host, port=self._port)
                if not self._mt5.initialize():
                    error = self._mt5.last_error()
                    logger.error("MT5 initialize échoué : %s", error)
                    self._connected = False
                    if attempt < RETRY_MAX - 1:
                        wait = RETRY_BACKOFF[attempt]
                        logger.info("Retry dans %ds...", wait)
                        time.sleep(wait)
                    continue

                self._connected = True
                info = self._mt5.terminal_info()
                logger.info(
                    "MT5 connecté — terminal: %s, build: %s",
                    getattr(info, "name", "N/A"),
                    getattr(info, "build", "N/A"),
                )
                return True

            except Exception as e:
                logger.error("Erreur connexion MT5 : %s", e)
                self._connected = False
                if attempt < RETRY_MAX - 1:
                    wait = RETRY_BACKOFF[attempt]
                    logger.info("Retry dans %ds...", wait)
                    time.sleep(wait)

        logger.critical("Connexion MT5 impossible après %d tentatives", RETRY_MAX)
        return False

    def disconnect(self):
        """Ferme la connexion MT5."""
        if self._mt5 is not None:
            try:
                self._mt5.shutdown()
                logger.info("MT5 déconnecté")
            except Exception as e:
                logger.error("Erreur déconnexion MT5 : %s", e)
            finally:
                self._connected = False
                self._mt5 = None

    def is_connected(self) -> bool:
        """Vérifie si la connexion MT5 est active.

        Returns:
            True si connecté et MT5 répond.
        """
        if not self._connected or self._mt5 is None:
            return False
        try:
            info = self._mt5.terminal_info()
            return info is not None
        except Exception:
            self._connected = False
            return False

    def _ensure_connection(self) -> bool:
        """Reconnecte si déconnecté.

        Returns:
            True si connexion active ou rétablie.
        """
        if self.is_connected():
            return True
        logger.warning("Connexion MT5 perdue — tentative de reconnexion")
        return self.connect()

    # --- Données marché ---

    def get_candles(
        self, symbol: str, timeframe: str = "M5", count: int = 20
    ) -> Optional[pd.DataFrame]:
        """Récupère les dernières bougies OHLCV.

        Args:
            symbol: Symbole interne (XAUUSD, US100).
            timeframe: Timeframe (M5 par défaut).
            count: Nombre de bougies à récupérer.

        Returns:
            DataFrame avec colonnes time, open, high, low, close, volume.
            None en cas d'erreur.
        """
        if not self._ensure_connection():
            return None

        resolved = self._resolve_symbol(symbol)
        if resolved is None:
            return None

        tf = self._parse_timeframe(timeframe)

        for attempt in range(RETRY_MAX):
            try:
                rates = self._mt5.copy_rates_from_pos(resolved, tf, 0, count)
                if rates is None or len(rates) == 0:
                    error = self._mt5.last_error()
                    logger.error(
                        "Pas de données pour %s (tf=%s) : %s", resolved, timeframe, error
                    )
                    return None

                df = pd.DataFrame(rates)
                df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
                df["time"] = df["time"].dt.tz_convert(PARIS_TZ)
                df = df[["time", "open", "high", "low", "close", "tick_volume"]]
                df = df.rename(columns={"tick_volume": "volume"})

                logger.debug(
                    "%d bougies %s récupérées pour %s", len(df), timeframe, symbol
                )
                return df

            except Exception as e:
                logger.error(
                    "Erreur get_candles %s (tentative %d/%d) : %s",
                    symbol, attempt + 1, RETRY_MAX, e,
                )
                if attempt < RETRY_MAX - 1:
                    time.sleep(RETRY_BACKOFF[attempt])
                    self._ensure_connection()

        return None

    def get_current_price(self, symbol: str) -> Optional[dict]:
        """Récupère le prix actuel (bid, ask, last).

        Args:
            symbol: Symbole interne (XAUUSD, US100).

        Returns:
            {"bid": float, "ask": float, "last": float} ou None.
        """
        if not self._ensure_connection():
            return None

        resolved = self._resolve_symbol(symbol)
        if resolved is None:
            return None

        try:
            tick = self._mt5.symbol_info_tick(resolved)
            if tick is None:
                logger.error("Tick indisponible pour %s", resolved)
                return None

            return {
                "bid": tick.bid,
                "ask": tick.ask,
                "last": tick.last,
            }
        except Exception as e:
            logger.error("Erreur get_current_price %s : %s", symbol, e)
            return None

    def get_symbol_info(self, symbol: str):
        """Récupère les infos du symbole (lot size, tick value, etc.).

        Args:
            symbol: Symbole interne (XAUUSD, US100).

        Returns:
            Objet SymbolInfo MT5 ou None.
        """
        if not self._ensure_connection():
            return None

        resolved = self._resolve_symbol(symbol)
        if resolved is None:
            return None

        try:
            info = self._mt5.symbol_info(resolved)
            if info is None:
                logger.error("Symbol info indisponible pour %s", resolved)
                return None
            return info
        except Exception as e:
            logger.error("Erreur get_symbol_info %s : %s", symbol, e)
            return None

    # --- Exécution trades ---

    def open_trade(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        sl_price: float,
        tp_price: float,
        comment: str = "",
    ) -> Optional[dict]:
        """Ouvre un trade sur MT5.

        Args:
            symbol: Symbole interne.
            direction: "long" ou "short".
            lot_size: Taille du lot.
            sl_price: Prix du stop loss.
            tp_price: Prix du take profit.
            comment: Commentaire du trade.

        Returns:
            Dictionnaire avec ticket, retcode, etc. ou None.
        """
        if not self._ensure_connection():
            return None

        resolved = self._resolve_symbol(symbol)
        if resolved is None:
            return None

        price_info = self.get_current_price(symbol)
        if price_info is None:
            return None

        if direction == "long":
            order_type = self._mt5.ORDER_TYPE_BUY
            price = price_info["ask"]
        elif direction == "short":
            order_type = self._mt5.ORDER_TYPE_SELL
            price = price_info["bid"]
        else:
            logger.error("Direction invalide : %s", direction)
            return None

        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": resolved,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": Config.MAX_SLIPPAGE,
            "magic": Config.BOT_MAGIC,
            "comment": comment,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
            "type_time": self._mt5.ORDER_TIME_GTC,
        }

        for attempt in range(RETRY_MAX):
            try:
                result = self._mt5.order_send(request)
                if result is None:
                    error = self._mt5.last_error()
                    logger.error(
                        "order_send retourne None pour %s (tentative %d/%d) : %s",
                        symbol, attempt + 1, RETRY_MAX, error,
                    )
                    if attempt < RETRY_MAX - 1:
                        time.sleep(RETRY_BACKOFF[attempt])
                        self._ensure_connection()
                    continue

                result_dict = {
                    "retcode": result.retcode,
                    "ticket": getattr(result, "order", None),
                    "volume": result.volume,
                    "price": result.price,
                    "comment": result.comment,
                }

                if result.retcode == self._mt5.TRADE_RETCODE_DONE:
                    logger.info(
                        "Trade ouvert — %s %s %.2f lots @ %.5f | SL=%.5f TP=%.5f | ticket=%s",
                        direction.upper(), symbol, lot_size, result.price,
                        sl_price, tp_price, result_dict["ticket"],
                    )
                else:
                    logger.error(
                        "Trade rejeté — %s %s | retcode=%d | %s",
                        direction.upper(), symbol, result.retcode, result.comment,
                    )

                return result_dict

            except Exception as e:
                logger.error(
                    "Erreur open_trade %s (tentative %d/%d) : %s",
                    symbol, attempt + 1, RETRY_MAX, e,
                )
                if attempt < RETRY_MAX - 1:
                    time.sleep(RETRY_BACKOFF[attempt])
                    self._ensure_connection()

        return None

    def close_trade(
        self, ticket: int, symbol: str, direction: str, lot_size: float
    ) -> Optional[dict]:
        """Ferme un trade en ouvrant une position inverse.

        Args:
            ticket: Numéro de ticket de la position.
            symbol: Symbole interne.
            direction: Direction du trade original ("long" ou "short").
            lot_size: Taille du lot à fermer.

        Returns:
            Dictionnaire avec retcode, ticket, etc. ou None.
        """
        if not self._ensure_connection():
            return None

        resolved = self._resolve_symbol(symbol)
        if resolved is None:
            return None

        price_info = self.get_current_price(symbol)
        if price_info is None:
            return None

        if direction == "long":
            close_type = self._mt5.ORDER_TYPE_SELL
            price = price_info["bid"]
        elif direction == "short":
            close_type = self._mt5.ORDER_TYPE_BUY
            price = price_info["ask"]
        else:
            logger.error("Direction invalide pour fermeture : %s", direction)
            return None

        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": resolved,
            "volume": lot_size,
            "type": close_type,
            "price": price,
            "deviation": Config.MAX_SLIPPAGE,
            "magic": Config.BOT_MAGIC,
            "position": ticket,
            "comment": f"close #{ticket}",
            "type_filling": self._mt5.ORDER_FILLING_IOC,
            "type_time": self._mt5.ORDER_TIME_GTC,
        }

        for attempt in range(RETRY_MAX):
            try:
                result = self._mt5.order_send(request)
                if result is None:
                    error = self._mt5.last_error()
                    logger.error(
                        "close_trade retourne None pour ticket %d (tentative %d/%d) : %s",
                        ticket, attempt + 1, RETRY_MAX, error,
                    )
                    if attempt < RETRY_MAX - 1:
                        time.sleep(RETRY_BACKOFF[attempt])
                        self._ensure_connection()
                    continue

                result_dict = {
                    "retcode": result.retcode,
                    "ticket": getattr(result, "order", None),
                    "volume": result.volume,
                    "price": result.price,
                    "comment": result.comment,
                }

                if result.retcode == self._mt5.TRADE_RETCODE_DONE:
                    logger.info(
                        "Trade fermé — ticket %d | %s %s %.2f lots @ %.5f",
                        ticket, direction.upper(), symbol, lot_size, result.price,
                    )
                else:
                    logger.error(
                        "Fermeture rejetée — ticket %d | retcode=%d | %s",
                        ticket, result.retcode, result.comment,
                    )

                return result_dict

            except Exception as e:
                logger.error(
                    "Erreur close_trade ticket %d (tentative %d/%d) : %s",
                    ticket, attempt + 1, RETRY_MAX, e,
                )
                if attempt < RETRY_MAX - 1:
                    time.sleep(RETRY_BACKOFF[attempt])
                    self._ensure_connection()

        return None

    def get_open_positions(self) -> list[dict]:
        """Récupère les positions ouvertes du bot (magic=123456).

        Returns:
            Liste de dicts position. Liste vide si erreur ou aucune position.
        """
        if not self._ensure_connection():
            return []

        try:
            positions = self._mt5.positions_get()
            if positions is None:
                return []

            bot_positions = []
            for pos in positions:
                if pos.magic != Config.BOT_MAGIC:
                    continue
                bot_positions.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": pos.type,
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                    "magic": pos.magic,
                    "comment": pos.comment,
                    "time": datetime.fromtimestamp(pos.time, tz=PARIS_TZ),
                })

            logger.debug("%d positions ouvertes du bot", len(bot_positions))
            return bot_positions

        except Exception as e:
            logger.error("Erreur get_open_positions : %s", e)
            return []

    def get_account_info(self) -> Optional[dict]:
        """Récupère les infos du compte (balance, equity, margin, etc.).

        Returns:
            Dictionnaire avec balance, equity, margin, free_margin, leverage.
            None en cas d'erreur.
        """
        if not self._ensure_connection():
            return None

        try:
            info = self._mt5.account_info()
            if info is None:
                logger.error("account_info indisponible")
                return None

            return {
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "free_margin": info.margin_free,
                "leverage": info.leverage,
                "currency": info.currency,
                "server": info.server,
            }
        except Exception as e:
            logger.error("Erreur get_account_info : %s", e)
            return None

    # --- Calcul lot size (SPEC section 9) ---

    def calculate_lot_size(
        self, symbol: str, entry_price: float, sl_price: float
    ) -> Optional[float]:
        """Calcule le lot size dynamique basé sur 1% de risque.

        Formule : lot_size = (capital * 0.01) / (distance_en_ticks * tick_value)

        Args:
            symbol: Symbole interne.
            entry_price: Prix d'entrée prévu.
            sl_price: Prix du stop loss.

        Returns:
            Lot size calculé et clampé, ou None en cas d'erreur.
        """
        account = self.get_account_info()
        if account is None:
            logger.error("Impossible de calculer le lot size : account_info indisponible")
            return None

        sym_info = self.get_symbol_info(symbol)
        if sym_info is None:
            logger.error("Impossible de calculer le lot size : symbol_info indisponible pour %s", symbol)
            return None

        capital = account["balance"]
        distance_sl = abs(entry_price - sl_price)

        if distance_sl == 0:
            logger.error("Distance SL nulle — calcul lot size impossible")
            return None

        tick_value = sym_info.trade_tick_value
        tick_size = sym_info.trade_tick_size

        if tick_value <= 0 or tick_size <= 0:
            logger.error(
                "Valeurs tick invalides pour %s : tick_value=%s, tick_size=%s",
                symbol, tick_value, tick_size,
            )
            return None

        distance_en_ticks = distance_sl / tick_size
        risk_amount = capital * Config.RISK_PERCENT
        lot_size = risk_amount / (distance_en_ticks * tick_value)

        volume_step = sym_info.volume_step
        volume_min = sym_info.volume_min
        volume_max = sym_info.volume_max

        if volume_step > 0:
            lot_size = round(lot_size / volume_step) * volume_step
            lot_size = round(lot_size, 10)

        lot_size = max(volume_min, min(volume_max, lot_size))

        logger.info(
            "Lot size calculé pour %s — capital=%.2f | SL distance=%.5f | "
            "ticks=%.2f | tick_value=%.5f | lot=%.5f (min=%.5f max=%.5f step=%.5f)",
            symbol, capital, distance_sl, distance_en_ticks,
            tick_value, lot_size, volume_min, volume_max, volume_step,
        )

        return lot_size

    # --- Historique des deals ---

    def get_history_deals(self, from_date, to_date) -> list:
        """Récupère l'historique des deals MT5 sur une période.

        Args:
            from_date: Date de début.
            to_date: Date de fin.

        Returns:
            Liste de deals MT5 ou liste vide.
        """
        if not self._ensure_connection():
            return []

        try:
            from_date_naive = from_date.replace(tzinfo=None) if from_date.tzinfo else from_date
            to_date_naive = to_date.replace(tzinfo=None) if to_date.tzinfo else to_date
            deals = self._mt5.history_deals_get(from_date_naive, to_date_naive)
            if deals is None:
                return []
            return list(deals)
        except Exception as e:
            logger.error("Erreur history_deals_get : %s", e)
            return []

    # --- Mapping symboles ---

    def _resolve_symbol(self, symbol: str) -> Optional[str]:
        """Résout le symbole interne vers le symbole broker.

        Essaie le symbole tel quel, puis les alias (.cash suffix, etc.).

        Args:
            symbol: Symbole interne (XAUUSD, US100).

        Returns:
            Symbole résolu ou None si introuvable.
        """
        if symbol in self._symbol_cache:
            return self._symbol_cache[symbol]

        candidates = SYMBOL_ALIASES.get(symbol, [symbol, f"{symbol}.cash"])

        for candidate in candidates:
            try:
                info = self._mt5.symbol_info(candidate)
                if info is not None:
                    if not info.visible:
                        self._mt5.symbol_select(candidate, True)
                    self._symbol_cache[symbol] = candidate
                    if candidate != symbol:
                        logger.info("Symbole résolu : %s → %s", symbol, candidate)
                    return candidate
            except Exception as e:
                logger.debug("Symbole %s non trouvé : %s", candidate, e)
                continue

        logger.error(
            "Symbole introuvable pour %s — candidats testés : %s",
            symbol, candidates,
        )
        return None

    # --- Utilitaires ---

    def _parse_timeframe(self, timeframe: str):
        """Convertit un string timeframe en constante MT5.

        Args:
            timeframe: Chaîne (M1, M5, M15, H1, H4, D1).

        Returns:
            Constante MT5 correspondante.
        """
        mapping = {
            "M1": self._mt5.TIMEFRAME_M1,
            "M5": self._mt5.TIMEFRAME_M5,
            "M15": self._mt5.TIMEFRAME_M15,
            "M30": self._mt5.TIMEFRAME_M30,
            "H1": self._mt5.TIMEFRAME_H1,
            "H4": self._mt5.TIMEFRAME_H4,
            "D1": self._mt5.TIMEFRAME_D1,
        }
        tf = mapping.get(timeframe)
        if tf is None:
            logger.warning("Timeframe inconnu '%s', fallback M5", timeframe)
            tf = self._mt5.TIMEFRAME_M5
        return tf
