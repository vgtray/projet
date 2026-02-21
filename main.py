import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, time
from logging.handlers import TimedRotatingFileHandler
from zoneinfo import ZoneInfo

from src import config, database
from src.mt5_client import MT5Client
from src.levels import LevelsCalculator
from src.confluences import ConfluenceDetector
from src.sentiment import SentimentAnalyzer
from src.groq_client import GroqAnalyzer
from src.risk import RiskManager
from src.trader import Trader
from src.monitor import TradeMonitor

PARIS_TZ = ZoneInfo(config.TIMEZONE)
NY_START = time(14, 30)
NY_END = time(21, 0)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging():
    """Configure logging fichier (rotation journalière 30j) + console."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "bot.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


# ---------------------------------------------------------------------------
# Bot principal
# ---------------------------------------------------------------------------

class TradingBot:

    def __init__(self):
        self.mt5 = MT5Client()
        self.levels_calc = LevelsCalculator(self.mt5)
        self.confluence_detector = ConfluenceDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.groq_analyzer = GroqAnalyzer()
        self.risk_manager = RiskManager(self.mt5)
        self.trader = Trader(self.mt5, self.risk_manager, database)
        self.monitor = TradeMonitor(self.mt5, database)
        self.running = False
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self):
        """Initialise DB + MT5 puis lance les 2 boucles en parallèle."""
        self.logger.info("Initialisation de la base de données…")
        database.init_db()

        self.logger.info("Connexion à MetaTrader 5…")
        if not self.mt5.connect():
            self.logger.critical("Impossible de se connecter à MT5 au démarrage")
            # On continue quand même — les boucles retenteront

        self.running = True
        self.logger.info("Bot démarré — boucles actives")

        try:
            await asyncio.gather(
                self.main_loop(),
                self.monitor_loop(),
            )
        except asyncio.CancelledError:
            self.logger.info("Boucles annulées")
        finally:
            await self.stop()

    async def stop(self):
        """Arrêt propre."""
        if not self.running:
            return
        self.running = False
        self.mt5.disconnect()
        self.logger.info("Bot arrêté proprement")

    # ------------------------------------------------------------------
    # Boucle principale — toutes les 10 s
    # ------------------------------------------------------------------

    async def main_loop(self):
        """Vérifie chaque asset toutes les 10 s ; analyse uniquement sur nouvelle bougie M5."""
        while self.running:
            for symbol in config.ASSETS:
                try:
                    await self._check_and_analyze(symbol)
                except Exception as exc:
                    self.logger.error("Erreur main_loop pour %s : %s", symbol, exc)

            await asyncio.sleep(config.CANDLE_CHECK_INTERVAL)

    async def _check_and_analyze(self, symbol: str):
        """Fetch les bougies, compare le timestamp, lance l'analyse si nouvelle bougie."""
        if not self.mt5.is_connected():
            self.logger.error("MT5 déconnecté, tentative de reconnexion…")
            if not self.mt5.connect():
                self.logger.error("Reconnexion MT5 échouée, skip %s", symbol)
                return

        candles = await asyncio.to_thread(self.mt5.get_candles, symbol, config.CANDLES_COUNT)
        if not candles:
            self.logger.warning("Aucune bougie récupérée pour %s", symbol)
            return

        last_candle_ts = str(candles[-1]["time"])

        last_analyzed = await asyncio.to_thread(database.get_last_analyzed_timestamp, symbol)

        if last_candle_ts == last_analyzed:
            return  # Pas de nouvelle bougie

        # Nouvelle bougie détectée
        now_paris = datetime.now(PARIS_TZ).time()
        in_ny = NY_START <= now_paris <= NY_END

        if not in_ny:
            self.logger.info("New M5 candle detected for %s (no analysis - outside NY session)", symbol)
            await asyncio.to_thread(database.set_last_analyzed_timestamp, symbol, last_candle_ts)
            return

        self.logger.info("New M5 candle detected for %s", symbol)
        await self.analyze_asset(symbol, candles)
        await asyncio.to_thread(database.set_last_analyzed_timestamp, symbol, last_candle_ts)

    # ------------------------------------------------------------------
    # Analyse complète — flux section 13 SPEC
    # ------------------------------------------------------------------

    async def analyze_asset(self, symbol: str, candles: list[dict]):
        """Pipeline complet : niveaux → confluences → sentiment → Groq → exécution."""

        # Prix actuel
        price_data = await asyncio.to_thread(self.mt5.get_current_price, symbol)
        if price_data is None:
            self.logger.error("Impossible de récupérer le prix pour %s", symbol)
            return
        current_price = price_data["bid"]
        self.logger.info("Analysing %s at %.5f", symbol, current_price)

        # 1. Niveaux
        levels = await asyncio.to_thread(self.levels_calc.get_levels, symbol)

        # 2. Confluences
        confluences = self.confluence_detector.detect_all(candles, levels, current_price)

        # 3. Sentiment (news + Reddit)
        sentiment = await asyncio.to_thread(self.sentiment_analyzer.get_sentiment, symbol)

        # 4. Stats de perf (par pattern)
        perf_stats = {}
        for pattern in ["FVG", "OB", "iFVG", "BB", "sweep", "FVG+sweep", "OB+sweep"]:
            stats = await asyncio.to_thread(database.get_performance_stats, symbol, pattern)
            if stats:
                perf_stats[pattern] = stats

        # 5. Compteur journalier
        today = datetime.now(PARIS_TZ).date()
        daily_count = await asyncio.to_thread(database.get_daily_trade_count, symbol, today)

        # 6. Groq
        signal_result = await asyncio.to_thread(
            self.groq_analyzer.analyze,
            symbol, current_price, candles, levels,
            confluences, sentiment, perf_stats, daily_count,
        )

        self.logger.info(
            "Signal: %s | Valid: %s | Confidence: %s%%",
            signal_result.get("direction", "none"),
            signal_result.get("trade_valid", False),
            signal_result.get("confidence", 0),
        )

        # 7. Sauvegarder le signal en DB (même si non valide)
        signal_data = {
            "asset": symbol,
            "timestamp": datetime.now(PARIS_TZ),
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
            "reason": signal_result.get("reason", ""),
            "executed": False,
        }
        await asyncio.to_thread(database.save_signal, signal_data)

        # 8. Si non valide → warning et stop
        if not signal_result.get("trade_valid"):
            self.logger.warning(
                "Setup detected but conditions not met for %s — %s",
                symbol, signal_result.get("reason", ""),
            )
            return

        # 9. Déduplication
        is_dup = await asyncio.to_thread(
            database.check_duplicate_signal,
            symbol,
            signal_result.get("direction", ""),
            signal_result.get("sweep_level", ""),
        )
        if is_dup:
            self.logger.info("Duplicate signal skipped for %s", symbol)
            return

        # 10. Exécution MT5
        executed = await asyncio.to_thread(self.trader.execute_if_valid, signal_result)
        if executed:
            entry = signal_result.get("entry_price")
            sl = signal_result.get("sl_price")
            tp = signal_result.get("tp_price")
            self.logger.info(
                "Trade executed: %s @ %.5f, SL: %.5f, TP: %.5f",
                symbol, entry, sl, tp,
            )

    # ------------------------------------------------------------------
    # Boucle monitoring — toutes les 30 s
    # ------------------------------------------------------------------

    async def monitor_loop(self):
        """Vérifie les trades ouverts toutes les 30 s."""
        while self.running:
            try:
                await asyncio.to_thread(self.monitor.check_open_trades)
            except Exception as exc:
                self.logger.error("Erreur monitor_loop : %s", exc)

            await asyncio.sleep(config.MONITOR_INTERVAL)


# ---------------------------------------------------------------------------
# Arrêt propre via signaux système
# ---------------------------------------------------------------------------

_bot_instance: TradingBot | None = None


def handle_shutdown(signum, frame):
    """Handler SIGINT / SIGTERM → arrêt propre."""
    logger = logging.getLogger(__name__)
    sig_name = signal.Signals(signum).name
    logger.info("Signal %s reçu — arrêt en cours…", sig_name)

    if _bot_instance is not None:
        _bot_instance.running = False

    # Annuler les tâches asyncio en cours
    loop = asyncio.get_event_loop()
    if loop.is_running():
        for task in asyncio.all_tasks(loop):
            task.cancel()


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("Mobyr Trade Bot - Démarrage")
    logger.info("Assets: %s", config.ASSETS)
    logger.info("Session NY: %s - %s Paris", config.NY_SESSION_START, config.NY_SESSION_END)
    logger.info("=" * 50)

    bot = TradingBot()
    _bot_instance = bot

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    asyncio.run(bot.start())
