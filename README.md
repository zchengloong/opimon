# opimon — 舆情监控爬虫

Public opinion monitoring CLI tool for Zhihu and Weibo. Crawl trending topics by keyword, perform Chinese sentiment analysis, and generate word cloud visualizations.

## Features

- **Multi-platform crawling** — Zhihu and Weibo, via their search APIs
- **Chinese sentiment analysis** — classify posts as positive / negative / neutral using SnowNLP
- **Word cloud generation** — visual word frequency charts with Chinese font support
- **Offline mode** — cache results and re-analyze without repeated network requests
- **Modular pipeline** — crawl, analyze, and visualize as separate steps or in one command

## Installation

```bash
# Clone and install
cd demo_proj
pip install -e .

# Optional: install a Chinese font (Linux)
sudo apt install fonts-wqy-microhei
```

## Quick Start

```bash
# Full pipeline — crawl, analyze, visualize
opimon run "人工智能"

# Single platform only
opimon run "芯片" -p zhihu --pages 5

# Crawl only (save raw data)
opimon crawl "新能源汽车" -p weibo

# Analyze existing data offline
opimon report -i ./output/20250630_120000_人工智能/

# Offline mode — re-analyze cached data without network
opimon run "人工智能" --offline

# Custom Chinese font
opimon run "数据科学" --font /path/to/SimHei.ttf
```

## Commands

| Command | Description |
|---|---|
| `opimon run KEYWORD` | Full pipeline: crawl → analyze → word cloud |
| `opimon crawl KEYWORD` | Fetch only, save raw JSON |
| `opimon report -i PATH` | Analyze existing JSON data |

## Output Structure

Each run creates a timestamped directory under `output/`:

```
output/20250630_120000_人工智能/
├── raw_zhihu.json           # Raw crawl data from Zhihu
├── raw_weibo.json           # Raw crawl data from Weibo
├── sentiment_report.json    # Sentiment analysis report
└── wordcloud_人工智能.png   # Word cloud image
```

## Running Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP client |
| `beautifulsoup4` + `lxml` | HTML parsing |
| `jieba` | Chinese word segmentation |
| `snownlp` | Chinese sentiment analysis |
| `wordcloud` | Word cloud generation |
| `matplotlib` | Rendering backend |
| `click` | CLI framework |

## Notes

- Web scraping may be blocked by platform anti-bot measures. Use `--offline` to work with cached data during development.
- SnowNLP's sentiment model is pre-trained on product reviews — accuracy may vary for news/social media text.
- A Chinese-capable font is required for word cloud generation. On headless Linux servers, install `fonts-wqy-microhei`.
