"""Shared test fixtures."""

from pathlib import Path

import pytest

from opimon.models import Post

# Paths
SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"


def _load_sample_json(name: str) -> dict:
    """Load a sample JSON file from data/samples/."""
    path = SAMPLES_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        import json
        return json.load(f)


@pytest.fixture
def zhihu_sample() -> dict:
    """Sample Zhihu API v4 search response."""
    return _load_sample_json("zhihu_search_sample.json")


@pytest.fixture
def weibo_sample() -> dict:
    """Sample Weibo mobile API search response."""
    return _load_sample_json("weibo_search_sample.json")


@pytest.fixture
def sample_zhihu_posts() -> list[Post]:
    """Pre-built Zhihu Post objects for testing NLP/analysis."""
    return [
        Post(
            source="zhihu",
            post_id="1",
            title="人工智能在医疗领域有哪些突破性应用？",
            content="人工智能在医疗领域的应用越来越广泛，特别是在影像诊断方面，深度学习模型已经能够达到甚至超过人类医生的准确率。",
            url="https://www.zhihu.com/question/100001",
        ),
        Post(
            source="zhihu",
            post_id="2",
            title="如何看待大语言模型的快速发展？",
            content="大语言模型的发展速度令人惊叹，但同时也引发了关于AI安全和伦理的广泛讨论。",
            url="https://www.zhihu.com/question/100002",
        ),
        Post(
            source="zhihu",
            post_id="3",
            title="AI的发展会让你感到焦虑吗？",
            content="我个人非常担心AI会取代大量工作岗位，特别是初级程序员、翻译和客服人员。",
            url="https://www.zhihu.com/question/100003",
        ),
    ]


@pytest.fixture
def sample_weibo_posts() -> list[Post]:
    """Pre-built Weibo Post objects."""
    return [
        Post(
            source="weibo",
            post_id="w1",
            title="人工智能真的太强大了！",
            content="人工智能真的太强大了！最近的AI绘画技术简直不可思议，大家有没有试过用AI生成艺术作品？",
            url="https://m.weibo.cn/detail/w1",
            author="科技达人小李",
        ),
        Post(
            source="weibo",
            post_id="w2",
            title="无语了，所谓的人工智能写出来的文章完全不能用",
            content="无语了，所谓的人工智能写出来的文章完全不能用，内容空洞，逻辑混乱，简直就是浪费时间。",
            url="https://m.weibo.cn/detail/w2",
            author="文字工作者",
        ),
        Post(
            source="weibo",
            post_id="w3",
            title="开心！公司AI项目终于上线了",
            content="开心！公司AI项目终于上线了！团队辛苦了大半年，看到用户反馈这么好，一切都值得了！",
            url="https://m.weibo.cn/detail/w3",
            author="创业在路上",
        ),
    ]


@pytest.fixture
def sample_posts(sample_zhihu_posts, sample_weibo_posts) -> list[Post]:
    """Combined posts from both platforms."""
    return sample_zhihu_posts + sample_weibo_posts
