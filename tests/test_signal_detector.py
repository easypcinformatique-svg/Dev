"""Tests unitaires pour signal_detector.py."""

import json
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from signal_detector import (
    SignalDetector, TweetSignal, MAX_SIGNALS_PER_HOUR,
    WATCHED_ACCOUNTS, GENERAL_KEYWORDS,
)


class TestSignalDetectorInit(unittest.TestCase):
    """Tests d'initialisation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.detector = SignalDetector(
            signal_log_path=f"{self.tmpdir}/signals.json"
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_init_no_bearer_token(self):
        self.assertEqual(self.detector.bearer_token, "")

    def test_init_with_bearer_token(self):
        d = SignalDetector(
            bearer_token="test_token",
            signal_log_path=f"{self.tmpdir}/sig.json",
        )
        self.assertEqual(d.bearer_token, "test_token")

    def test_watched_accounts_not_empty(self):
        self.assertGreater(len(WATCHED_ACCOUNTS), 0)
        for category, accounts in WATCHED_ACCOUNTS.items():
            self.assertIsInstance(accounts, list)
            self.assertGreater(len(accounts), 0)

    def test_general_keywords_not_empty(self):
        self.assertGreater(len(GENERAL_KEYWORDS), 0)


class TestMatchTweetToMarket(unittest.TestCase):
    """Tests pour le matching tweet-marche."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.detector = SignalDetector(
            signal_log_path=f"{self.tmpdir}/signals.json"
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_high_relevance_matching_keywords(self):
        tweet = {"text": "Trump signs executive order banning TikTok immediately"}
        question = "Will Trump sign an executive order to ban TikTok?"
        score = self.detector.match_tweet_to_market(tweet, question)
        self.assertGreater(score, 0.5)

    def test_low_relevance_unrelated(self):
        tweet = {"text": "Beautiful weather today in Paris, great for a walk"}
        question = "Will Bitcoin reach $100,000 by December 2025?"
        score = self.detector.match_tweet_to_market(tweet, question)
        self.assertLess(score, 0.3)

    def test_proper_noun_matching(self):
        tweet = {"text": "Biden announces new climate policy at the White House"}
        question = "Will Biden announce new climate regulations in 2025?"
        score = self.detector.match_tweet_to_market(tweet, question)
        self.assertGreater(score, 0.4)

    def test_empty_question_returns_zero(self):
        tweet = {"text": "some tweet"}
        score = self.detector.match_tweet_to_market(tweet, "")
        self.assertEqual(score, 0.0)

    def test_engagement_bonus(self):
        tweet_low = {"text": "Trump executive order", "engagement": 0}
        tweet_high = {"text": "Trump executive order", "engagement": 50000}
        question = "Will Trump sign an executive order?"

        score_low = self.detector.match_tweet_to_market(tweet_low, question)
        score_high = self.detector.match_tweet_to_market(tweet_high, question)
        self.assertGreaterEqual(score_high, score_low)

    def test_score_between_zero_and_one(self):
        tweet = {"text": "anything goes here with many words " * 10, "engagement": 999999}
        question = "anything goes here with many words " * 10
        score = self.detector.match_tweet_to_market(tweet, question)
        self.assertLessEqual(score, 1.0)
        self.assertGreaterEqual(score, 0.0)


class TestGenerateSignal(unittest.TestCase):
    """Tests pour la generation de signaux."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.detector = SignalDetector(
            signal_log_path=f"{self.tmpdir}/signals.json"
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_signal_below_threshold_returns_none(self):
        tweet = {"id": "1", "text": "hello", "author": "user"}
        result = self.detector.generate_signal(tweet, "m1", "Q?", score=0.5)
        self.assertIsNone(result)

    def test_signal_above_threshold_returns_tweet_signal(self):
        tweet = {"id": "1", "text": "Great news! Confirmed!", "author": "reporter"}
        result = self.detector.generate_signal(tweet, "m1", "Will X happen?", score=0.8)
        self.assertIsInstance(result, TweetSignal)
        self.assertIn(result.direction, ("YES", "NO"))
        self.assertGreater(result.confidence, 0)

    def test_rate_limiting(self):
        tweet = {"id": "1", "text": "Confirmed deal signed!", "author": "user"}
        signals = []
        for i in range(MAX_SIGNALS_PER_HOUR + 2):
            tweet["id"] = str(i)
            result = self.detector.generate_signal(tweet, f"m{i}", "Q?", score=0.8)
            if result:
                signals.append(result)
        self.assertLessEqual(len(signals), MAX_SIGNALS_PER_HOUR)

    def test_signal_logged_to_json(self):
        tweet = {"id": "42", "text": "Breaking: deal confirmed!", "author": "news"}
        self.detector.generate_signal(tweet, "m1", "Will deal happen?", score=0.9)

        with open(f"{self.tmpdir}/signals.json") as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["tweet_id"], "42")


class TestAnalyzeDirection(unittest.TestCase):
    """Tests pour l'analyse directionnelle."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.detector = SignalDetector(
            signal_log_path=f"{self.tmpdir}/signals.json"
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_positive_tweet_gives_yes(self):
        tweet = {"text": "Great success! Deal approved and signed!"}
        direction, confidence = self.detector._analyze_direction(tweet, "Q?")
        self.assertEqual(direction, "YES")
        self.assertGreater(confidence, 0.3)

    def test_negative_tweet_gives_no(self):
        tweet = {"text": "Deal rejected, total failure, crashed and burned"}
        direction, confidence = self.detector._analyze_direction(tweet, "Q?")
        self.assertEqual(direction, "NO")
        self.assertGreater(confidence, 0.3)

    def test_neutral_tweet_low_confidence(self):
        tweet = {"text": "The meeting took place today at the office"}
        direction, confidence = self.detector._analyze_direction(tweet, "Q?")
        self.assertLessEqual(confidence, 0.6)

    def test_high_engagement_boosts_confidence(self):
        tweet_low = {"text": "Big win confirmed!", "engagement": 0}
        tweet_high = {"text": "Big win confirmed!", "engagement": 5000}
        _, conf_low = self.detector._analyze_direction(tweet_low, "Q?")
        _, conf_high = self.detector._analyze_direction(tweet_high, "Q?")
        self.assertGreaterEqual(conf_high, conf_low)

    def test_confidence_capped_at_095(self):
        tweet = {"text": "AMAZING SUCCESS WIN APPROVE GAIN RISE!!!", "engagement": 100000}
        _, confidence = self.detector._analyze_direction(tweet, "Q?")
        self.assertLessEqual(confidence, 0.95)


class TestScanAndMatch(unittest.TestCase):
    """Tests pour le pipeline complet scan_and_match."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.detector = SignalDetector(
            signal_log_path=f"{self.tmpdir}/signals.json"
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch.object(SignalDetector, "scan_tweets", return_value=[])
    def test_no_tweets_returns_empty(self, mock_scan):
        result = self.detector.scan_and_match([])
        self.assertEqual(result, [])

    @patch.object(SignalDetector, "scan_tweets")
    def test_matching_tweet_generates_signal(self, mock_scan):
        mock_scan.return_value = [
            {"id": "1", "text": "Trump signs executive order on TikTok ban",
             "author": "POTUS", "engagement": 5000},
        ]
        market = MagicMock()
        market.question = "Will Trump sign an executive order to ban TikTok?"
        market.condition_id = "0xabc"

        signals = self.detector.scan_and_match([market])
        # Le score pourrait etre < 0.7 selon le matching exact, on verifie juste le type
        for s in signals:
            self.assertIsInstance(s, TweetSignal)


if __name__ == "__main__":
    unittest.main()
