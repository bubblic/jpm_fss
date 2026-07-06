"""Encode/decode adapters: E(s) = (z, m) and D(z, m) = s.

z holds the values of information-bearing rows (leaves) per period; m holds
everything else needed to re-render the native statement: row order, labels,
signs, units, decimals, sections, the calculation structure, and column
periods. Derived rows (calculation parents and member aggregates) are
dropped from z and recomputed on decode; that reduction is lossless because
the dropped values are exact functions of the kept ones.

Where a filer's own reported subtotal differs from the recomputed sum
(rounding inside the filing), the row is demoted to a stored leaf and the
discrepancy is recorded: reconstruction stays exact and the inconsistency
is surfaced instead of hidden. Injectivity of E (and hence the existence of
the lossless decoder) is by construction: z and m together carry every cell
and every presentation attribute of s.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from fss.statements import Cell, StatementRow, StructuredStatement

RowKeyStr = str  # "concept", "concept|axis=member;...", optional "@start"/"@end"


def _period_role(row: StatementRow) -> str:
    """Distinguishes instant rows on a duration statement (beginning vs
    ending cash share one concept and dims; only the preferred label's
    period role separates them, so the encoding key must carry it)."""
    preferred = (row.preferred_label or "").lower()
    if row.period_type == "instant" and "periodstart" in preferred:
        return "@start"
    if row.period_type == "instant" and "periodend" in preferred:
        return "@end"
    return ""


def row_key_str(row: StatementRow) -> RowKeyStr:
    key = row.concept
    if row.dims:
        dims = ";".join(f"{axis}={member}" for axis, member in row.dims)
        key = f"{key}|{dims}"
    return key + _period_role(row)


def _canon(value: Decimal) -> Decimal:
    return value.quantize(Decimal(1)) if value == value.to_integral_value() else value


@dataclass
class Encoded:
    company: str
    statement: str
    z: dict[RowKeyStr, dict[str, Decimal]]  # leaf values: key -> period -> value
    m: dict[str, Any]  # presentation map (rows sans leaf values, calc, columns)
    demotions: list[str] = field(default_factory=list)


def _recompute_cell(
    statement: StructuredStatement,
    row: StatementRow,
    period: str,
    values: dict[tuple[str, tuple], Decimal | None],
    visiting: frozenset,
) -> Decimal | None:
    """Value of a derived row from leaves, through member aggregation and
    calculation arcs, recursively."""
    key = (row.concept, row.dims)
    if key in values:
        return values[key]
    if key in visiting:
        return None
    visiting = visiting | {key}
    total = Decimal(0)
    contributed = False
    if row.derivation == "member_agg":
        for candidate in statement.rows_for_concept(row.concept):
            if candidate.dims and candidate.kind != "abstract":
                child = _resolve(statement, candidate, period, values, visiting)
                if child is not None:
                    total += child
                    contributed = True
    else:  # calc
        for child_concept, weight in statement.calc_children.get(row.concept, []):
            child_rows = [
                candidate
                for candidate in statement.rows_for_concept(child_concept)
                if not candidate.dims and candidate.kind != "abstract"
            ]
            if not child_rows:
                continue
            child = _resolve(statement, child_rows[0], period, values, visiting)
            if child is not None:
                total += weight * child
                contributed = True
    return _canon(total) if contributed else None


def _resolve(
    statement: StructuredStatement,
    row: StatementRow,
    period: str,
    values: dict[tuple[str, tuple], Decimal | None],
    visiting: frozenset,
) -> Decimal | None:
    key = (row.concept, row.dims)
    if key in values:
        return values[key]
    if row.kind == "derived":
        return _recompute_cell(statement, row, period, values, visiting)
    cell = row.cell(period)
    return cell.value if cell else None


def _find_demotions(statement: StructuredStatement) -> tuple[set[tuple[str, tuple]], list[str]]:
    """Derived rows whose reported cells are not exactly recomputable.

    Rows are checked in statement order (children print before their
    subtotals), and a demoted row's reported values become available to the
    rows after it, so one filer-rounded subtotal does not cascade into
    demoting everything above it.
    """
    demoted: set[tuple[str, tuple]] = set()
    notes: list[str] = []
    resolved: dict[str, dict[tuple[str, tuple], Decimal | None]] = {}
    for period in statement.columns:
        resolved[period] = {
            (row.concept, row.dims): (row.cell(period).value if row.cell(period) else None)
            for row in statement.rows
            if row.kind == "leaf"
        }
    for row in statement.rows:
        if row.kind != "derived":
            continue
        for period in statement.columns:
            reported = row.cell(period)
            if reported is None or reported.value is None:
                continue
            recomputed = _recompute_cell(statement, row, period, resolved[period], frozenset())
            if recomputed is None or _canon(recomputed) != _canon(reported.value):
                demoted.add((row.concept, row.dims))
                notes.append(
                    f"{row.label} [{row.concept}] {period}: reported "
                    f"{reported.value} vs recomputed {recomputed}"
                )
                break
        if (row.concept, row.dims) in demoted:
            for period in statement.columns:
                cell = row.cell(period)
                resolved[period][(row.concept, row.dims)] = (
                    cell.value if cell else None
                )
    return demoted, notes


def encode(statement: StructuredStatement) -> Encoded:
    """Split the statement into (z, m), demoting underivable derived cells."""
    demoted, demotions = _find_demotions(statement)
    stored: dict[RowKeyStr, dict[str, Decimal]] = {}
    row_meta: list[dict[str, Any]] = []
    for row in statement.rows:
        keep_values = row.kind == "leaf" or (
            row.kind == "derived" and (row.concept, row.dims) in demoted
        )
        meta = {
            "order": row.order,
            "concept": row.concept,
            "dims": [list(pair) for pair in row.dims],
            "label": row.label,
            "depth": row.depth,
            "kind": "leaf" if (row.kind == "derived" and keep_values) else row.kind,
            "derivation": "" if (row.kind == "derived" and keep_values) else row.derivation,
            "preferred_label": row.preferred_label,
            "negated": row.negated,
            "displayed_sign": row.displayed_sign,
            "period_type": row.period_type,
            "balance": row.balance,
            "is_monetary": row.is_monetary,
            "is_extension": row.is_extension,
            "anchor": row.anchor,
            "section": list(row.section),
            "cells": [
                {"period": cell.period, "decimals": cell.decimals, "unit": cell.unit}
                for cell in row.cells
            ],
        }
        row_meta.append(meta)
        if keep_values and row.kind != "abstract":
            per_period = {
                cell.period: cell.value for cell in row.cells if cell.value is not None
            }
            if per_period:
                stored[row_key_str(row)] = per_period
    m = {
        "company": statement.company,
        "standard": statement.standard,
        "statement": statement.statement,
        "linkrole": statement.linkrole,
        "role_definition": statement.role_definition,
        "currency": statement.currency,
        "columns": list(statement.columns),
        "rows": row_meta,
        "calc_children": {
            parent: [[child, str(weight)] for child, weight in kids]
            for parent, kids in statement.calc_children.items()
        },
        "notes": list(statement.notes),
    }
    return Encoded(statement.company, statement.statement, stored, m, demotions)


def decode(encoded: Encoded) -> StructuredStatement:
    """Re-render the statement from (z, m); derived cells recomputed."""
    m = encoded.m
    calc = {
        parent: [(child, Decimal(weight)) for child, weight in kids]
        for parent, kids in m["calc_children"].items()
    }
    columns = tuple(m["columns"])
    # first pass: rows with stored/leaf values
    draft_rows: list[StatementRow] = []
    for meta in m["rows"]:
        dims = tuple((pair[0], pair[1]) for pair in meta["dims"])
        key = f"{meta['concept']}|{';'.join(f'{a}={b}' for a, b in dims)}" if dims else meta["concept"]
        preferred = (meta["preferred_label"] or "").lower()
        if meta["period_type"] == "instant" and "periodstart" in preferred:
            key += "@start"
        elif meta["period_type"] == "instant" and "periodend" in preferred:
            key += "@end"
        stored = encoded.z.get(key, {})
        cells = tuple(
            Cell(
                period=cell_meta["period"],
                value=stored.get(cell_meta["period"]) if meta["kind"] == "leaf" else None,
                decimals=cell_meta["decimals"],
                unit=cell_meta["unit"],
            )
            for cell_meta in meta["cells"]
        )
        draft_rows.append(
            StatementRow(
                order=meta["order"],
                concept=meta["concept"],
                dims=dims,
                label=meta["label"],
                depth=meta["depth"],
                kind=meta["kind"],
                derivation=meta["derivation"],
                preferred_label=meta["preferred_label"],
                negated=meta["negated"],
                displayed_sign=meta["displayed_sign"],
                period_type=meta["period_type"],
                balance=meta["balance"],
                is_monetary=meta["is_monetary"],
                is_extension=meta["is_extension"],
                anchor=meta["anchor"],
                section=tuple(meta["section"]),
                cells=cells,
            )
        )
    statement = StructuredStatement(
        company=m["company"],
        standard=m["standard"],
        statement=m["statement"],
        linkrole=m["linkrole"],
        role_definition=m["role_definition"],
        currency=m["currency"],
        columns=columns,
        rows=draft_rows,
        calc_children=calc,
        notes=list(m["notes"]),
    )
    # second pass: recompute derived cells
    final_rows: list[StatementRow] = []
    for row in statement.rows:
        if row.kind != "derived":
            final_rows.append(row)
            continue
        new_cells = []
        for cell in row.cells:
            leaf_values: dict[tuple[str, tuple], Decimal | None] = {
                (candidate.concept, candidate.dims): (
                    candidate.cell(cell.period).value
                    if candidate.cell(cell.period)
                    else None
                )
                for candidate in statement.rows
                if candidate.kind == "leaf"
            }
            value = _recompute_cell(statement, row, cell.period, leaf_values, frozenset())
            new_cells.append(
                Cell(cell.period, value, cell.decimals, cell.unit)
            )
        final_rows.append(
            StatementRow(
                order=row.order,
                concept=row.concept,
                dims=row.dims,
                label=row.label,
                depth=row.depth,
                kind=row.kind,
                derivation=row.derivation,
                preferred_label=row.preferred_label,
                negated=row.negated,
                displayed_sign=row.displayed_sign,
                period_type=row.period_type,
                balance=row.balance,
                is_monetary=row.is_monetary,
                is_extension=row.is_extension,
                anchor=row.anchor,
                section=row.section,
                cells=tuple(new_cells),
            )
        )
    statement.rows = final_rows
    return statement


@dataclass
class ReconstructionResult:
    company: str
    statement: str
    exact: bool
    cells_checked: int
    diffs: list[str]
    demotions: list[str]


def verify_reconstruction(statement: StructuredStatement) -> ReconstructionResult:
    """encode -> decode must reproduce every cell and every attribute."""
    encoded = encode(statement)
    decoded = decode(encoded)
    diffs: list[str] = []
    cells = 0
    if len(decoded.rows) != len(statement.rows):
        diffs.append(f"row count {len(decoded.rows)} != {len(statement.rows)}")
    for original, rebuilt in zip(statement.rows, decoded.rows):
        for attr in (
            "order",
            "concept",
            "dims",
            "label",
            "depth",
            "preferred_label",
            "negated",
            "displayed_sign",
            "period_type",
            "balance",
            "is_monetary",
            "is_extension",
            "anchor",
            "section",
        ):
            if getattr(original, attr) != getattr(rebuilt, attr):
                diffs.append(
                    f"{original.label}: attribute {attr} "
                    f"{getattr(original, attr)!r} != {getattr(rebuilt, attr)!r}"
                )
        for cell_a, cell_b in zip(original.cells, rebuilt.cells):
            cells += 1
            value_a = cell_a.value
            value_b = cell_b.value
            equal = (
                value_a is None and value_b is None
                or (value_a is not None and value_b is not None and value_a == value_b)
            )
            if not equal or cell_a.period != cell_b.period or cell_a.decimals != cell_b.decimals or cell_a.unit != cell_b.unit:
                diffs.append(
                    f"{original.label} {cell_a.period}: "
                    f"({value_a}, {cell_a.decimals}, {cell_a.unit}) != "
                    f"({value_b}, {cell_b.decimals}, {cell_b.unit})"
                )
    return ReconstructionResult(
        company=statement.company,
        statement=statement.statement,
        exact=not diffs,
        cells_checked=cells,
        diffs=diffs[:20],
        demotions=encoded.demotions,
    )
