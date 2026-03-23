"""MEV protection — Jito bundle submission to prevent sandwich attacks."""

from __future__ import annotations

import base64
import logging
from typing import Optional

import aiohttp

from src.config import AppConfig

logger = logging.getLogger(__name__)

# Jito block engine endpoints
_JITO_ENDPOINTS = [
    "https://frankfurt.mainnet.block-engine.jito.wtf",
    "https://amsterdam.mainnet.block-engine.jito.wtf",
    "https://ny.mainnet.block-engine.jito.wtf",
    "https://tokyo.mainnet.block-engine.jito.wtf",
]

# Standard tip accounts (Jito validators)
_TIP_ACCOUNTS = [
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "HFqU5x63VTqvQss8hp11i4bVqkfRtQ7NmXwkiYN6Y2Kc",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "ADaUMid9yfUytqMBgopwjb2DTLSdxQHLRAdtPzY1FKso",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
]


class MevProtection:
    """Protects trades from MEV (sandwich attacks) using Jito bundles."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._use_jito = config.get("execution", "use_jito", default=True)
        self._tip_lamports = config.jito.tip_lamports
        self._block_engine = config.jito.block_engine_url or _JITO_ENDPOINTS[0]
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        logger.info("MevProtection started (jito=%s)", self._use_jito)

    async def stop(self) -> None:
        if self._session:
            await self._session.close()

    @property
    def enabled(self) -> bool:
        return self._use_jito

    def get_tip_account(self) -> str:
        """Get a random Jito tip account for the tip transaction."""
        import random
        custom = self._config.jito.tip_account
        if custom:
            return custom
        return random.choice(_TIP_ACCOUNTS)

    def create_tip_instruction(self, payer_pubkey: str) -> dict:
        """
        Create a tip transfer instruction for Jito.

        Returns instruction data that should be appended to the transaction.
        """
        return {
            "programId": "11111111111111111111111111111111",  # System program
            "keys": [
                {"pubkey": payer_pubkey, "isSigner": True, "isWritable": True},
                {"pubkey": self.get_tip_account(), "isSigner": False, "isWritable": True},
            ],
            "data": self._tip_lamports.to_bytes(8, "little").hex(),
        }

    async def send_bundle(self, signed_transactions: list[str]) -> Optional[str]:
        """
        Send a bundle of transactions via Jito block engine.

        Args:
            signed_transactions: List of base64-encoded signed transactions.

        Returns:
            Bundle ID if successful, None otherwise.
        """
        if not self._use_jito or not self._session:
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendBundle",
            "params": [signed_transactions],
        }

        # Try multiple Jito endpoints
        endpoints = [self._block_engine] + [
            e for e in _JITO_ENDPOINTS if e != self._block_engine
        ]

        for endpoint in endpoints[:3]:
            try:
                url = f"{endpoint}/api/v1/bundles"
                async with self._session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        bundle_id = data.get("result")
                        if bundle_id:
                            logger.info("Jito bundle sent: %s", bundle_id)
                            return bundle_id
                    else:
                        body = await resp.text()
                        logger.debug(
                            "Jito endpoint %s failed (%d): %s",
                            endpoint[:30],
                            resp.status,
                            body[:100],
                        )
            except Exception:
                logger.debug("Jito endpoint %s unreachable", endpoint[:30])

        logger.warning("Failed to send Jito bundle to any endpoint")
        return None

    async def check_bundle_status(self, bundle_id: str) -> Optional[str]:
        """Check the status of a submitted bundle."""
        assert self._session
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBundleStatuses",
                "params": [[bundle_id]],
            }
            url = f"{self._block_engine}/api/v1/bundles"
            async with self._session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    statuses = data.get("result", {}).get("value", [])
                    if statuses:
                        return statuses[0].get("confirmation_status")
        except Exception:
            logger.debug("Bundle status check failed for %s", bundle_id)
        return None
