"""Run the three PDF readers over one statement and package their outputs."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from fss.pdfread import locate, reader_geom, reader_lines, reader_pypdf
from fss.pdfread.rows import ReaderOutput
from fss.pdfread.textnorm import ScalePolicy, detect_scale

logging.getLogger("pdfminer").setLevel(logging.ERROR)


@dataclass
class PdfExtraction:
    statement: str
    pages: list[int]
    scale: ScalePolicy
    readers: dict[str, ReaderOutput]
    notes: list[str] = field(default_factory=list)


def read_statement_pages(
    pdf: Any,
    pdf_path: Path,
    statement: str,
    page_indices: list[int],
    pages_info: list[locate.PageInfo] | None = None,
    text_options: dict[str, float] | None = None,
) -> PdfExtraction:
    """Run the three readers over already-located pages.

    With page metadata available, each page is cropped to this statement's
    region so a page carrying two statements feeds the readers only one.
    """
    windows: dict[int, tuple[str | None, str | None]] | None = None
    if pages_info is not None:
        windows = {
            index: locate.crop_texts(pages_info[index], statement)
            for index in page_indices
            if index < len(pages_info)
        }
    options = text_options or {}
    geometry = reader_geom.read_pages(pdf, page_indices, windows=windows, text_options=options)
    lines = reader_lines.read_pages(pdf, page_indices, windows=windows, text_options=options)
    pypdf_reader = reader_pypdf.read_pages(pdf_path, page_indices, windows=windows)
    header_text = " ".join(geometry.header_lines + lines.header_lines)
    scale = detect_scale(header_text)
    return PdfExtraction(
        statement=statement,
        pages=page_indices,
        scale=scale,
        readers={reader.reader: reader for reader in (geometry, lines, pypdf_reader)},
    )


def extract_pdf_statements(pdf_path: Path) -> dict[str, PdfExtraction]:
    """Locate and read all three core statements from the filing PDF."""
    out: dict[str, PdfExtraction] = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = locate.scan_pages(pdf)
        for statement in ("balance_sheet", "income_statement", "cash_flow"):
            page_indices = locate.locate_statement(pages, statement)
            out[statement] = read_statement_pages(
                pdf, pdf_path, statement, page_indices, pages
            )
    return out
