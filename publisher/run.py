"""Publish due queue entries: `python -m publisher.run [--dry-run] [--only ID] [--now ISO]`."""
import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests

from publisher.instagram import TOKEN_ERROR_CODE, InstagramClient, InstagramError
from shared.config import load_settings, require
from shared.post_queue import (MAX_ATTEMPTS, QUEUE_PATH, due_entries, load_queue, mark_failed,
                               mark_published, save_queue)
from shared.timeutil import now_local, parse_time


@dataclass
class RunResult:
    published: list[str] = field(default_factory=list)
    retrying: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def media_urls(entry: dict, base_url: str) -> list[str]:
    return [f"{base_url}/media/{entry['id']}/{name}" for name in entry["media"]]


def _select(queue, now, only) -> list[dict]:
    if only:
        return [entry for entry in queue
                if entry["id"] == only and entry["platforms"].get("instagram", {}).get("status") == "pending"]
    return due_entries(queue, "instagram", now)


def _publish(client, entry, urls) -> str:
    if entry["type"] == "reel":
        return client.publish_reel(urls[0], entry["caption"])
    return client.publish_carousel(urls, entry["caption"])


def _record_failure(entry, message, result, log) -> None:
    gave_up = mark_failed(entry, "instagram", message)
    (result.failed if gave_up else result.retrying).append(message)
    log(f"{'FAILED' if gave_up else 'retry next hour'}: {message}")


def publish_due(queue, client, base_url, now, *, only=None, dry_run=False, log=print,
                on_change=lambda: None) -> RunResult:
    """Publish due Instagram entries; an invalid token aborts the run without spending attempts.

    on_change runs after every entry whose state changed, so a job killed mid-run never forgets a post
    that already went out (which would republish it next hour).
    """
    result = RunResult()
    for entry in _select(queue, now, only):
        urls = media_urls(entry, base_url)
        if dry_run:
            log(f"DRY-RUN {entry['scheduled_at']} {entry['type']} {entry['id']} -> {urls}")
            continue
        try:
            published_id = _publish(client, entry, urls)
        except InstagramError as exc:
            if exc.code == TOKEN_ERROR_CODE:
                raise
            _record_failure(entry, f"{entry['id']}: {exc}", result, log)
        except requests.RequestException as exc:
            _record_failure(entry, f"{entry['id']}: network error: {exc}", result, log)
        else:
            mark_published(entry, "instagram", published_id)
            result.published.append(entry["id"])
            log(f"published {entry['id']} -> {published_id}")
        on_change()
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Publish due queue entries to Instagram")
    parser.add_argument("--dry-run", action="store_true", help="list what would be published")
    parser.add_argument("--only", metavar="ID", help="publish this pending entry now, ignoring its schedule")
    parser.add_argument("--now", metavar="ISO", help="pretend the current time is this (testing)")
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    args = parser.parse_args(argv)
    settings = load_settings()
    now = parse_time(args.now) if args.now else now_local()
    queue = load_queue(args.queue)
    base_url = require(settings.pages_base_url, "PAGES_BASE_URL")
    client = None if args.dry_run else InstagramClient(require(settings.ig_user_id, "IG_USER_ID"),
                                                       require(settings.ig_access_token, "IG_ACCESS_TOKEN"))
    try:
        result = publish_due(queue, client, base_url, now, only=args.only, dry_run=args.dry_run,
                             on_change=lambda: save_queue(args.queue, queue))
    except InstagramError as exc:
        save_queue(args.queue, queue)
        print(f"ERROR: Instagram token invalid or expired ({exc}). "
              "Generate a new one: docs/setup/accounts.md, section 5.", file=sys.stderr)
        return 1
    if not args.dry_run:
        save_queue(args.queue, queue)
    for message in result.failed:
        print(f"ERROR: gave up after {MAX_ATTEMPTS} attempts: {message}", file=sys.stderr)
    return 1 if result.failed else 0


if __name__ == "__main__":
    sys.exit(main())
