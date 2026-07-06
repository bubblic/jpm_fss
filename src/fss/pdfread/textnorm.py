"""Numeric token parsing and scale policy for printed statements.

Printed values arrive as text with currency markers, thousands separators,
parenthetical or minus-sign negatives, unicode minus signs, footnote
punctuation, and a statement-level scale header ("In millions ...") with
exceptions for share counts and per-share amounts. Every reader shares this
normalizer so that "agreement" between readers means agreement on the
number, not on typography.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

CURRENCY_MARKS = ("$", "€", "£", "¥")
DASHES = {"—", "–", "-", "−"}
_NUMERIC_BODY = re.compile(r"^\(?[-−]?[0-9][0-9,]*(?:\.[0-9]+)?\)?$")


@dataclass(frozen=True)
class NumToken:
    value: Decimal | None  # None for a bare dash (printed empty/zero marker)
    kind: str  # "plain" | "paren" | "minus" | "dash"
    raw: str


def parse_number(token: str) -> NumToken | None:
    """Parse one whitespace-delimited token; None when it is not a value."""
    raw = token
    text = token.strip()
    for mark in CURRENCY_MARKS:
        text = text.replace(mark, "")
    text = text.strip().rstrip(",;:").strip()
    if not text:
        return None
    if text in DASHES:
        return NumToken(None, "dash", raw)
    if not _NUMERIC_BODY.match(text):
        return None
    kind = "plain"
    if text.startswith("(") and text.endswith(")"):
        kind = "paren"
        text = text[1:-1]
    text = text.replace(",", "")
    negative = kind == "paren"
    if text.startswith("-") or text.startswith("−"):
        if kind == "paren":
            return None  # "(-3)" is not a statement value
        kind = "minus"
        negative = True
        text = text[1:]
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return NumToken(-value if negative else value, kind, raw)


def is_currency_mark(token: str) -> bool:
    return token.strip() in CURRENCY_MARKS


@dataclass(frozen=True)
class ScalePolicy:
    statement_scale: Decimal  # applies to monetary rows
    share_scale: Decimal  # applies to share-count rows
    source: str  # the header text the policy was read from

    def scale_for(self, label: str, section: str) -> Decimal:
        """Resolve the scale for one row from its label and section header.

        Order matters: a share-count section wins over the per-share wording
        it may contain ("Shares used in computing earnings per share"), and
        monetary equity rows that merely mention shares in their label
        ("Common stock ... shares issued and outstanding") are vetoed back
        to the statement scale.
        """
        section_l = section.lower()
        label_l = label.lower()
        if _PER_SHARE_HINT.search(label_l):
            return Decimal(1)
        if _SHARES_SECTION.search(section_l):
            return self.share_scale
        if _MONETARY_VETO.search(label_l):
            return self.statement_scale
        if _SHARE_ROW_HINT.search(label_l):
            return self.share_scale
        if _PER_SHARE_HINT.search(section_l):
            return Decimal(1)
        return self.statement_scale


_SHARES_SECTION = re.compile(
    r"shares used in computing|weighted[\s-]?average.*\bshares\b|\bshares outstanding\b"
)
_PER_SHARE_HINT = re.compile(
    r"per share|per ordinary share|per common share|\(in €\)|\(in eur\)|\(in dollars"
)
_SHARE_ROW_HINT = re.compile(
    r"\bshares?\b.*\b(basic|diluted|issued|outstanding|weighted)\b"
    r"|\b(basic|diluted|weighted)\b.*\bshares?\b"
)
_MONETARY_VETO = re.compile(
    r"common stock|paid-?in capital|par value|treasury|compensation|repurchase|settlement"
)

_SCALE_PATTERNS: tuple[tuple[re.Pattern[str], Decimal], ...] = (
    (re.compile(r"in\s+(?:[€$£]\s*)?millions|[€$£]\s*millions?\b", re.IGNORECASE), Decimal(10) ** 6),
    (re.compile(r"in\s+(?:[€$£]\s*)?thousands|[€$£]\s*thousands?\b", re.IGNORECASE), Decimal(10) ** 3),
    (re.compile(r"in\s+(?:[€$£]\s*)?billions", re.IGNORECASE), Decimal(10) ** 9),
)
_SHARES_IN_THOUSANDS = re.compile(
    r"shares?,?\s*(?:which\s+are\s+|are\s+)?reflected\s+in\s+thousands", re.IGNORECASE
)
_SHARES_EXCEPTED = re.compile(r"except\s+(?:number\s+of\s+)?shares?\b|except\s+share\b", re.IGNORECASE)


def detect_scale(header_text: str) -> ScalePolicy:
    """Read the scale policy from the statement's header block."""
    statement_scale = Decimal(1)
    matched = ""
    for pattern, scale in _SCALE_PATTERNS:
        found = pattern.search(header_text)
        if found:
            statement_scale = scale
            matched = found.group(0)
            break
    if _SHARES_IN_THOUSANDS.search(header_text):
        share_scale = Decimal(10) ** 3
    elif _SHARES_EXCEPTED.search(header_text):
        share_scale = Decimal(1)
    else:
        share_scale = statement_scale
    return ScalePolicy(statement_scale, share_scale, matched or header_text[:80])


def strip_footnote_marks(label: str) -> str:
    """Remove superscript-style footnote digits glued to label words."""
    return re.sub(r"(?<=[a-zA-Z%€)])[0-9](?=[\s,.;:]|$)", "", label)
