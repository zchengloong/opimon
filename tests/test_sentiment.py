"""Tests for SentimentAnalyzer."""

from opimon.models import Post
from opimon.nlp import SentimentAnalyzer


class TestSentimentAnalyzer:
    def test_classify_positive(self):
        a = SentimentAnalyzer()
        assert a.classify(0.8) == "positive"
        assert a.classify(0.6) == "positive"

    def test_classify_negative(self):
        a = SentimentAnalyzer()
        assert a.classify(0.2) == "negative"
        assert a.classify(0.0) == "negative"

    def test_classify_neutral(self):
        a = SentimentAnalyzer()
        assert a.classify(0.5) == "neutral"
        assert a.classify(0.45) == "neutral"

    def test_short_text_returns_neutral(self):
        a = SentimentAnalyzer()
        score = a.analyze("你好")
        assert score == 0.5

    def test_empty_text_returns_neutral(self):
        a = SentimentAnalyzer()
        assert a.analyze("") == 0.5
        assert a.analyze(None) == 0.5  # type: ignore

    def test_positive_text(self):
        a = SentimentAnalyzer()
        score = a.analyze("今天天气真好，心情非常好，生活充满了希望和快乐")
        assert score > 0.5  # Should lean positive

    def test_negative_text(self):
        a = SentimentAnalyzer()
        score = a.analyze("太糟糕了，非常失望，简直令人绝望，这完全不可接受")
        assert score < 0.5  # Should lean negative

    def test_analyze_post(self):
        a = SentimentAnalyzer()
        post = Post(
            source="test",
            post_id="1",
            title="开心",
            content="今天真是美好的一天，一切都很顺利，心情非常愉快",
            url="http://x.com",
        )
        score = a.analyze_post(post)
        assert 0 <= score <= 1
        assert post.sentiment_score == score

    def test_generate_report(self, sample_posts):
        a = SentimentAnalyzer()
        report = a.generate_report(sample_posts)

        assert report.total_posts == len(sample_posts)
        assert report.total_posts > 0
        assert report.positive_count + report.negative_count + report.neutral_count == report.total_posts
        assert 0 <= report.avg_score <= 1

        # Check platform breakdown exists
        assert "zhihu" in report.platform_breakdown
        assert "weibo" in report.platform_breakdown

    def test_generate_report_empty(self):
        a = SentimentAnalyzer()
        report = a.generate_report([])
        assert report.total_posts == 0

    def test_generate_report_sets_scores(self, sample_posts):
        a = SentimentAnalyzer()
        a.generate_report(sample_posts)
        for post in sample_posts:
            assert 0 <= post.sentiment_score <= 1
