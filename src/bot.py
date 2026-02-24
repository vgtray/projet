"""Boucle principale du bot de trading SMC/ICT.

Orchestre tous les modules : MT5, niveaux clés, confluences, indicateurs,
sentiment, LLM, base de données. Deux boucles parallèles :
1. Analyse toutes les 10s (sur nouvelle bougie M5)
2. Monitoring des trades ouverts toutes les 30s

Ref: SPEC.md sections 14, 8, 16, 19.
"""

import logging
import signal
import threading
import time
from datetime import datetime, date, timedelta
from typing import Optional

import pytz

from src.config import Config
from src.database import Database
from src.mt5_client import MT5Client
from src.key_levels import KeyLevels
from src.confluences import ConfluenceDetector
from src.indicators import Indicators
from src.sentiment import SentimentAnalyzer
from src.llm_client import LLMClient
from src.logging_setup import setup_logging

logger = logging.getLogger(__name__)

PARIS_TZ = pytz.timezone(Config.TIMEZONE)


class TradingBot:
    """Bot de trading SMC/ICT — cœur de l'orchestration."""

    def __init__(self):
        self.config = Config
        self.db = Database()
        self.mt5 = MT5Client(host=Config.MT5_HOST, port=Config.MT5_PORT)
        self.key_levels = KeyLevels()
        self.confluences = ConfluenceDetector()
        self.indicators = Indicators()
        self.sentiment = SentimentAnalyzer()
        self.llm = LLMClient()
        self.running = False
        self._last_analyzed: dict[str, str] = {}
        self._threads: list[threading.Thread] = []

    def start(self):
        """Démarre le bot : logging, connexions, boucles parallèles, shutdown."""
        setup_logging()  # console + file uniquement (DB pas encore connectée)
        logger.info("=== Démarrage du bot SMC/ICT ===")

        self.db.connect()
        self.db.init_schema()
        setup_logging(db=self.db)  # re-setup en ajoutant le handler DB

        if not self.mt5.connect():
            logger.critical("Impossible de connecter MT5 — arrêt du bot")
            self.db.disconnect()
            return

        self._load_state()
        self.running = True

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        analysis_thread = threading.Thread(
            target=self._analysis_loop, name="analysis", daemon=True
        )
        monitoring_thread = threading.Thread(
            target=self._monitoring_loop, name="monitoring", daemon=True
        )
        self._threads = [analysis_thread, monitoring_thread]

        analysis_thread.start()
        monitoring_thread.start()

        logger.info("Boucles démarrées — analyse (10s) + monitoring (30s)")
        logger.info("Assets : %s | Session NY : 14h30-21h00 Paris", Config.ASSETS)

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Arrête le bot proprement."""
        if not self.running:
            return
        self.running = False
        logger.info("Arrêt du bot en cours...")

        for t in self._threads:
            t.join(timeout=5)

        self.mt5.disconnect()
        self.db.disconnect()
        logger.info("=== Bot arrêté proprement ===")

    def _signal_handler(self, signum, frame):
        """Gère SIGINT/SIGTERM pour un arrêt propre."""
        sig_name = signal.Signals(signum).name
        logger.info("Signal %s reçu — arrêt demandé", sig_name)
        self.running = False

    def _load_state(self):
        """Charge l'état persisté depuis la DB (last_analyzed par asset)."""
        for asset in Config.ASSETS:
            key = f"last_analyzed_{asset}"
            value = self.db.get_bot_state(key)
            self._last_analyzed[asset] = value or ""
            if value:
                logger.info("État restauré : %s = %s", key, value)

    # ── Boucle d'analyse ─────────────────────────────────────────────

    def _analysis_loop(self):
        """Boucle d'analyse : vérifie chaque asset toutes les 10 secondes."""
        while self.running:
            try:
                paused = self.db.get_bot_state("bot_paused")
                if paused == "true":
                    logger.info("Bot en pause — analyse suspendue")
                    time.sleep(10)
                    continue
            except Exception:
                pass

            for asset in Config.ASSETS:
                try:
                    self._analyze_asset(asset)
                except Exception as e:
                    logger.error("Erreur analyse %s : %s", asset, e, exc_info=True)
            time.sleep(10)

    def _analyze_asset(self, asset: str):
        """Analyse complète d'un asset si nouvelle bougie M5 détectée."""
        # 1. Fetch dernières bougies M5
        candles = self.mt5.get_candles(asset, "M5", 20)
        if candles is None or candles.empty:
            logger.warning("Pas de données M5 pour %s — skip", asset)
            return

        # 2. Comparer timestamp avec last_analyzed
        last_candle_time = candles["time"].iloc[-1]
        last_ts = str(last_candle_time)
        if last_ts == self._last_analyzed.get(asset, ""):
            return

        # 4. Nouvelle bougie détectée
        current_price_data = self.mt5.get_current_price(asset)
        current_price = current_price_data["bid"] if current_price_data else float(candles["close"].iloc[-1])
        logger.info("New M5 candle detected for %s — prix: %.5f", asset, current_price)

        # 5. Vérifier session NY
        now_paris = datetime.now(PARIS_TZ)
        if not Config.is_ny_session(now_paris):
            logger.info("Hors session NY pour %s — skip", asset)
            self._last_analyzed[asset] = last_ts
            self.db.set_bot_state(f"last_analyzed_{asset}", last_ts)
            return

        # 6. Anti-overtrade
        today = now_paris.date()
        daily_count = self.db.get_daily_trade_count(asset, today)
        if daily_count >= Config.MAX_TRADES_PER_DAY:
            logger.info("Max trades atteint pour %s (%d/%d) — skip",
                        asset, daily_count, Config.MAX_TRADES_PER_DAY)
            self._last_analyzed[asset] = last_ts
            self.db.set_bot_state(f"last_analyzed_{asset}", last_ts)
            return

        # 7. Niveaux clés (besoin de plus de bougies pour Asia/London/PrevDay)
        candles_extended = self.mt5.get_candles(asset, "M5", 500)
        if candles_extended is None or candles_extended.empty:
            candles_extended = candles
        key_levels = self.key_levels.calculate_all(candles_extended, now_paris, asset)

        # 8. Confluences
        confluences = self.confluences.detect_all(candles)

        # 9. Sweep
        sweep_info = self.key_levels.detect_sweep(current_price, key_levels, candles)

        # 10. Indicateurs (EMA 50/200 nécessitent 200+ bougies)
        candles_long = self.mt5.get_candles(asset, "M5", 250)
        if candles_long is not None and not candles_long.empty:
            indicators = self.indicators.calculate_all(candles_long)
        else:
            indicators = self.indicators.calculate_all(candles)

        # 11. Sentiment
        sentiment = self.sentiment.get_all_sentiment(asset)

        # 12. Stats de performance
        perf_history = {}
        for pattern in ("reversal", "continuation"):
            stats = self.db.get_performance_stats(pattern, asset)
            if stats:
                perf_history[pattern] = stats

        # 13. Construire le dict data pour le LLM (spec section 10)
        candles_list = []
        for _, row in candles.iterrows():
            candles_list.append({
                "open": round(float(row["open"]), 5),
                "high": round(float(row["high"]), 5),
                "low": round(float(row["low"]), 5),
                "close": round(float(row["close"]), 5),
                "volume": int(row["volume"]),
            })

        # Aplatir les confluences en une seule liste pour le LLM
        confluences_flat = []
        for zone_type in ("fvg", "ifvg", "ob", "bb"):
            for zone in confluences.get(zone_type, []):
                confluences_flat.append({
                    "type": zone.get("type", zone_type),
                    "high": zone.get("top") or zone.get("high"),
                    "low": zone.get("bottom") or zone.get("low"),
                })

        ema_data = indicators.get("ema", {})
        macd_data = indicators.get("macd", {})

        data = {
            "asset": asset,
            "current_time_paris": now_paris.strftime("%Y-%m-%d %H:%M:%S"),
            "current_price": current_price,
            "candles": candles_list,
            "indicators": {
                "rsi": indicators.get("rsi"),
                "macd_line": macd_data.get("macd"),
                "macd_signal": macd_data.get("signal"),
                "macd_hist": macd_data.get("histogram"),
                "ema20": ema_data.get("ema_20"),
                "ema50": ema_data.get("ema_50"),
                "ema200": ema_data.get("ema_200"),
            },
            "key_levels": key_levels,
            "confluences": confluences_flat,
            "sweep_info": sweep_info,
            "news_sentiment": sentiment.get("news_sentiment", "neutral"),
            "social_sentiment": sentiment.get("social_sentiment", "neutral"),
            "performance_history": perf_history,
            "daily_trade_count": daily_count,
        }

        # 14. Appel LLM
        signal_result = self.llm.analyze(data)

        # 15. Log
        logger.info(
            "Signal %s — direction: %s | valid: %s | confidence: %s%% | scenario: %s | llm: %s",
            asset,
            signal_result.get("direction"),
            signal_result.get("trade_valid"),
            signal_result.get("confidence"),
            signal_result.get("scenario"),
            signal_result.get("llm_used"),
        )

        # 16. Sauvegarder le signal en DB
        signal_record = {
            "asset": asset,
            "timestamp": now_paris,
            "direction": signal_result.get("direction"),
            "scenario": signal_result.get("scenario"),
            "confidence": signal_result.get("confidence"),
            "entry_price": signal_result.get("entry_price"),
            "sl_price": signal_result.get("sl_price"),
            "tp_price": signal_result.get("tp_price"),
            "rr_ratio": signal_result.get("rr_ratio"),
            "confluences_used": signal_result.get("confluences_used", []),
            "sweep_level": signal_result.get("sweep_level"),
            "news_sentiment": signal_result.get("news_sentiment"),
            "social_sentiment": signal_result.get("social_sentiment"),
            "trade_valid": signal_result.get("trade_valid", False),
            "reason": signal_result.get("reason"),
            "executed": False,
            "llm_used": signal_result.get("llm_used"),
        }
        signal_id = self.db.save_signal(signal_record)

        # 17. Exécution si trade_valid
        if signal_result.get("trade_valid"):
            direction = signal_result.get("direction")
            sweep_level = signal_result.get("sweep_level")

            # 17a. Déduplication — vérifier les trades exécutés, pas les signaux
            if self.db.check_duplicate_trade(asset, direction, Config.DEDUP_WINDOW_MINUTES):
                logger.info("Duplicate trade skipped — %s %s", asset, direction)
                self._last_analyzed[asset] = last_ts
                self.db.set_bot_state(f"last_analyzed_{asset}", last_ts)
                return

            entry_price = signal_result.get("entry_price")
            sl_price = signal_result.get("sl_price")
            tp_price = signal_result.get("tp_price")

            if entry_price is None or sl_price is None or tp_price is None:
                logger.warning("Signal valide mais prix manquants — skip exécution")
                self._last_analyzed[asset] = last_ts
                self.db.set_bot_state(f"last_analyzed_{asset}", last_ts)
                return

            # 17b. Lot size
            lot_size = self.mt5.calculate_lot_size(asset, entry_price, sl_price)
            if lot_size is None:
                logger.error("Calcul lot size échoué pour %s — skip exécution", asset)
                self._last_analyzed[asset] = last_ts
                self.db.set_bot_state(f"last_analyzed_{asset}", last_ts)
                return

            # 17c. Exécution
            comment = f"SMC {direction} {asset}"
            trade_result = self.mt5.open_trade(
                symbol=asset,
                direction=direction,
                lot_size=lot_size,
                sl_price=sl_price,
                tp_price=tp_price,
                comment=comment,
            )

            if trade_result and trade_result.get("retcode") == 10009:  # TRADE_RETCODE_DONE
                logger.info(
                    "Trade executed: %s @ %.5f, SL: %.5f, TP: %.5f, lot: %.5f, ticket: %s",
                    asset, trade_result.get("price", entry_price),
                    sl_price, tp_price, lot_size, trade_result.get("ticket"),
                )

                # 17d. Sauvegarder le trade en DB
                mt5_ticket = trade_result.get("order") or trade_result.get("ticket")
                trade_record = {
                    "signal_id": signal_id,
                    "asset": asset,
                    "entry_time": now_paris,
                    "direction": direction,
                    "entry_price": trade_result.get("price", entry_price),
                    "sl_price": sl_price,
                    "tp_price": tp_price,
                    "lot_size": lot_size,
                    "mt5_ticket": mt5_ticket,
                    "status": "open",
                }
                self.db.save_trade(trade_record)

                # Marquer le signal comme exécuté
                if signal_id:
                    try:
                        with self.db.conn.cursor() as cur:
                            cur.execute(
                                "UPDATE signals SET executed = TRUE WHERE id = %s",
                                (signal_id,),
                            )
                    except Exception as e:
                        logger.error("Erreur marquage signal executed : %s", e)
            else:
                logger.error("Exécution trade échouée pour %s — result: %s", asset, trade_result)

        # 18. Mettre à jour last_analyzed
        self._last_analyzed[asset] = last_ts
        self.db.set_bot_state(f"last_analyzed_{asset}", last_ts)

    # ── Boucle de monitoring ─────────────────────────────────────────

    def _monitoring_loop(self):
        """Boucle de monitoring des trades ouverts toutes les 30 secondes."""
        while self.running:
            try:
                self._check_open_trades()
            except Exception as e:
                logger.error("Erreur monitoring trades : %s", e, exc_info=True)
            time.sleep(30)

    def _check_open_trades(self):
        """Vérifie si des trades ouverts ont été fermés par TP/SL."""
        # 1. Positions ouvertes MT5
        mt5_positions = self.mt5.get_open_positions()
        mt5_tickets = {pos["ticket"] for pos in mt5_positions}

        # 2. Trades ouverts en DB
        db_trades = self.db.get_open_trades()
        if not db_trades:
            return

        for trade in db_trades:
            trade_id = trade["id"]
            signal_id = trade.get("signal_id")
            asset = trade["asset"]
            direction = trade["direction"]
            entry_price = float(trade["entry_price"])
            sl_price = float(trade["sl_price"]) if trade.get("sl_price") else None
            tp_price = float(trade["tp_price"]) if trade.get("tp_price") else None
            mt5_ticket = trade.get("mt5_ticket")

            # Matcher via le ticket MT5 stocké en DB
            position_found = False
            if mt5_ticket and mt5_ticket in mt5_tickets:
                position_found = True
            else:
                # Fallback : matching par comment/prix si pas de ticket
                for pos in mt5_positions:
                    if (pos.get("comment", "").find(asset) >= 0 and
                            abs(pos["price_open"] - entry_price) < 1.0):
                        position_found = True
                        break

            if position_found:
                continue  # Trade encore ouvert

            # 3. Position fermée — récupérer les détails depuis l'historique MT5
            try:
                exit_price, pnl = self._get_closed_trade_details(asset, entry_price, direction, mt5_ticket)
            except Exception as e:
                logger.error("Erreur récupération détails trade fermé id=%s : %s", trade_id, e)
                continue

            if exit_price is None:
                # Pas trouvé dans l'historique — peut-être encore en cours
                continue

            # 4. Déterminer la raison de fermeture
            closed_reason = "tp" if pnl > 0 else "sl"

            # 5. Mettre à jour le trade en DB
            now_paris = datetime.now(PARIS_TZ)
            self.db.update_trade(trade_id, {
                "exit_price": exit_price,
                "exit_time": now_paris,
                "pnl": pnl,
                "status": "closed",
                "closed_reason": closed_reason,
            })

            # 6. Incrémenter le compteur journalier
            self.db.increment_daily_trade_count(asset, now_paris.date())

            # 7. Mettre à jour les stats de performance
            rr_ratio = 0.0
            if sl_price and tp_price:
                sl_distance = abs(entry_price - sl_price)
                if sl_distance > 0:
                    rr_ratio = abs(exit_price - entry_price) / sl_distance

            # Déterminer le pattern depuis le signal
            pattern_type = "unknown"
            if signal_id:
                try:
                    with self.db.conn.cursor() as cur:
                        cur.execute("SELECT scenario FROM signals WHERE id = %s", (signal_id,))
                        row = cur.fetchone()
                        if row and row[0]:
                            pattern_type = row[0]
                except Exception as e:
                    logger.error("Erreur lecture scenario signal id=%s : %s", signal_id, e)

            self.db.update_performance_stats(
                pattern_type=pattern_type,
                asset=asset,
                won=pnl > 0,
                rr=round(rr_ratio, 2),
                pnl=round(pnl, 2),
            )

            logger.info(
                "Trade fermé — id=%s %s %s | PnL: %.2f | Raison: %s | RR: %.2f",
                trade_id, direction.upper(), asset, pnl, closed_reason, rr_ratio,
            )

    def _get_closed_trade_details(
        self, asset: str, entry_price: float, direction: str,
        mt5_ticket: Optional[int] = None
    ) -> tuple:
        """Récupère le prix de sortie et le PnL d'un trade fermé via l'historique MT5.

        Args:
            asset: Symbole de l'asset.
            entry_price: Prix d'entrée du trade.
            direction: Direction du trade ("long" ou "short").
            mt5_ticket: Ticket MT5 pour matching précis par position_id.

        Returns:
            Tuple (exit_price, pnl) ou (None, None) si non trouvé.
        """
        if not self.mt5.is_connected():
            return None, None

        try:
            now = datetime.now(PARIS_TZ)
            from_date = now - timedelta(days=1)

            deals = self.mt5.get_history_deals(from_date, now)
            if not deals:
                return None, None

            for deal in reversed(deals):
                if deal.magic != Config.BOT_MAGIC:
                    continue
                # Chercher un deal de fermeture (entry=1:out)
                if deal.entry != 1:
                    continue
                # Matcher par position_id (ticket MT5 stocké en DB)
                if mt5_ticket and hasattr(deal, "position_id") and deal.position_id == mt5_ticket:
                    return float(deal.price), float(deal.profit)
                # Fallback : tolérance relative (0.5% du prix) si pas de ticket
                tolerance = entry_price * 0.005
                if abs(deal.price - entry_price) <= tolerance:
                    return float(deal.price), float(deal.profit)

            return None, None

        except Exception as e:
            logger.error("Erreur history_deals_get : %s", e)
            return None, None
