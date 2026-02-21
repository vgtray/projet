import json
import logging
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from groq import Groq

from . import config

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "asset", "direction", "scenario", "confidence",
    "entry_price", "sl_price", "tp_price", "rr_ratio",
    "confluences_used", "sweep_level",
    "news_sentiment", "social_sentiment",
    "trade_valid", "reason",
]

FIELD_DEFAULTS = {
    "asset": "UNKNOWN",
    "direction": "none",
    "scenario": "none",
    "confidence": 0,
    "entry_price": None,
    "sl_price": None,
    "tp_price": None,
    "rr_ratio": None,
    "confluences_used": [],
    "sweep_level": "none",
    "news_sentiment": "neutral",
    "social_sentiment": "neutral",
    "trade_valid": False,
    "reason": "champ manquant complété par défaut",
}


class GroqAnalyzer:

    def __init__(self):
        self._client = Groq(api_key=config.GROQ_API_KEY)
        self._model = "llama-3.3-70b-versatile"

    # ------------------------------------------------------------------
    # Point d'entrée
    # ------------------------------------------------------------------

    def analyze(
        self,
        symbol: str,
        current_price: float,
        candles: list[dict],
        levels: dict,
        confluences: dict,
        sentiment: dict,
        perf_stats: dict,
        daily_trade_count: int,
    ) -> dict:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            symbol, current_price, candles, levels,
            confluences, sentiment, perf_stats, daily_trade_count,
        )

        raw = self._call_groq(system_prompt, user_prompt)
        if raw is None:
            return self._get_default_response(symbol, "groq_unavailable")

        result = self._parse_response(raw)
        if result is None:
            return self._get_default_response(symbol, "parse_error")

        result.setdefault("asset", symbol)
        logger.info(
            "Analyse %s — direction=%s confidence=%s trade_valid=%s",
            symbol,
            result.get("direction"),
            result.get("confidence"),
            result.get("trade_valid"),
        )
        return result

    # ------------------------------------------------------------------
    # Prompt système (section 20 SPEC)
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        return (
            "Tu es un algorithme de trading expert basé sur la stratégie Trade (SMC/ICT).\n"
            "\n"
            "## ASSETS TRADÉS\n"
            "- XAUUSD (Or spot CFD)\n"
            "- NAS100 (Nasdaq 100 Cash CFD)\n"
            "Timeframe : M5\n"
            "Risque par trade : 1% du capital\n"
            "\n"
            "## SESSION DE TRADING\n"
            "Tu trades UNIQUEMENT pendant la session New York (14h30 - 21h00 heure de Paris).\n"
            "Asia et London préparent le marché. New York fait le vrai mouvement.\n"
            'En dehors de New York → {"direction": "none", "reason": "hors session"}\n'
            "\n"
            "## NIVEAUX CLÉS (fournis à chaque analyse)\n"
            "- Asia High / Asia Low (00h00 - 09h00 Paris)\n"
            "- London High / London Low (09h00 - 14h30 Paris)\n"
            "- Previous Day High / Previous Day Low\n"
            "Ces niveaux sont fixes pour la journée.\n"
            "Le marché les dépasse souvent pour prendre les stops avant de réagir.\n"
            "\n"
            "## CONFLUENCES REQUISES\n"
            "Tu ne trades JAMAIS sans confluence. Confluences valides :\n"
            "- FVG (Fair Value Gap) : vide créé par mouvement rapide, 3 bougies, zone de retour du prix\n"
            "- iFVG (Inverse FVG) : FVG cassée qui devient zone de blocage ou continuation\n"
            "- OB (Order Block) : dernière bougie opposée avant un fort mouvement directionnel\n"
            "- BB (Breaker Block) : ancien OB cassé qui change de rôle\n"
            "\n"
            "## 3 CONDITIONS OBLIGATOIRES POUR ENTRER\n"
            "\n"
            "1. Un niveau clé a été dépassé → Liquidity Sweep confirmé\n"
            "2. Le prix revient dans une confluence (FVG, OB, iFVG)\n"
            "3. Bougie de confirmation franche dans le sens du trade\n"
            "\n"
            "Si une seule condition manque → trade_valid: false\n"
            "\n"
            "## 2 SCÉNARIOS POSSIBLES\n"
            "\n"
            "Scénario 1 - Reversal :\n"
            "Le marché dépasse un niveau puis repart dans l'autre sens.\n"
            "Les traders piégés ferment → on trade dans le sens inverse du sweep.\n"
            "Cible : prochain high ou low visible opposed.\n"
            "\n"
            "Scénario 2 - Continuation :\n"
            "Le marché dépasse un niveau et continue dans le même sens.\n"
            "La tendance est forte, pas de reversal.\n"
            "Cible : prochain high ou low dans le sens du mouvement.\n"
            "\n"
            "## STOP LOSS ET TAKE PROFIT\n"
            "- SL : derrière le niveau dépassé (là où l'idée est invalidée)\n"
            "- TP : prochain key level visible sur le graphique (Asia/London/PrevDay high ou low)\n"
            "- Ne jamais inventer des niveaux\n"
            "\n"
            "## RÈGLE ANTI-OVERTRADE\n"
            "- Maximum 2 trades par jour par asset\n"
            "- Après 2 trades (TP ou SL) → stop jusqu'au lendemain\n"
            "- Pas de setup valide = on ne trade pas\n"
            "- La patience est une position\n"
            "\n"
            "## DONNÉES REÇUES À CHAQUE ANALYSE\n"
            "- Asset + heure exacte (timezone Paris)\n"
            "- Prix actuel + OHLCV des 20 dernières bougies M5\n"
            "- RSI, MACD, EMA 20/50/200\n"
            "- Asia High/Low, London High/Low, PrevDay High/Low\n"
            "- Confluences détectées : FVG, OB, iFVG, sweep (calculés algorithmiquement)\n"
            "- News récentes sur l'asset (NewsAPI)\n"
            "- Sentiment Reddit (r/Forex, r/Gold pour XAUUSD / r/investing, r/stocks pour NAS100)\n"
            "- Stats de performances passées pour patterns similaires\n"
            "\n"
            "## FORMAT DE RÉPONSE OBLIGATOIRE\n"
            "Réponds UNIQUEMENT en JSON valide, rien d'autre :\n"
            "\n"
            "{\n"
            '  "asset": "XAUUSD | NAS100",\n'
            '  "direction": "long | short | none",\n'
            '  "scenario": "reversal | continuation | unclear | none",\n'
            '  "confidence": 0-100,\n'
            '  "entry_price": float ou null,\n'
            '  "sl_price": float ou null,\n'
            '  "tp_price": float ou null,\n'
            '  "rr_ratio": float ou null,\n'
            '  "confluences_used": ["FVG", "OB", "sweep", ...],\n'
            '  "sweep_level": "asia_high | asia_low | london_high | london_low | prev_high | prev_low | none",\n'
            '  "news_sentiment": "bullish | bearish | neutral",\n'
            '  "social_sentiment": "bullish | bearish | neutral",\n'
            '  "trade_valid": true | false,\n'
            '  "reason": "explication courte en français"\n'
            "}\n"
            "\n"
            "Si trade_valid est false → entry_price, sl_price, tp_price, rr_ratio sont null.\n"
            "Ne jamais halluciner des niveaux ou des confluences non présents dans les données reçues."
        )

    # ------------------------------------------------------------------
    # Prompt utilisateur
    # ------------------------------------------------------------------

    def _build_user_prompt(
        self,
        symbol: str,
        current_price: float,
        candles: list[dict],
        levels: dict,
        confluences: dict,
        sentiment: dict,
        perf_stats: dict,
        daily_trade_count: int,
    ) -> str:
        now_paris = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")

        # --- Niveaux clés ---
        asia_high = levels.get("asia_high", "N/A")
        asia_low = levels.get("asia_low", "N/A")
        london_high = levels.get("london_high", "N/A")
        london_low = levels.get("london_low", "N/A")
        prev_day_high = levels.get("prev_day_high", "N/A")
        prev_day_low = levels.get("prev_day_low", "N/A")

        # --- Confluences ---
        fvg_list = confluences.get("fvg", [])
        ob_list = confluences.get("ob", [])
        ifvg_list = confluences.get("ifvg", [])
        bb_list = confluences.get("bb", [])
        sweep = confluences.get("sweep", "aucun")
        active = confluences.get("active_confluences", [])

        fvg_str = _format_zones(fvg_list) if fvg_list else "aucun"
        ob_str = _format_zones(ob_list) if ob_list else "aucun"
        ifvg_str = _format_zones(ifvg_list) if ifvg_list else "aucun"
        bb_str = _format_zones(bb_list) if bb_list else "aucun"
        active_str = ", ".join(str(a) for a in active) if active else "aucune"

        # --- Bougies ---
        candle_header = "time               | open      | high      | low       | close     | volume"
        candle_sep = "-" * len(candle_header)
        candle_rows = []
        for c in candles:
            candle_rows.append(
                f"{c.get('time', '')} | {c.get('open', '')} | {c.get('high', '')} | "
                f"{c.get('low', '')} | {c.get('close', '')} | {c.get('volume', '')}"
            )
        candle_table = "\n".join([candle_header, candle_sep, *candle_rows])

        # --- Sentiment ---
        news_sent = sentiment.get("news", "neutral")
        social_sent = sentiment.get("social", "neutral")

        # --- Performances passées ---
        if perf_stats:
            perf_lines = []
            for pattern, stats in perf_stats.items():
                if stats:
                    perf_lines.append(
                        f"  {pattern} : {stats.get('total_trades', 0)} trades, "
                        f"winrate {stats.get('win_rate', 0)}%, "
                        f"RR moyen {stats.get('avg_rr', 0)}, "
                        f"PnL total {stats.get('total_pnl', 0)}"
                    )
            perf_str = "\n".join(perf_lines) if perf_lines else "Pas encore de données"
        else:
            perf_str = "Pas encore de données"

        return (
            f"=== ANALYSE TRADING - {symbol} ===\n"
            f"Heure Paris : {now_paris}\n"
            f"Prix actuel : {current_price}\n"
            f"\n"
            f"=== NIVEAUX CLÉS ===\n"
            f"Asia High: {asia_high} | Asia Low: {asia_low}\n"
            f"London High: {london_high} | London Low: {london_low}\n"
            f"Prev Day High: {prev_day_high} | Prev Day Low: {prev_day_low}\n"
            f"\n"
            f"=== CONFLUENCES DÉTECTÉES ===\n"
            f"FVG actifs: {fvg_str}\n"
            f"OB actifs: {ob_str}\n"
            f"iFVG actifs: {ifvg_str}\n"
            f"BB actifs: {bb_str}\n"
            f"Sweep détecté: {sweep}\n"
            f"Confluences où le prix est actuellement: {active_str}\n"
            f"\n"
            f"=== BOUGIES M5 (20 dernières) ===\n"
            f"{candle_table}\n"
            f"\n"
            f"=== SENTIMENT ===\n"
            f"News: {news_sent}\n"
            f"Social (Reddit): {social_sent}\n"
            f"\n"
            f"=== PERFORMANCES PASSÉES (patterns similaires) ===\n"
            f"{perf_str}\n"
            f"\n"
            f"=== COMPTEUR JOURNALIER ===\n"
            f"Trades fermés aujourd'hui: {daily_trade_count}/{config.MAX_TRADES_PER_DAY}\n"
            f"\n"
            f"Analyse le marché et réponds UNIQUEMENT en JSON valide."
        )

    # ------------------------------------------------------------------
    # Appel Groq avec retry
    # ------------------------------------------------------------------

    def _call_groq(self, system_prompt: str, user_prompt: str) -> str | None:
        for attempt in range(config.RETRY_MAX):
            try:
                logger.info("Appel Groq (tentative %d/%d)", attempt + 1, config.RETRY_MAX)
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1024,
                )
                usage = response.usage
                if usage:
                    logger.info(
                        "Groq tokens — prompt: %d, completion: %d, total: %d",
                        usage.prompt_tokens,
                        usage.completion_tokens,
                        usage.total_tokens,
                    )
                return response.choices[0].message.content

            except Exception as exc:
                wait = config.RETRY_BACKOFF[attempt] if attempt < len(config.RETRY_BACKOFF) else config.RETRY_BACKOFF[-1]
                logger.error(
                    "Groq API indisponible (tentative %d/%d) : %s — retry dans %ds",
                    attempt + 1, config.RETRY_MAX, exc, wait,
                )
                if attempt < config.RETRY_MAX - 1:
                    time.sleep(wait)

        logger.error("Groq API échouée après %d tentatives", config.RETRY_MAX)
        return None

    # ------------------------------------------------------------------
    # Parsing réponse
    # ------------------------------------------------------------------

    def _parse_response(self, response: str) -> dict | None:
        try:
            # Extraire le JSON même si entouré de texte ou de ```
            cleaned = response.strip()
            json_match = re.search(r"\{[\s\S]*\}", cleaned)
            if not json_match:
                logger.error("Aucun JSON trouvé dans la réponse Groq")
                return None
            data = json.loads(json_match.group())
        except json.JSONDecodeError as exc:
            logger.error("Erreur parsing JSON Groq : %s", exc)
            return None

        # Compléter les champs manquants
        for field in REQUIRED_FIELDS:
            if field not in data:
                logger.warning("Champ manquant dans la réponse Groq : %s — valeur par défaut appliquée", field)
                data[field] = FIELD_DEFAULTS[field]

        # Forcer nulls si trade_valid == false
        if not data.get("trade_valid"):
            data["entry_price"] = None
            data["sl_price"] = None
            data["tp_price"] = None
            data["rr_ratio"] = None

        return data

    # ------------------------------------------------------------------
    # Réponse par défaut
    # ------------------------------------------------------------------

    def _get_default_response(self, symbol: str, reason: str) -> dict:
        return {
            "asset": symbol,
            "direction": "none",
            "scenario": "none",
            "confidence": 0,
            "entry_price": None,
            "sl_price": None,
            "tp_price": None,
            "rr_ratio": None,
            "confluences_used": [],
            "sweep_level": "none",
            "news_sentiment": "neutral",
            "social_sentiment": "neutral",
            "trade_valid": False,
            "reason": reason,
        }


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _format_zones(zones: list) -> str:
    """Formate une liste de zones (FVG/OB/etc.) en string lisible."""
    if not zones:
        return "aucun"
    parts = []
    for z in zones:
        if isinstance(z, dict):
            top = z.get("top", z.get("high", "?"))
            bottom = z.get("bottom", z.get("low", "?"))
            direction = z.get("direction", "")
            label = f"[{bottom} - {top}]"
            if direction:
                label += f" ({direction})"
            parts.append(label)
        else:
            parts.append(str(z))
    return ", ".join(parts)
