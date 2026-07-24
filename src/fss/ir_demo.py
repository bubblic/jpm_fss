"""IR-editions-versus-tags preliminary validation: python -m fss.ir_demo.

Six untagged-sweep documents are true investor-relations annual reports
of filers whose same-fiscal-year filings are tagged on EDGAR. For each,
this demo replays the document deterministically from its committed
mapping artifact (runtime semantics: artifact pages and adjudications,
no model constructed), then scores the result against the filing's tag
path at two levels:

  - value level: every accepted cell against the tagged value the filer
    reported for the same label and year, with unmatched ground-truth
    rows kept visible rather than absorbed;
  - concept level: the artifact's label-to-concept choices against the
    concepts the filer's own presentation uses.

This extends the measured accuracy bar from same-document renders (the
PDF-only ablation of fss.measure) to genuinely foreign layouts. The
numbers are expected to be imperfect here: these are the hard documents,
and the report says exactly where and why. CIKs are asserted against the
submissions API's company name, never trusted from memory.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pdfplumber

from fss import edgar, tagread, xbrl
from fss.carry_demo import _score_mapping, _score_section
from fss.config import Company
from fss.paths import DATA_DIR, OUT_DIR
from fss.pdfread import locate
from fss.pdfread.assemble import read_statement_pages
from fss.reconcile import (
    AccuracyReport,
    ReconciledStatement,
    canon_label,
    compare_to_ground_truth,
    reconcile,
)
from fss.statements import StructuredStatement
from fss.untagged import (
    STATEMENTS,
    _apply_artifact_adjudications,
    _header_years,
    _sha256,
    load_artifact,
)

IR_DIR = OUT_DIR / "ir_validation"


@dataclass(frozen=True)
class Experiment:
    document: str
    company: Company
    name_token: str  # asserted against the submissions API company name
    period_prefix: str  # fiscal period end of the year the document covers


EXPERIMENTS = (
    Experiment(
        "2023_general_motors_annual_report",
        Company("gm", "General Motors Company", "0001467858", "10-K", "us-gaap"),
        "GENERAL MOTORS",
        "2023-12",
    ),
    Experiment(
        "exxon_2024",
        Company("exxon", "Exxon Mobil Corporation", "0000034088", "10-K", "us-gaap"),
        "EXXON",
        "2024-12",
    ),
    Experiment(
        "jpmorgan_2024",
        Company("jpm", "JPMorgan Chase & Co.", "0000019617", "10-K", "us-gaap"),
        "JPMORGAN",
        "2024-12",
    ),
    Experiment(
        "google_2024",
        Company("google", "Alphabet Inc.", "0001652044", "10-K", "us-gaap"),
        "ALPHABET",
        "2024-12",
    ),
    Experiment(
        "svb_ar2022",
        Company("svb", "SVB Financial Group", "0000719739", "10-K", "us-gaap"),
        "SVB",
        "2022-12",
    ),
    Experiment(
        "bbby_ar2022",
        Company("bbby", "Bed Bath & Beyond Inc.", "0000886158", "10-K", "us-gaap"),
        "BED BATH",
        "2023-02",
    ),
)


def _acquire(experiment: Experiment) -> edgar.Filing:
    filing = edgar.annual_by_period(experiment.company, experiment.period_prefix)
    submissions = json.loads(
        (DATA_DIR / f"submissions_CIK{experiment.company.cik}.json").read_text(
            encoding="utf-8"
        )
    )
    # a bankruptcy estate renames the registrant (Bed Bath & Beyond's CIK
    # now answers as its post-bankruptcy shell), so identity is asserted
    # against the current name and every former name the CIK carries
    names = [str(submissions.get("name", ""))] + [
        str(former.get("name", "")) for former in submissions.get("formerNames", [])
    ]
    if not any(experiment.name_token.lower() in name.lower() for name in names):
        sys.exit(
            f"{experiment.document}: CIK {experiment.company.cik} resolves to "
            f"{names!r}, not {experiment.name_token!r}; refusing to score "
            "against the wrong company"
        )
    print(
        f"{experiment.document}: {names[0]} {experiment.company.form} "
        f"period {filing.report_date}, accession {filing.accession}"
    )
    edgar.fetch_filing_files(filing)
    edgar.warm_arelle_cache(filing)
    return filing


def _replay(
    experiment: Experiment, artifact: dict[str, Any]
) -> dict[str, tuple[ReconciledStatement, Any]]:
    """The runtime read path: artifact pages and adjudications, no model."""
    pdf_path = Path(str(artifact["source_file"]))
    if _sha256(pdf_path) != artifact.get("source_sha256"):
        sys.exit(f"{experiment.document}: source hash drifted; re-onboarding required")
    replayed: dict[str, tuple[ReconciledStatement, Any]] = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        text_options = locate.probe_text_options(pdf)
        pages = locate.scan_pages(pdf, text_options)
        for kind in STATEMENTS:
            stmt_artifact = artifact.get("statements", {}).get(kind)
            if not stmt_artifact or not stmt_artifact.get("pages"):
                continue
            page_indices = [p - 1 for p in stmt_artifact["pages"]]
            extraction = read_statement_pages(
                pdf, pdf_path, kind, page_indices, pages, text_options
            )
            reconciled = reconcile(extraction)
            if reconciled.flags:
                _apply_artifact_adjudications(
                    reconciled, stmt_artifact.get("adjudications", [])
                )
            reconciled.flags = [p for p in reconciled.flags if p.rule == "flagged"]
            replayed[kind] = (reconciled, extraction)
    return replayed


def _column_year(column_id: str) -> int | None:
    found = re.search(r"(\d{4})-\d{2}-\d{2}$", column_id)
    return int(found.group(1)) if found else None


def _reorder_columns(
    statement: StructuredStatement, year_order: list[int]
) -> StructuredStatement | None:
    """Reorder ground-truth columns to the document's own year order.

    The comparator aligns columns positionally, and IR documents disagree
    with filings on column order (Alphabet prints the prior year first),
    so the ground truth is permuted to match. Comparison stops at the
    first document year the filing does not carry."""
    gt_years = [_column_year(column) for column in statement.columns]
    permutation: list[int] = []
    for year in year_order:
        if year in gt_years:
            permutation.append(gt_years.index(year))
        else:
            break
    if not permutation:
        return None
    columns = tuple(statement.columns[i] for i in permutation)
    rows = [
        replace(row, cells=tuple(row.cells[i] for i in permutation))
        for row in statement.rows
    ]
    return replace(statement, columns=columns, rows=rows)


def _concept_truth(
    statements: dict[str, StructuredStatement]
) -> dict[str, dict[str, set[str]]]:
    truth: dict[str, dict[str, set[str]]] = {}
    for kind, statement in statements.items():
        labels: dict[str, set[str]] = {}
        for row in statement.rows:
            if row.kind == "abstract":
                continue
            key = canon_label(row.label)
            if key:
                labels.setdefault(key, set()).add(row.concept)
        truth[kind] = labels
    return truth


def _bucket_unmatched(entries: list[tuple[str, str, str]]) -> dict[str, int]:
    buckets = {"derived (unprinted subtotal)": 0, "share counts": 0, "leaf, not extracted": 0}
    for _label, kind, unit in entries:
        if kind == "derived":
            buckets["derived (unprinted subtotal)"] += 1
        elif "share" in (unit or "").lower():
            buckets["share counts"] += 1
        else:
            buckets["leaf, not extracted"] += 1
    return buckets


def _value_section(
    document: str, reports: dict[str, AccuracyReport | str]
) -> list[str]:
    lines = [
        "| Statement | compared | match | mismatch | missing | flagged | gt unmatched |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    examples: list[str] = []
    for kind in STATEMENTS:
        outcome = reports.get(kind)
        if outcome is None:
            lines.append(f"| {kind} | not onboarded | | | | | |")
            continue
        if isinstance(outcome, str):
            lines.append(f"| {kind} | {outcome} | | | | | |")
            continue
        lines.append(
            f"| {kind} | {outcome.compared} | {outcome.matches} "
            f"| {len(outcome.mismatches)} | {len(outcome.missing)} "
            f"| {outcome.flagged_cells} | {len(outcome.gt_rows_unmatched)} |"
        )
        for miss in outcome.mismatches[:4]:
            examples.append(
                f"- {kind} mismatch, '{miss.label[:60]}' column {miss.column}: "
                f"filing {miss.ground_truth}, document read {miss.pdf}"
            )
        buckets = _bucket_unmatched(outcome.gt_rows_unmatched)
        summary = ", ".join(f"{v} {k}" for k, v in buckets.items() if v)
        if summary:
            examples.append(f"- {kind} ground-truth rows unmatched: {summary}")
    return lines + ([""] + examples if examples else [])


def _run_experiment(experiment: Experiment) -> tuple[list[str], dict[str, int]]:
    filing = _acquire(experiment)
    artifact = load_artifact(experiment.document)
    if artifact is None:
        sys.exit(f"{experiment.document}: no committed mapping artifact")
    replayed = _replay(experiment, artifact)
    model = xbrl.load_model(filing.primary_path)
    ground_truth = tagread.extract_all(
        model, experiment.company.key, experiment.company.standard
    )
    model.close()
    reports: dict[str, AccuracyReport | str] = {}
    totals = {"compared": 0, "matches": 0, "mismatches": 0, "missing": 0}
    for kind, (reconciled, extraction) in replayed.items():
        statement = ground_truth.get(kind)
        if statement is None:
            reports[kind] = "no tagged statement found"
            continue
        year_order = _header_years(extraction)
        reordered = _reorder_columns(statement, year_order) if year_order else None
        if reordered is None:
            reports[kind] = "document years not in the filing"
            continue
        report = compare_to_ground_truth(experiment.document, reconciled, reordered)
        reports[kind] = report
        totals["compared"] += report.compared
        totals["matches"] += report.matches
        totals["mismatches"] += len(report.mismatches)
        totals["missing"] += len(report.missing)
    lines = [
        f"## {experiment.document}",
        "",
        f"{experiment.company.name} {experiment.company.form}, accession "
        f"{filing.accession}, period {filing.report_date}; document replayed "
        "deterministically from its committed artifact (no model constructed).",
        "",
    ]
    lines += _value_section(experiment.document, reports)
    lines.append("")
    lines += _score_section(
        "Concept choices vs the filer's tags", _score_mapping(artifact, _concept_truth(ground_truth))
    )
    return lines, totals


def main() -> None:
    IR_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Investor-relations editions scored against their filings' tags",
        "",
        "Six untagged-sweep documents are true IR annual reports of filers "
        "whose same-fiscal-year filings are tagged on EDGAR. Each document "
        "is replayed deterministically from its committed mapping artifact "
        "and scored against the filing's tag path: accepted cell values "
        "against tagged values (aligned by label and fiscal year), and "
        "label-to-concept choices against the filer's own presentation.",
        "",
    ]
    grand = {"compared": 0, "matches": 0, "mismatches": 0, "missing": 0}
    for experiment in EXPERIMENTS:
        # per-document sections cache so the run resumes rather than
        # repeating completed acquisitions and replays
        part = IR_DIR / f"section_{experiment.document}.json"
        if part.exists():
            saved = json.loads(part.read_text(encoding="utf-8"))
            section, totals = saved["lines"], saved["totals"]
            print(f"{experiment.document}: reusing completed section")
        else:
            section, totals = _run_experiment(experiment)
            part.write_text(
                json.dumps({"lines": section, "totals": totals}, indent=0),
                encoding="utf-8",
            )
        lines += section
        for key in grand:
            grand[key] += totals[key]
    lines += [
        "## Totals",
        "",
        f"Accepted cells compared {grand['compared']}, matching the filing "
        f"exactly {grand['matches']}, mismatching {grand['mismatches']}, "
        f"missing from the document read {grand['missing']}.",
        "",
    ]
    report = IR_DIR / "report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"report -> {report}")
    print(
        f"TOTAL: compared {grand['compared']} matches {grand['matches']} "
        f"mismatches {grand['mismatches']} missing {grand['missing']}"
    )


if __name__ == "__main__":
    main()
