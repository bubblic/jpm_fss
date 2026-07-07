"""Line reader over pdfplumber text (R2).

Consumes the linearized text of the located pages and applies the shared
trailing-value grammar. Shares the pdfplumber text engine with R1 but none
of its geometry; shares the line grammar with R3 but not its text engine.
"""
from __future__ import annotations

from typing import Any

from fss.pdfread.rows import ReaderOutput, parse_text_lines, window_lines


def read_pages(
    pdf: Any,
    page_indices: list[int],
    reader: str = "R2_lines",
    windows: dict[int, tuple[str | None, str | None]] | None = None,
) -> ReaderOutput:
    lines: list[tuple[int, int, str]] = []
    for page_index in page_indices:
        page = pdf.pages[page_index]
        text = page.extract_text() or ""
        page_lines = text.splitlines()
        if windows and page_index in windows:
            page_lines = window_lines(page_lines, *windows[page_index])
        for line_no, line in enumerate(page_lines):
            lines.append((page_index, line_no, line))
    return parse_text_lines(lines, reader)
