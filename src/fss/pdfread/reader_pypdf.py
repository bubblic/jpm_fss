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

from fss.pdfread.rows import ReaderOutput, parse_text_lines


def read_pages(pdf_path: Path, page_indices: list[int], reader: str = "R3_pypdf") -> ReaderOutput:
    document = PdfReader(str(pdf_path))
    lines: list[tuple[int, int, str]] = []
    for page_index in page_indices:
        text = document.pages[page_index].extract_text() or ""
        for line_no, line in enumerate(text.splitlines()):
            lines.append((page_index, line_no, line))
    return parse_text_lines(lines, reader)
