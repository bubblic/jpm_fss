"""Encode/decode: lossless reduction and the injectivity guards."""
from decimal import Decimal

from fss.encdec import encode, decode, verify_reconstruction
from fss.statements import Cell, StatementRow, StructuredStatement


def _row(order, concept, label, kind, values, derivation="", preferred=None, period_type="instant"):
    cells = tuple(
        Cell(period, None if v is None else Decimal(v), -6, "USD")
        for period, v in values
    )
    return StatementRow(
        order=order,
        concept=concept,
        dims=(),
        label=label,
        depth=1,
        kind=kind,
        derivation=derivation,
        preferred_label=preferred,
        negated=False,
        displayed_sign=1,
        period_type=period_type,
        balance="debit",
        is_monetary=True,
        is_extension=False,
        anchor=None,
        section=("Assets",),
        cells=cells,
    )


def _statement(rows, calc):
    return StructuredStatement(
        company="test",
        standard="us-gaap",
        statement="balance_sheet",
        linkrole="http://example/role",
        role_definition="TEST",
        currency="USD",
        columns=("I2025-12-31",),
        rows=rows,
        calc_children=calc,
    )


def test_subtotal_dropped_from_z_and_reconstructed():
    rows = [
        _row(0, "t:A", "Alpha", "leaf", [("I2025-12-31", "60")]),
        _row(1, "t:B", "Beta", "leaf", [("I2025-12-31", "40")]),
        _row(2, "t:T", "Total", "derived", [("I2025-12-31", "100")], derivation="calc"),
    ]
    statement = _statement(rows, {"t:T": [("t:A", Decimal(1)), ("t:B", Decimal(1))]})
    encoded = encode(statement)
    assert "t:T" not in encoded.z  # the lossless reduction
    assert verify_reconstruction(statement).exact


def test_filer_rounded_subtotal_demoted_and_still_exact():
    rows = [
        _row(0, "t:A", "Alpha", "leaf", [("I2025-12-31", "60")]),
        _row(1, "t:B", "Beta", "leaf", [("I2025-12-31", "40")]),
        _row(2, "t:T", "Total", "derived", [("I2025-12-31", "101")], derivation="calc"),
    ]
    statement = _statement(rows, {"t:T": [("t:A", Decimal(1)), ("t:B", Decimal(1))]})
    encoded = encode(statement)
    assert "t:T" in encoded.z  # stored verbatim, discrepancy disclosed
    assert encoded.demotions
    assert verify_reconstruction(statement).exact


def test_period_role_keeps_beginning_and_ending_cash_distinct():
    start = "http://www.xbrl.org/2003/role/periodStartLabel"
    end = "http://www.xbrl.org/2003/role/periodEndLabel"
    rows = [
        _row(0, "t:Cash", "Cash, beginning", "leaf", [("D2025-01-01:2025-12-31", "10")], preferred=start),
        _row(1, "t:Cash", "Cash, ending", "leaf", [("D2025-01-01:2025-12-31", "25")], preferred=end),
    ]
    statement = _statement(rows, {})
    statement.columns = ("D2025-01-01:2025-12-31",)
    encoded = encode(statement)
    assert encoded.z["t:Cash@start"] != encoded.z["t:Cash@end"]
    decoded = decode(encoded)
    assert decoded.rows[0].cells[0].value == Decimal(10)
    assert decoded.rows[1].cells[0].value == Decimal(25)
