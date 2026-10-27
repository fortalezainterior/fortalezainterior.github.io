"""Publication queue shared by the local generator and the GitHub Actions publisher."""
from datetime import datetime
from pathlib import Path

from shared.config import PUBLIC_DIR
from shared.jsonio import read_json, write_json
from shared.timeutil import parse_time

QUEUE_PATH = PUBLIC_DIR / "queue.json"  # in the public repo itself the workflows pass --queue queue.json
MAX_ATTEMPTS = 3
TIKTOK_AUTOMATED = False  # flip once the TikTok app passes audit (spec Phase 5)


def load_queue(path: Path = QUEUE_PATH) -> list[dict]:
    return read_json(path) if Path(path).exists() else []


def save_queue(path: Path, queue: list[dict]) -> None:
    write_json(path, queue)


def compose_caption(item: dict) -> str:
    return f"{item['caption'].strip()}\n\n{' '.join(item['hashtags'])}".strip()


def make_entry(item: dict, media: list[str]) -> dict:
    platforms = {}
    for platform in item["platforms"]:
        status = "manual" if platform == "tiktok" and not TIKTOK_AUTOMATED else "pending"
        platforms[platform] = {"status": status, "attempts": 0, "published_id": None, "last_error": None}
    return {"id": item["id"], "type": item["type"], "scheduled_at": item["scheduled_at"],
            "caption": compose_caption(item), "media": list(media), "platforms": platforms}


def add_entries(queue: list[dict], entries: list[dict]) -> list[dict]:
    """Append entries, replacing same-id entries that were never published."""
    by_id = {entry["id"]: entry for entry in queue}
    for entry in entries:
        old = by_id.get(entry["id"])
        if old and any(state["status"] == "published" for state in old["platforms"].values()):
            raise ValueError(f"{entry['id']}: already published, refusing to replace")
        by_id[entry["id"]] = entry
    return sorted(by_id.values(), key=lambda e: parse_time(e["scheduled_at"]))


def due_entries(queue: list[dict], platform: str, now: datetime) -> list[dict]:
    due = [entry for entry in queue
           if entry["platforms"].get(platform, {}).get("status") == "pending"
           and parse_time(entry["scheduled_at"]) <= now]
    return sorted(due, key=lambda e: parse_time(e["scheduled_at"]))


def has_pending(entry: dict) -> bool:
    return any(state["status"] == "pending" for state in entry["platforms"].values())


def mark_published(entry: dict, platform: str, published_id: str) -> None:
    entry["platforms"][platform].update(status="published", published_id=published_id, last_error=None)


def mark_failed(entry: dict, platform: str, error: str) -> bool:
    """Record a failed attempt; returns True when the entry gave up (status 'failed')."""
    state = entry["platforms"][platform]
    state["attempts"] += 1
    state["last_error"] = error[:500]
    state["status"] = "failed" if state["attempts"] >= MAX_ATTEMPTS else "pending"
    return state["status"] == "failed"
