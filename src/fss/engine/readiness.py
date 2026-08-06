"""Semantic readiness checks that must pass before scenario projection."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from fss.engine import roles as R
from fss.statements import StatementRow, StructuredStatement

if TYPE_CHECKING:
    from fss.engine.project import Projector


def _row_key(row: StatementRow) -> tuple[str, tuple, str]:
    preferred = (row.preferred_label or "").lower()
    period_role = ""
    if row.period_type == "instant" and "periodstart" in preferred:
        period_role = "start"
    elif row.period_type == "instant" and "periodend" in preferred:
        period_role = "end"
    return (row.concept, row.dims, period_role)


def _material_cutoff(statement: StructuredStatement) -> tuple[str | None, Decimal]:
    latest = statement.columns[0] if statement.columns else None
    scale = max(
        (
            abs(cell.value)
            for row in statement.rows
            if row.kind != "abstract"
            for cell in row.cells
            if cell.period == latest and cell.value is not None
        ),
        default=Decimal("1"),
    )
    return latest, max(Decimal("1"), scale * Decimal("0.01"))


def simulation_readiness(
    projector: "Projector", statements: dict[str, StructuredStatement]
) -> list[str]:
    """Return named semantic blockers before invoking the flow engine."""
    blockers: list[str] = []
    for kind, statement in statements.items():
        latest, cutoff = _material_cutoff(statement)
        unresolved = [
            row.label
            for row in statement.rows
            if row.is_extension
            and row.kind == "leaf"
            and latest
            and (cell := row.cell(latest)) is not None
            and cell.value is not None
            and abs(cell.value) >= cutoff
        ]
        if unresolved:
            blockers.append(f"{kind} unresolved material rows: {unresolved[:6]}")

        role_map = projector.roles[kind]
        broad_defaults = []
        for row in statement.rows:
            if row.kind != "leaf" or not latest:
                continue
            cell = row.cell(latest)
            if cell is None or cell.value is None or abs(cell.value) < cutoff:
                continue
            assignment = role_map.get(_row_key(row))
            if assignment is None:
                broad_defaults.append(row.label)
            elif kind in ("income_statement", "balance_sheet") and assignment.source in (
                "default",
                "section",
            ):
                broad_defaults.append(row.label)
        if broad_defaults:
            blockers.append(f"{kind} material roles need review: {broad_defaults[:6]}")

    required = (
        ("income_statement", {R.REVENUE}, "revenue"),
        ("balance_sheet", {R.CASH}, "cash"),
        ("balance_sheet", {R.RETAINED_EARNINGS}, "retained earnings/equity"),
    )
    for kind, roles, label in required:
        if not projector._rows(statements[kind], roles):
            blockers.append(f"{label} role unresolved")
    operating_costs = {
        R.COGS,
        R.OPEX_RND,
        R.OPEX_SELLING,
        R.OPEX_ADMIN,
        R.OPEX_OTHER,
        R.RESTRUCTURING,
    }
    if not projector._rows(statements["income_statement"], operating_costs):
        blockers.append("operating cost/expense roles unresolved")

    cf = statements["cash_flow"]
    cf_map = projector.roles["cash_flow"]
    cf_roles = {assignment.role for assignment in cf_map.values()}
    if R.CF_CASH_BEGIN in cf_roles and R.CF_CASH_END not in cf_roles:
        blockers.append("cash-flow ending cash role unresolved")
    if R.CF_CASH_END in cf_roles and R.CF_CASH_BEGIN not in cf_roles:
        blockers.append("cash-flow beginning cash role unresolved")
    if R.CF_NET_CHANGE not in cf_roles and R.CF_ACTIVITY_TOTAL not in cf_roles:
        blockers.append("cash-flow net-change/activity role unresolved")

    cf_latest, cf_cutoff = _material_cutoff(cf)
    generic_roles = {
        R.CF_OTHER_NONCASH,
        R.CF_OTHER_INVESTING,
        R.CF_OTHER_FINANCING,
    }
    generic_cash_flows = []
    for row in cf.rows:
        if row.kind != "leaf" or not cf_latest:
            continue
        cell = row.cell(cf_latest)
        assignment = cf_map.get(_row_key(row))
        if (
            cell is not None
            and cell.value is not None
            and abs(cell.value) >= cf_cutoff
            and assignment is not None
            and assignment.role in generic_roles
            and assignment.source in ("default", "section")
        ):
            generic_cash_flows.append(row.label)
    if generic_cash_flows:
        blockers.append(
            f"cash_flow material generic roles need review: {generic_cash_flows[:6]}"
        )

    bs_map = projector.roles["balance_sheet"]
    for row in cf.rows:
        assignment = cf_map.get(_row_key(row))
        if row.kind != "leaf" or assignment is None or assignment.role != R.CF_WC:
            continue
        if not projector._bind_wc_row(row, bs_map):
            blockers.append(f"working-capital binding unresolved: {row.label}")

    debt_rows = projector._rows(statements["balance_sheet"], {R.DEBT, R.COMMERCIAL_PAPER})
    if debt_rows and not cf_roles.intersection({R.CF_DEBT_ISSUE, R.CF_DEBT_REPAY, R.CF_CP_NET}):
        latest = statements["balance_sheet"].columns[0]
        prior = (
            statements["balance_sheet"].columns[1]
            if len(statements["balance_sheet"].columns) > 1
            else None
        )
        if prior:
            debt_change = sum(
                (
                    (row.cell(latest).value or Decimal(0))
                    - (row.cell(prior).value or Decimal(0))
                    for row in debt_rows
                    if row.cell(latest) and row.cell(prior)
                ),
                Decimal(0),
            )
            if debt_change:
                blockers.append("debt changed but financing cash-flow roles are unresolved")
    return blockers
