"""Weibo search crawler via mobile API (m.weibo.cn)."""

import html
import re
import time
from datetime import datetime
from urllib.parse import quote_plus

from opimon.crawler.base import BaseCrawler
from opimon.models import CrawlConfig, CrawlResult, Post
from opimon.utils import random_delay


class WeiboCrawler(BaseCrawler):
    """Crawl Weibo posts via the m.weibo.cn mobile API."""

    MOBILE_API = "https://m.weibo.cn/api/container/getIndex"

    def _source_name(self) -> str:
        return "weibo"

    def _build_search_container_id(self) -> str:
        """Build containerid for keyword search."""
        return f"100103type=1&q={self.config.keyword}"

    def fetch(self) -> CrawlResult:
        errors: list[str] = []
        safe_keyword = quote_plus(self.config.keyword)

        # ── Offline path ───────────────────────────────────────
        if self.config.offline:
            posts = self._try_load_offline()
            if posts is not None:
                return CrawlResult(
                    keyword=self.config.keyword,
                    source="weibo",
                    posts=posts,
                )
            errors.append("No offline cache found")
            return CrawlResult(
                keyword=self.config.keyword,
                source="weibo",
                posts=[],
                errors=errors,
            )

        # ── Live crawl ─────────────────────────────────────────
        all_posts: list[Post] = []
        seen_ids: set[str] = set()
        container_id = self._build_search_container_id()

        for page in range(1, self.config.max_pages + 1):
            url = (
                f"{self.MOBILE_API}"
                f"?type=wb&queryVal={safe_keyword}"
                f"&containerid={container_id}"
                f"&page={page}"
            )

            print(f"  [Weibo] Fetching page {page} …")

            extra_headers = {
                "Referer": "https://m.weibo.cn/",
                "X-Requested-With": "XMLHttpRequest",
            }

            resp = self._request_with_retry(url, extra_headers=extra_headers)
            if resp is None:
                errors.append(f"Failed to fetch page {page}")
                continue

            try:
                data = resp.json()
            except Exception as e:
                errors.append(f"JSON parse error on page {page}: {e}")
                continue

            if data.get("ok") != 1:
                url_hint = data.get("url", "")
                # Check if redirected to login
                if "passport.weibo.com/sso/signin" in url_hint or "passport.weibo.com/sso/login" in url_hint:
                    errors.append(
                        "Weibo API requires login. "
                        "Try: opimon run \"KEYWORD\" --cookie 'SUB=your-cookie-value'  "
                        "(copy the SUB cookie from your browser after logging into m.weibo.cn)"
                    )
                    break

                msg = data.get("msg", "Unknown error")
                errors.append(f"Weibo API error on page {page}: {msg}")
                if "rate limit" in str(msg).lower() or "frequency" in str(msg).lower():
                    print(f"  [Weibo] Rate limited — stopping pagination.")
                    break
                continue

            posts = self._parse_search_result(data, seen_ids)
            all_posts.extend(posts)
            seen_ids.update(p.post_id for p in posts)

            if len(posts) < 10:
                print(f"  [Weibo] Fewer than 10 results on page {page}, stopping.")
                break

            random_delay(self.config.delay, self.config.delay + 1.5)

        result = CrawlResult(
            keyword=self.config.keyword,
            source="weibo",
            posts=all_posts,
            errors=errors,
        )
        self._save_cache(result)
        return result

    # ── Response parsing ───────────────────────────────────────

    def _parse_search_result(
        self, data: dict, seen_ids: set[str]
    ) -> list[Post]:
        """Parse m.weibo.cn search API response into Post objects."""
        posts: list[Post] = []

        cards = data.get("data", {}).get("cards", [])
        if not isinstance(cards, list):
            return posts

        for card in cards:
            # Card type 9 = weibo post
            if card.get("card_type") != 9:
                continue

            mblog = card.get("mblog", {})
            if not mblog:
                # Some cards wrap the post differently
                # Try extracting from card_group
                card_group = card.get("card_group", [])
                for sub_card in card_group:
                    sub_mblog = sub_card.get("mblog", {})
                    if sub_mblog:
                        mblog = sub_mblog
                        break

            if not mblog:
                continue

            try:
                post_id = str(mblog.get("id", mblog.get("mid", "")))
                if not post_id or post_id in seen_ids:
                    continue

                # Full text — prefer longText over text
                text = html.unescape(mblog.get("text", ""))
                # Strip HTML tags from Weibo text (often contains <br/>, <a>, <span>)
                text = self._strip_html(text)

                user = mblog.get("user", {})
                author = user.get("screen_name", "")

                created_str = mblog.get("created_at", "")
                created_at = self._parse_weibo_time(created_str)

                url = f"https://m.weibo.cn/detail/{post_id}"

                reposts = mblog.get("reposts_count", 0)
                comments = mblog.get("comments_count", 0)
                attitudes = mblog.get("attitudes_count", 0)

                # Use first 50 chars as title
                title = text[:80] + ("…" if len(text) > 80 else "")

                posts.append(
                    Post(
                        source="weibo",
                        post_id=post_id,
                        title=title,
                        content=text,
                        url=url,
                        author=author,
                        created_at=created_at,
                        like_count=attitudes,
                        comment_count=comments,
                    )
                )
            except Exception:
                continue

        return posts

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags and common Weibo markup artifacts."""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        return html.unescape(text).strip()

    @staticmethod
    def _parse_weibo_time(time_str: str) -> datetime | None:
        """Parse Weibo's 'created_at' format.

        Examples: '10分钟前', '2小时前', '06-25', '2025-06-25'
        """
        if not time_str:
            return None

        now = datetime.now()

        # Relative times: "X分钟前", "X小时前", "昨天", "刚刚"
        minute_match = re.match(r"(\d+)分钟前", time_str)
        if minute_match:
            minutes = int(minute_match.group(1))
            return datetime.fromtimestamp(time.time() - minutes * 60)

        hour_match = re.match(r"(\d+)小时前", time_str)
        if hour_match:
            hours = int(hour_match.group(1))
            return datetime.fromtimestamp(time.time() - hours * 3600)

        if "昨天" in time_str:
            return datetime.fromtimestamp(time.time() - 86400)

        if time_str in ("刚刚", "刚刚发布"):
            return now

        # Absolute dates
        for fmt in ("%m-%d", "%m月%d日", "%Y-%m-%d", "%Y-%m-%d %H:%M", "%a %b %d %H:%M:%S +0800 %Y"):
            try:
                parsed = datetime.strptime(time_str.strip(), fmt)
                if parsed.year == 1900:
                    parsed = parsed.replace(year=now.year)
                return parsed
            except ValueError:
                continue

        return None
