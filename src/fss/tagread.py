"""Tag-path extractor: structured statements from a filing's inline XBRL.

Reads the filer's own tagged facts through the presentation network of each
core statement role, reproducing the displayed rows: abstract headers,
dimensioned member rows (in axis order, with the member's label), their
undimensioned aggregate, preferred-label sign flips, and one cell per
reported column. Values are the facts' exact Decimals; nothing is inferred.

Debug entry point: python -m fss.tagread [company ...]
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from timeit import default_timer
from typing import Any

from arelle import XbrlConst
from arelle.ModelXbrl import ModelXbrl

from fss import kg
from fss.statements import Cell, StatementRow, StructuredStatement

MAX_COLUMNS = {"balance_sheet": 2, "income_statement": 3, "cash_flow": 3}
COLUMN_COVERAGE = 0.5  # a column must carry at least this share of the max column's facts
TOTAL_LABEL_ROLE = "http://www.xbrl.org/2003/role/totalLabel"

DimsSig = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class _PresEntry:
    concept: Any
    preferred: str | None
    depth: int
    section: tuple[str, ...]


@dataclass(frozen=True)
class _Column:
    key: str
    start: datetime | None  # None for instant columns
    end: datetime


def _iso(moment: datetime) -> str:
    """XBRL end-of-day datetimes name the day they close."""
    from datetime import timedelta

    return (moment - timedelta(days=1)).date().isoformat()


def _column_for_instant(when: datetime) -> _Column:
    return _Column(key=f"I{_iso(when)}", start=None, end=when)


def _column_for_duration(start: datetime, end: datetime) -> _Column:
    return _Column(key=f"D{start.date().isoformat()}:{_iso(end)}", start=start, end=end)


def _walk_presentation(
    model: ModelXbrl, linkrole: str
) -> tuple[list[_PresEntry], dict[str, list[tuple[str, str | None]]]]:
    """Displayed entries plus per-axis member order.

    Structural nodes (Table/Axis/Domain/Member/LineItems) are not display
    rows; concepts under an Axis register as its ordered members.
    """
    pres = model.relationshipSet(XbrlConst.parentChild, linkrole)
    entries: list[_PresEntry] = []
    members: dict[str, list[tuple[str, str | None]]] = {}

    def visit(
        concept: Any,
        preferred: str | None,
        display_depth: int,
        section: tuple[str, ...],
        axis: str | None,
        ancestors: frozenset,
    ) -> None:
        child_axis = axis
        child_depth = display_depth
        child_section = section
        if axis is not None:
            local = concept.qname.localName
            if not local.endswith("Domain"):
                members.setdefault(axis, []).append((str(concept.qname), preferred))
        elif getattr(concept, "isDimensionItem", False):
            child_axis = str(concept.qname)
            members.setdefault(child_axis, [])
        elif kg.is_structural(concept):
            pass  # Table / LineItems: recurse without emitting or deepening
        else:
            entries.append(_PresEntry(concept, preferred, display_depth, section))
            child_depth = display_depth + 1
            if concept.isAbstract:
                label = concept.label(preferredLabel=preferred, lang="en-US", fallbackToQname=True)
                child_section = section + (label,)
        for rel in sorted(
            pres.fromModelObject(concept), key=lambda r: r.orderDecimal or Decimal(0)
        ):
            child = rel.toModelObject
            if child is None or child in ancestors:
                continue
            visit(
                child,
                rel.preferredLabel,
                child_depth,
                child_section,
                child_axis,
                ancestors | {concept},
            )

    for root in sorted(pres.rootConcepts, key=lambda c: str(c.qname)):
        visit(root, None, 0, (), None, frozenset())
    return entries, members


def _fact_value(fact: Any) -> Decimal:
    value = getattr(fact, "xValue", None)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Decimal(str(value))
    return Decimal(fact.value)


def _fact_decimals(fact: Any) -> int | None:
    raw = (fact.decimals or "").strip()
    if not raw or raw.upper() == "INF":
        return None
    return int(raw)


def _fact_unit(fact: Any) -> str | None:
    unit = fact.unit
    if unit is None:
        return None
    numerators, denominators = unit.measures
    top = "*".join(sorted(measure.localName for measure in numerators))
    if denominators:
        bottom = "*".join(sorted(measure.localName for measure in denominators))
        return f"{top}/{bottom}"
    return top


def _dims_signature(context: Any, allowed_members: dict[str, set[str]]) -> DimsSig | None:
    """Sorted (axis, member) pairs; None when the context uses an axis or a
    member that this statement's presentation tree does not declare (those
    facts belong to notes, not the face)."""
    pairs: list[tuple[str, str]] = []
    for axis_qname, dim_value in context.qnameDims.items():
        axis = str(axis_qname)
        if axis not in allowed_members:
            return None
        if dim_value.isTyped:
            return None
        member = str(dim_value.memberQname)
        if member not in allowed_members[axis]:
            return None
        pairs.append((axis, member))
    return tuple(sorted(pairs))


@dataclass
class _FactIndex:
    by_row: dict[tuple[str, DimsSig], dict[tuple[datetime | None, datetime], Any]]
    duplicate_conflicts: list[str]
    unparseable: list[str]


def _collect_facts(
    model: ModelXbrl, concepts: set[str], allowed_members: dict[str, set[str]]
) -> _FactIndex:
    by_row: dict[tuple[str, DimsSig], dict[tuple[datetime | None, datetime], Any]] = {}
    conflicts: list[str] = []
    unparseable: list[str] = []
    for fact in sorted(model.factsInInstance, key=lambda f: f.objectIndex):
        if fact.concept is None:
            continue
        qname = str(fact.qname)
        if qname not in concepts:
            continue
        context = fact.context
        if context is None:
            continue
        if context.instantDatetime is not None:
            period = (None, context.instantDatetime)
        elif context.startDatetime is not None and context.endDatetime is not None:
            period = (context.startDatetime, context.endDatetime)
        else:
            continue
        sig = _dims_signature(context, allowed_members)
        if sig is None:
            continue
        if fact.isNil:
            continue
        try:
            _fact_value(fact)
        except Exception:
            if qname not in unparseable:
                unparseable.append(qname)
            continue
        slot = by_row.setdefault((qname, sig), {})
        if period in slot:
            if _fact_value(slot[period]) != _fact_value(fact):
                conflicts.append(qname)
            continue
        slot[period] = fact
    return _FactIndex(by_row, conflicts, unparseable)


def _select_columns(index: _FactIndex, statement: str) -> list[_Column]:
    counts: dict[tuple[datetime | None, datetime], int] = {}
    for periods in index.by_row.values():
        for period in periods:
            counts[period] = counts.get(period, 0) + 1
    wanted_instant = statement == "balance_sheet"
    filtered = {
        period: n
        for period, n in counts.items()
        if (period[0] is None) == wanted_instant
    }
    if not filtered:
        raise RuntimeError(f"no facts found to define columns for {statement}")
    top = max(filtered.values())
    kept = [period for period, n in filtered.items() if n >= COLUMN_COVERAGE * top]
    kept.sort(key=lambda period: period[1], reverse=True)
    kept = kept[: MAX_COLUMNS[statement]]
    return [
        _column_for_instant(end) if start is None else _column_for_duration(start, end)
        for start, end in kept
    ]


def _member_label(model: ModelXbrl, member_qname: str, preferred: str | None) -> str:
    concept = model.qnameConcepts.get(_to_qname(model, member_qname))
    if concept is None:
        return member_qname
    return concept.label(preferredLabel=preferred, lang="en-US", fallbackToQname=True)


def _to_qname(model: ModelXbrl, qname_str: str) -> Any:
    prefix, _, local = qname_str.partition(":")
    for qname in model.qnameConcepts:
        if qname.localName == local and str(qname) == qname_str:
            return qname
    return None


def _calc_children(model: ModelXbrl, linkrole: str, concepts: set[str]) -> dict[str, list[tuple[str, Decimal]]]:
    collected: dict[str, dict[str, Decimal]] = {}
    for arcrole in XbrlConst.summationItems:
        for rel in model.relationshipSet(arcrole, linkrole).modelRelationships:
            parent, child = rel.fromModelObject, rel.toModelObject
            if parent is None or child is None:
                continue
            parent_q, child_q = str(parent.qname), str(child.qname)
            if parent_q not in concepts or child_q not in concepts:
                continue
            weight = rel.weightDecimal if rel.weightDecimal is not None else Decimal(str(rel.weight))
            collected.setdefault(parent_q, {})[child_q] = weight
    return {parent: sorted(kids.items()) for parent, kids in collected.items()}


def _match_period(
    row_period_type: str,
    preferred: str | None,
    column: _Column,
    periods: dict[tuple[datetime | None, datetime], Any],
) -> Any | None:
    if column.start is None:  # instant column (balance sheet)
        return periods.get((None, column.end))
    if row_period_type == "instant":
        wants_start = bool(preferred) and "periodstart" in preferred.lower()
        moment = column.start if wants_start else column.end
        return periods.get((None, moment))
    return periods.get((column.start, column.end))


def _dominant_currency(rows: list[StatementRow]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        for cell in row.cells:
            if cell.unit and "/" not in cell.unit and cell.unit not in ("shares",):
                counts[cell.unit] = counts.get(cell.unit, 0) + 1
    return max(counts, key=lambda unit: counts[unit]) if counts else ""


def extract_statement(
    model: ModelXbrl,
    company_key: str,
    standard: str,
    statement: str,
    linkrole: str,
    role_definition: str,
) -> StructuredStatement:
    entries, member_orders = _walk_presentation(model, linkrole)
    concepts = {str(entry.concept.qname) for entry in entries}
    allowed_members = {
        axis: {member for member, _ in axis_members}
        for axis, axis_members in member_orders.items()
    }
    member_rank: dict[str, int] = {}
    member_preferred: dict[str, str | None] = {}
    rank = 0
    for axis, axis_members in member_orders.items():
        for member_qname, preferred in axis_members:
            if member_qname not in member_rank:
                member_rank[member_qname] = rank
                member_preferred[member_qname] = preferred
                rank += 1

    index = _collect_facts(model, concepts, allowed_members)
    columns = _select_columns(index, statement)
    calc = _calc_children(model, linkrole, concepts)
    anchors = {child: parent for parent, kids in calc.items() for child, _ in kids}

    rows: list[StatementRow] = []
    notes: list[str] = []

    def emit(
        entry: _PresEntry,
        dims: DimsSig,
        label: str,
        kind: str,
        derivation: str,
        periods: dict[tuple[datetime | None, datetime], Any] | None,
    ) -> None:
        concept = entry.concept
        preferred = entry.preferred
        negated = bool(preferred and "negated" in preferred.lower())
        cells = []
        for column in columns:
            fact = None
            if periods is not None:
                fact = _match_period(concept.periodType or "", preferred, column, periods)
            cells.append(
                Cell(
                    period=column.key,
                    value=_fact_value(fact) if fact is not None else None,
                    decimals=_fact_decimals(fact) if fact is not None else None,
                    unit=_fact_unit(fact) if fact is not None else None,
                )
            )
        is_ext = kg.is_extension_concept(concept)
        rows.append(
            StatementRow(
                order=len(rows),
                concept=str(concept.qname),
                dims=dims,
                label=label,
                depth=entry.depth,
                kind=kind,
                derivation=derivation,
                preferred_label=preferred,
                negated=negated,
                displayed_sign=-1 if negated else 1,
                period_type=concept.periodType or "",
                balance=concept.balance or "",
                is_monetary=bool(concept.isMonetary),
                is_extension=is_ext,
                anchor=anchors.get(str(concept.qname)) if is_ext else None,
                section=entry.section,
                cells=tuple(cells),
            )
        )

    for entry in entries:
        concept = entry.concept
        qname = str(concept.qname)
        label = concept.label(preferredLabel=entry.preferred, lang="en-US", fallbackToQname=True)
        if concept.isAbstract:
            emit(entry, (), label, "abstract", "", None)
            continue
        dimensioned = {
            sig: periods
            for (row_q, sig), periods in index.by_row.items()
            if row_q == qname and sig
        }
        undimensioned = index.by_row.get((qname, ()), {})
        if dimensioned:
            ordered = sorted(
                dimensioned.items(),
                key=lambda item: tuple(member_rank.get(member, 10_000) for _, member in item[0]),
            )
            for sig, periods in ordered:
                member_names = [
                    _member_label(model, member, member_preferred.get(member))
                    for _, member in sig
                ]
                emit(entry, sig, " / ".join(member_names), "leaf", "", periods)
            if undimensioned:
                # The renderer titles the member aggregate with the concept's
                # total label when one exists ("Total net sales").
                total_label = concept.label(
                    preferredLabel=TOTAL_LABEL_ROLE, fallbackToQname=False, lang="en-US"
                )
                emit(
                    entry,
                    (),
                    total_label or label,
                    "derived",
                    "member_agg",
                    undimensioned,
                )
            continue
        if undimensioned or not dimensioned:
            derived_by_calc = qname in calc
            emit(
                entry,
                (),
                label,
                "derived" if derived_by_calc else "leaf",
                "calc" if derived_by_calc else "",
                undimensioned or None,
            )

    if index.duplicate_conflicts:
        notes.append(
            "duplicate facts with conflicting values: "
            + ", ".join(sorted(set(index.duplicate_conflicts)))
        )
    if index.unparseable:
        notes.append("unparseable facts treated as missing: " + ", ".join(index.unparseable))

    result = StructuredStatement(
        company=company_key,
        standard=standard,
        statement=statement,
        linkrole=linkrole,
        role_definition=role_definition,
        currency="",
        columns=tuple(column.key for column in columns),
        rows=rows,
        calc_children=calc,
        notes=notes,
    )
    result.currency = _dominant_currency(rows)
    return result


def extract_all(model: ModelXbrl, company_key: str, standard: str) -> dict[str, StructuredStatement]:
    roles = kg.find_statement_roles(model)
    out: dict[str, StructuredStatement] = {}
    for statement, (linkrole, definition) in roles.items():
        started = default_timer()
        out[statement] = extract_statement(
            model, company_key, standard, statement, linkrole, definition
        )
        elapsed = default_timer() - started
        print(
            f"{company_key}: {statement} <- {definition!r} "
            f"({len(out[statement].rows)} rows, {len(out[statement].columns)} columns, "
            f"{elapsed:.1f}s)"
        )
    return out


def main() -> None:
    import sys

    from fss import edgar
    from fss.paths import DATA_DIR
    from fss.xbrl import load_model

    keys = sys.argv[1:] or list(edgar.COMPANIES)
    for key in keys:
        company = edgar.COMPANIES[key]
        filing = edgar.latest_annual(company)
        model = load_model(filing.primary_path)
        statements = extract_all(model, key, company.standard)
        for statement in statements.values():
            target = DATA_DIR / "extracted" / f"{key}_{statement.statement}.json"
            statement.save(target)
            print(f"{key}: wrote {target}")
        model.close()


if __name__ == "__main__":
    main()
