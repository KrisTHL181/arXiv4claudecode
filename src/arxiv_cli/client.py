"""HTTP client for arXiv APIs with rate limiting and retries."""

from __future__ import annotations

import re
import time
import urllib.parse

import requests

from arxiv_cli.models import ArxivArticle
from arxiv_cli.parsers import parse_atom_entry, parse_list_page, parse_rss_item


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


class ArxivClient:
    """HTTP client for arXiv with rate limiting for the query API."""

    BASE_QUERY = "https://export.arxiv.org/api/query"
    RSS_TEMPLATE = "https://rss.arxiv.org/rss/{category}"
    LIST_TEMPLATE = "https://arxiv.org/list/{path}"
    USER_AGENT = "arxiv-cli/0.1.0 (mailto:user@example.com)"

    def __init__(self, query_delay: float = 3.0, num_retries: int = 3):
        self.query_delay = query_delay
        self.num_retries = num_retries
        self._last_query_time: float = 0.0
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.USER_AGENT})

    # ── Public API ──────────────────────────────────────────────

    def search(
        self,
        query: str,
        max_results: int = 100,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        start: int = 0,
        categories: list[str] | None = None,
    ) -> list[ArxivArticle]:
        """Search the arXiv query API."""
        search_query = self._build_query(query, categories)

        params: dict[str, str | int] = {
            "search_query": search_query,
            "start": start,
            "max_results": min(max_results, 2000),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        url = self.BASE_QUERY + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return self._request_feed(url, rate_limited=True)

    def search_by_date(
        self,
        start_date: str,
        end_date: str,
        categories: list[str] | None = None,
        max_results: int = 200,
    ) -> list[ArxivArticle]:
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

    def fetch_rss(self, category: str) -> list[ArxivArticle]:
        """Fetch the latest papers via RSS feed for a category."""
        url = self.RSS_TEMPLATE.format(category=category)
        return self._request_rss(url)

    def fetch_list_page(self, path: str) -> list[ArxivArticle]:
        """Fetch papers from an arxiv.org/list/... HTML page."""
        url = self.LIST_TEMPLATE.format(path=path)
        return self._request_list_page(url)

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
                        wait = 2**attempt
                        time.sleep(wait)
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
                    wait = 2**attempt
                    time.sleep(wait)
                    continue
                raise DownloadError(
                    f"Failed to download {url}: {e}"
                ) from e

        raise DownloadError(f"Failed to download {url} after retries.")

    # ── Private helpers ─────────────────────────────────────────

    def _enforce_rate_limit(self) -> None:
        """Sleep if needed to respect the 3-second query API rate limit."""
        elapsed = time.monotonic() - self._last_query_time
        if elapsed < self.query_delay:
            time.sleep(self.query_delay - elapsed)

    @staticmethod
    def _build_query(query: str, categories: list[str] | None) -> str:
        """Build a compound search query with optional category filter."""
        if not categories:
            return query

        cat_clauses = " OR ".join(f"cat:{c}" for c in categories)
        if len(categories) > 1:
            cat_filter = f"({cat_clauses})"
        else:
            cat_filter = cat_clauses

        # Wrap raw query if it contains spaces and is plain text
        # (no explicit field prefix, boolean grouping, or phrase).
        q = query.strip()
        _FIELD_PREFIX_RE = r"^(ti|au|abs|all|cat|jr|rn|id|co):"
        if " " in q and not (
            q.startswith("(") or q.startswith('"') or re.match(_FIELD_PREFIX_RE, q)
        ):
            q = f"all:{q}"

        return f"({q}) AND ({cat_filter})"

    def _request_feed(
        self, url: str, rate_limited: bool = False
    ) -> list[ArxivArticle]:
        """Fetch and parse an Atom feed from the query API."""
        import feedparser

        for attempt in range(self.num_retries):
            try:
                if rate_limited:
                    self._enforce_rate_limit()

                resp = self._session.get(url, timeout=30)
                if rate_limited:
                    self._last_query_time = time.monotonic()

                if resp.status_code == 400:
                    raise APIError("Bad request. Query may exceed max results (30000 total).")
                if resp.status_code == 503:
                    if attempt < self.num_retries - 1:
                        time.sleep(2**attempt)
                        continue
                    raise APIError("arXiv is temporarily unavailable (503).")
                resp.raise_for_status()

                feed = feedparser.parse(resp.content)

                # Check for error response
                if feed.entries and feed.entries[0].get("title") == "Error":
                    msg = feed.entries[0].get("summary", "Unknown API error")
                    raise APIError(f"arXiv API error: {msg}")

                articles = []
                for entry in feed.entries:
                    try:
                        articles.append(parse_atom_entry(entry))
                    except Exception:
                        # Skip malformed entries
                        continue
                return articles

            except requests.RequestException as e:
                if attempt < self.num_retries - 1:
                    time.sleep(2**attempt)
                    continue
                raise APIError(f"Failed to reach arXiv: {e}") from e

        return []

    def _request_rss(self, url: str) -> list[ArxivArticle]:
        """Fetch and parse an RSS feed."""
        import feedparser

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

    def _request_list_page(self, url: str) -> list[ArxivArticle]:
        """Fetch and parse an arXiv list page."""
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
