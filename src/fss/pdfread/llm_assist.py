"""LLM-assisted stages for untagged documents, on the user's calling logic.

Four narrowly-scoped, gated uses (the LLM never has sole authority):

  1. Page identification fallback: when the deterministic locator finds no
     pages for a statement, page batches go to the LLM with the user's
     ``{"pages": [...]}`` prompt shape (previous_llm_extractor's
     page_identifier pattern).
  2. Flagged-cell adjudication: for cells the reader gate abstained on,
     the LLM reads the located pages (median vote across n runs, the
     user's hallucination control) and a flagged cell is accepted only
     when the LLM's voted value exactly matches one of the deterministic
     readers. Disagreement stays flagged.
  3. Concept mapping assist: for face rows the lexical dictionary cannot
     map, the LLM chooses among a lexically retrieved shortlist of
     taxonomy concepts; the choice is accepted only if the concept's
     balance polarity is consistent with the row's printed sign and
     section. Unresolvable rows stay unmapped, per the abstain rule.
  4. Reporting-standard fallback: when the deterministic declaration scan
     (fss.standards) abstains, the LLM reads the declaration-bearing
     pages and proposes the framework; the proposal is recorded in the
     artifact for sign-off, and anything outside us-gaap/ifrs refuses.

Every call, prompt digest, vote, and decision lands in the audit record.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from fss.llm import LLMClient, extract_json_from_text, median_vote

PAGE_PROMPT = (
    "You are given multiple pages from an annual report. "
    "Identify which pages contain the table for the requested query. "
    'Return ONLY JSON in the shape: {{"pages": [<page_number>, ...]}}. '
    "Include all pages that contain the table or line items. "
    'If none, return {{"pages": []}}.\n\n'
    "Query: {query}\n\n"
    "Pages:\n{pages}"
)

CELL_PROMPT = (
    "You are a financial statement extraction engine.\n"
    "From the statement pages below, report the value of one table cell.\n"
    'Return ONLY JSON: {{"value": <number or null>}}.\n'
    "Rules: numbers exactly as printed but without thousands separators, "
    "currency symbols, or footnote marks; numbers in parentheses are "
    "negative; a dash means null; column {column} counts value columns "
    "left to right starting at 1 (ignore note-reference columns).\n\n"
    "Row label: {label}\n"
    "Column: {column}\n\n"
    "Pages:\n{pages}"
)

CONCEPT_PROMPT = (
    "You map financial statement line items to accounting taxonomy concepts.\n"
    "Choose the single best concept name for the line item, or null if none fits.\n"
    'Return ONLY JSON: {{"concept": "<name from the candidate list or null>"}}.\n\n'
    "Statement: {statement}\n"
    "Section: {section}\n"
    "Line item label: {label}\n"
    "Candidate concepts:\n{candidates}\n"
)

STANDARD_PROMPT = (
    "You identify the accounting framework an annual report's financial "
    "statements are prepared under, from the auditor's opinion or the "
    "basis-of-preparation note in the pages below.\n"
    'Return ONLY JSON: {{"standard": "us-gaap" | "ifrs" | "other" | null}}.\n'
    "Rules: us-gaap means United States GAAP. ifrs means IFRS, including "
    "IFRS as adopted by the EU or the UK. other means a different national "
    "framework (Hong Kong FRS alone, Japanese GAAP, Ind AS, PRC standards, "
    "and similar). null means these pages do not say.\n\n"
    "Pages:\n{pages}"
)


@dataclass
class LLMAudit:
    calls: int = 0
    decisions: list[dict[str, Any]] = field(default_factory=list)

    def record(self, kind: str, detail: dict[str, Any]) -> None:
        self.decisions.append({"kind": kind, **detail})


def _page_blocks(pages: dict[int, str]) -> str:
    blocks = [f"Page {number}:\n{(text or '').strip()}" for number, text in sorted(pages.items())]
    return "\n\n---\n\n".join(blocks)


def select_pages(
    client: LLMClient,
    audit: LLMAudit,
    pages: dict[int, str],
    query: str,
    batch_size: int = 25,
) -> list[int]:
    """The user's batched page-identification pattern."""
    valid = sorted(pages)
    selected: set[int] = set()
    for start in range(0, len(valid), batch_size):
        batch = {n: pages[n] for n in valid[start : start + batch_size]}
        prompt = PAGE_PROMPT.format(query=query, pages=_page_blocks(batch))
        audit.calls += 1
        print(
            f"    llm select_pages [{query[:30]}] batch {start // batch_size + 1} "
            f"({len(batch)} pages)...",
            flush=True,
        )
        response = client.ask_json(
            message="gen-ai-response", prompt=prompt, parameters={}, reasoning=False
        )
        if "raw_response" in response:
            embedded = extract_json_from_text(str(response["raw_response"]))
            if embedded:
                response = embedded
        raw = response.get("pages") or response.get("page_numbers") or []
        for item in raw if isinstance(raw, list) else []:
            try:
                number = int(item)
            except (TypeError, ValueError):
                continue
            if number in batch:
                selected.add(number)
    audit.record("select_pages", {"query": query[:60], "pages": sorted(selected)})
    return sorted(selected)


def _parse_value(raw: Any) -> Decimal | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


