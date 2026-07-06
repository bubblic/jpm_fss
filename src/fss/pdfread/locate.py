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
    "balance_sheet": ("balance sheet", "statement of financial position", "statements of financial position"),
    "income_statement": (
        "statement of operations",
        "statements of operations",
        "income statement",
        "income statements",
        "statement of income",
        "statements of income",
    ),
    "cash_flow": ("statement of cash flows", "statements of cash flows", "cash flows statement"),
}
TITLE_VETO: dict[str, tuple[str, ...]] = {
    "balance_sheet": ("parenthetical",),
    "income_statement": ("parenthetical", "comprehensive"),
    "cash_flow": ("parenthetical",),
}
ANCHORS: dict[str, re.Pattern[str]] = {
    "balance_sheet": re.compile(r"^total assets\b", re.IGNORECASE | re.MULTILINE),
    "income_statement": re.compile(
        r"per share|income tax|profit before tax", re.IGNORECASE
    ),
    "cash_flow": re.compile(r"operating activities", re.IGNORECASE),
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


def scan_pages(pdf: Any) -> list[PageInfo]:
    pages: list[PageInfo] = []
    for index, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lines = text.splitlines()
        pages.append(PageInfo(index, text, lines, _value_row_count(lines)))
    return pages


def _title_hit(info: PageInfo, statement: str) -> bool:
    hints = TITLE_HINTS[statement]
    vetos = TITLE_VETO[statement]
    for line in info.top_lines():
        lowered = " ".join(line.lower().split())
        if len(lowered) > 110:
            continue
        if any(v in lowered for v in vetos):
            continue
        if any(h in lowered for h in hints):
            return True
    return False


def _other_title_hit(info: PageInfo, statement: str) -> bool:
    return any(
        _title_hit(info, other) for other in TITLE_HINTS if other != statement
    )


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
    terminal_seen = bool(TERMINALS[statement].search(best.text))
    cursor = best.index
    while not terminal_seen and len(chosen) <= MAX_CONTINUATIONS:
        cursor += 1
        if cursor >= len(pages):
            break
        info = pages[cursor]
        if info.value_rows < MIN_VALUE_ROWS:
            break
        if _other_title_hit(info, statement):
            break
        chosen.append(info.index)
        terminal_seen = bool(TERMINALS[statement].search(info.text))
    return chosen
