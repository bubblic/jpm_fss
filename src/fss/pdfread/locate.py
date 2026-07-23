"""Locate the pages of each core statement inside a filing PDF.

Pure-PDF logic: generic title vocabulary (no tag-path metadata), a
value-row density requirement that rejects index and auditor pages, an
anchor row the true statement must contain ("Total assets", "operating
activities"), and terminal-anchored continuation so statements spanning
pages are captured whole.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fss.pdfread.rows import split_trailing_values

TITLE_HINTS: dict[str, tuple[str, ...]] = {
    "balance_sheet": (
        "balance sheet",
        "statement of financial position",
        "statements of financial position",
        "statement of financial condition",  # banks and broker-dealers
        "statements of financial condition",
        "資產負債表",  # HK/PRC reports carry a Chinese-language section
        "资产负债表",
        "財務狀況表",
        "财务状况表",
    ),
    "income_statement": (
        "statement of operations",
        "statements of operations",
        "income statement",
        "income statements",
        "statement of income",
        "statements of income",
        "statement of profit or loss",  # IFRS wording common in HK/EU reports
        "statements of profit or loss",
        "利潤表",
        "利润表",
        "損益表",
        "损益表",
        "收益表",
    ),
    "cash_flow": (
        "statement of cash flows",
        "statements of cash flows",
        "cash flows statement",
        "cash flow statement",  # European singular wording (LVMH, VW)
        "statement of cash flow",
        "現金流量表",
        "现金流量表",
    ),
}
TITLE_VETO: dict[str, tuple[str, ...]] = {
    "balance_sheet": ("parenthetical",),
    "income_statement": ("parenthetical", "comprehensive"),
    "cash_flow": ("parenthetical",),
}
ANCHORS: dict[str, re.Pattern[str]] = {
    "balance_sheet": re.compile(
        r"^total ?assets\b|資產總額|资产总额|總資產|总资产", re.IGNORECASE | re.MULTILINE
    ),
    "income_statement": re.compile(
        r"per ?share|income ?tax|profit ?before ?tax|每股|所得稅|所得税", re.IGNORECASE
    ),
    "cash_flow": re.compile(r"operating ?activities|經營活動|经营活动", re.IGNORECASE),
}
TERMINALS: dict[str, re.Pattern[str]] = {
    "balance_sheet": re.compile(
        r"total (equity and liabilities|liabilities and (shareholders|stockholders|equity))"
        r"|負債及權益總額|负债及权益总额",
        re.IGNORECASE,
    ),
    "income_statement": re.compile(r"\bdiluted\b", re.IGNORECASE),
    "cash_flow": re.compile(
        r"(cash .*end of (the )?(year|period))|supplemental", re.IGNORECASE
    ),
}
TOP_LINES = 8
MIN_VALUE_ROWS = 6
MAX_CONTINUATIONS = 4  # HK balance sheets run four pages
ANY_TITLE = re.compile(
    r"balance sheet|statements? of financial (position|condition)|income statements?|"
    r"statements? of (operations|income|earnings)|statements? of profit or loss|"
    r"cash flows? statements?|"
    r"statements? of cash flows|statements? of (stockholders|shareholders|changes in)"
    r"|comprehensive income",
    re.IGNORECASE,
)


def _title_candidates(lines: list[str]) -> list[tuple[int, str]]:
    """(line index, condensed text) for each line and each adjacent pair.

    Narrow layouts wrap statement titles across lines ("CONSOLIDATED
    STATEMENT OF PROFIT OR" / "LOSS"); joining neighbours lets the hints
    match the wrapped form. Index reported is the first line's.
    """
    squeezed = [_squeeze(line) for line in lines]
    candidates: list[tuple[int, str]] = []
    for index, text in enumerate(squeezed):
        if text and len(text) <= 100:
            candidates.append((index, text))
        if (
            text
            and index + 1 < len(squeezed)
            and squeezed[index + 1]
            and len(text) + len(squeezed[index + 1]) <= 110
        ):
            candidates.append((index, text + squeezed[index + 1]))
    return candidates


def _hint_match(text: str, statement: str) -> bool:
    hints = tuple(_squeeze(h) for h in TITLE_HINTS[statement])
    vetos = tuple(_squeeze(v) for v in TITLE_VETO[statement])
    if any(v in text for v in vetos):
        # HK/IFRS filers COMBINE the statements: "statement of profit or
        # loss and other comprehensive income" IS the income statement
        if not (statement == "income_statement" and "profitorloss" in text):
            return False
    return any(h in text for h in hints)


def _title_line_index(info: "PageInfo", statement: str) -> int | None:
    """Line index of this statement's title on the page, if present."""
    for index, text in _title_candidates(info.lines):
        if _hint_match(text, statement):
            return index
    return None


def crop_region(info: "PageInfo", statement: str) -> tuple[int, int]:
    """(start_line, end_line) bounding this statement's region on the page.

    The region runs from this statement's title (or the page top when the
    statement continues from a prior page) to the next different statement
    title, so a page carrying two statements feeds the readers only one.
    The scan starts two lines below the title (the line directly under it
    can be the WRAPPED REMAINDER of this statement's own title, e.g.
    "...PROFIT OR" / "LOSS AND OTHER COMPREHENSIVE INCOME") and considers
    adjacent line pairs so wrapped titles of the next statement stop the
    region too.
    """
    start = _title_line_index(info, statement)
    begin = start if start is not None else 0
    end = len(info.lines)
    lowered_lines = [" ".join(line.lower().split()) for line in info.lines]
    hints = TITLE_HINTS[statement]
    for index in range(begin + 2, len(info.lines)):
        candidates = [lowered_lines[index]]
        if index + 1 < len(info.lines):
            candidates.append(lowered_lines[index] + " " + lowered_lines[index + 1])
        stop = False
        for text in candidates:
            if not text or len(text) > 110:
                continue
            if ANY_TITLE.search(text) and not any(h in text for h in hints):
                stop = True
                break
        if stop:
            end = index
            break
    return begin, end


@dataclass
class PageInfo:
    index: int
    text: str
    lines: list[str]
    value_rows: int
    text_options: dict[str, float] | None = None

    def top_lines(self) -> list[str]:
        return [line for line in self.lines if line.strip()][:TOP_LINES]


_INVISIBLE_TR = re.compile(rb"\b[37]\s+Tr\b")  # text rendering modes 3 and 7


def _content_stream_bytes(page: Any) -> bytes:
    """The page's decoded content stream(s); empty on any failure."""
    from pdfminer.pdftypes import resolve1

    contents = getattr(page.page_obj, "contents", None)
    if contents is None:
        return b""
    if not isinstance(contents, list):
        contents = [contents]
    data = b""
    for ref in contents:
        try:
            data += resolve1(ref).get_data()
        except Exception:
            continue
    return data


def authored_text_issues(page: Any) -> list[str]:
    """Mechanical born-digital check for one statement page.

    The scope gate is AUTHORED text, not merely present text: an OCR'd
    scan carries a text layer (invisible glyphs, rendering mode 3, laid
    over a full-page raster), so it would pass a naive has-text check
    while feeding every text-consuming reader from the single OCR error
    source. The decisive signature is the combination of a page-dominating
    image XObject with absent or invisible text; font embeddedness alone
    is deliberately NOT a hard signal, because authored documents set in
    the standard-14 fonts (older filings) carry no embedded fonts and are
    perfectly fine. Returns a list of issues; empty means authored.
    """
    issues: list[str] = []
    area = float(page.width) * float(page.height)
    coverage = 0.0
    for image in page.images:
        width = float(image["x1"]) - float(image["x0"])
        height = float(image["bottom"]) - float(image["top"])
        if area > 0:
            coverage = max(coverage, (width * height) / area)
    text = (page.extract_text() or "").strip()
    if coverage >= 0.8:
        if len(text) < 200:
            issues.append(
                "page-dominating raster image with little or no text (scanned page)"
            )
        elif _INVISIBLE_TR.search(_content_stream_bytes(page)):
            issues.append(
                "page-dominating raster image with an invisible text overlay (OCR layer)"
            )
    elif not text and not page.chars:
        issues.append("no extractable text on the page")
    return issues


def _value_row_count(lines: list[str]) -> int:
    count = 0
    for line in lines:
        _, values = split_trailing_values(line.split())
        if len([v for v in values if v.value is not None]) >= 2:
            count += 1
    return count


def probe_text_options(pdf: Any) -> dict[str, float]:
    """Choose extraction tolerances for this document.

    Some PDFs carry no space glyphs and rely on kerning; at the default
    tolerance their words fuse ("CONSOLIDATEDBALANCESHEET"). When sampled
    pages show almost no spaces, drop to a tight tolerance so gaps become
    word breaks again.
    """
    samples = [pdf.pages[i] for i in range(0, len(pdf.pages), max(1, len(pdf.pages) // 6))][:6]
    characters = spaces = 0
    for page in samples:
        text = page.extract_text() or ""
        characters += len(text)
        spaces += text.count(" ")
    if characters and spaces / characters < 0.05:
        return {"x_tolerance": 1.2}
    return {}


_COMMON_WORDS = frozenset(
    """the and of in for to from net total cash income statement statements assets
    liabilities equity revenue revenues cost costs expense expenses tax taxes shares
    share year years december january june march notes note other current deferred
    long short term interest operating investing financing activities balance sheet
    flow flows stock common preferred capital earnings retained value fair per
    millions thousands dollars euros accounts receivable payable inventories goodwill
    property plant equipment debt loss gain gains accrued paid change changes
    beginning end period consolidated company group accumulated depreciation""".split()
)


def _fusion_score(text: str) -> float:
    """Word-recognition score used to pick the best de-fusing tolerance.

    Space-ratio alone cannot arbitrate: over-splitting also raises it. Real
    words rise, one-to-two-letter shards sink.
    """
    tokens = re.findall(r"[A-Za-z]+", text)
    if not tokens:
        return 0.0
    hits = sum(1 for token in tokens if token.lower() in _COMMON_WORDS)
    shards = sum(1 for token in tokens if len(token) <= 2)
    return hits - 0.5 * shards


def page_text_with_repair(
    page: Any, base_options: dict[str, float] | None
) -> tuple[str, dict[str, float] | None]:
    """Extract one page, re-extracting at tighter tolerances when fused.

    Fusion is often PER PAGE (a filing whose statement pages are set tighter
    than its notes), so the document-level probe is not enough: each page
    with almost no spaces gets its own tolerance sweep, scored by word
    recognition. Returns the text and the options that produced it (None
    when the document-level options were kept).
    """
    options = dict(base_options or {})
    text = page.extract_text(**options) or ""
    alpha = sum(ch.isalpha() for ch in text)
    if alpha < 200 or text.count(" ") / max(len(text), 1) >= 0.06:
        return text, (base_options or None)
    best = (_fusion_score(text), text, base_options or None)
    for tolerance in (2.0, 1.5, 1.2, 1.0):
        candidate_options = {**options, "x_tolerance": tolerance}
        candidate = page.extract_text(**candidate_options) or ""
        score = _fusion_score(candidate)
        if score > best[0]:
            best = (score, candidate, candidate_options)
    return best[1], best[2]


def scan_pages(pdf: Any, text_options: dict[str, float] | None = None) -> list[PageInfo]:
    options = probe_text_options(pdf) if text_options is None else text_options
    pages: list[PageInfo] = []
    for index, page in enumerate(pdf.pages):
        text, page_options = page_text_with_repair(page, options)
        lines = text.splitlines()
        pages.append(
            PageInfo(index, text, lines, _value_row_count(lines), page_options)
        )
    return pages


_LIGATURES = str.maketrans(
    {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st"}
)


def _squeeze(text: str) -> str:
    return "".join(text.translate(_LIGATURES).lower().split())


def _title_hit(info: PageInfo, statement: str) -> bool:
    """Title match, tolerant of PDFs whose space glyphs vanish
    ("CONSOLIDATEDBALANCESHEET") and of titles wrapped across lines:
    hints compare in condensed form over lines and adjacent pairs."""
    for _, text in _title_candidates(info.top_lines()):
        if _hint_match(text, statement):
            return True
    return False


def _other_title_hit(info: PageInfo, statement: str) -> bool:
    return any(
        _title_hit(info, other) for other in TITLE_HINTS if other != statement
    )


def crop_texts(info: PageInfo, statement: str) -> tuple[str | None, str | None]:
    """(start_anchor, stop_anchor) line texts bounding the statement region."""
    begin, end = crop_region(info, statement)
    start_text = info.lines[begin].strip() if begin > 0 or _title_line_index(info, statement) == 0 else None
    if _title_line_index(info, statement) is None:
        start_text = None  # continuation page: start at the top
    stop_text = info.lines[end].strip() if end < len(info.lines) else None
    return start_text, stop_text


def _expand_run(pages: list[PageInfo], statement: str, best: PageInfo) -> list[int]:
    """One start page extended into its full statement run."""
    chosen = [best.index]
    # statements printed across pages often repeat the title on every page:
    # take the whole contiguous title-hit run around the best page
    cursor = best.index - 1
    while cursor >= 0 and pages[cursor].value_rows >= 3 and _title_hit(pages[cursor], statement):
        chosen.insert(0, cursor)
        cursor -= 1
    begin, end = crop_region(best, statement)
    terminal_seen = bool(TERMINALS[statement].search("\n".join(best.lines[begin:end])))
    cursor = chosen[-1]
    while not terminal_seen and len(chosen) <= MAX_CONTINUATIONS:
        cursor += 1
        if cursor >= len(pages):
            break
        info = pages[cursor]
        ends_here = not _title_hit(info, statement) and _other_title_hit(info, statement)
        region_begin, region_end = crop_region(info, statement)
        region = info.lines[region_begin:region_end]
        if _value_row_count(region) < 3:
            break
        chosen.append(info.index)
        terminal_seen = bool(TERMINALS[statement].search("\n".join(region)))
        if ends_here:
            # the next statement's title is on this page: this statement's
            # tail above that title still belongs to it (cropping bounds
            # the region), but nothing continues past this page
            break
    return chosen


def candidate_runs(
    pages: list[PageInfo], statement: str, top: int = 6
) -> list[tuple[float, list[int]]]:
    """Scored candidate page-runs for one statement, best first.

    Runs are scored on the evidence of the WHOLE run (a section-divider
    page that merely carries the title contributes nothing; the dense face
    pages behind a proper start dominate), plus an anchor bonus when the
    statement's own vocabulary appears anywhere in the run.
    """
    starts: list[PageInfo] = [
        info
        for info in pages
        if info.value_rows >= MIN_VALUE_ROWS and _title_hit(info, statement)
    ]
    runs: list[tuple[float, list[int]]] = []
    seen: set[tuple[int, ...]] = set()
    for info in starts:
        run = _expand_run(pages, statement, info)
        key = tuple(run)
        if key in seen:
            continue
        seen.add(key)
        density = sum(pages[i].value_rows for i in run) / max(len(run), 1)
        anchored = any(ANCHORS[statement].search(pages[i].text) for i in run)
        runs.append((density + (10.0 if anchored else 0.0), run))
    runs.sort(key=lambda item: (-item[0], item[1][0]))
    return runs[:top]


def _span_gap(a: list[int], b: list[int]) -> int:
    return max(a[0] - b[-1], b[0] - a[-1], 0)


def assign_statements(pages: list[PageInfo]) -> dict[str, list[int]]:
    """Choose one run per statement jointly rather than greedily.

    The three statements of an annual report sit within a few pages of each
    other. A lone summary table elsewhere can outscore the real statement
    on local evidence (density, anchors); it cannot also bring the other
    two statements with it. Score = run scores + adjacency bonuses - a
    heavy penalty for two statements claiming a page that does not carry
    both titles (same-page layouts are fine: cropping separates them).
    """
    statements = list(TITLE_HINTS)
    runs = {s: candidate_runs(pages, s) for s in statements}
    from itertools import product

    best_pick: dict[str, list[int]] = {}
    best_score: float | None = None
    options: list[list[tuple[float, list[int]] | None]] = [
        list(runs[s]) or [None] for s in statements
    ]
    for combo in product(*options):
        picked = {
            s: item for s, item in zip(statements, combo) if item is not None
        }
        total = sum(score for score, _ in picked.values())
        names = list(picked)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                run_i, run_j = picked[names[i]][1], picked[names[j]][1]
                gap = _span_gap(run_i, run_j)
                if gap <= 6:
                    total += 12.0
                elif gap <= 15:
                    total += 4.0
                for shared in set(run_i) & set(run_j):
                    info = pages[shared]
                    if _title_hit(info, names[i]) and _title_hit(info, names[j]):
                        continue
                    total -= 60.0
        if best_score is None or total > best_score:
            best_score = total
            best_pick = {s: run for s, (_, run) in picked.items()}
    return best_pick


def locate_statement(pages: list[PageInfo], statement: str) -> list[int]:
    """Single-statement compatibility wrapper over the joint assignment."""
    assigned = assign_statements(pages).get(statement)
    if not assigned:
        raise RuntimeError(f"could not locate {statement} pages")
    return assigned
