"""Output formatters: rich (terminal), plain (pipe-friendly), JSON (machine-readable)."""

from __future__ import annotations

import json
import re
import sys

import arxiv

from arxiv_cli.models import CategoryGroup


class Formatter:
    """Three-mode output formatter: rich, plain, json."""

    def __init__(self, style: str = "rich"):
        self.style = style

    def print_articles(
        self,
        articles: list[arxiv.Result],
        show_abstracts: bool = True,
    ) -> None:
        """Print a list of articles."""
        if not articles:
            self.print_error("No results found.")
            return

        if self.style == "json":
            self._print_articles_json(articles)
        elif self.style == "plain":
            self._print_articles_plain(articles, show_abstracts)
        else:
            self._print_articles_rich(articles, show_abstracts)

    def print_categories(self, groups: list[CategoryGroup]) -> None:
        """Print category taxonomy."""
        if not groups:
            self.print_error("No categories found.")
            return

        if self.style == "json":
            self._print_categories_json(groups)
        elif self.style == "plain":
            self._print_categories_plain(groups)
        else:
            self._print_categories_rich(groups)

    def print_stats(
        self,
        data: dict[int, dict[str, int]],
        year: int | None = None,
        category: str | None = None,
    ) -> None:
        """Print submission statistics."""
        if not data:
            self.print_error("No statistics data available.")
            return

        if self.style == "json":
            json.dump(data, sys.stdout, indent=2)
            sys.stdout.write("\n")
        elif self.style == "plain":
            self._print_stats_plain(data, year, category)
        else:
            self._print_stats_rich(data, year, category)

    def print_download_result(self, path: str) -> None:
        """Print download confirmation."""
        if self.style == "json":
            json.dump({"downloaded": path}, sys.stdout)
            sys.stdout.write("\n")
        elif self.style == "rich":
            from rich.console import Console
            Console().print(f"[green]Downloaded:[/green] {path}")
        else:
            print(f"Downloaded: {path}")

    def print_error(self, message: str) -> None:
        """Print an error message."""
        if self.style == "json":
            json.dump({"error": message}, sys.stdout)
            sys.stdout.write("\n")
        elif self.style == "rich":
            from rich.console import Console
            Console().print(f"[red]Error:[/red] {message}")
        else:
            print(f"Error: {message}", file=sys.stderr)

    # ── Rich rendering ────────────────────────────────────────

    @staticmethod
    def _print_articles_rich(articles: list[arxiv.Result], show_abstracts: bool) -> None:
        from rich.console import Console, Group
        from rich.markdown import Markdown
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = Console()
        for i, a in enumerate(articles):
            title = Text.from_markup(f"[bold yellow]#{i + 1}[/bold yellow]  {a.title}")

            meta_table = Table.grid(padding=(0, 2))
            meta_table.add_column(style="bold", width=10)
            meta_table.add_column()

            short_id = a.get_short_id()
            abs_url = a.entry_id
            pdf_url = a.pdf_url
            html_url = _html_url(short_id)

            if short_id:
                urls = f"[green]abs:[/green] {abs_url}\n[green]pdf:[/green] {pdf_url}"
                if html_url:
                    urls += f"\n[green]html:[/green] {html_url}"
                meta_table.add_row("ID", f"[green]{short_id}[/green]  {urls}")
            if a.primary_category:
                meta_table.add_row("Category", f"[cyan]{a.primary_category}[/cyan]"
                                   + (f"  ({', '.join(a.categories)})" if len(a.categories) > 1 else ""))
            if a.authors:
                names = ", ".join(au.name for au in a.authors[:10])
                if len(a.authors) > 10:
                    names += f" [dim](+{len(a.authors) - 10} more)[/dim]"
                meta_table.add_row("Authors", names)
            if a.published:
                meta_table.add_row("Date", a.published.strftime("%Y-%m-%d"))
            if a.comment:
                meta_table.add_row("Comments", f"[dim]{a.comment}[/dim]")
            if a.journal_ref:
                meta_table.add_row("Journal", a.journal_ref)

            elements: list = [meta_table]

            if show_abstracts and a.summary:
                elements.append(Text(""))
                elements.append(Text("Abstract:", style="bold"))
                text = a.summary[:800]
                if len(a.summary) > 800:
                    text += "..."
                elements.append(Markdown(text))

            panel = Panel(
                Group(*elements),
                title=title,
                border_style="blue",
                padding=(1, 2),
            )
            console.print(panel)
            if i < len(articles) - 1:
                console.print("")

    @staticmethod
    def _print_categories_rich(groups: list[CategoryGroup]) -> None:
        from rich.console import Console
        from rich.tree import Tree

        console = Console()
        root = Tree("[bold]arXiv Category Taxonomy[/bold]")
        for group in groups:
            branch = root.add(f"[bold cyan]{group.id}[/bold cyan] — {group.name}  [dim]({len(group.categories)})[/dim]")
            for cat in group.categories:
                desc = f" — {cat.description}" if cat.description else ""
                branch.add(f"[green]{cat.id}[/green] {cat.name}{desc}")
        console.print(root)

    @staticmethod
    def _print_stats_rich(
        data: dict[int, dict[str, int]],
        year: int | None,
        category: str | None,
    ) -> None:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="arXiv Submission Statistics")
        table.add_column("Year", style="cyan", justify="right")
        table.add_column("Category", style="green")
        table.add_column("Submissions", style="yellow", justify="right")

        years = sorted(data.keys())
        if year:
            years = [y for y in years if y == year]

        for y in years:
            cats = data.get(y, {})
            if category:
                count = cats.get(category, 0)
                table.add_row(str(y), category, f"{count:,}")
            else:
                for cat, count in sorted(cats.items()):
                    if count > 0:
                        table.add_row(str(y), cat, f"{count:,}")

        if table.row_count == 0:
            console.print("[dim]No matching statistics found.[/dim]")
        else:
            console.print(table)

    # ── Plain rendering ───────────────────────────────────────

    @staticmethod
    def _print_articles_plain(articles: list[arxiv.Result], show_abstracts: bool) -> None:
        for i, a in enumerate(articles):
            print(f"--- {i + 1}. {a.title}")
            short_id = a.get_short_id()
            if short_id:
                print(f"ID: {short_id}")
            if a.primary_category:
                print(f"Category: {a.primary_category}")
            if a.authors:
                names = ", ".join(au.name for au in a.authors)
                print(f"Authors: {names}")
            if a.published:
                print(f"Published: {a.published.strftime('%Y-%m-%d')}")
            if a.comment:
                print(f"Comments: {a.comment}")
            if a.journal_ref:
                print(f"Journal: {a.journal_ref}")
            if a.pdf_url:
                print(f"PDF: {a.pdf_url}")
            if show_abstracts and a.summary:
                print(f"Abstract: {a.summary}")
            print()

    @staticmethod
    def _print_categories_plain(groups: list[CategoryGroup]) -> None:
        for group in groups:
            print(f"{group.id} — {group.name}")
            for cat in group.categories:
                print(f"  {cat.id}  {cat.name}")
            print()

    @staticmethod
    def _print_stats_plain(
        data: dict[int, dict[str, int]],
        year: int | None,
        category: str | None,
    ) -> None:
        years = sorted(data.keys())
        if year:
            years = [y for y in years if y == year]

        for y in years:
            cats = data.get(y, {})
            if category:
                count = cats.get(category, 0)
                print(f"{y}  {category}: {count:,}")
            else:
                for cat, count in sorted(cats.items()):
                    if count > 0:
                        print(f"{y}  {cat}: {count:,}")

    # ── JSON rendering ────────────────────────────────────────

    @staticmethod
    def _print_articles_json(articles: list[arxiv.Result]) -> None:
        items = [_result_to_dict(a) for a in articles]
        json.dump(items, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    @staticmethod
    def _print_categories_json(groups: list[CategoryGroup]) -> None:
        result = []
        for g in groups:
            result.append({
                "group_id": g.id,
                "group_name": g.name,
                "categories": [
                    {"id": c.id, "name": c.name, "description": c.description}
                    for c in g.categories
                ],
            })
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")


def _html_url(short_id: str) -> str | None:
    """Derive the HTML URL from a short arXiv ID (strips version suffix)."""
    if not short_id:
        return None
    return f"https://arxiv.org/html/{_id_without_version(short_id)}"


def _id_without_version(short_id: str) -> str:
    """Strip version suffix from arXiv ID."""
    return re.sub(r"v\d+$", "", short_id)


def _result_to_dict(a: arxiv.Result) -> dict:
    """Convert an arxiv.Result to a JSON-serialisable dict."""
    short_id = a.get_short_id()
    return {
        "entry_id": a.entry_id,
        "short_id": short_id,
        "id_without_version": _id_without_version(short_id),
        "title": a.title,
        "summary": a.summary,
        "authors": [{"name": au.name} for au in a.authors],
        "published": a.published.isoformat() if a.published else None,
        "updated": a.updated.isoformat() if a.updated else None,
        "primary_category": a.primary_category,
        "categories": a.categories,
        "comment": a.comment,
        "journal_ref": a.journal_ref,
        "doi": a.doi,
        "pdf_url": a.pdf_url,
        "abs_url": a.entry_id,
        "html_url": _html_url(short_id),
        "source_url": f"https://arxiv.org/src/{short_id}" if short_id else None,
    }
