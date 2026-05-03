"""arXiv LaTeXML HTML to Markdown converter.

Handles the structured HTML output from arXiv's LaTeXML pipeline,
converting it to clean Markdown with LaTeX math.
"""

from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup, NavigableString, Tag


# ── MathML → LaTeX converter ──────────────────────────────────

_MATHML_ENTITIES: dict[str, str] = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
    "&apos;": "'", "&nbsp;": " ", "&times;": r"\times",
    "&plusmn;": r"\pm", "&minus;": r"-", "&divide;": r"\div",
    "&middot;": r"\cdot", "&equals;": "=", "&ne;": r"\neq",
    "&le;": r"\leq", "&ge;": r"\geq", "&lt;": "<", "&gt;": ">",
    "&larr;": r"\leftarrow", "&rarr;": r"\rightarrow",
    "&uarr;": r"\uparrow", "&darr;": r"\downarrow",
    "&harr;": r"\leftrightarrow",
    "&infin;": r"\infty", "&sum;": r"\sum", "&prod;": r"\prod",
    "&int;": r"\int", "&part;": r"\partial",
    "&alpha;": r"\alpha", "&beta;": r"\beta", "&gamma;": r"\gamma",
    "&delta;": r"\delta", "&epsilon;": r"\epsilon", "&zeta;": r"\zeta",
    "&eta;": r"\eta", "&theta;": r"\theta", "&iota;": r"\iota",
    "&kappa;": r"\kappa", "&lambda;": r"\lambda", "&mu;": r"\mu",
    "&nu;": r"\nu", "&xi;": r"\xi", "&pi;": r"\pi", "&rho;": r"\rho",
    "&sigma;": r"\sigma", "&tau;": r"\tau", "&upsilon;": r"\upsilon",
    "&phi;": r"\phi", "&chi;": r"\chi", "&psi;": r"\psi", "&omega;": r"\omega",
    "&Gamma;": r"\Gamma", "&Delta;": r"\Delta", "&Theta;": r"\Theta",
    "&Lambda;": r"\Lambda", "&Xi;": r"\Xi", "&Pi;": r"\Pi",
    "&Sigma;": r"\Sigma", "&Phi;": r"\Phi", "&Psi;": r"\Psi",
    "&Omega;": r"\Omega",
    "&subset;": r"\subset", "&supset;": r"\supset",
    "&subseteq;": r"\subseteq", "&supseteq;": r"\supseteq",
    "&cap;": r"\cap", "&cup;": r"\cup",
    "&isin;": r"\in", "&notin;": r"\notin",
    "&sim;": r"\sim", "&approx;": r"\approx", "&equiv;": r"\equiv",
    "&propto;": r"\propto",
    "&perp;": r"\perp", "&parallel;": r"\parallel",
    "&forall;": r"\forall", "&exist;": r"\exists",
    "&ang;": r"\angle", "&nabla;": r"\nabla",
    "&hellip;": r"\dots", "&middot;": r"\cdot",
}


def _get_math_latex(element: Tag) -> str:
    """Extract LaTeX from a <math> element, preferring the alttext attribute."""
    alttext = element.get("alttext", "")
    if alttext:
        return alttext.strip()
    # Fall back to MathML → LaTeX conversion
    result = _mathml_walk(element)
    result = re.sub(r"\s+", " ", result)
    return result.strip()


