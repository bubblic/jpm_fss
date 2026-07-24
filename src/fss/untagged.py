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

import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pdfplumber

from fss import llm as llm_module
from fss.paths import DATA_DIR, OUT_DIR, ROOT
from fss.pdfread import locate, zh
from fss.pdfread.assemble import read_statement_pages
from fss.pdfread.llm_assist import LLMAudit, adjudicate_flags, map_concept, select_pages
from fss.reconcile import ReconciledStatement, canon_label, reconcile
from fss.statements import Cell, StatementRow, StructuredStatement

UNTAGGED_DIR = OUT_DIR / "untagged"
RUNTIME_DIR = OUT_DIR / "runtime"
ARTIFACTS_DIR = ROOT / "artifacts" / "mappings"
STATEMENTS = ("balance_sheet", "income_statement", "cash_flow")
TOTAL_PREFIX = re.compile(r"^(total|net total)\b", re.IGNORECASE)
CF_ACTIVITY_TOTAL = re.compile(
    r"^(net )?cash (flows? )?(provided by|used in|used for|from|generated)", re.IGNORECASE
)
CF_NET_CHANGE = re.compile(r"net (increase|decrease|change)", re.IGNORECASE)
CASH_ENDPOINT = re.compile(
    r"beginning|at january|start of|end of|at december|ending balance", re.IGNORECASE
)
YEAR = re.compile(r"\b(19|20)\d{2}\b|(19|20)\d{2}(?=年)")
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


def _load_dictionary() -> tuple[
    dict[str, ConceptInfo], dict[str, dict[str, ConceptInfo]], dict[str, set[str]]
]:
    """label -> concept info (plain and condensed), globally and scoped per
    statement kind, plus a token index.

    The statement scope exists because the same printed label legitimately
    means different concepts on different faces: on a balance sheet
    ``Inventories`` is the stock (InventoryNet), on a cash flow it is the
    period's delta (IncreaseDecreaseInInventories). Lookups prefer the
    statement's own scope and fall back to the global view."""
    by_label: dict[str, ConceptInfo] = {}
    by_statement: dict[str, dict[str, ConceptInfo]] = {}
    tokens: dict[str, set[str]] = {}
    for path in sorted((DATA_DIR / "extracted").glob("*.json")):
        scoped = by_statement.setdefault(path.stem.split("_", 1)[1], {})
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["rows"]:
            if row["kind"] == "abstract" or row["dims"]:
                continue
            info = ConceptInfo(
                row["concept"], row["balance"], row["period_type"], row["is_monetary"]
            )
            for key in (canon_label(row["label"]), _condensed(row["label"])):
                if key:
                    by_label.setdefault(key, info)
                    scoped.setdefault(key, info)
            local = row["concept"].split(":", 1)[-1]
            words = {w.lower() for w in re.findall(r"[A-Z][a-z]+|[a-z]+", local)}
            words.update(canon_label(row["label"]).split())
            tokens.setdefault(row["concept"], set()).update(words)
    return by_label, by_statement, tokens


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
    result = [concept for score, concept in scored[:top] if score > 0.15]
    if result:
        return result
    # Fused-label fallback: tightly-set PDFs glue words together, so token
    # overlap scores zero. Score by how many of a concept's long words
    # appear as substrings of the space-free label instead.
    condensed = _condensed(label)
    if len(condensed) >= 12:
        contained = []
        for concept, concept_words in tokens.items():
            long_words = [w for w in concept_words if len(w) >= 4]
            if not long_words:
                continue
            hit = sum(1 for w in long_words if w in condensed)
            contained.append((hit / len(long_words), concept))
        contained.sort(reverse=True)
        return [concept for score, concept in contained[:top] if score >= 0.5]
    return []


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


