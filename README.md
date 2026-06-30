# opimon — 舆情监控爬虫

Public opinion monitoring CLI tool — crawl trending topics from **Zhihu** (知乎) and **Weibo** (微博) by keyword, perform Chinese sentiment analysis, and generate word cloud visualizations.

## Features

- **Multi-platform crawling** — Zhihu API v4 + Weibo mobile API, with BeautifulSoup fallback
- **Chinese sentiment analysis** — SnowNLP-based classification (positive / neutral / negative)
- **Word cloud generation** — jieba segmentation + wordcloud with automatic Chinese font discovery
- **Offline mode** — cache raw results to disk, re-analyze without repeated network requests
- **Cookie support** — pass browser cookies via `--cookie` to bypass platform anti-bot walls
- **Modular pipeline** — `run` (crawl → analyze → visualize), `crawl` (fetch only), `report` (analyze existing data)

## Project Structure

```
opimon/
├── __init__.py          # Version
├── __main__.py          # python -m opimon support
├── cli.py               # Click CLI (run/crawl/report subcommands)
├── models.py            # Dataclasses: Post, CrawlConfig, CrawlResult, SentimentReport
├── utils.py             # HTTP session builder, JSON I/O, random delay helpers
├── crawler/
│   ├── base.py          # Abstract BaseCrawler — retry, backoff, offline cache
│   ├── zhihu.py         # ZhihuCrawler — API v4 + SSR fallback via BeautifulSoup
│   └── weibo.py         # WeiboCrawler — mobile API (m.weibo.cn)
├── nlp/
│   ├── segmenter.py     # jieba word segmentation + stopword filtering
│   └── sentiment.py     # SnowNLP sentiment scoring + report generation
└── visualize/
    └── wordcloud.py     # WordCloud generation with multi-platform Chinese font discovery
data/
├── stopwords.txt        # Bundled Chinese stopword list (~300 words)
└── samples/             # Sample API responses for offline testing
tests/
├── conftest.py
├── test_models.py
├── test_zhihu_crawler.py
├── test_weibo_crawler.py
├── test_segmenter.py
├── test_sentiment.py
└── test_visualize.py
output/                  # Generated results (gitignored)
```

## Installation

### Requirements

- Python 3.11+
- A Chinese TrueType font (for word cloud generation)

### Install with uv

```bash
# Clone the repo
git clone git@github.com:zchengloong/opimon.git
cd opimon

# Create venv and install
uv sync

# Install dev dependencies (for running tests)
uv sync --dev

# Run the installed CLI
uv run opimon --help
```

### Install a Chinese font

```bash
# Arch Linux
sudo pacman -S wqy-microhei

# Debian / Ubuntu
sudo apt install fonts-wqy-microhei

# macOS
# Use built-in PingFang SC (auto-discovered) or:
brew install --cask font-wqy-microhei

# Windows
# SimHei and Microsoft YaHei are auto-discovered from C:\Windows\Fonts
```

The word cloud module auto-discovers fonts across all common platform paths. If none are found, it prints a clear error with install instructions for your OS.

## Quick Start

### Basic usage

```bash
# Full pipeline: crawl Zhihu + Weibo, analyze sentiment, generate word cloud
uv run opimon run "人工智能"

# Single platform only
uv run opimon run "芯片" -p zhihu --pages 5

# Crawl only — save raw JSON without analysis
uv run opimon crawl "新能源汽车" -p weibo

# Analyze previously crawled data
uv run opimon report -i ./output/20250630_105251_人工智能/

# Re-analyze cached data without network access
uv run opimon run "人工智能" --offline
```

### Using cookies for authenticated crawling

Both Zhihu and Weibo require login cookies to return real search results. Without cookies, Zhihu returns an anti-bot challenge and Weibo redirects to a login page.

**How to get cookies:**

1.  **Zhihu:** Open your browser DevTools (F12) → Application → Cookies → `www.zhihu.com`. Copy the entire cookie string, or at minimum the `z_c0` and `d_c0` values.

2.  **Weibo:** Log in to `m.weibo.cn` in your browser. DevTools (F12) → Application → Cookies → `m.weibo.cn`. Copy the `SUB` cookie value.

**Providing cookies to opimon:**