def _mathml_walk(el) -> str:
    """Recursively walk MathML tree and produce LaTeX."""
    if isinstance(el, NavigableString):
        text = str(el)
        for ent, latex in _MATHML_ENTITIES.items():
            text = text.replace(ent, latex)
        return unescape(text)

    if not isinstance(el, Tag):
        return ""

    tag = el.name

    # Subscripts / superscripts
    if tag in ("msub", "msubsup"):
        children = [c for c in el.children if isinstance(c, Tag)]
        if len(children) >= 2:
            base = _mathml_walk(children[0])
            sub = _mathml_walk(children[1])
            if tag == "msub":
                return f"{base}_{{{sub}}}"
            elif len(children) >= 3:
                sup = _mathml_walk(children[2])
                return f"{base}_{{{sub}}}^{{{sup}}}"
        return ""

    if tag == "msup":
        children = [c for c in el.children if isinstance(c, Tag)]
        if len(children) >= 2:
            base = _mathml_walk(children[0])
            sup = _mathml_walk(children[1])
            return f"{base}^{{{sup}}}"
        return ""

    # Fractions
    if tag == "mfrac":
        children = [c for c in el.children if isinstance(c, Tag)]
        if len(children) >= 2:
            num = _mathml_walk(children[0])
            den = _mathml_walk(children[1])
            return f"\\frac{{{num}}}{{{den}}}"
        return ""

    # Square roots
    if tag == "msqrt":
        inner = "".join(_mathml_walk(c) for c in el.children if not isinstance(c, NavigableString) or str(c).strip())
        return f"\\sqrt{{{inner}}}"

    if tag == "mroot":
        children = [c for c in el.children if isinstance(c, Tag)]
        if len(children) >= 2:
            inner = _mathml_walk(children[0])
            root = _mathml_walk(children[1])
            return f"\\sqrt[{root}]{{{inner}}}"
        return ""

    # Rows (for matrices, arrays, etc.)
    if tag == "mtable":
        rows = []
        for row in el.find_all("mtr", recursive=False):
            cells = []
            for cell in row.find_all("mtd", recursive=False):
                cells.append(_mathml_walk(cell))
            rows.append(" & ".join(cells))
        return r"\begin{array}{" + "c" * (len(rows[0].split("&")) if rows else 1) + "} " + " \\\\ ".join(rows) + r" \end{array}"

    if tag == "mover":
        children = [c for c in el.children if isinstance(c, Tag)]
        if len(children) >= 2:
            above = _mathml_walk(children[1])
            if "overbrace" in str(el) or "&#x23DE;" in str(el):
                base = _mathml_walk(children[0])
                return f"\\overbrace{{{base}}}^{{{above}}}"
            base = _mathml_walk(children[0])
            return f"\\overline{{{base}}}"
        return ""

    if tag == "munder":
        children = [c for c in el.children if isinstance(c, Tag)]
        if len(children) >= 2:
            base = _mathml_walk(children[0])
            under = _mathml_walk(children[1])
            return f"\\underset{{{under}}}{{{base}}}"
        return ""

    # Fenced expressions (parentheses, brackets)
    if tag in ("mfenced", "mrow"):
        parts = [_mathml_walk(c) for c in el.children]
        inner = " ".join(p for p in parts if p.strip())
        if tag == "mfenced":
            open_br = el.get("open", "(")
            close_br = el.get("close", ")")
            return f"{open_br}{inner}{close_br}"
        return inner

    # Text (operators, etc.)
    if tag in ("mi", "mn", "mo", "mtext", "mspace"):
        return _get_text_content(el)

    # Annotation (sometimes contains LaTeX directly)
    if tag == "annotation":
        encoding = el.get("encoding", "")
        if encoding == "application/x-tex":
            return str(el.string or "").strip()
        return _get_text_content(el)

    if tag == "semantics":
        # Prefer the annotation with LaTeX if available
        ann = el.find("annotation", attrs={"encoding": "application/x-tex"})
        if ann and ann.string:
            return str(ann.string).strip()
        # Otherwise, process first child
        children = [c for c in el.children if isinstance(c, Tag)]
        if children:
            return _mathml_walk(children[0])
        return ""

    if tag == "merror":
        return _get_text_content(el)

    # Default: process all children
    return "".join(_mathml_walk(c) for c in el.children)


def _get_text_content(el: Tag) -> str:
    """Get text content from an element, applying entity substitution."""
    text = el.get_text()
    for ent, latex in _MATHML_ENTITIES.items():
        text = text.replace(ent, latex)
    return unescape(text)


