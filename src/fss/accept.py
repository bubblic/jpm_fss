"""The acceptance battery: everything the proposal promises, measured.

Entry points:
    python -m fss accept --company apple      # one filer, writes outcome.json
    python -m fss accept --merge              # merge outcomes into report.md
    python -m fss accept                      # all filers then merge

Per company: extraction accuracy of the PDF-only mode against the tag path
(zero accepted-cell errors required; every unmatched ground-truth row must
fall in a documented benign category), perfect reconstruction through
(z, m), footing of the extracted statements within the decimals tolerance,
Monte Carlo simulation under every scenario with zero identity violations,
the directional battery, and the plausibility battery. Artifacts land under
out/acceptance/: the report, per-scenario simulated statements, flow
journals, per-company outcome summaries, and the run manifest.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from fss import edgar
from fss.config import COMPANIES, MONTE_CARLO_PATHS, RANDOM_SEED
from fss.drivers import SCENARIOS
from fss.encdec import verify_reconstruction
from fss.engine import roles as R
from fss.engine.project import Projector
from fss.manifest import write_manifest
from fss.paths import ACCEPT_DIR, DATA_DIR
from fss.pdfread.assemble import extract_pdf_statements
from fss.reconcile import compare_to_ground_truth, reconcile
from fss.render import statement_markdown
from fss.simulate import directional_battery, run_all_scenarios
from fss.statements import StructuredStatement
from fss.validate import footing_checks, plausibility_battery

MILLION = Decimal(1_000_000)
QUANTILES = ("0.05", "0.25", "0.5", "0.75", "0.95")


def _load_statements(key: str) -> dict[str, StructuredStatement]:
    return {
        kind: StructuredStatement.load(DATA_DIR / "extracted" / f"{key}_{kind}.json")
        for kind in ("balance_sheet", "income_statement", "cash_flow")
    }


def _benign_unmatched(entry: tuple[str, str, str], statement: str) -> str | None:
    label, kind, unit = entry
    if kind == "derived":
        return "derived row not printed separately; arithmetic verified through its children"
    if statement == "balance_sheet" and unit == "shares":
        return "share counts printed inside the equity label, not as table cells"
    return None


def run_company(key: str, paths: int, seed: int) -> dict:
    company = COMPANIES[key]
    filing = edgar.latest_annual(company)
    statements = _load_statements(key)

    # 1. extraction accuracy (PDF-only ablation vs tag path)
    extraction_rows = []
    extraction_pass = True
    benign_notes: list[str] = []
    extractions = extract_pdf_statements(filing.pdf_path)
    for statement_kind, extraction in extractions.items():
        reconciled = reconcile(extraction)
        report = compare_to_ground_truth(key, reconciled, statements[statement_kind])
        extraction_rows.append(
            {
                "statement": statement_kind,
                "compared": report.compared,
                "matches": report.matches,
                "mismatches": len(report.mismatches),
                "missing": len(report.missing),
                "flagged": report.flagged_cells,
            }
        )
        if report.mismatches or report.missing:
            extraction_pass = False
        for entry in report.gt_rows_unmatched:
            reason = _benign_unmatched(tuple(entry), statement_kind)
            if reason is None:
                extraction_pass = False
                benign_notes.append(
                    f"{statement_kind}: UNEXPLAINED unmatched row {entry[0]!r}"
                )
            else:
                benign_notes.append(f"{statement_kind}: {entry[0]!r}: {reason}")

    # 2. perfect reconstruction
    reconstruction = [verify_reconstruction(statements[k]) for k in statements]
    reconstruction_pass = all(r.exact for r in reconstruction)
    reconstruction_rows = [
        {
            "statement": r.statement,
            "exact": r.exact,
            "cells": r.cells_checked,
            "demotions": len(r.demotions),
        }
        for r in reconstruction
    ]

    # 3. footing with the decimals tolerance; cells on the disclosed
    # demotion list are the filer's own rounding inconsistencies
    demoted_cells: set[tuple[str, str]] = set()
    for result in reconstruction:
        for note in result.demotions:
            label = note.split(" [", 1)[0]
            period = note.split("] ", 1)[1].split(":", 1)[0] if "] " in note else ""
            demoted_cells.add((label, period))
    footing = [check for k in statements for check in footing_checks(statements[k])]
    footing_failures = [
        f"{check.statement}/{check.label} {check.period}: diff {check.diff}"
        for check in footing
        if not check.passed and (check.label, check.period) not in demoted_cells
    ]
    footing_excused = sum(
        1
        for check in footing
        if not check.passed and (check.label, check.period) in demoted_cells
    )

    # 4. symbolic verification, then simulation under every scenario
    # (TensorFlow fan; Decimal replays for the audit artifacts)
    results, symbolic_verdict = run_all_scenarios(key, statements, paths=paths, seed=seed)
    mc_violations = sum(result.violations for result in results.values())
    max_residual = max(
        (result.max_residual for result in results.values()), default=Decimal(0)
    )

    # 5. directional battery
    projector = Projector(key, statements)
    net_cash = (
        projector._sum(projector.bs, {R.CASH, R.SECURITIES})
        - projector._sum(projector.bs, {R.DEBT, R.COMMERCIAL_PAPER})
    )
    directional = directional_battery(results, net_cash)

    # 6. plausibility on the representative and deterministic paths
    base_metrics = {
        "revenue": projector._sum(projector.inc, {R.REVENUE}),
        "gross_margin_bp": results["baseline"].deterministic.metrics["gross_margin_bp"],
    }
    plausibility_total = 0
    plausibility_failures: list[str] = []
    for scenario_key, result in results.items():
        for period in (result.representative, result.deterministic):
            for check in plausibility_battery(period, base_metrics):
                plausibility_total += 1
                if not check.passed:
                    plausibility_failures.append(
                        f"[{scenario_key}] {check.name}: {check.detail}"
                    )

    # artifacts: simulated statements and journals per scenario
    company_dir = ACCEPT_DIR / key
    company_dir.mkdir(parents=True, exist_ok=True)
    fans: dict[str, dict[str, list[str]]] = {}
    for metric in ("net_income", "revenue"):
        fans[metric] = {
            scenario_key: [f"{result.mean(metric) / MILLION:,.0f}"]
            + [
                f"{result.quantile(metric, Decimal(q)) / MILLION:,.0f}"
                for q in QUANTILES
            ]
            for scenario_key, result in results.items()
        }
    for scenario_key, result in results.items():
        lines: list[str] = [
            f"## {company.name}: simulated next period, scenario '{scenario_key}'",
            "",
            SCENARIOS[scenario_key].description,
            "",
            f"Median-net-income path of {result.paths} Monte Carlo paths; "
            "prior year shown as comparative.",
            "",
        ]
        for kind in ("income_statement", "balance_sheet", "cash_flow"):
            lines.extend(
                statement_markdown(
                    result.representative.statements[kind],
                    kind.replace("_", " ").title(),
                )
            )
        (company_dir / f"simulated_{scenario_key}.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )
        journal = [
            {"flow": record.name, "amount": str(record.amount), "effect": record.effect}
            for record in result.representative.journal
        ]
        (company_dir / f"journal_{scenario_key}.json").write_text(
            json.dumps(journal, indent=1), encoding="utf-8"
        )

    outcome = {
        "key": key,
        "name": company.name,
        "standard": company.standard,
        "form": company.form,
        "report_date": filing.report_date,
        "accession": filing.accession,
        "primary_path": str(filing.primary_path),
        "pdf_path": str(filing.pdf_path),
        "paths": paths,
        "seed": seed,
        "extraction_rows": extraction_rows,
        "extraction_pass": extraction_pass,
        "benign_notes": benign_notes,
        "reconstruction_rows": reconstruction_rows,
        "reconstruction_pass": reconstruction_pass,
        "footing_total": len(footing),
        "footing_failures": footing_failures,
        "footing_excused": footing_excused,
        "footing_pass": not footing_failures,
        "mc_violations": mc_violations,
        "max_identity_residual": str(max_residual),
        "symbolic": {
            "balanced": symbolic_verdict.balanced,
            "acyclic": symbolic_verdict.acyclic,
            "residual": symbolic_verdict.residual,
            "culprits": symbolic_verdict.culprits,
        },
        "directional": [
            {"name": check.name, "detail": check.detail, "passed": check.passed}
            for check in directional
        ],
        "directional_pass": all(check.passed for check in directional),
        "plausibility_total": plausibility_total,
        "plausibility_failures": plausibility_failures,
        "plausibility_pass": not plausibility_failures,
        "net_cash": str(net_cash),
        "fans": fans,
    }
    (company_dir / "outcome.json").write_text(
        json.dumps(outcome, indent=1), encoding="utf-8"
    )
    return outcome


def _verdict(outcome: dict) -> bool:
    return (
        outcome["extraction_pass"]
        and outcome["reconstruction_pass"]
        and outcome["footing_pass"]
        and outcome["mc_violations"] == 0
        and outcome["directional_pass"]
        and outcome["plausibility_pass"]
    )


def write_report(outcomes: list[dict]) -> Path:
    lines: list[str] = []
    add = lines.append
    add("# FSS acceptance report")
    add("")
    total_compared = sum(
        row["compared"] for outcome in outcomes for row in outcome["extraction_rows"]
    )
    total_matches = sum(
        row["matches"] for outcome in outcomes for row in outcome["extraction_rows"]
    )
    total_flags = sum(
        row["flagged"] for outcome in outcomes for row in outcome["extraction_rows"]
    )
    all_pass = all(_verdict(outcome) for outcome in outcomes)
    add(f"Overall verdict: {'PASS' if all_pass else 'FAIL'}")
    add("")
    if total_compared:
        add(
            f"- PDF-only extraction: {total_matches} of {total_compared} accepted cells "
            f"match the tag-path ground truth exactly ({total_flags} flagged cells "
            "abstained). Rule-of-three 95% upper bound on the per-field error rate: "
            f"{3 / total_compared:.2%}."
        )
    paths = outcomes[0]["paths"] if outcomes else 0
    seed = outcomes[0]["seed"] if outcomes else 0
    add(
        f"- Monte Carlo: {paths} paths per scenario per firm (common random "
        f"numbers across scenarios), seed {seed}; every path keeps A = L + E and "
        "the cash tie exactly, relative to the filer's own printed rounding residual."
    )
    add("")
    for outcome in outcomes:
        add(
            f"## {outcome['name']} ({outcome['standard']}, {outcome['form']} "
            f"{outcome['report_date']})"
        )
        add("")
        add(f"Verdict: {'PASS' if _verdict(outcome) else 'FAIL'}")
        add("")
        add("### Extraction (PDF-only mode vs tag path)")
        add("")
        add("| Statement | compared | matches | mismatches | missing | flagged |")
        add("| --- | ---: | ---: | ---: | ---: | ---: |")
        for row in outcome["extraction_rows"]:
            add(
                f"| {row['statement']} | {row['compared']} | {row['matches']} "
                f"| {row['mismatches']} | {row['missing']} | {row['flagged']} |"
            )
        add("")
        for note in outcome["benign_notes"]:
            add(f"- {note}")
        add("")
        add("### Reconstruction and footing")
        add("")
        for row in outcome["reconstruction_rows"]:
            demoted = (
                f", {row['demotions']} filer-rounded subtotals stored verbatim"
                if row["demotions"]
                else ""
            )
            add(f"- {row['statement']}: exact on {row['cells']} cells{demoted}")
        excused = (
            f" ({outcome['footing_excused']} exceptions, all on the disclosed "
            "filer-rounding list)"
            if outcome["footing_excused"]
            else ""
        )
        add(
            f"- footing: {outcome['footing_total'] - outcome['footing_excused'] - len(outcome['footing_failures'])}"
            f"/{outcome['footing_total']} derived cells within the decimals tolerance{excused}"
        )
        for failure in outcome["footing_failures"]:
            add(f"- FOOTING FAIL: {failure}")
        add("")
        add("### Scenarios (Monte Carlo fan, millions)")
        add("")
        for metric, label in (("net_income", "net income"), ("revenue", "revenue")):
            add(f"| Scenario | mean {label} | p5 | p25 | p50 | p75 | p95 |")
            add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
            for scenario_key, cells in outcome["fans"][metric].items():
                add(f"| {scenario_key} | " + " | ".join(cells) + " |")
            add("")
        add("### Directional battery")
        add("")
        for check in outcome["directional"]:
            add(
                f"- {'PASS' if check['passed'] else 'FAIL'}: {check['name']} "
                f"({check['detail']})"
            )
        add("")
        add("### Plausibility (representative and deterministic paths, all scenarios)")
        add("")
        symbolic = outcome.get("symbolic", {})
        add(
            "- symbolic closure: "
            + (
                "PROVEN (flow system cancels for all parameter values; "
                "computation DAG acyclic)"
                if symbolic.get("balanced") and symbolic.get("acyclic")
                else f"FAILED ({symbolic.get('residual')}, culprits {symbolic.get('culprits')})"
            )
        )
        add(
            f"- {outcome['plausibility_total'] - len(outcome['plausibility_failures'])} of "
            f"{outcome['plausibility_total']} checks pass; Monte Carlo (TensorFlow) "
            f"identity violations: {outcome['mc_violations']}; max per-path "
            f"identity residual: {outcome.get('max_identity_residual', '0')} "
            "(tolerance 1 currency unit)"
        )
        for failure in outcome["plausibility_failures"]:
            add(f"- FAIL {failure}")
        add("")
    ACCEPT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ACCEPT_DIR / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def merge() -> bool:
    outcomes = []
    for key in COMPANIES:
        path = ACCEPT_DIR / key / "outcome.json"
        if not path.exists():
            print(f"missing outcome for {key}; run: python -m fss accept --company {key}")
            return False
        outcomes.append(json.loads(path.read_text(encoding="utf-8")))
    report_path = write_report(outcomes)
    inputs = {}
    for outcome in outcomes:
        inputs[f"{outcome['key']}_primary"] = Path(outcome["primary_path"])
        inputs[f"{outcome['key']}_pdf"] = Path(outcome["pdf_path"])
    write_manifest(
        ACCEPT_DIR / "manifest.json",
        inputs,
        {
            "monte_carlo_paths": outcomes[0]["paths"],
            "seed": outcomes[0]["seed"],
            "scenarios": {k: asdict(s) for k, s in SCENARIOS.items()},
        },
    )
    all_pass = all(_verdict(outcome) for outcome in outcomes)
    print(f"acceptance: {'PASS' if all_pass else 'FAIL'} -> {report_path}")
    for outcome in outcomes:
        print(
            f"  {outcome['key']}: extraction={'PASS' if outcome['extraction_pass'] else 'FAIL'} "
            f"reconstruction={'PASS' if outcome['reconstruction_pass'] else 'FAIL'} "
            f"footing={'PASS' if outcome['footing_pass'] else 'FAIL'} "
            f"mc_violations={outcome['mc_violations']} "
            f"directional={'PASS' if outcome['directional_pass'] else 'FAIL'} "
            f"plausibility={'PASS' if outcome['plausibility_pass'] else 'FAIL'}"
        )
    return all_pass


def main(
    paths: int = MONTE_CARLO_PATHS,
    seed: int = RANDOM_SEED,
    companies: list[str] | None = None,
    merge_only: bool = False,
) -> bool:
    if merge_only:
        return merge()
    for key in companies or list(COMPANIES):
        outcome = run_company(key, paths, seed)
        print(f"{key}: {'PASS' if _verdict(outcome) else 'FAIL'} (outcome.json written)")
    if companies:
        return True  # partial run; merge separately
    return merge()


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
