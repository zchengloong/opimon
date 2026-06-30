"""Tests for WordCloudGenerator."""

from pathlib import Path

import pytest

from opimon.visualize import WordCloudGenerator


class TestWordCloudGenerator:
    def test_find_chinese_font(self):
        """Verify font discovery returns a valid path or raises with instructions."""
        try:
            font_path = WordCloudGenerator()._find_chinese_font()
            assert Path(font_path).is_file()
        except FileNotFoundError as e:
            # Acceptable: no Chinese font on system
            assert "No Chinese font found" in str(e)
            assert "sudo apt install" in str(e) or "sudo dnf" in str(e)

    def test_create_with_nonexistent_path(self, tmp_path):
        """Passing a nonexistent font path should fail when generating."""
        gen = WordCloudGenerator(font_path="/nonexistent/font.ttf")
        with pytest.raises((FileNotFoundError, OSError)):
            gen.generate({"测试": 1}, tmp_path / "out.png")

    def test_generate_png(self, tmp_path):
        """If a Chinese font is available, generate a word cloud."""
        try:
            gen = WordCloudGenerator()
        except FileNotFoundError:
            pytest.skip("No Chinese font available on this system")

        freqs = {
            "人工智能": 50,
            "深度学习": 40,
            "机器学习": 35,
            "数据科学": 30,
            "自然语言处理": 25,
            "计算机视觉": 20,
            "神经网络": 15,
            "算法": 10,
        }

        output = tmp_path / "test_wordcloud.png"
        result = gen.generate(freqs, output)

        assert result.exists()
        assert result.stat().st_size > 1000  # Should be a real image
