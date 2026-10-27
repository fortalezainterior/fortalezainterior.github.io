"""Refresh the 60-day Instagram token: `python -m publisher.refresh_token --out FILE` (never prints it)."""
import argparse
import sys
from pathlib import Path

import requests

from shared.config import load_settings, require

REFRESH_URL = "https://graph.instagram.com/refresh_access_token"


def refresh_token(token: str, session=None) -> tuple[str, int]:
    session = session or requests.Session()
    response = session.get(REFRESH_URL, params={"grant_type": "ig_refresh_token", "access_token": token},
                           timeout=30)
    data = response.json()
    if response.status_code >= 400 or "access_token" not in data:
        message = data.get("error", {}).get("message", "unknown error")
        raise RuntimeError(f"token refresh failed: HTTP {response.status_code}: {message}")
    return data["access_token"], int(data.get("expires_in", 0))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the Instagram long-lived token")
    parser.add_argument("--out", type=Path, required=True, help="file that receives the new token")
    args = parser.parse_args(argv)
    token, expires_in = refresh_token(require(load_settings().ig_access_token, "IG_ACCESS_TOKEN"))
    args.out.write_text(token, encoding="utf-8")
    print(f"token refreshed; valid for {expires_in // 86400} days")
    return 0


if __name__ == "__main__":
    sys.exit(main())