def _solve_weights(
    values_by_column: list[dict[int, Decimal]],
    child_indices: list[int],
    total_by_column: list[Decimal | None],
    node_budget: int = 120_000,
) -> list[Decimal] | None:
    """Search child weights in {+1, 0, -1} that reproduce the total.

    This is the arithmetic a human does with a pencil when a printed
    statement carries netting the labels do not spell out ("Net revenues"
    = revenues minus interest expense; "Total assets" skipping the gross
    loans that a "Net loans" line already absorbs). The reference column
    proposes candidate weightings (branch and bound, nearest rows first,
    magnitude pruning); every OTHER checkable column must then agree, so a
    coincidental subset on one column dies on the next. Returns weights
    aligned with child_indices, or None.
    """
    reference = max(
        range(len(values_by_column)),
        key=lambda c: (total_by_column[c] is not None)
        * (1 + len(values_by_column[c])),
    )
    target = total_by_column[reference]
    if target is None:
        return None
    values = values_by_column[reference]
    usable = [i for i in child_indices if i in values]
    if len(usable) < 2:
        return None
    # nearest the total first: totals summarize adjacent content
    usable = sorted(usable, reverse=True)[:20]
    suffix_max = [Decimal(0)] * (len(usable) + 1)
    for pos in range(len(usable) - 1, -1, -1):
        suffix_max[pos] = suffix_max[pos + 1] + abs(values[usable[pos]])
    solutions: list[dict[int, Decimal]] = []
    nodes = 0

    def descend(pos: int, running: Decimal, weights: dict[int, Decimal]) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > node_budget or len(solutions) >= 24:
            return
        used = [w for w in weights.values() if w]
        tolerance = Decimal("0.5") * (len(used) + 1)
        if pos == len(usable):
            if len(used) >= 2 and abs(running - target) <= tolerance:
                solutions.append(dict(weights))
            return
        max_tolerance = Decimal("0.5") * (len(usable) + 1)
        if abs(running - target) > suffix_max[pos] + max_tolerance:
            return  # even all-in cannot reach the target
        index = usable[pos]
        for weight in (Decimal(1), Decimal(0), Decimal(-1)):
            weights[index] = weight
            descend(pos + 1, running + weight * values[index], weights)
        del weights[index]

    descend(0, Decimal(0), {})
    if not solutions:
        return None

    def preference(solution: dict[int, Decimal]) -> tuple:
        used = [i for i, w in solution.items() if w]
        flips = sum(1 for w in solution.values() if w < 0)
        span = (max(used) - min(used) + 1) - len(used) if used else 99
        return (flips, span, -len(used))

    for solution in sorted(solutions, key=preference):
        agreed = checked = 0
        for column, column_values in enumerate(values_by_column):
            total = total_by_column[column]
            terms = [
                w * column_values[i]
                for i, w in solution.items()
                if w and i in column_values
            ]
            if total is None or len(terms) < 2:
                continue
            checked += 1
            tolerance = Decimal("0.5") * (len(terms) + 1)
            if abs(sum(terms) - total) <= tolerance:
                agreed += 1
        if checked and agreed == checked:
            return [solution.get(i, Decimal(0)) for i in child_indices]
    return None


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
        if not (best and best.columns_checked and best.columns_passed == best.columns_checked):
            # label-driven candidates failed: solve for the weights the
            # printed arithmetic itself implies (netting, absorbed
            # mini-totals), cross-checked on every column
            window = stack[-20:]
            values_by_column: list[dict[int, Decimal]] = []
            total_by_column: list[Decimal | None] = []
            for column in range(reconciled.n_columns):
                values_by_column.append(
                    {
                        i: rows[i].printed[column]
                        for i in window
                        if rows[i].printed[column] is not None and not flagged(i, column)
                    }
                )
                usable_total = (
                    rows[index].printed[column] is not None
                    and not flagged(index, column)
                )
                total_by_column.append(
                    rows[index].printed[column] if usable_total else None
                )
            solved = _solve_weights(values_by_column, window, total_by_column)
            if solved is not None:
                children = [i for i, w in zip(window, solved) if w]
                weights = [w for w, i in zip(solved, window) if w]
                checked, passed, _ = verify(index, children, weights)
                if checked and passed == checked:
                    best = FootingGroup(index, children, weights, checked, passed, "solved")
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
    overlay: dict[str, ConceptInfo] | None = None,
    overlay_source: str = "artifact",
) -> tuple[dict[int, ConceptInfo], dict[str, int], dict[int, str]]:
    """Row -> taxonomy concept: lexical, then the reviewed artifact
    overlay (runtime replay, or a prior year's artifact carried forward
    at onboard time), then LLM-over-shortlist (build time only)."""
    stats = {"lexical": 0, "artifact": 0, "carried": 0, "llm": 0, "unmapped": 0}
    concepts: dict[int, ConceptInfo] = {}
    sources: dict[int, str] = {}
    llm_budget = 25  # mapping calls per statement (cost bound)
    for index, row in enumerate(reconciled.rows):
        canon = canon_label(row.label)
        # Filers often print a note reference after the label ("Long-term
        # debt 14"); lookups try the bare label too.
        bare = re.sub(r"\s+\(?\d{1,3}\)?$", "", row.label)
        info = (
            dictionary.get(canon)
            or dictionary.get(_condensed(row.label))
            or dictionary.get(canon_label(bare))
            or dictionary.get(_condensed(bare))
        )
        source = "lexical"
        if info is None and zh.has_cjk(row.label):
            found = zh.lookup(row.label)
            if found is not None:
                local, balance, period_type = found
                info = ConceptInfo(f"us-gaap:{local}", balance, period_type, True)
        if info is None and overlay is not None:
            info = (
                overlay.get(canon)
                or overlay.get(_condensed(row.label))
                or overlay.get(canon_label(bare))
                or overlay.get(_condensed(bare))
            )
            if info is not None:
                source = overlay_source
        if info is None and llm_client is not None and row.label.strip() and llm_budget > 0:
            llm_budget -= 1
            shortlist = _shortlist(bare, tokens)
            if shortlist:
                chosen = map_concept(
                    llm_client, audit, statement_kind, row.section, row.label, shortlist
                )
                if chosen:
                    matches = [i for i in dictionary.values() if i.concept == chosen]
                    if matches:
                        info = matches[0]
                        source = "llm"
        veto_applies = statement_kind == "balance_sheet" or (
            # exact lexical label hits are trusted on the income statement
            # ("Provision for income taxes" is a debit despite the word
            # "income"); the polarity veto there only screens LLM choices
            statement_kind == "income_statement"
            and source == "llm"
        )
        if info is not None and veto_applies:
            side_debit = _expected_debit(statement_kind, row.section, row.label)
            if side_debit is not None and (info.balance == "debit") != side_debit:
                if "treasury" not in canon:
                    info = None  # polarity veto: abstain rather than force
        if info is not None:
            concepts[index] = info
            stats[source] += 1
            sources[index] = source
        else:
            stats["unmapped"] += 1
    return concepts, stats, sources


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
    text = f"{section} {label}".lower()
    if statement == "income_statement":
        # mis-polarized income-statement mappings flip signed-cascade
        # footing groups, so they get the same veto as balance-sheet rows;
        # expense words match first ("income tax expense" is a debit)
        if re.search(r"cost|expense|charge|depreciation|amorti|impairment|provision", text):
            return True
        if re.search(r"revenue|sales|income|profit|gain|earnings", text):
            return False
        return None
    if statement != "balance_sheet":
        return None
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


