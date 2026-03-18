"""
Client Polymarket unifié — Gamma API + CLOB API + WebSocket.

Gère :
- Découverte des marchés (Gamma API)
- Prix, orderbooks, midpoints (CLOB API)
- Données historiques pour backtesting
- Placement d'ordres (limit, market, FOK)
- WebSocket temps réel
"""

import json
import time
import logging
import requests
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon


@dataclass
class PolymarketMarket:
    """Marché Polymarket avec toutes les métadonnées."""
    condition_id: str
    question: str
    category: str
    yes_token_id: str
    no_token_id: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: float
    active: bool
    closed: bool
    end_date: Optional[str] = None
    description: str = ""
    slug: str = ""
    market_maker_address: str = ""
    tick_size: float = 0.01


@dataclass
class OrderBookLevel:
    """Niveau dans l'orderbook."""
    price: float
    size: float


@dataclass
class OrderBook:
    """Orderbook complet d'un token."""
    token_id: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    midpoint: float
    spread: float
    best_bid: float
    best_ask: float


class PolymarketClient:
    """
    Client read-only pour les données Polymarket.
    Utilisé pour le backtesting et l'analyse.
    Pas besoin d'authentification.
    """

    def __init__(self, rate_limit_delay: float = 0.2):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PolymarketBacktestBot/1.0",
        })
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Respecter le rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, params: dict | None = None, retries: int = 3) -> dict | list:
        """GET avec retry et rate limiting."""
        for attempt in range(retries):
            self._rate_limit()
            try:
                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code == 404:
                    return {}  # Resource not found, no retry
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt < retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Request failed: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        return {}

    # ================================================================
    #  GAMMA API — Découverte des marchés
    # ================================================================

    def get_markets(
        self,
        active: bool = True,
        limit: int = 100,
        offset: int = 0,
        order: str = "volume",
        ascending: bool = False,
        tag: str | None = None,
        volume_min: float | None = None,
        liquidity_min: float | None = None,
    ) -> list[PolymarketMarket]:
        """Récupère les marchés depuis la Gamma API."""
        params = {
            "active": str(active).lower(),
            "limit": limit,
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
        }
        if tag:
            params["tag"] = tag
        if volume_min is not None:
            params["volume_num_min"] = volume_min
        if liquidity_min is not None:
            params["liquidity_num_min"] = liquidity_min

        raw_markets = self._get(f"{GAMMA_API_URL}/markets", params)
        return [self._parse_market(m) for m in raw_markets if self._is_valid_market(m)]

    def get_all_active_markets(
        self,
        min_volume: float = 10000,
        min_liquidity: float = 1000,
        max_markets: int = 500,
    ) -> list[PolymarketMarket]:
        """Récupère tous les marchés actifs avec pagination."""
        all_markets = []
        offset = 0
        batch_size = 100

        while len(all_markets) < max_markets:
            batch = self.get_markets(
                active=True,
                limit=batch_size,
                offset=offset,
                volume_min=min_volume,
                liquidity_min=min_liquidity,
            )
            if not batch:
                break
            all_markets.extend(batch)
            offset += batch_size
            if len(batch) < batch_size:
                break

        logger.info(f"Fetched {len(all_markets)} active markets")
        return all_markets[:max_markets]

    def get_market_by_condition(self, condition_id: str) -> PolymarketMarket | None:
        """Récupère un marché spécifique par condition_id."""
        raw = self._get(f"{GAMMA_API_URL}/markets", {"condition_ids": condition_id})
        if raw:
            return self._parse_market(raw[0])
        return None

    def search_markets(self, query: str, limit: int = 20) -> list[PolymarketMarket]:
        """Recherche de marchés par texte."""
        raw = self._get(f"{GAMMA_API_URL}/markets", {
            "active": "true",
            "limit": limit,
            "_q": query,
        })
        return [self._parse_market(m) for m in raw if self._is_valid_market(m)]

    def get_events(self, active: bool = True, limit: int = 50) -> list[dict]:
        """Récupère les événements (groupes de marchés)."""
        return self._get(f"{GAMMA_API_URL}/events", {
            "active": str(active).lower(),
            "limit": limit,
            "order": "volume",
            "ascending": "false",
        })

    def _is_valid_market(self, raw: dict) -> bool:
        """Vérifie qu'un marché a les données nécessaires et est tradable."""
        try:
            token_ids = json.loads(raw.get("clobTokenIds", "[]"))
            if len(token_ids) < 2:
                return False
            if not raw.get("enableOrderBook", False):
                return False
            # Exclure les marchés résolus (prix à 0 ou 1)
            prices = json.loads(raw.get("outcomePrices", '["0.5","0.5"]'))
            yes_price = float(prices[0]) if prices else 0.5
            if yes_price <= 0.02 or yes_price >= 0.98:
                return False
            # Exclure les marchés sans liquidité
            liquidity = float(raw.get("liquidity", 0) or 0)
            if liquidity <= 0:
                return False
            return True
        except (json.JSONDecodeError, TypeError, ValueError):
            return False

    def _parse_market(self, raw: dict) -> PolymarketMarket:
        """Parse un marché brut de la Gamma API."""
        token_ids = json.loads(raw.get("clobTokenIds", "[]"))
        outcomes = json.loads(raw.get("outcomes", '["Yes","No"]'))
        prices = json.loads(raw.get("outcomePrices", '["0.5","0.5"]'))

        return PolymarketMarket(
            condition_id=raw.get("conditionId", ""),
            question=raw.get("question", ""),
            category=raw.get("tags", [{}])[0].get("label", "other") if raw.get("tags") else raw.get("groupItemTitle", "other"),
            yes_token_id=token_ids[0] if len(token_ids) > 0 else "",
            no_token_id=token_ids[1] if len(token_ids) > 1 else "",
            yes_price=float(prices[0]) if prices else 0.5,
            no_price=float(prices[1]) if len(prices) > 1 else 0.5,
            volume=float(raw.get("volume", 0) or 0),
            liquidity=float(raw.get("liquidity", 0) or 0),
            active=bool(raw.get("active", False)),
            closed=bool(raw.get("closed", False)),
            end_date=raw.get("endDate"),
            description=raw.get("description", ""),
            slug=raw.get("slug", ""),
            market_maker_address=raw.get("marketMakerAddress", ""),
        )

    # ================================================================
    #  CLOB API — Prix et Orderbooks
    # ================================================================

    def get_midpoint(self, token_id: str) -> float:
        """Prix midpoint d'un token."""
        data = self._get(f"{CLOB_API_URL}/midpoint", {"token_id": token_id})
        return float(data.get("mid", 0.5))

    def get_price(self, token_id: str, side: str = "BUY") -> float:
        """Meilleur prix bid ou ask."""
        data = self._get(f"{CLOB_API_URL}/price", {
            "token_id": token_id,
            "side": side.upper(),
        })
        return float(data.get("price", 0.5))

    def get_orderbook(self, token_id: str) -> OrderBook:
        """Orderbook complet d'un token."""
        data = self._get(f"{CLOB_API_URL}/book", {"token_id": token_id})

        bids = [OrderBookLevel(float(b["price"]), float(b["size"]))
                for b in data.get("bids", [])]
        asks = [OrderBookLevel(float(a["price"]), float(a["size"]))
                for a in data.get("asks", [])]

        best_bid = bids[0].price if bids else 0.0
        best_ask = asks[0].price if asks else 1.0
        midpoint = (best_bid + best_ask) / 2 if bids and asks else 0.5
        spread = best_ask - best_bid if bids and asks else 1.0

        return OrderBook(
            token_id=token_id,
            bids=bids,
            asks=asks,
            midpoint=midpoint,
            spread=spread,
            best_bid=best_bid,
            best_ask=best_ask,
        )

    def get_spread(self, token_id: str) -> dict:
        """Spread actuel d'un token."""
        data = self._get(f"{CLOB_API_URL}/spread", {"token_id": token_id})
        return {
            "spread": float(data.get("spread", 1.0)),
            "bid": float(data.get("bid", 0.0)),
            "ask": float(data.get("ask", 1.0)),
        }

    # ================================================================
    #  CLOB API — Données historiques
    # ================================================================

    def get_price_history(
        self,
        token_id: str,
        interval: str = "max",
        fidelity: int = 60,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> pd.DataFrame:
        """
        Récupère l'historique des prix d'un token.

        Args:
            token_id: ID du token (YES ou NO)
            interval: "1h", "6h", "1d", "1w", "1m", "max", "all"
            fidelity: Granularité en minutes (1, 5, 15, 60, etc.)
            start_ts: Timestamp Unix de début
            end_ts: Timestamp Unix de fin

        Returns:
            DataFrame avec colonnes [timestamp, price]
        """
        params = {
            "market": token_id,
            "interval": interval,
            "fidelity": fidelity,
        }
        if start_ts:
            params["startTs"] = start_ts
        if end_ts:
            params["endTs"] = end_ts

        data = self._get(f"{CLOB_API_URL}/prices-history", params)
        history = data.get("history", [])

        if not history:
            return pd.DataFrame(columns=["timestamp", "mid_price"])

        df = pd.DataFrame(history)
        df.columns = ["timestamp", "mid_price"]
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df["mid_price"] = df["mid_price"].astype(float)
        df = df.sort_values("timestamp").reset_index(drop=True)

        return df

    def get_market_history_for_backtest(
        self,
        market: PolymarketMarket,
        fidelity: int = 60,
    ) -> pd.DataFrame:
        """
        Récupère l'historique complet d'un marché formaté pour le backtest.

        Enrichit les données brutes avec des estimations de volume et spread
        basées sur l'orderbook actuel (les données historiques de Polymarket
        ne contiennent que le prix).
        """
        # Prix historiques YES
        df = self.get_price_history(
            token_id=market.yes_token_id,
            interval="max",
            fidelity=fidelity,
        )

        if df.empty:
            return df

        # Enrichir avec les données dérivées
        df["market_id"] = market.condition_id
        df["question"] = market.question
        df["category"] = market.category

        # Estimer le spread à partir de la volatilité locale
        df["returns"] = df["mid_price"].pct_change()
        rolling_vol = df["returns"].rolling(window=24, min_periods=1).std()
        df["spread"] = np.clip(rolling_vol * 2, 0.005, 0.10).fillna(0.02)
        df["bid_price"] = np.clip(df["mid_price"] - df["spread"] / 2, 0.01, 0.99)
        df["ask_price"] = np.clip(df["mid_price"] + df["spread"] / 2, 0.01, 0.99)

        # Estimer le volume (proportionnel à la liquidité du marché
        # et inversement proportionnel au spread)
        base_vol = max(market.volume / max(len(df), 1), 1000)
        noise = np.random.lognormal(0, 0.5, size=len(df))
        spread_factor = 0.02 / np.maximum(df["spread"].values, 0.005)
        df["volume_usd"] = np.maximum(100, base_vol * noise * spread_factor)

        # Nombre de trades estimé
        df["num_trades"] = np.maximum(1, (df["volume_usd"] / 500).astype(int))

        # Open interest estimé
        df["open_interest"] = (df["volume_usd"].cumsum() * 0.1).clip(lower=1000)

        # Outcome : on ne le connaît pas encore (marché actif)
        df["outcome"] = None

        df = df.drop(columns=["returns"], errors="ignore")
        return df


class PolymarketTradingClient:
    """
    Client de trading pour le vrai Polymarket.
    Requiert py-clob-client et une clé privée.
    """

    def __init__(
        self,
        private_key: str,
        signature_type: int = 0,
        funder: str | None = None,
    ):
        try:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType
            from py_clob_client.order_builder.constants import BUY, SELL
        except ImportError:
            raise ImportError(
                "py-clob-client requis pour le trading. "
                "Installer avec: pip install py-clob-client"
            )

        self._ClobClient = ClobClient
        self._OrderArgs = OrderArgs
        self._MarketOrderArgs = MarketOrderArgs
        self._OrderType = OrderType
        self._BUY = BUY
        self._SELL = SELL

        self.client = ClobClient(
            CLOB_API_URL,
            key=private_key,
            chain_id=CHAIN_ID,
            signature_type=signature_type,
            funder=funder or "",
        )

        # Dériver les credentials API
        api_creds = self.client.create_or_derive_api_creds()
        self.client.set_api_creds(api_creds)
        logger.info("Trading client authenticated")

    def place_limit_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str = "BUY",
    ) -> dict:
        """
        Place un ordre limit GTC.

        Args:
            token_id: Token YES ou NO
            price: Prix (0.01 à 0.99)
            size: Nombre de shares
            side: "BUY" ou "SELL"
        """
        order_args = self._OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=self._BUY if side.upper() == "BUY" else self._SELL,
        )
        signed = self.client.create_order(order_args)
        result = self.client.post_order(signed, self._OrderType.GTC)
        logger.info(f"Limit order placed: {side} {size} @ {price} -> {result}")
        return result

    def place_market_order(
        self,
        token_id: str,
        amount_usd: float,
        side: str = "BUY",
    ) -> dict:
        """
        Place un ordre market FOK.

        Args:
            token_id: Token YES ou NO
            amount_usd: Montant en USD
            side: "BUY" ou "SELL"
        """
        market_args = self._MarketOrderArgs(
            token_id=token_id,
            amount=amount_usd,
            side=self._BUY if side.upper() == "BUY" else self._SELL,
        )
        signed = self.client.create_market_order(market_args)
        result = self.client.post_order(signed, self._OrderType.FOK)
        logger.info(f"Market order placed: {side} ${amount_usd} -> {result}")
        return result

    def cancel_order(self, order_id: str) -> dict:
        """Annule un ordre."""
        result = self.client.cancel(order_id)
        logger.info(f"Order cancelled: {order_id}")
        return result

    def cancel_all_orders(self) -> dict:
        """Annule tous les ordres ouverts."""
        result = self.client.cancel_all()
        logger.info("All orders cancelled")
        return result

    def get_open_orders(self) -> list[dict]:
        """Récupère les ordres ouverts."""
        from py_clob_client.clob_types import OpenOrderParams
        return self.client.get_orders(OpenOrderParams())

    def get_trades(self) -> list[dict]:
        """Récupère l'historique des trades."""
        return self.client.get_trades()

    def get_balances(self) -> dict:
        """Récupère les balances."""
        try:
            return self.client.get_balance_allowance()
        except Exception as e:
            logger.warning(f"Could not fetch balances: {e}")
            return {}
