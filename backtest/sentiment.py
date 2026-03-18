"""
Module de sentiment analysis — Twitter/X scraping + VADER + Grok (optionnel).

Pipeline (sans cle API) :
    1. TwitterScraper → scrape tweets via guest token (pas de cle API)
    2. VADER (NLTK) → analyse de sentiment locale gratuite
    3. Score composite → signal integre dans la strategie

Pipeline (avec cles API, optionnel) :
    1. Twitter API v2 → recherche de tweets (TWITTER_BEARER_TOKEN)
    2. Grok API (xAI) → analyse avancee (XAI_API_KEY)

pip install nltk beautifulsoup4 requests
"""

import os
import re
import time
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import numpy as np

logger = logging.getLogger(__name__)

# ================================================================
#  CONFIGURATION
# ================================================================

GROK_BASE_URL = "https://api.x.ai/v1"
GROK_MODEL = "grok-3-mini"
TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

# User-Agent rotatif pour le scraping
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


@dataclass
class SentimentResult:
    """Resultat de l'analyse de sentiment pour un marche."""
    market_id: str
    query: str
    tweet_count: int
    avg_sentiment: float        # -1.0 (tres negatif) a +1.0 (tres positif)
    sentiment_std: float        # Volatilite du sentiment
    weighted_sentiment: float   # Pondere par engagement (likes, RT)
    grok_probability: float     # Probabilite estimee par Grok (0.0 a 1.0)
    grok_confidence: float      # Confiance de Grok dans son estimation
    grok_reasoning: str         # Raisonnement de Grok
    total_engagement: int       # Likes + RT + replies total
    bullish_ratio: float        # % de tweets bullish
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def composite_score(self) -> float:
        """Score composite combinant Twitter sentiment + Grok/VADER analysis."""
        twitter_score = np.clip(self.weighted_sentiment, -1, 1)
        grok_score = (self.grok_probability - 0.5) * 2  # Map 0-1 a -1..+1
        grok_weight = self.grok_confidence

        if grok_weight > 0:
            # Mode API : 40% Twitter + 60% Grok
            composite = (
                0.4 * twitter_score +
                0.6 * grok_score * grok_weight
            )
        else:
            # Mode scraping/VADER : 100% sentiment Twitter (analyse par VADER)
            composite = twitter_score

        return float(np.clip(composite, -1, 1))


# ================================================================
#  VADER SENTIMENT ANALYZER (LOCAL, GRATUIT)
# ================================================================

class VaderAnalyzer:
    """Analyse de sentiment locale via NLTK VADER — pas de cle API."""

    def __init__(self):
        self._analyzer = None
        self._available = False
        try:
            import nltk
            nltk.download('vader_lexicon', quiet=True)
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            self._analyzer = SentimentIntensityAnalyzer()
            self._available = True
            logger.info("VADER sentiment analyzer charge")
        except Exception as e:
            logger.warning(f"VADER non disponible: {e}")

    def analyze_tweet(self, text: str) -> float:
        """Retourne un score entre -1 et +1 pour un tweet."""
        if not self._available:
            return 0.0
        scores = self._analyzer.polarity_scores(text)
        return scores['compound']  # -1 a +1

    def analyze_tweets(self, tweets: list[dict]) -> list[float]:
        """Analyse une liste de tweets, retourne les scores."""
        return [self.analyze_tweet(t.get("text", "")) for t in tweets]

    def estimate_probability(
        self,
        question: str,
        tweets: list[dict],
        current_price: float,
    ) -> dict:
        """Estime la probabilite a partir du sentiment moyen des tweets."""
        if not tweets:
            return {
                "probability": current_price,
                "confidence": 0.0,
                "sentiment": "neutral",
                "reasoning": "Pas de tweets trouves",
                "tweet_sentiments": [],
            }

        sentiments = self.analyze_tweets(tweets)
        avg = np.mean(sentiments) if sentiments else 0.0
        std = np.std(sentiments) if len(sentiments) > 1 else 1.0

        # Convertir le sentiment en ajustement de probabilite
        # avg in [-1, +1] => shift de -15% a +15% max
        shift = avg * 0.15
        estimated_prob = np.clip(current_price + shift, 0.05, 0.95)

        # Confiance basee sur le consensus (faible std = fort consensus)
        consensus = max(0, 1.0 - std) if len(sentiments) >= 3 else 0.3
        confidence = min(consensus * (len(sentiments) / 20.0), 0.85)

        if avg > 0.15:
            sentiment_label = "bullish"
        elif avg < -0.15:
            sentiment_label = "bearish"
        else:
            sentiment_label = "neutral"

        # Discretiser en -1, 0, +1 pour compatibilite
        discrete_sentiments = []
        for s in sentiments:
            if s > 0.2:
                discrete_sentiments.append(1)
            elif s < -0.2:
                discrete_sentiments.append(-1)
            else:
                discrete_sentiments.append(0)

        return {
            "probability": float(estimated_prob),
            "confidence": float(confidence),
            "sentiment": sentiment_label,
            "reasoning": f"VADER: avg={avg:+.2f} std={std:.2f} sur {len(sentiments)} tweets",
            "tweet_sentiments": discrete_sentiments,
        }


