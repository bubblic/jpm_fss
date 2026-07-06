"""Shared raw-row model and row assembly for the PDF readers.

Both reader families (line-based over extracted text, geometry-based over
word positions) reduce a page to per-line (label, values) pairs and feed
them through one RowAssembler, which applies the shared display grammar:
  - a no-value line ending with a colon is a section header;
  - a no-value line followed by a value line whose label starts lowercase
    (or is empty) is a wrapped-label fragment and merges forward;
  - other no-value lines stand alone ("Commitments and contingencies");
  - page furniture (footers, "See accompanying Notes", bare numbers) drops.
The ways the two families can fail differ (that is the decorrelation), but
"row" means the same thing to both, so their outputs are comparable
cell by cell.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from fss.pdfread.textnorm import NumToken, is_currency_mark, parse_number

JUNK_PATTERNS = re.compile(
    r"^(see accompanying|the accompanying|table of contents$|"
    r"part (i|ii|iii|iv)\b|item \d|f-\d+$|\d+$|\(\d+\)$|"
    r"consolidated\s+(statements?|balance|income)\b|"
    r"[a-z].{0,40}\| \d{4} form 10-k \| \d+$)",
    re.IGNORECASE,
)
# Column-header lines whose only "values" are day-of-month numbers
# ("September 27, September 28,"): every non-numeric word is a date word.
DATE_WORDS = re.compile(
    r"^(january|february|march|april|may|june|july|august|september|october|"
    r"november|december|year|years|ended|ending|as|of|at|and|the|for|in|to|"
    r"fiscal|months?|\d{1,2})[,.]?$",
    re.IGNORECASE,
)


@dataclass
class RawRow:
    kind: str  # "header" | "row" | "bare"
    label: str
    values: list[NumToken | None]  # printed order; None = empty cell (geometry only)
    page: int
    line_no: int
    reader: str
    section: str = ""
    merged_fragment: bool = False


@dataclass
class ReaderOutput:
    reader: str
    rows: list[RawRow]
    header_lines: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def data_rows(self) -> list[RawRow]:
        return [row for row in self.rows if row.kind == "row"]


def is_junk_line(text: str) -> bool:
    return bool(JUNK_PATTERNS.search(text.strip()))


class RowAssembler:
    """Shared display grammar over per-line (label, values) inputs."""

    def __init__(self, reader: str) -> None:
        self.reader = reader
        self.rows: list[RawRow] = []
        self.header_lines: list[str] = []
        self.notes: list[str] = []
        self._section = ""
        self._fragment: tuple[int, int, str] | None = None
        self._seen_values = False

    @staticmethod
    def _year_like(token: NumToken) -> bool:
        """A bare year, possibly with a glued superscript footnote ("20253")."""
        if token.value is None or token.value != token.value.to_integral_value():
            return False
        if "," in token.raw or "." in token.raw:
            return False
        value = int(token.value)
        return 1990 <= value <= 2035 or 19900 <= value <= 20359

    def _is_header_like(self, label_words: list[str], values: list[NumToken]) -> bool:
        """Column-header lines: date words with day numbers ("June 30,"),
        or a line whose numeric tokens are all bare years ("... 2025 2024")."""
        if label_words and all(DATE_WORDS.match(word) for word in label_words):
            return True
        if values and all(self._year_like(token) for token in values):
            return True
        return False

    def feed(
        self, page: int, line_no: int, label: str, values: list[NumToken | None], raw: str
    ) -> None:
        stripped = raw.strip()
        if not stripped or is_junk_line(stripped):
            return
        label = label.strip()
        label_words = label.split()
        real_values = [v for v in values if v is not None]
        if self._is_header_like(label_words, real_values):
            if self._fragment is not None and not self._seen_values:
                # a held no-value line followed by a column-header line is
                # header text (the scale parenthetical), not a row label
                self.header_lines.append(self._fragment[2])
                self._fragment = None
            self.header_lines.append(stripped)
            return
        if real_values and not label and self._fragment is None:
            if not self._seen_values:
                self.header_lines.append(stripped)
            else:
                # an unlabeled value line inside the table is a display row:
                # IFRS filers print section totals with no label at all
                self.rows.append(
                    RawRow(
                        "row", "", list(values), page, line_no, self.reader, self._section
                    )
                )
            return
        if not real_values:
            if not self._seen_values:
                if stripped.endswith(":"):
                    if self._fragment is not None:
                        self.header_lines.append(self._fragment[2])
                        self._fragment = None
                    self._section = stripped.rstrip(":").strip()
                    self.rows.append(
                        RawRow("header", stripped, [], page, line_no, self.reader, self._section)
                    )
                else:
                    # hold the line: it may be the wrapped first row label
                    if self._fragment is not None:
                        self.header_lines.append(self._fragment[2])
                    self._fragment = (page, line_no, stripped)
                return
            if stripped.endswith(":"):
                self._flush_fragment()
                self._section = stripped.rstrip(":").strip()
                self.rows.append(
                    RawRow("header", stripped, [], page, line_no, self.reader, self._section)
                )
            elif self._fragment is None:
                self._fragment = (page, line_no, stripped)
            else:
                self._flush_fragment()
                self._fragment = (page, line_no, stripped)
            return
        self._seen_values = True
        merged = False
        if self._fragment is not None:
            fragment_text = self._fragment[2]
            # a continuation label starts lowercase, with a digit, or with
            # punctuation ("and 7,434 ...", "$650, respectively ...")
            continues = not label or not label[:1].isalpha() or label[:1].islower()
            if continues:
                label = f"{fragment_text} {label}".strip()
                merged = True
            else:
                self._flush_fragment()
            self._fragment = None
        self.rows.append(
            RawRow(
                "row",
                label,
                list(values),
                page,
                line_no,
                self.reader,
                self._section,
                merged_fragment=merged,
            )
        )

    def _flush_fragment(self) -> None:
        if self._fragment is not None:
            page, line_no, text = self._fragment
            self.rows.append(RawRow("bare", text, [], page, line_no, self.reader, self._section))
            # a standalone no-value line acts as a section header even
            # without a colon (IFRS statements often print them that way)
            self._section = text.rstrip(":").strip()
            self._fragment = None

    def finish(self) -> ReaderOutput:
        self._flush_fragment()
        return ReaderOutput(self.reader, self.rows, self.header_lines, self.notes)


def split_trailing_values(tokens: list[str]) -> tuple[list[str], list[NumToken]]:
    """Split whitespace tokens into (label tokens, trailing value run).

    Walks from the right taking numeric tokens; bare currency marks between
    numbers are absorbed; the first other token ends the run. A number GLUED
    to a currency symbol ("$944") is label prose, not a column value
    (tables print the symbol separated and aligned), so it terminates the
    run; this keeps label-embedded amounts ("allowance of $944 and $830")
    out of the value columns.
    """
    values: list[NumToken] = []
    cut = len(tokens)
    index = len(tokens) - 1
    while index >= 0:
        token = tokens[index]
        if is_currency_mark(token):
            cut = index
            index -= 1
            continue
        if len(token) > 1 and token[0] in "$€£¥":
            break
        parsed = parse_number(token)
        if parsed is None:
            break
        values.append(parsed)
        cut = index
        index -= 1
    values.reverse()
    return tokens[:cut], values


def parse_text_lines(lines: list[tuple[int, int, str]], reader: str) -> ReaderOutput:
    """Line-based parsing shared by the two text-engine readers."""
    assembler = RowAssembler(reader)
    for page, line_no, text in lines:
        tokens = text.split()
        label_tokens, values = split_trailing_values(tokens)
        assembler.feed(page, line_no, " ".join(label_tokens), list(values), text)
    return assembler.finish()
