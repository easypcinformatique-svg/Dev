#!/usr/bin/env python3
"""
Moteur de news en temps réel pour trading intraday Polymarket.
Sources: RSS feeds majeurs (gratuit, sans clé API) + Twitter scraping.
"""

import re
import time
import hashlib
import logging
try:
    from defusedxml.ElementTree import fromstring as safe_xml_fromstring
except ImportError:
    import xml.etree.ElementTree as _ET
    safe_xml_fromstring = _ET.fromstring
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import defaultdict
from typing import List, Dict, Optional, Tuple
import requests
from threading import Thread, Lock

logger = logging.getLogger("news_engine")


# ─── RSS Feeds gratuits (aucune clé API) ─────────────────────────────────────

RSS_FEEDS = {
    # Breaking news US/World
    "reuters_world": "https://feeds.reuters.com/Reuters/worldNews",
    "reuters_politics": "https://feeds.reuters.com/Reuters/PoliticsNews",
    "reuters_business": "https://feeds.reuters.com/Reuters/businessNews",
    "ap_topnews": "https://rsshub.app/apnews/topics/apf-topnews",
    "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "bbc_politics": "https://feeds.bbci.co.uk/news/politics/rss.xml",
    "nyt_world": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "nyt_politics": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    "guardian_world": "https://www.theguardian.com/world/rss",
    "cnn_top": "https://rss.cnn.com/rss/edition.rss",
    # Crypto / Finance
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "bloomberg_markets": "https://feeds.bloomberg.com/markets/news.rss",
    # Tech / Elon / AI
    "techcrunch": "https://techcrunch.com/feed/",
    "verge": "https://www.theverge.com/rss/index.xml",
}

# Mots-clés à haute valeur pour Polymarket
HIGH_VALUE_KEYWORDS = {
    # Politique US
    "trump": 3.0, "biden": 2.5, "desantis": 2.0, "congress": 1.5,
    "supreme court": 2.5, "executive order": 2.0, "impeach": 3.0,
    "indictment": 3.0, "verdict": 3.0, "resign": 3.0, "election": 2.0,
    "primary": 2.0, "senate": 1.5, "governor": 1.5, "speaker": 2.0,
    "cabinet": 1.5, "veto": 2.0, "shutdown": 2.5, "debt ceiling": 2.5,
    "tariff": 2.5, "trade war": 2.5, "sanction": 2.0,
    # Géopolitique
    "war": 3.0, "ceasefire": 3.0, "invasion": 3.0, "nato": 2.5,
    "ukraine": 2.5, "russia": 2.5, "china": 2.0, "taiwan": 3.0,
    "iran": 2.5, "north korea": 2.5, "missile": 3.0, "nuclear": 3.0,
    "peace deal": 3.0, "treaty": 2.5,
    # Finance / Crypto
    "fed": 2.5, "interest rate": 2.5, "inflation": 2.0, "recession": 2.5,
    "bitcoin": 2.0, "ethereum": 1.5, "crypto": 1.5, "sec": 2.0,
    "etf": 2.0, "default": 3.0, "bailout": 3.0, "crash": 3.0,
    # Tech / Personalités
    "elon musk": 2.5, "spacex": 2.0, "tesla": 2.0, "openai": 2.0,
    "google": 1.5, "apple": 1.5, "meta": 1.5, "tiktok": 2.0,
    # Sport (gros marchés Polymarket)
    "nba": 1.5, "nfl": 1.5, "ufc": 1.5, "champion": 1.5,
    # Catastrophes
    "earthquake": 2.5, "hurricane": 2.5, "pandemic": 3.0, "outbreak": 2.5,
}


@dataclass
class NewsItem:
    """Un article de news détecté."""
    title: str
    source: str
    url: str
    published: datetime
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    keywords_matched: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    sentiment: float = 0.0  # -1 (bearish) to +1 (bullish)
    hash_id: str = ""

    def __post_init__(self):
        self.hash_id = hashlib.sha256(
            (self.title + self.source).encode()
        ).hexdigest()[:16]


@dataclass
class BreakingAlert:
    """Alerte breaking news avec score d'urgence."""
    news_items: List[NewsItem]
    trigger_keyword: str
    urgency_score: float  # 0-10
    first_seen: datetime
    source_count: int
    velocity: float  # articles/minute
    suggested_direction: str  # "YES_UP", "YES_DOWN", "UNCERTAIN"
    matched_markets: List[dict] = field(default_factory=list)


