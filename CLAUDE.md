# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# Install in editable mode
pip install -e .

# Run the CLI
arxiv --help
arxiv browse new cs.AI
arxiv search "transformers" -c cs.CL -n 20
arxiv download 2107.05580 -o ./papers

# No test suite or linter is configured yet.
```

## Architecture

`arxiv` CLI entry point (`arxiv_cli.cli:cli`) — a Click group that initializes `Formatter` and `ArxivClient` into the Click context. Every subcommand gets these from `ctx.obj`.

### Data flow (all commands follow this pattern)

1. **CLI layer** (`cli.py`) — Click commands parse args, call client methods, pass results to formatter.
2. **Client** (`client.py`) — `ArxivClient` wraps `requests.Session` with 3s rate limiting on the query API (`export.arxiv.org`), exponential-backoff retries, and three fetch strategies:
   - `search()` / `search_by_date()` → Atom feed from `export.arxiv.org/api/query`
   - `fetch_rss()` → RSS feed from `rss.arxiv.org/rss/{category}`
   - `fetch_list_page()` → HTML scraping from `arxiv.org/list/{path}`
   - `download_file()` → direct file download with retry
3. **Parsers** (`parsers.py`) — `parse_atom_entry()`, `parse_rss_item()`, `parse_list_page()` each produce `ArxivArticle` dataclass instances.
4. **Formatter** (`formatter.py`) — Three output modes controlled by `--json` / `--plain` flags (default: rich terminal). Each entity type (articles, categories, stats) has a dispatch method that delegates to the style-specific private method.

### Key models (`models.py`)

- `ArxivArticle` — dataclass with `entry_id`, `title`, `summary`, `authors`, `published`, `updated`, `primary_category`, `categories`, `comment`, `journal_ref`, `doi`, `pdf_url`. Computed properties: `short_id` (extracts arXiv ID from URL), `abs_url`, `html_url`, `source_url`.
- `Category` / `CategoryGroup` — taxonomy nodes.

### Category taxonomy (`categories.py`)

Static dictionary of ~180 canonical arXiv categories across 8 groups (cs, econ, eess, math, physics, q-bio, q-fin, stat). Built at import time into `Category`/`CategoryGroup` dataclass instances. Lookup functions: `get_group()`, `get_category()`, `is_valid_category()`.

### HTML→Markdown converter (`converter.py`)

`HtmlToMarkdown` class walks arXiv LaTeXML HTML (`class="ltx_*"`) and produces Markdown with `$`/`$$` math delimiters. Includes a recursive MathML→LaTeX converter with entity mapping. Used by the `html2md` subcommand.

### Statistics (`stats.py`)

Bundled fallback data (2020–2024 annual totals by group) plus a live scraper that attempts to extract numbers from `arxiv.org/stats/monthly_submissions`. Activated via `--refresh`.

## Commands overview

| Command | Source |
|---------|--------|
| `arxiv browse new/recent/current/month` | RSS + HTML list scraping |
| `arxiv catch-up <date>` | Query API date range search |
| `arxiv search <query>` | Query API full-text search (supports `ti:`, `au:`, `abs:`, `all:`, `cat:` prefixes) |
| `arxiv download <id>` | Direct PDF/src/html/e-print download |
| `arxiv stats` | Bundled + live submission stats |
| `arxiv categories` | Category taxonomy listing |
| `arxiv html2md <id\|file>` | LaTeXML HTML → Markdown conversion |

## Design notes

- The query API (`export.arxiv.org`) enforces a rate limit — `ArxivClient` defaults to 3s between requests.
- List page scraping (`arxiv.org/list/...`) is fragile: the parser targets `<dl>/<dt>/<dd>` structure and `list-*` CSS classes. If arXiv changes their HTML, `parse_list_page()` in `parsers.py` will need updating.
- RSS feeds (`rss.arxiv.org`) return only the latest mailing — no search, no pagination.
- `html2md` detects whether its argument is a file path or arXiv ID by checking `os.path.exists()` and file extension — arXiv IDs that happen to match local file names will be read as files.