# ── LaTeXML → Markdown converter ──────────────────────────────

class HtmlToMarkdown:
    """Convert arXiv LaTeXML HTML to Markdown."""

    def __init__(self):
        self.output: list[str] = []
        self._figures: list[str] = []
        self._tables: list[str] = []

    def convert(self, html: str) -> str:
        """Convert arXiv HTML paper to Markdown string."""
        self.output = []
        self._figures = []
        self._tables = []

        soup = BeautifulSoup(html, "lxml")

        # Find the main article content
        article = soup.find("article", class_="ltx_document")
        if not article:
            article = soup.find("div", class_="ltx_page_content")
        if not article:
            return "Error: Could not find paper content in HTML."

        self._process_element(article)
        return "\n\n".join(self.output).strip() + "\n"

    def _process_element(self, el) -> None:
        """Recursively process a LaTeXML element."""
        if isinstance(el, NavigableString):
            text = str(el).strip()
            if text:
                self._append_text(text)
            return

        if not isinstance(el, Tag):
            return

        classes = el.get("class", [])

        # ── Document structure ──
        if "ltx_title_document" in classes or "ltx_title" in classes:
            title = _clean(el.get_text())
            self.output.append(f"# {title}")
            return

        if "ltx_authors" in classes:
            authors = []
            for a in el.find_all("span", class_="ltx_author"):
                authors.append(_clean(a.get_text()))
            if authors:
                self.output.append(f"**Authors:** {', '.join(authors)}")
            return

        if "ltx_abstract" in classes:
            self.output.append("## Abstract")
            for child in el.children:
                if isinstance(child, Tag):
                    self._process_inline(child)
            self.output.append("")
            return

        # ── Sections ──
        if "ltx_section" in classes:
            heading = self._extract_heading(el)
            self.output.append(f"## {heading}")
            self._process_section_children(el)
            return

        if "ltx_subsection" in classes:
            heading = self._extract_heading(el)
            self.output.append(f"### {heading}")
            self._process_section_children(el)
            return

        if "ltx_subsubsection" in classes:
            heading = self._extract_heading(el)
            self.output.append(f"#### {heading}")
            self._process_section_children(el)
            return

        if "ltx_paragraph" in classes:
            heading = self._extract_heading(el)
            self.output.append(f"##### {heading}")
            self._process_section_children(el)
            return

        # ── Paragraphs ──
        if "ltx_para" in classes:
            # Paragraphs may contain both inline text and block elements (tables, equations)
            self._process_mixed_element(el)
            return

        # ── Figures ──
        if "ltx_figure" in classes or "ltx_table" in classes:
            fig_text = self._process_figure(el)
            if fig_text:
                self.output.append(fig_text)
            return

        # ── Equations ──
        if "ltx_equation" in classes or "ltx_eqn" in classes or "ltx_display" in classes:
            # Collect all math cells in this equation row
            eqn_parts: list[str] = []
            for cell in el.find_all("td", class_="ltx_eqn_cell", recursive=False):
                math_el = cell.find("math")
                if math_el:
                    latex = _get_math_latex(math_el)
                    if latex:
                        eqn_parts.append(latex)
            if eqn_parts:
                eqn_text = " ".join(eqn_parts)
                self.output.append(f"$$\n{eqn_text}\n$$")
            return

        if "ltx_equationgroup" in classes:
            # Multi-line aligned equations
            group_lines: list[str] = []
            for row in el.find_all(class_="ltx_equation"):
                row_parts: list[str] = []
                for cell in row.find_all("td", class_="ltx_eqn_cell", recursive=False):
                    math_el = cell.find("math")
                    if math_el:
                        latex = _get_math_latex(math_el)
                        if latex:
                            row_parts.append(latex)
                if row_parts:
                    group_lines.append(" ".join(row_parts))
            if group_lines:
                aligned = "\n".join(group_lines)
                self.output.append(f"$$\n\\begin{{aligned}}\n{aligned}\n\\end{{aligned}}\n$$")
            return

        # ── Lists ──
        if "ltx_itemize" in classes:
            for item in el.find_all("li", class_="ltx_item", recursive=False):
                text = self._collect_inline(item)
                self.output.append(f"- {text}")
            return

        if "ltx_enumerate" in classes:
            items = el.find_all("li", class_="ltx_item", recursive=False)
            for i, item in enumerate(items, 1):
                text = self._collect_inline(item)
                self.output.append(f"{i}. {text}")
            return

        # ── Bibliography ──
        if "ltx_bibitem" in classes:
            bib_id = el.get("id", "")
            text = self._collect_inline(el)
            self.output.append(f"[^{bib_id}]: {text}")
            return

        if "ltx_bibblock" in classes:
            return

        # ── Tags / labels (equation numbers, section numbers) ──
        if "ltx_tag" in classes:
            # Equation/section tags are collected during inline processing
            return

        # ── Notes / errors ──
        if "ltx_note" in classes or "ltx_rule" in classes:
            return

        # ── Recurse into children ──
        for child in el.children:
            if isinstance(child, Tag):
                self._process_element(child)

    def _extract_heading(self, el: Tag) -> str:
        """Extract heading text from the heading child element (h2/h3/etc or ltx_title_*), not the whole section."""
        # Find the actual heading element within the section
        heading_el = None
        for cls_prefix in ("ltx_title_section", "ltx_title_subsection",
                           "ltx_title_subsubsection", "ltx_title_paragraph"):
            heading_el = el.find(class_=cls_prefix)
            if heading_el:
                break

        if not heading_el:
            # Try h2-h6 tags
            for htag in ("h2", "h3", "h4", "h5", "h6"):
                heading_el = el.find(htag)
                if heading_el:
                    break

        if heading_el:
            tag_span = heading_el.find("span", class_="ltx_tag")
            if tag_span:
                tag_span.decompose()
            return _clean(heading_el.get_text())

        return _clean(el.get_text())

    def _process_mixed_element(self, el: Tag) -> None:
        """Process an element that may contain both inline and block children."""
        block_classes = {
            "ltx_equation", "ltx_equationgroup", "ltx_eqn_table",
            "ltx_figure", "ltx_table", "ltx_itemize", "ltx_enumerate",
            "ltx_bibitem",
        }
        _BLOCK_TAGS = {"table", "figure", "ul", "ol", "dl"}

        accumulated: list[str] = []

        def _flush() -> None:
            text = _normalize_whitespace("".join(accumulated))
            if text.strip():
                self.output.append(text)
            accumulated.clear()

        for child in el.children:
            if isinstance(child, NavigableString):
                accumulated.append(str(child))
                continue

            if not isinstance(child, Tag):
                continue

            child_cls = set(child.get("class", []))
            child_tags_in = {t.name for t in child.find_all() if isinstance(t, Tag)} | {child.name}

            # Block children get processed separately
            if child_cls & block_classes or child.name in _BLOCK_TAGS:
                _flush()
                self._process_element(child)
            elif child.name == "math":
                latex = _get_math_latex(child)
                if latex:
                    if child.get("display") == "inline" or "ltx_Math" in child_cls:
                        accumulated.append(f"${latex}$")
                    else:
                        _flush()
                        self.output.append(f"$$\n{latex}\n$$")
                else:
                    accumulated.append(child.get_text())
            else:
                accumulated.append(self._collect_inline(child))

        # Flush remaining text
        _flush()

    def _process_section_children(self, el: Tag) -> None:
        """Process section children, skipping the heading element."""
        heading_classes = {
            "ltx_title_section", "ltx_title_subsection",
            "ltx_title_subsubsection", "ltx_title_paragraph",
        }
        for child in el.children:
            if isinstance(child, Tag):
                child_cls = set(child.get("class", []))
                # Skip heading element
                if child_cls & heading_classes or child.name in ("h2", "h3", "h4", "h5", "h6"):
                    continue
                self._process_element(child)

    def _collect_inline(self, el) -> str:
        """Collect inline content, converting MathML and formatting."""
        parts: list[str] = []
        for child in el.children:
            if isinstance(child, NavigableString):
                text = str(child)
                parts.append(text)
            elif isinstance(child, Tag):
                cls = child.get("class", [])

                if child.name == "math":
                    # Inline math
                    latex = _get_math_latex(child)
                    if latex:
                        parts.append(f"${latex}$")
                elif "ltx_ref" in cls:
                    ref_text = _clean(child.get_text())
                    parts.append(ref_text)
                elif "ltx_cite" in cls:
                    cite_text = _clean(child.get_text())
                    parts.append(f"[{cite_text}]")
                elif child.name == "em" or "ltx_emph" in cls:
                    parts.append(f"*{self._collect_inline(child)}*")
                elif child.name == "strong":
                    parts.append(f"**{self._collect_inline(child)}**")
                elif child.name == "a":
                    href = child.get("href", "")
                    link_text = self._collect_inline(child)
                    if href:
                        parts.append(f"[{link_text}]({href})")
                    else:
                        parts.append(link_text)
                elif child.name == "sub":
                    parts.append(f"~{self._collect_inline(child)}~")
                elif child.name == "sup":
                    parts.append(f"^{self._collect_inline(child)}^")
                elif child.name == "code":
                    parts.append(f"`{self._collect_inline(child)}`")
                elif child.name == "br":
                    parts.append("\n")
                elif "ltx_tag" in cls:
                    pass  # Skip equation/section numbers
                else:
                    parts.append(self._collect_inline(child))

        return _normalize_whitespace("".join(parts))

    def _process_figure(self, el: Tag) -> str:
        """Process a figure or table, return as a Markdown reference."""
        fig_id = el.get("id", "")
        caption_el = el.find("figcaption")
        caption = ""
        if caption_el:
            tag_span = caption_el.find("span", class_="ltx_tag_figure")
            if tag_span:
                tag_span.decompose()
            caption = _clean(caption_el.get_text())

        # Try to extract the image URL
        img = el.find("img")
        if img:
            src = img.get("src", "")
            alt = img.get("alt", caption or "Figure")
            return f"![{alt}]({src})\n\n*{caption}*" if caption else f"![{alt}]({src})"

        # For tables, render as an HTML block since Markdown tables are limited
        table = el.find("table")
        if table:
            return self._table_to_md(table, caption)

        return f"*Figure: {caption}*" if caption else ""

    def _table_to_md(self, table: Tag, caption: str = "") -> str:
        """Convert an HTML table to Markdown."""
        lines: list[str] = []
        if caption:
            lines.append(f"**{caption}**")

        rows = table.find_all("tr")
        for i, row in enumerate(rows):
            cells = []
            for cell in row.find_all(["th", "td"]):
                cells.append(_clean(cell.get_text()))
            lines.append("| " + " | ".join(cells) + " |")
            if i == 0 and rows:
                lines.append("|" + "|".join(["---"] * len(cells)) + "|")

        lines.append("")
        return "\n".join(lines)

    def _process_inline(self, el) -> None:
        """Process an element as inline content and append it to output."""
        text = self._collect_inline(el)
        if text.strip():
            self.output.append(text)

    def _append_text(self, text: str) -> None:
        """Append text to the current last line."""
        if self.output and not self.output[-1].endswith("\n\n"):
            self.output[-1] += text


def _clean(text: str) -> str:
    """Clean text: collapse whitespace, remove excessive newlines."""
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace for inline text."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def convert_html_to_markdown(html: str) -> str:
    """Convenience function: convert arXiv HTML to Markdown."""
    converter = HtmlToMarkdown()
    return converter.convert(html)
