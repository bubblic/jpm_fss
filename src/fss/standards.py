"""Which reporting standard an annual report declares, read from the report.

Scan entry point: python -m fss.standards [pdf-or-folder ...]

An audited annual report states its reporting framework in itself: the
auditor's opinion ("in conformity with accounting principles generally
accepted in the United States of America") and the basis-of-preparation
note ("in accordance with IFRS as issued by the IASB"). The phrase set is
small, standardized, and near-universal in audited reports, so the
declared standard is read the way statement pages are located: by a
deterministic scan first, over condensed text (spacing-immune, with a
variant pack covering the EU and UK adoption wordings and the Chinese
declarations alongside the Chinese label pack), with the LLM as a leashed
build-time fallback (llm_assist.detect_standard) and the operator's
--standard flag as the human declaration. Never a guess: when both
supported standards are declared the scan abstains (ambiguous), and when
nothing resolves the pipeline proceeds with the conservative
cross-standard views it always had.

Supported standards are us-gaap and ifrs, the two taxonomies the union
state space is built over. A document that affirmatively declares a
different framework (Hong Kong FRS, Japanese GAAP, Ind AS, PRC ASBE, and
peers) and no supported one is refused loudly by the pipeline rather
than mapped as if covered; --standard overrides after human review.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

SUPPORTED = ("us-gaap", "ifrs")
STANDARD_PREFIX = {"us-gaap": "us-gaap:", "ifrs": "ifrs-full:"}

_US_GAAP = [
    (
        "US GAAP opinion wording",
        re.compile(r"accountingprinciplesgenerallyacceptedintheunitedstates"),
    ),
    (
        "US GAAP accordance wording",
        re.compile(r"generallyacceptedaccountingprinciplesintheunitedstates"),
    ),
    (
        "US GAAP accordance wording",
        re.compile(r"(unitedstates|us)generallyacceptedaccountingprinciples"),
    ),
    ("US GAAP named directly", re.compile(r"(accordance|conformity)withusgaap")),
]

# "As issued by the IASB" and the EU/UK endorsement wordings are decisive
# on their own. The bare accordance wording is weaker, because local
# adoptions reuse it ("IFRS as adopted by the Republic of Korea"), so an
# adoption-by-another-jurisdiction match discards the weak evidence and
# never the strong.
_IFRS_STRONG = [
    (
        "IFRS as issued by the IASB",
        re.compile(r"asissuedbytheinternationalaccountingstandardsboard"),
    ),
    ("IFRS as issued by the IASB", re.compile(r"ifrss?asissuedbytheiasb")),
    (
        "IFRS as adopted in the EU",
        re.compile(
            r"(internationalfinancialreportingstandards|ifrss?)"
            r"as(adopted|endorsed)bytheeu(ropeanunion)?"
        ),
    ),
    (
        "UK-adopted international accounting standards",
        re.compile(r"ukadoptedinternationalaccountingstandards"),
    ),
    (
        "IFRS Accounting Standards",
        re.compile(
            r"(accordance|compliance|complies|comply|conformity|conforms)"
            r"with(the)?ifrsaccountingstandards"
        ),
    ),
]
_IFRS_WEAK = [
    (
        "IFRS accordance wording",
        re.compile(
            r"(accordance|compliance|complies|comply|conformity|conforms)"
            r"with(the)?internationalfinancialreportingstandards"
        ),
    ),
    (
        # the declaration form says "prepared in accordance with IFRS"
        # (…根據國際財務報告準則編製); requiring the prepared-anchor within a
        # short gap keeps note prose that merely compares treatments
        # ("under IFRS, such equity is classified as…") and listing-rule
        # boilerplate naming several frameworks from counting as declared
        "IFRS basis-of-preparation wording (Chinese)",
        re.compile(
            r"(按照|根據|根据|遵照|依據|依据)(國際財務報告準則|国际财务报告准则)"
            r".{0,24}(編製|编制|編制|编製)"
        ),
    ),
]
_IFRS_LOCAL_ADOPTION = (
    "IFRS as adopted outside the EU and the UK",
    re.compile(
        r"(internationalfinancialreportingstandards|ifrss?)"
        r"as(adopted|endorsed)by(?!(the)?(eu|europeanunion|uk|unitedkingdom))"
    ),
)
_UNSUPPORTED = [
    (
        # the Chinese form is declaration-anchored like the IFRS pattern
        # above, because Hong Kong listing-rule boilerplate names several
        # acceptable frameworks in one sentence without declaring any
        "Hong Kong Financial Reporting Standards",
        re.compile(
            r"hongkongfinancialreportingstandards"
            r"|(按照|根據|根据|遵照|依據|依据)(香港財務報告準則|香港财务报告准则)"
            r".{0,24}(編製|编制|編制|编製)"
        ),
    ),
    (
        "Japanese GAAP",
        re.compile(
            r"accountingprinciplesgenerallyacceptedinjapan"
            r"|generallyacceptedaccountingprinciplesinjapan|japanesegaap"
        ),
    ),
    (
        "Indian Accounting Standards (Ind AS)",
        re.compile(r"indianaccountingstandards|(accordance|conformity)withindas"),
    ),
    (
        "PRC Accounting Standards for Business Enterprises",
        re.compile(
            r"accountingstandardsforbusinessenterprises|chineseaccountingstandards"
            r"|企業會計準則|企业会计准则"
        ),
    ),
    (
        "Singapore Financial Reporting Standards",
        re.compile(r"singaporefinancialreportingstandards"),
    ),
    ("Australian Accounting Standards", re.compile(r"australianaccountingstandards")),
    (
        "Korean IFRS",
        re.compile(r"koreaninternationalfinancialreportingstandards|koreanifrs"),
    ),
    (
        "Canadian GAAP",
        re.compile(
            r"accountingprinciplesgenerallyacceptedincanada"
            r"|canadiangenerallyacceptedaccountingprinciples"
        ),
    ),
]

_DECLARATION_MARKERS = re.compile(
    r"independentauditor|reportofindependent|auditorsreport|inouropinion"
    r"|basisofpreparation|basisofpresentation|significantaccountingpolicies"
    r"|核數師報告|审计报告|編製基準|编制基准"
)


@dataclass(frozen=True)
class StandardDetection:
    standard: str | None  # "us-gaap" | "ifrs" | None
    evidence: tuple[str, ...]  # page-numbered matches behind the verdict
    unsupported: tuple[str, ...]  # other-framework declarations found
    ambiguous: bool = False  # both supported standards declared


def _condense_with_map(text: str) -> tuple[str, list[int]]:
    """Space-free lowercase text plus, per kept character, its position in
    the original: matching survives the PDFs' fused and split spacing, and
    a match can still be quoted from the original wording as evidence."""
    lowered = text.lower()
    chars: list[str] = []
    positions: list[int] = []
    for index, ch in enumerate(lowered):
        if "a" <= ch <= "z" or "0" <= ch <= "9" or "一" <= ch <= "鿿":
            chars.append(ch)
            positions.append(index)
    return "".join(chars), positions


def _context(text: str, positions: list[int], start: int, end: int) -> str:
    left = positions[start]
    right = positions[end - 1] + 1 if end - 1 < len(positions) else len(text)
    snippet = text[max(0, left - 30) : right + 30]
    return re.sub(r"\s+", " ", snippet).strip()[:130]


def _matches(
    patterns: list[tuple[str, re.Pattern[str]]],
    condensed: str,
    positions: list[int],
    original: str,
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for label, pattern in patterns:
        match = pattern.search(condensed)
        if match:
            found.append(
                (label, _context(original, positions, match.start(), match.end()))
            )
    return found


def detect(page_texts: Sequence[str]) -> StandardDetection:
    """The deterministic scan: us-gaap, ifrs, or None, with evidence.

    Both supported standards declared resolves to None with ambiguous set
    (abstain, never guess). Unsupported-framework declarations are always
    reported; the caller refuses on them only when no supported standard
    is declared, because dual-compliance statements (IFRS alongside a
    converged local framework) are common and legitimate.
    """
    us: list[str] = []
    strong: list[str] = []
    weak: list[str] = []
    unsupported: list[str] = []
    local_adoption = False
    for number, text in enumerate(page_texts, start=1):
        if not text:
            continue
        condensed, positions = _condense_with_map(text)
        if not condensed:
            continue
        for label, context in _matches(_US_GAAP, condensed, positions, text):
            us.append(f'page {number}: {label}: "{context}"')
        for label, context in _matches(_IFRS_STRONG, condensed, positions, text):
            strong.append(f'page {number}: {label}: "{context}"')
        for label, context in _matches(_IFRS_WEAK, condensed, positions, text):
            weak.append(f'page {number}: {label}: "{context}"')
        for label, context in _matches(_UNSUPPORTED, condensed, positions, text):
            unsupported.append(f'page {number}: {label}: "{context}"')
        for label, context in _matches(
            [_IFRS_LOCAL_ADOPTION], condensed, positions, text
        ):
            local_adoption = True
            unsupported.append(f'page {number}: {label}: "{context}"')
    ifrs = strong + ([] if local_adoption else weak)
    if us and ifrs:
        return StandardDetection(
            None, tuple((us + ifrs)[:8]), tuple(unsupported[:4]), ambiguous=True
        )
    if us:
        return StandardDetection("us-gaap", tuple(us[:6]), tuple(unsupported[:4]))
    if ifrs:
        return StandardDetection("ifrs", tuple(ifrs[:6]), tuple(unsupported[:4]))
    return StandardDetection(None, (), tuple(unsupported[:6]))


def mismatches(concept: str, standard: str | None) -> bool:
    """True when a standard-prefixed concept belongs to the other declared
    standard. Firm extensions and document-local slugs carry no standard
    prefix and never mismatch; with no declared standard nothing does."""
    if standard is None:
        return False
    for name, prefix in STANDARD_PREFIX.items():
        if concept.startswith(prefix):
            return name != standard
    return False


def declaration_candidates(
    page_texts: Sequence[str], limit: int = 6, chars: int = 2400
) -> dict[int, str]:
    """Pages likely to state the framework (the auditor's report, the
    basis-of-preparation note): the LLM fallback reads these few pages,
    never the whole document."""
    found: dict[int, str] = {}
    for number, text in enumerate(page_texts, start=1):
        if len(found) >= limit:
            break
        if not text:
            continue
        condensed, _ = _condense_with_map(text)
        if _DECLARATION_MARKERS.search(condensed):
            found[number] = text[:chars]
    return found


def _write_scan_report(out_dir: Path, verdicts: dict[str, Any]) -> None:
    lines = [
        "# Reporting-standard scan (deterministic, no LLM)",
        "",
        "Raw per-page text suffices here: the scan matches condensed",
        "(space-free) forms, so the extraction tolerances that matter to",
        "table reading are immaterial to it.",
        "",
        "| Document | Verdict | First evidence |",
        "| --- | --- | --- |",
    ]
    details: list[str] = []
    for document in sorted(verdicts):
        record = verdicts[document]
        if "error" in record:
            lines.append(f"| {document} | ERROR | {record['error'][:80]} |")
            continue
        if record["standard"]:
            verdict = record["standard"]
        elif record.get("ambiguous"):
            verdict = "ambiguous"
        elif record.get("unsupported"):
            verdict = "UNSUPPORTED (refuse)"
        else:
            verdict = "undeclared"
        first = (record.get("evidence") or record.get("unsupported") or [""])[0]
        lines.append(f"| {document} | {verdict} | {first.replace('|', '/')} |")
        shown = list(record.get("evidence", []))[:3] + list(
            record.get("unsupported", [])
        )[:3]
        if shown:
            details.append(f"## {document}")
            details.extend(f"- {item}" for item in shown)
            details.append("")
    (out_dir / "report.md").write_text(
        "\n".join(lines + ["", *details]), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    """Scan PDFs for their declared standard and record the verdicts under
    out/standard_scan/ (merging with any prior scan), no LLM anywhere."""
    import pdfplumber

    from fss.paths import OUT_DIR

    arguments = sys.argv[1:] if argv is None else argv
    targets: list[Path] = []
    for argument in arguments or [
        str(
            Path("previous_llm_extractor") / "annual_reports" / "for_financial_statements"
        )
    ]:
        path = Path(argument)
        if path.is_dir():
            targets.extend(sorted(path.rglob("*.pdf")))
        elif path.suffix.lower() == ".pdf":
            targets.append(path)
    out_dir = OUT_DIR / "standard_scan"
    out_dir.mkdir(parents=True, exist_ok=True)
    verdict_path = out_dir / "verdicts.json"
    verdicts: dict[str, Any] = (
        json.loads(verdict_path.read_text(encoding="utf-8"))
        if verdict_path.exists()
        else {}
    )
    from fss.untagged import _document_slug

    for pdf_path in targets:
        document = _document_slug(pdf_path)
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                texts = [page.extract_text() or "" for page in pdf.pages]
            detection = detect(texts)
            verdicts[document] = {
                "file": str(pdf_path),
                "pages": len(texts),
                "standard": detection.standard,
                "ambiguous": detection.ambiguous,
                "evidence": list(detection.evidence),
                "unsupported": list(detection.unsupported),
            }
            if detection.standard:
                verdict = detection.standard
            elif detection.ambiguous:
                verdict = "AMBIGUOUS"
            elif detection.unsupported:
                verdict = "UNSUPPORTED (refuse)"
            else:
                verdict = "undeclared"
            print(f"{document}: {verdict}")
        except Exception as exc:  # keep the scan alive; report the failure
            verdicts[document] = {"file": str(pdf_path), "error": f"{type(exc).__name__}: {exc}"}
            print(f"{document}: ERROR {exc}")
    verdict_path.write_text(
        json.dumps(verdicts, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    _write_scan_report(out_dir, verdicts)
    print(f"scan -> {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
