"""Historical data collector for backtesting — gathers past listing announcements and price data."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class HistoricalListing:
    """A historical listing event with price data."""

    token_symbol: str
    token_name: str
    exchange: str
    announcement_time: str     # ISO format
    listing_time: str          # ISO format
    contract_address: str = ""
    chain: str = "solana"
    # Price data
    price_at_announcement: float = 0.0
    price_at_listing: float = 0.0
    price_1h_after: float = 0.0
    price_4h_after: float = 0.0
    price_24h_after: float = 0.0
    price_peak_24h: float = 0.0
    # Volume
    volume_at_listing: float = 0.0
    liquidity_at_listing: float = 0.0
    # Calculated
    gain_1h_pct: float = 0.0
    gain_4h_pct: float = 0.0
    gain_24h_pct: float = 0.0
    peak_gain_pct: float = 0.0


class DataCollector:
    """Collects historical listing data for backtesting."""

    def __init__(self, output_dir: str = "data/historical") -> None:
        self._output = Path(output_dir)
        self._output.mkdir(parents=True, exist_ok=True)
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()

    async def stop(self) -> None:
        if self._session:
            await self._session.close()

    async def collect_binance_listings(
        self, months: int = 6
    ) -> list[HistoricalListing]:
        """Collect Binance listing announcements from the past N months."""
        assert self._session
        listings: list[HistoricalListing] = []

        try:
            # Fetch from Binance CMS API
            for page in range(1, 10):
                payload = {
                    "type": 1,
                    "catalogId": 48,
                    "pageNo": page,
                    "pageSize": 20,
                }
                async with self._session.post(
                    "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    articles = data.get("data", {}).get("articles", [])
                    if not articles:
                        break

                    for article in articles:
                        title = article.get("title", "")
                        release = article.get("releaseDate", 0)
                        if not release:
                            continue

                        release_dt = datetime.fromtimestamp(
                            release / 1000, tz=timezone.utc
                        )
                        cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
                        if release_dt < cutoff:
                            break

                        # Extract ticker
                        import re
                        match = re.search(r"\(([A-Z0-9]{2,10})\)", title)
                        if not match:
                            continue
                        ticker = match.group(1)

                        listing = HistoricalListing(
                            token_symbol=ticker,
                            token_name=title.split("(")[0].strip().split("List")[-1].strip(),
                            exchange="BINANCE",
                            announcement_time=release_dt.isoformat(),
                            listing_time=release_dt.isoformat(),  # Approximate
                        )
                        listings.append(listing)

                await asyncio.sleep(0.5)  # Rate limit
        except Exception:
            logger.exception("Failed to collect Binance listings")

        logger.info("Collected %d Binance listings", len(listings))
        return listings

    async def enrich_with_price_data(
        self, listings: list[HistoricalListing]
    ) -> list[HistoricalListing]:
        """Enrich listings with historical price data from DexScreener/CoinGecko."""
        assert self._session

        for listing in listings:
            try:
                # Get token address from DexScreener
                url = f"https://api.dexscreener.com/latest/dex/search?q={listing.token_symbol}"
                async with self._session.get(
                    url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    pairs = [
                        p for p in data.get("pairs", [])
                        if p.get("chainId") == "solana"
                        and p.get("baseToken", {}).get("symbol", "").upper()
                        == listing.token_symbol.upper()
                    ]
                    if pairs:
                        best = max(
                            pairs,
                            key=lambda p: float(
                                p.get("liquidity", {}).get("usd", 0) or 0
                            ),
                        )
                        listing.contract_address = best.get("baseToken", {}).get(
                            "address", ""
                        )
                        listing.price_at_listing = float(
                            best.get("priceUsd", 0) or 0
                        )
                        listing.liquidity_at_listing = float(
                            best.get("liquidity", {}).get("usd", 0) or 0
                        )
                        listing.volume_at_listing = float(
                            best.get("volume", {}).get("h24", 0) or 0
                        )

                await asyncio.sleep(0.3)
            except Exception:
                logger.debug("Price enrichment failed for %s", listing.token_symbol)

        return listings

    async def save_to_csv(
        self, listings: list[HistoricalListing], filename: str = "listings.csv"
    ) -> str:
        """Save collected listings to CSV."""
        path = self._output / filename
        if not listings:
            return str(path)

        fieldnames = list(asdict(listings[0]).keys())
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for listing in listings:
                writer.writerow(asdict(listing))

        logger.info("Saved %d listings to %s", len(listings), path)
        return str(path)

    async def save_to_json(
        self, listings: list[HistoricalListing], filename: str = "listings.json"
    ) -> str:
        """Save collected listings to JSON."""
        path = self._output / filename
        with open(path, "w") as f:
            json.dump([asdict(l) for l in listings], f, indent=2)
        logger.info("Saved %d listings to %s", len(listings), path)
        return str(path)

    async def load_from_json(self, filename: str = "listings.json") -> list[HistoricalListing]:
        """Load listings from JSON."""
        path = self._output / filename
        if not path.exists():
            return []
        with open(path) as f:
            data = json.load(f)
        return [HistoricalListing(**d) for d in data]
