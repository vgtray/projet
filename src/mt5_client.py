import logging
import time
from datetime import datetime, timezone

from zoneinfo import ZoneInfo

from mt5linux import MetaTrader5

from . import config

logger = logging.getLogger(__name__)

PARIS_TZ = ZoneInfo(config.TIMEZONE)
UTC_TZ = ZoneInfo("UTC")


def _utc_to_paris(dt: datetime) -> datetime:
    """Convertit un datetime UTC en Europe/Paris."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(PARIS_TZ)


class MT5Client:
    def __init__(self):
        self.mt5: MetaTrader5 | None = None
        self._host = config.MT5_HOST
        self._port = config.MT5_PORT

    # ------------------------------------------------------------------
    # Connexion / déconnexion
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Connexion RPyC à MT5. Retry 3x avec backoff. Retourne True si succès."""
        for attempt in range(config.RETRY_MAX):
            try:
                self.mt5 = MetaTrader5(host=self._host, port=self._port)
                if self.mt5.initialize():
                    logger.info("Connexion MT5 établie (%s:%d)", self._host, self._port)
                    return True
                err = self.mt5.last_error()
                logger.error("MT5 initialize échoué (tentative %d/%d) : %s",
                             attempt + 1, config.RETRY_MAX, err)
            except Exception as exc:
                logger.error("Erreur connexion MT5 (tentative %d/%d) : %s",
                             attempt + 1, config.RETRY_MAX, exc)
            if attempt < config.RETRY_MAX - 1:
                wait = config.RETRY_BACKOFF[attempt]
                logger.info("Retry connexion MT5 dans %ds…", wait)
                time.sleep(wait)
        logger.critical("Impossible de se connecter à MT5 après %d tentatives", config.RETRY_MAX)
        self.mt5 = None
        return False

    def disconnect(self):
        """Ferme la connexion RPyC proprement."""
        if self.mt5 is not None:
            try:
                self.mt5.shutdown()
                logger.info("Connexion MT5 fermée")
            except Exception as exc:
                logger.warning("Erreur lors de la déconnexion MT5 : %s", exc)
            finally:
                self.mt5 = None

    def is_connected(self) -> bool:
        """Vérifie si la connexion est active."""
        if self.mt5 is None:
            return False
        try:
            info = self.mt5.account_info()
            return info is not None
        except Exception:
            return False

    def _ensure_connected(self) -> bool:
        """Reconnecte automatiquement si la connexion est perdue."""
        if self.is_connected():
            return True
        logger.warning("Connexion MT5 perdue, tentative de reconnexion…")
        return self.connect()

    # ------------------------------------------------------------------
    # Helpers retry
    # ------------------------------------------------------------------

    def _retry(self, func, label: str):
        """Exécute `func` avec retry + reconnexion auto. Retourne le résultat ou None."""
        for attempt in range(config.RETRY_MAX):
            if not self._ensure_connected():
                return None
            try:
                result = func()
                if result is not None:
                    return result
                err = self.mt5.last_error()
                logger.error("%s échoué (tentative %d/%d) : %s",
                             label, attempt + 1, config.RETRY_MAX, err)
            except Exception as exc:
                logger.error("%s exception (tentative %d/%d) : %s",
                             label, attempt + 1, config.RETRY_MAX, exc)
                self.mt5 = None
            if attempt < config.RETRY_MAX - 1:
                wait = config.RETRY_BACKOFF[attempt]
                logger.info("Retry %s dans %ds…", label, wait)
                time.sleep(wait)
        logger.error("%s : échec après %d tentatives", label, config.RETRY_MAX)
        return None

    # ------------------------------------------------------------------
    # Compte
    # ------------------------------------------------------------------

    def get_account_info(self) -> dict | None:
        """Retourne balance, equity, margin_free, currency. Retry 3x."""
        def _fetch():
            info = self.mt5.account_info()
            if info is None:
                return None
            return {
                "balance": float(info.balance),
                "equity": float(info.equity),
                "margin_free": float(info.margin_free),
                "currency": info.currency,
            }
        return self._retry(_fetch, "get_account_info")

    # ------------------------------------------------------------------
    # Bougies
    # ------------------------------------------------------------------

    def _parse_candles(self, rates) -> list[dict]:
        """Transforme le tableau numpy MT5 en liste de dicts."""
        candles = []
        for r in rates:
            dt_utc = datetime.fromtimestamp(r["time"], tz=UTC_TZ)
            candles.append({
                "time": _utc_to_paris(dt_utc),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(r["real_volume"]) if "real_volume" in r.dtype.names else 0,
                "tick_volume": int(r["tick_volume"]),
            })
        return candles

    def get_candles(self, symbol: str, count: int = 20) -> list[dict] | None:
        """Récupère les `count` dernières bougies M5 fermées. Retry 3x."""
        def _fetch():
            # count+1 pour exclure la bougie en cours (non fermée)
            rates = self.mt5.copy_rates_from_pos(symbol, self.mt5.TIMEFRAME_M5, 1, count)
            if rates is None or len(rates) == 0:
                return None
            return self._parse_candles(rates)
        result = self._retry(_fetch, f"get_candles({symbol})")
        if result is not None:
            logger.info("Récupéré %d bougies M5 pour %s", len(result), symbol)
        return result

    def get_candles_range(self, symbol: str, date_from: datetime, date_to: datetime) -> list[dict] | None:
        """Récupère les bougies M5 entre deux dates. Retry 3x."""
        def _fetch():
            # S'assurer que les dates sont en UTC pour MT5
            df = date_from.astimezone(UTC_TZ) if date_from.tzinfo else date_from.replace(tzinfo=UTC_TZ)
            dt = date_to.astimezone(UTC_TZ) if date_to.tzinfo else date_to.replace(tzinfo=UTC_TZ)
            rates = self.mt5.copy_rates_range(symbol, self.mt5.TIMEFRAME_M5, df, dt)
            if rates is None or len(rates) == 0:
                return None
            return self._parse_candles(rates)
        result = self._retry(_fetch, f"get_candles_range({symbol})")
        if result is not None:
            logger.info("Récupéré %d bougies M5 range pour %s", len(result), symbol)
        return result

    # ------------------------------------------------------------------
    # Symbole / prix
    # ------------------------------------------------------------------

    def get_symbol_info(self, symbol: str) -> dict | None:
        """Retourne les infos du symbole nécessaires au calcul du lot size."""
        def _fetch():
            info = self.mt5.symbol_info(symbol)
            if info is None:
                return None
            return {
                "trade_tick_value": float(info.trade_tick_value),
                "trade_tick_size": float(info.trade_tick_size),
                "volume_min": float(info.volume_min),
                "volume_max": float(info.volume_max),
                "volume_step": float(info.volume_step),
                "digits": int(info.digits),
            }
        return self._retry(_fetch, f"get_symbol_info({symbol})")

    def get_current_price(self, symbol: str) -> dict | None:
        """Retourne le prix actuel bid/ask."""
        def _fetch():
            tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            return {
                "bid": float(tick.bid),
                "ask": float(tick.ask),
                "time": _utc_to_paris(datetime.fromtimestamp(tick.time, tz=UTC_TZ)),
            }
        return self._retry(_fetch, f"get_current_price({symbol})")

    # ------------------------------------------------------------------
    # Ordres
    # ------------------------------------------------------------------

    def place_order(self, symbol: str, direction: str, lot_size: float,
                    entry_price: float, sl_price: float, tp_price: float) -> dict:
        """Exécute un ordre market. Retry 3x."""
        def _fetch():
            order_type = self.mt5.ORDER_TYPE_BUY if direction == "long" else self.mt5.ORDER_TYPE_SELL
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": entry_price,
                "sl": sl_price,
                "tp": tp_price,
                "deviation": 20,
                "magic": 123456,
                "comment": "bot",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            result = self.mt5.order_send(request)
            if result is None:
                return None
            if result.retcode == self.mt5.TRADE_RETCODE_DONE:
                logger.info("Ordre exécuté : %s %s %.5f lots @ %.5f — ticket #%d",
                            direction, symbol, lot_size, entry_price, result.order)
                return {
                    "success": True,
                    "order_id": int(result.order),
                    "error": None,
                }
            # Retcode != DONE → échec mais on a une réponse
            err_msg = f"retcode={result.retcode} comment={result.comment}"
            logger.warning("Ordre rejeté : %s", err_msg)
            return {"success": False, "order_id": None, "error": err_msg}

        res = self._retry(_fetch, f"place_order({symbol} {direction})")
        if res is not None:
            return res
        return {"success": False, "order_id": None, "error": "échec après retries"}

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_open_positions(self) -> list[dict]:
        """Retourne les positions ouvertes."""
        def _fetch():
            positions = self.mt5.positions_get()
            if positions is None:
                return []
            result = []
            for p in positions:
                pos_type = "long" if p.type == self.mt5.ORDER_TYPE_BUY else "short"
                result.append({
                    "ticket": int(p.ticket),
                    "symbol": p.symbol,
                    "type": pos_type,
                    "volume": float(p.volume),
                    "open_price": float(p.price_open),
                    "sl": float(p.sl),
                    "tp": float(p.tp),
                    "profit": float(p.profit),
                    "open_time": _utc_to_paris(datetime.fromtimestamp(p.time, tz=UTC_TZ)),
                })
            return result

        res = self._retry(_fetch, "get_open_positions")
        return res if res is not None else []

    def close_position(self, ticket: int) -> bool:
        """Ferme une position par son ticket. Retourne True si succès."""
        def _fetch():
            positions = self.mt5.positions_get(ticket=ticket)
            if positions is None or len(positions) == 0:
                logger.warning("Position #%d introuvable pour fermeture", ticket)
                return False
            pos = positions[0]
            close_type = self.mt5.ORDER_TYPE_SELL if pos.type == self.mt5.ORDER_TYPE_BUY else self.mt5.ORDER_TYPE_BUY
            tick = self.mt5.symbol_info_tick(pos.symbol)
            if tick is None:
                return None
            price = tick.bid if pos.type == self.mt5.ORDER_TYPE_BUY else tick.ask
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": float(pos.volume),
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": "bot_close",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            result = self.mt5.order_send(request)
            if result is None:
                return None
            if result.retcode == self.mt5.TRADE_RETCODE_DONE:
                logger.info("Position #%d fermée avec succès", ticket)
                return True
            logger.warning("Fermeture position #%d rejetée : retcode=%d %s",
                           ticket, result.retcode, result.comment)
            return False

        res = self._retry(_fetch, f"close_position(#{ticket})")
        return res is True
