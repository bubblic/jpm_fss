"""Validation: footing checks on extracted statements and the plausibility
battery on simulated statements.

Footing uses the decimals-based tolerance (0.5 * 10^-decimals * (n+1));
simulated statements are held to exact identities (the engine constructs
them, so anything off is a defect) plus accountant-style plausibility
bounds.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fss.engine.project import ProjectedPeriod
from fss.statements import StructuredStatement

HALF = Decimal("0.5")


@dataclass(frozen=True)
class FootingCheck:
    statement: str
    label: str
    period: str
    computed: Decimal
    reported: Decimal
    diff: Decimal
    tolerance: Decimal
    passed: bool


def footing_checks(statement: StructuredStatement) -> list[FootingCheck]:
    """Every derived cell against the weighted sum of its immediate
    children's reported values, with the decimals-based tolerance.

    Footing is a per-level check by definition: each printed subtotal is
    compared with the addends the filer printed next to it. (Recomputing
    from leaves through nested subtotals would compound the filer's
    per-line roundings across levels and test something no reader of the
    statement would compute.)
    """
    checks: list[FootingCheck] = []
    reported: dict[str, dict[tuple[str, tuple], Decimal]] = {}
    for period in statement.columns:
        reported[period] = {
            (row.concept, row.dims): row.cell(period).value
            for row in statement.rows
            if row.kind != "abstract" and row.cell(period) and row.cell(period).value is not None
        }
    for period in statement.columns:
        values = reported[period]
        for row in statement.rows:
            if row.kind != "derived":
                continue
            cell = row.cell(period)
            if cell is None or cell.value is None:
                continue
            if row.derivation == "member_agg":
                children = [
                    values[(candidate.concept, candidate.dims)]
                    for candidate in statement.rows_for_concept(row.concept)
                    if candidate.dims and (candidate.concept, candidate.dims) in values
                ]
                if not children:
                    continue
                computed = sum(children, Decimal(0))
                n_children = len(children)
            else:
                terms = [
                    weight * values[(child, ())]
                    for child, weight in statement.calc_children.get(row.concept, [])
                    if (child, ()) in values
                ]
                if not terms:
                    continue
                computed = sum(terms, Decimal(0))
                n_children = len(terms)
            decimals = cell.decimals if cell.decimals is not None else 0
            step = Decimal(10) ** Decimal(-decimals)
            tolerance = HALF * step * (n_children + 1)
            diff = computed - cell.value
            checks.append(
                FootingCheck(
                    statement.statement,
                    row.label,
                    period,
                    computed,
                    cell.value,
                    diff,
                    tolerance,
                    abs(diff) <= tolerance,
                )
            )
    return checks


@dataclass(frozen=True)
class PlausibilityCheck:
    name: str
    detail: str
    passed: bool


def plausibility_battery(period: ProjectedPeriod, base_metrics: dict[str, Decimal]) -> list[PlausibilityCheck]:
    """Accountant-style sanity on one simulated period."""
    checks: list[PlausibilityCheck] = []
    metrics = period.metrics

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append(PlausibilityCheck(name, detail, passed))

    check(
        "identities hold exactly",
        not period.violations,
        "; ".join(period.violations) or "A = L + E and the cash tie hold",
    )
    revenue = metrics.get("revenue", Decimal(0))
    base_revenue = base_metrics.get("revenue", Decimal(0))
    if base_revenue:
        growth = revenue / base_revenue - 1
        check(
            "revenue growth within [-40%, +60%]",
            Decimal("-0.4") <= growth <= Decimal("0.6"),
            f"growth {growth:.1%}",
        )
    margin = metrics.get("gross_margin_bp", Decimal(0))
    base_margin = base_metrics.get("gross_margin_bp", Decimal(0))
    if base_margin:
        check(
            "gross margin within 15pp of base",
            abs(margin - base_margin) <= Decimal(1500),
            f"margin {margin/100:.1f}% vs base {base_margin/100:.1f}%",
        )
    check("cash non-negative", metrics.get("cash", Decimal(0)) >= 0, f"cash {metrics.get('cash', 0):,}")
    check(
        "total assets positive",
        metrics.get("total_assets", Decimal(0)) > 0,
        f"assets {metrics.get('total_assets', 0):,}",
    )
    return checks
