"""Arithmetic and coverage checks over the balance-sheet overlay."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from spike.overlay import Overlay

ASSETS_QNAME = "us-gaap:Assets"
LIABILITIES_QNAMES = ("us-gaap:Liabilities",)
EQUITY_QNAMES = (
    "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "us-gaap:StockholdersEquity",
)
TOTAL_LIAB_EQUITY_QNAME = "us-gaap:LiabilitiesAndStockholdersEquity"
COVERAGE_TARGET = Decimal("0.95")


@dataclass(frozen=True)
class FootingCheck:
    parent: str
    label: str
    children_used: int
    children_skipped: list[str]  # calc children on the statement with no value
    computed: Decimal
    reported: Decimal
    diff: Decimal
    tolerance: Decimal
    passed: bool


@dataclass(frozen=True)
class IdentityCheck:
    assets_concept: str | None
    liabilities_concept: str | None
    equity_concept: str | None
    assets: Decimal | None
    liabilities: Decimal | None
    equity: Decimal | None
    diff: Decimal | None
    tolerance: Decimal | None
    passed: bool
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CoverageCheck:
    face_lines: int
    resolved: int
    fraction: Decimal
    passed: bool
    unresolved: list[str]  # face qnames missing periodType or balance
    non_instant: list[str]  # face qnames whose periodType is not "instant"


def _rounding_step(decimals: int | None) -> Decimal:
    """decimals=-6 means rounded to the nearest 10^6; None means exact."""
    if decimals is None:
        return Decimal(0)
    return Decimal(10) ** Decimal(-decimals)


def _tolerance(overlay: Overlay, qnames: list[str], n_addends: int) -> Decimal:
    step = max(
        (_rounding_step(overlay.decimals_by_qname.get(q)) for q in qnames),
        default=Decimal(0),
    )
    return Decimal("0.5") * step * (n_addends + 1)


def footing_checks(overlay: Overlay) -> list[FootingCheck]:
    """Every derived concept must equal the weighted sum of its calc children."""
    values = {**overlay.z, **overlay.derived}
    labels = {row.qname: row.label for row in overlay.rows}
    seen: set[str] = set()
    results: list[FootingCheck] = []
    for row in overlay.rows:
        if row.kind != "derived" or row.qname in seen:
            continue
        seen.add(row.qname)
        kids = overlay.calc_children[row.qname]
        used = [(child, weight) for child, weight in kids if child in values]
        skipped = [child for child, _ in kids if child not in values]
        computed = sum((weight * values[child] for child, weight in used), Decimal(0))
        reported = values.get(row.qname)
        if reported is None:
            # No reported value to check against; surfaced via missing_value_rows.
            continue
        involved = [row.qname] + [child for child, _ in used]
        tolerance = _tolerance(overlay, involved, len(used))
        diff = computed - reported
        results.append(
            FootingCheck(
                parent=row.qname,
                label=labels.get(row.qname, row.qname),
                children_used=len(used),
                children_skipped=skipped,
                computed=computed,
                reported=reported,
                diff=diff,
                tolerance=tolerance,
                passed=abs(diff) <= tolerance,
            )
        )
    return results


def _first_present(candidates: tuple[str, ...], values: dict[str, Decimal]) -> str | None:
    for qname in candidates:
        if qname in values:
            return qname
    return None


def identity_check(overlay: Overlay) -> IdentityCheck:
    """Assets = Liabilities + Equity, using the reported totals."""
    values = {**overlay.z, **overlay.derived}
    assets_q = ASSETS_QNAME if ASSETS_QNAME in values else None
    liabilities_q = _first_present(LIABILITIES_QNAMES, values)
    equity_q = _first_present(EQUITY_QNAMES, values)
    notes: list[str] = []
    if not (assets_q and liabilities_q and equity_q):
        missing = [
            name
            for name, q in (
                ("assets", assets_q),
                ("liabilities", liabilities_q),
                ("equity", equity_q),
            )
            if q is None
        ]
        notes.append("could not match concepts for: " + ", ".join(missing))
        return IdentityCheck(
            assets_q, liabilities_q, equity_q, None, None, None, None, None, False, notes
        )
    assets = values[assets_q]
    liabilities = values[liabilities_q]
    equity = values[equity_q]
    diff = assets - (liabilities + equity)
    tolerance = _tolerance(overlay, [assets_q, liabilities_q, equity_q], 2)
    if TOTAL_LIAB_EQUITY_QNAME in values:
        cross = values[TOTAL_LIAB_EQUITY_QNAME] - assets
        notes.append(
            f"cross-check: reported {TOTAL_LIAB_EQUITY_QNAME} minus Assets = {cross:,f}"
        )
    return IdentityCheck(
        assets_concept=assets_q,
        liabilities_concept=liabilities_q,
        equity_concept=equity_q,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        diff=diff,
        tolerance=tolerance,
        passed=abs(diff) <= tolerance,
        notes=notes,
    )


def coverage_check(overlay: Overlay) -> CoverageCheck:
    """Face lines resolving to concepts with periodType and balance populated."""
    face = overlay.face_rows
    unresolved: list[str] = []
    non_instant: list[str] = []
    for row in face:
        if not (row.period_type and row.balance):
            if row.qname not in unresolved:
                unresolved.append(row.qname)
        if row.period_type != "instant" and row.qname not in non_instant:
            non_instant.append(row.qname)
    resolved = sum(1 for row in face if row.period_type and row.balance)
    fraction = Decimal(resolved) / Decimal(len(face)) if face else Decimal(0)
    return CoverageCheck(
        face_lines=len(face),
        resolved=resolved,
        fraction=fraction,
        passed=fraction >= COVERAGE_TARGET,
        unresolved=unresolved,
        non_instant=non_instant,
    )
