"""The structured statement model.

A StructuredStatement is the normal form every extraction path produces and
every downstream stage consumes: ordered rows with native labels, one cell
per reported column, exact Decimal values, units, decimals, sign
conventions, and the derivation structure (calculation arcs and dimensional
aggregation) discovered from the filing.

Row identity is (concept, dims): face statements may repeat one concept
across axis members (Apple and Microsoft disaggregate revenue and cost of
sales by product/service on the face), and the undimensioned row is then the
member aggregate.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

STATEMENT_KINDS = ("balance_sheet", "income_statement", "cash_flow")

RowKey = tuple[str, tuple[tuple[str, str], ...]]  # (concept qname, sorted (axis, member))


@dataclass(frozen=True)
class Cell:
    period: str  # column key, e.g. "I2025-09-27" or "D2024-09-29:2025-09-27"
    value: Decimal | None  # fact-sign value in absolute units; None when not reported
    decimals: int | None  # None = exact (decimals INF) or no fact
    unit: str | None  # "USD", "EUR", "shares", "USD/shares", None for abstract


@dataclass(frozen=True)
class StatementRow:
    order: int
    concept: str
    dims: tuple[tuple[str, str], ...]  # sorted ((axis, member), ...); () = undimensioned
    label: str
    depth: int
    kind: str  # "abstract" | "leaf" | "derived"
    derivation: str  # "" | "calc" | "member_agg" (why the row is derived)
    preferred_label: str | None
    negated: bool
    displayed_sign: int
    period_type: str
    balance: str
    is_monetary: bool
    is_extension: bool
    anchor: str | None
    section: tuple[str, ...]  # labels of abstract ancestors, outermost first
    cells: tuple[Cell, ...]  # aligned with StructuredStatement.columns

    @property
    def key(self) -> RowKey:
        return (self.concept, self.dims)

    def cell(self, period: str) -> Cell | None:
        for cell in self.cells:
            if cell.period == period:
                return cell
        return None

    def displayed(self, period: str) -> Decimal | None:
        cell = self.cell(period)
        if cell is None or cell.value is None:
            return None
        return cell.value * self.displayed_sign


@dataclass
class StructuredStatement:
    company: str
    standard: str
    statement: str  # one of STATEMENT_KINDS
    linkrole: str
    role_definition: str
    currency: str
    columns: tuple[str, ...]  # newest first
    rows: list[StatementRow]
    # concept-level calculation arcs restricted to concepts on this statement:
    # parent concept -> [(child concept, weight)]
    calc_children: dict[str, list[tuple[str, Decimal]]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def face_rows(self) -> list[StatementRow]:
        return [row for row in self.rows if row.kind != "abstract"]

    @property
    def leaf_rows(self) -> list[StatementRow]:
        return [row for row in self.rows if row.kind == "leaf"]

    def row(self, key: RowKey) -> StatementRow | None:
        for candidate in self.rows:
            if candidate.key == key:
                return candidate
        return None

    def rows_for_concept(self, concept: str) -> list[StatementRow]:
        return [row for row in self.rows if row.concept == concept]

    # ---- canonical serialization (exact: Decimals as strings) ----

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["columns"] = list(self.columns)
        payload["rows"] = [_row_payload(row) for row in self.rows]
        payload["calc_children"] = {
            parent: [[child, str(weight)] for child, weight in kids]
            for parent, kids in sorted(self.calc_children.items())
        }
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "StructuredStatement":
        rows = [_row_from_payload(row) for row in payload["rows"]]
        calc = {
            parent: [(child, Decimal(weight)) for child, weight in kids]
            for parent, kids in payload["calc_children"].items()
        }
        return cls(
            company=payload["company"],
            standard=payload["standard"],
            statement=payload["statement"],
            linkrole=payload["linkrole"],
            role_definition=payload["role_definition"],
            currency=payload["currency"],
            columns=tuple(payload["columns"]),
            rows=rows,
            calc_children=calc,
            notes=list(payload.get("notes", [])),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_payload(), indent=1, default=str) + "\n", encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> "StructuredStatement":
        return cls.from_payload(json.loads(path.read_text(encoding="utf-8")))


def _row_payload(row: StatementRow) -> dict[str, Any]:
    data = asdict(row)
    data["dims"] = [list(pair) for pair in row.dims]
    data["section"] = list(row.section)
    data["cells"] = [
        {
            "period": cell.period,
            "value": None if cell.value is None else str(cell.value),
            "decimals": cell.decimals,
            "unit": cell.unit,
        }
        for cell in row.cells
    ]
    return data


def _row_from_payload(data: dict[str, Any]) -> StatementRow:
    cells = tuple(
        Cell(
            period=cell["period"],
            value=None if cell["value"] is None else Decimal(cell["value"]),
            decimals=cell["decimals"],
            unit=cell["unit"],
        )
        for cell in data["cells"]
    )
    return StatementRow(
        order=data["order"],
        concept=data["concept"],
        dims=tuple((pair[0], pair[1]) for pair in data["dims"]),
        label=data["label"],
        depth=data["depth"],
        kind=data["kind"],
        derivation=data.get("derivation", ""),
        preferred_label=data["preferred_label"],
        negated=data["negated"],
        displayed_sign=data["displayed_sign"],
        period_type=data["period_type"],
        balance=data["balance"],
        is_monetary=data["is_monetary"],
        is_extension=data["is_extension"],
        anchor=data["anchor"],
        section=tuple(data["section"]),
        cells=cells,
    )
