"""Sleep until the next pending Instagram post: `python -m publisher.wait`.

GitHub's hourly cron runs hours late or not at all, so each publish job waits for the next post itself and
then dispatches the next job (see .github/workflows/publish.yml). Writes `has_pending` and `wait` to
$GITHUB_OUTPUT when set.
"""
import argparse
import os
import sys
import time
from pathlib import Path

from shared.post_queue import QUEUE_PATH, load_queue
from shared.timeutil import now_local, parse_time

MAX_WAIT = 5 * 3600  # GitHub kills a job after 6 h; leave room for setup and publishing
RETRY_WAIT = 30 * 60  # a post still pending after its attempt is retried later, never in a tight loop


def next_wait(queue: list[dict], now) -> int | None:
    """Seconds to sleep before the next Instagram post is due, or None when nothing is pending."""
    pending = [parse_time(entry["scheduled_at"]) for entry in queue
               if entry["platforms"].get("instagram", {}).get("status") == "pending"]
    if not pending:
        return None
    seconds = (min(pending) - now).total_seconds()
    return RETRY_WAIT if seconds <= 0 else min(int(seconds) + 1, MAX_WAIT)


def write_github_output(path: Path, **values) -> None:
    with open(path, "a", encoding="utf-8") as out:
        for key, value in values.items():
            out.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")


def main(argv=None, sleep=time.sleep) -> int:
    parser = argparse.ArgumentParser(description="Sleep until the next pending Instagram post")
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    args = parser.parse_args(argv)
    wait = next_wait(load_queue(args.queue), now_local())
    if os.environ.get("GITHUB_OUTPUT"):
        write_github_output(Path(os.environ["GITHUB_OUTPUT"]), has_pending=wait is not None, wait=wait or 0)
    if wait is None:
        print("nothing pending on Instagram")
        return 0
    print(f"sleeping {wait} s until the next post", flush=True)
    sleep(wait)
    return 0


if __name__ == "__main__":
    sys.exit(main())
