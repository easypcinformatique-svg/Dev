"""
Module de sentiment analysis — Twitter/X + Grok (xAI).

Pipeline :
    1. Twitter/X API v2 → recherche de tweets liés au marché
    2. Grok API (xAI) → analyse du sentiment + estimation de probabilité
    3. Score composite → signal intégré dans la stratégie

Requiert :
    - TWITTER_BEARER_TOKEN (env var)
    - XAI_API_KEY (env var)
    - pip install tweepy openai
"""

import os
import re
import time
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

logger = logging.getLogger(__name__)

# ================================================================
#  CONFIGURATION
# ================================================================

GROK_BASE_URL = "https://api.x.ai/v1"
GROK_MODEL = "grok-3-mini"  # Bon rapport qualité/prix
TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


@dataclass
class SentimentResult:
    """Résultat de l'analyse de sentiment pour un marché."""
    market_id: str
    query: str
    tweet_count: int
    avg_sentiment: float        # -1.0 (très négatif) à +1.0 (très positif)
    sentiment_std: float        # Volatilité du sentiment
    weighted_sentiment: float   # Pondéré par engagement (likes, RT)
    grok_probability: float     # Probabilité estimée par Grok (0.0 à 1.0)
    grok_confidence: float      # Confiance de Grok dans son estimation
    grok_reasoning: str         # Raisonnement de Grok
    total_engagement: int       # Likes + RT + replies total
    bullish_ratio: float        # % de tweets bullish
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def composite_score(self) -> float:
        """Score composite combinant Twitter sentiment + Grok analysis."""
        # 40% sentiment Twitter pondéré, 60% estimation Grok
        twitter_score = np.clip(self.weighted_sentiment, -1, 1)
        grok_score = (self.grok_probability - 0.5) * 2  # Map 0-1 à -1..+1
        grok_weight = self.grok_confidence

        composite = (
            0.4 * twitter_score +
            0.6 * grok_score * grok_weight
        )
        return np.clip(composite, -1, 1)


# ================================================================
#  TWITTER / X CLIENT
# ================================================================

class TwitterClient:
    """Client Twitter/X API v2 pour récupérer les tweets."""

    def __init__(self, bearer_token: str | None = None):
        self.bearer_token = bearer_token or os.environ.get("TWITTER_BEARER_TOKEN", "")
        if not self.bearer_token:
            logger.warning("TWITTER_BEARER_TOKEN non configuré — sentiment Twitter désactivé")

        self._last_request = 0.0
        self._rate_limit_delay = 3.1  # 300 req / 15 min = 1 req / 3s

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": "PolymarketSentimentBot/1.0",
        }

    def search_tweets(
        self,
        query: str,
        max_results: int = 50,
        lang: str = "en",
    ) -> list[dict]:
        """
        Recherche les tweets récents (7 derniers jours).

        Returns:
            Liste de dicts avec text, likes, retweets, replies, created_at
        """
        if not self.bearer_token:
            return []

        import requests

        # Rate limiting
        elapsed = time.time() - self._last_request
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)

        # Construire la query : exclure retweets et réponses pour du contenu original
        full_query = f"{query} lang:{lang} -is:retweet -is:reply"

        params = {
            "query": full_query,
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "username,public_metrics",
        }

        try:
            resp = requests.get(
                TWITTER_SEARCH_URL,
                params=params,
                headers=self._headers(),
                timeout=15,
            )
            self._last_request = time.time()

            if resp.status_code == 429:
                logger.warning("Twitter rate limited")
                return []
            if resp.status_code != 200:
                logger.warning(f"Twitter API error {resp.status_code}: {resp.text[:200]}")
                return []

            data = resp.json()
            tweets = []

            # Map author_id -> username
            users = {}
            for u in data.get("includes", {}).get("users", []):
                users[u["id"]] = u.get("username", "")

            for tweet in data.get("data", []):
                metrics = tweet.get("public_metrics", {})
                tweets.append({
                    "text": tweet["text"],
                    "created_at": tweet.get("created_at", ""),
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "quotes": metrics.get("quote_count", 0),
                    "author": users.get(tweet.get("author_id", ""), ""),
                })

            return tweets

        except Exception as e:
            logger.error(f"Twitter search failed: {e}")
            return []

    def build_query_for_market(self, question: str) -> str:
        """
        Construit une requête Twitter à partir de la question du marché.
        Extrait les mots-clés principaux.
        """
        # Nettoyer la question
        q = question.strip().rstrip("?")

        # Supprimer les mots communs
        stop_words = {
            "will", "the", "be", "is", "are", "was", "were", "has", "have",
            "had", "do", "does", "did", "a", "an", "and", "or", "but", "in",
            "on", "at", "to", "for", "of", "with", "by", "from", "this",
            "that", "it", "its", "as", "if", "not", "no", "yes", "than",
            "before", "after", "above", "below", "up", "down", "out",
        }

        words = re.findall(r'\b[A-Za-z0-9]+\b', q)
        keywords = [w for w in words if w.lower() not in stop_words and len(w) > 2]

        # Garder les 4-5 mots-clés les plus importants
        # Prioriser les mots capitalisés (noms propres)
        proper_nouns = [w for w in keywords if w[0].isupper()]
        other_words = [w for w in keywords if not w[0].isupper()]

        selected = proper_nouns[:4]
        if len(selected) < 3:
            selected.extend(other_words[:3 - len(selected)])

        return " ".join(selected) if selected else q[:50]


