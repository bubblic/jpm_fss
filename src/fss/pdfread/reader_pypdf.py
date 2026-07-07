"""Line reader over pypdf text (R3).

Same line grammar as R2 but a fully independent PDF text engine (pypdf's
content-stream interpreter rather than pdfminer's layout analysis), so the
two fail differently on glyph ordering, spacing, and ligatures. That
difference is the point: R2 and R3 agreeing is evidence about the text,
not about one library's quirks.
"""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from fss.pdfread.rows import ReaderOutput, parse_text_lines, window_lines


def read_pages(
    pdf_path: Path,
    page_indices: list[int],
    reader: str = "R3_pypdf",
    windows: dict[int, tuple[str | None, str | None]] | None = None,
) -> ReaderOutput:
    document = PdfReader(str(pdf_path))
    lines: list[tuple[int, int, str]] = []
    for page_index in page_indices:
        text = document.pages[page_index].extract_text() or ""
        page_lines = text.splitlines()
        if windows and page_index in windows:
            page_lines = window_lines(page_lines, *windows[page_index])
        for line_no, line in enumerate(page_lines):
            lines.append((page_index, line_no, line))
    return parse_text_lines(lines, reader)