def _snap_llm_pages(
    picked: list[int],
    pages: list["locate.PageInfo"],
    assigned: dict[str, list[int]],
    statement: str,
) -> list[int]:
    """LLM page picks -> one dense contiguous cluster.

    The LLM proposes 1-based page numbers with no contiguity guarantee;
    merging scattered pages into one table produces junk grids. Group the
    surviving picks into contiguous clusters (gap <= 1) and keep the best
    by density, anchor evidence, and proximity to statements already
    located deterministically.
    """
    survivors = sorted(
        p - 1
        for p in set(picked)
        if 0 <= p - 1 < len(pages) and pages[p - 1].value_rows >= locate.MIN_VALUE_ROWS
    )
    if not survivors:
        return []
    clusters: list[list[int]] = [[survivors[0]]]
    for index in survivors[1:]:
        if index - clusters[-1][-1] <= 2:
            clusters[-1].append(index)
        else:
            clusters.append([index])
    located_spans = [run for run in assigned.values() if run]

    def cluster_score(cluster: list[int]) -> float:
        score = float(sum(pages[i].value_rows for i in cluster))
        if any(locate.ANCHORS[statement].search(pages[i].text) for i in cluster):
            score += 40.0  # the statement's own vocabulary beats mere density
        near = min(
            (locate._span_gap(cluster, run) for run in located_spans),
            default=999,
        )
        if near <= 8:
            score += 25.0
        elif near <= 20:
            score += 8.0
        return score

    best = max(clusters, key=cluster_score)
    return best[:3]


