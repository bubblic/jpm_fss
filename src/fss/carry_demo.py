"""Cross-year carry-forward demonstration: python -m fss.carry_demo.

For each experiment, onboard a firm's PRIOR-year annual report three ways
and score every mapping choice against the filer's own tags for that year:

  1. control onboard (no carry): the lexicon and, where configured, the
     model resolve the mapping from scratch;
  2. carried onboard (--carry-from <prior document>): the already-onboarded
     year's artifact seeds pages and label->concept choices, so the model
     is consulted only for rows neither the lexicon nor the prior artifact
     resolves;
  3. runtime replay from the carried artifact (no model constructed).

Two experiments bracket the mechanism:

  - microsoft_2024 carried from microsoft_2025: Microsoft is one of the
    four filers the lexicon is harvested from, so the lexicon already
    covers its labels and carry is expected to add little (the boundary
    case);
  - bbby_2021 carried from bbby_ar2022 (fiscal 2021, ended 2022-02-26,
    seeded from the fiscal-2022 report already onboarded in the untagged
    sweep): Bed Bath & Beyond is NOT a lexicon firm, so its firm-specific
    labels can resolve only from the prior artifact or the model (the
    payoff case).

Both prior-year filings are tagged on EDGAR, so the tag path supplies
concept ground truth. Products land under out/carry/, headlined by
out/carry/report.md. The run is resumable: acquisition caches under
data/, and a completed control onboard is reused rather than re-run.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fss import edgar, tagread, xbrl
from fss.config import COMPANIES, Company
from fss.paths import DATA_DIR, OUT_DIR
from fss.reconcile import canon_label
from fss.untagged import analyze_pdf, artifact_path, load_artifact

CARRY_DIR = OUT_DIR / "carry"
NOTE_REF = re.compile(r"\s+\(?\d{1,3}\)?$")
STATEMENTS = ("balance_sheet", "income_statement", "cash_flow")


@dataclass(frozen=True)
class Experiment:
    document: str  # slug for the prior-year PDF onboarded here
    company: Company
    period_prefix: str  # fiscal period end prefix of the year to onboard
    prior_document: str  # already-onboarded artifact that seeds it
    lexicon_firm: bool  # whether the firm is in the lexicon's harvest set


EXPERIMENTS = (
    Experiment(
        "microsoft_2024", COMPANIES["microsoft"], "2024-06", "microsoft_2025", True
    ),
    Experiment(
        "bbby_2021",
        Company("bbby", "Bed Bath & Beyond Inc.", "0000886158", "10-K", "us-gaap"),
        "2022-02",
        "bbby_ar2022",
        False,
    ),
)


def _acquire(experiment: Experiment) -> tuple[edgar.Filing, Path]:
    filing = edgar.annual_by_period(experiment.company, experiment.period_prefix)
    print(
        f"{experiment.company.key}: {experiment.company.form} filed "
        f"{filing.filing_date}, period {filing.report_date}, "
        f"accession {filing.accession}"
    )
    edgar.fetch_filing_files(filing)
    edgar.warm_arelle_cache(filing)
    edgar.render_pdf(filing)
    pdf_path = DATA_DIR / "carry" / f"{experiment.document}.pdf"
    if not pdf_path.exists():
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filing.pdf_path, pdf_path)
    return filing, pdf_path


def _ground_truth(
    filing: edgar.Filing, experiment: Experiment
) -> dict[str, dict[str, set[str]]]:
    """Tag-path label -> concept sets per statement, from the filer's own
    presentation of the onboarded year."""
    model = xbrl.load_model(filing.primary_path)
    statements = tagread.extract_all(
        model, experiment.company.key, experiment.company.standard
    )
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


def _score_mapping(
    artifact: dict[str, Any], truth: dict[str, dict[str, set[str]]]
) -> dict[str, Any]:
    """Score every mapping entry against the tag-path concepts for the
    same printed label: match / mismatch / off-face (label not on the
    tagged statement face, e.g. discovered section totals)."""
    scored: dict[str, Any] = {}
    for kind, stmt in artifact.get("statements", {}).items():
        gt = truth.get(kind, {})
        counts: dict[str, dict[str, int]] = {}
        mismatches: list[dict[str, str]] = []
        for entry in stmt.get("mapping", []):
            source = str(entry.get("source", "?"))
            bucket = counts.setdefault(
                source, {"match": 0, "mismatch": 0, "off_face": 0}
            )
            label = str(entry["label"])
            concepts = gt.get(canon_label(label)) or gt.get(
                canon_label(NOTE_REF.sub("", label))
            )
            if concepts is None:
                bucket["off_face"] += 1
            elif entry["concept"] in concepts:
                bucket["match"] += 1
            else:
                bucket["mismatch"] += 1
                mismatches.append(
                    {
                        "label": label,
                        "chosen": str(entry["concept"]),
                        "tagged": "|".join(sorted(concepts)),
                        "source": source,
                    }
                )
        scored[kind] = {"counts": counts, "mismatches": mismatches}
    return scored


def _mapping_line(outcome: dict[str, Any], kind: str, tag: str) -> str:
    record = outcome.get("statements", {}).get(kind, {})
    if "error" in record:
        return f"| {kind} ({tag}) | error: {record['error'][:60]} | | | | | | |"
    stats = record.get("mapping", {})
    return (
        f"| {kind} ({tag}) | {record.get('located_by', '?')} "
        f"| {record.get('rows', 0)} | {record.get('flags', 0)} "
        f"| {stats.get('lexical', 0)} | {stats.get('carried', 0)} "
        f"| {stats.get('llm', 0)} | {stats.get('unmapped', 0)} |"
    )


def _score_section(title: str, scored: dict[str, Any]) -> list[str]:
    lines = [f"#### {title}", ""]
    lines.append("| Statement | source | match | mismatch | off-face |")
    lines.append("| --- | --- | ---: | ---: | ---: |")
    for kind, result in scored.items():
        for source, bucket in sorted(result["counts"].items()):
            lines.append(
                f"| {kind} | {source} | {bucket['match']} "
                f"| {bucket['mismatch']} | {bucket['off_face']} |"
            )
    mismatches = [m for result in scored.values() for m in result["mismatches"]]
    if mismatches:
        lines.append("")
        lines.append("Mismatches:")
        for m in mismatches:
            lines.append(
                f"- [{m['source']}] '{m['label']}': chose {m['chosen']}, "
                f"filer tags {m['tagged']}"
            )
    lines.append("")
    return lines


def _carried_entries(artifact: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for kind, stmt in artifact.get("statements", {}).items():
        for entry in stmt.get("mapping", []):
            if entry.get("source") == "carried":
                lines.append(f"- {kind}: '{entry['label']}' -> {entry['concept']}")
    return lines


def _run_experiment(experiment: Experiment) -> dict[str, Any]:
    filing, pdf_path = _acquire(experiment)
    control_outcome_path = CARRY_DIR / f"control_outcome_{experiment.document}.json"
    control_artifact_path = CARRY_DIR / f"control_artifact_{experiment.document}.json"
    if control_outcome_path.exists():
        print(f"=== {experiment.document}: control onboard reused from cache")
        control = json.loads(control_outcome_path.read_text(encoding="utf-8"))
        control_artifact = json.loads(
            control_artifact_path.read_text(encoding="utf-8")
        )
    else:
        print(f"=== {experiment.document}: control onboard (no carry)")
        control = analyze_pdf(pdf_path, mode="onboard")
        control_artifact = load_artifact(experiment.document) or {}
        control_artifact_path.write_text(
            json.dumps(control_artifact, indent=1, default=str), encoding="utf-8"
        )
        control_outcome_path.write_text(
            json.dumps(control, indent=1, default=str), encoding="utf-8"
        )
    print(
        f"=== {experiment.document}: carried onboard "
        f"(--carry-from {experiment.prior_document})"
    )
    carried = analyze_pdf(
        pdf_path, mode="onboard", carry_from=experiment.prior_document
    )
    carried_artifact = load_artifact(experiment.document) or {}
    print(f"=== {experiment.document}: runtime replay from the carried artifact")
    replay = analyze_pdf(pdf_path, mode="runtime")
    print(f"=== {experiment.document}: scoring against the filer's tags")
    truth = _ground_truth(filing, experiment)
    return {
        "experiment": experiment,
        "filing": filing,
        "control": control,
        "carried": carried,
        "replay": replay,
        "control_score": _score_mapping(control_artifact, truth),
        "carried_score": _score_mapping(carried_artifact, truth),
        "carried_artifact": carried_artifact,
    }


def _experiment_section(result: dict[str, Any]) -> list[str]:
    experiment: Experiment = result["experiment"]
    filing: edgar.Filing = result["filing"]
    control, carried, replay = result["control"], result["carried"], result["replay"]
    provenance = result["carried_artifact"].get("carried_from", {})
    role = (
        "boundary case: a lexicon firm, so the lexicon should already cover it"
        if experiment.lexicon_firm
        else "payoff case: not a lexicon firm, so firm-specific labels resolve "
        "only from the prior artifact or the model"
    )
    lines = [
        f"## {experiment.document} carried from {experiment.prior_document}",
        "",
        f"{experiment.company.name} {experiment.company.form}, accession "
        f"{filing.accession}, filed {filing.filing_date}, period "
        f"{filing.report_date} (rendered from the EDGAR primary document). "
        f"Carried from {provenance.get('document', experiment.prior_document)} "
        f"(artifact sha {str(provenance.get('source_sha256', ''))[:16]}..., "
        f"sign-off: {provenance.get('approved_by', '?')}). This is the {role}.",
        "",
        "| Statement | located_by | rows | flags | lexical | carried | llm | unmapped |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for kind in STATEMENTS:
        lines.append(_mapping_line(control, kind, "control"))
        lines.append(_mapping_line(carried, kind, "carried"))
    lines += [
        "",
        f"LLM calls: control {control.get('llm_calls', 0)}, "
        f"carried {carried.get('llm_calls', 0)}. "
        f"Simulation: control {control.get('simulation', {}).get('status', '?')}, "
        f"carried {carried.get('simulation', {}).get('status', '?')}, "
        f"runtime replay {replay.get('simulation', {}).get('status', '?')} "
        f"(runtime model constructed: {replay.get('llm', False)}).",
        "",
        "### Concept accuracy against the filer's own tags",
        "",
    ]
    lines += _score_section("Control onboard", result["control_score"])
    lines += _score_section("Carried onboard", result["carried_score"])
    carried_list = _carried_entries(result["carried_artifact"])
    if carried_list:
        lines += ["### Entries resolved by carry", ""]
        lines += carried_list
        lines.append("")
    return lines


def main() -> None:
    CARRY_DIR.mkdir(parents=True, exist_ok=True)
    # legacy single-experiment cache names predate the two-experiment design
    for stale in ("control_outcome.json", "control_artifact.json"):
        (CARRY_DIR / stale).unlink(missing_ok=True)
    lines = [
        "# Cross-year carry-forward demonstration",
        "",
        "Each experiment onboards a firm's prior-year annual report with and "
        "without seeding from the already-onboarded year's mapping artifact, "
        "replays the carried artifact at runtime, and scores every mapping "
        "choice against the filer's own tags for the onboarded year.",
        "",
    ]
    for experiment in EXPERIMENTS:
        result = _run_experiment(experiment)
        lines += _experiment_section(result)
    report = CARRY_DIR / "report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"report -> {report}")


if __name__ == "__main__":
    main()
