"""Static configuration: the test-set registry and numeric policy.

Nothing here contains financial data; company entries are identifiers only.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Company:
    key: str  # short handle used in paths and reports
    name: str
    cik: str  # zero-padded, 10 digits
    form: str  # annual report form type on EDGAR
    standard: str  # "us-gaap" or "ifrs"


COMPANIES: dict[str, Company] = {
    "apple": Company("apple", "Apple Inc.", "0000320193", "10-K", "us-gaap"),
    "microsoft": Company("microsoft", "Microsoft Corporation", "0000789019", "10-K", "us-gaap"),
    "sap": Company("sap", "SAP SE", "0001000184", "20-F", "ifrs"),
    "spotify": Company("spotify", "Spotify Technology S.A.", "0001639920", "20-F", "ifrs"),
}

US_GAAP_KEYS = tuple(k for k, c in COMPANIES.items() if c.standard == "us-gaap")
IFRS_KEYS = tuple(k for k, c in COMPANIES.items() if c.standard == "ifrs")

# Reconciliation policy.
MIN_READER_AGREEMENT = 2  # accepted value needs at least this many agreeing readers
ROUNDING_HALF = Decimal("0.5")  # tolerance = 0.5 * step * (n_addends + 1)

# Simulation policy (documented in the proposal; all rates are annual).
MONTE_CARLO_PATHS = 500
RANDOM_SEED = 20260706
REVENUE_SIGMA = Decimal("0.03")  # noise std dev on revenue growth
MARGIN_SIGMA = Decimal("0.01")  # noise std dev on gross-margin ratio
OPEX_SIGMA = Decimal("0.01")  # noise std dev on opex growth
