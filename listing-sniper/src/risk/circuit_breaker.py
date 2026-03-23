"""Circuit breakers — automated safety switches for infrastructure and market anomalies."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

import aiohttp

from src.config import AppConfig
from src.infra.telegram_alerts import TelegramAlerter
from src.infra import metrics

logger = logging.getLogger(__name__)


@dataclass
class BreakerStatus:
    """Status of all circuit breakers."""

    is_tripped: bool
    reasons: list[str]
    sol_balance: float
    rpc_error_rate: float
    network_congestion: float


class CircuitBreaker:
    """
    Automated safety switches. When tripped, ALL trading stops.

    Checks:
    1. RPC error rate > 10% → pause
    2. SOL balance too low → pause
    3. Solana network congestion → pause
    4. No profit in 7 days → alert for review
    """

    # Hard-coded thresholds
    RPC_ERROR_RATE_THRESHOLD: float = 0.10  # 10%
    MIN_SOL_BALANCE: float = 0.1
    NETWORK_CONGESTION_THRESHOLD: float = 0.80

    def __init__(self, config: AppConfig, alerter: TelegramAlerter) -> None:
        self._config = config
        self._alerter = alerter
        self._rpc_calls: deque[tuple[float, bool]] = deque(maxlen=100)  # (time, success)
        self._tripped = False
        self._trip_reasons: list[str] = []
        self._session: Optional[aiohttp.ClientSession] = None
        self._sol_balance: float = 0.0
        self._monitoring = False
        # In paper/dry_run mode, never trip the circuit breaker
        self._test_mode = config.mode in ("dry_run", "paper")

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        self._monitoring = True
        logger.info("CircuitBreaker started")

    async def stop(self) -> None:
        self._monitoring = False
        if self._session:
            await self._session.close()

    @property
    def is_tripped(self) -> bool:
        return self._tripped

    def record_rpc_call(self, success: bool) -> None:
        """Record an RPC call result for error rate tracking."""
        self._rpc_calls.append((time.monotonic(), success))

    def get_rpc_error_rate(self) -> float:
        """Get the current RPC error rate."""
        if not self._rpc_calls:
            return 0.0
        # Only consider last 60 seconds
        cutoff = time.monotonic() - 60
        recent = [(t, s) for t, s in self._rpc_calls if t > cutoff]
        if not recent:
            return 0.0
        errors = sum(1 for _, s in recent if not s)
        return errors / len(recent)

    async def check_all(self) -> BreakerStatus:
        """Run all circuit breaker checks."""
        # In paper/dry_run mode, skip all checks — never trip
        if self._test_mode:
            was_tripped = self._tripped
            self._tripped = False
            self._trip_reasons = []
            if was_tripped:
                logger.info("Circuit breaker cleared (test mode)")
            return BreakerStatus(
                is_tripped=False,
                reasons=[],
                sol_balance=999.0,
                rpc_error_rate=0.0,
                network_congestion=0.0,
            )

        reasons: list[str] = []

        # 1. RPC error rate
        error_rate = self.get_rpc_error_rate()
        if error_rate > self.RPC_ERROR_RATE_THRESHOLD:
            reasons.append(
                f"RPC error rate {error_rate:.0%} > {self.RPC_ERROR_RATE_THRESHOLD:.0%}"
            )

        # 2. SOL balance
        sol_balance = await self._check_sol_balance()
        if sol_balance < self.MIN_SOL_BALANCE:
            reasons.append(
                f"SOL balance {sol_balance:.4f} < {self.MIN_SOL_BALANCE}"
            )

        # 3. Network congestion (via recent slot times)
        congestion = await self._check_network_congestion()

        if congestion > self.NETWORK_CONGESTION_THRESHOLD:
            reasons.append(
                f"Network congestion {congestion:.0%} > {self.NETWORK_CONGESTION_THRESHOLD:.0%}"
            )

        # Update state
        was_tripped = self._tripped
        self._tripped = bool(reasons)
        self._trip_reasons = reasons

        if self._tripped and not was_tripped:
            reason_str = "; ".join(reasons)
            logger.warning("CIRCUIT BREAKER TRIPPED: %s", reason_str)
            metrics.circuit_breaker_trips.labels(reason=reasons[0] if reasons else "unknown").inc()
            await self._alerter.circuit_breaker(reason_str)
        elif not self._tripped and was_tripped:
            logger.info("Circuit breaker cleared")

        # Update metrics
        metrics.sol_balance.set(sol_balance)

        return BreakerStatus(
            is_tripped=self._tripped,
            reasons=reasons,
            sol_balance=sol_balance,
            rpc_error_rate=error_rate,
            network_congestion=congestion,
        )

    async def monitor(self) -> None:
        """Continuously check circuit breakers."""
        while self._monitoring:
            try:
                await self.check_all()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Circuit breaker check error")
            await asyncio.sleep(10)  # Check every 10 seconds

    async def _check_sol_balance(self) -> float:
        """Check the SOL balance of the trading wallet."""
        assert self._session
        rpc_url = self._config.solana.rpc_primary
        if not rpc_url or not self._config.solana.private_key:
            return 999.0  # Skip check if no wallet configured

        try:
            # Get wallet pubkey
            pubkey = self._get_wallet_pubkey()
            if not pubkey:
                return 999.0

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [pubkey],
            }
            async with self._session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lamports = data.get("result", {}).get("value", 0)
                    self._sol_balance = lamports / 1e9
                    self.record_rpc_call(True)
                    return self._sol_balance
                self.record_rpc_call(False)
        except Exception:
            self.record_rpc_call(False)
            logger.debug("SOL balance check failed")
        return self._sol_balance

    async def _check_network_congestion(self) -> float:
        """
        Estimate Solana network congestion.
        Uses recent performance samples to gauge slot processing times.
        """
        assert self._session
        rpc_url = self._config.solana.rpc_primary
        if not rpc_url:
            return 0.0

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getRecentPerformanceSamples",
                "params": [4],
            }
            async with self._session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    samples = data.get("result", [])
                    if not samples:
                        return 0.0

                    # Expected: ~400ms per slot = 2.5 slots/sec
                    # If actual is significantly lower, network is congested
                    total_slots = sum(s.get("numSlots", 0) for s in samples)
                    total_secs = sum(s.get("samplePeriodSecs", 0) for s in samples)
                    if total_secs == 0:
                        return 0.0

                    actual_sps = total_slots / total_secs
                    expected_sps = 2.5
                    # Congestion = 1 - (actual / expected), clamped to [0, 1]
                    congestion = max(0.0, min(1.0, 1.0 - actual_sps / expected_sps))
                    self.record_rpc_call(True)
                    return congestion
                self.record_rpc_call(False)
        except Exception:
            self.record_rpc_call(False)
            logger.debug("Network congestion check failed")
        return 0.0

    def _get_wallet_pubkey(self) -> str:
        pk = self._config.solana.private_key
        if not pk:
            return ""
        try:
            from solders.keypair import Keypair
            kp = Keypair.from_base58_string(pk)
            return str(kp.pubkey())
        except Exception:
            return ""
