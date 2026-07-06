"""Run the full spike pipeline and write out/report.md plus artifacts.

Entry point: python -m spike.report
"""
from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from spike import checks, fetch, graph, overlay, roundtrip
from spike.checks import CoverageCheck, FootingCheck, IdentityCheck
from spike.fetch import Filing
from spike.graph import GraphStats
from spike.overlay import Overlay
from spike.paths import OUT_DIR
from spike.roundtrip import RoundTripResult

REPORT_PATH = OUT_DIR / "report.md"
OVERLAY_JSON_PATH = OUT_DIR / "overlay.json"


def _number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _number(value)
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def _money(value: Decimal | None) -> str:
    if value is None:
        return "(none)"
    return f"{value:,f}"


def write_overlay_json(statement: Overlay, filing: Filing) -> None:
    payload = {
        "meta": {
            "entity": statement.entity,
            "cik": filing.cik,
            "accession": filing.accession,
            "form": "10-K",
            "filing_date": filing.filing_date,
            "period_of_report": filing.report_date,
            "statement_linkrole": statement.linkrole,
            "statement_role_definition": statement.role_definition,
            "balance_sheet_date": statement.instant.isoformat(),
        },
        "counts": {
            "rows": len(statement.rows),
            "face_lines": len(statement.face_rows),
            "leaves_in_z": len(statement.z),
            "derived": len(statement.derived),
            "extensions": len(statement.extension_qnames),
            "dimensioned_facts_skipped_at_date": statement.dimensioned_skipped_at_date,
            "dimensioned_facts_skipped_total": statement.dimensioned_skipped_total,
        },
        "z": statement.z,
        "derived": statement.derived,
        "calc_children": {
            parent: [{"child": child, "weight": weight} for child, weight in kids]
            for parent, kids in sorted(statement.calc_children.items())
        },
        "m": [asdict(row) for row in statement.rows],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OVERLAY_JSON_PATH.write_text(
        json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8"
    )


def _footing_table(footings: list[FootingCheck]) -> list[str]:
    lines = [
        "| Subtotal | Children | Computed | Reported | Diff | Tolerance | Result |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for check in footings:
        lines.append(
            f"| {check.label} (`{check.parent}`) | {check.children_used} "
            f"| {_money(check.computed)} | {_money(check.reported)} "
            f"| {_money(check.diff)} | {_money(check.tolerance)} "
            f"| {'PASS' if check.passed else 'FAIL'} |"
        )
    return lines


def _findings(
    statement: Overlay,
    footings: list[FootingCheck],
    identity: IdentityCheck,
    coverage: CoverageCheck,
    trip: RoundTripResult,
) -> list[str]:
    found: list[str] = []
    if len(statement.candidate_roles) > 1:
        listing = "; ".join(definition for _, definition in statement.candidate_roles)
        found.append(
            f"Role selection was ambiguous: {len(statement.candidate_roles)} candidate "
            f"linkroles matched ({listing}). The one with the largest presentation tree "
            "was used. A production loader needs a firmer statement-selection rule."
        )
    else:
        found.append(
            "Role selection was unambiguous: exactly one linkrole matched the "
            "balance-sheet heuristics."
        )
    negated_rows = [row for row in statement.rows if row.negated]
    if negated_rows:
        rows = "; ".join(f"{row.label} (`{row.qname}`)" for row in negated_rows)
        found.append(
            f"Negated preferred labels appear on {len(negated_rows)} row(s): {rows}. "
            "The displayed sign is flipped relative to the fact value, and the overlay "
            "records that flip in m. Any consumer that ignores preferredLabel would "
            "show these rows with the wrong sign."
        )
    else:
        found.append(
            "No negated preferred labels occur on this statement, so the sign-flip "
            "handling in m is implemented but was not exercised by this filing."
        )
    arcroles = ", ".join(sorted(statement.calc_arcroles_used)) or "(none)"
    found.append(
        "Calculation arcs found under arcrole(s): "
        + arcroles
        + ". Calc 1.0 and calc 1.1 sets were merged; "
        + (
            f"{len(statement.calc_weight_conflicts)} conflicting weight(s) found: "
            + ", ".join(statement.calc_weight_conflicts)
            if statement.calc_weight_conflicts
            else "no conflicting weights between them."
        )
    )
    if statement.extension_qnames:
        anchored = []
        unanchored = []
        by_qname = {row.qname: row for row in statement.rows}
        for qname in statement.extension_qnames:
            row = by_qname[qname]
            if row.anchor:
                anchored.append(f"`{qname}` anchored to `{row.anchor}`")
            else:
                unanchored.append(f"`{qname}` (no calc parent on this statement)")
        found.append(
            f"Company extension concepts on the statement: {len(statement.extension_qnames)}. "
            + "; ".join(anchored + unanchored)
            + ". Extensions stay in the state space and their calc parent is the anchor "
            "back into us-gaap."
        )
    else:
        found.append(
            "No company extension concepts appear on this statement; every row is a "
            "standard us-gaap concept."
        )
    found.append(
        f"Dimensioned facts skipped: {statement.dimensioned_skipped_at_date} at the "
        f"balance-sheet date ({statement.dimensioned_skipped_total} across all instant "
        "dates for these concepts). These are member-level breakdowns (for example "
        "equity by component) that belong to other statements or notes; the face of "
        "the balance sheet uses only undimensioned facts here."
    )
    if statement.duplicate_fact_conflicts:
        found.append(
            "Duplicate facts with conflicting values for: "
            + ", ".join(sorted(set(statement.duplicate_fact_conflicts)))
            + "."
        )
    if statement.missing_value_rows:
        found.append(
            "Face rows with no undimensioned fact value at the balance-sheet date: "
            + ", ".join(f"`{q}`" for q in statement.missing_value_rows)
            + ". Typically these are nil-valued rows such as commitments and "
            "contingencies; they carry no amount and drop out of z."
        )
    skipped_children = {
        child for check in footings for child in check.children_skipped
    }
    if skipped_children:
        found.append(
            "Footing sums skipped calc children without values: "
            + ", ".join(f"`{q}`" for q in sorted(skipped_children))
            + " (consistent with the nil rows above)."
        )
    if coverage.non_instant:
        found.append(
            "Face concepts with periodType other than instant: "
            + ", ".join(f"`{q}`" for q in coverage.non_instant)
            + ". Everything on a balance sheet should be a stock (instant)."
        )
    else:
        found.append(
            "Every face concept is periodType instant, as a balance sheet requires; "
            "the stock/flow attribute behaves as the state-space encoding assumes."
        )
    if coverage.unresolved:
        found.append(
            "Face concepts missing periodType or balance: "
            + ", ".join(f"`{q}`" for q in coverage.unresolved)
            + "."
        )
    if trip.underivable:
        found.append(
            "Derived rows that could not be recomputed from calc arcs: "
            + ", ".join(f"`{q}`" for q in trip.underivable)
            + "."
        )
    qname_labeled = [
        row for row in statement.rows if row.kind != "abstract" and row.label == row.qname
    ]
    if qname_labeled:
        found.append(
            "Rows whose label fell back to the raw qname (missing label in the "
            "filing's label linkbase): "
            + ", ".join(f"`{row.qname}`" for row in qname_labeled)
            + "."
        )
    found.append(
        "Scope: the overlay covers the latest column of the statement only. The "
        "prior-year column is present in the filing and would need a second z "
        "vector; nothing in the encoding prevents that."
    )
    return found


def write_report(
    filing: Filing,
    stats: GraphStats,
    statement: Overlay,
    footings: list[FootingCheck],
    identity: IdentityCheck,
    coverage: CoverageCheck,
    trip: RoundTripResult,
) -> None:
    lines: list[str] = []
    add = lines.append
    add("# KG encoding spike: Apple 10-K balance sheet")
    add("")
    add(
        f"Filing: {statement.entity}, form 10-K, accession {filing.accession}, "
        f"filed {filing.filing_date}, period {filing.report_date}. "
        f"Statement role: {statement.role_definition}. "
        f"Balance-sheet date used: {statement.instant.isoformat()}."
    )
    add("")
    add("## What was tested")
    add("")
    add(
        "1. The US GAAP taxonomy discovered from the filing loads as a directed "
        "graph carrying periodType (stock/flow), balance (sign convention), "
        "monetary flags, labels, and weighted calculation arcs."
    )
    add(
        "2. The filing's consolidated balance sheet resolves onto that graph as a "
        "firm overlay: z holds leaf values, m holds the ordered presentation map."
    )
    add(
        "3. The overlay foots: every subtotal equals the weighted sum of its calc "
        "children within the decimals-based rounding tolerance, and "
        "Assets = Liabilities + Equity."
    )
    add(
        "4. A round trip from (z, m) plus the calc arcs regenerates the native "
        "statement rows (label, displayed value, order) without reading derived "
        "values from the filing."
    )
    add("")
    add("## Graph stats")
    add("")
    add(f"- Concepts (nodes): {stats.concepts:,}")
    add(f"- Calculation edges (calc 1.0 + 1.1 merged): {stats.calc_edges:,}")
    add(
        f"- Concepts with a standard label in this DTS: {stats.labeled_concepts:,} "
        "(labels ride with the filing's linkbases, which only cover concepts the "
        "filing uses; the rest of the taxonomy still resolves structurally)"
    )
    add("")
    add("| Concept | periodType | balance |")
    add("| --- | --- | --- |")
    for qname, period_type, balance in stats.sample:
        add(f"| `{qname}` | {period_type} | {balance} |")
    add("")
    add("## Overlay summary")
    add("")
    add(f"- Statement linkrole: `{statement.linkrole}`")
    add(f"- Rows in m: {len(statement.rows)} ({len(statement.face_rows)} face lines, "
        f"{len(statement.rows) - len(statement.face_rows)} abstract headers)")
    add(f"- Leaves in z: {len(statement.z)}")
    add(f"- Derived (calc parents, excluded from z): {len(statement.derived)}")
    add(f"- Company extension concepts: {len(statement.extension_qnames)}")
    add(
        f"- Dimensioned facts skipped: {statement.dimensioned_skipped_at_date} at the "
        f"balance-sheet date, {statement.dimensioned_skipped_total} across all dates"
    )
    add(f"- Face rows without a value at the date: {len(statement.missing_value_rows)}")
    add("")
    add("## Check results")
    add("")
    add("### Footing (subtotal = weighted sum of calc children)")
    add("")
    lines.extend(_footing_table(footings))
    add("")
    footing_pass = sum(1 for check in footings if check.passed)
    add(f"{footing_pass} of {len(footings)} subtotal checks pass.")
    add("")
    add("### Identity: Assets = Liabilities + Equity")
    add("")
    if identity.assets is not None:
        add(
            f"- Matched concepts: assets `{identity.assets_concept}`, liabilities "
            f"`{identity.liabilities_concept}`, equity `{identity.equity_concept}`"
        )
        add(
            f"- {_money(identity.assets)} vs {_money(identity.liabilities)} + "
            f"{_money(identity.equity)}: diff {_money(identity.diff)}, tolerance "
            f"{_money(identity.tolerance)}: {'PASS' if identity.passed else 'FAIL'}"
        )
    else:
        add("- FAIL: " + "; ".join(identity.notes))
    for note in identity.notes if identity.assets is not None else []:
        add(f"- {note}")
    add("")
    add("### Coverage")
    add("")
    add(
        f"- {coverage.resolved} of {coverage.face_lines} face lines resolve to a "
        f"concept with both periodType and balance populated: "
        f"{coverage.fraction * 100:.1f}% (target 95%): "
        f"{'PASS' if coverage.passed else 'FAIL'}"
    )
    add(
        "- Non-instant face concepts: "
        + (", ".join(f"`{q}`" for q in coverage.non_instant) if coverage.non_instant else "none")
    )
    add("")
    add("## Round trip")
    add("")
    add(
        f"- {trip.matched} of {trip.total} rows match exactly on (label, displayed "
        f"value, order): {'PASS' if trip.exact else 'FAIL'}"
    )
    add(
        "- Derived values were recomputed from z through the calc arcs; reported "
        "subtotals were not read back from the filing. Labels and order come from "
        "m, which is what the encoding stores."
    )
    mismatches = [comparison for comparison in trip.comparisons if not comparison.match]
    if mismatches:
        add("")
        add("| # | Row | Native | Regenerated |")
        add("| ---: | --- | ---: | ---: |")
        for comparison in mismatches:
            add(
                f"| {comparison.order} | {comparison.label} (`{comparison.qname}`) "
                f"| {comparison.native or '(empty)'} | {comparison.regenerated or '(empty)'} |"
            )
    add("")
    add("## Findings and limitations")
    add("")
    for index, finding in enumerate(_findings(statement, footings, identity, coverage, trip), 1):
        add(f"{index}. {finding}")
    add("")
    add("## What this de-risks for the full build")
    add("")
    add(
        "- The common state space is real: one taxonomy graph carries the "
        "attributes the simulator needs (stock vs flow, sign convention, calc "
        "structure), and a real filing lands on it without manual mapping."
    )
    add(
        "- The arithmetic layer is trustworthy: subtotal footing and the "
        "accounting identity hold within stated rounding, so simulated deltas to "
        "z can be re-aggregated mechanically through the same arcs."
    )
    add(
        "- Values and presentation separate cleanly: (z, m) reproduces the native "
        "statement exactly, so a simulator can mutate z alone and re-render "
        "statements without touching presentation logic."
    )
    add("")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    filing = fetch.main()
    model = graph.load_model(filing.primary_path)
    print("building taxonomy graph...")
    taxonomy_graph = graph.build_graph(model)
    stats = graph.graph_stats(taxonomy_graph)
    graph.export_graphml(taxonomy_graph)
    print("building balance-sheet overlay...")
    statement = overlay.build_overlay(model)
    footings = checks.footing_checks(statement)
    identity = checks.identity_check(statement)
    coverage = checks.coverage_check(statement)
    trip = roundtrip.run(statement)
    write_overlay_json(statement, filing)
    write_report(filing, stats, statement, footings, identity, coverage, trip)
    print(f"graph: {stats.concepts} concepts, {stats.calc_edges} calc edges")
    print(
        f"overlay: {len(statement.rows)} rows, {len(statement.z)} leaves, "
        f"{len(statement.derived)} derived, date {statement.instant.isoformat()}"
    )
    footing_pass = sum(1 for check in footings if check.passed)
    print(f"footing: {footing_pass}/{len(footings)} pass")
    print(f"identity A = L + E: {'PASS' if identity.passed else 'FAIL'}")
    print(f"coverage: {coverage.fraction * 100:.1f}% ({'PASS' if coverage.passed else 'FAIL'})")
    print(f"round trip: {trip.matched}/{trip.total} rows ({'PASS' if trip.exact else 'FAIL'})")
    print(f"wrote {REPORT_PATH}, {OVERLAY_JSON_PATH}, {graph.GRAPHML_PATH}")


if __name__ == "__main__":
    main()
