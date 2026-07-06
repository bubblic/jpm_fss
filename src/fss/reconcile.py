"""Reconciliation gate: accept a field only when independent readers agree.

Policy (independence-weighted, per the proposal): the geometry reader R1
consumes word positions; R2 and R3 share a line grammar but use different
text engines. A cell is accepted when R1 agrees exactly with at least one
line reader; when R1 has no reading, R2 and R3 agreeing with each other is
accepted with a weaker rule tag (they are decorrelated as text engines but
correlated in alignment logic). Anything else is flagged, never guessed.
Flags cost review time; only silent concordant error costs correctness.

Also provides the ground-truth comparison used to measure the PDF-only
mode's per-field accuracy against the tag path.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from decimal import Decimal

from fss.kg import normalize_label
from fss.pdfread.assemble import PdfExtraction
from fss.pdfread.rows import RawRow
from fss.pdfread.textnorm import NumToken, strip_footnote_marks
from fss.statements import StructuredStatement


NOTE_REF = re.compile(r"\(\s*(?:[A-Za-z]{1,2}\.)?\d{1,2}(?:\.\d+)?\s*\)[,;]?")
TRAILING_NOTE_REFS = re.compile(r"(?:\s+\d{1,2}(?:\s*,\s*\d{1,2})*)$")


def canon_label(label: str) -> str:
    """Alignment key: footnote marks, note references, and label-embedded
    numbers (par values, share counts, allowance amounts) do not distinguish
    display rows, and readers split them differently, so digits drop out."""
    text = NOTE_REF.sub(" ", label)
    text = TRAILING_NOTE_REFS.sub("", text.strip())
    normalized = normalize_label(strip_footnote_marks(text))
    return " ".join(word for word in normalized.split() if not word.isdigit())


@dataclass
class FieldProvenance:
    label: str
    section: str
    column: int
    readings: dict[str, str]  # reader -> printed token (or "" when absent)
    accepted_printed: Decimal | None
    rule: str  # "R1+line" | "lines_only" | "empty" | "flagged"


@dataclass
class ReconciledRow:
    label: str
    section: str
    printed: list[Decimal | None]
    values: list[Decimal | None]  # after scale
    dash: list[bool]  # True where readers agreed the cell shows a dash
    scale: Decimal
    provenance: list[FieldProvenance]


@dataclass
class ReconciledStatement:
    statement: str
    pages: list[int]
    n_columns: int
    rows: list[ReconciledRow]
    flags: list[FieldProvenance]
    reader_extras: dict[str, list[str]]
    notes: list[str] = field(default_factory=list)

    @property
    def accepted_cells(self) -> int:
        return sum(
            1 for row in self.rows for cell in row.values if cell is not None
        )


def _align(anchor: list[RawRow], other: list[RawRow]) -> dict[int, int]:
    """Map anchor row index -> other row index via label sequence matching."""
    a_labels = [canon_label(row.label) for row in anchor]
    b_labels = [canon_label(row.label) for row in other]
    matcher = difflib.SequenceMatcher(None, a_labels, b_labels, autojunk=False)
    mapping: dict[int, int] = {}
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        if op == "equal":
            for offset in range(a1 - a0):
                mapping[a0 + offset] = b0 + offset
    return mapping


def _right_align(tokens: list[NumToken | None], width: int) -> tuple[list[NumToken | None], bool]:
    real = list(tokens)
    if len(real) == width:
        return real, False
    if len(real) > width:
        return real[-width:], True
    return [None] * (width - len(real)) + real, False


def _token_value(token: NumToken | None) -> Decimal | None:
    if token is None:
        return None
    return token.value  # dash tokens carry None


def _is_dash(token: NumToken | None) -> bool:
    return token is not None and token.kind == "dash"


def reconcile(extraction: PdfExtraction) -> ReconciledStatement:
    geometry = extraction.readers["R1_geometry"]
    lines = extraction.readers["R2_lines"]
    pypdf_reader = extraction.readers["R3_pypdf"]
    g_rows = geometry.data_rows()
    l2_rows = lines.data_rows()
    l3_rows = pypdf_reader.data_rows()
    n_columns = max((len(row.values) for row in g_rows), default=0)

    map2 = _align(g_rows, l2_rows)
    map3 = _align(g_rows, l3_rows)
    used2 = set(map2.values())
    used3 = set(map3.values())

    rows: list[ReconciledRow] = []
    flags: list[FieldProvenance] = []
    for index, g_row in enumerate(g_rows):
        r2 = l2_rows[map2[index]] if index in map2 else None
        r3 = l3_rows[map3[index]] if index in map3 else None
        g_vals, _ = _right_align(g_row.values, n_columns)
        v2, trunc2 = _right_align(r2.values, n_columns) if r2 else ([None] * n_columns, False)
        v3, trunc3 = _right_align(r3.values, n_columns) if r3 else ([None] * n_columns, False)
        scale = extraction.scale.scale_for(g_row.label, g_row.section)
        # value-shape override: only per-share amounts print with decimal
        # fractions on a scaled statement, whatever the label says
        fractional = [
            token
            for token in g_row.values
            if token is not None
            and token.value is not None
            and token.value != token.value.to_integral_value()
        ]
        if fractional and len(fractional) == len(
            [t for t in g_row.values if t is not None and t.value is not None]
        ):
            scale = Decimal(1)
        printed: list[Decimal | None] = []
        values: list[Decimal | None] = []
        dashes: list[bool] = []
        provenance: list[FieldProvenance] = []
        for column in range(n_columns):
            tokens = {
                "R1_geometry": g_vals[column],
                "R2_lines": v2[column],
                "R3_pypdf": v3[column],
            }
            readings = {
                reader: ("" if token is None else token.raw)
                for reader, token in tokens.items()
            }
            g, a, b = tokens["R1_geometry"], tokens["R2_lines"], tokens["R3_pypdf"]
            gv, av, bv = _token_value(g), _token_value(a), _token_value(b)
            accepted: Decimal | None = None
            dash = False
            if gv is not None and (gv == av or gv == bv):
                rule = "R1+line"
                accepted = gv
            elif _is_dash(g) and (_is_dash(a) or _is_dash(b)):
                rule = "dash"
                dash = True
            elif g is None and av is not None and av == bv:
                rule = "lines_only"
                accepted = av
            elif g is None and _is_dash(a) and _is_dash(b):
                rule = "dash"
                dash = True
            elif g is None and a is None and b is None:
                rule = "empty"
            else:
                rule = "flagged"
            prov = FieldProvenance(
                g_row.label, g_row.section, column, readings, accepted, rule
            )
            provenance.append(prov)
            if rule == "flagged":
                flags.append(prov)
            printed.append(accepted)
            dashes.append(dash)
            values.append(accepted * scale if accepted is not None else None)
        if trunc2 or trunc3:
            flags.append(
                FieldProvenance(
                    g_row.label,
                    g_row.section,
                    -1,
                    {"note": "line reader produced more tokens than columns"},
                    None,
                    "flagged",
                )
            )
        rows.append(
            ReconciledRow(
                g_row.label, g_row.section, printed, values, dashes, scale, provenance
            )
        )

    extras = {
        "R2_lines": [row.label for i, row in enumerate(l2_rows) if i not in used2],
        "R3_pypdf": [row.label for i, row in enumerate(l3_rows) if i not in used3],
    }
    return ReconciledStatement(
        statement=extraction.statement,
        pages=extraction.pages,
        n_columns=n_columns,
        rows=rows,
        flags=flags,
        reader_extras=extras,
        notes=list(extraction.notes),
    )


# ---------------------------------------------------------------------------
# Ground-truth comparison (measures the PDF-only mode against the tag path)
# ---------------------------------------------------------------------------


@dataclass
class CellComparison:
    label: str
    column: int
    ground_truth: Decimal | None
    pdf: Decimal | None
    status: str  # "match" | "mismatch" | "missing_pdf" | "flagged"


@dataclass
class AccuracyReport:
    company: str
    statement: str
    compared: int
    matches: int
    mismatches: list[CellComparison]
    missing: list[CellComparison]
    flagged_cells: int
    # GT rows with values that no PDF row matched: (label, kind, unit)
    gt_rows_unmatched: list[tuple[str, str, str]]
    pdf_rows_unmatched: list[str]  # PDF rows no GT row matched (junk watch)

    @property
    def accepted_accuracy(self) -> tuple[int, int]:
        return self.matches, self.compared


def compare_to_ground_truth(
    company: str, reconciled: ReconciledStatement, ground_truth: StructuredStatement
) -> AccuracyReport:
    gt_rows = [
        row
        for row in ground_truth.rows
        if row.kind != "abstract" and any(cell.value is not None for cell in row.cells)
    ]
    gt_labels = [canon_label(row.label) for row in gt_rows]
    pdf_rows = reconciled.rows
    pdf_labels = [canon_label(row.label) for row in pdf_rows]
    matcher = difflib.SequenceMatcher(None, gt_labels, pdf_labels, autojunk=False)
    pairs: list[tuple[int, int]] = []
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        if op == "equal":
            pairs.extend((a0 + k, b0 + k) for k in range(a1 - a0))
        elif op == "replace" and (a1 - a0) == 1 and (b1 - b0) == 1:
            # unique gap between matched anchors: the same display row under
            # a drifting label ("Total operating expense(s)"); pair it
            pairs.append((a0, b0))
    matched_gt = {a for a, _ in pairs}
    matched_pdf = {b for _, b in pairs}

    n_columns = min(len(ground_truth.columns), reconciled.n_columns)
    compared = 0
    matches = 0
    mismatches: list[CellComparison] = []
    missing: list[CellComparison] = []
    flagged = 0
    flagged_keys = {
        (canon_label(prov.label), prov.column)
        for prov in (flag for row in pdf_rows for flag in row.provenance)
        if prov.rule == "flagged"
    }
    for gt_index, pdf_index in pairs:
        gt_row = gt_rows[gt_index]
        pdf_row = pdf_rows[pdf_index]
        for column in range(n_columns):
            gt_value = gt_row.displayed(ground_truth.columns[column])
            pdf_value = pdf_row.values[column]
            is_dash = pdf_row.dash[column]
            if gt_value is None and pdf_value is None and not is_dash:
                continue
            key = (canon_label(pdf_row.label), column)
            if key in flagged_keys:
                flagged += 1
                continue
            if is_dash:
                # a printed dash denotes zero (or an untagged empty cell)
                if gt_value is None:
                    continue
                compared += 1
                if gt_value == 0:
                    matches += 1
                else:
                    mismatches.append(
                        CellComparison(gt_row.label, column, gt_value, Decimal(0), "mismatch")
                    )
                continue
            if pdf_value is None:
                missing.append(
                    CellComparison(gt_row.label, column, gt_value, None, "missing_pdf")
                )
                continue
            compared += 1
            if gt_value is not None and pdf_value == gt_value:
                matches += 1
            else:
                mismatches.append(
                    CellComparison(gt_row.label, column, gt_value, pdf_value, "mismatch")
                )
    # A GT row can duplicate another row's concept and values (IFRS filers
    # tag the section header and its total with one concept); when a matched
    # twin carried the same values, the unmatched twin is benign.
    matched_keys = {
        (gt_rows[a].concept, gt_rows[a].dims, tuple(c.value for c in gt_rows[a].cells))
        for a, _ in pairs
    }
    gt_unmatched = []
    for i in range(len(gt_rows)):
        if i in matched_gt:
            continue
        key = (gt_rows[i].concept, gt_rows[i].dims, tuple(c.value for c in gt_rows[i].cells))
        if key in matched_keys:
            continue  # duplicate of a row already compared
        row = gt_rows[i]
        unit = next((cell.unit for cell in row.cells if cell.unit), "")
        gt_unmatched.append((row.label, row.kind, unit or ""))
    return AccuracyReport(
        company=company,
        statement=reconciled.statement,
        compared=compared,
        matches=matches,
        mismatches=mismatches,
        missing=missing,
        flagged_cells=flagged,
        gt_rows_unmatched=gt_unmatched,
        pdf_rows_unmatched=[
            pdf_rows[i].label for i in range(len(pdf_rows)) if i not in matched_pdf
        ],
    )
