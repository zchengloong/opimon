"""Word cloud generation with Chinese font support."""

import os
import sys
from pathlib import Path

import matplotlib.font_manager as fm
from wordcloud import WordCloud


class WordCloudGenerator:
    """Generate Chinese word cloud images.

    Usage:
        gen = WordCloudGenerator()  # auto-discovers Chinese font
        gen.generate({"人工智能": 10, "数据": 8}, "output.png")
    """

    # Common Chinese font paths across platforms
    _FONT_CANDIDATES = [
        # Linux — WenQuanYi
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/wenquanyi/wqy-microhei/wqy-microhei.ttc",  # Arch Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Windows
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
    ]

    def __init__(self, font_path: str | None = None):
        """Initialize with optional *font_path*.

        If not provided, auto-discovers a Chinese-capable font on the system.
        """
        self.font_path = font_path or self._find_chinese_font()

    def generate(
        self,
        frequencies: dict[str, int],
        output_path: str | Path,
        width: int = 800,
        height: int = 600,
        max_words: int = 200,
        background_color: str = "white",
        colormap: str = "viridis",
    ) -> Path:
        """Generate a word cloud PNG from word frequencies.

        Args:
            frequencies: ``{word: count}`` dict (from ``ChineseSegmenter``).
            output_path: Where to save the PNG image.
            width: Image width in pixels.
            height: Image height in pixels.
            max_words: Maximum number of words to display.
            background_color: CSS color name for background.
            colormap: Matplotlib colormap name.

        Returns:
            The resolved Path of the output file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        wc = WordCloud(
            font_path=self.font_path,
            width=width,
            height=height,
            max_words=max_words,
            background_color=background_color,
            colormap=colormap,
            collocations=False,  # We pre-segmented; avoid bigram generation
            prefer_horizontal=0.75,
            scale=2,  # Higher DPI
        )
        wc.generate_from_frequencies(frequencies)
        wc.to_file(str(output_path))

        return output_path.resolve()

    # ── Font discovery ─────────────────────────────────────────

    def _find_chinese_font(self) -> str:
        """Locate a Chinese-capable font file on the system.

        Priority:
        1. Known system paths (self._FONT_CANDIDATES)
        2. Matplotlib font manager CJK fonts
        3. Raise FileNotFoundError with install instructions
        """
        # 1. Check known paths
        for path in self._FONT_CANDIDATES:
            if os.path.isfile(path):
                return path

        # 2. Search matplotlib font manager
        for f in fm.fontManager.ttflist:
            if self._is_cjk_font(f.name):
                return f.fname

        # 3. Bail with helpful message
        raise FileNotFoundError(
            "No Chinese font found on the system.\n\n"
            "Install one of:\n"
            "  Ubuntu/Debian:  sudo apt install fonts-wqy-microhei\n"
            "  Fedora/RHEL:    sudo dnf install wqy-microhei-fonts\n"
            "  Arch:           sudo pacman -S wqy-microhei\n"
            "  macOS:          (PingFang is built-in — check system)\n"
            "  Windows:        (SimHei/MSYH is built-in — check system)\n\n"
            "Or provide a font path manually:\n"
            "  opimon run \"关键词\" --font /path/to/chinese-font.ttf"
        )

    @staticmethod
    def _is_cjk_font(name: str) -> bool:
        """Return True if the font name looks like a CJK font."""
        cjk_markers = [
            "CJK", "Han", "WenQuanYi", "WQY", "Noto Sans",
            "SimHei", "SimSun", "MSYH", "Microsoft YaHei",
            "PingFang", "STHeiti", "Heiti", "Arial Unicode",
            "DroidSansFallback", "AR PL", "Source Han",
        ]
        lower = name.lower()
        return any(m.lower() in lower for m in cjk_markers)