class NewsEngine:
    """
    Moteur de détection de breaking news en temps réel.
    100% gratuit — utilise uniquement des RSS feeds publics.
    """

    def __init__(self, scan_interval: int = 30):
        self.scan_interval = scan_interval
        self.seen_hashes: set = set()
        self.news_buffer: List[NewsItem] = []
        self.alerts: List[BreakingAlert] = []
        self.keyword_velocity: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = Lock()
        self._running = False
        self._baseline_rates: Dict[str, float] = defaultdict(lambda: 0.5)  # articles/heure par keyword

    def start_background(self):
        """Lance le scan RSS en arrière-plan."""
        self._running = True
        thread = Thread(target=self._scan_loop, daemon=True)
        thread.start()
        logger.info(f"NewsEngine démarré (scan toutes les {self.scan_interval}s)")

    def stop(self):
        self._running = False

    def _scan_loop(self):
        while self._running:
            try:
                self._scan_all_feeds()
                self._detect_breaking()
                self._cleanup_old()
            except Exception as e:
                logger.error(f"NewsEngine erreur: {e}")
            time.sleep(self.scan_interval)

    def _fetch_rss(self, name: str, url: str) -> List[NewsItem]:
        """Parse un flux RSS et retourne les articles récents."""
        items = []
        try:
            resp = requests.get(url, timeout=8, headers={
                "User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)"
            })
            if not resp.ok:
                return items

            root = safe_xml_fromstring(resp.content)

            # RSS 2.0 format
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = item.findtext("pubDate") or ""

                if not title:
                    continue

                published = self._parse_date(pub_date)
                if not published:
                    published = datetime.now(timezone.utc)

                # Ignorer les articles de plus de 2h
                age = datetime.now(timezone.utc) - published
                if age > timedelta(hours=2):
                    continue

                news = NewsItem(
                    title=title,
                    source=name,
                    url=link,
                    published=published,
                )
                self._score_news(news)
                items.append(news)

            # Atom format
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                pub = entry.findtext("atom:published", namespaces=ns) or \
                      entry.findtext("atom:updated", namespaces=ns) or ""

                if not title:
                    continue

                published = self._parse_date(pub)
                if not published:
                    published = datetime.now(timezone.utc)

                age = datetime.now(timezone.utc) - published
                if age > timedelta(hours=2):
                    continue

                news = NewsItem(
                    title=title,
                    source=name,
                    url=link,
                    published=published,
                )
                self._score_news(news)
                items.append(news)

        except Exception as e:
            logger.debug(f"RSS {name} erreur: {e}")

        return items

    def _score_news(self, news: NewsItem):
        """Score un article par pertinence pour Polymarket."""
        title_lower = news.title.lower()
        total_score = 0.0
        matched = []

        for keyword, weight in HIGH_VALUE_KEYWORDS.items():
            if keyword in title_lower:
                total_score += weight
                matched.append(keyword)

        news.keywords_matched = matched
        news.relevance_score = min(total_score, 10.0)

        # Sentiment basique basé sur les mots
        bullish_words = ["deal", "peace", "agreement", "rally", "surge", "win",
                         "approve", "pass", "success", "recover", "rise", "gain"]
        bearish_words = ["crash", "war", "crisis", "fail", "reject", "loss",
                         "collapse", "default", "scandal", "arrest", "die",
                         "kill", "attack", "bomb", "strike", "sanction"]

        bull = sum(1 for w in bullish_words if w in title_lower)
        bear = sum(1 for w in bearish_words if w in title_lower)

        if bull + bear > 0:
            news.sentiment = (bull - bear) / (bull + bear)

    def _scan_all_feeds(self):
        """Scan tous les flux RSS."""
        new_items = []
        for name, url in RSS_FEEDS.items():
            items = self._fetch_rss(name, url)
            for item in items:
                if item.hash_id not in self.seen_hashes:
                    self.seen_hashes.add(item.hash_id)
                    new_items.append(item)
                    # Track keyword velocity
                    for kw in item.keywords_matched:
                        self.keyword_velocity[kw].append(
                            datetime.now(timezone.utc)
                        )

        with self._lock:
            self.news_buffer.extend(new_items)
            # Nettoyage périodique des velocity timestamps (> 30 min)
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            for kw in list(self.keyword_velocity.keys()):
                self.keyword_velocity[kw] = [
                    t for t in self.keyword_velocity[kw] if t > cutoff
                ]
                if not self.keyword_velocity[kw]:
                    del self.keyword_velocity[kw]

        if new_items:
            high_relevance = [n for n in new_items if n.relevance_score >= 2.0]
            if high_relevance:
                logger.info(
                    f"📰 {len(new_items)} news ({len(high_relevance)} haute pertinence)"
                )
                for n in high_relevance[:3]:
                    logger.info(f"   → [{n.source}] {n.title[:80]} (score={n.relevance_score:.1f})")

    def _detect_breaking(self):
        """Détecte les breaking news par clustering de keywords."""
        now = datetime.now(timezone.utc)
        window = timedelta(minutes=15)

        for keyword, timestamps in self.keyword_velocity.items():
            # Garder seulement les 15 dernières minutes
            recent = [t for t in timestamps if now - t < window]
            self.keyword_velocity[keyword] = recent

            if len(recent) < 3:
                continue

            # Velocity = articles/minute
            if len(recent) >= 2:
                span = (recent[-1] - recent[0]).total_seconds() / 60.0
                velocity = len(recent) / max(span, 0.5)
            else:
                velocity = 0

            # Baseline comparison
            baseline = self._baseline_rates[keyword]
            spike_ratio = velocity / max(baseline, 0.01)

            if spike_ratio >= 3.0 and len(recent) >= 3:
                # BREAKING NEWS détecté !
                with self._lock:
                    related_news = [
                        n for n in self.news_buffer
                        if keyword in n.keywords_matched
                        and now - n.detected_at < window
                    ]

                sources = len(set(n.source for n in related_news))
                avg_sentiment = (
                    sum(n.sentiment for n in related_news) / len(related_news)
                    if related_news else 0
                )

                if avg_sentiment > 0.2:
                    direction = "YES_UP"
                elif avg_sentiment < -0.2:
                    direction = "YES_DOWN"
                else:
                    direction = "UNCERTAIN"

                urgency = min(10.0, spike_ratio * 1.5 + sources * 0.5)

                alert = BreakingAlert(
                    news_items=related_news,
                    trigger_keyword=keyword,
                    urgency_score=urgency,
                    first_seen=related_news[0].detected_at if related_news else now,
                    source_count=sources,
                    velocity=velocity,
                    suggested_direction=direction,
                )

                # Éviter les doublons
                existing = [a for a in self.alerts
                            if a.trigger_keyword == keyword
                            and now - a.first_seen < timedelta(minutes=30)]
                if not existing:
                    self.alerts.append(alert)
                    logger.warning(
                        f"🚨 BREAKING: '{keyword}' | urgence={urgency:.1f} | "
                        f"{sources} sources | vel={velocity:.1f}/min | "
                        f"direction={direction}"
                    )

            # Update baseline (slow EMA)
            self._baseline_rates[keyword] = (
                0.95 * baseline + 0.05 * velocity
            )

    def _cleanup_old(self):
        """Nettoie les données anciennes."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=4)

        with self._lock:
            self.news_buffer = [
                n for n in self.news_buffer if n.detected_at > cutoff
            ]
            self.alerts = [
                a for a in self.alerts if a.first_seen > cutoff
            ]

        # Limiter les hashes en mémoire
        if len(self.seen_hashes) > 10000:
            self.seen_hashes = set(list(self.seen_hashes)[-5000:])

    def get_recent_alerts(self, minutes: int = 30) -> List[BreakingAlert]:
        """Retourne les alertes des N dernières minutes."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        with self._lock:
            return [a for a in self.alerts if a.first_seen > cutoff]

    def get_news_for_keywords(self, keywords: List[str],
                               minutes: int = 60) -> List[NewsItem]:
        """Retourne les news récentes matchant des keywords."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        results = []
        with self._lock:
            for news in self.news_buffer:
                if news.detected_at < cutoff:
                    continue
                title_lower = news.title.lower()
                if any(kw.lower() in title_lower for kw in keywords):
                    results.append(news)
        return sorted(results, key=lambda n: n.detected_at, reverse=True)

    def get_keyword_velocity(self, keyword: str) -> float:
        """Retourne la vélocité actuelle d'un keyword (articles/minute)."""
        now = datetime.now(timezone.utc)
        with self._lock:
            timestamps = list(self.keyword_velocity.get(keyword, []))
        recent = [t for t in timestamps if now - t < timedelta(minutes=15)]
        if len(recent) < 2:
            return 0.0
        span = (recent[-1] - recent[0]).total_seconds() / 60.0
        return len(recent) / max(span, 0.5)

    def match_news_to_market(self, market_question: str,
                              minutes: int = 30) -> Tuple[float, List[NewsItem]]:
        """
        Match les news récentes à un marché Polymarket.
        Retourne (score_pertinence, [news_matchées]).
        """
        # Extraire les mots-clés du marché
        question_lower = market_question.lower()
        # Retirer les mots communs
        stop_words = {"will", "the", "be", "a", "an", "in", "on", "by", "to",
                      "of", "and", "or", "for", "is", "at", "it", "this",
                      "that", "with", "from", "as", "are", "was", "has",
                      "have", "do", "does", "did", "not", "no", "yes",
                      "before", "after", "between", "more", "than", "over",
                      "under", "win", "lose"}

        words = re.findall(r'\b[a-z]{3,}\b', question_lower)
        keywords = [w for w in words if w not in stop_words]

        # Ajouter les noms propres (majuscules dans la question originale)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', market_question)
        keywords.extend([n.lower() for n in proper_nouns])

        matched_news = self.get_news_for_keywords(keywords, minutes)
        if not matched_news:
            return 0.0, []

        # Score = somme des relevance scores normalisée
        total_relevance = sum(n.relevance_score for n in matched_news)
        source_diversity = len(set(n.source for n in matched_news))

        score = min(10.0, total_relevance * 0.5 + source_diversity * 1.0)
        return score, matched_news

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse divers formats de date RSS."""
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return None