# ---------------------------------------------------------------------------
# mapping artifacts: LLMs at build time, determinism at run time
# ---------------------------------------------------------------------------


def _document_slug(pdf_path: Path) -> str:
    stem = pdf_path.stem.lower()
    if re.fullmatch(r"(ar|annual[_ ]?report)?[_ ]?\d{4}", stem):
        stem = f"{pdf_path.parent.name.lower()}_{stem}"  # generic names collide
    return re.sub(r"[^a-z0-9]+", "_", stem).strip("_")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_version() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def artifact_path(document: str) -> Path:
    return ARTIFACTS_DIR / f"{document}.json"


def load_artifact(document: str) -> dict[str, Any] | None:
    path = artifact_path(document)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_overlay(entries: list[dict[str, Any]]) -> dict[str, "ConceptInfo"]:
    """Reviewed label->concept choices from the artifact, keyed like the
    lexical dictionary (canonical and condensed forms)."""
    overlay: dict[str, ConceptInfo] = {}
    for entry in entries:
        info = ConceptInfo(
            entry["concept"], entry["balance"], entry["period_type"], True
        )
        for key in (canon_label(entry["label"]), _condensed(entry["label"])):
            if key:
                overlay.setdefault(key, info)
    return overlay


def rebuild_artifact(pdf_path: Path) -> Path:
    """Assemble the mapping artifact from committed build products.

    Build runs record every LLM decision (audit log) and every accepted
    mapping (statement JSONs). When the hosted endpoint later changes or
    disappears -- the precise risk the build/runtime split exists for --
    the artifact can be reconstructed from those versioned products
    without consulting any model.
    """
    document = _document_slug(pdf_path)
    out_dir = UNTAGGED_DIR / document
    outcome = json.loads((out_dir / "outcome.json").read_text(encoding="utf-8"))
    audit_file = out_dir / "audit_llm.json"
    decisions = (
        json.loads(audit_file.read_text(encoding="utf-8")).get("decisions", [])
        if audit_file.exists()
        else []
    )
    adjudications = [
        {"label": d["label"], "column": d["column"], "value": d["value"]}
        for d in decisions
        if d.get("kind") == "adjudicated"
    ]
    build: dict[str, Any] = {
        "document": document,
        "source_file": str(pdf_path),
        "source_sha256": _sha256(pdf_path),
        "code_version": _git_version(),
        "built_from": "committed build products (LLM decisions recorded at build time)",
        "approved_by": "PENDING SIGN-OFF",
        "statements": {},
    }
    for kind, record in outcome["statements"].items():
        if "error" in record or not record.get("pages"):
            continue
        mapping: list[dict[str, Any]] = []
        statement_file = out_dir / f"{kind}.json"
        if statement_file.exists():
            payload = json.loads(statement_file.read_text(encoding="utf-8"))
            for row in payload["rows"]:
                if row["kind"] == "abstract" or row["concept"].startswith("doc:"):
                    continue
                mapping.append(
                    {
                        "label": row["label"],
                        "concept": row["concept"],
                        "balance": row["balance"] or "",
                        "period_type": row["period_type"],
                        "source": "build_products",
                    }
                )
        build["statements"][kind] = {
            "pages": record["pages"],
            "located_by": record["located_by"],
            "mapping": mapping,
            # adjudications are stored globally per document; replay is
            # safe because acceptance re-verifies against the readers
            "adjudications": adjudications,
        }
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    path = artifact_path(document)
    path.write_text(json.dumps(build, indent=1, default=str), encoding="utf-8")
    return path


