"""Round trip: regenerate the statement rows purely from (z, m) + calc arcs.

Derived values are recomputed bottom-up from the calculation graph; nothing
is read back from the filing. The regenerated rows (label, displayed value,
order) are then diffed against the natively extracted rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from spike.overlay import Overlay


@dataclass(frozen=True)
class RowComparison:
    order: int
    qname: str
    kind: str
    label: str
    native: str
    regenerated: str
    match: bool


@dataclass(frozen=True)
class RoundTripResult:
    comparisons: list[RowComparison]
    total: int
    matched: int
    underivable: list[str]  # derived rows that could not be recomputed

    @property
    def exact(self) -> bool:
        return self.matched == self.total and not self.underivable


def format_displayed(value: Decimal | None, sign: int) -> str:
    if value is None:
        return ""
    shown = value * sign
    if shown == shown.to_integral_value():
        shown = shown.quantize(Decimal(1))
    return f"{shown:,f}"


def recompute_values(overlay: Overlay) -> tuple[dict[str, Decimal], list[str]]:
    """Bottom-up values from z and the calc arcs; reported values not used.

    Children with no resolvable value (for example nil facts) drop out of the
    sum, mirroring the footing check; a derived concept with no resolvable
    children at all stays unresolved.
    """
    values: dict[str, Decimal] = dict(overlay.z)
    underivable: list[str] = []

    def resolve(qname: str, stack: frozenset) -> Decimal | None:
        if qname in values:
            return values[qname]
        kids = overlay.calc_children.get(qname)
        if not kids or qname in stack:
            return None
        total = Decimal(0)
        resolved_any = False
        for child, weight in kids:
            child_value = resolve(child, stack | {qname})
            if child_value is not None:
                total += weight * child_value
                resolved_any = True
        if not resolved_any:
            return None
        values[qname] = total
        return total

    for row in overlay.rows:
        if row.kind == "derived" and resolve(row.qname, frozenset()) is None:
            if row.qname not in underivable:
                underivable.append(row.qname)
    return values, underivable


def run(overlay: Overlay) -> RoundTripResult:
    regenerated_values, underivable = recompute_values(overlay)
    comparisons: list[RowComparison] = []
    matched = 0
    for row in overlay.rows:
        native = format_displayed(row.value, row.displayed_sign)
        if row.kind == "abstract":
            regenerated = ""
        else:
            regenerated = format_displayed(regenerated_values.get(row.qname), row.displayed_sign)
        match = native == regenerated
        if match:
            matched += 1
        comparisons.append(
            RowComparison(
                order=row.order,
                qname=row.qname,
                kind=row.kind,
                label=row.label,
                native=native,
                regenerated=regenerated,
                match=match,
            )
        )
    return RoundTripResult(
        comparisons=comparisons,
        total=len(comparisons),
        matched=matched,
        underivable=underivable,
    )
