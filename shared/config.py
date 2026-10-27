"""Runtime configuration: constants plus settings from .env locally or GitHub Secrets in CI."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
# This repository is private. Publishing runs in a public one (free GitHub Actions and Pages) that holds the queue,
# publisher/, shared/ and the media; PUBLIC_DIR is its local clone (generator/public_repo.py).
PUBLIC_REMOTE = "https://github.com/fortalezainterior/fortalezainterior.github.io.git"
PUBLIC_DIR = ROOT / "public"
TIMEZONE = "America/Sao_Paulo"
VOICE = "pm_santa"  # Kokoro pt-BR male: lowest pitch with the widest intonation range we measured
VOICE_SPEED = 1.1  # inside sentences only; the pauses between sentences keep their length
KOKORO_MODEL = ROOT / "generator" / "voices" / "kokoro-v1.0.onnx"
KOKORO_VOICES = ROOT / "generator" / "voices" / "voices-v1.0.bin"


@dataclass(frozen=True)
class Settings:
    pixabay_api_key: str | None
    ig_user_id: str | None
    ig_access_token: str | None
    pages_base_url: str | None
    handle: str


def load_settings(env_file: Path | None = ROOT / ".env") -> Settings:
    if env_file is not None and Path(env_file).exists():
        load_dotenv(env_file, override=False)
    return Settings(
        pixabay_api_key=os.getenv("PIXABAY_API_KEY") or None,
        ig_user_id=os.getenv("IG_USER_ID") or None,
        ig_access_token=os.getenv("IG_ACCESS_TOKEN") or None,
        pages_base_url=(os.getenv("PAGES_BASE_URL") or "").rstrip("/") or None,
        handle=os.getenv("IG_HANDLE", ""),
    )


def require(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"Missing required setting {name}; set it in .env or GitHub Secrets")
    return value
