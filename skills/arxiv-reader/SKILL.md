---
name: arxiv-reader
description: Read, search, and browse arXiv papers directly in the terminal. Use this skill whenever the user wants to read an academic paper from arXiv, search for papers on a topic, browse the latest papers in a category, or catch up on recent research. Triggers on mentions of arXiv, paper IDs (e.g. 2107.05580), "read this paper", "find papers about", "what's new in cs.AI", "show me the latest", or any academic paper reading request.
---

# arXiv Paper Reader

Read arXiv papers in the terminal by downloading HTML or LaTeX source and converting to readable Markdown.

## Core workflow: read a paper by ID

Use the bundled `scripts/read_paper.sh` script — it handles the full pipeline (download → extract → convert → cleanup) with automatic format fallback.

```bash
scripts/read_paper.sh <arxiv_id> [output_file]
```

If no output file is given, the Markdown prints to stdout. Let the user see it directly in the terminal.

**What it does internally:**
1. Tries HTML format → converts to Markdown via `arxiv html2md` (best results — preserves math, sections, figures)
2. Falls back to LaTeX source (`.tar.gz`) → extracts and outputs raw `.tex` (Claude can read LaTeX natively)
3. Last resort: PDF → extracts text via `pdftotext` if available

## Discovery: finding papers before reading

Use the `arxiv` CLI directly for discovery. Always use `--json` for machine-readable output when you need to parse results programmatically.

### Search

```bash
arxiv search "<query>" -c <category> -n <max_results> --sort-by relevance --json
```

Query prefixes narrow the search: `ti:` (title), `au:` (author), `abs:` (abstract), `all:` (full text), `cat:` (category).

Examples:
- `arxiv search 'ti:"graph neural network"' -c cs.LG -n 10 --json`
- `arxiv search 'au:"Yann LeCun"' -n 20 --json`
- `arxiv search "transformers attention mechanism" -c cs.CL -n 15 --json`

After showing search results to the user, ask which one they want to read, then use `read_paper.sh` with the chosen ID.

### Browse latest papers

```bash
arxiv browse new <category>           # today's new submissions (RSS)
arxiv browse recent <category> -n 20  # last 5 mailings
arxiv browse current <category> -n 50 # current month
arxiv browse month 2026 5 <category>  # specific month
```

Category defaults to `cs`. Common categories: `cs.AI`, `cs.CL`, `cs.CV`, `cs.LG`, `math`, `physics`, `stat`, `q-bio`.

### Catch up since a date

```bash
arxiv catch-up "2026-04-01" -c cs.AI -n 50 --json
arxiv catch-up "15 April 2026" -c cs.CL -n 100 --json
```

## Presenting papers to the user

When displaying a paper, always include:

1. **Header**: Title, authors, arXiv ID, categories, publication date
2. **Link**: `https://arxiv.org/abs/<id>` so the user can open in browser if needed
3. **Abstract**: Full abstract
4. **Content**: The converted Markdown body

For long papers, show the abstract, introduction, and conclusion first. Offer to show specific sections on request rather than dumping the entire paper at once — papers can be 20-50 pages.

If the paper was read from LaTeX source (`.tex`), note this to the user — the output will contain raw LaTeX markup rather than rendered Markdown, but Claude can still understand and explain it.

## Important notes

- **Not all papers have HTML**: Papers submitted before ~2010 may only have PDF + LaTeX source. The script handles this automatically.
- **Rate limiting**: arXiv's API enforces delays between requests. Don't fire off rapid searches — the CLI handles this internally with 3s delays.
- **Versioned IDs**: arXiv IDs with versions (e.g., `2107.05580v2`) work fine. The script strips versions for HTML URLs automatically since arXiv serves the latest version at the base URL.
- **Huge papers**: Some theses or long papers produce very large Markdown. When the output is >500 lines, summarize key sections rather than dumping everything into context.
- **Math rendering**: The `html2md` converter handles MathML → LaTeX with `$`/`$$` delimiters. LaTeX math in the Markdown output will display correctly in most terminals that support Unicode math symbols.
