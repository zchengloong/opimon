"""Abstract base crawler with retry logic and offline fallback."""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import requests

from opimon.models import CrawlConfig, CrawlResult, Post
from opimon.utils import load_json, random_ua


class BaseCrawler(ABC):
    """Abstract crawler with retry + backoff + offline support."""

    def __init__(self, config: CrawlConfig):
        self.config = config
        self.session = self._make_session()

    def _make_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": random_ua(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "DNT": "1",
            }
        )
        session.timeout = self.config.timeout

        # Inject user-supplied cookie
        if self.config.cookie:
            session.headers["Cookie"] = self.config.cookie

        return session

    # ── Public API ───────────────────────────────────────────────

    @abstractmethod
    def fetch(self) -> CrawlResult:
        """Fetch posts from the platform. Subclasses must implement."""
        ...

    # ── Retry logic ──────────────────────────────────────────────

    def _request_with_retry(
        self,
        url: str,
        retries: int = 3,
        backoff: float = 1.5,
        extra_headers: dict[str, str] | None = None,
    ) -> requests.Response | None:
        """GET *url* with exponential backoff on 429/5xx.

        Returns the Response on success, or None after exhausting retries.
        """
        headers = extra_headers or {}

        for attempt in range(1, retries + 1):
            try:
                # Rotate User-Agent per attempt
                self.session.headers["User-Agent"] = random_ua()
                resp = self.session.get(url, headers=headers)

                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else backoff**attempt
                    print(f"  [429] Rate limited, waiting {wait:.1f}s … (attempt {attempt}/{retries})")
                    time.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    wait = backoff**attempt
                    print(f"  [{resp.status_code}] Server error, retrying in {wait:.1f}s … (attempt {attempt}/{retries})")
                    time.sleep(wait)
                    continue

                if resp.status_code == 403:
                    print(f"  [403] Access denied for {url}. Platform may block the request.")
                    return None

                resp.raise_for_status()
                return resp

            except requests.Timeout:
                print(f"  [Timeout] Request timed out (attempt {attempt}/{retries})")
                time.sleep(backoff**attempt)

            except requests.RequestException as e:
                print(f"  [Error] {e} (attempt {attempt}/{retries})")
                time.sleep(backoff**attempt)

        print(f"  [FAIL] All {retries} retries exhausted for {url}")
        return None

    # ── Offline support ──────────────────────────────────────────

    def _offline_cache_path(self) -> Path:
        """Path to the cached raw data file for this crawler."""
        source = self._source_name()
        return Path(self.config.cache_dir) / f"raw_{source}.json"

    def _try_load_offline(self) -> list[Post] | None:
        """Load cached posts if offline mode is set.

        Returns None if no cache file exists.
        """
        cache_path = self._offline_cache_path()
        if not cache_path.exists():
            return None

        print(f"  [Offline] Loading cached data from {cache_path}")
        data = load_json(cache_path)
        return [Post(**p) for p in data.get("posts", [])]

    def _save_cache(self, result: CrawlResult) -> None:
        """Save crawl result to disk for offline reuse."""
        cache_path = self._offline_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = result.to_dict()
        from opimon.utils import save_json

        save_json(data, cache_path)
        print(f"  [Cache] Saved {len(result.posts)} posts to {cache_path}")

    @abstractmethod
    def _source_name(self) -> str:
        """Return platform source name (e.g. 'zhihu', 'weibo')."""
        ...
