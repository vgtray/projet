"""Module sentiment — NewsAPI + Reddit + Twitter/X (twscrape).

Analyse le sentiment marché via les titres de news, posts Reddit et tweets.
Dégradation gracieuse : si une source échoue → retourne "neutral".
Ref: SPEC.md sections 10, 16.
"""

import asyncio
import logging
import os
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

ASSET_TWITTER_QUERIES = {
    "XAUUSD": "gold XAUUSD OR #gold OR #XAUUSD OR #xauusd lang:en",
    "US100": "nasdaq US100 OR #nasdaq OR #NAS100 OR #US100 lang:en",
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


class TwitterSentiment:
    """Analyse le sentiment via Twitter/X (twscrape, sans API officielle)."""

    # Fichier de persistance des comptes twscrape (dans /tmp pour Docker)
    _DB_PATH = "/tmp/twscrape_accounts.db"

    def __init__(self):
        self._username = Config.TWITTER_USERNAME
        self._password = Config.TWITTER_PASSWORD
        self._email = Config.TWITTER_EMAIL
        self._enabled = False
        self._api = None

        if not self._username or not self._password:
            logger.info("TWITTER_USERNAME/PASSWORD absents — module Twitter désactivé")
            return

        try:
            import twscrape  # noqa: F401
            self._enabled = True
            logger.info("Module Twitter (twscrape) activé")
        except ImportError:
            logger.warning("twscrape non installé — module Twitter désactivé")

    async def _get_api(self):
        """Initialise et retourne l'API twscrape (lazy, avec pool de comptes)."""
        if self._api is not None:
            return self._api
        from twscrape import API
        api = API(self._DB_PATH)
        # Ajouter le compte seulement s'il n'est pas déjà enregistré
        try:
            await api.pool.add_account(
                username=self._username,
                password=self._password,
                email=self._email,
                email_password="",  # pas nécessaire si pas de 2FA email
            )
            await api.pool.login_all()
        except Exception as e:
            logger.warning("twscrape login : %s (compte peut-être déjà loggé)", e)
        self._api = api
        return api

    async def _fetch_sentiment_async(self, asset: str) -> str:
        """Fetch et analyse les tweets pour un asset (async)."""
        query = ASSET_TWITTER_QUERIES.get(asset)
        if not query:
            return "neutral"

        api = await self._get_api()
        total_bullish = 0
        total_bearish = 0
        count = 0

        try:
            async for tweet in api.search(query, limit=30):
                text = tweet.rawContent or ""
                b, br = _count_sentiment(text)
                total_bullish += b
                total_bearish += br
                count += 1
        except Exception as e:
            logger.error("Erreur twscrape search pour %s : %s", asset, e)
            return "neutral"

        if count == 0:
            logger.info("Aucun tweet trouvé pour %s — neutral", asset)
            return "neutral"

        sentiment = _resolve_sentiment(total_bullish, total_bearish)
        logger.info(
            "Twitter sentiment %s : %s (bullish=%d, bearish=%d, tweets=%d)",
            asset, sentiment, total_bullish, total_bearish, count,
        )
        return sentiment

    def get_twitter_sentiment(self, asset: str) -> str:
        """Récupère le sentiment Twitter pour un asset (interface synchrone).

        Args:
            asset: "XAUUSD" ou "US100".

        Returns:
            "bullish", "bearish" ou "neutral".
        """
        if not self._enabled:
            return "neutral"
        try:
            return asyncio.run(self._fetch_sentiment_async(asset))
        except Exception as e:
            logger.error("Erreur Twitter sentiment %s : %s — fallback neutral", asset, e)
            return "neutral"


class SentimentAnalyzer:
    """Façade combinant toutes les sources de sentiment."""

    def __init__(self):
        self._news = NewsSentiment()
        self._reddit = RedditSentiment()
        self._twitter = TwitterSentiment()

    def get_all_sentiment(self, asset: str) -> dict:
        """Récupère le sentiment de toutes les sources pour un asset.

        Combine Reddit + Twitter en un seul score social.

        Args:
            asset: "XAUUSD" ou "US100".

        Returns:
            {"news_sentiment": str, "social_sentiment": str}
        """
        news = self._news.get_news_sentiment(asset)
        reddit = self._reddit.get_reddit_sentiment(asset)
        twitter = self._twitter.get_twitter_sentiment(asset)

        # Combiner Reddit + Twitter : majorité l'emporte, sinon neutral
        social_scores = {"bullish": 0, "bearish": 0, "neutral": 0}
        social_scores[reddit] += 1
        social_scores[twitter] += 1
        if social_scores["bullish"] > social_scores["bearish"]:
            social = "bullish"
        elif social_scores["bearish"] > social_scores["bullish"]:
            social = "bearish"
        else:
            social = "neutral"

        logger.info(
            "Sentiment global %s — news: %s, reddit: %s, twitter: %s → social: %s",
            asset, news, reddit, twitter, social,
        )

        return {
            "news_sentiment": news,
            "social_sentiment": social,
        }
