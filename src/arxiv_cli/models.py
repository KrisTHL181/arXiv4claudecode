"""Data models for arXiv CLI."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Author:
    """An arXiv paper author."""

    name: str


@dataclass
class ArxivArticle:
    """Represents a single arXiv paper."""

    entry_id: str
    title: str
    summary: str
    authors: list[Author]
    published: datetime
    updated: datetime
    primary_category: str = ""
    categories: list[str] = field(default_factory=list)
    comment: str | None = None
    journal_ref: str | None = None
    doi: str | None = None
    pdf_url: str | None = None

    @property
    def short_id(self) -> str:
        """Extract the arXiv ID from the entry_id URL."""
        m = re.search(r"arxiv\.org/abs/(.+)", self.entry_id)
        return m.group(1) if m else self.entry_id

    @property
    def id_without_version(self) -> str:
        """ArXiv ID without version suffix (e.g., '2107.05580' not '2107.05580v2')."""
        sid = self.short_id
        return re.sub(r"v\d+$", "", sid)

    @property
    def source_url(self) -> str | None:
        """URL to download LaTeX source tarball."""
        if not self.short_id:
            return None
        return f"https://arxiv.org/src/{self.short_id}"

    @property
    def html_url(self) -> str | None:
        """URL to rendered HTML version."""
        if not self.id_without_version:
            return None
        return f"https://arxiv.org/html/{self.id_without_version}"

    @property
    def abs_url(self) -> str | None:
        """URL to abstract page."""
        if not self.short_id:
            return None
        return f"https://arxiv.org/abs/{self.short_id}"


@dataclass
class Category:
    """A single arXiv category."""

    id: str
    name: str
    group: str
    description: str = ""


@dataclass
class CategoryGroup:
    """A top-level group of arXiv categories (e.g., cs, math, physics)."""

    id: str
    name: str
    categories: list[Category] = field(default_factory=list)
