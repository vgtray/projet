"""Module sentiment — NewsAPI + Reddit.

Analyse le sentiment marché via les titres de news et les posts Reddit.
Dégradation gracieuse : si une source échoue → retourne "neutral".
Ref: SPEC.md sections 10, 16.
"""

import logging
from typing import Optional

import requests

from src.config import Config

logger = logging.getLogger(__name__)

BULLISH_WORDS = [
    "surge", "rally", "gain", "rise", "bull", "up", "high", "record",
    "soar", "jump", "boost", "growth", "positive", "strong",
]

BEARISH_WORDS = [
    "crash", "fall", "drop", "decline", "bear", "down", "low", "plunge",
    "sink", "loss", "weak", "negative", "fear", "sell",
]

ASSET_NEWS_QUERIES = {
    "XAUUSD": "XAUUSD OR gold",
    "US100": "NASDAQ OR US100 OR nasdaq100 OR tech stocks",
}

ASSET_SUBREDDITS = {
    "XAUUSD": ["Forex", "Gold"],
    "US100": ["investing", "stocks"],
}


def _count_sentiment(text: str) -> tuple[int, int]:
    """Compte les mots bullish et bearish dans un texte.

    Args:
        text: Texte à analyser (titre d'article ou de post).

    Returns:
        Tuple (bullish_count, bearish_count).
    """
    words = text.lower().split()
    bullish = sum(1 for w in words if w in BULLISH_WORDS)
    bearish = sum(1 for w in words if w in BEARISH_WORDS)
    return bullish, bearish


def _resolve_sentiment(bullish_count: int, bearish_count: int) -> str:
    """Détermine le sentiment global à partir des compteurs.

    Args:
        bullish_count: Nombre de mots positifs.
        bearish_count: Nombre de mots négatifs.

    Returns:
        "bullish", "bearish" ou "neutral".
    """
    if bullish_count > bearish_count:
        return "bullish"
    if bearish_count > bullish_count:
        return "bearish"
    return "neutral"


class NewsSentiment:
    """Analyse le sentiment via NewsAPI."""

    def __init__(self):
        self._api_key: str = Config.NEWSAPI_KEY

    def get_news_sentiment(self, asset: str) -> str:
        """Récupère et analyse le sentiment des news pour un asset.

        Appelle NewsAPI /v2/everything, analyse les titres avec un
        comptage de mots positifs/négatifs.

        Args:
            asset: "XAUUSD" ou "US100".

        Returns:
            "bullish", "bearish" ou "neutral".
        """
        if not self._api_key:
            logger.warning("NEWSAPI_KEY absente — sentiment news par défaut: neutral")
            return "neutral"

        query = ASSET_NEWS_QUERIES.get(asset)
        if not query:
            logger.warning("Asset %s non supporté pour les news — neutral", asset)
            return "neutral"

        try:
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "apiKey": self._api_key,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            if not articles:
                logger.info("Aucun article trouvé pour %s — neutral", asset)
                return "neutral"

            total_bullish = 0
            total_bearish = 0
            for article in articles:
                title = article.get("title") or ""
                b, br = _count_sentiment(title)
                total_bullish += b
                total_bearish += br

            sentiment = _resolve_sentiment(total_bullish, total_bearish)
            logger.info(
                "News sentiment %s : %s (bullish=%d, bearish=%d, articles=%d)",
                asset, sentiment, total_bullish, total_bearish, len(articles),
            )
            return sentiment

        except Exception as e:
            logger.error("Erreur NewsAPI pour %s : %s — fallback neutral", asset, e)
            return "neutral"


class RedditSentiment:
    """Analyse le sentiment via Reddit (praw)."""

    def __init__(self):
        self._client_id: str = Config.REDDIT_CLIENT_ID
        self._client_secret: str = Config.REDDIT_CLIENT_SECRET
        self._user_agent: str = Config.REDDIT_USER_AGENT
        self._reddit: Optional[object] = None
        self._enabled: bool = False

        if not self._client_id or not self._client_secret:
            logger.info("Reddit credentials absents — module Reddit désactivé")
            return

        try:
            import praw
            self._reddit = praw.Reddit(
                client_id=self._client_id,
                client_secret=self._client_secret,
                user_agent=self._user_agent,
            )
            self._enabled = True
            logger.info("Module Reddit initialisé")
        except Exception as e:
            logger.error("Impossible d'initialiser praw : %s — module Reddit désactivé", e)

    def get_reddit_sentiment(self, asset: str) -> str:
        """Récupère et analyse le sentiment des posts Reddit pour un asset.

        Récupère les 10 derniers posts hot de chaque subreddit associé
        à l'asset et analyse les titres.

        Args:
            asset: "XAUUSD" ou "US100".

        Returns:
            "bullish", "bearish" ou "neutral".
        """
        if not self._enabled:
            return "neutral"

        subreddits = ASSET_SUBREDDITS.get(asset)
        if not subreddits:
            logger.warning("Asset %s non supporté pour Reddit — neutral", asset)
            return "neutral"

        try:
            total_bullish = 0
            total_bearish = 0
            total_posts = 0

            for sub_name in subreddits:
                subreddit = self._reddit.subreddit(sub_name)
                for post in subreddit.hot(limit=10):
                    title = post.title or ""
                    b, br = _count_sentiment(title)
                    total_bullish += b
                    total_bearish += br
                    total_posts += 1

            sentiment = _resolve_sentiment(total_bullish, total_bearish)
            logger.info(
                "Reddit sentiment %s : %s (bullish=%d, bearish=%d, posts=%d)",
                asset, sentiment, total_bullish, total_bearish, total_posts,
            )
            return sentiment

        except Exception as e:
            logger.error("Erreur Reddit pour %s : %s — fallback neutral", asset, e)
            return "neutral"


class SentimentAnalyzer:
    """Façade combinant toutes les sources de sentiment."""

    def __init__(self):
        self._news = NewsSentiment()
        self._reddit = RedditSentiment()

    def get_all_sentiment(self, asset: str) -> dict:
        """Récupère le sentiment de toutes les sources pour un asset.

        Args:
            asset: "XAUUSD" ou "US100".

        Returns:
            {"news_sentiment": str, "social_sentiment": str}
        """
        news = self._news.get_news_sentiment(asset)
        social = self._reddit.get_reddit_sentiment(asset)

        logger.info(
            "Sentiment global %s — news: %s, social: %s",
            asset, news, social,
        )

        return {
            "news_sentiment": news,
            "social_sentiment": social,
        }
