"""Tests for WeiboCrawler parsing logic (offline)."""

from opimon.crawler.weibo import WeiboCrawler
from opimon.models import CrawlConfig


class TestWeiboCrawlerParsing:
    def test_parse_search_result(self, weibo_sample):
        crawler = WeiboCrawler(CrawlConfig(keyword="人工智能"))
        posts = crawler._parse_search_result(weibo_sample, set())

        assert len(posts) >= 5
        for p in posts:
            assert p.source == "weibo"
            assert p.post_id
            assert p.content

    def test_parse_search_result_empty(self):
        crawler = WeiboCrawler(CrawlConfig(keyword="test"))
        posts = crawler._parse_search_result({}, set())
        assert posts == []

    def test_parse_search_result_dedup(self, weibo_sample):
        crawler = WeiboCrawler(CrawlConfig(keyword="人工智能"))
        seen = set()
        posts1 = crawler._parse_search_result(weibo_sample, seen)
        seen.update(p.post_id for p in posts1)
        posts2 = crawler._parse_search_result(weibo_sample, seen)
        assert posts2 == []


class TestWeiboTimeParsing:
    def test_minutes_ago(self):
        result = WeiboCrawler._parse_weibo_time("10分钟前")
        assert result is not None

    def test_hours_ago(self):
        result = WeiboCrawler._parse_weibo_time("2小时前")
        assert result is not None

    def test_just_now(self):
        result = WeiboCrawler._parse_weibo_time("刚刚")
        assert result is not None

    def test_absolute_date(self):
        result = WeiboCrawler._parse_weibo_time("06-25")
        assert result is not None
        assert result.month == 6
        assert result.day == 25

    def test_empty(self):
        assert WeiboCrawler._parse_weibo_time("") is None
        assert WeiboCrawler._parse_weibo_time(None) is None


class TestWeiboOffline:
    def test_fetch_offline(self, tmp_path):
        from opimon.models import Post, CrawlResult
        from opimon.utils import save_json

        p = Post(source="weibo", post_id="w1", title="TT", content="CC", url="http://x.com")
        result = CrawlResult(keyword="test", source="weibo", posts=[p])
        save_json(result.to_dict(), tmp_path / "raw_weibo.json")

        config = CrawlConfig(keyword="test", platforms=["weibo"], offline=True, cache_dir=str(tmp_path))
        crawler = WeiboCrawler(config)
        posts = crawler._try_load_offline()
        assert posts is not None
        assert len(posts) == 1
        assert posts[0].post_id == "w1"
