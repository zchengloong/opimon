"""Tests for ChineseSegmenter."""

from opimon.nlp import ChineseSegmenter


class TestChineseSegmenter:
    def test_create(self):
        seg = ChineseSegmenter()
        assert seg.stopwords is not None
        assert len(seg.stopwords) > 10

    def test_segment_empty(self):
        seg = ChineseSegmenter()
        assert seg.segment("") == []

    def test_segment_basic(self):
        seg = ChineseSegmenter()
        words = seg.segment("人工智能正在改变世界")
        # Should contain meaningful words, not stopwords
        assert "人工智能" in words
        assert "改变" in words
        assert "世界" in words
        # Common stopwords should be filtered
        assert "的" not in words
        assert "了" not in words

    def test_segment_filters_short_words(self):
        seg = ChineseSegmenter()
        words = seg.segment("他的书")
        # Single-char words (except meaningful ones) should be filtered
        assert "他" not in words  # length < 2

    def test_compute_frequencies(self):
        seg = ChineseSegmenter()
        texts = [
            "人工智能人工智能非常有趣",  # 人工智能 appears twice
            "人工智能正在改变世界",
        ]
        freqs = seg.compute_frequencies(texts)
        assert "人工智能" in freqs
        assert freqs["人工智能"] >= 2
        assert "有趣" in freqs

    def test_compute_frequencies_empty(self):
        seg = ChineseSegmenter()
        assert seg.compute_frequencies([]) == {}
