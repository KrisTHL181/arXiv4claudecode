"""Parsers for arXiv Atom feeds, RSS feeds, and HTML list pages."""

from __future__ import annotations

import re
from datetime import datetime
from html import unescape

from arxiv_cli.models import ArxivArticle, Author


# ── Atom feed parser (export.arxiv.org/api/query) ──────────────

def parse_atom_entry(entry: dict) -> ArxivArticle:
    """Parse a feedparser Atom entry into an ArxivArticle."""
    # ID and URLs
    entry_id = entry.get("id", "")

    pdf_url = ""
    for link in entry.get("links", []):
        if link.get("title") == "pdf":
            pdf_url = link.get("href", "")
            break

    # Title
    title = _clean_text(entry.get("title", "Untitled"))

    # Abstract
    summary = _clean_text(entry.get("summary", ""))

    # Authors
    authors = [Author(name=a.get("name", "Unknown")) for a in entry.get("authors", [])]

    # Dates
    published = _parse_datetime(entry.get("published", ""))
    updated = _parse_datetime(entry.get("updated", "")) or published

    # Categories
    categories = []
    primary_category = ""
    for tag in entry.get("tags", []):
        if tag.get("scheme") == "http://arxiv.org/schemas/atom":
            cat_id = tag.get("term", "")
            if cat_id:
                categories.append(cat_id)

    # arXiv primary_category extension
    arxiv_primary = entry.get("arxiv_primary_category", {})
    primary_category = arxiv_primary.get("term", categories[0] if categories else "")

    # Optional fields
    comment = entry.get("arxiv_comment", None)
    journal_ref = entry.get("arxiv_journal_ref", None)
    doi = entry.get("arxiv_doi", None)

    return ArxivArticle(
        entry_id=entry_id,
        title=title,
        summary=summary,
        authors=authors,
        published=published,
        updated=updated,
        primary_category=primary_category,
        categories=categories,
        comment=comment,
        journal_ref=journal_ref,
        doi=doi,
        pdf_url=pdf_url,
    )


# ── RSS feed parser (rss.arxiv.org/rss/{category}) ─────────────

def parse_rss_item(item: dict) -> ArxivArticle:
    """Parse a feedparser RSS item into an ArxivArticle."""
    link = item.get("link", "")
    entry_id = link  # RSS uses the abstract page link as ID

    title = _clean_text(item.get("title", "Untitled"))
    summary = _clean_text(item.get("description", ""))

    # RSS author may be comma-separated or a single name
    author_str = item.get("author", "")
    if author_str:
        author_names = [n.strip() for n in author_str.split(",") if n.strip()]
    else:
        author_names = []
    authors = [Author(name=n) for n in author_names] if author_names else [Author(name="Unknown")]

    # Categories from RSS tags
    categories = []
    primary_category = ""
    for tag in item.get("tags", []):
        # RSS tags may use 'term' or just be a string
        if isinstance(tag, dict):
            term = tag.get("term", "")
        else:
            term = str(tag)
        if term:
            categories.append(term)
    if categories:
        primary_category = categories[0]

    # Publication date
    published = _parse_datetime(item.get("published", "")) or datetime.now()

    # PDF URL derived from abstract link
    pdf_url = ""
    if link:
        pdf_url = re.sub(r"/abs/", "/pdf/", link)
        if not pdf_url.endswith(".pdf"):
            pdf_url += ".pdf"

    # Extract arXiv ID from the link
    if not entry_id and link:
        entry_id = link

    return ArxivArticle(
        entry_id=entry_id,
        title=title,
        summary=summary,
        authors=authors,
        published=published,
        updated=published,
        primary_category=primary_category,
        categories=categories,
        pdf_url=pdf_url,
    )


# ── HTML list page parser (arxiv.org/list/{path}) ──────────────

