"""Parsers for arXiv RSS feeds and HTML list pages.

Atom feed parsing is handled by the `arxiv` library (arxiv.Result._from_feed_entry).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape
from typing import Any

import arxiv


# ── RSS feed parser (rss.arxiv.org/rss/{category}) ─────────────

def parse_rss_item(item: dict[str, Any]) -> arxiv.Result:
    """Parse a feedparser RSS item into an arxiv.Result."""
    link = item.get("link", "")
    entry_id = link  # RSS uses the abstract page link as ID

    title = _clean_text(item.get("title", "Untitled"))
    summary = _clean_text(item.get("description", ""))

    author_str = item.get("author", "")
    if author_str:
        author_names = [n.strip() for n in author_str.split(",") if n.strip()]
    else:
        author_names = []
    authors = [arxiv.Result.Author(name=n) for n in author_names] if author_names else [arxiv.Result.Author(name="Unknown")]

    categories: list[str] = []
    primary_category = ""
    for tag in item.get("tags", []):
        if isinstance(tag, dict):
            term = tag.get("term", "")
        else:
            term = str(tag)
        if term:
            categories.append(term)
    if categories:
        primary_category = categories[0]

    published = _parse_datetime(item.get("published", "")) or datetime.now(tz=timezone.utc)

    pdf_url = ""
    if link:
        pdf_url = re.sub(r"/abs/", "/pdf/", link)
        if not pdf_url.endswith(".pdf"):
            pdf_url += ".pdf"

    links = [arxiv.Result.Link(href=pdf_url, title="pdf")] if pdf_url else []

    return arxiv.Result(
        entry_id=entry_id,
        title=title,
        summary=summary,
        authors=authors,
        published=published,
        updated=published,
        primary_category=primary_category,
        categories=categories,
        links=links,
    )


# ── HTML list page parser (arxiv.org/list/{path}) ──────────────

def parse_list_page(html: str) -> list[arxiv.Result]:
    """Parse an arXiv list page (e.g., /list/cs/recent, /list/hep-th/2020-01).

    arXiv list pages use <dl> with <dt>/<dd> pairs for each paper.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    articles: list[arxiv.Result] = []

    dl = soup.find("dl")
    if not dl:
        dl = soup.find("dl", id="articles")
    if not dl:
        return articles

    dt_tags = dl.find_all("dt", recursive=False)
    dd_tags = dl.find_all("dd", recursive=False)

    for dt, dd in zip(dt_tags, dd_tags):
        try:
            article = _parse_list_entry(dt, dd)
            if article:
                articles.append(article)
        except Exception:
            continue

    return articles


def _parse_list_entry(dt, dd) -> arxiv.Result | None:
    """Parse a single <dt>/<dd> pair from an arXiv list page."""
    id_link = dt.find("a", href=re.compile(r"/abs/"))
    if not id_link:
        return None

    arxiv_id = id_link.text.strip().replace("arXiv:", "")
    entry_id = f"https://arxiv.org/abs/{arxiv_id}"

    # Title
    title_div = dd.find("div", class_="list-title")
    title = "Untitled"
    if title_div:
        desc_span = title_div.find("span", class_="descriptor")
        if desc_span:
            desc_span.decompose()
        title = _clean_text(title_div.get_text())

    # Authors
    authors_div = dd.find("div", class_="list-authors")
    if authors_div:
        author_links = authors_div.find_all("a")
        author_names = [_clean_text(a.text) for a in author_links if a.text.strip()]
    else:
        author_names = []
    authors = [arxiv.Result.Author(name=n) for n in author_names] if author_names else [arxiv.Result.Author(name="Unknown")]

    # Subjects / Categories
    subjects_div = dd.find("div", class_="list-subjects")
    categories: list[str] = []
    primary_category = ""
    if subjects_div:
        desc_span = subjects_div.find("span", class_="descriptor")
        if desc_span:
            desc_span.decompose()
        subjects_text = _clean_text(subjects_div.get_text())
        cats = re.findall(r"([a-z-]+(?:\.[A-Z][A-Za-z-]*)+)", subjects_text)
        categories = list(dict.fromkeys(cats))
        if categories:
            primary_category = categories[0]

    # Abstract
    abstract_p = dd.find("p", class_="mathjax")
    summary = _clean_text(abstract_p.get_text()) if abstract_p else ""

    # Comments (optional)
    comments_div = dd.find("div", class_="list-comments")
    comment = None
    if comments_div:
        desc_span = comments_div.find("span", class_="descriptor")
        if desc_span:
            desc_span.decompose()
        comment = _clean_text(comments_div.get_text()) or None

    # Journal ref (optional)
    jref_div = dd.find("div", class_="list-journal-ref")
    journal_ref = None
    if jref_div:
        desc_span = jref_div.find("span", class_="descriptor")
        if desc_span:
            desc_span.decompose()
        journal_ref = _clean_text(jref_div.get_text()) or None

    # PDF URL
    pdf_link = dt.find("a", href=re.compile(r"/pdf/"))
    pdf_url = f"https://arxiv.org{pdf_link['href']}" if pdf_link else f"https://arxiv.org/pdf/{arxiv_id}"

    links = [arxiv.Result.Link(href=pdf_url, title="pdf")]

    return arxiv.Result(
        entry_id=entry_id,
        title=title,
        summary=summary,
        authors=authors,
        published=datetime.now(tz=timezone.utc),
        updated=datetime.now(tz=timezone.utc),
        primary_category=primary_category,
        categories=categories,
        comment=comment or "",
        journal_ref=journal_ref or "",
        links=links,
    )


# ── Helpers ────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Clean text: unescape HTML entities, collapse whitespace."""
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_datetime(date_str: str) -> datetime | None:
    """Parse a datetime string in common arXiv/RSS formats."""
    if not date_str:
        return None

    # ISO 8601: 2021-07-20T17:59:59Z
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # RFC 2822 (RSS format): Tue, 20 Jul 2021 17:59:59 GMT
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        pass

    return None
