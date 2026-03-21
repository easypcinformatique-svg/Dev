"""
Client Polymarket unifie avec mode DRY_RUN et retry automatique.

Wrappe le client existant (backtest/polymarket_client.py) et ajoute :
- Mode DRY_RUN : simule les ordres sans les envoyer, mais logue tout
- Retry automatique (3 tentatives, backoff exponentiel) sur erreurs reseau
- Configuration via variables d'environnement (.env)

Variables d'environnement :
    PRIVATE_KEY          - Cle privee Ethereum (Polygon)
    POLYMARKET_API_KEY   - Cle API Polymarket
    POLYMARKET_API_SECRET - Secret API
    POLYMARKET_API_PASSPHRASE - Passphrase API
    DRY_RUN              - "true" pour simuler (defaut: true)
"""

import os
import time
import logging
from datetime import datetime
from typing import Optional

from backtest.polymarket_client import (
    PolymarketClient as BaseReadClient,
    PolymarketTradingClient as BaseTradingClient,
    PolymarketMarket,
)

logger = logging.getLogger("polymarket_client")

MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # secondes


def _with_retry(func, *args, **kwargs):
    """Execute une fonction avec retry et backoff exponentiel."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                logger.warning(f"Tentative {attempt + 1}/{MAX_RETRIES} echouee: {e}. "
                               f"Retry dans {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"Echec apres {MAX_RETRIES} tentatives: {e}")
    raise last_error


class PolymarketClient:
    """
    Client Polymarket avec mode DRY_RUN integre.

    En mode DRY_RUN, les appels de lecture (marches, prix) sont reels,
    mais les ordres sont simules et logues sans etre envoyes.
    """

    def __init__(self, private_key: str = "", dry_run: bool = True):
        self.dry_run = dry_run

        # Client read-only (toujours actif)
        self.read_client = BaseReadClient(rate_limit_delay=0.3)

        # Client trading (seulement en mode live)
        self.trading_client: Optional[BaseTradingClient] = None
        if not dry_run and private_key:
            try:
                self.trading_client = BaseTradingClient(private_key)
                logger.info("Polymarket LIVE trading client initialise")
            except Exception as e:
                logger.error(f"Impossible d'initialiser le trading client: {e}")
                logger.warning("Passage en mode DRY_RUN")
                self.dry_run = True
        elif dry_run:
            logger.info("Polymarket client en mode DRY_RUN")

        # Compteur d'ordres DRY
        self._dry_order_counter = 0

    # ------------------------------------------------------------------
    #  LECTURE (toujours reel)
    # ------------------------------------------------------------------

    def get_markets(self, limit: int = 100, **kwargs) -> list[PolymarketMarket]:
        """Recupere les marches actifs."""
        return _with_retry(
            self.read_client.get_all_active_markets,
            max_markets=limit,
            **kwargs,
        )

    def get_market_price(self, token_id: str) -> dict:
        """Prix bid/ask en temps reel."""
        return _with_retry(self.read_client.get_price, token_id)

    def get_midpoint(self, token_id: str) -> float:
        """Prix midpoint d'un token."""
        return _with_retry(self.read_client.get_midpoint, token_id)

    def get_spread(self, token_id: str) -> dict:
        """Spread bid/ask d'un token."""
        return _with_retry(self.read_client.get_spread, token_id)

    def get_orderbook(self, token_id: str):
        """Orderbook complet."""
        return _with_retry(self.read_client.get_orderbook, token_id)

    def get_position(self, market_id: str) -> dict:
        """Recupere la position actuelle sur un marche."""
        if self.trading_client:
            try:
                trades = _with_retry(self.trading_client.get_trades)
                market_trades = [t for t in trades if t.get("market", "") == market_id]
                return {"trades": market_trades}
            except Exception as e:
                logger.warning(f"get_position echoue: {e}")
        return {"trades": []}

    # ------------------------------------------------------------------
    #  TRADING (DRY_RUN ou LIVE)
    # ------------------------------------------------------------------

    def place_order(
        self,
        token_id: str,
        side: str,
        size_usd: float,
        price: float,
    ) -> dict:
        """
        Place un ordre (limit ou market selon le contexte).

        En mode DRY_RUN, simule l'ordre et retourne un resultat fictif.
        """
        if self.dry_run:
            return self._dry_place_order(token_id, side, size_usd, price)

        # Mode LIVE — placement reel
        shares = size_usd / max(price, 0.01)
        result = _with_retry(
            self.trading_client.place_limit_order,
            token_id=token_id,
            price=round(price, 2),
            size=round(shares, 2),
            side=side,
        )
        logger.info(f"[LIVE] Ordre place: {side} {shares:.2f} shares @ {price:.3f}")
        return result

    def close_position(
        self,
        token_id: str,
        shares: float,
    ) -> dict:
        """Ferme une position (vend toutes les shares)."""
        if self.dry_run:
            return self._dry_close_position(token_id, shares)

        result = _with_retry(
            self.trading_client.place_market_order,
            token_id=token_id,
            amount_usd=shares,  # FOK market order
            side="SELL",
        )
        logger.info(f"[LIVE] Position fermee: SELL {shares:.2f} shares")
        return result

    # ------------------------------------------------------------------
    #  DRY RUN
    # ------------------------------------------------------------------

    def _dry_place_order(self, token_id: str, side: str, size_usd: float,
                         price: float) -> dict:
        self._dry_order_counter += 1
        order_id = f"DRY-{self._dry_order_counter:06d}"
        result = {
            "orderID": order_id,
            "status": "MATCHED",
            "side": side,
            "price": price,
            "size_usd": size_usd,
            "token_id": token_id,
            "timestamp": datetime.now().isoformat(),
            "dry_run": True,
        }
        logger.info(f"[DRY] Ordre simule: {order_id} | {side} ${size_usd:.2f} @ {price:.3f}")
        return result

    def _dry_close_position(self, token_id: str, shares: float) -> dict:
        self._dry_order_counter += 1
        order_id = f"DRY-{self._dry_order_counter:06d}"
        result = {
            "orderID": order_id,
            "status": "MATCHED",
            "side": "SELL",
            "shares": shares,
            "token_id": token_id,
            "timestamp": datetime.now().isoformat(),
            "dry_run": True,
        }
        logger.info(f"[DRY] Fermeture simulee: {order_id} | SELL {shares:.2f} shares")
        return result
