from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class EventConfig:
    artist: str
    expected_onsale: datetime | None = None
    min_price_eur: float = 0
    max_price_eur: float = 999

    @classmethod
    def from_dict(cls, d: dict) -> EventConfig:
        onsale = d.get("expected_onsale")
        if isinstance(onsale, str):
            onsale = datetime.fromisoformat(onsale)
        return cls(
            artist=d["artist"],
            expected_onsale=onsale,
            min_price_eur=d.get("min_price_eur", 0),
            max_price_eur=d.get("max_price_eur", 999),
        )


@dataclass
class AppConfig:
    tm_api_key: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str
    alert_phone_number: str
    telegram_bot_token: str
    telegram_chat_id: str
    events: list[EventConfig] = field(default_factory=list)
    poll_interval_seconds: int = 30


def load_config(
    env_path: str | Path = ".env",
    events_path: str | Path = "config/events.yaml",
) -> AppConfig:
    load_dotenv(env_path)

    events: list[EventConfig] = []
    events_file = Path(events_path)
    if events_file.exists():
        with open(events_file) as f:
            data = yaml.safe_load(f)
        for item in data.get("events", []):
            events.append(EventConfig.from_dict(item))

    return AppConfig(
        tm_api_key=os.getenv("TM_API_KEY", ""),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        twilio_from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
        alert_phone_number=os.getenv("ALERT_PHONE_NUMBER", ""),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        events=events,
    )
