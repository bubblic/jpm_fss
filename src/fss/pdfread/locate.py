"""Locate the pages of each core statement inside a filing PDF.

Pure-PDF logic: generic title vocabulary (no tag-path metadata), a
value-row density requirement that rejects index and auditor pages, an
anchor row the true statement must contain ("Total assets", "operating
activities"), and terminal-anchored continuation so statements spanning
pages are captured whole.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fss.pdfread.rows import split_trailing_values

TITLE_HINTS: dict[str, tuple[str, ...]] = {
    "balance_sheet": (
        "balance sheet",
        "statement of financial position",
        "statements of financial position",
        "statement of financial condition",  # banks and broker-dealers
        "statements of financial condition",
    ),
    "income_statement": (
        "statement of operations",
        "statements of operations",
        "income statement",
        "income statements",
        "statement of income",
        "statements of income",
        "statement of profit or loss",  # IFRS wording common in HK/EU reports
        "statements of profit or loss",
    ),
    "cash_flow": ("statement of cash flows", "statements of cash flows", "cash flows statement"),
}
TITLE_VETO: dict[str, tuple[str, ...]] = {
    "balance_sheet": ("parenthetical",),
    "income_statement": ("parenthetical", "comprehensive"),
    "cash_flow": ("parenthetical",),
}
ANCHORS: dict[str, re.Pattern[str]] = {
    "balance_sheet": re.compile(
        r"^total ?assets\b", re.IGNORECASE | re.MULTILINE
    ),
    "income_statement": re.compile(
        r"per ?share|income ?tax|profit ?before ?tax", re.IGNORECASE
    ),
    "cash_flow": re.compile(r"operating ?activities", re.IGNORECASE),
}
TERMINALS: dict[str, re.Pattern[str]] = {
    "balance_sheet": re.compile(
        r"total (equity and liabilities|liabilities and (shareholders|stockholders))",
        re.IGNORECASE,
    ),
    "income_statement": re.compile(r"\bdiluted\b", re.IGNORECASE),
    "cash_flow": re.compile(
        r"(cash .*end of (the )?(year|period))|supplemental", re.IGNORECASE
    ),
}
TOP_LINES = 8
MIN_VALUE_ROWS = 6
MAX_CONTINUATIONS = 2
ANY_TITLE = re.compile(
    r"balance sheet|statements? of financial (position|condition)|income statements?|"
    r"statements? of (operations|income|earnings)|statements? of profit or loss|"
    r"cash flows? statements?|"
    r"statements? of cash flows|statements? of (stockholders|shareholders|changes in)"
    r"|comprehensive income",
    re.IGNORECASE,
)


def _title_line_index(info: "PageInfo", statement: str) -> int | None:
    """Line index of this statement's title on the page, if present."""
    hints = tuple(_squeeze(h) for h in TITLE_HINTS[statement])
    vetos = tuple(_squeeze(v) for v in TITLE_VETO[statement])
    for index, line in enumerate(info.lines):
        squeezed = _squeeze(line)
        if not squeezed or len(squeezed) > 100:
            continue
        if any(v in squeezed for v in vetos):
            continue
        if any(h in squeezed for h in hints):
            return index
    return None


def crop_region(info: "PageInfo", statement: str) -> tuple[int, int]:
    """(start_line, end_line) bounding this statement's region on the page.

    The region runs from this statement's title (or the page top when the
    statement continues from a prior page) to the next different statement
    title, so a page carrying two statements feeds the readers only one.
    """
    start = _title_line_index(info, statement)
    begin = start if start is not None else 0
    end = len(info.lines)
    for index in range(begin + 1, len(info.lines)):
        lowered = " ".join(info.lines[index].lower().split())
        if len(lowered) > 110:
            continue
        if ANY_TITLE.search(lowered):
            hints = TITLE_HINTS[statement]
            if not any(h in lowered for h in hints):
                end = index
                break
    return begin, end


@dataclass
class PageInfo:
    index: int
    text: str
    lines: list[str]
    value_rows: int

    def top_lines(self) -> list[str]:
        return [line for line in self.lines if line.strip()][:TOP_LINES]


