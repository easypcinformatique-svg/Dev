"""
Detecteur de signaux Twitter/News pour le bot Polymarket.

Surveille des comptes Twitter cles par categorie, detecte les tweets pertinents
pour les marches Polymarket ouverts, et genere des signaux directionnels.

Utilise le module sentiment existant (backtest/sentiment.py) pour l'analyse,
et ajoute une couche de matching tweet-marche + rate limiting.

Usage :
    detector = SignalDetector()
    signals = detector.scan_and_match(markets)
"""

import os
import re
import time
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

import requests
import numpy as np

logger = logging.getLogger("signal_detector")

# ================================================================
#  CONFIGURATION
# ================================================================

# Comptes Twitter a surveiller par categorie (defaut, surchargeable via constructeur)
DEFAULT_WATCHED_ACCOUNTS = {
    "politique_us": [
        "realDonaldTrump", "POTUS", "WhiteHouse", "SpeakerJohnson",
        "VP", "SecYellen",
    ],
    "crypto": [
        "cz_binance", "saylor", "coinbase", "VitalikButerin",
        "elikiara", "brian_armstrong",
    ],
    "economie": [
        "federalreserve", "WSJ", "Bloomberg", "Reuters",
        "business", "FT",
    ],
    "geopolitique": [
        "NATO", "UN", "SecBlinken", "WarMonitor3",
    ],
}
# Retrocompatibilite
WATCHED_ACCOUNTS = DEFAULT_WATCHED_ACCOUNTS

# Mots-cles generaux a surveiller
GENERAL_KEYWORDS = [
    "polymarket", "prediction market", "betting odds",
    "executive order", "breaking", "just in",
    "federal reserve", "rate cut", "rate hike",
    "war", "ceasefire", "peace deal",
    "indictment", "impeach", "resign",
    "bitcoin", "crypto", "SEC",
    "election", "poll", "debate",
]

TWITTER_API_URL = "https://api.twitter.com/2/tweets/search/recent"
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]

MAX_SIGNALS_PER_HOUR = 3


@dataclass
class TweetSignal:
    """Signal genere a partir d'un tweet."""
    tweet_id: str
    tweet_text: str
    author: str
    market_id: str
    market_question: str
    relevance_score: float  # 0.0 a 1.0
    direction: str          # "YES" ou "NO"
    confidence: float       # 0.0 a 1.0
    timestamp: str
    category: str = ""