def parse_list_page(html: str) -> list[ArxivArticle]:
    """Parse an arXiv list page (e.g., /list/cs/recent, /list/hep-th/2020-01).

    arXiv list pages use <dl> with <dt>/<dd> pairs for each paper:
    - <dt> contains the arXiv ID link and title
    - <dd> contains authors, comments, journal ref, abstract, subjects
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    articles: list[ArxivArticle] = []

    # Find the main content <dl>
    dl = soup.find("dl")
    if not dl:
        dl = soup.find("dl", id="articles")
    if not dl:
        return articles

    # Collect dt/dd pairs
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


def _parse_list_entry(dt, dd) -> ArxivArticle | None:
    """Parse a single <dt>/<dd> pair from an arXiv list page.

    <dt> contains the arXiv ID link and format links.
    <dd> contains title, authors, subjects, abstract.
    """
    # Extract arXiv ID from <dt> — the link with href="/abs/..."
    id_link = dt.find("a", href=re.compile(r"/abs/"))
    if not id_link:
        return None

    arxiv_id = id_link.text.strip().replace("arXiv:", "")
    entry_id = f"https://arxiv.org/abs/{arxiv_id}"

    # Title — in <dd> <div class="list-title mathjax">, after a <span class="descriptor">Title:</span>
    title_div = dd.find("div", class_="list-title")
    title = "Untitled"
    if title_div:
        # Remove the "Title:" descriptor span
        desc_span = title_div.find("span", class_="descriptor")
        if desc_span:
            desc_span.decompose()
        title = _clean_text(title_div.get_text())

    # Authors — <a> tags inside <div class="list-authors">
    authors_div = dd.find("div", class_="list-authors")
    if authors_div:
        author_links = authors_div.find_all("a")
        author_names = [_clean_text(a.text) for a in author_links if a.text.strip()]
    else:
        author_names = []
    authors = [Author(name=n) for n in author_names] if author_names else [Author(name="Unknown")]

    # Subjects / Categories — <div class="list-subjects">
    subjects_div = dd.find("div", class_="list-subjects")
    categories: list[str] = []
    primary_category = ""
    if subjects_div:
        desc_span = subjects_div.find("span", class_="descriptor")
        if desc_span:
            desc_span.decompose()
        subjects_text = _clean_text(subjects_div.get_text())
        # Matches patterns like "cs.AI", "math.NT (Primary)", eess.IV
        cats = re.findall(r"([a-z-]+(?:\.[A-Z][A-Za-z-]*)+)", subjects_text)
        categories = list(dict.fromkeys(cats))  # dedup, preserve order
        if categories:
            primary_category = categories[0]

    # Abstract — <p class="mathjax">
    abstract_p = dd.find("p", class_="mathjax")
    summary = _clean_text(abstract_p.get_text()) if abstract_p else ""

    # Comments — <div class="list-comments"> (optional)
    comments_div = dd.find("div", class_="list-comments")
    comment = None
    if comments_div:
        desc_span = comments_div.find("span", class_="descriptor")
        if desc_span:
            desc_span.decompose()
        comment = _clean_text(comments_div.get_text()) or None

    # Journal ref — <div class="list-journal-ref"> (optional)
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

    published = datetime.now()

    return ArxivArticle(
        entry_id=entry_id,
        title=title,
        summary=summary,
        authors=authors,
        published=published,
        updated=published,
        primary_category=primary_category,
        categories=categories,
        comment=comment,
        journal_ref=journal_ref,
        pdf_url=pdf_url,
    )


# ── Helpers ────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Clean text: unescape HTML entities, collapse whitespace."""
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_datetime(date_str: str) -> datetime | None:
    """Parse a datetime string in common arXiv formats."""
    if not date_str:
        return None

    # Try ISO 8601 (feedparser format): 2021-07-20T17:59:59Z
    from datetime import timezone

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # Try RFC 2822 (RSS format): Tue, 20 Jul 2021 17:59:59 GMT
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        pass

    return None
