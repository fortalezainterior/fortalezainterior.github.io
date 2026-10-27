"""Timezone-aware time helpers; every timestamp in the project carries a UTC offset."""
from datetime import datetime
from zoneinfo import ZoneInfo

from shared.config import TIMEZONE


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp without UTC offset: {value}")
    return parsed


def now_local() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))