# ================================================================
#  TWITTER SCRAPER (SANS CLE API)
# ================================================================

class TwitterScraper:
    """
    Scraper Twitter/X utilisant le guest token — aucune cle API requise.
    Fallback: recherche via Google/Bing pour trouver des tweets.
    """

    def __init__(self):
        self._guest_token: str | None = None
        self._guest_token_time: float = 0
        self._last_request = 0.0
        self._rate_limit_delay = 2.0
        self._session = None

    def _get_session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": _USER_AGENTS[0],
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            })
        return self._session

    def _get_guest_token(self) -> str | None:
        """Obtient un guest token Twitter (valide ~3h)."""
        # Reutiliser le token s'il est recent
        if self._guest_token and (time.time() - self._guest_token_time) < 7200:
            return self._guest_token

        import requests

        try:
            session = self._get_session()

            # Activation token via l'endpoint public
            activate_url = "https://api.twitter.com/1.1/guest/activate.json"
            bearer = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

            resp = session.post(
                activate_url,
                headers={"Authorization": f"Bearer {bearer}"},
                timeout=10,
            )

            if resp.status_code == 200:
                self._guest_token = resp.json().get("guest_token")
                self._guest_token_time = time.time()
                logger.info(f"Guest token obtenu: {self._guest_token[:8]}...")
                return self._guest_token

            logger.warning(f"Guest token failed: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Guest token error: {e}")

        return None

    def search_tweets(
        self,
        query: str,
        max_results: int = 30,
        lang: str = "en",
    ) -> list[dict]:
        """Recherche des tweets via guest token ou fallback web search."""
        # Rate limiting
        elapsed = time.time() - self._last_request
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)

        # Essayer le guest token d'abord
        tweets = self._search_via_guest_token(query, max_results, lang)
        if tweets:
            return tweets

        # Fallback : recherche web
        tweets = self._search_via_web(query, max_results)
        return tweets

    def _search_via_guest_token(
        self, query: str, max_results: int, lang: str
    ) -> list[dict]:
        """Recherche via l'API Twitter avec guest token."""
        guest_token = self._get_guest_token()
        if not guest_token:
            return []

        import requests

        bearer = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

        search_url = "https://api.twitter.com/2/search/adaptive.json"
        params = {
            "q": f"{query} lang:{lang} -filter:retweets -filter:replies",
            "count": min(max_results, 40),
            "query_source": "typed_query",
            "result_filter": "latest",
            "tweet_mode": "extended",
            "include_entities": "true",
        }

        try:
            resp = requests.get(
                search_url,
                params=params,
                headers={
                    "Authorization": f"Bearer {bearer}",
                    "x-guest-token": guest_token,
                    "User-Agent": _USER_AGENTS[0],
                },
                timeout=15,
            )
            self._last_request = time.time()

            if resp.status_code == 429:
                logger.warning("Twitter guest token rate limited")
                self._guest_token = None  # Forcer renouvellement
                return []

            if resp.status_code != 200:
                logger.info(f"Guest search status {resp.status_code}, trying fallback")
                return []

            data = resp.json()
            tweets = []

            # Parser les tweets du format adaptive
            tweet_data = data.get("globalObjects", {}).get("tweets", {})
            user_data = data.get("globalObjects", {}).get("users", {})

            for tid, tweet in list(tweet_data.items())[:max_results]:
                text = tweet.get("full_text", tweet.get("text", ""))
                user = user_data.get(str(tweet.get("user_id_str", "")), {})
                tweets.append({
                    "text": text,
                    "created_at": tweet.get("created_at", ""),
                    "likes": tweet.get("favorite_count", 0),
                    "retweets": tweet.get("retweet_count", 0),
                    "replies": tweet.get("reply_count", 0),
                    "quotes": tweet.get("quote_count", 0),
                    "author": user.get("screen_name", ""),
                    "followers": user.get("followers_count", 0),
                })

            logger.info(f"Guest token search: {len(tweets)} tweets pour '{query}'")
            return tweets

        except Exception as e:
            logger.warning(f"Guest token search failed: {e}")
            return []

    def _search_via_web(self, query: str, max_results: int) -> list[dict]:
        """Fallback: recherche via Google News RSS (gratuit, fiable)."""
        import requests

        tweets = []
        encoded_query = quote_plus(query)

        try:
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            resp = requests.get(
                url,
                headers={"User-Agent": _USER_AGENTS[1]},
                timeout=15,
            )
            self._last_request = time.time()

            if resp.status_code == 200:
                import re as _re
                # Parser les titres d'articles du RSS
                titles = _re.findall(
                    r'<title><!\[CDATA\[(.*?)\]\]></title>', resp.text
                )
                if not titles:
                    titles = _re.findall(r'<title>(.*?)</title>', resp.text)

                # Ignorer les 2 premiers (feed title + Google News)
                articles = [t for t in titles[2:] if len(t) > 15]

                for title in articles[:max_results]:
                    tweets.append({
                        "text": title,
                        "created_at": "",
                        "likes": 5,  # Poids de base pour les news
                        "retweets": 2,
                        "replies": 0,
                        "quotes": 0,
                        "author": "news",
                        "followers": 0,
                    })

                logger.info(
                    f"Google News fallback: {len(tweets)} articles pour '{query}'"
                )

        except Exception as e:
            logger.warning(f"Google News fallback failed: {e}")

        return tweets

    def build_query_for_market(self, question: str) -> str:
        """Construit une requete de recherche a partir de la question du marche."""
        q = question.strip().rstrip("?")

        stop_words = {
            "will", "the", "be", "is", "are", "was", "were", "has", "have",
            "had", "do", "does", "did", "a", "an", "and", "or", "but", "in",
            "on", "at", "to", "for", "of", "with", "by", "from", "this",
            "that", "it", "its", "as", "if", "not", "no", "yes", "than",
            "before", "after", "above", "below", "up", "down", "out",
        }

        words = re.findall(r'\b[A-Za-z0-9]+\b', q)
        keywords = [w for w in words if w.lower() not in stop_words and len(w) > 2]

        proper_nouns = [w for w in keywords if w[0].isupper()]
        other_words = [w for w in keywords if not w[0].isupper()]

        selected = proper_nouns[:4]
        if len(selected) < 3:
            selected.extend(other_words[:3 - len(selected)])

        return " ".join(selected) if selected else q[:50]


