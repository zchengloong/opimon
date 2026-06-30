"""Shared utilities: HTTP session, file I/O, delay, User-Agent rotation."""

import json
import random
import time
from pathlib import Path
from typing import Any

import requests

# ── User-Agent rotation ──────────────────────────────────────────────

_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    # Safari on iOS
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Chrome on Android
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
]


def random_ua() -> str:
    """Return a random User-Agent string."""
    return random.choice(_USER_AGENTS)


# ── HTTP Session ─────────────────────────────────────────────────────


def make_session(timeout: int = 30) -> requests.Session:
    """Create a requests.Session with realistic browser headers."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    session.timeout = timeout
    return session


# ── Rate limiting ────────────────────────────────────────────────────


def random_delay(min_s: float = 0.5, max_s: float = 2.5) -> None:
    """Sleep for a random interval to avoid triggering rate limits."""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


# ── JSON file I/O ────────────────────────────────────────────────────


def save_json(data: Any, filepath: str | Path) -> Path:
    """Serialize data to JSON and write to *filepath*. Returns the Path."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def load_json(filepath: str | Path) -> Any:
    """Load and deserialize JSON from *filepath*."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Directory helpers ────────────────────────────────────────────────


def ensure_output_dir(path: str | Path) -> Path:
    """Create output directory if it doesn't exist; return resolved Path."""
    p = Path(path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p
