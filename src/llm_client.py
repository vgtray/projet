"""Module LLM — Claude Sonnet 4.6 (principal) + Groq Llama 3.3 70B (fallback).

Claude est le cerveau principal. Si timeout ou erreur → switch Groq.
Groq en fallback — pas de seuil de confidence car ce n'est plus un fallback critique.
Ref: SPEC.md sections 11, 12, 22.
"""

import json
import logging
import re

import anthropic
import groq

from src.config import Config

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "asset", "direction", "scenario", "confidence",
    "entry_price", "sl_price", "tp_price", "rr_ratio",
    "confluences_used", "sweep_level",
    "news_sentiment", "social_sentiment",
    "trade_valid", "reason",
]

INVALID_SIGNAL = {
    "asset": None,
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
    "reason": "llm_unavailable",
    "llm_used": "none",
}


class LLMClient:
    """Client LLM avec fallback automatique Claude → Groq."""

    def __init__(self):
        self._anthropic_client = anthropic.Anthropic(
            api_key=Config.ANTHROPIC_API_KEY,
        )
        self._groq_client = groq.Groq(api_key=Config.GROQ_API_KEY)
        self._timeout = Config.LLM_TIMEOUT

    def get_system_prompt(self) -> str:
        """Retourne le prompt système exact de la spec section 22."""
        return (
            "Tu es un algorithme de trading expert basé sur la stratégie SMC/ICT.\n"
            "\n"
            "## ASSETS TRADÉS\n"
            "- XAUUSD (Or spot CFD)\n"
            "- US100 (Nasdaq 100 Cash CFD)\n"
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
            "Cible : prochain high ou low visible opposé.\n"
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
            "- Sentiment Reddit (r/Forex, r/Gold pour XAUUSD / r/investing, r/stocks pour US100)\n"
            "- Stats de performances passées pour patterns similaires (auto-calibration)\n"
            "\n"
            "## FORMAT DE RÉPONSE OBLIGATOIRE\n"
            "Réponds UNIQUEMENT en JSON compact, rien d'autre :\n"
            '{"a":"XAUUSD","d":"l|s|n","s":"r|c|u|n","c":0,"e":null,"sl":null,"tp":null,"rr":null,"cf":[],"sw":"none","ns":"n","ss":"n","v":false,"r":"x"}\n'
            "\n"
            "Clés: a=asset, d=direction(l/s/n), s=scenario(r/c/u/n), c=confidence%, e=entry, sl=stoploss, tp=takeprofit, rr=RR, cf=confluences, sw=sweep, ns=news, ss=social, v=valid, r=reason(court).\n"
            "Si v=false → e,sl,tp,rr=null.\n"
            "Ne jamais halluciner."
        )

    def build_analysis_prompt(self, data: dict) -> str:
        """Construit le prompt utilisateur avec toutes les données de marché.

        Args:
            data: Dictionnaire contenant asset, current_price, candles, indicators,
                  key_levels, confluences, sweep_info, news_sentiment,
                  social_sentiment, performance_history, current_time_paris,
                  daily_trade_count.

        Returns:
            Prompt texte structuré pour le LLM.
        """
        candles_text = ""
        for i, candle in enumerate(data.get("candles", [])):
            candles_text += (
                f"  [{i+1}] O:{candle.get('open')} H:{candle.get('high')} "
                f"L:{candle.get('low')} C:{candle.get('close')} V:{candle.get('volume')}\n"
            )

        indicators = data.get("indicators", {})
        key_levels = data.get("key_levels", {})
        confluences = data.get("confluences", [])
        sweep = data.get("sweep_info", {})
        perf = data.get("performance_history", {})

        confluences_text = ""
        if confluences:
            for c in confluences:
                confluences_text += f"  - {c.get('type', '?')} zone [{c.get('low', '?')} - {c.get('high', '?')}]\n"
        else:
            confluences_text = "  Aucune confluence détectée\n"

        perf_text = ""
        if perf:
            for pattern, stats in perf.items():
                perf_text += (
                    f"  - {pattern}: {stats.get('total_trades', 0)} trades, "
                    f"WR={stats.get('win_rate', 0)}%, "
                    f"avgRR={stats.get('avg_rr', 0)}, "
                    f"PnL={stats.get('total_pnl', 0)}\n"
                )
        else:
            perf_text = "  Pas encore de données de performance\n"

        return (
            f"=== ANALYSE DE MARCHÉ ===\n"
            f"\n"
            f"Asset : {data.get('asset')}\n"
            f"Heure Paris : {data.get('current_time_paris')}\n"
            f"Prix actuel : {data.get('current_price')}\n"
            f"Trades aujourd'hui : {data.get('daily_trade_count', 0)}/2\n"
            f"\n"
            f"--- BOUGIES M5 (20 dernières) ---\n"
            f"{candles_text}\n"
            f"--- INDICATEURS ---\n"
            f"RSI(14) : {indicators.get('rsi')}\n"
            f"MACD : signal={indicators.get('macd_signal')}, hist={indicators.get('macd_hist')}, line={indicators.get('macd_line')}\n"
            f"EMA20 : {indicators.get('ema20')}\n"
            f"EMA50 : {indicators.get('ema50')}\n"
            f"EMA200 : {indicators.get('ema200')}\n"
            f"\n"
            f"--- NIVEAUX CLÉS ---\n"
            f"Asia High : {key_levels.get('asia_high')}\n"
            f"Asia Low : {key_levels.get('asia_low')}\n"
            f"London High : {key_levels.get('london_high')}\n"
            f"London Low : {key_levels.get('london_low')}\n"
            f"Previous Day High : {key_levels.get('prev_day_high')}\n"
            f"Previous Day Low : {key_levels.get('prev_day_low')}\n"
            f"\n"
            f"--- CONFLUENCES DÉTECTÉES ---\n"
            f"{confluences_text}\n"
            f"--- SWEEP INFO ---\n"
            f"Sweep : {'OUI' if sweep.get('swept') else 'NON'}\n"
            f"Niveau : {sweep.get('level', 'aucun')}\n"
            f"Direction : {sweep.get('direction', 'aucune')}\n"
            f"\n"
            f"--- SENTIMENT ---\n"
            f"News : {data.get('news_sentiment', 'neutral')}\n"
            f"Social (Reddit) : {data.get('social_sentiment', 'neutral')}\n"
            f"\n"
            f"--- PERFORMANCE HISTORIQUE (auto-calibration) ---\n"
            f"{perf_text}\n"
            f"=== FIN DES DONNÉES ==="
        )

    def analyze(self, data: dict) -> dict:
        """Analyse complète : appelle le LLM et retourne le signal de trading.

        Essaie MiniMax d'abord, puis Groq en fallback.
        Si fallback utilisé et confidence <= 85 → force trade_valid: false.

        Args:
            data: Données de marché complètes.

        Returns:
            Dictionnaire du signal de trading (format spec section 11).
        """
        system_prompt = self.get_system_prompt()
        user_prompt = self.build_analysis_prompt(data)

        # Tentative Claude (principal)
        response_text = None
        llm_used = "claude"
        for attempt in range(2):
            try:
                response_text = self._call_claude(system_prompt, user_prompt)
                logger.info("Claude a répondu (tentative %d)", attempt + 1)
                break
            except Exception as e:
                logger.warning(
                    "Claude tentative %d échouée : %s", attempt + 1, e
                )

        # Fallback Groq si Claude a échoué
        if response_text is None:
            logger.warning("Claude indisponible — switch sur Groq fallback")
            llm_used = "groq"
            for attempt in range(2):
                try:
                    response_text = self._call_groq(system_prompt, user_prompt)
                    logger.info("Groq a répondu (tentative %d)", attempt + 1)
                    break
                except Exception as e:
                    logger.warning(
                        "Groq tentative %d échouée : %s", attempt + 1, e
                    )

        # Les deux LLM ont échoué
        if response_text is None:
            logger.error("Les deux LLM sont indisponibles — signal invalide")
            result = INVALID_SIGNAL.copy()
            result["asset"] = data.get("asset")
            return result

        result = self._parse_response(response_text, llm_used)
        result["asset"] = result.get("asset") or data.get("asset")

        return result

    def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        """Appelle Claude via le SDK Anthropic.

        Args:
            system_prompt: Prompt système.
            user_prompt: Prompt utilisateur avec les données.

        Returns:
            Contenu texte de la réponse.

        Raises:
            Exception: Si l'appel échoue ou timeout.
        """
        response = self._anthropic_client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        content = response.content[0].text
        logger.debug("Réponse Claude brute : %s", content[:200])
        return content

    def _call_groq(self, system_prompt: str, user_prompt: str) -> str:
        """Appelle Groq via le SDK Groq.

        Args:
            system_prompt: Prompt système.
            user_prompt: Prompt utilisateur avec les données.

        Returns:
            Contenu texte de la réponse.

        Raises:
            Exception: Si l'appel échoue.
        """
        response = self._groq_client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        logger.debug("Réponse Groq brute : %s", content[:200])
        return content

    def _parse_response(self, response_text: str, llm_used: str) -> dict:
        """Parse la réponse JSON du LLM.

        Gère les cas où le LLM ajoute du texte autour du JSON
        (markdown code blocks, texte avant/après).

        Args:
            response_text: Texte brut de la réponse LLM.
            llm_used: "minimax" ou "groq".

        Returns:
            Dictionnaire du signal avec champ llm_used ajouté.
        """
        try:
            # Nettoyage : extraire le JSON même si entouré de texte
            text = response_text.strip()

            # Cas markdown ```json ... ```
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if json_match:
                text = json_match.group(1)
            else:
                # Cas JSON brut avec du texte autour
                brace_match = re.search(r"\{.*\}", text, re.DOTALL)
                if brace_match:
                    text = brace_match.group(0)

            result = json.loads(text)

            # Mapping valeurs (compact ou plein → valeur canonique)
            VAL_MAP = {
                "direction": {
                    "l": "long", "long": "long",
                    "s": "short", "short": "short",
                    "n": "none", "none": "none",
                },
                "scenario": {
                    "r": "reversal", "reversal": "reversal",
                    "c": "continuation", "continuation": "continuation",
                    "u": "unclear", "unclear": "unclear",
                    "n": "none", "none": "none",
                },
                "news_sentiment": {
                    "b": "bullish", "bullish": "bullish",
                    "be": "bearish", "bear": "bearish", "bearish": "bearish",
                    "n": "neutral", "neutral": "neutral",
                },
                "social_sentiment": {
                    "b": "bullish", "bullish": "bullish",
                    "be": "bearish", "bear": "bearish", "bearish": "bearish",
                    "n": "neutral", "neutral": "neutral",
                },
            }

            # Détecter si le LLM a répondu avec les clés complètes ou compactes
            FULL_KEYS = {"asset", "direction", "scenario", "confidence", "entry_price",
                         "sl_price", "tp_price", "rr_ratio", "confluences_used", "sweep_level",
                         "news_sentiment", "social_sentiment", "trade_valid", "reason"}
            if FULL_KEYS & result.keys():
                # Réponse avec clés complètes — appliquer seulement VAL_MAP sur les valeurs
                mapped = dict(result)
            else:
                # Réponse compacte — mapper clés + valeurs
                KEY_MAP = {
                    "a": "asset", "d": "direction", "s": "scenario", "c": "confidence",
                    "e": "entry_price", "sl": "sl_price", "tp": "tp_price", "rr": "rr_ratio",
                    "cf": "confluences_used", "sw": "sweep_level", "ns": "news_sentiment",
                    "ss": "social_sentiment", "v": "trade_valid", "r": "reason",
                }
                mapped = {}
                for short_key, full_key in KEY_MAP.items():
                    if short_key in result:
                        mapped[full_key] = result[short_key]

            # Normaliser les valeurs via VAL_MAP
            for full_key, vmap in VAL_MAP.items():
                if full_key in mapped and isinstance(mapped[full_key], str):
                    mapped[full_key] = vmap.get(mapped[full_key].lower(), mapped[full_key])
            result = mapped

            # Validation des champs obligatoires
            missing = [f for f in REQUIRED_FIELDS if f not in result]
            if missing:
                logger.warning("Champs manquants dans la réponse LLM : %s", missing)
                for field in missing:
                    if field in ("confidence",):
                        result[field] = 0
                    elif field in ("trade_valid",):
                        result[field] = False
                    elif field in ("confluences_used",):
                        result[field] = []
                    elif field in ("direction", "scenario", "sweep_level"):
                        result[field] = "none"
                    elif field in ("news_sentiment", "social_sentiment"):
                        result[field] = "neutral"
                    elif field == "reason":
                        result[field] = "champs manquants dans la réponse"
                    else:
                        result[field] = None

            result["llm_used"] = llm_used
            logger.info(
                "Signal parsé — direction: %s, valid: %s, confidence: %s, llm: %s",
                result.get("direction"), result.get("trade_valid"),
                result.get("confidence"), llm_used,
            )
            return result

        except (json.JSONDecodeError, AttributeError) as e:
            logger.error("Échec du parsing JSON LLM (%s) : %s", llm_used, e)
            logger.debug("Réponse brute : %s", response_text[:500])
            return {
                "asset": None,
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
                "reason": "parse_error",
                "llm_used": llm_used,
            }
