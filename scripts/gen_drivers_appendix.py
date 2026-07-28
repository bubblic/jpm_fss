#!/usr/bin/env python
"""Generate proposal/drivers_appendix.tex: scenarios, drivers, dispatch.

Three tables: the scenario definitions with their conditioning values
(imported from fss.drivers.SCENARIOS), the response parameters and noise
scales with their rationale comments (parsed from src/fss/drivers.py and
src/fss/config.py), and the nine drivers with their meanings (parsed
from the DriverDraw fields) and their dispatch: which roles each driver
acts on and how. The dispatch column restates
fss.engine.project.Projector.project and is kept in sync with it by
hand, the same discipline as the Apple overlay's law-of-motion column;
the acceptance battery gates both. A sync tripwire asserts the dispatch
rows match the DriverDraw fields exactly.

Regenerate (PowerShell, from the repo root):
    $env:PYTHONPATH = "src"
    python scripts/gen_drivers_appendix.py

The output file is committed; do not hand-edit it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fss.drivers import SCENARIOS  # noqa: E402

DRIVERS_SOURCE = ROOT / "src" / "fss" / "drivers.py"
CONFIG_SOURCE = ROOT / "src" / "fss" / "config.py"
OUT = ROOT / "proposal" / "drivers_appendix.tex"

# Which roles each driver acts on, and how: restates Projector.project.
DISPATCH: dict[str, tuple[str, str]] = {
    "revenue_growth": (
        "REVENUE; the CF\\_WC-bound stocks; CF\\_DA, CF\\_SBC, CF\\_CAPEX, "
        "CF\\_SBC\\_TAX\\_WITHHOLD",
        "revenue rows scale by $1+g$; working-capital stocks bound on the "
        "firm's own cash flow move to base $\\times(1+g)$; the "
        "activity-linked flows scale with it",
    ),
    "cogs_ratio_shift": (
        "COGS; the INVENTORY and AP targets",
        "cost rows scale by $(1+g)(1+\\text{shift})$, and the inventory and "
        "payables working-capital targets move with the same factor",
    ),
    "opex_growth": (
        "OPEX\\_RND, OPEX\\_SELLING, OPEX\\_ADMIN",
        "the semi-variable expense families scale by $1+g_{\\text{opex}}$; "
        "other operating expense holds at base",
    ),
    "restructuring_factor": (
        "RESTRUCTURING",
        "restructuring rows scale by the factor",
    ),
    "asset_yield_shift": (
        "INTEREST\\_INCOME (OTHER\\_INCOME when no separate lines)",
        "interest income reprices as (base yield $+$ shift) on the firm's "
        "own cash and securities balances; without separate interest lines "
        "the net rate effect lands on other income",
    ),
    "debt_rate_shift": (
        "INTEREST\\_EXPENSE (OTHER\\_INCOME when no separate lines)",
        "interest expense reprices as (base rate $+$ shift) on the firm's "
        "own debt and commercial paper balances",
    ),
    "tax_rate_shift": (
        "TAX; the CF tax articulation rows",
        "the effective rate, clipped to 5\\% to 45\\%, applies to projected "
        "pretax income through the firm's own calculation arcs",
    ),
    "dividend_growth": (
        "CF\\_DIVIDENDS; the RETAINED\\_EARNINGS leg",
        "dividends paid scale by $1+d$ and post against retained earnings",
    ),
    "buyback_factor": (
        "CF\\_BUYBACK; the TREASURY or RETAINED\\_EARNINGS leg; "
        "SHARE\\_COUNT and EPS",
        "repurchases scale by the factor, post into treasury or against "
        "retained earnings, and scale the share-count trend that per-share "
        "figures recompute from",
    ),
}


def parsed_constants(source: Path) -> list[tuple[str, str, str]]:
    pattern = re.compile(r'^([A-Z][A-Z0-9_]*) = Decimal\("([^"]+)"\)\s*# (.*)$')
    found: list[tuple[str, str, str]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            found.append((match.group(1), match.group(2), match.group(3)))
    return found


def parsed_fields() -> list[tuple[str, str]]:
    pattern = re.compile(r"^    (\w+): Decimal\s*# (.*)$")
    fields: list[tuple[str, str]] = []
    in_class = False
    for line in DRIVERS_SOURCE.read_text(encoding="utf-8").splitlines():
        if line.startswith("class DriverDraw"):
            in_class = True
            continue
        if in_class and line and not line.startswith(" "):
            break
        if in_class:
            match = pattern.match(line)
            if match:
                fields.append((match.group(1), match.group(2)))
    return fields


def tt(name: str) -> str:
    return r"\texttt{" + name.replace("_", r"\_\allowbreak{}") + "}"


def text(value: str) -> str:
    """Escape LaTeX specials in text pulled from the code (descriptions and
    rationale comments name identifiers like rate_hike)."""
    return (
        value.replace("&", r"\&")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("_", r"\_")
    )


def main() -> None:
    fields = parsed_fields()
    assert [name for name, _ in fields] == list(DISPATCH), (
        "dispatch table out of sync with DriverDraw fields"
    )
    parameters = parsed_constants(DRIVERS_SOURCE)
    sigmas = [
        entry for entry in parsed_constants(CONFIG_SOURCE) if entry[0].endswith("SIGMA")
    ]

    lines: list[str] = [
        "% GENERATED FILE, do not hand-edit.",
        "% Rebuilt by scripts/gen_drivers_appendix.py from src/fss/drivers.py,",
        "% src/fss/config.py, and the dispatch of src/fss/engine/project.py;",
        "% regenerate after any change to scenarios, parameters, or dispatch.",
        r"\begingroup",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.18}",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{1.9cm}"
        r">{\raggedright\arraybackslash}p{6.3cm}rrrrr@{}}",
        r"\multicolumn{7}{@{}l}{\headtext{The %d scenarios (conditioning values, hand-chosen)}}\\[3pt]"
        % len(SCENARIOS),
        r"\headtext{Scenario} & \headtext{Conditioning} & "
        r"\headtext{$\Delta g^{\text{GDP}}$ pp} & \headtext{$\Delta\pi$ pp} & "
        r"\headtext{$\Delta r$ bp} & \headtext{$z_c$} & \headtext{$z_d$} \\",
        r"\hline",
        r"\endhead",
    ]
    for scenario in SCENARIOS.values():
        lines.append(
            "%s & %s & $%s$ & $%s$ & $%s$ & $%s$ & $%s$ \\\\"
            % (
                tt(scenario.key),
                text(scenario.description),
                scenario.gdp_growth_pp,
                scenario.inflation_pp,
                scenario.rate_shift_bp,
                scenario.competition_z,
                scenario.demand_z,
            )
        )
    lines += [r"\hline", r"\end{longtable}"]

    lines += [
        r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{4.9cm}r"
        r">{\raggedright\arraybackslash}p{8.6cm}@{}}",
        r"\multicolumn{3}{@{}l}{\headtext{The %d response parameters and %d noise scales (chosen by argument, documented)}}\\[3pt]"
        % (len(parameters), len(sigmas)),
        r"\headtext{Parameter} & \headtext{Value} & \headtext{Rationale, as documented in the code} \\",
        r"\hline",
        r"\endhead",
    ]
    for name, value, comment in parameters + sigmas:
        lines.append("%s & $%s$ & %s \\\\" % (tt(name), value, text(comment)))
    lines += [r"\hline", r"\end{longtable}"]

    lines += [
        r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{2.3cm}"
        r">{\raggedright\arraybackslash}p{3.3cm}"
        r">{\raggedright\arraybackslash}p{3.4cm}"
        r">{\raggedright\arraybackslash}p{5.6cm}@{}}",
        r"\multicolumn{4}{@{}l}{\headtext{The %d drivers and their dispatch (which roles each acts on, and how)}}\\[3pt]"
        % len(fields),
        r"\headtext{Driver} & \headtext{Meaning} & \headtext{Acts on the roles} & \headtext{Mechanism in the engine} \\",
        r"\hline",
        r"\endfirsthead",
        r"\multicolumn{4}{@{}l}{\headtext{The drivers and their dispatch, continued}}\\[3pt]",
        r"\headtext{Driver} & \headtext{Meaning} & \headtext{Acts on the roles} & \headtext{Mechanism in the engine} \\",
        r"\hline",
        r"\endhead",
    ]
    for name, meaning in fields:
        acts_on, mechanism = DISPATCH[name]
        lines.append(
            "%s & %s & \\texttt{%s} & %s \\\\"
            % (tt(name), text(meaning), acts_on, mechanism)
        )
    lines += [r"\hline", r"\end{longtable}", r"\endgroup"]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT}: {len(SCENARIOS)} scenarios, "
        f"{len(parameters)} parameters, {len(sigmas)} noise scales, "
        f"{len(fields)} drivers"
    )


if __name__ == "__main__":
    main()