# ================================================================
#  TWITTER / X CLIENT (API OFFICIELLE — OPTIONNEL)
# ================================================================

class TwitterClient:
    """Client Twitter/X API v2 — necessite TWITTER_BEARER_TOKEN."""

    def __init__(self, bearer_token: str | None = None):
        self.bearer_token = bearer_token or os.environ.get("TWITTER_BEARER_TOKEN", "")
        if not self.bearer_token:
            logger.info("TWITTER_BEARER_TOKEN absent — utilisation du scraper")

        self._last_request = 0.0
        self._rate_limit_delay = 3.1

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
        if not self.bearer_token:
            return []

        import requests

        elapsed = time.time() - self._last_request
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)

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
                logger.warning(f"Twitter API error {resp.status_code}")
                return []

            data = resp.json()
            tweets = []

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
        q = question.strip().rstrip("?")
        stop_words = {
            "will", "the", "be", "is", "are", "was", "were", "has", "have",
            "had", "do", "does", "did", "a", "an", "and", "or", "but", "in",
            "on", "at", "to", "for", "of", "with", "by", "from", "this",
            "that", "it", "its", "as", "if", "not", "no", "yes", "than",
            "before", "after", "above", "below", "up", "down", "out",
        }
        words = re.findall(r'\b[A-Za-z0-9]+\b', q)
        keywords = [w for w in words if w.lower() not in stop_words and len(w) > 2]
        proper_nouns = [w for w in keywords if w[0].isupper()]
        other_words = [w for w in keywords if not w[0].isupper()]
        selected = proper_nouns[:4]
        if len(selected) < 3:
            selected.extend(other_words[:3 - len(selected)])
        return " ".join(selected) if selected else q[:50]


