"""Shared data models for the opimon pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Post:
    """A single crawled post / article from a platform."""

    source: str  # "zhihu" | "weibo"
    post_id: str  # Platform-native ID
    title: str  # Title or truncated text
    content: str  # Full text body
    url: str  # Permalink
    author: str = ""
    created_at: datetime | None = None
    like_count: int = 0
    comment_count: int = 0
    sentiment_score: float = 0.0  # 0.0 = most negative, 1.0 = most positive

    @property
    def full_text(self) -> str:
        """Return title + content for NLP processing."""
        if self.title and self.content:
            return f"{self.title} {self.content}"
        return self.title or self.content


@dataclass
class CrawlConfig:
    """Controls how crawlers behave."""

    keyword: str
    platforms: list[str] = field(default_factory=lambda: ["zhihu", "weibo"])
    max_pages: int = 3
    delay: float = 1.5  # Seconds between requests
    timeout: int = 30  # HTTP request timeout
    offline: bool = False
    cache_dir: str = "./output"
    cookie: str = ""  # Browser cookie for authenticated requests


@dataclass
class CrawlResult:
    """Output of one platform crawl."""

    keyword: str
    source: str  # Platform name
    posts: list[Post] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def success(self) -> bool:
        return len(self.posts) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "post_count": len(self.posts),
            "errors": self.errors,
            "posts": [
                {
                    "source": p.source,
                    "post_id": p.post_id,
                    "title": p.title,
                    "content": p.content,
                    "url": p.url,
                    "author": p.author,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "like_count": p.like_count,
                    "comment_count": p.comment_count,
                    "sentiment_score": p.sentiment_score,
                }
                for p in self.posts
            ],
        }


@dataclass
class SentimentReport:
    """Aggregate sentiment analysis result."""

    keyword: str
    total_posts: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    avg_score: float = 0.0
    platform_breakdown: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def positive_pct(self) -> float:
        if self.total_posts == 0:
            return 0.0
        return self.positive_count / self.total_posts * 100

    @property
    def negative_pct(self) -> float:
        if self.total_posts == 0:
            return 0.0
        return self.negative_count / self.total_posts * 100

    @property
    def neutral_pct(self) -> float:
        if self.total_posts == 0:
            return 0.0
        return self.neutral_count / self.total_posts * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "total_posts": self.total_posts,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "positive_pct": round(self.positive_pct, 1),
            "negative_pct": round(self.negative_pct, 1),
            "neutral_pct": round(self.neutral_pct, 1),
            "avg_score": round(self.avg_score, 4),
            "platform_breakdown": self.platform_breakdown,
        }