```bash
# Zhihu only
uv run opimon run "人工智能" -p zhihu --cookie 'z_c0="..."; d_c0="..."'

# Weibo only
uv run opimon run "热搜" -p weibo --cookie 'SUB=_2AkM...'

# Both platforms (cookies are sent to all, each platform's API ignores unknown cookies)
uv run opimon run "AI" --cookie 'z_c0="..."; SUB=_2AkM...'
```

> **Note:** Do not commit cookies to version control. The cookie value is only used in the current session and is not persisted to disk.

## CLI Reference

```bash
opimon [OPTIONS] COMMAND [ARGS]
```

| Option | Description |
|---|---|
| `--version` | Show version and exit |
| `--help` | Show help message |

### `opimon run KEYWORD`

Full pipeline: crawl → sentiment analysis → word cloud.

| Option | Default | Description |
|---|---|---|
| `-p, --platforms` | `zhihu,weibo` | Comma-separated list of platforms to crawl |
| `--pages` | `3` | Number of pages per platform |
| `-o, --output` | `./output` | Output directory |
| `--offline` | (flag) | Skip network, use cached data only |
| `--font` | (auto) | Path to a Chinese .ttf/.ttc font |
| `--cookie` | (none) | Browser cookie string for authenticated requests |

### `opimon crawl KEYWORD`

Fetch raw data only — saves `raw_{platform}.json` files. Same options as `run` minus `--font`.

### `opimon report -i PATH`

Load existing crawl data and run analysis + word cloud generation.

| Option | Required | Description |
|---|---|---|
| `-i, --input` | **Yes** | Path to a `raw_*.json` file or directory containing them |
| `-o, --output` | No | Output directory (default: `./output`) |
| `--font` | No | Path to a Chinese .ttf/.ttc font |

## Output Structure

Each `run` or `crawl` creates a timestamped directory under the output root:

```
output/20250630_105251_人工智能/
├── raw_zhihu.json           # Raw posts from Zhihu (Post objects)
├── raw_weibo.json           # Raw posts from Weibo (Post objects)
├── sentiment_report.json    # Sentiment distribution + per-post scores
└── wordcloud_人工智能.png   # Word cloud image (generated by run/report only)
```

### Sentiment report format

```json
{
  "keyword": "人工智能",
  "total_posts": 15,
  "positive_count": 5,
  "neutral_count": 7,
  "negative_count": 3,
  "positive_pct": "33%",
  "neutral_pct": "47%",
  "negative_pct": "20%",
  "avg_score": 0.512,
  "posts": [
    {
      "post_id": "123456",
      "title": "...",
      "sentiment_score": 0.78,
      "sentiment_label": "positive"
    }
  ]
}
```

## Running Tests

```bash
uv sync --dev
uv run pytest tests/ -v
```

44 tests across 7 test files, covering models, crawlers, NLP pipeline, and visualization.

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP client with session support |
| `beautifulsoup4` + `lxml` | HTML parsing (Zhihu SSR fallback) |
| `jieba` | Chinese word segmentation |
| `snownlp` | Chinese sentiment analysis (Naive Bayes, zero model download) |
| `wordcloud` | Word cloud image generation |
| `matplotlib` | WordCloud rendering backend |
| `click` | CLI framework |

## Notes & Limitations

- **Anti-bot measures:** Zhihu API v4 returns `HitLabels` challenge without a valid cookie. Weibo's mobile API redirects to `passport.weibo.com/sso/signin` when unauthenticated. Both give clear error messages directing you to use `--cookie`.
- **SnowNLP accuracy:** The model is pre-trained on e-commerce product reviews. Sentiment scores for news/social-media text may skew toward neutral — treat the classification as directional rather than definitive.
- **Rate limiting:** Crawlers use rotating User-Agent headers, random delays (1.5–3s), and exponential backoff on 429/5xx responses. However, sustained high-volume crawling may still trigger platform rate limits.
- **Weibo time parsing:** Supports relative timestamps (`X分钟前`, `X小时前`, `昨天`, `刚刚`) and absolute dates. Unix-timestamp-based posts may lose precision.
- **Font discovery:** Probes known paths for SimHei, Microsoft YaHei, PingFang, Noto Sans CJK, and WenQuanYi Micro Hei. Falls back to matplotlib's font manager. If all fail, a clear error message with OS-specific install instructions is printed.

## License

MIT
