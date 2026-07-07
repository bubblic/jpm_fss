"""Geometry reader (R1): word positions -> visual lines -> column bands.

Consumes pdfplumber word boxes. Value columns are found by clustering the
right edges of numeric tokens across the page (statement figures are
right-justified); a band must be supported by a quarter of the value lines,
which filters label-embedded numbers ("...15,116,786 shares issued...") and
stray figures. Rows carry band-aligned values with explicit gaps, which the
line readers cannot see, and that positional knowledge is exactly what makes
this reader decorrelated from them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fss.pdfread.rows import RowAssembler, ReaderOutput
from fss.pdfread.textnorm import NumToken, is_currency_mark, parse_number

LINE_TOLERANCE = 2.6  # points: words within this vertical distance share a line
BAND_GAP = 12.0  # points: right-edge gap that separates two columns
BAND_ATTACH = 24.0  # max distance from band center to attach a token
MIN_BAND_SHARE = 0.25  # a band needs support on this share of value lines


@dataclass
class _Word:
    text: str
    x0: float
    x1: float
    top: float


def _cluster_lines(words: list[_Word]) -> list[list[_Word]]:
    lines: list[list[_Word]] = []
    for word in sorted(words, key=lambda w: (w.top, w.x0)):
        if lines and abs(word.top - lines[-1][0].top) <= LINE_TOLERANCE:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [_repair_line(sorted(line, key=lambda w: w.x0)) for line in lines]


_FRAGMENT_GAP = 8.0  # points: split-number fragments sit closer than columns


def _repair_line(line: list[_Word]) -> list[_Word]:
    """Merge number fragments the PDF generator broke apart.

    Position-aware version of rows.repair_tokens: two adjacent tokens merge
    when they sit within a sub-column gap and the joint (also with bare
    digit fragments like "7" + "53") parses as one number while the left
    piece alone is incomplete or suspiciously short.
    """
    from fss.pdfread.rows import _PARTIAL_NUMBER, _incomplete
    from fss.pdfread.textnorm import parse_number

    repaired: list[_Word] = []
    for word in line:
        previous = repaired[-1] if repaired else None
        if previous is not None and (word.x0 - previous.x1) < _FRAGMENT_GAP:
            joint = previous.text + word.text
            closes = (
                word.text == ")"
                and previous.text.startswith("(")
                and parse_number(joint) is not None
            )
            grows = _incomplete(previous.text) and _PARTIAL_NUMBER.match(joint)
            digit_pair = (
                previous.text.replace("(", "").replace(",", "").isdigit()
                and word.text.replace(")", "").replace(",", "").replace(".", "").isdigit()
                and parse_number(joint) is not None
            )
            if closes or grows or digit_pair:
                repaired[-1] = _Word(joint, previous.x0, word.x1, previous.top)
                continue
        repaired.append(word)
    return repaired


def _numeric_words(line: list[_Word]) -> list[tuple[_Word, NumToken]]:
    out = []
    for word in line:
        if is_currency_mark(word.text):
            continue
        token = parse_number(word.text)
        if token is not None:
            out.append((word, token))
    return out


def _detect_bands(lines: list[list[_Word]], page_width: float) -> list[float]:
    """Cluster right edges of numeric tokens into column band centers.

    A candidate band whose tokens are overwhelmingly bare small integers
    (note references such as "12" in an IFRS "Notes" column) is dropped when
    real value bands exist to its right.
    """
    edged: list[tuple[float, NumToken]] = []
    value_lines = 0
    for line in lines:
        numerics = _numeric_words(line)
        if not numerics:
            continue
        value_lines += 1
        edged.extend(
            (word.x1, token)
            for word, token in numerics
            if word.x1 > 0.35 * page_width
        )
    if not edged:
        return []
    edged.sort(key=lambda pair: pair[0])
    clusters: list[list[tuple[float, NumToken]]] = [[edged[0]]]
    for pair in edged[1:]:
        if pair[0] - clusters[-1][-1][0] <= BAND_GAP:
            clusters[-1].append(pair)
        else:
            clusters.append([pair])
    min_support = max(4, int(MIN_BAND_SHARE * value_lines))
    kept = [cluster for cluster in clusters if len(cluster) >= min_support]

    def is_note_band(cluster: list[tuple[float, NumToken]]) -> bool:
        small = sum(
            1
            for _, token in cluster
            if token.value is not None
            and token.value == token.value.to_integral_value()
            and 0 <= int(token.value) <= 99
            and "," not in token.raw
            and "." not in token.raw
            and "(" not in token.raw
        )
        return small >= 0.8 * len(cluster)

    while len(kept) > 1 and is_note_band(kept[0]):
        kept = kept[1:]
    return [sum(edge for edge, _ in cluster) / len(cluster) for cluster in kept]


def read_pages(
    pdf: Any,
    page_indices: list[int],
    reader: str = "R1_geometry",
    windows: dict[int, tuple[str | None, str | None]] | None = None,
    text_options: dict[str, float] | None = None,
    page_options: dict[int, dict[str, float] | None] | None = None,
) -> ReaderOutput:
    from fss.pdfread.rows import window_lines

    assembler = RowAssembler(reader)
    for page_index in page_indices:
        page = pdf.pages[page_index]
        options = (page_options or {}).get(page_index) or text_options or {}
        words = [
            _Word(w["text"], float(w["x0"]), float(w["x1"]), float(w["top"]))
            for w in page.extract_words(keep_blank_chars=False, **options)
        ]
        lines = _cluster_lines(words)
        if windows and page_index in windows:
            texts = [" ".join(word.text for word in line) for line in lines]
            kept = window_lines(texts, *windows[page_index])
            if kept:
                keep_set = set()
                cursor = 0
                for index, text in enumerate(texts):
                    if cursor < len(kept) and text == kept[cursor]:
                        keep_set.add(index)
                        cursor += 1
                lines = [line for index, line in enumerate(lines) if index in keep_set]
        bands = _detect_bands(lines, float(page.width))
        if not bands:
            assembler.notes.append(f"page {page_index}: no value bands found")
            continue
        for line_no, line in enumerate(lines):
            raw = " ".join(word.text for word in line)
            numerics = _numeric_words(line)
            slots: list[NumToken | None] = [None] * len(bands)
            used_ids: set[int] = set()
            for word, token in numerics:
                distances = [abs(word.x1 - center) for center in bands]
                best = min(range(len(bands)), key=lambda i: distances[i])
                if distances[best] <= BAND_ATTACH and slots[best] is None:
                    slots[best] = token
                    used_ids.add(id(word))
            label_words = [
                word.text
                for word in line
                if id(word) not in used_ids
                and not is_currency_mark(word.text)
                and word.x0 < min(bands) - 4.0
            ]
            # words that sit inside the band zone but were not numeric stay
            # out of the label (column headers handle themselves upstream)
            label = " ".join(label_words)
            if all(slot is None for slot in slots):
                assembler.feed(page_index, line_no, raw if raw else label, [], raw)
            else:
                assembler.feed(page_index, line_no, label, slots, raw)
    return assembler.finish()