# ================================================================
#  GROK CLIENT (xAI) — OPTIONNEL
# ================================================================

class GrokClient:
    """Client Grok API (xAI) — necessite XAI_API_KEY."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("XAI_API_KEY", "")
        if not self.api_key:
            logger.info("XAI_API_KEY absent — utilisation de VADER pour le sentiment")

        self._last_request = 0.0
        self._rate_limit_delay = 1.0

    def analyze_market_sentiment(
        self,
        question: str,
        tweets: list[dict],
        current_price: float,
    ) -> dict:
        if not self.api_key:
            return self._default_response()

        import requests

        elapsed = time.time() - self._last_request
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)

        tweet_context = self._format_tweets(tweets[:20])

        prompt = f"""Tu es un analyste de marches predictifs. Analyse ces donnees pour le marche Polymarket suivant :

QUESTION DU MARCHE : "{question}"
PRIX ACTUEL (YES) : {current_price:.2f} (= {current_price*100:.0f}% de probabilite implicite)

TWEETS RECENTS SUR LE SUJET :
{tweet_context}

INSTRUCTIONS :
1. Analyse le sentiment general des tweets (bullish/bearish sur le YES)
2. Estime la VRAIE probabilite que l'evenement se realise (YES)
3. Compare avec le prix actuel du marche

