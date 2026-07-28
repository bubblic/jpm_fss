#!/usr/bin/env python
"""Generate proposal/roles_appendix.tex: the behavior layer's wiring surface.

Lists every economic role of the common behavior layer with its curated
concept-table entries (us-gaap and ifrs-full local names) and its label
rules, grouped by statement, exactly as the classifier defines them.
Nothing is hand-typed: the role groups come from the section markers of
src/fss/engine/roles.py read in source order, and the bindings from the
imported tables (CONCEPT_ROLES, LABEL_RULES), so the listing cannot
drift from the code.

Regenerate (PowerShell, from the repo root):
    $env:PYTHONPATH = "src"
    python scripts/gen_roles_appendix.py

The output file is committed; do not hand-edit it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fss.engine import roles as R  # noqa: E402

SOURCE = ROOT / "src" / "fss" / "engine" / "roles.py"
OUT = ROOT / "proposal" / "roles_appendix.tex"

GROUP_TITLES = {
    "income statement roles": "Income statement",
    "balance sheet roles": "Balance sheet",
    "cash flow roles": "Cash flow",
}


def role_groups() -> list[tuple[str, list[tuple[str, str]]]]:
    """(group title, [(constant name, role value), ...]) in source order."""
    groups: list[tuple[str, list[tuple[str, str]]]] = []
    current: tuple[str, list[tuple[str, str]]] | None = None
    marker = re.compile(r"^# ---- (.+?) ----$")
    definition = re.compile(r'^([A-Z][A-Z0-9_]*) = "([a-z0-9_]+)"')
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        found = marker.match(line.strip())
        if found:
            title = GROUP_TITLES.get(found.group(1))
            current = (title, []) if title else None
            if current:
                groups.append(current)
            continue
        if current is None:
            continue
        defined = definition.match(line)
        if defined:
            current[1].append((defined.group(1), defined.group(2)))
    return groups


def tt_constant(name: str) -> str:
    return r"\texttt{" + name.replace("_", r"\_\allowbreak{}") + "}"


def tt_concept(local_name: str) -> str:
    """CamelCase local names get break opportunities at the humps, else the
    longest taxonomy names overflow any column."""
    broken = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", r"\\allowbreak{}", local_name)
    return r"\texttt{" + broken + "}"


def tt_pattern(pattern: str) -> str:
    escaped = pattern.replace("$", r"\$").replace("^", r"\^{}")
    escaped = escaped.replace("|", r"|\allowbreak{}")
    return r"\texttt{" + escaped + "}"


def main() -> None:
    groups = role_groups()
    total = sum(len(members) for _, members in groups)
    constants = {
        name for name, value in vars(R).items()
        if name.isupper() and isinstance(value, str)
    }
    listed = {name for _, members in groups for name, _ in members}
    assert listed == constants, sorted(constants ^ listed)
    assert total == 90, f"role count changed to {total}: update every 'ninety' claim"
    concept_count = len(R.CONCEPT_ROLES)
    rule_count = len(R.LABEL_RULES)

    lines: list[str] = [
        "% GENERATED FILE, do not hand-edit.",
        "% Rebuilt by scripts/gen_roles_appendix.py from src/fss/engine/roles.py;",
        "% regenerate after any change to the role vocabulary or its tables.",
        r"\noindent The classifier defines %d roles: %s. The curated concept"
        % (total, ", ".join(
            "%d for the %s" % (len(members), title.lower())
            for title, members in groups
        )),
        r"table binds %d standard local names and %d label rules follow it;"
        % (concept_count, rule_count),
        r"both appear in full below. A role listed with neither binding is",
        r"assigned only by the in-code steps described above.",
        r"\begingroup",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.18}",
        r"\setlength{\tabcolsep}{5pt}",
    ]
    for title, members in groups:
        concept_entries = sum(
            1 for role in {value for _, value in members}
            for mapped in R.CONCEPT_ROLES.values() if mapped == role
        )
        lines += [
            r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{2.9cm}"
            r">{\raggedright\arraybackslash}p{7.9cm}"
            r">{\raggedright\arraybackslash}p{4.0cm}@{}}",
            r"\multicolumn{3}{@{}l}{\headtext{%s: %d roles, %d curated concept entries}}\\[3pt]"
            % (title, len(members), concept_entries),
            r"\headtext{Role} & \headtext{Curated concepts (us-gaap and ifrs-full local names)} & \headtext{Label rules} \\",
            r"\hline",
            r"\endfirsthead",
            r"\multicolumn{3}{@{}l}{\headtext{%s, continued}}\\[3pt]" % title,
            r"\headtext{Role} & \headtext{Curated concepts (us-gaap and ifrs-full local names)} & \headtext{Label rules} \\",
            r"\hline",
            r"\endhead",
        ]
        for name, value in members:
            concepts = [
                local for local, mapped in R.CONCEPT_ROLES.items() if mapped == value
            ]
            rules = [pattern for pattern, mapped in R.LABEL_RULES if mapped == value]
            lines.append(
                "%s & %s & %s \\\\"
                % (
                    tt_constant(name),
                    ", ".join(tt_concept(c) for c in concepts),
                    " \\quad ".join(tt_pattern(p) for p in rules),
                )
            )
        lines += [r"\hline", r"\end{longtable}"]
    lines.append(r"\endgroup")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT}: {total} roles, {concept_count} concept entries, "
        f"{rule_count} label rules"
    )


if __name__ == "__main__":
    main()
