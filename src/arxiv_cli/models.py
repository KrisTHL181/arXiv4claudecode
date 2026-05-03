"""Data models for arXiv CLI.

Article/search results are represented by `arxiv.Result` from the `arxiv`
PyPI library. This module keeps only the category taxonomy models.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
