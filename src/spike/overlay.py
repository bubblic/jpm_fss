"""Overlay the filing's consolidated balance sheet onto the taxonomy graph.

Produces z (leaf concept -> reported value at the latest balance-sheet date),
the derived set (calc parents on the statement, excluded from z), and m (the
ordered presentation rows with native labels, preferredLabel sign handling,
and leaf/derived/abstract kinds).

Debug entry point: python -m spike.overlay
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from arelle import XbrlConst
from arelle.ModelXbrl import ModelXbrl

BALANCE_SHEET_HINTS = ("balance sheet", "statement of financial position")
STANDARD_NAMESPACE_MARKERS = ("fasb.org", "xbrl.sec.gov", "xbrl.org")
DEI_NAMESPACE_MARKER = "xbrl.sec.gov/dei"


@dataclass(frozen=True)
class Row:
    order: int
    qname: str
    label: str
    kind: str  # "abstract" | "leaf" | "derived"
    depth: int
    preferred_label: str | None
    negated: bool
    displayed_sign: int  # -1 when a negated preferred label flips the shown sign
    period_type: str
    balance: str
    is_monetary: bool
    is_extension: bool
    anchor: str | None  # calc parent on this statement, recorded for extensions
    value: Decimal | None  # reported value at the statement date, fact sign
    decimals: int | None  # None means decimals="INF" or no fact


@dataclass
class Overlay:
    entity: str
    linkrole: str
    role_definition: str
    candidate_roles: list[tuple[str, str]]
    filing_defined_roles: list[tuple[str, str]]
    instant: date  # the balance-sheet date of the chosen column
    rows: list[Row]
    z: dict[str, Decimal]
    derived: dict[str, Decimal]
    calc_children: dict[str, list[tuple[str, Decimal]]]
    calc_arcroles_used: dict[str, int]
    calc_weight_conflicts: list[str]
    decimals_by_qname: dict[str, int | None]
    dimensioned_skipped_at_date: int
    dimensioned_skipped_total: int
    duplicate_fact_conflicts: list[str]
    unparseable_facts: list[str]
    ixt_unrecognized_total: int  # filing-wide facts with an unregistered transform
    missing_value_rows: list[str]
    extension_qnames: list[str]

    @property
    def face_rows(self) -> list[Row]:
        return [row for row in self.rows if row.kind != "abstract"]


def _is_filing_defined(role_type: Any) -> bool:
    """True when the role is declared by the filing's own schema, not a
    template role that ships inside the standard taxonomies."""
    uri = getattr(role_type.modelDocument, "uri", "") or ""
    return not any(marker in uri for marker in STANDARD_NAMESPACE_MARKERS)


def pick_balance_sheet_role(
    model: ModelXbrl,
) -> tuple[str, str, list[tuple[str, str]], list[tuple[str, str]]]:
    """Choose the consolidated balance sheet linkrole.

    Text heuristics match template roles baked into the us-gaap taxonomy as
    well, so filing-defined roles are preferred. Returns the chosen (uri,
    definition) plus all matches and the filing-defined subset, for the
    report's ambiguity finding.
    """
    matches: list[tuple[str, str]] = []
    filing_defined: list[tuple[str, str]] = []
    for uri, role_types in sorted(model.roleTypes.items()):
        for role_type in role_types:
            definition = role_type.definition or ""
            lowered = definition.lower()
            if "statement" not in lowered or "parenthetical" in lowered:
                continue
            if any(hint in lowered for hint in BALANCE_SHEET_HINTS):
                matches.append((uri, definition))
                if _is_filing_defined(role_type):
                    filing_defined.append((uri, definition))
                break
    if not matches:
        raise RuntimeError(
            "no linkrole definition looks like the consolidated balance sheet"
        )

    def presentation_size(uri: str) -> int:
        return len(model.relationshipSet(XbrlConst.parentChild, uri).modelRelationships)

    pool = filing_defined or matches
    uri, definition = max(pool, key=lambda cand: presentation_size(cand[0]))
    return uri, definition, matches, filing_defined


def presentation_rows(model: ModelXbrl, linkrole: str) -> list[tuple[Any, str | None, int]]:
    """Walk parentChild depth-first; children ordered by rel.order.

    Returns (concept, preferredLabel of the arriving arc, depth) per row.
    """
    pres = model.relationshipSet(XbrlConst.parentChild, linkrole)
    entries: list[tuple[Any, str | None, int]] = []

    def visit(concept: Any, preferred: str | None, depth: int, ancestors: frozenset) -> None:
        entries.append((concept, preferred, depth))
        rels = sorted(pres.fromModelObject(concept), key=lambda rel: rel.orderDecimal or Decimal(0))
        for rel in rels:
            child = rel.toModelObject
            if child is None or child in ancestors:
                continue
            visit(child, rel.preferredLabel, depth + 1, ancestors | {concept})

    for root in sorted(pres.rootConcepts, key=lambda c: str(c.qname)):
        visit(root, None, 0, frozenset())
    return entries


def _calc_children(
    model: ModelXbrl, linkrole: str, on_statement: set[str]
) -> tuple[dict[str, list[tuple[str, Decimal]]], dict[str, int], list[str]]:
    """Calc arcs of this statement restricted to on-statement concepts.

    Merges calc 1.0 and calc 1.1, dedupes (parent, child) pairs, and records
    conflicting weights should the two arc sets ever disagree.
    """
    collected: dict[str, dict[str, Decimal]] = {}
    arcroles_used: dict[str, int] = {}
    conflicts: list[str] = []
    for arcrole in XbrlConst.summationItems:
        rels = model.relationshipSet(arcrole, linkrole).modelRelationships
        if rels:
            arcroles_used[arcrole] = len(rels)
        for rel in rels:
            parent, child = rel.fromModelObject, rel.toModelObject
            if parent is None or child is None:
                continue
            parent_q, child_q = str(parent.qname), str(child.qname)
            if parent_q not in on_statement or child_q not in on_statement:
                continue
            weight = rel.weightDecimal if rel.weightDecimal is not None else Decimal(str(rel.weight))
            existing = collected.setdefault(parent_q, {})
            if child_q in existing and existing[child_q] != weight:
                conflicts.append(f"{parent_q} -> {child_q}")
            existing[child_q] = weight
    children = {parent: sorted(kids.items()) for parent, kids in collected.items()}
    return children, arcroles_used, conflicts


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


def _collect_facts(
    model: ModelXbrl, on_statement: set[str]
) -> tuple[dict[tuple[str, datetime], Any], dict[datetime, int], list[str], list[str]]:
    """Undimensioned instant facts for statement concepts, keyed (qname, instant).

    Also counts dimensioned instant facts per date (these are skipped), notes
    duplicate facts whose values disagree, and notes facts whose inline
    transformation cannot be evaluated (they are treated as missing).
    """
    facts: dict[tuple[str, datetime], Any] = {}
    dimensioned: dict[datetime, int] = {}
    conflicts: list[str] = []
    unparseable: list[str] = []
    for fact in sorted(model.factsInInstance, key=lambda f: f.objectIndex):
        if fact.concept is None or str(fact.qname) not in on_statement:
            continue
        context = fact.context
        if context is None or context.instantDatetime is None:
            continue
        when = context.instantDatetime
        if context.qnameDims:
            dimensioned[when] = dimensioned.get(when, 0) + 1
            continue
        if fact.isNil:
            continue
        key = (str(fact.qname), when)
        try:
            value = _fact_value(fact)
        except Exception:
            if key[0] not in unparseable:
                unparseable.append(key[0])
            continue
        if key in facts:
            if _fact_value(facts[key]) != value:
                conflicts.append(key[0])
            continue
        facts[key] = fact
    return facts, dimensioned, conflicts, unparseable


def _choose_instant(facts: dict[tuple[str, datetime], Any], face_count: int) -> datetime:
    """The latest balance-sheet date: newest instant covering most face lines."""
    counts: dict[datetime, int] = {}
    for _, when in facts:
        counts[when] = counts.get(when, 0) + 1
    if not counts:
        raise RuntimeError("no undimensioned instant facts found for statement concepts")
    threshold = max(1, face_count // 2)
    rich = [when for when, n in counts.items() if n >= threshold]
    if rich:
        return max(rich)
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def _count_unrecognized_transforms(model: ModelXbrl) -> int:
    """Filing-wide count of inline facts whose ixt registry Arelle lacks."""
    from arelle import FunctionIxt

    count = 0
    for fact in model.factsInInstance:
        fmt = getattr(fact, "format", None)
        if fmt is not None and fmt.namespaceURI not in FunctionIxt.ixtNamespaceFunctions:
            count += 1
    return count


def _is_extension(concept: Any) -> bool:
    namespace = concept.qname.namespaceURI or ""
    return not any(marker in namespace for marker in STANDARD_NAMESPACE_MARKERS)


def _label(concept: Any, preferred: str | None) -> str:
    label = concept.label(preferredLabel=preferred, lang="en-US", fallbackToQname=True)
    return label if label is not None else str(concept.qname)


def _entity_name(model: ModelXbrl) -> str:
    for fact in sorted(model.factsInInstance, key=lambda f: f.objectIndex):
        qname = fact.qname
        if qname.localName == "EntityRegistrantName" and DEI_NAMESPACE_MARKER in (qname.namespaceURI or ""):
            value = (fact.value or "").strip()
            if value:
                return value
    return "registrant name not tagged"


def build_overlay(model: ModelXbrl) -> Overlay:
    linkrole, definition, candidates, filing_defined = pick_balance_sheet_role(model)
    entries = presentation_rows(model, linkrole)
    on_statement = {str(concept.qname) for concept, _, _ in entries}
    calc_children, arcroles_used, weight_conflicts = _calc_children(model, linkrole, on_statement)
    anchors = {child: parent for parent, kids in calc_children.items() for child, _ in kids}
    facts, dimensioned_by_instant, duplicate_conflicts, unparseable = _collect_facts(model, on_statement)
    face_count = sum(1 for concept, _, _ in entries if not concept.isAbstract)
    instant = _choose_instant(facts, face_count)
    at_date = {qname: fact for (qname, when), fact in facts.items() if when == instant}

    rows: list[Row] = []
    z: dict[str, Decimal] = {}
    derived_values: dict[str, Decimal] = {}
    decimals_by_qname: dict[str, int | None] = {}
    missing: list[str] = []
    extensions: list[str] = []
    for position, (concept, preferred, depth) in enumerate(entries):
        qname = str(concept.qname)
        negated = bool(preferred and "negated" in preferred.lower())
        kind = "abstract" if concept.isAbstract else ("derived" if qname in calc_children else "leaf")
        fact = at_date.get(qname) if kind != "abstract" else None
        value = _fact_value(fact) if fact is not None else None
        decimals = _fact_decimals(fact) if fact is not None else None
        is_extension = _is_extension(concept)
        if is_extension and qname not in extensions:
            extensions.append(qname)
        if kind != "abstract":
            decimals_by_qname[qname] = decimals
            if value is None:
                if qname not in missing:
                    missing.append(qname)
            elif kind == "leaf":
                z[qname] = value
            else:
                derived_values[qname] = value
        rows.append(
            Row(
                order=position,
                qname=qname,
                label=_label(concept, preferred),
                kind=kind,
                depth=depth,
                preferred_label=preferred,
                negated=negated,
                displayed_sign=-1 if negated else 1,
                period_type=concept.periodType or "",
                balance=concept.balance or "",
                is_monetary=bool(concept.isMonetary),
                is_extension=is_extension,
                anchor=anchors.get(qname) if is_extension else None,
                value=value,
                decimals=decimals,
            )
        )

    return Overlay(
        entity=_entity_name(model),
        linkrole=linkrole,
        role_definition=definition,
        candidate_roles=candidates,
        filing_defined_roles=filing_defined,
        instant=(instant - timedelta(days=1)).date(),
        rows=rows,
        z=z,
        derived=derived_values,
        calc_children=calc_children,
        calc_arcroles_used=arcroles_used,
        calc_weight_conflicts=weight_conflicts,
        decimals_by_qname=decimals_by_qname,
        dimensioned_skipped_at_date=dimensioned_by_instant.get(instant, 0),
        dimensioned_skipped_total=sum(dimensioned_by_instant.values()),
        duplicate_fact_conflicts=duplicate_conflicts,
        unparseable_facts=unparseable,
        ixt_unrecognized_total=_count_unrecognized_transforms(model),
        missing_value_rows=missing,
        extension_qnames=extensions,
    )


def main() -> None:
    from spike import fetch, graph

    filing = fetch.main()
    model = graph.load_model(filing.primary_path)
    overlay = build_overlay(model)
    print(f"entity: {overlay.entity}")
    print(f"role: {overlay.role_definition} ({overlay.linkrole})")
    print(f"balance-sheet date: {overlay.instant.isoformat()}")
    print(
        f"rows: {len(overlay.rows)} total, {len(overlay.face_rows)} face lines, "
        f"{len(overlay.z)} leaves, {len(overlay.derived)} derived"
    )
    for row in overlay.rows:
        shown = "" if row.value is None else f"{row.value * row.displayed_sign:,f}"
        print(f"  {'  ' * row.depth}[{row.kind:8}] {row.label} = {shown}")


if __name__ == "__main__":
    main()