class SignalDetector:
    """Detecteur de signaux base sur Twitter/News."""

    def __init__(self, bearer_token: str = "", signal_log_path: str = "logs/signals.json",
                 watched_accounts: dict[str, list[str]] | None = None):
        """Initialise le detecteur de signaux Twitter/News.

        Args:
            bearer_token: Token Twitter API (ou via env TWITTER_BEARER_TOKEN).
            signal_log_path: Chemin du fichier de log des signaux.
            watched_accounts: Comptes Twitter a surveiller par categorie.
                Si None, utilise DEFAULT_WATCHED_ACCOUNTS.
        """
        self.bearer_token = bearer_token or os.environ.get("TWITTER_BEARER_TOKEN", "")
        self.signal_log_path = Path(signal_log_path)
        self.signal_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.watched_accounts = watched_accounts or DEFAULT_WATCHED_ACCOUNTS

        # Rate limiting
        self._signals_this_hour: list[str] = []  # timestamps
        self._last_scan: Optional[datetime] = None

        # Cache des signaux generes
        self._recent_signals: list[TweetSignal] = []

        # Session HTTP
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "PolymarketBot/1.0",
        })

        if self.bearer_token:
            logger.info("SignalDetector: Twitter API v2 active")
        else:
            logger.info("SignalDetector: mode scraping (pas de bearer token)")

    # ------------------------------------------------------------------
    #  SCAN DES TWEETS
    # ------------------------------------------------------------------

    def scan_tweets(self, keywords: list[str] = None,
                    since_minutes: int = 5) -> list[dict]:
        """
        Cherche les tweets/news recents contenant des mots-cles.
        Fallback : Twitter API -> Nitter scraping -> RSS News feeds.

        Returns:
            Liste de dicts {id, text, author, created_at, engagement}.
        """
        if keywords is None:
            keywords = GENERAL_KEYWORDS

        tweets = []

        if self.bearer_token:
            tweets = self._scan_twitter_api(keywords, since_minutes)

        if not tweets:
            tweets = self._scan_nitter(keywords, since_minutes)

        # Fallback RSS si aucun tweet trouve
        if not tweets:
            tweets = self._scan_rss_feeds(keywords)

        # Aussi scanner les comptes surveilles
        for category, accounts in self.watched_accounts.items():
            for account in accounts[:3]:  # Limiter pour eviter le rate limit
                try:
                    account_tweets = self._get_account_tweets(account, since_minutes)
                    for t in account_tweets:
                        t["category"] = category
                    tweets.extend(account_tweets)
                except Exception as e:
                    logger.debug(f"Erreur scan @{account}: {e}")

        logger.info(f"SignalDetector: {len(tweets)} tweets trouves")
        return tweets

    def _scan_twitter_api(self, keywords: list[str],
                          since_minutes: int) -> list[dict]:
        """Scan via l'API Twitter v2 officielle."""
        if not self.bearer_token:
            return []

        query = " OR ".join(f'"{kw}"' for kw in keywords[:10])
        query += " -is:retweet lang:en"

        since = datetime.utcnow() - timedelta(minutes=since_minutes)
        params = {
            "query": query,
            "max_results": 50,
            "start_time": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tweet.fields": "created_at,public_metrics,author_id",
        }
        headers = {"Authorization": f"Bearer {self.bearer_token}"}

        try:
            resp = self._session.get(TWITTER_API_URL, params=params,
                                     headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            tweets = []
            for t in data.get("data", []):
                metrics = t.get("public_metrics", {})
                tweets.append({
                    "id": t["id"],
                    "text": t["text"],
                    "author": t.get("author_id", ""),
                    "created_at": t.get("created_at", ""),
                    "engagement": (
                        metrics.get("like_count", 0) +
                        metrics.get("retweet_count", 0) * 2 +
                        metrics.get("reply_count", 0)
                    ),
                    "category": "",
                })
            return tweets
        except Exception as e:
            logger.warning(f"Twitter API scan echoue: {e}")
            return []

    def _scan_nitter(self, keywords: list[str],
                     since_minutes: int) -> list[dict]:
        """Scan via Nitter (fallback sans API key)."""
        from bs4 import BeautifulSoup

        tweets = []
        query = " OR ".join(keywords[:5])

        for instance in NITTER_INSTANCES:
            try:
                url = f"{instance}/search?f=tweets&q={requests.utils.quote(query)}"
                resp = self._session.get(url, timeout=10)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                for item in soup.select(".timeline-item")[:20]:
                    text_el = item.select_one(".tweet-content")
                    if not text_el:
                        continue
                    username_el = item.select_one(".username")
                    tweets.append({
                        "id": f"nitter-{hash(text_el.text)%10**8}",
                        "text": text_el.text.strip(),
                        "author": username_el.text.strip() if username_el else "",
                        "created_at": datetime.utcnow().isoformat(),
                        "engagement": 0,
                        "category": "",
                    })
                if tweets:
                    break  # Un seul instance suffit
            except Exception as e:
                logger.debug(f"Nitter {instance} echoue: {e}")
                continue

        return tweets

    def _scan_rss_feeds(self, keywords: list[str]) -> list[dict]:
        """Fallback: scan des flux RSS d'actualites financieres/crypto."""
        RSS_FEEDS = [
            "https://feeds.bbci.co.uk/news/business/rss.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
        ]
        tweets = []
        kw_lower = [kw.lower() for kw in keywords[:10]]

        for feed_url in RSS_FEEDS:
            try:
                resp = self._session.get(feed_url, timeout=10)
                if resp.status_code != 200:
                    continue

                # Parse XML basique sans dependance
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)

                for item in root.iter("item"):
                    title_el = item.find("title")
                    desc_el = item.find("description")
                    title = title_el.text if title_el is not None and title_el.text else ""
                    desc = desc_el.text if desc_el is not None and desc_el.text else ""
                    text = f"{title} {desc}".strip()

                    # Filtre par mots-cles
                    text_lower = text.lower()
                    if any(kw in text_lower for kw in kw_lower):
                        tweets.append({
                            "id": f"rss-{hash(text)%10**8}",
                            "text": text[:300],
                            "author": feed_url.split("/")[2],
                            "created_at": datetime.utcnow().isoformat(),
                            "engagement": 50,
                            "category": "news_rss",
                        })

                    if len(tweets) >= 15:
                        break
                if len(tweets) >= 15:
                    break
            except Exception as e:
                logger.debug(f"RSS feed {feed_url} echoue: {e}")
                continue

        if tweets:
            logger.info(f"SignalDetector: {len(tweets)} articles RSS (fallback)")
        return tweets

    def _get_account_tweets(self, username: str,
                            since_minutes: int) -> list[dict]:
        """Recupere les tweets recents d'un compte specifique."""
        if self.bearer_token:
            # Via API officielle — necessite user lookup d'abord
            # Simplifie : on utilise la recherche avec from:username
            query = f"from:{username} -is:retweet"
            since = datetime.utcnow() - timedelta(minutes=since_minutes)
            params = {
                "query": query,
                "max_results": 10,
                "start_time": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tweet.fields": "created_at,public_metrics",
            }
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            resp = self._session.get(TWITTER_API_URL, params=params,
                                     headers=headers, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [
                {
                    "id": t["id"],
                    "text": t["text"],
                    "author": username,
                    "created_at": t.get("created_at", ""),
                    "engagement": sum(t.get("public_metrics", {}).values()),
                }
                for t in data.get("data", [])
            ]
        else:
            # Via Nitter
            from bs4 import BeautifulSoup
            for instance in NITTER_INSTANCES[:2]:
                try:
                    resp = self._session.get(f"{instance}/{username}", timeout=10)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    tweets = []
                    for item in soup.select(".timeline-item")[:5]:
                        text_el = item.select_one(".tweet-content")
                        if text_el:
                            tweets.append({
                                "id": f"nitter-{hash(text_el.text)%10**8}",
                                "text": text_el.text.strip(),
                                "author": username,
                                "created_at": datetime.utcnow().isoformat(),
                                "engagement": 0,
                            })
                    return tweets
                except Exception:
                    continue
        return []

    # ------------------------------------------------------------------
    #  MATCHING TWEET <-> MARCHE
    # ------------------------------------------------------------------

    def match_tweet_to_market(self, tweet: dict, market_question: str) -> float:
        """
        Retourne un score de pertinence (0 a 1) entre un tweet et un marche.

        Utilise le matching par mots-cles + NLP basique.
        """
        tweet_text = tweet.get("text", "").lower()
        question = market_question.lower()

        # Extraire les mots significatifs de la question du marche
        # (exclure les stop words courants)
        stop_words = {"will", "the", "a", "an", "in", "on", "at", "to", "for",
                      "of", "is", "be", "by", "or", "and", "before", "after",
                      "this", "that", "it", "do", "does", "did", "has", "have",
                      "with", "from", "as", "if", "not", "no", "yes", "more",
                      "than", "who", "what", "when", "where", "which"}
        question_words = set(re.findall(r'\b\w{3,}\b', question)) - stop_words
        tweet_words = set(re.findall(r'\b\w{3,}\b', tweet_text))

        if not question_words:
            return 0.0

        # Score de chevauchement de mots-cles
        overlap = question_words & tweet_words
        keyword_score = len(overlap) / len(question_words)

        # Bonus pour les noms propres (entites nommees simplifiees)
        proper_nouns = set(re.findall(r'\b[A-Z][a-z]+\b', market_question))
        proper_overlap = sum(1 for n in proper_nouns if n.lower() in tweet_text)
        proper_score = proper_overlap / max(len(proper_nouns), 1)

        # Bonus engagement
        engagement = tweet.get("engagement", 0)
        engagement_bonus = min(0.1, engagement / 10000)

        score = 0.5 * keyword_score + 0.4 * proper_score + engagement_bonus
        return min(1.0, score)

    # ------------------------------------------------------------------
    #  GENERATION DE SIGNAUX
    # ------------------------------------------------------------------

    def generate_signal(self, tweet: dict, market_id: str,
                        market_question: str, score: float) -> Optional[TweetSignal]:
        """
        Genere un signal directionnel si le score de pertinence > 0.7.

        Returns:
            TweetSignal ou None si le score est trop faible.
        """
        if score < 0.7:
            return None

        # Rate limiting : max 3 signaux par heure
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        self._signals_this_hour = [
            ts for ts in self._signals_this_hour
            if datetime.fromisoformat(ts) > cutoff
        ]
        if len(self._signals_this_hour) >= MAX_SIGNALS_PER_HOUR:
            logger.info("SignalDetector: rate limit atteint (3/h)")
            return None

        # Determiner la direction basee sur le sentiment du tweet
        direction, confidence = self._analyze_direction(tweet, market_question)

        signal = TweetSignal(
            tweet_id=tweet.get("id", ""),
            tweet_text=tweet.get("text", "")[:200],
            author=tweet.get("author", ""),
            market_id=market_id,
            market_question=market_question,
            relevance_score=score,
            direction=direction,
            confidence=confidence,
            timestamp=now.isoformat(),
            category=tweet.get("category", ""),
        )

        self._signals_this_hour.append(now.isoformat())
        self._recent_signals.append(signal)
        self._log_signal(signal)

        logger.info(
            f"[SIGNAL] {direction} (conf={confidence:.2f}, rel={score:.2f}) | "
            f"@{signal.author}: {signal.tweet_text[:80]}... -> {market_question[:50]}"
        )
        return signal

    def _analyze_direction(self, tweet: dict,
                           market_question: str) -> tuple[str, float]:
        """
        Determine la direction (YES/NO) et la confiance a partir du tweet.

        Utilise VADER pour le sentiment + heuristiques.
        """
        text = tweet.get("text", "")

        # Essayer VADER
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            sid = SentimentIntensityAnalyzer()
            scores = sid.polarity_scores(text)
            compound = scores["compound"]
        except Exception:
            # Fallback heuristique
            positive_words = ["win", "pass", "approve", "success", "rise", "gain",
                              "confirmed", "yes", "agreed", "deal", "signed"]
            negative_words = ["fail", "reject", "lose", "drop", "fall", "no",
                              "block", "deny", "cancel", "crash", "war"]
            text_lower = text.lower()
            pos = sum(1 for w in positive_words if w in text_lower)
            neg = sum(1 for w in negative_words if w in text_lower)
            compound = (pos - neg) / max(pos + neg, 1)

        # Mapping sentiment -> direction
        if compound > 0.1:
            direction = "YES"
            confidence = min(0.9, 0.5 + compound * 0.4)
        elif compound < -0.1:
            direction = "NO"
            confidence = min(0.9, 0.5 + abs(compound) * 0.4)
        else:
            direction = "YES"
            confidence = 0.3  # Signal faible

        # Bonus engagement
        engagement = tweet.get("engagement", 0)
        if engagement > 1000:
            confidence = min(0.95, confidence + 0.1)

        return direction, round(confidence, 2)

    # ------------------------------------------------------------------
    #  SCAN COMPLET
    # ------------------------------------------------------------------

    def scan_and_match(self, markets: list) -> list[TweetSignal]:
        """
        Pipeline complet : scan tweets -> match avec marches -> genere signaux.

        Args:
            markets: liste d'objets PolymarketMarket (ou dicts avec question, condition_id)

        Returns:
            Liste de TweetSignal generes.
        """
        tweets = self.scan_tweets()
        if not tweets:
            return []

        signals = []
        for tweet in tweets:
            for market in markets:
                question = (market.question if hasattr(market, "question")
                            else market.get("question", ""))
                market_id = (market.condition_id if hasattr(market, "condition_id")
                             else market.get("condition_id", ""))

                score = self.match_tweet_to_market(tweet, question)
                if score >= 0.7:
                    signal = self.generate_signal(tweet, market_id, question, score)
                    if signal:
                        signals.append(signal)

                    # Rate limit check
                    if len(self._signals_this_hour) >= MAX_SIGNALS_PER_HOUR:
                        return signals

        return signals

    # ------------------------------------------------------------------
    #  LOGGING
    # ------------------------------------------------------------------

    def _log_signal(self, signal: TweetSignal):
        """Sauvegarde un signal dans le fichier JSON."""
        existing = []
        if self.signal_log_path.exists():
            try:
                with open(self.signal_log_path) as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, TypeError):
                existing = []

        existing.append({
            "tweet_id": signal.tweet_id,
            "author": signal.author,
            "tweet_text": signal.tweet_text,
            "market_id": signal.market_id,
            "market_question": signal.market_question,
            "relevance_score": signal.relevance_score,
            "direction": signal.direction,
            "confidence": signal.confidence,
            "timestamp": signal.timestamp,
            "category": signal.category,
        })

        # Garder les 500 derniers signaux
        existing = existing[-500:]

        with open(self.signal_log_path, "w") as f:
            json.dump(existing, f, indent=2)

    @property
    def recent_signals(self) -> list[TweetSignal]:
        return list(self._recent_signals[-20:])
