"""Measure PDF-only extraction accuracy against the tag-path ground truth.

Entry point: python -m fss.measure [company ...]

This is the PDF-only ablation from the proposal: the tag path contributes
nothing to the PDF readers; it serves only as the reference the accepted
values are scored against.
"""
from __future__ import annotations

import sys

from fss.config import COMPANIES
from fss.edgar import latest_annual
from fss.paths import DATA_DIR
from fss.pdfread.assemble import extract_pdf_statements
from fss.reconcile import AccuracyReport, compare_to_ground_truth, reconcile
from fss.statements import StructuredStatement


def measure_company(key: str, verbose: bool = True) -> list[AccuracyReport]:
    company = COMPANIES[key]
    filing = latest_annual(company)
    extractions = extract_pdf_statements(filing.pdf_path)
    reports: list[AccuracyReport] = []
    for statement, extraction in extractions.items():
        reconciled = reconcile(extraction)
        ground_truth = StructuredStatement.load(
            DATA_DIR / "extracted" / f"{key}_{statement}.json"
        )
        report = compare_to_ground_truth(key, reconciled, ground_truth)
        reports.append(report)
        if verbose:
            print(
                f"{key}/{statement}: pages {extraction.pages} "
                f"scale {extraction.scale.statement_scale:,} "
                f"cols {reconciled.n_columns} | compared {report.compared} "
                f"matches {report.matches} mismatches {len(report.mismatches)} "
                f"missing {len(report.missing)} flagged {report.flagged_cells}"
            )
            for miss in report.mismatches[:8]:
                print(
                    f"    MISMATCH col{miss.column} {miss.label[:60]!r}: "
                    f"gt={miss.ground_truth} pdf={miss.pdf}"
                )
            for miss in report.missing[:6]:
                print(f"    missing col{miss.column} {miss.label[:60]!r}: gt={miss.ground_truth}")
            if report.gt_rows_unmatched:
                print(
                    "    gt rows unmatched: "
                    f"{[(label[:40], kind) for label, kind, _ in report.gt_rows_unmatched]}"
                )
            if report.pdf_rows_unmatched:
                print(f"    pdf rows unmatched: {[l[:48] for l in report.pdf_rows_unmatched]}")
    return reports


def main() -> None:
    keys = sys.argv[1:] or list(COMPANIES)
    totals = {"compared": 0, "matches": 0, "mismatches": 0, "missing": 0, "flagged": 0}
    for key in keys:
        for report in measure_company(key):
            totals["compared"] += report.compared
            totals["matches"] += report.matches
            totals["mismatches"] += len(report.mismatches)
            totals["missing"] += len(report.missing)
            totals["flagged"] += report.flagged_cells
    print(
        f"TOTAL: compared {totals['compared']} matches {totals['matches']} "
        f"mismatches {totals['mismatches']} missing {totals['missing']} "
        f"flagged {totals['flagged']}"
    )


if __name__ == "__main__":
    main()