def _apply_artifact_adjudications(
    reconciled: ReconciledStatement, entries: list[dict[str, Any]]
) -> int:
    """Replay signed-off adjudications without a model.

    The acceptance rule is the same one the LLM was held to at build time:
    the artifact's value must exactly match one of the deterministic
    readers' readings for that cell TODAY. A cell whose readings drifted
    since onboarding stays flagged, so the artifact cannot inject numbers
    into a changed document.
    """
    resolved = 0
    for entry in entries:
        canon = canon_label(str(entry["label"]))
        if not canon:
            continue
        column = int(entry["column"])
        try:
            value = Decimal(str(entry["value"]))
        except InvalidOperation:
            continue
        for row in reconciled.rows:
            row_canon = canon_label(row.label)
            # audit records truncate long labels; a prefix match is safe
            # because the reader-agreement gate below still binds
            if row_canon != canon and not row_canon.startswith(canon):
                continue
            if column >= len(row.provenance):
                break
            prov = row.provenance[column]
            if prov.rule != "flagged":
                break
            readings: set[Decimal] = set()
            for reading in prov.readings.values():
                if not reading:
                    continue
                try:
                    readings.add(Decimal(reading.replace(",", "")))
                except InvalidOperation:
                    continue
            if value in readings:
                prov.accepted_printed = value
                prov.rule = "artifact_adjudicated"
                row.printed[column] = value
                row.values[column] = value * row.scale
                resolved += 1
            break
    return resolved


# ---------------------------------------------------------------------------
# per-document run
# ---------------------------------------------------------------------------


