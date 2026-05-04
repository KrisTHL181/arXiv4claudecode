"""arXiv CLI — Click command tree."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime

import click

from arxiv_cli import __version__
from arxiv_cli.categories import (
    get_all_groups,
    get_group,
    is_valid_category,
)
from arxiv_cli.client import (
    ArxivClient,
    ArxivCliError,
    DateParseError,
    DownloadError,
)
from arxiv_cli.formatter import Formatter


# ── Date parsing helpers ────────────────────────────────────

_MONTHS: dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_catchup_date(date_str: str) -> datetime:
    """Parse a catch-up date string in multiple formats.

    Accepted: 'DD Month YYYY' (e.g., '15 April 2025'), 'YYYY-MM-DD'
    """
    date_str = date_str.strip()

    # Try YYYY-MM-DD first
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass

    # Try DD Month YYYY
    parts = date_str.split()
    if len(parts) == 3:
        try:
            day = int(parts[0])
            month_name = parts[1].lower()
            year = int(parts[2])
            month = _MONTHS.get(month_name)
            if month and 1 <= day <= 31:
                return datetime(year, month, min(day, 28))
        except (ValueError, KeyError):
            pass

    raise DateParseError(
        f"Invalid date: '{date_str}'. "
        "Use 'DD Month YYYY' (e.g., '15 April 2025') or 'YYYY-MM-DD'."
    )


def _comma_sep_categories(ctx, param, value):
    """Click callback that expands comma-separated category lists."""
    if not value:
        return []
    result = []
    for v in value:
        result.extend(v.split(","))
    return [r.strip() for r in result if r.strip()]


# ── Helpers ──────────────────────────────────────────────────

def _output_options(func):
    """Decorator: add --json and --plain output format options to a command."""
    func = click.option(
        "--json", "output_format",
        flag_value="json", default=None,
        help="Output in JSON format.",
    )(func)
    func = click.option(
        "--plain", "output_format",
        flag_value="plain",
        help="Output in plain text format.",
    )(func)
    return func


def _apply_output_format(ctx, output_format):
    """Apply command-level output format override if given."""
    if output_format:
        ctx.obj["fmt"].style = output_format


# ── CLI group ────────────────────────────────────────────────

@click.group()
@click.option(
    "--json", "output_format",
    flag_value="json", default=None,
    help="Output in JSON format.",
)
@click.option(
    "--plain", "output_format",
    flag_value="plain",
    help="Output in plain text format.",
)
@click.option(
    "--no-abstracts", "show_abstracts",
    flag_value=False, default=True,
    help="Hide paper abstracts in output.",
)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, output_format, show_abstracts):
    """arXiv CLI — Browse, search, and download papers from arxiv.org."""
    ctx.ensure_object(dict)
    ctx.obj["fmt"] = Formatter(style=output_format or "rich")
    ctx.obj["client"] = ArxivClient()
    ctx.obj["show_abstracts"] = show_abstracts


# ── Browse group ─────────────────────────────────────────────

@cli.group()
def browse():
    """Browse recent arXiv listings."""


@browse.command("new")
@click.argument("category", default="cs", required=False)
@_output_options
@click.pass_context
def browse_new(ctx, category, output_format):
    """Most recent mailing (RSS feed, always shows abstracts).

    CATEGORY: arXiv category ID (default: cs).
    """
    _apply_output_format(ctx, output_format)
    client: ArxivClient = ctx.obj["client"]
    fmt: Formatter = ctx.obj["fmt"]

    _warn_if_invalid_category(category)

    try:
        articles = client.fetch_rss(category)
        fmt.print_articles(articles, show_abstracts=True)
    except ArxivCliError as e:
        fmt.print_error(str(e))
        raise SystemExit(1)


@browse.command("recent")
@click.argument("category", default="cs", required=False)
@click.option("--max-results", "-n", default=0, help="Limit results (0 = all).")
@_output_options
@click.pass_context
def browse_recent(ctx, category, max_results, output_format):
    """Last 5 mailings for a category.

    CATEGORY: arXiv category ID (default: cs).
    """
    _apply_output_format(ctx, output_format)
    client: ArxivClient = ctx.obj["client"]
    fmt: Formatter = ctx.obj["fmt"]

    _warn_if_invalid_category(category)

    try:
        articles = client.fetch_list_page(f"{category}/recent")
        if max_results and max_results > 0:
            articles = articles[:max_results]
        fmt.print_articles(articles, show_abstracts=ctx.obj["show_abstracts"])
    except ArxivCliError as e:
        fmt.print_error(str(e))
        raise SystemExit(1)


@browse.command("current")
@click.argument("category", default="cs", required=False)
@click.option("--max-results", "-n", default=0, help="Limit results (0 = all).")
@_output_options
@click.pass_context
def browse_current(ctx, category, max_results, output_format):
    """Current month's listings.

    CATEGORY: arXiv category ID (default: cs).
    """
    _apply_output_format(ctx, output_format)
    client: ArxivClient = ctx.obj["client"]
    fmt: Formatter = ctx.obj["fmt"]

    _warn_if_invalid_category(category)

    now = datetime.now()
    path = f"{category}/{now.year}-{now.month:02d}"

    try:
        articles = client.fetch_list_page(path)
        if max_results and max_results > 0:
            articles = articles[:max_results]
        fmt.print_articles(articles, show_abstracts=ctx.obj["show_abstracts"])
    except ArxivCliError as e:
        fmt.print_error(str(e))
        raise SystemExit(1)


@browse.command("month")
@click.argument("year", type=int)
@click.argument("month", type=int)
@click.argument("category", default="cs", required=False)
@click.option("--max-results", "-n", default=0, help="Limit results (0 = all).")
@_output_options
@click.pass_context
def browse_month(ctx, year, month, category, max_results, output_format):
    """Specific year/month listings.

    YEAR: e.g., 2025
    MONTH: 1-12
    CATEGORY: arXiv category ID (default: cs).
    """
    _apply_output_format(ctx, output_format)
    client: ArxivClient = ctx.obj["client"]
    fmt: Formatter = ctx.obj["fmt"]

    if not (1 <= month <= 12):
        fmt.print_error("Month must be between 1 and 12.")
        raise SystemExit(1)

    _warn_if_invalid_category(category)

    path = f"{category}/{year}-{month:02d}"

    try:
        articles = client.fetch_list_page(path)
        if max_results and max_results > 0:
            articles = articles[:max_results]
        fmt.print_articles(articles, show_abstracts=ctx.obj["show_abstracts"])
    except ArxivCliError as e:
        fmt.print_error(str(e))
        raise SystemExit(1)


# ── Catch-up command ─────────────────────────────────────────

@cli.command("catch-up")
@click.argument("since", type=str)
@click.option(
    "--category", "-c", "categories",
    multiple=True, callback=_comma_sep_categories,
    help="Filter by category (repeatable, comma-separated).",
)
@click.option("--max-results", "-n", default=200, help="Maximum results.")
@_output_options
@click.pass_context
def catch_up(ctx, since, categories, max_results, output_format):
    """Papers since a date. Use 'DD Month YYYY' (e.g. '15 April 2025') or 'YYYY-MM-DD'."""
    _apply_output_format(ctx, output_format)
    client: ArxivClient = ctx.obj["client"]
    fmt: Formatter = ctx.obj["fmt"]

    try:
        date = _parse_catchup_date(since)
    except DateParseError as e:
        fmt.print_error(str(e))
        raise SystemExit(1) from e

    for cat in categories:
        _warn_if_invalid_category(cat)

    start = date.strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")

    try:
        articles = client.search_by_date(
            start_date=start,
            end_date=end,
            categories=list(categories) or None,
            max_results=max_results,
        )
        fmt.print_articles(articles, show_abstracts=ctx.obj["show_abstracts"])
    except ArxivCliError as e:
        fmt.print_error(str(e))
        raise SystemExit(1)


# ── Search command ───────────────────────────────────────────

@cli.command("search")
@click.argument("query", type=str)
@click.option(
    "--category", "-c", "categories",
    multiple=True, callback=_comma_sep_categories,
    help="Filter by category (repeatable, comma-separated).",
)
@click.option("--max-results", "-n", default=50, help="Maximum results.")
@click.option(
    "--sort-by",
    type=click.Choice(["relevance", "submittedDate", "submitted", "updated", "lastUpdatedDate"]),
    default="relevance",
    help="Sort field.",
)
@click.option(
    "--sort-order",
    type=click.Choice(["asc", "desc"]),
    default="desc",
    help="Sort direction.",
)
@_output_options
@click.pass_context
def search(ctx, query, categories, max_results, sort_by, sort_order, output_format):
    """Search within the arXiv archive.

    QUERY: Search terms (supports field prefixes: ti:, au:, abs:, all:, cat:).
    """
    _apply_output_format(ctx, output_format)
    client: ArxivClient = ctx.obj["client"]
    fmt: Formatter = ctx.obj["fmt"]

    for cat in categories:
        _warn_if_invalid_category(cat)

    sort_map = {
        "relevance": "relevance",
        "submitted": "submittedDate",
        "submittedDate": "submittedDate",
        "updated": "lastUpdatedDate",
        "lastUpdatedDate": "lastUpdatedDate",
    }
    order_map = {"asc": "ascending", "desc": "descending"}

    try:
        articles = client.search(
            query=query,
            categories=list(categories) or None,
            max_results=max_results,
            sort_by=sort_map[sort_by],
            sort_order=order_map[sort_order],
        )
        fmt.print_articles(articles, show_abstracts=ctx.obj["show_abstracts"])
    except ArxivCliError as e:
        fmt.print_error(str(e))
        raise SystemExit(1)


# ── Stats command ────────────────────────────────────────────

@cli.command("stats")
@click.option("--year", "-y", type=int, help="Filter by year.")
@click.option("--category", "-c", "category_id", help="Filter by category.")
@click.option("--refresh", is_flag=True, help="Try to fetch live stats from arXiv.")
@_output_options
@click.pass_context
def stats(ctx, year, category_id, refresh, output_format):
    """Article submission statistics by year and category."""
    from arxiv_cli.stats import load_stats

    _apply_output_format(ctx, output_format)
    fmt: Formatter = ctx.obj["fmt"]

    try:
        data = load_stats(refresh=refresh)
        fmt.print_stats(data, year=year, category=category_id)
    except ArxivCliError as e:
        fmt.print_error(str(e))
        raise SystemExit(1)


# ── Download command ─────────────────────────────────────────

@cli.command("download")
@click.argument("paper_id", type=str)
@click.option(
    "--format", "-f", "fmt_type",
    type=click.Choice(["pdf", "src", "html", "eprint"]),
    default="pdf",
    help="Download format: pdf (default), src (LaTeX), html, or eprint.",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=".",
    help="Output directory.",
)
@click.option("--filename", type=str, help="Custom output filename.")
@_output_options
@click.pass_context
def download(ctx, paper_id, fmt_type, output, filename, output_format):
    """Download a paper from arXiv.

    PAPER_ID: arXiv paper ID (e.g., '2107.05580', '2107.05580v1').
    """
    _apply_output_format(ctx, output_format)
    client: ArxivClient = ctx.obj["client"]
    fmt: Formatter = ctx.obj["fmt"]

    urls = {
        "pdf": f"https://arxiv.org/pdf/{paper_id}.pdf",
        "src": f"https://arxiv.org/src/{paper_id}",
        "html": f"https://arxiv.org/html/{paper_id}",
        "eprint": f"https://arxiv.org/e-print/{paper_id}",
    }
    exts = {
        "pdf": ".pdf",
        "src": ".tar.gz",
        "html": ".html",
        "eprint": ".tar.gz",
    }

    url = urls[fmt_type]
    safe_id = re.sub(r"[/\\]", "_", paper_id)
    fname = filename or f"{safe_id}{exts[fmt_type]}"
    path = os.path.join(output, fname)

    try:
        result = client.download_file(url, path)
        fmt.print_download_result(result)
    except DownloadError as e:
        fmt.print_error(str(e))
        raise SystemExit(1)


# ── HTML to Markdown command ─────────────────────────────────

@cli.command("html2md")
@click.argument("input", type=str)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Output Markdown file path (prints to stdout if omitted).",
)
@click.option(
    "--timeout", type=int, default=300,
    help="Timeout in seconds for ar5ivist LaTeX conversion (default: 300).",
)
@_output_options
@click.pass_context
def html2md(ctx, input, output, output_format, timeout):
    """Convert an arXiv paper to Markdown.

    INPUT: arXiv paper ID (e.g., '2107.05580') or path to a local HTML file.

    For paper IDs, the conversion tries these in order:
      1. arXiv native HTML (arxiv.org/html/{id})
      2. LaTeX source via ar5ivist (Docker or local)
      3. Raw LaTeX source as a code block
    """
    _apply_output_format(ctx, output_format)
    client: ArxivClient = ctx.obj["client"]
    fmt: Formatter = ctx.obj["fmt"]

    from arxiv_cli.converter import convert_html_to_markdown

    is_file = os.path.exists(input) or input.endswith(".html") or input.endswith(".htm")

    if is_file:
        try:
            with open(input, "r", encoding="utf-8") as f:
                html = f.read()
        except OSError as e:
            fmt.print_error(f"Cannot read file '{input}': {e}")
            raise SystemExit(1)

        try:
            md = convert_html_to_markdown(html)
        except Exception as e:
            fmt.print_error(f"Conversion failed: {e}")
            raise SystemExit(1)

        _write_md_output(md, output, fmt)
        return

    # ── arXiv paper ID path ──────────────────────────────────
    paper_id = input

    # Phase 1: Try native arXiv HTML
    html = _fetch_arxiv_html(paper_id, client)
    if html is not None:
        try:
            md = convert_html_to_markdown(html)
            _write_md_output(md, output, fmt)
            return
        except Exception as e:
            fmt.print_error(f"HTML conversion failed: {e}")

    # Phase 2: Try ar5ivist pipeline (Docker → local)
    if _try_ar5ivist_pipeline(paper_id, client, fmt, output, timeout):
        return

    # Phase 3: Ultimate fallback — raw LaTeX source
    _output_raw_latex(paper_id, client, fmt, output)


def _fetch_arxiv_html(paper_id: str, client: ArxivClient) -> str | None:
    """Fetch HTML from arxiv.org/html/{id}. Returns None on 404."""
    import requests as _requests

    url = f"https://arxiv.org/html/{paper_id}"
    try:
        resp = client._session.get(url, timeout=30)  # noqa: SLF001
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.text
    except _requests.RequestException:
        return None


def _try_ar5ivist_pipeline(
    paper_id: str,
    client: ArxivClient,
    fmt: Formatter,
    output: str | None,
    timeout: int,
) -> bool:
    """Attempt ar5ivist conversion. Returns True on success."""
    from arxiv_cli.ar5ivist import (
        Ar5ivistNotFoundError,
        LaTeXConversionError,
        SourceExtractionError,
        tex_to_html,
    )
    from arxiv_cli.converter import convert_html_to_markdown, extract_generic_html

    temp_dir = tempfile.mkdtemp(prefix="arxiv_ar5ivist_")
    try:
        html = tex_to_html(
            paper_id, client, temp_dir,
            timeout=timeout,
        )

        md = convert_html_to_markdown(html)

        # If LaTeXML converter produced nothing useful, try generic extraction
        if not md or md.startswith("Error:"):
            md = extract_generic_html(html)

        _write_md_output(md, output, fmt)
        return True

    except Ar5ivistNotFoundError:
        click.echo(
            "ar5ivist not available — falling back to raw LaTeX source.", err=True,
        )
    except SourceExtractionError as e:
        click.echo(f"Source download failed: {e}", err=True)
    except LaTeXConversionError as e:
        click.echo(f"ar5ivist conversion failed: {e}", err=True)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return False


def _output_raw_latex(
    paper_id: str,
    client: ArxivClient,
    fmt: Formatter,
    output: str | None,
) -> None:
    """Last resort: download LaTeX source and output as a code block."""
    from arxiv_cli.ar5ivist import download_and_extract_source, SourceExtractionError

    temp_dir = tempfile.mkdtemp(prefix="arxiv_latex_")
    try:
        tex_path = download_and_extract_source(paper_id, client, temp_dir)
        with open(tex_path, "r", encoding="utf-8", errors="replace") as f:
            tex_content = f.read()

        md = (
            f"# LaTeX Source: {paper_id}\n\n"
            f"> _This paper has no HTML version. Showing raw LaTeX source._\n\n"
            f"```latex\n{tex_content}\n```\n"
        )
        _write_md_output(md, output, fmt)

    except SourceExtractionError as e:
        fmt.print_error(f"All conversion methods failed for {paper_id}: {e}")
        raise SystemExit(1)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _write_md_output(md: str, output: str | None, fmt: Formatter) -> None:
    """Write Markdown to file or stdout."""
    if output:
        try:
            with open(output, "w", encoding="utf-8") as f:
                f.write(md)
            fmt.print_download_result(output)
        except OSError as e:
            fmt.print_error(f"Cannot write to '{output}': {e}")
            raise SystemExit(1)
    else:
        click.echo(md)


# ── Categories command ───────────────────────────────────────

@cli.command("categories")
@click.option(
    "--group", "-g",
    help="Filter by group (cs, math, physics, econ, eess, q-bio, q-fin, stat).",
)
@_output_options
@click.pass_context
def categories(ctx, group, output_format):
    """List arXiv categories organized by group."""
    _apply_output_format(ctx, output_format)
    fmt: Formatter = ctx.obj["fmt"]

    if group:
        g = get_group(group)
        if not g:
            fmt.print_error(
                f"Unknown group: '{group}'. "
                f"Available: cs, math, physics, econ, eess, q-bio, q-fin, stat"
            )
            raise SystemExit(1)
        groups = [g]
    else:
        groups = get_all_groups()

    fmt.print_categories(groups)


# ── Helpers ──────────────────────────────────────────────────

def _warn_if_invalid_category(cat: str) -> None:
    """Print a warning if a category ID is not recognized, but don't block."""
    if not is_valid_category(cat):
        # Check if it's a top-level group — those work for RSS
        if cat in {g.id for g in get_all_groups()}:
            return
        click.echo(
            f"Warning: '{cat}' is not a recognized arXiv category. "
            f"Proceeding anyway...",
            err=True,
        )


# ── Entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    cli()
