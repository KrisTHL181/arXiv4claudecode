"""Output formatters: rich (terminal), plain (pipe-friendly), JSON (machine-readable)."""

from __future__ import annotations

import json
import sys
from dataclasses import fields, is_dataclass
from datetime import datetime

from arxiv_cli.models import ArxivArticle, Author, CategoryGroup


class Formatter:
    """Three-mode output formatter: rich, plain, json."""

    def __init__(self, style: str = "rich"):
        self.style = style

    def print_articles(
        self,
        articles: list[ArxivArticle],
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
    def _print_articles_rich(articles: list[ArxivArticle], show_abstracts: bool) -> None:
        from rich import box
        from rich.console import Console, Group
        from rich.markdown import Markdown
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = Console()
        for i, a in enumerate(articles):
            # Title with number
            title = Text.from_markup(f"[bold yellow]#{i + 1}[/bold yellow]  {a.title}")

            # Build metadata table
            meta_table = Table.grid(padding=(0, 2))
            meta_table.add_column(style="bold", width=10)
            meta_table.add_column()

            if a.short_id:
                urls = f"[green]abs:[/green] {a.abs_url}\n[green]pdf:[/green] {a.pdf_url}"
                if a.html_url:
                    urls += f"\n[green]html:[/green] {a.html_url}"
                meta_table.add_row("ID", f"[green]{a.short_id}[/green]  {urls}")
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

            # Build content group
            elements: list = [meta_table]

            if show_abstracts and a.summary:
                elements.append(Text(""))
                elements.append(Text("Abstract:", style="bold"))
                # Truncate abstract for display
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
    def _print_articles_plain(articles: list[ArxivArticle], show_abstracts: bool) -> None:
        for i, a in enumerate(articles):
            print(f"--- {i + 1}. {a.title}")
            if a.short_id:
                print(f"ID: {a.short_id}")
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
    def _print_articles_json(articles: list[ArxivArticle]) -> None:
        def _to_dict(obj):
            if is_dataclass(obj):
                d = {}
                for f in fields(obj):
                    d[f.name] = _to_dict(getattr(obj, f.name))
                # Include key properties
                if isinstance(obj, ArxivArticle):
                    d["short_id"] = obj.short_id
                    d["id_without_version"] = obj.id_without_version
                    d["source_url"] = obj.source_url
                    d["html_url"] = obj.html_url
                    d["abs_url"] = obj.abs_url
                return d
            if isinstance(obj, list):
                return [_to_dict(i) for i in obj]
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        items = [_to_dict(a) for a in articles]
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