def read_cell(
    client: LLMClient,
    audit: LLMAudit,
    pages_text: str,
    label: str,
    column: int,
    runs: int = 3,
) -> Decimal | None:
    """Median-voted LLM reading of one cell (the hallucination control)."""
    samples: list[Decimal | None] = []
    print(f"    llm read_cell {label[:40]!r} col{column} x{runs}...", flush=True)
    for run in range(runs):
        audit.calls += 1
        response = client.ask_json(
            message="gen-ai-response",
            prompt=CELL_PROMPT.format(label=label, column=column, pages=pages_text),
            parameters={},
            reasoning=False,
        )
        if "raw_response" in response:
            embedded = extract_json_from_text(str(response["raw_response"]))
            if embedded:
                response = embedded
        samples.append(_parse_value(response.get("value")))
    voted = median_vote(samples, runs)
    audit.record(
        "read_cell",
        {
            "label": label[:60],
            "column": column,
            "samples": [str(s) for s in samples],
            "voted": str(voted.value),
            "agreement": voted.agreement,
        },
    )
    return voted.value


def _label_window(pages_text: str, label: str, radius: int = 18) -> str:
    """The lines around the row's occurrence: a small, targeted prompt is
    faster, cheaper, and harder to distract than whole statement pages."""
    lines = pages_text.splitlines()
    needle = "".join(label.lower().split())[:40]
    for index, line in enumerate(lines):
        if needle and needle in "".join(line.lower().split()):
            start = max(0, index - radius)
            return "\n".join(lines[start : index + radius])
    return pages_text[:6000]


def adjudicate_flags(
    client: LLMClient,
    audit: LLMAudit,
    reconciled,
    pages_text: str,
    runs: int = 3,
    max_cells: int = 12,
) -> int:
    """Second-look at flagged cells; accept only LLM-and-reader agreement.

    Returns the number of flags resolved. The LLM's voted value must equal
    one of the deterministic readers' raw readings exactly; a value nobody
    read stays flagged (the LLM cannot introduce numbers). At most
    ``max_cells`` flagged cells are adjudicated per statement (cost bound);
    the remainder stay flagged for human review.
    """
    resolved = 0
    attempted = 0
    for row in reconciled.rows:
        if not re.search(r"[A-Za-z]{3}|[一-鿿]{2}", row.label):
            continue  # numeric/blank pseudo-labels are not line items
        for column, prov in enumerate(row.provenance):
            if prov.rule != "flagged":
                continue
            if attempted >= max_cells:
                audit.record(
                    "adjudication_capped",
                    {"max_cells": max_cells, "note": "remaining flags left for review"},
                )
                return resolved
            attempted += 1
            context = _label_window(pages_text, row.label)
            voted = read_cell(client, audit, context, row.label, column + 1, runs)
            if voted is None:
                continue
            reader_values = set()
            for reading in prov.readings.values():
                parsed = _parse_value(reading.replace(",", "")) if reading else None
                if parsed is not None:
                    reader_values.add(parsed)
            if voted in reader_values:
                prov.accepted_printed = voted
                prov.rule = "llm_adjudicated"
                row.printed[column] = voted
                row.values[column] = voted * row.scale
                resolved += 1
                audit.record(
                    "adjudicated",
                    {"label": row.label[:60], "column": column, "value": str(voted)},
                )
    return resolved


def detect_standard(
    client: LLMClient,
    audit: LLMAudit,
    pages: dict[int, str],
) -> str | None:
    """One leashed call when the deterministic standard scan abstains.

    The model reads only the declaration-bearing candidate pages
    (fss.standards.declaration_candidates) and proposes us-gaap, ifrs,
    other, or null. The proposal never acts silently: it is recorded in
    the audit log and the mapping artifact, where sign-off confirms it,
    and "other" makes the pipeline refuse the document rather than map
    it as if covered.
    """
    audit.calls += 1
    print(f"    llm detect_standard ({len(pages)} candidate pages)...", flush=True)
    response = client.ask_json(
        message="gen-ai-response",
        prompt=STANDARD_PROMPT.format(pages=_page_blocks(pages)),
        parameters={},
        reasoning=False,
    )
    if "raw_response" in response:
        embedded = extract_json_from_text(str(response["raw_response"]))
        if embedded:
            response = embedded
    raw = response.get("standard")
    verdict: str | None = None
    if isinstance(raw, str):
        cleaned = raw.strip().lower().replace("_", "-").replace(" ", "-")
        if cleaned in ("us-gaap", "usgaap"):
            verdict = "us-gaap"
        elif cleaned == "ifrs":
            verdict = "ifrs"
        elif cleaned == "other":
            verdict = "other"
    audit.record("detect_standard", {"pages": sorted(pages), "verdict": verdict})
    return verdict


def map_concept(
    client: LLMClient,
    audit: LLMAudit,
    statement: str,
    section: str,
    label: str,
    candidates: list[str],
) -> str | None:
    """Choose a concept from a lexically retrieved shortlist, or abstain."""
    audit.calls += 1
    response = client.ask_json(
        message="gen-ai-response",
        prompt=CONCEPT_PROMPT.format(
            statement=statement,
            section=section or "(none)",
            label=label,
            candidates="\n".join(f"- {c}" for c in candidates),
        ),
        parameters={},
        reasoning=False,
    )
    if "raw_response" in response:
        embedded = extract_json_from_text(str(response["raw_response"]))
        if embedded:
            response = embedded
    concept = response.get("concept")
    chosen = concept if isinstance(concept, str) and concept in candidates else None
    audit.record("map_concept", {"label": label[:60], "chosen": chosen})
    return chosen
