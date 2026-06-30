"""Crawler registry and factory."""

from opimon.crawler.base import BaseCrawler
from opimon.crawler.zhihu import ZhihuCrawler
from opimon.crawler.weibo import WeiboCrawler

AVAILABLE_CRAWLERS: dict[str, type[BaseCrawler]] = {
    "zhihu": ZhihuCrawler,
    "weibo": WeiboCrawler,
}


def get_crawler(platform: str) -> type[BaseCrawler]:
    """Look up a crawler class by platform name.

    Raises ValueError for unknown platforms.
    """
    platform = platform.lower().strip()
    if platform not in AVAILABLE_CRAWLERS:
        raise ValueError(
            f"Unknown platform '{platform}'. "
            f"Available: {', '.join(AVAILABLE_CRAWLERS)}"
        )
    return AVAILABLE_CRAWLERS[platform]