def _value_row_count(lines: list[str]) -> int:
    count = 0
    for line in lines:
        _, values = split_trailing_values(line.split())
        if len([v for v in values if v.value is not None]) >= 2:
            count += 1
    return count


def probe_text_options(pdf: Any) -> dict[str, float]:
    """Choose extraction tolerances for this document.

    Some PDFs carry no space glyphs and rely on kerning; at the default
    tolerance their words fuse ("CONSOLIDATEDBALANCESHEET"). When sampled
    pages show almost no spaces, drop to a tight tolerance so gaps become
    word breaks again.
    """
    samples = [pdf.pages[i] for i in range(0, len(pdf.pages), max(1, len(pdf.pages) // 6))][:6]
    characters = spaces = 0
    for page in samples:
        text = page.extract_text() or ""
        characters += len(text)
        spaces += text.count(" ")
    if characters and spaces / characters < 0.05:
        return {"x_tolerance": 1.2}
    return {}


def scan_pages(pdf: Any, text_options: dict[str, float] | None = None) -> list[PageInfo]:
    options = probe_text_options(pdf) if text_options is None else text_options
    pages: list[PageInfo] = []
    for index, page in enumerate(pdf.pages):
        text = page.extract_text(**options) or ""
        lines = text.splitlines()
        pages.append(PageInfo(index, text, lines, _value_row_count(lines)))
    return pages


def _squeeze(text: str) -> str:
    return "".join(text.lower().split())


def _title_hit(info: PageInfo, statement: str) -> bool:
    """Title match, tolerant of PDFs whose space glyphs vanish
    ("CONSOLIDATEDBALANCESHEET"): hints compare in condensed form."""
    hints = tuple(_squeeze(h) for h in TITLE_HINTS[statement])
    vetos = tuple(_squeeze(v) for v in TITLE_VETO[statement])
    for line in info.top_lines():
        squeezed = _squeeze(line)
        if not squeezed or len(squeezed) > 100:
            continue
        if any(v in squeezed for v in vetos):
            continue
        if any(h in squeezed for h in hints):
            return True
    return False


def _other_title_hit(info: PageInfo, statement: str) -> bool:
    return any(
        _title_hit(info, other) for other in TITLE_HINTS if other != statement
    )


def crop_texts(info: PageInfo, statement: str) -> tuple[str | None, str | None]:
    """(start_anchor, stop_anchor) line texts bounding the statement region."""
    begin, end = crop_region(info, statement)
    start_text = info.lines[begin].strip() if begin > 0 or _title_line_index(info, statement) == 0 else None
    if _title_line_index(info, statement) is None:
        start_text = None  # continuation page: start at the top
    stop_text = info.lines[end].strip() if end < len(info.lines) else None
    return start_text, stop_text


def locate_statement(pages: list[PageInfo], statement: str) -> list[int]:
    """Best start page by score, extended through continuation pages."""
    candidates: list[tuple[float, PageInfo]] = []
    for info in pages:
        if info.value_rows < MIN_VALUE_ROWS:
            continue
        if not _title_hit(info, statement):
            continue
        score = info.value_rows + (10.0 if ANCHORS[statement].search(info.text) else 0.0)
        candidates.append((score, info))
    if not candidates:
        raise RuntimeError(f"could not locate {statement} pages")
    best = max(candidates, key=lambda item: (item[0], -item[1].index))[1]
    chosen = [best.index]
    # statements printed across pages often repeat the title on every page:
    # take the whole contiguous title-hit run around the best page
    cursor = best.index - 1
    while cursor >= 0 and pages[cursor].value_rows >= 3 and _title_hit(pages[cursor], statement):
        chosen.insert(0, cursor)
        cursor -= 1
    begin, end = crop_region(best, statement)
    terminal_seen = bool(TERMINALS[statement].search("\n".join(best.lines[begin:end])))
    cursor = chosen[-1]
    while not terminal_seen and len(chosen) <= MAX_CONTINUATIONS:
        cursor += 1
        if cursor >= len(pages):
            break
        info = pages[cursor]
        region_begin, region_end = crop_region(info, statement)
        region = info.lines[region_begin:region_end]
        if _value_row_count(region) < 3:
            break
        chosen.append(info.index)
        terminal_seen = bool(TERMINALS[statement].search("\n".join(region)))
    return chosen
