"""On-chain listener — detects large deposits to exchange hot wallets on Solana."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

import aiohttp

from src.config import AppConfig
from src.models import Exchange, Signal, SignalSource

logger = logging.getLogger(__name__)


class OnchainListener:
    """Monitors Solana exchange hot wallets for unusual token deposits."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        hot_wallets_cfg = config.get("signals", "onchain", "hot_wallets", default={})
        self._hot_wallets: dict[str, Exchange] = {}
        for exchange_name, addresses in hot_wallets_cfg.items():
            ex = Exchange(exchange_name.upper())
            for addr in addresses:
                self._hot_wallets[addr] = ex

        self._rpc_url = config.solana.rpc_primary
        self._seen_sigs: set[str] = set()
        self._known_tokens: set[str] = set()
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False

    async def start(self) -> None:
        if not self._hot_wallets:
            logger.warning("OnchainListener disabled — no hot wallets configured")
            return
        if not self._rpc_url:
            logger.warning("OnchainListener disabled — no RPC URL")
            return
        self._session = aiohttp.ClientSession()
        self._running = True
        logger.info(
            "OnchainListener started — monitoring %d wallets", len(self._hot_wallets)
        )

    async def stop(self) -> None:
        self._running = False
        if self._session:
            await self._session.close()

    async def listen(self) -> AsyncIterator[Signal]:
        """Poll exchange hot wallets for new token deposits."""
        if not self._running:
            return

        while self._running:
            try:
                for wallet_addr, exchange in self._hot_wallets.items():
                    signals = await self._check_wallet(wallet_addr, exchange)
                    for sig in signals:
                        yield sig
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("OnchainListener error")
            await asyncio.sleep(10)  # 10s polling interval for on-chain

    async def _check_wallet(
        self, wallet: str, exchange: Exchange
    ) -> list[Signal]:
        """Check recent token transfers to an exchange wallet."""
        assert self._session
        signals: list[Signal] = []

        try:
            # Use Helius enhanced transactions API
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [wallet, {"limit": 20}],
            }
            async with self._session.post(
                self._rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return signals
                data = await resp.json()
                sigs = data.get("result", [])

                for sig_info in sigs:
                    sig = sig_info.get("signature", "")
                    if sig in self._seen_sigs:
                        continue
                    self._seen_sigs.add(sig)

                    # Get transaction details
                    token_info = await self._parse_transaction(sig)
                    if token_info:
                        mint, amount = token_info
                        if mint not in self._known_tokens:
                            self._known_tokens.add(mint)
                            signals.append(
                                Signal(
                                    token_symbol=mint[:8],  # Placeholder until resolved
                                    exchange=exchange,
                                    source=SignalSource.ONCHAIN,
                                    confidence=0.50,
                                    raw_text=f"Large deposit of {mint} to {exchange.value} wallet. Amount: {amount}",
                                    contract_address=mint,
                                    chain="solana",
                                )
                            )
                            logger.info(
                                "On-chain deposit detected: %s -> %s (%s)",
                                mint[:12],
                                exchange.value,
                                wallet[:8],
                            )
        except Exception:
            logger.debug("Failed to check wallet %s", wallet[:8])

        # Limit seen set size
        if len(self._seen_sigs) > 5000:
            self._seen_sigs = set(list(self._seen_sigs)[-2000:])

        return signals

    async def _parse_transaction(
        self, signature: str
    ) -> Optional[tuple[str, float]]:
        """Parse a transaction to extract SPL token transfer details."""
        assert self._session
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    signature,
                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
                ],
            }
            async with self._session.post(
                self._rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                tx = data.get("result")
                if not tx:
                    return None

                # Look for token transfers in inner instructions
                meta = tx.get("meta", {})
                pre_balances = meta.get("preTokenBalances", [])
                post_balances = meta.get("postTokenBalances", [])

                # Find tokens that increased in the wallet
                for post in post_balances:
                    mint = post.get("mint", "")
                    amount_str = (
                        post.get("uiTokenAmount", {}).get("uiAmountString", "0")
                    )
                    try:
                        amount = float(amount_str)
                    except (ValueError, TypeError):
                        continue

                    if amount > 0:
                        # Check if this is a significant deposit
                        pre_amount = 0.0
                        for pre in pre_balances:
                            if pre.get("mint") == mint:
                                try:
                                    pre_amount = float(
                                        pre.get("uiTokenAmount", {}).get(
                                            "uiAmountString", "0"
                                        )
                                    )
                                except (ValueError, TypeError):
                                    pass
                                break

                        net_deposit = amount - pre_amount
                        if net_deposit > 0:
                            return (mint, net_deposit)
        except Exception:
            pass
        return None
