"""Tests for ZhihuCrawler parsing logic (offline)."""

from opimon.crawler.zhihu import ZhihuCrawler
from opimon.models import CrawlConfig


class TestZhihuCrawlerParsing:
    def test_parse_api_response(self, zhihu_sample):
        crawler = ZhihuCrawler(CrawlConfig(keyword="人工智能"))
        posts = crawler._parse_api_response(zhihu_sample, set())

        assert len(posts) >= 5
        for p in posts:
            assert p.source == "zhihu"
            assert p.post_id
            assert p.title
            assert p.url

        # Check first post
        first = posts[0]
        assert "医疗" in first.title
        assert first.like_count > 0

    def test_parse_api_response_empty(self):
        crawler = ZhihuCrawler(CrawlConfig(keyword="test"))
        posts = crawler._parse_api_response({}, set())
        assert posts == []

    def test_parse_api_response_dedup(self, zhihu_sample):
        crawler = ZhihuCrawler(CrawlConfig(keyword="人工智能"))
        seen = set()
        posts1 = crawler._parse_api_response(zhihu_sample, seen)
        seen.update(p.post_id for p in posts1)
        posts2 = crawler._parse_api_response(zhihu_sample, seen)
        assert posts2 == []  # All should be duplicates


class TestZhihuCrawlerOffline:
    def test_fetch_offline(self, zhihu_sample, tmp_path):
        import json
        from opimon.utils import load_json

        # Write sample to temp cache
        cache_file = tmp_path / "raw_zhihu.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(zhihu_sample, f, ensure_ascii=False)

        # We need the crawler to find it — but offline expects the
        # to_dict() format. Let's test _try_load_offline with crafted data.
        # This test validates the offline path exists and works.
        config = CrawlConfig(
            keyword="人工智能",
            platforms=["zhihu"],
            offline=True,
            cache_dir=str(tmp_path),
        )

        # Write a properly cached result
        from opimon.models import Post
        from opimon.utils import save_json

        p = Post(source="zhihu", post_id="test1", title="TT", content="CC", url="http://x.com")
        from opimon.models import CrawlResult

        result = CrawlResult(keyword="人工智能", source="zhihu", posts=[p])
        save_json(result.to_dict(), tmp_path / "raw_zhihu.json")

        crawler = ZhihuCrawler(config)
        posts = crawler._try_load_offline()
        assert posts is not None
        assert len(posts) == 1
        assert posts[0].post_id == "test1"
