import logging
import time

from newsapi import NewsApiClient

import praw

from . import config

logger = logging.getLogger(__name__)

KEYWORDS = {
    "XAUUSD": "gold OR XAUUSD OR XAU",
    "NAS100": "nasdaq OR NAS100 OR tech stocks",
}

SUBREDDITS = {
    "XAUUSD": ["Forex", "Gold", "investing"],
    "NAS100": ["investing", "stocks", "wallstreetbets"],
}

BULLISH_WORDS = [
    "rise", "surge", "gain", "bull", "up", "high",
    "rally", "strong", "buy", "positive",
]
BEARISH_WORDS = [
    "fall", "drop", "decline", "bear", "down", "low",
    "crash", "weak", "sell", "negative",
]


class SentimentAnalyzer:

    def __init__(self):
        self._news_client: NewsApiClient | None = None
        self._reddit: praw.Reddit | None = None

        # NewsAPI
        if config.NEWSAPI_KEY:
            try:
                self._news_client = NewsApiClient(api_key=config.NEWSAPI_KEY)
            except Exception as exc:
                logger.warning("Impossible d'initialiser NewsAPI : %s", exc)

        # Reddit — mode authentifié ou lecture publique
        try:
            if config.REDDIT_CLIENT_ID:
                self._reddit = praw.Reddit(
                    client_id=config.REDDIT_CLIENT_ID,
                    client_secret=config.REDDIT_CLIENT_SECRET,
                    user_agent=config.REDDIT_USER_AGENT,
                )
            else:
                self._reddit = praw.Reddit(
                    client_id=None,
                    client_secret=None,
                    user_agent=config.REDDIT_USER_AGENT,
                )
        except Exception as exc:
            logger.warning("Impossible d'initialiser Reddit (praw) : %s", exc)

    # ------------------------------------------------------------------
    # Point d'entrée
    # ------------------------------------------------------------------

    def get_sentiment(self, symbol: str) -> dict:
        """Récupère le sentiment global (news + Reddit) pour un symbole."""
        news_sentiment = "neutral"
        news_count = 0
        social_sentiment = "neutral"
        reddit_count = 0

        try:
            news_sentiment, news_count = self._get_news_sentiment(symbol)
        except Exception as exc:
            logger.warning("Sentiment news indisponible pour %s : %s", symbol, exc)

        try:
            social_sentiment, reddit_count = self._get_reddit_sentiment(symbol)
        except Exception as exc:
            logger.warning("Sentiment Reddit indisponible pour %s : %s", symbol, exc)

        return {
            "news_sentiment": news_sentiment,
            "social_sentiment": social_sentiment,
            "news_count": news_count,
            "reddit_count": reddit_count,
        }

    # ------------------------------------------------------------------
    # News
    # ------------------------------------------------------------------

    def _get_news_sentiment(self, symbol: str) -> tuple[str, int]:
        """Appelle NewsAPI, analyse les titres. Retry 3x. Retourne (sentiment, count)."""
        if self._news_client is None:
            logger.warning("NewsAPI non configuré, sentiment par défaut")
            return "neutral", 0

        query = KEYWORDS.get(symbol, symbol)

        for attempt in range(config.RETRY_MAX):
            try:
                response = self._news_client.get_everything(
                    q=query,
                    language="en",
                    sort_by="publishedAt",
                    page_size=20,
                )
                articles = response.get("articles", [])
                texts = [a.get("title", "") for a in articles if a.get("title")]
                sentiment = self._analyze_text(texts)
                return sentiment, len(texts)
            except Exception as exc:
                logger.error("NewsAPI erreur (tentative %d/%d) : %s",
                             attempt + 1, config.RETRY_MAX, exc)
                if attempt < config.RETRY_MAX - 1:
                    time.sleep(config.RETRY_BACKOFF[attempt])

        return "neutral", 0

    # ------------------------------------------------------------------
    # Reddit
    # ------------------------------------------------------------------

    def _get_reddit_sentiment(self, symbol: str) -> tuple[str, int]:
        """Scrape Reddit via praw. Retry 3x. Retourne (sentiment, count)."""
        if self._reddit is None:
            logger.warning("Reddit non configuré, sentiment par défaut")
            return "neutral", 0

        subs = SUBREDDITS.get(symbol, ["investing"])

        for attempt in range(config.RETRY_MAX):
            try:
                texts: list[str] = []
                for sub_name in subs:
                    subreddit = self._reddit.subreddit(sub_name)
                    for post in subreddit.new(limit=10):
                        title = getattr(post, "title", "")
                        if title:
                            texts.append(title)
                sentiment = self._analyze_text(texts)
                return sentiment, len(texts)
            except Exception as exc:
                logger.error("Reddit erreur (tentative %d/%d) : %s",
                             attempt + 1, config.RETRY_MAX, exc)
                if attempt < config.RETRY_MAX - 1:
                    time.sleep(config.RETRY_BACKOFF[attempt])

        return "neutral", 0

    # ------------------------------------------------------------------
    # Analyse de texte
    # ------------------------------------------------------------------

    def _analyze_text(self, texts: list[str]) -> str:
        """Compte les mots bullish vs bearish dans une liste de textes."""
        bullish_count = 0
        bearish_count = 0

        for text in texts:
            words = text.lower().split()
            for w in words:
                if w in BULLISH_WORDS:
                    bullish_count += 1
                if w in BEARISH_WORDS:
                    bearish_count += 1

        if bullish_count > bearish_count:
            return "bullish"
        if bearish_count > bullish_count:
            return "bearish"
        return "neutral"