# ================================================================
#  GROK CLIENT (xAI)
# ================================================================

class GrokClient:
    """Client Grok API (xAI) pour l'analyse de sentiment et probabilité."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("XAI_API_KEY", "")
        if not self.api_key:
            logger.warning("XAI_API_KEY non configuré — analyse Grok désactivée")

        self._last_request = 0.0
        self._rate_limit_delay = 1.0

    def analyze_market_sentiment(
        self,
        question: str,
        tweets: list[dict],
        current_price: float,
    ) -> dict:
        """
        Analyse le sentiment des tweets + estime la probabilité du marché.

        Returns:
            dict avec probability, confidence, reasoning, tweet_sentiments
        """
        if not self.api_key:
            return self._default_response()

        import requests

        # Rate limiting
        elapsed = time.time() - self._last_request
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)

        # Préparer le contexte des tweets
        tweet_context = self._format_tweets(tweets[:20])  # Max 20 tweets

        prompt = f"""Tu es un analyste de marchés prédictifs. Analyse ces données pour le marché Polymarket suivant :

QUESTION DU MARCHÉ : "{question}"
PRIX ACTUEL (YES) : {current_price:.2f} (= {current_price*100:.0f}% de probabilité implicite)

TWEETS RÉCENTS SUR LE SUJET :
{tweet_context}

INSTRUCTIONS :
1. Analyse le sentiment général des tweets (bullish/bearish sur le YES)
2. Estime la VRAIE probabilité que l'événement se réalise (YES)
3. Compare avec le prix actuel du marché

Réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{{
  "probability": 0.XX,
  "confidence": 0.XX,
  "sentiment": "bullish" ou "bearish" ou "neutral",
  "reasoning": "explication courte (max 100 mots)",
  "tweet_sentiments": [1, -1, 0, ...]
}}

