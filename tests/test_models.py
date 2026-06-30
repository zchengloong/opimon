"""Tests for data models."""

from opimon.models import CrawlConfig, CrawlResult, Post, SentimentReport


class TestPost:
    def test_create_minimal(self):
        p = Post(source="zhihu", post_id="1", title="Hello", content="World", url="http://x.com")
        assert p.source == "zhihu"
        assert p.post_id == "1"
        assert p.sentiment_score == 0.0

    def test_full_text(self):
        p = Post(source="zhihu", post_id="1", title="Title", content="Body", url="http://x.com")
        assert p.full_text == "Title Body"

    def test_full_text_no_title(self):
        p = Post(source="zhihu", post_id="1", title="", content="Body", url="http://x.com")
        assert p.full_text == "Body"

    def test_full_text_no_content(self):
        p = Post(source="zhihu", post_id="1", title="Title", content="", url="http://x.com")
        assert p.full_text == "Title"


class TestCrawlConfig:
    def test_defaults(self):
        cfg = CrawlConfig(keyword="test")
        assert cfg.platforms == ["zhihu", "weibo"]
        assert cfg.max_pages == 3
        assert cfg.delay == 1.5
        assert cfg.offline is False


class TestCrawlResult:
    def test_success(self):
        r = CrawlResult(keyword="test", source="zhihu")
        assert r.success is False
        assert len(r.posts) == 0

    def test_success_with_posts(self):
        p = Post(source="zhihu", post_id="1", title="T", content="C", url="http://x.com")
        r = CrawlResult(keyword="test", source="zhihu", posts=[p])
        assert r.success is True

    def test_to_dict(self):
        p = Post(source="zhihu", post_id="1", title="T", content="C", url="http://x.com")
        r = CrawlResult(keyword="test", source="zhihu", posts=[p], errors=["err1"])
        d = r.to_dict()
        assert d["keyword"] == "test"
        assert d["source"] == "zhihu"
        assert d["post_count"] == 1
        assert len(d["posts"]) == 1
        assert d["errors"] == ["err1"]


class TestSentimentReport:
    def test_empty(self):
        r = SentimentReport(keyword="test")
        assert r.total_posts == 0
        assert r.positive_pct == 0.0
        assert r.negative_pct == 0.0
        assert r.neutral_pct == 0.0

    def test_percentages(self):
        r = SentimentReport(
            keyword="test",
            total_posts=10,
            positive_count=6,
            negative_count=3,
            neutral_count=1,
        )
        assert r.positive_pct == 60.0
        assert r.negative_pct == 30.0
        assert r.neutral_pct == 10.0

    def test_to_dict(self):
        r = SentimentReport(
            keyword="test",
            total_posts=5,
            positive_count=3,
            negative_count=1,
            neutral_count=1,
            avg_score=0.72,
            platform_breakdown={"zhihu": {"positive": 2, "negative": 1, "neutral": 0}},
        )
        d = r.to_dict()
        assert d["keyword"] == "test"
        assert d["total_posts"] == 5
        assert d["positive_pct"] == 60.0
        assert d["avg_score"] == 0.72
        assert "platform_breakdown" in d