def analyze_pdf(
    pdf_path: Path,
    simulate_paths: int = 200,
    seed: int = 20260706,
    mode: str = "explore",
    carry_from: str | None = None,
) -> dict[str, Any]:
    stem = pdf_path.stem.lower()
    if re.fullmatch(r"(ar|annual[_ ]?report)?[_ ]?\d{4}", stem):
        stem = f"{pdf_path.parent.name.lower()}_{stem}"  # generic names collide
    document = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    out_dir = (RUNTIME_DIR if mode == "runtime" else UNTAGGED_DIR) / document
    out_dir.mkdir(parents=True, exist_ok=True)
    source_sha = _sha256(pdf_path)
    # the run-time inference path never constructs a model client, no
    # matter what the environment provides (proposal v2: LLMs at build
    # time, determinism at run time)
    llm_client = None if mode == "runtime" else llm_module.default_client()
    audit = LLMAudit()
    dictionary, by_statement, tokens = _load_dictionary()
    outcome: dict[str, Any] = {
        "document": document,
        "file": str(pdf_path),
        "mode": mode,
        "source_sha256": source_sha,
        "llm": llm_client is not None,
        "statements": {},
    }
    artifact: dict[str, Any] | None = None
    overlays: dict[str, dict[str, ConceptInfo]] = {}
    if mode == "runtime":
        artifact = load_artifact(document)
        if artifact is None:
            reason = "no mapping artifact: run `fss onboard` and sign it off first"
            outcome["statements"] = {kind: {"error": reason} for kind in STATEMENTS}
            outcome["simulation"] = {"status": "skipped", "reason": reason}
            (out_dir / "outcome.json").write_text(
                json.dumps(outcome, indent=1, default=str), encoding="utf-8"
            )
            _write_report(out_dir, outcome)
            return outcome
        outcome["artifact"] = {
            "path": str(artifact_path(document)),
            "approved_by": artifact.get("approved_by", "PENDING SIGN-OFF"),
            "code_version_at_build": artifact.get("code_version", "unknown"),
        }
        if artifact.get("source_sha256") != source_sha:
            reason = (
                "source hash mismatch: the document changed since onboarding; "
                "re-onboarding and sign-off required"
            )
            outcome["statements"] = {kind: {"error": reason} for kind in STATEMENTS}
            outcome["simulation"] = {"status": "skipped", "reason": reason}
            (out_dir / "outcome.json").write_text(
                json.dumps(outcome, indent=1, default=str), encoding="utf-8"
            )
            _write_report(out_dir, outcome)
            return outcome
        for kind, stmt_artifact in artifact.get("statements", {}).items():
            overlays[kind] = _artifact_overlay(stmt_artifact.get("mapping", []))
    carry_artifact: dict[str, Any] | None = None
    if mode == "onboard" and carry_from:
        carry_artifact = load_artifact(carry_from)
        if carry_artifact is None:
            raise SystemExit(
                f"carry-from artifact not found: {artifact_path(carry_from)}; "
                "onboard that document first"
            )
        # a prior year's reviewed mapping seeds this year's onboarding:
        # labels that match resolve without a model, and every carried
        # choice still faces the polarity veto, footing, and identities.
        # carry seeds semantics, never layout: pages are per-document and
        # stay with the deterministic locator (or its LLM fallback)
        for kind, stmt_artifact in carry_artifact.get("statements", {}).items():
            overlays[kind] = _artifact_overlay(stmt_artifact.get("mapping", []))
        outcome["carried_from"] = carry_from
    overlay_source = "carried" if carry_artifact is not None else "artifact"
    build: dict[str, Any] = {
        "document": document,
        "source_file": str(pdf_path),
        "source_sha256": source_sha,
        "code_version": _git_version(),
        "approved_by": "PENDING SIGN-OFF",
        "statements": {},
    }
    if carry_artifact is not None:
        build["carried_from"] = {
            "document": carry_from,
            "source_sha256": carry_artifact.get("source_sha256", ""),
            "approved_by": carry_artifact.get("approved_by", "PENDING SIGN-OFF"),
        }
    statements: dict[str, StructuredStatement] = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        text_options = locate.probe_text_options(pdf)
        if text_options:
            outcome["text_options"] = text_options
        pages = locate.scan_pages(pdf, text_options)
        rich_pages = sorted(
            (info for info in pages if info.value_rows >= locate.MIN_VALUE_ROWS),
            key=lambda info: info.value_rows,
            reverse=True,
        )[:80]  # bound the LLM page-fallback prompt volume
        candidates = {
            info.index + 1: info.text[:2400] for info in sorted(rich_pages, key=lambda i: i.index)
        }
        assigned = locate.assign_statements(pages)
        for statement_kind in STATEMENTS:
            record: dict[str, Any] = {}
            outcome["statements"][statement_kind] = record
            try:
                if mode == "runtime":
                    stmt_artifact = (artifact or {}).get("statements", {}).get(
                        statement_kind
                    )
                    if not stmt_artifact or not stmt_artifact.get("pages"):
                        record["error"] = (
                            "not onboarded: the mapping artifact carries no "
                            "location for this statement"
                        )
                        continue
                    page_indices = [p - 1 for p in stmt_artifact["pages"]]
                    record["located_by"] = "artifact"
                else:
                    page_indices = assigned.get(statement_kind)
                    if page_indices:
                        record["located_by"] = "deterministic"
                    if not page_indices:
                        if llm_client is None:
                            record["error"] = "not located (no LLM fallback configured)"
                            continue
                        query = statement_kind.replace("_", " ")
                        picked = select_pages(llm_client, audit, candidates, query)
                        # the LLM proposes; the same density bar the deterministic
                        # locator uses disposes (prose pages with a few figures
                        # do not qualify as statement pages), and only ONE
                        # contiguous cluster survives: a statement is never
                        # scattered across the document
                        page_indices = _snap_llm_pages(picked, pages, assigned, statement_kind)
                        record["located_by"] = "llm"
                        if not page_indices:
                            record["error"] = "not located (LLM candidates failed the density bar)"
                            continue
                record["pages"] = [p + 1 for p in page_indices]
                # born-digital scope gate: statement pages must carry
                # AUTHORED text; a scan or an OCR overlay abstains here in
                # both build and runtime modes rather than degrading
                # silently (see locate.authored_text_issues)
                gate_issues = [
                    f"page {index + 1}: {issue}"
                    for index in page_indices
                    if index < len(pdf.pages)
                    for issue in locate.authored_text_issues(pdf.pages[index])
                ]
                if gate_issues:
                    record["error"] = (
                        "not born-digital: "
                        + "; ".join(gate_issues)
                        + " (scope: authored text required; OCR/vision "
                        "ingestion is out of scope)"
                    )
                    continue
                extraction = read_statement_pages(
                    pdf, pdf_path, statement_kind, page_indices, pages, text_options
                )
                reconciled = reconcile(extraction)
                if mode == "runtime" and reconciled.flags:
                    record["artifact_adjudicated"] = _apply_artifact_adjudications(
                        reconciled,
                        (artifact or {})
                        .get("statements", {})
                        .get(statement_kind, {})
                        .get("adjudications", []),
                    )
                elif llm_client is not None and reconciled.flags:
                    pages_text = "\n".join(
                        pages[i].text for i in page_indices if i < len(pages)
                    )
                    record["llm_adjudicated"] = adjudicate_flags(
                        llm_client, audit, reconciled, pages_text
                    )
                # adjudication rewrites provenance rules in place; drop
                # resolved entries so the flag count and the simulation
                # gate see the post-adjudication state
                reconciled.flags = [p for p in reconciled.flags if p.rule == "flagged"]
                lexicon = dict(dictionary)
                lexicon.update(by_statement.get(statement_kind, {}))
                concepts, mapping_stats, sources = map_rows(
                    statement_kind,
                    reconciled,
                    lexicon,
                    tokens,
                    llm_client,
                    audit,
                    overlay=overlays.get(statement_kind),
                    overlay_source=overlay_source,
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
                if mode == "onboard":
                    adjudications = [
                        {
                            "label": row.label,
                            "column": column,
                            "value": str(prov.accepted_printed),
                        }
                        for row in reconciled.rows
                        for column, prov in enumerate(row.provenance)
                        if prov.rule == "llm_adjudicated"
                    ]
                    build["statements"][statement_kind] = {
                        "pages": record["pages"],
                        "located_by": record["located_by"],
                        "mapping": [
                            {
                                "label": reconciled.rows[index].label,
                                "concept": info.concept,
                                "balance": info.balance,
                                "period_type": info.period_type,
                                "source": sources.get(index, "lexical"),
                            }
                            for index, info in sorted(concepts.items())
                        ],
                        "adjudications": adjudications,
                    }
                if statement is not None:
                    statements[statement_kind] = statement
                    statement.save(out_dir / f"{statement_kind}.json")
            except Exception as exc:  # keep the sweep alive; report the failure
                record["error"] = f"{type(exc).__name__}: {exc}"

    if all("error" in record for record in outcome["statements"].values()):
        corpus = "".join(info.text.lower().replace(" ", "") for info in pages)
        if "totalassets" not in corpus and "balancesheet" not in corpus:
            outcome["diagnosis"] = (
                "no financial-statement vocabulary in the extractable text: "
                "the statement pages are likely images; an OCR/vision reader "
                "is required for this document"
            )
    digitless = [
        info.index + 1
        for info in pages
        if len(info.text) >= 800 and not any(ch.isdigit() for ch in info.text)
    ]
    if len(digitless) >= 8:
        note = (
            f"{len(digitless)} text-bearing pages (e.g. pages "
            f"{digitless[0]}-{digitless[-1]}) extract with ZERO digits: their "
            "fonts lack unicode mappings for numerals, so no text engine can "
            "read numbers there. If the statements live in that region, any "
            "rows extracted elsewhere are condensed summaries, not the "
            "statement face; an OCR/vision reader is required."
        )
        existing = outcome.get("diagnosis")
        outcome["diagnosis"] = f"{existing} {note}" if existing else note
    outcome["simulation"] = _try_simulation(
        document, statements, simulate_paths, seed, outcome["statements"]
    )
    outcome["llm_calls"] = audit.calls
    if mode == "onboard":
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        build["llm_calls"] = audit.calls
        artifact_file = artifact_path(document)
        artifact_file.write_text(
            json.dumps(build, indent=1, default=str), encoding="utf-8"
        )
        outcome["artifact"] = {
            "path": str(artifact_file),
            "approved_by": build["approved_by"],
        }
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
    mode = outcome.get("mode", "explore")
    title = {
        "onboard": "Onboarding report (build time)",
        "runtime": "Runtime report (deterministic inference path)",
    }.get(mode, "Untagged extraction report")
    lines = [f"# {title}: {outcome['document']}", ""]
    lines.append(f"Source: `{outcome['file']}`  ")
    if outcome.get("source_sha256"):
        lines.append(f"Source SHA256: `{outcome['source_sha256']}`  ")
    if mode == "runtime":
        artifact_meta = outcome.get("artifact", {})
        lines.append(
            "LLM assist: FORBIDDEN in this mode (no model in the inference path)  "
        )
        if artifact_meta:
            lines.append(
                f"Mapping artifact: `{artifact_meta.get('path', '')}` "
                f"(approved by: {artifact_meta.get('approved_by', 'unknown')}; "
                f"built at code {artifact_meta.get('code_version_at_build', 'unknown')})  "
            )
    else:
        lines.append(
            "LLM assist: "
            + ("configured" if outcome["llm"] else "not configured (deterministic only)")
        )
        if mode == "onboard" and outcome.get("artifact"):
            lines.append(
                f"Mapping artifact written: `{outcome['artifact']['path']}` "
                f"(status: {outcome['artifact']['approved_by']})  "
            )
    if outcome.get("diagnosis"):
        lines.append("")
        lines.append(f"**Diagnosis:** {outcome['diagnosis']}")
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
        adjudication_note = ""
        if record.get("llm_adjudicated"):
            adjudication_note = f", LLM-adjudicated {record['llm_adjudicated']}"
        if record.get("artifact_adjudicated"):
            adjudication_note += (
                f", artifact-adjudicated {record['artifact_adjudicated']}"
            )
        lines.append(
            f"- accepted cells {record['accepted_cells']}, flags {record['flags']}"
            + adjudication_note
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
        artifact_part = (
            f"{mapping.get('artifact', 0)} artifact, " if mapping.get("artifact") else ""
        )
        lines.append(
            f"- concept mapping: {mapping.get('lexical', 0)} lexical, "
            f"{artifact_part}{mapping.get('llm', 0)} LLM, "
            f"{mapping.get('unmapped', 0)} unmapped"
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
    if mode == "runtime":
        lines.append(
            "LLM calls: 0 (runtime mode; replay is bit-exact given the same "
            "source, artifact, and code versions)"
        )
    else:
        lines.append(f"LLM calls: {outcome.get('llm_calls', 0)}")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def summarize(base_dir: Path = UNTAGGED_DIR) -> None:
    """Regenerate the sweep summary from every outcome.json on disk."""
    summary_rows: list[str] = [
        "| Document | BS | IS | CF | footing | A=L+E | cash tie | mapped | simulation |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for outcome_path in sorted(base_dir.glob("*/outcome.json")):
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
            mapped += (
                mapping.get("lexical", 0)
                + mapping.get("artifact", 0)
                + mapping.get("llm", 0)
            )
            unmapped += mapping.get("unmapped", 0)
        simulation = outcome["simulation"]["status"]
        share = f"{mapped}/{mapped + unmapped}" if (mapped + unmapped) else "-"
        summary_rows.append(
            f"| {outcome['document']} | {cells['balance_sheet']} | "
            f"{cells['income_statement']} | {cells['cash_flow']} | {footing} | "
            f"{identity} | {tie} | {share} | {simulation} |"
        )
    base_dir.mkdir(parents=True, exist_ok=True)
    heading = (
        "# Runtime sweep summary (deterministic inference path)"
        if base_dir == RUNTIME_DIR
        else "# Untagged sweep summary"
    )
    (base_dir / "summary.md").write_text(
        heading + "\n\n" + "\n".join(summary_rows) + "\n", encoding="utf-8"
    )
    print(f"summary -> {base_dir / 'summary.md'}")


def main(mode: str = "explore") -> None:
    arguments = sys.argv[1:]
    base_dir = RUNTIME_DIR if mode == "runtime" else UNTAGGED_DIR
    if arguments and arguments[0] == "--merge":
        summarize(base_dir)
        return
    rebuild = False
    carry_from: str | None = None
    if mode == "onboard":
        if "--rebuild" in arguments:
            rebuild = True
            arguments = [a for a in arguments if a != "--rebuild"]
        if "--carry-from" in arguments:
            marker = arguments.index("--carry-from")
            if marker + 1 >= len(arguments):
                raise SystemExit("--carry-from requires a prior document name")
            carry_from = arguments[marker + 1]
            arguments = arguments[:marker] + arguments[marker + 2 :]
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
        if rebuild:
            path = rebuild_artifact(pdf_path)
            print(f"    -> artifact {path}")
            continue
        outcome = analyze_pdf(pdf_path, mode=mode, carry_from=carry_from)
        print(f"    -> {outcome['simulation']['status']}")
    if not rebuild:
        summarize(base_dir)


if __name__ == "__main__":
    main()
