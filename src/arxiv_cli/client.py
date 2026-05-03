"""HTTP client for arXiv — query API via `arxiv` library, RSS/list/download via requests."""

from __future__ import annotations

import re
import time

import arxiv
import requests

from arxiv_cli.parsers import parse_list_page, parse_rss_item


class ArxivCliError(Exception):
    """Base exception for arXiv CLI errors."""


class APIError(ArxivCliError):
    """Error from the arXiv API."""


class FeedParseError(ArxivCliError):
    """Malformed feed entry."""


class ListPageParseError(ArxivCliError):
    """HTML list page parsing failure."""


class DownloadError(ArxivCliError):
    """File download or write failure."""


class DateParseError(ArxivCliError):
    """Invalid date string."""


def build_query(query: str, categories: list[str] | None = None) -> str:
    """Build a compound search query with optional category filter.

    Wraps plain-text queries with ``all:`` and appends a ``cat:`` filter.
    """
    if not categories:
        return query

    cat_clauses = " OR ".join(f"cat:{c}" for c in categories)
    cat_filter = f"({cat_clauses})" if len(categories) > 1 else cat_clauses

    q = query.strip()
    _FIELD_PREFIX_RE = r"^(ti|au|abs|all|cat|jr|rn|id|co):"
    if " " in q and not (
        q.startswith("(") or q.startswith('"') or re.match(_FIELD_PREFIX_RE, q)
    ):
        q = f"all:{q}"

    return f"({q}) AND ({cat_filter})"


class ArxivClient:
    """Thin client that delegates query API to `arxiv` library and keeps
    RSS / list-page / download functionality that the library does not cover."""

    RSS_TEMPLATE = "https://rss.arxiv.org/rss/{category}"
    LIST_TEMPLATE = "https://arxiv.org/list/{path}"
    USER_AGENT = "arxiv-cli/0.1.0 (mailto:user@example.com)"

    def __init__(self, query_delay: float = 3.0, num_retries: int = 3):
        self._arxiv = arxiv.Client(
            page_size=100,
            delay_seconds=query_delay,
            num_retries=num_retries,
        )
        self.num_retries = num_retries
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.USER_AGENT})

    # ── Query API (delegated to arxiv library) ──────────────────

    def search(
        self,
        query: str,
        max_results: int = 100,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        start: int = 0,
        categories: list[str] | None = None,
    ) -> list[arxiv.Result]:
        """Search the arXiv query API."""
        search_query = build_query(query, categories)

        sort_criterion = {
            "relevance": arxiv.SortCriterion.Relevance,
            "submittedDate": arxiv.SortCriterion.SubmittedDate,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
        }[sort_by]
        sort_dir = {
            "ascending": arxiv.SortOrder.Ascending,
            "descending": arxiv.SortOrder.Descending,
        }[sort_order]

        s = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=sort_criterion,
            sort_order=sort_dir,
        )
        return list(self._arxiv.results(s, offset=start))

    def search_by_date(
        self,
        start_date: str,
        end_date: str,
        categories: list[str] | None = None,
        max_results: int = 200,
    ) -> list[arxiv.Result]:
        """Search by submission date range. Dates as YYYYMMDD."""
        date_query = f"submittedDate:[{start_date}0000 TO {end_date}2359]"
        if categories:
            cat_filter = " OR ".join(f"cat:{c}" for c in categories)
            query = f"({date_query}) AND ({cat_filter})"
        else:
            query = date_query

        return self.search(
            query=query,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending",
        )

    # ── RSS feed ────────────────────────────────────────────────

    def fetch_rss(self, category: str) -> list[arxiv.Result]:
        """Fetch the latest papers via RSS feed for a category."""
        import feedparser

        url = self.RSS_TEMPLATE.format(category=category)
        try:
            resp = self._session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise APIError(f"Failed to fetch RSS feed: {e}") from e

        feed = feedparser.parse(resp.content)
        articles = []
        for item in feed.entries:
            try:
                articles.append(parse_rss_item(item))
            except Exception:
                continue
        return articles

    # ── HTML list page ──────────────────────────────────────────

    def fetch_list_page(self, path: str) -> list[arxiv.Result]:
        """Fetch papers from an arxiv.org/list/... HTML page."""
        url = self.LIST_TEMPLATE.format(path=path)
        try:
            resp = self._session.get(url, timeout=30)
            if resp.status_code == 404:
                raise APIError(
                    f"Page not found: {url}. The category or archive may not exist."
                )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise APIError(f"Failed to fetch list page: {e}") from e

        try:
            return parse_list_page(resp.text)
        except Exception as e:
            raise ListPageParseError(
                f"Could not parse the arXiv listings page. The format may have changed: {e}"
            ) from e

    # ── File download ───────────────────────────────────────────

    def download_file(self, url: str, output_path: str) -> str:
        """Download a file from arXiv to a local path. Returns the path."""
        for attempt in range(self.num_retries):
            try:
                resp = self._session.get(url, stream=True, timeout=60)
                if resp.status_code == 404:
                    raise DownloadError(
                        f"Paper not found at {url}. Check the ID."
                    )
                if resp.status_code == 503:
                    if attempt < self.num_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise DownloadError(
                        "arXiv is temporarily unavailable (503). Try again later."
                    )
                resp.raise_for_status()

                with open(output_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return output_path

            except requests.RequestException as e:
                if attempt < self.num_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise DownloadError(
                    f"Failed to download {url}: {e}"
                ) from e

        raise DownloadError(f"Failed to download {url} after retries.")
