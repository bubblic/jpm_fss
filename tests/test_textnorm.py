"""Number parsing and scale policy."""
from decimal import Decimal

from fss.pdfread.textnorm import ScalePolicy, detect_scale, parse_number


def test_plain_and_thousands():
    assert parse_number("35,934").value == Decimal("35934")
    assert parse_number("990").value == Decimal("990")


def test_parenthetical_negative():
    token = parse_number("(14,264)")
    assert token.value == Decimal("-14264")
    assert token.kind == "paren"


def test_minus_and_unicode_minus():
    assert parse_number("-5,480").value == Decimal("-5480")
    assert parse_number("−402").value == Decimal("-402")


def test_dash_is_explicit_empty():
    token = parse_number("—")
    assert token.value is None
    assert token.kind == "dash"


def test_currency_stripped_and_non_numbers_rejected():
    assert parse_number("$35,934").value == Decimal("35934")
    assert parse_number("(A.1),") is None
    assert parse_number("Notes") is None
    assert parse_number("(-3)") is None


def test_decimals():
    assert parse_number("7.49").value == Decimal("7.49")


def test_detect_scale_variants():
    apple = detect_scale(
        "(In millions, except number of shares, which are reflected in "
        "thousands, and par value)"
    )
    assert apple.statement_scale == Decimal(10) ** 6
    assert apple.share_scale == Decimal(10) ** 3
    msft = detect_scale("(In millions) (Unaudited)")
    assert msft.statement_scale == Decimal(10) ** 6
    assert msft.share_scale == Decimal(10) ** 6
    sap = detect_scale("€ millions, unless otherwise stated Notes 2025 2024 2023")
    assert sap.statement_scale == Decimal(10) ** 6
    spotify = detect_scale("(in € millions, except share and per share data)")
    assert spotify.statement_scale == Decimal(10) ** 6
    assert spotify.share_scale == Decimal(1)


def test_scale_for_rows():
    policy = ScalePolicy(Decimal(10) ** 6, Decimal(10) ** 3, "test")
    # monetary equity row that merely mentions shares in its label
    assert (
        policy.scale_for(
            "Common stock and additional paid-in capital, $0.00001 par value: "
            "50,400,000 shares authorized; 14,773,260 and 15,116,786 shares "
            "issued and outstanding, respectively",
            "Shareholders' equity:",
        )
        == Decimal(10) ** 6
    )
    # share-count rows under a shares section
    assert (
        policy.scale_for("Basic", "Shares used in computing earnings per share:")
        == Decimal(10) ** 3
    )
    # per-share rows
    assert policy.scale_for("Basic (in dollars per share)", "") == Decimal(1)
    assert policy.scale_for("Earnings per share, basic (in €)", "") == Decimal(1)
