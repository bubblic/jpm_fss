"""Untagged-PDF pipeline: arbitrary annual reports, no XBRL anywhere.

Entry point: python -m fss untagged [path ...]

For each PDF: locate the three core statements (deterministic locator,
LLM page-identification fallback when configured), extract through the
reader gate, adjudicate flagged cells with median-voted LLM readings when
configured, and validate what a tag-free document allows:

  - printed-subtotal footing (each total against the rows above it, with
    nesting), which doubles as the discovered calculation structure;
  - A = L + E from the printed totals;
  - the cash tie on the cash flow statement.

Rows then map to taxonomy concepts through the label dictionary harvested
from the tagged validation set (lexical first, LLM-over-shortlist second,
polarity-checked, abstain otherwise), and firms whose mapping supports the
driver roles are simulated through the same symbolic-verified TensorFlow
engine as the tagged set. Everything lands in a per-document report under
out/untagged/, plus a sweep summary.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pdfplumber

from fss import llm as llm_module
from fss.paths import DATA_DIR, OUT_DIR
from fss.pdfread import locate
from fss.pdfread.assemble import read_statement_pages
from fss.pdfread.llm_assist import LLMAudit, adjudicate_flags, map_concept, select_pages
from fss.reconcile import ReconciledStatement, canon_label, reconcile
from fss.statements import Cell, StatementRow, StructuredStatement

UNTAGGED_DIR = OUT_DIR / "untagged"
STATEMENTS = ("balance_sheet", "income_statement", "cash_flow")
TOTAL_PREFIX = re.compile(r"^(total|net total)\b", re.IGNORECASE)
CF_ACTIVITY_TOTAL = re.compile(
    r"^(net )?cash (flows? )?(provided by|used in|used for|from|generated)", re.IGNORECASE
)
CF_NET_CHANGE = re.compile(r"net (increase|decrease|change)", re.IGNORECASE)
CASH_ENDPOINT = re.compile(
    r"beginning|at january|start of|end of|at december|ending balance", re.IGNORECASE
)
YEAR = re.compile(r"\b(19|20)\d{2}\b")
# income-statement subtotal concepts: the cascade anchors
DERIVED_IS_LOCALS = {
    "GrossProfit",
    "OperatingIncomeLoss",
    "ProfitLossFromOperatingActivities",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    "ProfitLossBeforeTax",
    "NetIncomeLoss",
    "ProfitLoss",
    "ProfitLossFromContinuingOperations",
}


# ---------------------------------------------------------------------------
# label dictionary harvested from the tagged validation set
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConceptInfo:
    concept: str
    balance: str
    period_type: str
    is_monetary: bool


def _condensed(label: str) -> str:
    """Space-free matching key: loosely-set PDFs split letters inside words
    ("cas h equivalents"), which whitespace normalization cannot heal."""
    return re.sub(r"[^a-z0-9]", "", canon_label(label))


def _load_dictionary() -> tuple[dict[str, ConceptInfo], dict[str, set[str]]]:
    """label -> concept info (plain and condensed), plus a token index."""
    by_label: dict[str, ConceptInfo] = {}
    tokens: dict[str, set[str]] = {}
    for path in sorted((DATA_DIR / "extracted").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["rows"]:
            if row["kind"] == "abstract" or row["dims"]:
                continue
            info = ConceptInfo(
                row["concept"], row["balance"], row["period_type"], row["is_monetary"]
            )
            label = canon_label(row["label"])
            if label and label not in by_label:
                by_label[label] = info
            condensed = _condensed(row["label"])
            if condensed and condensed not in by_label:
                by_label[condensed] = info
            local = row["concept"].split(":", 1)[-1]
            words = {w.lower() for w in re.findall(r"[A-Z][a-z]+|[a-z]+", local)}
            words.update(label.split())
            tokens.setdefault(row["concept"], set()).update(words)
    return by_label, tokens


def _shortlist(label: str, tokens: dict[str, set[str]], top: int = 8) -> list[str]:
    words = set(canon_label(label).split())
    if not words:
        return []
    scored = sorted(
        (
            (len(words & concept_words) / len(words | concept_words), concept)
            for concept, concept_words in tokens.items()
        ),
        reverse=True,
    )
    return [concept for score, concept in scored[:top] if score > 0.15]


# ---------------------------------------------------------------------------
# validation without tags
# ---------------------------------------------------------------------------


@dataclass
class FootingGroup:
    total_index: int
    child_indices: list[int]
    child_weights: list[Decimal]
    columns_checked: int
    columns_passed: int
    method: str  # "group" | "cascade_plain" | "cascade_signed"


@dataclass
class UntaggedChecks:
    footing_groups: list[FootingGroup] = field(default_factory=list)
    footing_pass: bool = True
    identity_detail: str = "not found"
    identity_pass: bool | None = None
    cash_tie_detail: str = "not found"
    cash_tie_pass: bool | None = None


def _is_total_like(row, section: str, statement: str) -> bool:
    label = row.label.strip()
    if not label:
        return True
    if TOTAL_PREFIX.search(label):
        return True
    if statement == "cash_flow" and (
        CF_ACTIVITY_TOTAL.search(label) or CF_NET_CHANGE.search(label)
    ):
        return True
    return bool(section) and canon_label(label) == canon_label(section)


SUBTOTAL_LABELS = {
    "gross margin",
    "gross profit",
    "operating income",
    "operating profit",
    "operating income loss",
    "income before income taxes",
    "income before provision for income taxes",
    "profit before tax",
    "profit before income tax",
    "net income",
    "net income loss",
    "net earnings",
    "profit for the year",
    "profit after tax",
    "net revenues",
}


def _footing(
    reconciled: ReconciledStatement,
    statement: str,
    concepts: dict[int, "ConceptInfo"],
) -> list[FootingGroup]:
    """Printed-subtotal discovery with consumption semantics.

    A running stack holds the rows not yet explained by a verified total.
    Each candidate total tries child sets in order and keeps the first that
    verifies on every checkable column:

      1. its section run: the consecutive rows directly above that share
         its section header ("Total cost of revenue" = the cost rows, not
         the revenue block above them);
      2. the full stack, plain sum: nested totals ("Total assets" = the
         section totals plus loose rows);
      3. the full stack, polarity-signed: income-statement cascades
         ("Gross margin" = revenue minus costs), under either sign
         convention (US reports print expenses positive; many European
         reports print them negative, which the plain sum covers).

    A verified total consumes its children and represents them upward, so
    the discovered structure is exactly a calculation tree.
    """
    groups: list[FootingGroup] = []
    stack: list[int] = []
    rows = reconciled.rows

    def flagged(index: int, column: int) -> bool:
        provenance = rows[index].provenance
        return column < len(provenance) and provenance[column].rule == "flagged"

    def verify(total_index: int, children: list[int], weights: list[Decimal]) -> tuple[int, int, int]:
        """(checked, passed, flagged_columns): a column with a flagged cell
        among the participants is an abstention, not a footing failure."""
        checked = passed = flagged_columns = 0
        for column in range(reconciled.n_columns):
            participants = [total_index, *children]
            if any(flagged(i, column) for i in participants):
                flagged_columns += 1
                continue
            total = rows[total_index].printed[column]
            terms = [
                weight * rows[i].printed[column]
                for i, weight in zip(children, weights)
                if rows[i].printed[column] is not None
            ]
            if total is None or not terms:
                continue
            checked += 1
            tolerance = Decimal("0.5") * (len(terms) + 1)
            if abs(sum(terms) - total) <= tolerance:
                passed += 1
        return checked, passed, flagged_columns

    def is_cascade_anchor(index: int) -> bool:
        if statement != "income_statement":
            return False
        info = concepts.get(index)
        if info and info.concept.split(":", 1)[-1] in DERIVED_IS_LOCALS:
            return True
        return canon_label(rows[index].label) in SUBTOTAL_LABELS

    def sigma(index: int) -> Decimal:
        info = concepts.get(index)
        balance = info.balance if info else "debit"
        return Decimal(1) if balance == "credit" else Decimal(-1)

    def section_run(index: int) -> list[int]:
        section = rows[index].section
        run: list[int] = []
        for candidate in reversed(stack):
            if rows[candidate].section != section:
                break
            if candidate in consumed_totals:
                break
            run.insert(0, candidate)
        return run

    consumed_totals: set[int] = set()
    for index, row in enumerate(rows):
        if statement == "cash_flow" and CASH_ENDPOINT.search(row.label):
            continue  # beginning/ending balances live outside the arithmetic
        total_like = _is_total_like(row, row.section, statement)
        cascade = is_cascade_anchor(index)
        if not total_like and not cascade:
            stack.append(index)
            continue
        if not stack:
            stack.append(index)
            continue
        candidates: list[tuple[str, list[int], list[Decimal]]] = []
        run = section_run(index)
        if run and len(run) < len(stack):
            candidates.append(("section", run, [Decimal(1)] * len(run)))
        # plain sums over stack suffixes: the shortest suffix wins first, so
        # a completed hierarchy lower in the stack ("Total assets" when the
        # liability side foots) cannot pollute an unrelated total
        for start in range(len(stack) - 1, -1, -1):
            suffix = stack[start:]
            if len(suffix) < 2 and len(stack) > 1:
                continue
            candidates.append(("group", suffix, [Decimal(1)] * len(suffix)))
        relative = sigma(index)
        candidates.append(
            ("cascade_signed", list(stack), [sigma(i) / relative for i in stack])
        )
        best: FootingGroup | None = None
        any_flagged = 0
        for method, children, weights in candidates:
            checked, passed, flagged_columns = verify(index, children, weights)
            any_flagged = max(any_flagged, flagged_columns)
            group = FootingGroup(index, children, weights, checked, passed, method)
            if checked and passed == checked:
                best = group
                break
            if best is None or (checked and passed > best.columns_passed):
                best = group
        if best is None:
            stack.append(index)
            continue
        if best.columns_checked == 0 and any_flagged:
            best = FootingGroup(
                best.total_index,
                best.child_indices,
                best.child_weights,
                0,
                0,
                "unverifiable_flags",
            )
        groups.append(best)
        if best.columns_checked and best.columns_passed == best.columns_checked:
            for child in best.child_indices:
                if child in stack:
                    stack.remove(child)
            consumed_totals.add(index)
        stack.append(index)
    return groups


_IDENTITY_RIGHT = (
    "total liabilities and shareholders equity",
    "total liabilities and stockholders equity",
    "total liabilities and equity",
    "total equity and liabilities",
    "total liabilities shareholders equity",
)


def _find(reconciled: ReconciledStatement, canon: str) -> int | None:
    for index, row in enumerate(reconciled.rows):
        if canon_label(row.label) == canon:
            return index
    return None


def _identity_check(reconciled: ReconciledStatement) -> tuple[bool | None, str]:
    assets = _find(reconciled, "total assets")
    if assets is None:
        return None, "no 'Total assets' row"
    right = None
    for candidate in _IDENTITY_RIGHT:
        right = _find(reconciled, candidate)
        if right is not None:
            break
    if right is None:
        liabilities = _find(reconciled, "total liabilities")
        equity = _find(reconciled, "total equity") or _find(
            reconciled, "total shareholders equity"
        )
        if liabilities is None or equity is None:
            return None, "no combined or component totals"
        ok = True
        for column in range(reconciled.n_columns):
            a = reconciled.rows[assets].printed[column]
            l = reconciled.rows[liabilities].printed[column]
            e = reconciled.rows[equity].printed[column]
            if None in (a, l, e):
                continue
            ok = ok and abs(a - (l + e)) <= Decimal("1.5")
        return ok, "assets vs liabilities + equity"
    ok = True
    for column in range(reconciled.n_columns):
        a = reconciled.rows[assets].printed[column]
        b = reconciled.rows[right].printed[column]
        if None in (a, b):
            continue
        ok = ok and abs(a - b) <= Decimal("1")
    return ok, "assets vs combined right-hand total"


def _cash_tie(reconciled: ReconciledStatement) -> tuple[bool | None, str]:
    begin = end = change = None
    fx = Decimal(0)
    activity_totals: list[Decimal] = []
    for row in reconciled.rows:
        canon = canon_label(row.label)
        value = row.printed[0]
        if value is None:
            continue
        if re.search(r"(beginning|at january|start) ", canon + " ") or canon.endswith(
            "beginning"
        ):
            begin = value if begin is None else begin
        elif re.search(r"(end of|at december|ending)", canon):
            end = value
        elif re.search(r"net (increase|decrease|change)", canon):
            change = value
        elif "effect of" in canon and "exchange" in canon:
            fx = value
        elif CF_ACTIVITY_TOTAL.search(row.label):
            activity_totals.append(value)
    if begin is None or end is None:
        return None, "no beginning/ending cash rows"
    if change is None and activity_totals:
        change = sum(activity_totals, Decimal(0))
        detail = "activity totals"
    elif change is None:
        return None, "no net-change row or activity totals"
    else:
        detail = "net-change row"
    # filers differ on whether the net-change row already includes the FX
    # effect; either convention ties
    with_fx = abs(begin + change + fx - end)
    without_fx = abs(begin + change - end)
    ok = min(with_fx, without_fx) <= Decimal("3")
    convention = "fx inside change" if without_fx < with_fx else "fx added"
    return ok, f"begin {begin} + change {change} ({detail}, {convention}) vs end {end}"


def run_checks(
    reconciled: ReconciledStatement,
    statement: str,
    concepts: dict[int, "ConceptInfo"],
) -> UntaggedChecks:
    checks = UntaggedChecks()
    checks.footing_groups = _footing(reconciled, statement, concepts)
    verified = [group for group in checks.footing_groups if group.columns_checked]
    checks.footing_pass = all(
        group.columns_passed == group.columns_checked for group in verified
    )
    if statement == "balance_sheet":
        checks.identity_pass, checks.identity_detail = _identity_check(reconciled)
    if statement == "cash_flow":
        checks.cash_tie_pass, checks.cash_tie_detail = _cash_tie(reconciled)
    return checks


def map_rows(
    statement_kind: str,
    reconciled: ReconciledStatement,
    dictionary: dict[str, ConceptInfo],
    tokens: dict[str, set[str]],
    llm_client: llm_module.LLMClient | None,
    audit: LLMAudit,
) -> tuple[dict[int, ConceptInfo], dict[str, int]]:
    """Row -> taxonomy concept, lexical first, LLM-over-shortlist second."""
    stats = {"lexical": 0, "llm": 0, "unmapped": 0}
    concepts: dict[int, ConceptInfo] = {}
    for index, row in enumerate(reconciled.rows):
        canon = canon_label(row.label)
        info = dictionary.get(canon) or dictionary.get(_condensed(row.label))
        source = "lexical"
        if info is None and llm_client is not None and row.label.strip():
            shortlist = _shortlist(row.label, tokens)
            if shortlist:
                chosen = map_concept(
                    llm_client, audit, statement_kind, row.section, row.label, shortlist
                )
                if chosen:
                    matches = [i for i in dictionary.values() if i.concept == chosen]
                    if matches:
                        info = matches[0]
                        source = "llm"
        if info is not None and statement_kind == "balance_sheet":
            side_debit = _expected_debit(statement_kind, row.section, row.label)
            if side_debit is not None and (info.balance == "debit") != side_debit:
                if "treasury" not in canon:
                    info = None  # polarity veto: abstain rather than force
        if info is not None:
            concepts[index] = info
            stats[source] += 1
        else:
            stats["unmapped"] += 1
    return concepts, stats


# ---------------------------------------------------------------------------
# statement construction (concept mapping + discovered calc structure)
# ---------------------------------------------------------------------------


def _slug(text: str, index: int) -> str:
    cleaned = unicodedata.normalize("NFKD", text)
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", cleaned.title()) or f"Row{index}"
    return f"doc:{cleaned[:60]}_{index}"


def _header_years(extraction) -> list[int]:
    for output in extraction.readers.values():
        text = " ".join(output.header_lines)
        years = [int(match.group(0)) for match in YEAR.finditer(text)]
        deduped: list[int] = []
        for year in years:
            if year not in deduped:
                deduped.append(year)
        if len(deduped) >= 2:
            return deduped[:3]
    return []


def build_statement(
    document: str,
    statement_kind: str,
    reconciled: ReconciledStatement,
    checks: UntaggedChecks,
    years: list[int],
    concepts: dict[int, ConceptInfo],
) -> StructuredStatement | None:
    """A StructuredStatement from reconciled rows, or None without columns."""
    n_columns = min(reconciled.n_columns, 3 if statement_kind != "balance_sheet" else 2)
    if n_columns == 0:
        return None
    if len(years) >= n_columns:
        ordered = years[:n_columns]
    else:
        ordered = list(range(2024, 2024 - n_columns, -1))  # unknown: label-only
    if statement_kind == "balance_sheet":
        columns = tuple(f"I{year}-12-31" for year in ordered)
    else:
        columns = tuple(f"D{year}-01-01:{year}-12-31" for year in ordered)

    total_indices = {group.total_index for group in checks.footing_groups}
    rows: list[StatementRow] = []
    calc: dict[str, list[tuple[str, Decimal]]] = {}
    concept_names: dict[int, str] = {}
    void_totals: set[int] = set()
    for index, row in enumerate(reconciled.rows):
        info = concepts.get(index)
        concept_names[index] = info.concept if info else _slug(row.label, index)
    for group in checks.footing_groups:
        verified = group.columns_checked and group.columns_passed == group.columns_checked
        if verified or group.method == "unverifiable_flags":
            calc[concept_names[group.total_index]] = [
                (concept_names[i], weight)
                for i, weight in zip(group.child_indices, group.child_weights)
            ]
        if group.method == "unverifiable_flags":
            # a total whose arithmetic could not be checked (flagged cells
            # among the participants) must not stand beside its components
            # as an independent account: it becomes a derived row with its
            # value voided, and the flagged hole surfaces as a constant,
            # disclosed identity residual instead of silent double counting
            void_totals.add(group.total_index)
    for index, row in enumerate(reconciled.rows):
        info = concepts.get(index)
        is_total = index in total_indices
        label_lower = row.label.lower()
        period_type = "instant" if statement_kind == "balance_sheet" else "duration"
        preferred = None
        if statement_kind == "cash_flow" and re.search(
            r"beginning|at january|start of", label_lower
        ):
            period_type = "instant"
            preferred = "http://www.xbrl.org/2003/role/periodStartLabel"
        elif statement_kind == "cash_flow" and re.search(
            r"end of|at december|ending", label_lower
        ):
            period_type = "instant"
            preferred = "http://www.xbrl.org/2003/role/periodEndLabel"
        balance = info.balance if info else _default_balance(statement_kind, row.section, row.label)
        voided = index in void_totals
        cells = tuple(
            Cell(
                columns[column],
                None
                if voided
                else (row.values[column] if column < len(row.values) else None),
                -6,
                None,
            )
            for column in range(n_columns)
        )
        rows.append(
            StatementRow(
                order=index,
                concept=concept_names[index],
                dims=(),
                label=row.label or "(total)",
                depth=1,
                kind="derived" if concept_names[index] in calc else "leaf",
                derivation="calc" if concept_names[index] in calc else "",
                preferred_label=preferred,
                negated=False,
                displayed_sign=1,
                period_type=info.period_type if info and statement_kind != "cash_flow" else period_type,
                balance=balance,
                is_monetary=True,
                is_extension=info is None,
                anchor=None,
                section=(row.section,) if row.section else (),
                cells=cells,
            )
        )
    statement = StructuredStatement(
        company=document,
        standard="untagged",
        statement=statement_kind,
        linkrole=f"document:{document}:{statement_kind}",
        role_definition=f"{statement_kind} (untagged extraction)",
        currency="",
        columns=columns,
        rows=rows,
        calc_children=calc,
        notes=[f"columns assume 31 Dec fiscal years: {ordered}"] if years else [
            "column years not detected; synthetic ordering"
        ],
    )
    return statement


def _expected_debit(statement: str, section: str, label: str) -> bool | None:
    if statement != "balance_sheet":
        return None
    text = f"{section} {label}".lower()
    if "asset" in text:
        return True
    if any(word in text for word in ("liabilit", "equity", "payable", "capital")):
        return False
    return None


def _default_balance(statement: str, section: str, label: str) -> str:
    if statement == "balance_sheet":
        side = _expected_debit(statement, section, label)
        return "debit" if side in (True, None) else "credit"
    if statement == "income_statement":
        return "credit" if re.search(r"revenue|sales|income from", label.lower()) else "debit"
    return "debit"


# ---------------------------------------------------------------------------
# per-document run
# ---------------------------------------------------------------------------


def analyze_pdf(pdf_path: Path, simulate_paths: int = 200, seed: int = 20260706) -> dict[str, Any]:
    document = re.sub(r"[^a-z0-9]+", "_", pdf_path.stem.lower()).strip("_")
    out_dir = UNTAGGED_DIR / document
    out_dir.mkdir(parents=True, exist_ok=True)
    llm_client = llm_module.default_client()
    audit = LLMAudit()
    dictionary, tokens = _load_dictionary()
    outcome: dict[str, Any] = {
        "document": document,
        "file": str(pdf_path),
        "llm": llm_client is not None,
        "statements": {},
    }
    statements: dict[str, StructuredStatement] = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = locate.scan_pages(pdf)
        candidates = {
            info.index + 1: info.text[:2400]
            for info in pages
            if info.value_rows >= locate.MIN_VALUE_ROWS
        }
        for statement_kind in STATEMENTS:
            record: dict[str, Any] = {}
            outcome["statements"][statement_kind] = record
            try:
                try:
                    page_indices = locate.locate_statement(pages, statement_kind)
                    record["located_by"] = "deterministic"
                except RuntimeError:
                    if llm_client is None:
                        record["error"] = "not located (no LLM fallback configured)"
                        continue
                    query = statement_kind.replace("_", " ")
                    picked = select_pages(llm_client, audit, candidates, query)
                    page_indices = [p - 1 for p in picked][:3]
                    record["located_by"] = "llm"
                    if not page_indices:
                        record["error"] = "not located"
                        continue
                record["pages"] = [p + 1 for p in page_indices]
                extraction = read_statement_pages(
                    pdf, pdf_path, statement_kind, page_indices, pages
                )
                reconciled = reconcile(extraction)
                if llm_client is not None and reconciled.flags:
                    pages_text = "\n".join(
                        pages[i].text for i in page_indices if i < len(pages)
                    )
                    record["llm_adjudicated"] = adjudicate_flags(
                        llm_client, audit, reconciled, pages_text
                    )
                concepts, mapping_stats = map_rows(
                    statement_kind, reconciled, dictionary, tokens, llm_client, audit
                )
                checks = run_checks(reconciled, statement_kind, concepts)
                record.update(
                    {
                        "rows": len(reconciled.rows),
                        "columns": reconciled.n_columns,
                        "accepted_cells": reconciled.accepted_cells,
                        "flags": len(reconciled.flags),
                        "scale": str(extraction.scale.statement_scale),
                        "footing_groups": len(checks.footing_groups),
                        "footing_pass": checks.footing_pass,
                        "identity": {
                            "pass": checks.identity_pass,
                            "detail": checks.identity_detail,
                        }
                        if statement_kind == "balance_sheet"
                        else None,
                        "cash_tie": {
                            "pass": checks.cash_tie_pass,
                            "detail": checks.cash_tie_detail,
                        }
                        if statement_kind == "cash_flow"
                        else None,
                    }
                )
                years = _header_years(extraction)
                statement = build_statement(
                    document, statement_kind, reconciled, checks, years, concepts
                )
                record["mapping"] = mapping_stats
                if statement is not None:
                    statements[statement_kind] = statement
                    statement.save(out_dir / f"{statement_kind}.json")
            except Exception as exc:  # keep the sweep alive; report the failure
                record["error"] = f"{type(exc).__name__}: {exc}"

    outcome["simulation"] = _try_simulation(
        document, statements, simulate_paths, seed, outcome["statements"]
    )
    outcome["llm_calls"] = audit.calls
    (out_dir / "audit_llm.json").write_text(
        json.dumps({"calls": audit.calls, "decisions": audit.decisions}, indent=1),
        encoding="utf-8",
    )
    (out_dir / "outcome.json").write_text(
        json.dumps(outcome, indent=1, default=str), encoding="utf-8"
    )
    _write_report(out_dir, outcome)
    return outcome


def _try_simulation(
    document: str,
    statements: dict[str, StructuredStatement],
    paths: int,
    seed: int,
    quality: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if set(statements) != set(STATEMENTS):
        return {"status": "skipped", "reason": "not all three statements extracted"}
    # structural quality gate: simulation needs a balance sheet whose cells
    # all cleared the reader gate and whose arithmetic verified; flagged
    # cells are holes that LLM adjudication must clear first
    if quality:
        blockers: list[str] = []
        for kind, record in quality.items():
            if record.get("flags") and kind == "balance_sheet":
                blockers.append(f"{record['flags']} flagged balance-sheet cells")
            if record.get("footing_pass") is False:
                blockers.append(f"{kind} footing unverified")
            if kind == "balance_sheet" and record.get("identity", {}) and record["identity"].get("pass") is False:
                blockers.append("A = L + E failed")
        if blockers:
            return {
                "status": "skipped",
                "reason": "; ".join(sorted(set(blockers)))
                + " (adjudication required before simulation)",
            }
    from fss.engine import roles as R
    from fss.engine.project import Projector

    try:
        projector = Projector(document, statements)
        revenue = projector._rows(projector.inc, {R.REVENUE})
        cash = projector._rows(projector.bs, {R.CASH})
        retained = projector._rows(projector.bs, {R.RETAINED_EARNINGS})
        missing = [
            name
            for name, rows in (("revenue", revenue), ("cash", cash), ("retained earnings", retained))
            if not rows
        ]
        if missing:
            return {"status": "skipped", "reason": f"driver roles unresolved: {missing}"}
        from fss.simulate import run_all_scenarios

        results, verdict = run_all_scenarios(document, statements, paths=paths, seed=seed)
        summary = {
            scenario: {
                "mean_net_income_m": f"{result.mean('net_income') / Decimal(1_000_000):,.0f}",
                "violations": result.violations,
            }
            for scenario, result in results.items()
        }
        return {
            "status": "ok",
            "symbolic_balanced": verdict.balanced,
            "scenarios": summary,
        }
    except Exception as exc:
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}


def _write_report(out_dir: Path, outcome: dict[str, Any]) -> None:
    lines = [f"# Untagged extraction report: {outcome['document']}", ""]
    lines.append(f"Source: `{outcome['file']}`  ")
    lines.append(
        "LLM assist: " + ("configured" if outcome["llm"] else "not configured (deterministic only)")
    )
    lines.append("")
    for statement, record in outcome["statements"].items():
        lines.append(f"## {statement}")
        lines.append("")
        if "error" in record:
            lines.append(f"- FAILED: {record['error']}")
            lines.append("")
            continue
        lines.append(
            f"- pages {record['pages']} ({record['located_by']}), "
            f"{record['rows']} rows x {record['columns']} columns, scale {record['scale']}"
        )
        lines.append(
            f"- accepted cells {record['accepted_cells']}, flags {record['flags']}"
            + (
                f", LLM-adjudicated {record['llm_adjudicated']}"
                if record.get("llm_adjudicated")
                else ""
            )
        )
        lines.append(
            f"- footing: {record['footing_groups']} verified groups, "
            f"{'PASS' if record['footing_pass'] else 'FAIL'}"
        )
        if record.get("identity"):
            identity = record["identity"]
            verdict = {True: "PASS", False: "FAIL", None: "N/A"}[identity["pass"]]
            lines.append(f"- A = L + E: {verdict} ({identity['detail']})")
        if record.get("cash_tie"):
            tie = record["cash_tie"]
            verdict = {True: "PASS", False: "FAIL", None: "N/A"}[tie["pass"]]
            lines.append(f"- cash tie: {verdict} ({tie['detail']})")
        mapping = record.get("mapping", {})
        lines.append(
            f"- concept mapping: {mapping.get('lexical', 0)} lexical, "
            f"{mapping.get('llm', 0)} LLM, {mapping.get('unmapped', 0)} unmapped"
        )
        lines.append("")
    simulation = outcome["simulation"]
    lines.append("## Simulation")
    lines.append("")
    if simulation["status"] == "ok":
        lines.append("- symbolic closure: " + ("PROVEN" if simulation["symbolic_balanced"] else "FAILED"))
        for scenario, row in simulation["scenarios"].items():
            lines.append(
                f"- {scenario}: mean net income {row['mean_net_income_m']}M "
                f"(identity violations {row['violations']})"
            )
    else:
        lines.append(f"- {simulation['status']}: {simulation.get('reason', '')}")
    lines.append("")
    lines.append(f"LLM calls: {outcome.get('llm_calls', 0)}")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def summarize() -> None:
    """Regenerate the sweep summary from every outcome.json on disk."""
    summary_rows: list[str] = [
        "| Document | BS | IS | CF | footing | A=L+E | cash tie | mapped | simulation |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for outcome_path in sorted(UNTAGGED_DIR.glob("*/outcome.json")):
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        cells = {"balance_sheet": "-", "income_statement": "-", "cash_flow": "-"}
        footing = identity = tie = "-"
        mapped = unmapped = 0
        for statement, record in outcome["statements"].items():
            if "error" in record:
                cells[statement] = "FAIL"
                continue
            cells[statement] = f"{record['rows']}r"
            footing = "PASS" if record["footing_pass"] and footing != "FAIL" else "FAIL"
            if record.get("identity") and record["identity"]["pass"] is not None:
                identity = "PASS" if record["identity"]["pass"] else "FAIL"
            if record.get("cash_tie") and record["cash_tie"]["pass"] is not None:
                tie = "PASS" if record["cash_tie"]["pass"] else "FAIL"
            mapping = record.get("mapping", {})
            mapped += mapping.get("lexical", 0) + mapping.get("llm", 0)
            unmapped += mapping.get("unmapped", 0)
        simulation = outcome["simulation"]["status"]
        share = f"{mapped}/{mapped + unmapped}" if (mapped + unmapped) else "-"
        summary_rows.append(
            f"| {outcome['document']} | {cells['balance_sheet']} | "
            f"{cells['income_statement']} | {cells['cash_flow']} | {footing} | "
            f"{identity} | {tie} | {share} | {simulation} |"
        )
    UNTAGGED_DIR.mkdir(parents=True, exist_ok=True)
    (UNTAGGED_DIR / "summary.md").write_text(
        "# Untagged sweep summary\n\n" + "\n".join(summary_rows) + "\n", encoding="utf-8"
    )
    print(f"summary -> {UNTAGGED_DIR / 'summary.md'}")


def main() -> None:
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--merge":
        summarize()
        return
    targets: list[Path] = []
    for argument in arguments or [
        str(Path("previous_llm_extractor/annual_reports/for_financial_statements"))
    ]:
        path = Path(argument)
        if path.is_dir():
            targets.extend(sorted(path.rglob("*.pdf")))
        elif path.suffix.lower() == ".pdf":
            targets.append(path)
    for pdf_path in targets:
        print(f"=== {pdf_path.name}")
        outcome = analyze_pdf(pdf_path)
        print(f"    -> {outcome['simulation']['status']}")
    summarize()


if __name__ == "__main__":
    main()
