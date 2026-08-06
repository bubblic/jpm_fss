from decimal import Decimal

from fss.engine.project import Projector
from fss.engine.readiness import simulation_readiness
from fss.statements import Cell, StatementRow, StructuredStatement


def _row(
    order,
    concept,
    label,
    value,
    balance,
    section,
    *,
    extension=False,
    preferred=None,
    period_type="instant",
):
    return StatementRow(
        order=order,
        concept=concept,
        dims=(),
        label=label,
        depth=1,
        kind="leaf",
        derivation="",
        preferred_label=preferred,
        negated=False,
        displayed_sign=1,
        period_type=period_type,
        balance=balance,
        is_monetary=True,
        is_extension=extension,
        anchor=None,
        section=(section,),
        cells=(Cell("I2025-12-31", Decimal(value), -6, "USD"),),
    )


def _statement(kind, rows):
    return StructuredStatement(
        company="test",
        standard="us-gaap",
        statement=kind,
        linkrole=f"test:{kind}",
        role_definition=kind,
        currency="USD",
        columns=("I2025-12-31",),
        rows=rows,
    )


def _statements(*, unresolved=False, unbound_wc=False, broad_default=False, generic_cf=False):
    start = "http://www.xbrl.org/2003/role/periodStartLabel"
    end = "http://www.xbrl.org/2003/role/periodEndLabel"
    bs = _statement(
        "balance_sheet",
        [
            _row(0, "us-gaap:CashAndCashEquivalentsAtCarryingValue", "Cash", "100", "debit", "assets"),
            _row(1, "us-gaap:RetainedEarningsAccumulatedDeficit", "Retained earnings", "70", "credit", "equity"),
            _row(
                2,
                "doc:Unresolved_2",
                "Unresolved operating asset",
                "50" if unresolved else "0",
                "debit",
                "assets",
                extension=True,
            ),
        ],
    )
    inc = _statement(
        "income_statement",
        [
            _row(
                0,
                "us-gaap:Revenue",
                "Revenue",
                "1000",
                "credit",
                "income",
                period_type="duration",
            ),
            _row(
                1,
                "us-gaap:CostOfRevenue",
                "Cost of revenue",
                "600",
                "debit",
                "income",
                period_type="duration",
            ),
        ],
    )
    cf_rows = [
        _row(0, "us-gaap:CashAndCashEquivalentsAtCarryingValue", "Cash beginning", "90", "debit", "cash", preferred=start),
        _row(1, "us-gaap:CashAndCashEquivalentsAtCarryingValue", "Cash ending", "100", "debit", "cash", preferred=end),
    ]
    if unbound_wc:
        cf_rows.append(
            _row(
                2,
                "us-gaap:IncreaseDecreaseInInventories",
                "Increase in inventories",
                "10",
                "debit",
                "operating activities - changes in working capital",
                period_type="duration",
            )
        )
    if generic_cf:
        cf_rows.append(
            _row(
                3,
                "us-gaap:UnclassifiedInvestingCashFlow",
                "Other investing activity",
                "20",
                "debit",
                "investing activities",
                period_type="duration",
            )
        )
    if broad_default:
        bs.rows.append(
            _row(
                3,
                "us-gaap:UnclassifiedAsset",
                "Unclassified asset",
                "50",
                "debit",
                "assets",
            )
        )
    cf = _statement("cash_flow", cf_rows)
    return {"balance_sheet": bs, "income_statement": inc, "cash_flow": cf}


def test_material_document_local_row_blocks_simulation():
    statements = _statements(unresolved=True)
    blockers = simulation_readiness(Projector("test", statements), statements)
    assert any("unresolved material rows" in blocker for blocker in blockers)


def test_unbound_working_capital_row_blocks_simulation():
    statements = _statements(unbound_wc=True)
    blockers = simulation_readiness(Projector("test", statements), statements)
    assert "working-capital binding unresolved: Increase in inventories" in blockers


def test_material_broad_default_role_blocks_simulation():
    statements = _statements(broad_default=True)
    blockers = simulation_readiness(Projector("test", statements), statements)
    assert any("balance_sheet material roles need review" in blocker for blocker in blockers)


def test_material_generic_cash_flow_role_blocks_simulation():
    statements = _statements(generic_cf=True)
    blockers = simulation_readiness(Projector("test", statements), statements)
    assert any("cash_flow material generic roles need review" in blocker for blocker in blockers)
