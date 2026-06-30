"""Chinese word segmentation via jieba with stopword filtering."""

from collections import Counter
from pathlib import Path

import jieba


class ChineseSegmenter:
    """Segment Chinese text using jieba, with stopword filtering.

    Usage:
        seg = ChineseSegmenter()
        words = seg.segment("人工智能正在改变世界")
        # → ["人工智能", "正在", "改变", "世界"]

        freqs = seg.compute_frequencies(["文本1", "文本2", ...])
        # → {"人工智能": 5, "改变": 3, ...}
    """

    # Bundled stopwords path relative to the package
    _BUNDLED_STOPWORDS = Path(__file__).resolve().parent.parent.parent / "data" / "stopwords.txt"

    def __init__(self, stopwords_path: str | Path | None = None):
        """Initialize segmenter with optional custom stopwords file.

        Args:
            stopwords_path: Path to a stopwords file (one word per line).
                            Defaults to the bundled ``data/stopwords.txt``.
        """
        self.stopwords: set[str] = self._load_stopwords(stopwords_path)
        # Ensure jieba is initialized (lazy-loaded internally)
        jieba.initialize()

    def segment(self, text: str) -> list[str]:
        """Cut *text* with jieba and filter stopwords + short tokens.

        Returns a list of meaningful Chinese words (length >= 2).
        """
        if not text:
            return []

        words = jieba.lcut(text)
        return [
            w.strip()
            for w in words
            if len(w.strip()) >= 2 and w.strip() not in self.stopwords
        ]

    def compute_frequencies(self, texts: list[str]) -> dict[str, int]:
        """Segment a list of texts and return word → frequency mapping.

        This is the primary input for the WordCloud generator.
        """
        counter: Counter[str] = Counter()
        for text in texts:
            words = self.segment(text)
            counter.update(words)
        return dict(counter.most_common())

    # ── Internals ──────────────────────────────────────────────

    def _load_stopwords(self, path: str | Path | None) -> set[str]:
        """Load stopwords from file, falling back to bundled list."""
        resolved = Path(path) if path else self._BUNDLED_STOPWORDS

        if not resolved.exists():
            # Create minimal default set
            return {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
                    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
                    "着", "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那"}

        with open(resolved, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip() and not line.startswith("#")}
