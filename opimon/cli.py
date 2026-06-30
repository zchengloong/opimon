"""CLI entry point — click command groups."""

from datetime import datetime
from pathlib import Path

import click

from opimon import __version__
from opimon.crawler import get_crawler
from opimon.models import CrawlConfig, Post
from opimon.nlp import ChineseSegmenter, SentimentAnalyzer
from opimon.utils import ensure_output_dir, load_json, save_json


def _clean_keyword(keyword: str) -> str:
    """Strip surrogate characters and control chars from *keyword*.

    Some terminal / shell combos can corrupt multibyte input into lone
    surrogates that crash the UTF-8 encoder downstream.
    """
    return keyword.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="replace").replace("�", "").strip()
from opimon.visualize import WordCloudGenerator


# ── Shared options ───────────────────────────────────────────────────


def _platform_option(f):
    """Decorator for the --platforms / -p option."""
    return click.option(
        "-p",
        "--platforms",
        default="zhihu,weibo",
        help="Comma-separated platforms to crawl (zhihu, weibo)",
    )(f)


def _pages_option(f):
    return click.option(
        "--pages",
        default=3,
        type=int,
        help="Number of pages to crawl per platform",
    )(f)


def _output_option(f):
    return click.option(
        "-o",
        "--output",
        default="./output",
        help="Output directory for results",
    )(f)


def _offline_option(f):
    return click.option(
        "--offline",
        is_flag=True,
        help="Use cached data — skip all network requests",
    )(f)


def _font_option(f):
    return click.option(
        "--font",
        default=None,
        help="Path to a Chinese TrueType font file (.ttf / .ttc)",
    )(f)


def _cookie_option(f):
    return click.option(
        "--cookie",
        default=None,
        help="Browser cookie string for authenticated requests (bypass anti-bot walls)",
    )(f)


# ── Helper: build run directory ──────────────────────────────────────


