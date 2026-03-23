"""Jupiter V6 swap executor — builds and sends Solana transactions via Jupiter aggregator."""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Optional

import aiohttp

from src.config import AppConfig
from src.models import TradeOrder, TradeSide, TradeStatus

logger = logging.getLogger(__name__)

# SOL mint address
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Jupiter V6 API
_JUPITER_QUOTE = "https://quote-api.jup.ag/v6/quote"
_JUPITER_SWAP = "https://quote-api.jup.ag/v6/swap"


class JupiterExecutor:
    """Executes swaps via Jupiter V6 aggregator on Solana."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._dry_run = config.dry_run
        self._priority_fee = config.get("execution", "priority_fee_lamports", default=100000)
        self._compute_units = config.get("execution", "compute_units", default=400000)
        self._confirmation = config.get("execution", "confirmation_level", default="confirmed")
        self._session: Optional[aiohttp.ClientSession] = None

        # RPC endpoints for multi-send
        self._rpc_urls: list[str] = []
        if config.solana.rpc_primary:
            self._rpc_urls.append(config.solana.rpc_primary)
        if config.solana.rpc_secondary:
            self._rpc_urls.append(config.solana.rpc_secondary)
        if config.solana.rpc_tertiary:
            self._rpc_urls.append(config.solana.rpc_tertiary)

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        logger.info(
            "JupiterExecutor started (dry_run=%s, rpcs=%d)",
            self._dry_run,
            len(self._rpc_urls),
        )

    async def stop(self) -> None:
        if self._session:
            await self._session.close()

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount_lamports: int,
        slippage_bps: int = 200,
    ) -> Optional[dict]:
        """Get a swap quote from Jupiter V6."""
        assert self._session
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount_lamports),
                "slippageBps": str(slippage_bps),
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "false",
            }
            async with self._session.get(
                _JUPITER_QUOTE,
                params=params,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    quote = await resp.json()
                    logger.info(
                        "Jupiter quote: %s -> %s, in=%s out=%s, price_impact=%s",
                        input_mint[:8],
                        output_mint[:8],
                        quote.get("inAmount"),
                        quote.get("outAmount"),
                        quote.get("priceImpactPct"),
                    )
                    return quote
                else:
                    body = await resp.text()
                    logger.warning("Jupiter quote failed (%d): %s", resp.status, body[:200])
                    return None
        except Exception:
            logger.exception("Jupiter quote error")
            return None

    async def execute_swap(self, order: TradeOrder) -> TradeOrder:
        """
        Execute a swap order via Jupiter.

        For BUY: SOL -> Token
        For SELL: Token -> SOL
        """
        assert self._session
        start = time.monotonic()

        if self._dry_run:
            return self._simulate_swap(order)

        # Step 1: Get quote
        if order.side == TradeSide.BUY:
            input_mint = SOL_MINT
            output_mint = order.token_address
            amount_lamports = int(order.amount_sol * 1e9)
        else:
            input_mint = order.token_address
            output_mint = SOL_MINT
            amount_lamports = int(order.amount_tokens * (10 ** 9))  # Assuming 9 decimals

        quote = await self.get_quote(
            input_mint, output_mint, amount_lamports, order.slippage_bps
        )
        if not quote:
            order.status = TradeStatus.FAILED
            order.error = "Failed to get Jupiter quote"
            return order

        # Check price impact
        price_impact = float(quote.get("priceImpactPct", "0") or "0")
        if abs(price_impact) > 5.0:
            order.status = TradeStatus.FAILED
            order.error = f"Price impact too high: {price_impact:.2f}%"
            return order

        # Step 2: Get swap transaction
        try:
            swap_body = {
                "quoteResponse": quote,
                "userPublicKey": self._get_wallet_pubkey(),
                "wrapAndUnwrapSol": True,
                "computeUnitPriceMicroLamports": self._priority_fee,
                "dynamicComputeUnitLimit": True,
            }
            async with self._session.post(
                _JUPITER_SWAP,
                json=swap_body,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    order.status = TradeStatus.FAILED
                    order.error = f"Jupiter swap API failed ({resp.status}): {body[:200]}"
                    return order
                swap_data = await resp.json()
        except Exception as e:
            order.status = TradeStatus.FAILED
            order.error = f"Swap transaction build failed: {e}"
            return order

        # Step 3: Sign and send transaction
        tx_base64 = swap_data.get("swapTransaction")
        if not tx_base64:
            order.status = TradeStatus.FAILED
            order.error = "No swap transaction returned"
            return order

        # Sign the transaction
        signed_tx = self._sign_transaction(tx_base64)
        if not signed_tx:
            order.status = TradeStatus.FAILED
            order.error = "Transaction signing failed"
            return order

        # Send to multiple RPCs in parallel
        tx_sig = await self._send_to_rpcs(signed_tx)
        if not tx_sig:
            order.status = TradeStatus.FAILED
            order.error = "Transaction send failed on all RPCs"
            return order

        # Step 4: Confirm transaction
        confirmed = await self._confirm_transaction(tx_sig)

        elapsed = time.monotonic() - start
        if confirmed:
            order.status = TradeStatus.OPEN
            order.tx_signature = tx_sig
            order.amount_tokens = float(quote.get("outAmount", 0)) / 1e9
            logger.info(
                "Swap executed in %.2fs: %s %s, tx=%s",
                elapsed,
                order.side.value,
                order.token_symbol,
                tx_sig[:20],
            )
        else:
            order.status = TradeStatus.FAILED
            order.error = f"Transaction not confirmed: {tx_sig}"
            order.tx_signature = tx_sig

        return order

    def _simulate_swap(self, order: TradeOrder) -> TradeOrder:
        """Simulate a swap in dry-run mode."""
        import random
        slippage = random.uniform(0.001, order.slippage_bps / 10000)
        order.status = TradeStatus.OPEN
        order.tx_signature = f"DRY_RUN_{order.id}"
        order.fees_sol = 0.000005  # ~5000 lamports
        order.fees_usd = order.fees_sol * 150  # Approximate SOL price

        if order.side == TradeSide.BUY:
            # Simulate receiving tokens
            effective_price = order.price_usd * (1 + slippage)
            order.amount_tokens = order.amount_usd / effective_price if effective_price > 0 else 0
        else:
            effective_price = order.price_usd * (1 - slippage)
            order.amount_sol = order.amount_tokens * effective_price / 150

        logger.info(
            "[DRY RUN] %s %s: $%.2f, tokens=%.2f, slippage=%.2f%%",
            order.side.value,
            order.token_symbol,
            order.amount_usd,
            order.amount_tokens,
            slippage * 100,
        )
        return order

    def _get_wallet_pubkey(self) -> str:
        """Get the wallet public key from the private key."""
        pk = self._config.solana.private_key
        if not pk:
            return ""
        try:
            from solders.keypair import Keypair
            kp = Keypair.from_base58_string(pk)
            return str(kp.pubkey())
        except Exception:
            logger.error("Failed to derive pubkey from private key")
            return ""

    def _sign_transaction(self, tx_base64: str) -> Optional[str]:
        """Sign a versioned transaction with our keypair."""
        pk = self._config.solana.private_key
        if not pk:
            return None
        try:
            from solders.keypair import Keypair
            from solders.transaction import VersionedTransaction

            kp = Keypair.from_base58_string(pk)
            tx_bytes = base64.b64decode(tx_base64)
            tx = VersionedTransaction.from_bytes(tx_bytes)
            tx.sign([kp])
            return base64.b64encode(bytes(tx)).decode("utf-8")
        except ImportError:
            logger.error("solders not installed — cannot sign transactions")
            return None
        except Exception:
            logger.exception("Transaction signing failed")
            return None

    async def _send_to_rpcs(self, signed_tx_b64: str) -> Optional[str]:
        """Send signed transaction to multiple RPCs in parallel."""
        assert self._session

        async def _send_one(rpc_url: str) -> Optional[str]:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        signed_tx_b64,
                        {"encoding": "base64", "skipPreflight": True},
                    ],
                }
                async with self._session.post(  # type: ignore[union-attr]
                    rpc_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "result" in data:
                            return data["result"]
                        logger.warning("RPC error: %s", data.get("error"))
            except Exception:
                logger.debug("RPC send failed: %s", rpc_url[:40])
            return None

        if not self._rpc_urls:
            logger.error("No RPC URLs configured")
            return None

        results = await asyncio.gather(
            *[_send_one(url) for url in self._rpc_urls],
            return_exceptions=True,
        )

        for r in results:
            if isinstance(r, str):
                return r
        return None

    async def _confirm_transaction(self, signature: str, timeout_sec: int = 30) -> bool:
        """Wait for transaction confirmation."""
        assert self._session
        rpc_url = self._rpc_urls[0] if self._rpc_urls else ""
        if not rpc_url:
            return False

        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignatureStatuses",
                    "params": [[signature], {"searchTransactionHistory": True}],
                }
                async with self._session.post(
                    rpc_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        statuses = data.get("result", {}).get("value", [])
                        if statuses and statuses[0]:
                            status = statuses[0]
                            if status.get("err"):
                                logger.error("Transaction failed: %s", status["err"])
                                return False
                            conf = status.get("confirmationStatus")
                            if conf in ("confirmed", "finalized"):
                                return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False