Reponds UNIQUEMENT en JSON valide avec cette structure exacte :
{{
  "probability": 0.XX,
  "confidence": 0.XX,
  "sentiment": "bullish" ou "bearish" ou "neutral",
  "reasoning": "explication courte (max 100 mots)",
  "tweet_sentiments": [1, -1, 0, ...]
}}
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
                        {"role": "system", "content": "Tu es un analyste expert en marches predictifs. Reponds uniquement en JSON valide."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30,
            )
            self._last_request = time.time()

            if resp.status_code != 200:
                logger.warning(f"Grok API error {resp.status_code}")
                return self._default_response()

            content = resp.json()["choices"][0]["message"]["content"]
            return self._parse_response(content)

        except Exception as e:
            logger.error(f"Grok analysis failed: {e}")
            return self._default_response()

    def _format_tweets(self, tweets: list[dict]) -> str:
        if not tweets:
            return "(Aucun tweet trouve)"
        lines = []
        for i, t in enumerate(tweets, 1):
            engagement = t["likes"] + t["retweets"]
            lines.append(f"[{i}] ({engagement} engagements) {t['text'][:200]}")
        return "\n".join(lines)

    def _parse_response(self, content: str) -> dict:
        try:
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
    Analyseur de sentiment multi-source avec fallback automatique.

    Priorite :
        1. Twitter API v2 + Grok (si cles API disponibles)
        2. TwitterScraper + VADER (GRATUIT, sans cle API)

    Usage:
        analyzer = SentimentAnalyzer()  # Auto-detecte les sources
        result = analyzer.analyze("Will Bitcoin hit $100k?", "0xconditionid", 0.65)
        print(result.composite_score)  # -1.0 a +1.0
    """

    def __init__(
        self,
        twitter_token: str | None = None,
        grok_api_key: str | None = None,
        cache_ttl_seconds: int = 300,
    ):
        # Sources API (optionnelles)
        self.twitter_api = TwitterClient(twitter_token)
        self.grok = GrokClient(grok_api_key)

        # Sources gratuites (toujours disponibles)
        self.scraper = TwitterScraper()
        self.vader = VaderAnalyzer()

        self.cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[datetime, SentimentResult]] = {}

        # Detecter le mode
        self.has_api = bool(self.twitter_api.bearer_token or self.grok.api_key)
        self.has_scraper = True  # Toujours disponible

        if self.has_api:
            logger.info("Sentiment: mode API (Twitter + Grok)")
        else:
            logger.info("Sentiment: mode SCRAPER + VADER (gratuit, sans cle API)")

    def analyze(
        self,
        question: str,
        market_id: str,
        current_price: float,
        max_tweets: int = 30,
    ) -> SentimentResult:
        """Analyse complete du sentiment pour un marche."""
        # Check cache
        if market_id in self._cache:
            cached_time, cached_result = self._cache[market_id]
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                return cached_result

        # 1. Recuperer les tweets (API ou scraper)
        if self.twitter_api.bearer_token:
            query = self.twitter_api.build_query_for_market(question)
            tweets = self.twitter_api.search_tweets(query, max_results=max_tweets)
            source = "API"
        else:
            query = self.scraper.build_query_for_market(question)
            tweets = self.scraper.search_tweets(query, max_results=max_tweets)
            source = "scraper"

        logger.info(f"[{source}] '{query}' -> {len(tweets)} tweets")

        # 2. Analyser le sentiment (Grok ou VADER)
        if self.grok.api_key:
            analysis = self.grok.analyze_market_sentiment(
                question=question,
                tweets=tweets,
                current_price=current_price,
            )
            analyzer_name = "Grok"
        else:
            analysis = self.vader.estimate_probability(
                question=question,
                tweets=tweets,
                current_price=current_price,
            )
            analyzer_name = "VADER"

        # 3. Calculer les metriques
        tweet_sentiments = analysis.get("tweet_sentiments", [])
        total_engagement = sum(
            t.get("likes", 0) + t.get("retweets", 0) + t.get("replies", 0)
            for t in tweets
        )

        avg_sentiment = 0.0
        sentiment_std = 0.0
        if tweet_sentiments:
            avg_sentiment = float(np.mean(tweet_sentiments))
            sentiment_std = float(np.std(tweet_sentiments)) if len(tweet_sentiments) > 1 else 0.0

        # Sentiment pondere par engagement
        weighted_sentiment = 0.0
        if tweets and tweet_sentiments:
            weights = []
            for t in tweets[:len(tweet_sentiments)]:
                w = 1 + t.get("likes", 0) + t.get("retweets", 0) * 2 + t.get("quotes", 0) * 3
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
            grok_probability=analysis["probability"],
            grok_confidence=analysis["confidence"],
            grok_reasoning=analysis["reasoning"],
            total_engagement=total_engagement,
            bullish_ratio=bullish_ratio,
        )

        # Cache
        self._cache[market_id] = (datetime.now(), result)

        logger.info(
            f"  -> [{analyzer_name}] sentiment={avg_sentiment:+.2f} "
            f"weighted={weighted_sentiment:+.2f} "
            f"prob={analysis['probability']:.2f} "
            f"composite={result.composite_score:+.3f}"
        )

        return result

    def is_available(self) -> bool:
        """Toujours disponible grace au scraper + VADER."""
        return True