- probability: ta meilleure estimation (0.0 à 1.0)
- confidence: ta confiance dans cette estimation (0.0 à 1.0)
- tweet_sentiments: score pour chaque tweet (-1=bearish, 0=neutre, +1=bullish)
"""

        try:
            resp = requests.post(
                f"{GROK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROK_MODEL,
                    "messages": [
                        {"role": "system", "content": "Tu es un analyste expert en marchés prédictifs. Réponds uniquement en JSON valide."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30,
            )
            self._last_request = time.time()

            if resp.status_code != 200:
                logger.warning(f"Grok API error {resp.status_code}: {resp.text[:200]}")
                return self._default_response()

            content = resp.json()["choices"][0]["message"]["content"]
            return self._parse_response(content)

        except Exception as e:
            logger.error(f"Grok analysis failed: {e}")
            return self._default_response()

    def _format_tweets(self, tweets: list[dict]) -> str:
        """Formate les tweets pour le prompt."""
        if not tweets:
            return "(Aucun tweet trouvé)"

        lines = []
        for i, t in enumerate(tweets, 1):
            engagement = t["likes"] + t["retweets"]
            lines.append(f"[{i}] ({engagement} engagements) {t['text'][:200]}")
        return "\n".join(lines)

    def _parse_response(self, content: str) -> dict:
        """Parse la réponse JSON de Grok."""
        try:
            # Extraire le JSON du contenu (peut être entouré de ```json ... ```)
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "probability": float(data.get("probability", 0.5)),
                    "confidence": float(data.get("confidence", 0.5)),
                    "sentiment": data.get("sentiment", "neutral"),
                    "reasoning": data.get("reasoning", ""),
                    "tweet_sentiments": data.get("tweet_sentiments", []),
                }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Grok response: {e}")

        return self._default_response()

    def _default_response(self) -> dict:
        return {
            "probability": 0.5,
            "confidence": 0.0,
            "sentiment": "neutral",
            "reasoning": "No analysis available",
            "tweet_sentiments": [],
        }


# ================================================================
#  SENTIMENT ANALYZER — COMBINE TOUT
# ================================================================

class SentimentAnalyzer:
    """
    Analyseur de sentiment combinant Twitter/X + Grok.

    Usage:
        analyzer = SentimentAnalyzer()  # Utilise les env vars
        result = analyzer.analyze("Will Bitcoin hit $100k?", "0xconditionid", 0.65)
        print(result.composite_score)  # -1.0 à +1.0
    """

    def __init__(
        self,
        twitter_token: str | None = None,
        grok_api_key: str | None = None,
        cache_ttl_seconds: int = 300,
    ):
        self.twitter = TwitterClient(twitter_token)
        self.grok = GrokClient(grok_api_key)
        self.cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[datetime, SentimentResult]] = {}

    def analyze(
        self,
        question: str,
        market_id: str,
        current_price: float,
        max_tweets: int = 50,
    ) -> SentimentResult:
        """
        Analyse complète du sentiment pour un marché.

        Args:
            question: Question du marché Polymarket
            market_id: Condition ID du marché
            current_price: Prix YES actuel (0.0-1.0)
            max_tweets: Nombre max de tweets à récupérer

        Returns:
            SentimentResult avec tous les scores
        """
        # Check cache
        if market_id in self._cache:
            cached_time, cached_result = self._cache[market_id]
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                return cached_result

        # 1. Construire la query Twitter
        query = self.twitter.build_query_for_market(question)
        logger.info(f"Sentiment query: '{query}' for: {question[:50]}...")

        # 2. Récupérer les tweets
        tweets = self.twitter.search_tweets(query, max_results=max_tweets)
        logger.info(f"  -> {len(tweets)} tweets found")

        # 3. Analyse par Grok
        grok_result = self.grok.analyze_market_sentiment(
            question=question,
            tweets=tweets,
            current_price=current_price,
        )

        # 4. Calculer les métriques Twitter
        tweet_sentiments = grok_result.get("tweet_sentiments", [])
        total_engagement = sum(t["likes"] + t["retweets"] + t["replies"] for t in tweets)

        # Sentiment moyen simple
        avg_sentiment = 0.0
        sentiment_std = 0.0
        if tweet_sentiments:
            avg_sentiment = np.mean(tweet_sentiments)
            sentiment_std = np.std(tweet_sentiments) if len(tweet_sentiments) > 1 else 0.0

        # Sentiment pondéré par engagement
        weighted_sentiment = 0.0
        if tweets and tweet_sentiments:
            weights = []
            for t in tweets[:len(tweet_sentiments)]:
                w = 1 + t["likes"] + t["retweets"] * 2 + t["quotes"] * 3
                weights.append(w)
            total_w = sum(weights)
            if total_w > 0:
                weighted_sentiment = sum(
                    s * w for s, w in zip(tweet_sentiments, weights)
                ) / total_w

        # Ratio bullish
        bullish = sum(1 for s in tweet_sentiments if s > 0)
        bullish_ratio = bullish / len(tweet_sentiments) if tweet_sentiments else 0.5

        result = SentimentResult(
            market_id=market_id,
            query=query,
            tweet_count=len(tweets),
            avg_sentiment=avg_sentiment,
            sentiment_std=sentiment_std,
            weighted_sentiment=weighted_sentiment,
            grok_probability=grok_result["probability"],
            grok_confidence=grok_result["confidence"],
            grok_reasoning=grok_result["reasoning"],
            total_engagement=total_engagement,
            bullish_ratio=bullish_ratio,
        )

        # Cache
        self._cache[market_id] = (datetime.now(), result)

        logger.info(
            f"  -> Sentiment: avg={avg_sentiment:+.2f} weighted={weighted_sentiment:+.2f} "
            f"| Grok: prob={grok_result['probability']:.2f} conf={grok_result['confidence']:.2f} "
            f"| Composite: {result.composite_score:+.3f}"
        )

        return result

    def is_available(self) -> bool:
        """Vérifie si au moins une source est configurée."""
        return bool(self.twitter.bearer_token or self.grok.api_key)
