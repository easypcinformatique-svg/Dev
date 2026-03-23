"""Configuration loader — merges settings.yaml with environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _PROJECT_ROOT / "config"


def _load_yaml() -> dict[str, Any]:
    path = _CONFIG_DIR / "settings.yaml"
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


@dataclass(frozen=True)
class SolanaConfig:
    private_key: str = ""
    rpc_primary: str = ""
    rpc_secondary: str = ""
    rpc_tertiary: str = ""


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str = ""
    chat_id: str = ""


@dataclass(frozen=True)
class DatabaseConfig:
    url: str = "postgresql+asyncpg://sniper:sniper@localhost:5432/listing_sniper"
    pool_size: int = 10
    max_overflow: int = 20


@dataclass(frozen=True)
class RedisConfig:
    url: str = "redis://localhost:6379/0"


@dataclass(frozen=True)
class JitoConfig:
    tip_account: str = ""
    block_engine_url: str = "https://frankfurt.mainnet.block-engine.jito.wtf"
    tip_lamports: int = 10000


@dataclass
class AppConfig:
    """Top-level application configuration."""

    mode: str = "dry_run"
    yaml_data: dict[str, Any] = field(default_factory=dict)
    solana: SolanaConfig = field(default_factory=SolanaConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    jito: JitoConfig = field(default_factory=JitoConfig)
    log_level: str = "INFO"

    # Derived convenience
    dry_run: bool = True

    @classmethod
    def load(cls) -> AppConfig:
        load_dotenv(_CONFIG_DIR / ".env", override=False)
        load_dotenv(_CONFIG_DIR / ".env.example", override=False)
        y = _load_yaml()

        mode = os.getenv("MODE", y.get("mode", "dry_run"))
        dry_run = mode != "live"

        solana = SolanaConfig(
            private_key=os.getenv("SOLANA_PRIVATE_KEY", ""),
            rpc_primary=os.getenv("SOLANA_RPC_PRIMARY", ""),
            rpc_secondary=os.getenv("SOLANA_RPC_SECONDARY", ""),
            rpc_tertiary=os.getenv("SOLANA_RPC_TERTIARY", ""),
        )
        telegram = TelegramConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        )
        db_y = y.get("database", {})
        database = DatabaseConfig(
            url=os.getenv("DATABASE_URL", "postgresql+asyncpg://sniper:sniper@localhost:5432/listing_sniper"),
            pool_size=db_y.get("pool_size", 10),
            max_overflow=db_y.get("max_overflow", 20),
        )
        redis = RedisConfig(url=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        jito = JitoConfig(
            tip_account=os.getenv("JITO_TIP_ACCOUNT", ""),
            block_engine_url=os.getenv(
                "JITO_BLOCK_ENGINE_URL",
                "https://frankfurt.mainnet.block-engine.jito.wtf",
            ),
            tip_lamports=int(
                y.get("execution", {}).get("jito_tip_lamports", 10000)
            ),
        )

        return cls(
            mode=mode,
            yaml_data=y,
            solana=solana,
            telegram=telegram,
            database=database,
            redis=redis,
            jito=jito,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            dry_run=dry_run,
        )

    def get(self, *keys: str, default: Any = None) -> Any:
        """Dot-path accessor into yaml_data, e.g. config.get('signals','binance','poll_interval_sec')."""
        d: Any = self.yaml_data
        for k in keys:
            if isinstance(d, dict):
                d = d.get(k)
            else:
                return default
            if d is None:
                return default
        return d