def _make_run_dir(output_base: str, keyword: str) -> Path:
    """Create ``output_base/{timestamp}_{keyword}/`` and return its path."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = keyword.replace("/", "_").replace(" ", "_")[:30]
    run_dir = Path(output_base) / f"{ts}_{safe_keyword}"
    return ensure_output_dir(run_dir)


# ── Core pipeline functions ──────────────────────────────────────────


def _do_crawl(config: CrawlConfig, run_dir: Path) -> list[Post]:
    """Run crawlers for all requested platforms.

    Saves ``raw_{platform}.json`` to *run_dir*.
    Returns combined list of all Post objects.
    """
    all_posts: list[Post] = []

    for platform in config.platforms:
        click.echo(f"\n{'='*50}")
        click.echo(f"  Crawling {platform.upper()} for: {config.keyword}")
        click.echo(f"{'='*50}")

        crawler_cls = get_crawler(platform)
        crawler = crawler_cls(config)

        try:
            result = crawler.fetch()
        except Exception as e:
            click.echo(f"  [Error] Crawler crashed: {e}", err=True)
            continue

        # Save raw data
        if result.posts:
            raw_path = run_dir / f"raw_{platform}.json"
            save_json(result.to_dict(), raw_path)
            click.echo(f"  ✓ Saved {len(result.posts)} posts to {raw_path}")

        if result.errors:
            for err in result.errors:
                click.echo(f"  ⚠ {err}", err=True)

        all_posts.extend(result.posts)

    click.echo(f"\n  Total posts crawled: {len(all_posts)}")
    return all_posts


def _do_analyze(posts: list[Post], keyword: str, run_dir: Path) -> dict:
    """Run sentiment analysis and word segmentation.

    Saves ``sentiment_report.json`` to *run_dir*.
    Returns the sentiment report as a dict.
    """
    if not posts:
        click.echo("  No posts to analyze.", err=True)
        return {}

    click.echo(f"\n{'='*50}")
    click.echo("  Sentiment Analysis")
    click.echo(f"{'='*50}")

    analyzer = SentimentAnalyzer()
    report = analyzer.generate_report(posts)
    report.keyword = keyword

    report_dict = report.to_dict()

    # Save report
    report_path = run_dir / "sentiment_report.json"
    save_json(report_dict, report_path)
    click.echo(f"  ✓ Saved sentiment report to {report_path}")

    return report_dict


def _do_wordcloud(posts: list[Post], keyword: str, run_dir: Path, font_path: str | None) -> Path | None:
    """Generate word cloud from all post texts.

    Returns the path to the generated PNG, or None on failure.
    """
    if not posts:
        click.echo("  No posts for word cloud generation.", err=True)
        return None

    click.echo(f"\n{'='*50}")
    click.echo("  Word Cloud Generation")
    click.echo(f"{'='*50}")

    # Segment
    segmenter = ChineseSegmenter()
    all_texts = [p.full_text for p in posts]
    freqs = segmenter.compute_frequencies(all_texts)

    if not freqs:
        click.echo("  No words extracted — skipping word cloud.", err=True)
        return None

    click.echo(f"  Unique words after filtering: {len(freqs)}")
    click.echo(f"  Top 10: {', '.join(list(freqs.keys())[:10])}")

    # Generate word cloud
    try:
        generator = WordCloudGenerator(font_path=font_path)
    except FileNotFoundError as e:
        click.echo(f"\n  ✗ {e}", err=True)
        return None

    output_path = run_dir / f"wordcloud_{keyword}.png"
    generator.generate(freqs, output_path)
    click.echo(f"  ✓ Word cloud saved to {output_path}")

    return output_path


def _print_summary(report: dict, wc_path: Path | None, run_dir: Path) -> None:
    """Print a pretty summary to the console."""
    click.echo(f"\n{'='*50}")
    click.echo("  RESULTS SUMMARY")
    click.echo(f"{'='*50}")

    if not report:
        click.echo("  No results to display.")
        return

    click.echo(f"  关键词:       {report.get('keyword', 'N/A')}")
    click.echo(f"  总帖子数:     {report.get('total_posts', 0)}")
    click.echo(f"  情感分布:")
    click.echo(f"    正面: {report.get('positive_count', 0)} ({report.get('positive_pct', 0)}%)")
    click.echo(f"    中性: {report.get('neutral_count', 0)} ({report.get('neutral_pct', 0)}%)")
    click.echo(f"    负面: {report.get('negative_count', 0)} ({report.get('negative_pct', 0)}%)")
    click.echo(f"  平均情感得分: {report.get('avg_score', 0):.3f}")

    if wc_path:
        click.echo(f"  词云图:       {wc_path}")
    click.echo(f"  输出目录:     {run_dir}")
    click.echo(f"{'='*50}\n")


# ── CLI group ────────────────────────────────────────────────────────


@click.group()
@click.version_option(__version__, prog_name="opimon")
def cli():
    """opimon — 舆情监控爬虫 (Public Opinion Monitor)

    Crawl trending topics from Zhihu and Weibo by keyword,
    analyze sentiment, and generate word cloud visualizations.

    \b
    Examples:
      opimon run "人工智能"
      opimon run "芯片" -p zhihu --pages 5
      opimon crawl "新能源" -p weibo
      opimon report -i ./output/raw_zhihu.json
      opimon run "测试" --offline
    """


# ── "run" subcommand ─────────────────────────────────────────────────


@cli.command()
@click.argument("keyword")
@_platform_option
@_pages_option
@_output_option
@_offline_option
@_font_option
@_cookie_option
def run(
    keyword: str,
    platforms: str,
    pages: int,
    output: str,
    offline: bool,
    font: str | None,
    cookie: str | None,
):
    """Full pipeline: crawl → analyze → visualize.

    Crawls Zhihu and/or Weibo for KEYWORD, performs sentiment
    analysis on the results, and generates a word cloud image.
    """
    keyword = _clean_keyword(keyword)
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]
    run_dir = _make_run_dir(output, keyword)

    config = CrawlConfig(
        keyword=keyword,
        platforms=platform_list,
        max_pages=pages,
        offline=offline,
        cache_dir=str(run_dir),
        cookie=cookie or "",
    )

    click.echo(f"🔍 opimon v{__version__}")
    click.echo(f"   Keyword:    {keyword}")
    click.echo(f"   Platforms:  {', '.join(platform_list)}")
    click.echo(f"   Max pages:  {pages}")
    click.echo(f"   Offline:    {offline}")
    click.echo(f"   Output:     {run_dir}")

    # Phase 1: Crawl
    posts = _do_crawl(config, run_dir)

    if not posts:
        click.echo("\n  No posts found. Try a different keyword or platform.", err=True)
        return

    # Phase 2: Analyze
    report = _do_analyze(posts, keyword, run_dir)

    # Phase 3: Visualize
    wc_path = _do_wordcloud(posts, keyword, run_dir, font)

    # Print summary
    _print_summary(report, wc_path, run_dir)


# ── "crawl" subcommand ───────────────────────────────────────────────


@cli.command()
@click.argument("keyword")
@_platform_option
@_pages_option
@_output_option
@_offline_option
@_cookie_option
def crawl(
    keyword: str,
    platforms: str,
    pages: int,
    output: str,
    offline: bool,
    cookie: str | None,
):
    """Crawl data only — save raw JSON without analysis.

    Useful for collecting data first and analyzing later with
    the 'report' subcommand, or for avoiding repeated requests
    while experimenting with analysis parameters.
    """
    keyword = _clean_keyword(keyword)
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]
    run_dir = _make_run_dir(output, keyword)

    config = CrawlConfig(
        keyword=keyword,
        platforms=platform_list,
        max_pages=pages,
        offline=offline,
        cache_dir=str(run_dir),
        cookie=cookie or "",
    )

    click.echo(f"📥 Crawling: {keyword} from {', '.join(platform_list)}")
    posts = _do_crawl(config, run_dir)

    if not posts:
        click.echo("\n  No posts found. Try a different keyword or platform.", err=True)
        return

    click.echo(f"\n  Done. Saved to {run_dir}")
    click.echo(f"  Re-analyze later with: opimon report -i {run_dir}")


# ── "report" subcommand ──────────────────────────────────────────────


@cli.command()
@click.option(
    "-i",
    "--input",
    "input_path",
    required=True,
    help="Path to a raw_{platform}.json file, or a directory containing them",
)
@click.option("-o", "--output", default="./output", help="Output directory")
@_font_option
def report(input_path: str, output: str, font: str | None):
    """Analyze existing crawl data and generate report + word cloud.

    Loads previously crawled data (JSON) and runs sentiment
    analysis + word cloud generation on it.
    """
    input_p = Path(input_path)
    all_posts: list[Post] = []

    # Determine keyword from data
    keyword = ""

    if input_p.is_dir():
        # Load all raw_*.json files in the directory
        json_files = sorted(input_p.glob("raw_*.json"))
        if not json_files:
            raise click.BadParameter(
                f"No raw_*.json files found in '{input_path}'. "
                f"Run 'opimon crawl' first."
            )
        for jf in json_files:
            data = load_json(jf)
            keyword = data.get("keyword", keyword) or keyword
            for p_data in data.get("posts", []):
                all_posts.append(Post(**p_data))
        run_dir = input_p
    else:
        # Single file
        data = load_json(input_p)
        keyword = data.get("keyword", "")
        for p_data in data.get("posts", []):
            all_posts.append(Post(**p_data))
        run_dir = ensure_output_dir(output)

    if not all_posts:
        click.echo("No posts found in input data.", err=True)
        return

    click.echo(f"📊 Analyzing {len(all_posts)} posts …")

    # Analyze
    report = _do_analyze(all_posts, keyword, run_dir)

    # Word cloud
    wc_path = _do_wordcloud(all_posts, keyword, run_dir, font)

    # Summary
    _print_summary(report, wc_path, run_dir)
