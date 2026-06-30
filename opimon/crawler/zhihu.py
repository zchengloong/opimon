"""Zhihu search crawler via API v4 with BeautifulSoup fallback."""

import html
import re
from datetime import datetime
from urllib.parse import quote_plus

from opimon.crawler.base import BaseCrawler
from opimon.models import CrawlConfig, CrawlResult, Post
from opimon.utils import random_delay


class ZhihuCrawler(BaseCrawler):
    """Crawl Zhihu search results."""

    SEARCH_API = "https://www.zhihu.com/api/v4/search_v3"
    SEARCH_PAGE = "https://www.zhihu.com/search"

    def _source_name(self) -> str:
        return "zhihu"

    def fetch(self) -> CrawlResult:
        errors: list[str] = []
        safe_keyword = quote_plus(self.config.keyword)

        # ── Offline path ───────────────────────────────────────
        if self.config.offline:
            posts = self._try_load_offline()
            if posts is not None:
                return CrawlResult(
                    keyword=self.config.keyword,
                    source="zhihu",
                    posts=posts,
                )
            errors.append("No offline cache found — try running without --offline first")
            return CrawlResult(
                keyword=self.config.keyword,
                source="zhihu",
                posts=[],
                errors=errors,
            )

        # ── Live crawl ─────────────────────────────────────────
        all_posts: list[Post] = []
        seen_ids: set[str] = set()

        for page in range(self.config.max_pages):
            offset = page * 20
            url = f"{self.SEARCH_API}?q={safe_keyword}&type=content&offset={offset}&limit=20"
            print(f"  [Zhihu] Fetching page {page + 1} …")

            resp = self._request_with_retry(url)
            if resp is None:
                errors.append(f"Failed to fetch page {page + 1}")
                continue

            try:
                data = resp.json()
            except Exception as e:
                errors.append(f"JSON parse error on page {page + 1}: {e}")
                # Try BeautifulSoup fallback on search page
                fallback_posts = self._scrape_search_page(page)
                all_posts.extend(fallback_posts)
                random_delay()
                continue

            # Check for anti-bot / auth walls
            if isinstance(data, dict) and "HitLabels" in data:
                errors.append(
                    "Zhihu API returned anti-bot challenge (HitLabels). "
                    "The API v4 endpoint requires a valid cookie. "
                    "Try: opimon run \"KEYWORD\" --cookie '...'  "
                    "(copy cookies from your browser's Zhihu session)"
                )
                break

            posts = self._parse_api_response(data, seen_ids)
            all_posts.extend(posts)
            seen_ids.update(p.post_id for p in posts)

            if len(posts) < 20:
                print(f"  [Zhihu] Fewer than 20 results on page {page + 1}, stopping pagination.")
                break

            random_delay(self.config.delay, self.config.delay + 1.0)

        result = CrawlResult(
            keyword=self.config.keyword,
            source="zhihu",
            posts=all_posts,
            errors=errors,
        )
        self._save_cache(result)
        return result

    # ── API parsing ────────────────────────────────────────────

    def _parse_api_response(
        self, data: dict, seen_ids: set[str]
    ) -> list[Post]:
        """Parse Zhihu API v4 search response into Post objects."""
        posts: list[Post] = []

        items = data.get("data", [])
        if not isinstance(items, list):
            return posts

        for item in items:
            try:
                obj = item.get("object", {})
                if not obj:
                    continue

                obj_type = obj.get("type", "")

                if obj_type == "answer":
                    question = obj.get("question", {})
                    post_id = str(obj.get("id", ""))
                    title = html.unescape(question.get("title", ""))
                    content = html.unescape(obj.get("excerpt", ""))
                    url = obj.get("url", f"https://www.zhihu.com/question/{question.get('id', '')}/answer/{post_id}")
                    author = obj.get("author", {}).get("name", "")
                    created_at = datetime.fromtimestamp(obj.get("created_time", 0)) if obj.get("created_time") else None
                    like_count = obj.get("voteup_count", 0)
                    comment_count = obj.get("comment_count", 0)

                elif obj_type == "article":
                    post_id = str(obj.get("id", ""))
                    title = html.unescape(obj.get("title", ""))
                    content = html.unescape(obj.get("excerpt", obj.get("content", "")))
                    url = obj.get("url", f"https://zhuanlan.zhihu.com/p/{post_id}")
                    author = obj.get("author", {}).get("name", "")
                    created_at = datetime.fromtimestamp(obj.get("created", 0)) if obj.get("created") else None
                    like_count = obj.get("voteup_count", 0)
                    comment_count = obj.get("comment_count", 0)

                elif obj_type == "search_result" and "question" in obj:
                    question = obj["question"]
                    post_id = str(question.get("id", ""))
                    title = html.unescape(question.get("title", ""))
                    content = html.unescape(obj.get("excerpt", ""))
                    url = question.get("url", f"https://www.zhihu.com/question/{post_id}")
                    author = ""
                    created_at = None
                    like_count = 0
                    comment_count = question.get("answer_count", 0)

                else:
                    continue

                # Deduplicate
                if post_id in seen_ids:
                    continue

                # Strip HTML tags from content
                content = self._strip_html(content)

                if not title and not content:
                    continue

                posts.append(
                    Post(
                        source="zhihu",
                        post_id=post_id,
                        title=title,
                        content=content,
                        url=url,
                        author=author,
                        created_at=created_at,
                        like_count=like_count,
                        comment_count=comment_count,
                    )
                )
            except Exception:
                continue  # Skip malformed items silently

        return posts

    # ── BeautifulSoup fallback ──────────────────────────────────

    def _scrape_search_page(self, page: int) -> list[Post]:
        """Fallback: scrape the SSR search page with BeautifulSoup.

        This is less reliable but works when the API is blocked.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        url = f"{self.SEARCH_PAGE}?type=content&q={safe_keyword}&offset={page * 20}"
        print(f"  [Zhihu] Trying SSR page fallback: {url}")

        resp = self._request_with_retry(url)
        if resp is None:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        posts: list[Post] = []

        # Try to find search result cards
        cards = soup.select(".List-item, .SearchResultCard, [itemprop]")
        for card in cards:
            title_el = card.select_one("h2 a, .ContentItem-title a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://www.zhihu.com{href}"

            excerpt_el = card.select_one(".RichText, .SearchItem-excerpt, [itemprop='description']")
            content = excerpt_el.get_text(strip=True) if excerpt_el else ""

            post_id = href.rstrip("/").rsplit("/", 1)[-1] if href else ""

            posts.append(
                Post(
                    source="zhihu",
                    post_id=post_id,
                    title=title,
                    content=content,
                    url=href,
                )
            )

        return posts

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        return text.strip()
