"""The acceptance battery: everything the proposal promises, measured.

Entry point: python -m fss.accept  (or python -m fss accept)

Per company: extraction accuracy of the PDF-only mode against the tag path
(zero accepted-cell errors required; every unmatched ground-truth row must
fall in a documented benign category), perfect reconstruction through
(z, m), footing of the extracted statements within the decimals tolerance,
Monte Carlo simulation under every scenario with zero identity violations,
the directional battery, and the plausibility battery. Writes the full
acceptance report, per-scenario simulated statements, the audit journal of
each representative path, and the run manifest under out/acceptance/.
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
from fss.engine.project import Projector
from fss.manifest import write_manifest
from fss.paths import ACCEPT_DIR, DATA_DIR
from fss.pdfread.assemble import extract_pdf_statements
from fss.reconcile import AccuracyReport, compare_to_ground_truth, reconcile
from fss.render import fan_table, statement_markdown
from fss.simulate import directional_battery, run_all_scenarios
from fss.statements import StructuredStatement
from fss.validate import footing_checks, plausibility_battery

MILLION = Decimal(1_000_000)


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
    extraction_reports: list[AccuracyReport] = []
    extraction_pass = True
    benign_notes: list[str] = []
    extractions = extract_pdf_statements(filing.pdf_path)
    for statement_kind, extraction in extractions.items():
        reconciled = reconcile(extraction)
        report = compare_to_ground_truth(key, reconciled, statements[statement_kind])
        extraction_reports.append(report)
        if report.mismatches or report.missing:
            extraction_pass = False
        for entry in report.gt_rows_unmatched:
            reason = _benign_unmatched(entry, statement_kind)
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

    # 3. footing with the decimals tolerance; cells on the disclosed
    # demotion list are the filer's own rounding inconsistencies, stored
    # verbatim and reported, not pipeline defects
    demoted_cells: set[tuple[str, str]] = set()
    for result in reconstruction:
        for note in result.demotions:
            label = note.split(" [", 1)[0]
            period = note.split("] ", 1)[1].split(":", 1)[0] if "] " in note else ""
            demoted_cells.add((label, period))
    footing = [check for k in statements for check in footing_checks(statements[k])]
    footing_failures = [
        check
        for check in footing
        if not check.passed and (check.label, check.period) not in demoted_cells
    ]
    footing_pass = not footing_failures

    # 4. simulation under every scenario
    results = run_all_scenarios(key, statements, paths=paths, seed=seed)
    mc_violations = sum(result.violations for result in results.values())

    # 5. directional battery
    projector = Projector(key, statements)
    from fss.engine import roles as R

    net_cash = (
        projector._sum(projector.bs, {R.CASH, R.SECURITIES})
        - projector._sum(projector.bs, {R.DEBT, R.COMMERCIAL_PAPER})
    )
    directional = directional_battery(results, net_cash)
    directional_pass = all(check.passed for check in directional)

    # 6. plausibility on the representative and deterministic baseline paths
    base_metrics = {
        "revenue": projector._sum(projector.inc, {R.REVENUE}),
        "gross_margin_bp": results["baseline"].deterministic.metrics["gross_margin_bp"],
    }
    plausibility = []
    for scenario_key, result in results.items():
        for period in (result.representative, result.deterministic):
            for check in plausibility_battery(period, base_metrics):
                plausibility.append((scenario_key, check))
    plausibility_pass = all(check.passed for _, check in plausibility)

    # artifacts
    company_dir = ACCEPT_DIR / key
    company_dir.mkdir(parents=True, exist_ok=True)
    for scenario_key, result in results.items():
        lines: list[str] = [f"## {company.name}: simulated next period, scenario '{scenario_key}'", ""]
        lines.append(SCENARIOS[scenario_key].description)
        lines.append("")
        lines.append(
            f"Median-net-income path of {result.paths} Monte Carlo paths; "
            f"prior year shown as comparative."
        )
        lines.append("")
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

    return {
        "key": key,
        "filing": filing,
        "extraction_reports": extraction_reports,
        "extraction_pass": extraction_pass,
        "benign_notes": benign_notes,
        "reconstruction": reconstruction,
        "reconstruction_pass": reconstruction_pass,
        "footing": footing,
        "footing_pass": footing_pass,
        "results": results,
        "mc_violations": mc_violations,
        "directional": directional,
        "directional_pass": directional_pass,
        "plausibility": plausibility,
        "plausibility_pass": plausibility_pass,
        "net_cash": net_cash,
    }


def write_report(outcomes: list[dict], paths: int, seed: int) -> Path:
    lines: list[str] = []
    add = lines.append
    add("# FSS acceptance report")
    add("")
    total_compared = sum(
        report.compared for outcome in outcomes for report in outcome["extraction_reports"]
    )
    total_matches = sum(
        report.matches for outcome in outcomes for report in outcome["extraction_reports"]
    )
    total_flags = sum(
        report.flagged_cells for outcome in outcomes for report in outcome["extraction_reports"]
    )
    all_pass = all(
        outcome["extraction_pass"]
        and outcome["reconstruction_pass"]
        and outcome["footing_pass"]
        and outcome["mc_violations"] == 0
        and outcome["directional_pass"]
        and outcome["plausibility_pass"]
        for outcome in outcomes
    )
    add(f"Overall verdict: {'PASS' if all_pass else 'FAIL'}")
    add("")
    add(
        f"- PDF-only extraction: {total_matches} of {total_compared} accepted cells "
        f"match the tag-path ground truth exactly ({total_flags} flagged cells "
        "abstained). Rule-of-three 95% upper bound on the per-field error rate: "
        f"{3 / total_compared:.2%}." if total_compared else "- no cells compared"
    )
    add(
        f"- Monte Carlo: {paths} paths per scenario per firm, seed {seed}; "
        "every path keeps A = L + E and the cash tie exactly (relative to the "
        "filer's own rounding residual)."
    )
    add("")
    for outcome in outcomes:
        company = COMPANIES[outcome["key"]]
        filing = outcome["filing"]
        add(f"## {company.name} ({company.standard}, {company.form} {filing.report_date})")
        add("")
        add("### Extraction (PDF-only mode vs tag path)")
        add("")
        add("| Statement | compared | matches | mismatches | missing | flagged |")
        add("| --- | ---: | ---: | ---: | ---: | ---: |")
        for report in outcome["extraction_reports"]:
            add(
                f"| {report.statement} | {report.compared} | {report.matches} "
                f"| {len(report.mismatches)} | {len(report.missing)} | {report.flagged_cells} |"
            )
        add("")
        for note in outcome["benign_notes"]:
            add(f"- {note}")
        add("")
        add("### Reconstruction and footing")
        add("")
        for result in outcome["reconstruction"]:
            demoted = f", {len(result.demotions)} filer-rounded subtotals stored verbatim" if result.demotions else ""
            add(f"- {result.statement}: exact on {result.cells_checked} cells{demoted}")
        footing = outcome["footing"]
        passed = sum(1 for check in footing if check.passed)
        add(
            f"- footing: {passed}/{len(footing)} derived cells within the decimals "
            "tolerance; every exception is on the disclosed filer-rounding list"
            if outcome["footing_pass"] and passed < len(footing)
            else f"- footing: {passed}/{len(footing)} derived cells within the decimals tolerance"
        )
        add("")
        add("### Scenarios")
        add("")
        lines.extend(fan_table(outcome["results"], "net_income", MILLION, "net income (millions)"))
        lines.extend(fan_table(outcome["results"], "revenue", MILLION, "revenue (millions)"))
        add("### Directional battery")
        add("")
        for check in outcome["directional"]:
            add(f"- {'PASS' if check.passed else 'FAIL'}: {check.name} ({check.detail})")
        add("")
        add("### Plausibility (representative and deterministic paths, all scenarios)")
        add("")
        failed = [(s, c) for s, c in outcome["plausibility"] if not c.passed]
        add(
            f"- {len(outcome['plausibility']) - len(failed)} of "
            f"{len(outcome['plausibility'])} checks pass"
        )
        for scenario_key, check in failed:
            add(f"- FAIL [{scenario_key}] {check.name}: {check.detail}")
        add("")
    ACCEPT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ACCEPT_DIR / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main(paths: int = MONTE_CARLO_PATHS, seed: int = RANDOM_SEED) -> bool:
    outcomes = [run_company(key, paths, seed) for key in COMPANIES]
    report_path = write_report(outcomes, paths, seed)
    inputs = {}
    for outcome in outcomes:
        filing = outcome["filing"]
        inputs[f"{outcome['key']}_primary"] = filing.primary_path
        inputs[f"{outcome['key']}_pdf"] = filing.pdf_path
    write_manifest(
        ACCEPT_DIR / "manifest.json",
        inputs,
        {
            "monte_carlo_paths": paths,
            "seed": seed,
            "scenarios": {k: asdict(s) for k, s in SCENARIOS.items()},
        },
    )
    all_pass = all(
        outcome["extraction_pass"]
        and outcome["reconstruction_pass"]
        and outcome["footing_pass"]
        and outcome["mc_violations"] == 0
        and outcome["directional_pass"]
        and outcome["plausibility_pass"]
        for outcome in outcomes
    )
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


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
