"""Seeded-error battery: the agreement gate must flag, never guess.

The proposal requires that seeded read-errors are caught and disagreements
surfaced rather than silently resolved. Each test corrupts one reader's
tokens and asserts the gate abstains (flags) or survives via the
independence rule, and never accepts a wrong value silently.
"""
from decimal import Decimal

from fss.pdfread.assemble import PdfExtraction
from fss.pdfread.rows import RawRow, ReaderOutput
from fss.pdfread.textnorm import NumToken, ScalePolicy
from fss.reconcile import reconcile

POLICY = ScalePolicy(Decimal(1), Decimal(1), "test")


def _token(value: str) -> NumToken:
    return NumToken(Decimal(value), "plain", value)


def _reader(name: str, rows: list[tuple[str, list[str]]]) -> ReaderOutput:
    return ReaderOutput(
        name,
        [
            RawRow("row", label, [_token(v) for v in values], 0, i, name, "")
            for i, (label, values) in enumerate(rows)
        ],
    )


def _extraction(r1_rows, r2_rows, r3_rows) -> PdfExtraction:
    return PdfExtraction(
        statement="balance_sheet",
        pages=[0],
        scale=POLICY,
        readers={
            "R1_geometry": _reader("R1_geometry", r1_rows),
            "R2_lines": _reader("R2_lines", r2_rows),
            "R3_pypdf": _reader("R3_pypdf", r3_rows),
        },
    )


CLEAN = [("Cash", ["100", "90"]), ("Receivables", ["50", "40"])]


def test_clean_agreement_accepts():
    reconciled = reconcile(_extraction(CLEAN, CLEAN, CLEAN))
    assert not reconciled.flags
    assert reconciled.rows[0].values == [Decimal(100), Decimal(90)]


def test_single_reader_corruption_still_accepts_but_only_with_majority():
    corrupted = [("Cash", ["100", "90"]), ("Receivables", ["58", "40"])]  # 50 -> 58
    reconciled = reconcile(_extraction(CLEAN, corrupted, CLEAN))
    # R1 agrees with R3: accepted, and the correct value wins
    assert reconciled.rows[1].values[0] == Decimal(50)


def test_geometry_corruption_flags_cell():
    corrupted = [("Cash", ["100", "90"]), ("Receivables", ["58", "40"])]
    reconciled = reconcile(_extraction(corrupted, CLEAN, CLEAN))
    # R1 disagrees with both line readers: the gate abstains (line readers
    # alone are not independent enough to outvote positional evidence)
    flagged = [f for f in reconciled.flags if f.label == "Receivables"]
    assert flagged
    assert reconciled.rows[1].values[0] is None


def test_correlated_line_reader_error_does_not_win():
    corrupted = [("Cash", ["100", "90"]), ("Receivables", ["58", "40"])]  # both lines wrong
    reconciled = reconcile(_extraction(CLEAN, corrupted, corrupted))
    # geometry disagrees with the identical line-reader error: flag, not accept
    flagged = [f for f in reconciled.flags if f.label == "Receivables"]
    assert flagged
    assert reconciled.rows[1].values[0] is None


def test_missing_geometry_row_accepts_lines_agreement():
    r1 = [("Cash", ["100", "90"])]
    reconciled = reconcile(_extraction(r1, CLEAN, CLEAN))
    # the receivables row exists only in the line readers; their agreement
    # is accepted under the weaker lines-only rule and recorded as an extra
    assert reconciled.reader_extras["R2_lines"] == ["Receivables"]
