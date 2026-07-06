"""Native-label rendering of structured statements and simulation tables."""
from __future__ import annotations

from decimal import Decimal

from fss.simulate import ScenarioResult
from fss.statements import StructuredStatement


def _fmt(value: Decimal | None, unit: str | None, currency: str) -> str:
    if value is None:
        return "—"
    if unit and "/" in unit:  # per-share
        return f"{value:,.2f}"
    if unit == "shares":
        return f"{value:,.0f}"
    millions = value / Decimal(1_000_000)
    return f"{millions:,.0f}"


def statement_markdown(statement: StructuredStatement, title: str) -> list[str]:
    """Rows in native order and labels; monetary cells shown in millions."""
    lines = [f"#### {title}", ""]
    header = "| Line item | " + " | ".join(statement.columns) + " |"
    lines.append(header)
    lines.append("| --- | " + " | ".join("---:" for _ in statement.columns) + " |")
    for row in statement.rows:
        if row.kind == "abstract":
            lines.append(f"| **{row.label}** | " + " | ".join("" for _ in statement.columns) + " |")
            continue
        cells = []
        for period in statement.columns:
            cell = row.cell(period)
            shown = None
            unit = cell.unit if cell else None
            if cell and cell.value is not None:
                shown = cell.value * row.displayed_sign
            cells.append(_fmt(shown, unit, statement.currency))
        indent = "&nbsp;" * (2 * max(row.depth - 1, 0))
        bold = row.kind == "derived"
        label = f"**{row.label}**" if bold else row.label
        lines.append(f"| {indent}{label} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(
        f"*Monetary amounts in {statement.currency} millions; per-share amounts as reported.*"
    )
    lines.append("")
    return lines


def fan_table(results: dict[str, ScenarioResult], metric: str, scale: Decimal, label: str) -> list[str]:
    lines = [
        f"| Scenario | mean {label} | p5 | p25 | p50 | p75 | p95 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, result in results.items():
        row = [key]
        row.append(f"{result.mean(metric) / scale:,.0f}")
        for q in ("0.05", "0.25", "0.5", "0.75", "0.95"):
            row.append(f"{result.quantile(metric, Decimal(q)) / scale:,.0f}")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines
