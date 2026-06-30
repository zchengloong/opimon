"""Sentiment analysis for Chinese text using SnowNLP."""

import re

from snownlp import SnowNLP

from opimon.models import Post, SentimentReport


class SentimentAnalyzer:
    """Analyze sentiment of Chinese text using SnowNLP.

    SnowNLP is a pre-trained Naive Bayes model that outputs a score
    in [0, 1]. Higher scores indicate more positive sentiment.

    Usage:
        analyzer = SentimentAnalyzer()
        score = analyzer.analyze("今天天气真好")
        label = analyzer.classify(score)  # "positive"
    """

    POSITIVE_THRESHOLD = 0.6
    NEGATIVE_THRESHOLD = 0.4
    MIN_TEXT_LENGTH = 5  # Characters below this get a neutral score

    def analyze(self, text: str) -> float:
        """Return a sentiment score in [0.0, 1.0] for *text*.

        Returns 0.5 (neutral) for very short or empty text.
        """
        if not text or len(self._clean(text)) < self.MIN_TEXT_LENGTH:
            return 0.5

        try:
            s = SnowNLP(text)
            return s.sentiments
        except Exception:
            return 0.5

    def classify(self, score: float) -> str:
        """Classify a sentiment score into 'positive', 'negative', or 'neutral'.

        >>> SentimentAnalyzer().classify(0.8)
        'positive'
        >>> SentimentAnalyzer().classify(0.2)
        'negative'
        >>> SentimentAnalyzer().classify(0.5)
        'neutral'
        """
        if score >= self.POSITIVE_THRESHOLD:
            return "positive"
        elif score <= self.NEGATIVE_THRESHOLD:
            return "negative"
        return "neutral"

    def analyze_post(self, post: Post) -> float:
        """Analyze a single Post and attach the score to it.

        Returns the sentiment score.
        """
        text = post.full_text
        score = self.analyze(text)
        post.sentiment_score = score
        return score

    def generate_report(self, posts: list[Post]) -> SentimentReport:
        """Analyze all posts and produce an aggregate SentimentReport.

        Side effect: sets ``sentiment_score`` on each Post.
        """
        if not posts:
            return SentimentReport(keyword="", total_posts=0)

        # Use the keyword from the first post's context (set by caller)
        keyword = ""

        pos = neg = neu = 0
        total_score = 0.0
        platform_counts: dict[str, dict[str, int]] = {}

        for post in posts:
            score = self.analyze_post(post)
            label = self.classify(score)

            if label == "positive":
                pos += 1
            elif label == "negative":
                neg += 1
            else:
                neu += 1

            total_score += score

            # Per-platform breakdown
            src = post.source
            if src not in platform_counts:
                platform_counts[src] = {"positive": 0, "negative": 0, "neutral": 0}
            platform_counts[src][label] += 1

        total = len(posts)

        return SentimentReport(
            keyword=keyword,
            total_posts=total,
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            avg_score=total_score / total if total > 0 else 0.0,
            platform_breakdown=platform_counts,
        )

    @staticmethod
    def _clean(text: str) -> str:
        """Strip URLs, HTML, and extra whitespace."""
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()
