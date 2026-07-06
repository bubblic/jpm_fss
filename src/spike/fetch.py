"""Fetch Apple's most recent 10-K from EDGAR into the local cache.

Entry point: python -m spike.fetch

Network access happens only in this module (including the one-time Arelle
DTS warm-up it triggers). Every download lands under data/ and cached files
are never re-downloaded.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from spike.paths import ARELLE_CACHE_DIR, DATA_DIR, FILINGS_DIR

CIK = "0000320193"  # Apple Inc.
SUBMISSIONS_URL = f"https://data.sec.gov/submissions/CIK{CIK}.json"
ARCHIVE_BASE = f"https://www.sec.gov/Archives/edgar/data/{int(CIK)}"
REQUEST_GAP_SECONDS = 0.25  # about 4 requests/second, well under the SEC cap of 10
# The extension schema and linkbases sit next to the inline document; with
# these cached locally Arelle resolves the filing side of the DTS offline.
FILING_FILE_PATTERN = re.compile(r"\.xsd$|_(cal|def|lab|pre)\.xml$", re.IGNORECASE)
DTS_WARMED_SENTINEL = ARELLE_CACHE_DIR / ".dts_warmed"

_last_request = 0.0


@dataclass(frozen=True)
class Filing:
    cik: str
    accession: str  # accession number without dashes
    primary_document: str
    filing_date: str
    report_date: str

    @property
    def directory(self) -> Path:
        return FILINGS_DIR / self.accession

    @property
    def primary_path(self) -> Path:
        return self.directory / self.primary_document


def user_agent() -> str:
    """The SEC-required identifying User-Agent, from SEC_USER_AGENT."""
    agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not agent:
        sys.exit(
            "SEC_USER_AGENT is not set; SEC requests must identify the caller.\n"
            'Set it first, e.g.: $env:SEC_USER_AGENT = "Jane Doe jane@example.com"'
        )
    return agent


def _get(url: str) -> bytes:
    global _last_request
    wait = REQUEST_GAP_SECONDS - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    response = requests.get(url, headers={"User-Agent": user_agent()}, timeout=60)
    _last_request = time.monotonic()
    response.raise_for_status()
    return response.content


def _download(url: str, target: Path) -> bool:
    """Fetch url into target unless already cached; True when downloaded."""
    if target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_get(url))
    return True


def _note(downloaded: bool, what: str) -> None:
    print(("downloaded " if downloaded else "cached     ") + what)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_10k(submissions: dict[str, Any]) -> Filing:
    recent = submissions["filings"]["recent"]
    rows = zip(
        recent["form"],
        recent["accessionNumber"],
        recent["primaryDocument"],
        recent["filingDate"],
        recent["reportDate"],
    )
    tenks = [row for row in rows if row[0] == "10-K"]
    if not tenks:
        sys.exit(f"The submissions API lists no 10-K for CIK {CIK}")
    _, accession, primary, filed, period = max(tenks, key=lambda row: row[3])
    return Filing(CIK, accession.replace("-", ""), primary, filed, period)


def fetch_filing() -> Filing:
    submissions_path = DATA_DIR / f"submissions_CIK{CIK}.json"
    _note(_download(SUBMISSIONS_URL, submissions_path), "submissions API response")
    filing = latest_10k(_read_json(submissions_path))
    print(
        f"latest 10-K: filed {filing.filing_date}, period {filing.report_date}, "
        f"accession {filing.accession}, primary document {filing.primary_document}"
    )
    index_path = filing.directory / "index.json"
    _note(_download(f"{ARCHIVE_BASE}/{filing.accession}/index.json", index_path), "filing file index")
    names = [item["name"] for item in _read_json(index_path)["directory"]["item"]]
    wanted = [n for n in names if n == filing.primary_document or FILING_FILE_PATTERN.search(n)]
    for name in sorted(wanted):
        _note(_download(f"{ARCHIVE_BASE}/{filing.accession}/{name}", filing.directory / name), name)
    if not filing.primary_path.exists():
        sys.exit(f"primary document {filing.primary_document} was not downloaded")
    return filing


def warm_arelle_cache(filing: Filing) -> None:
    """One-time Arelle load so the standard taxonomies land under data/.

    This belongs to the fetch step: afterwards pipeline loads run with the
    Arelle web cache in offline mode and never touch the network.
    """
    if DTS_WARMED_SENTINEL.exists():
        _note(False, "Arelle DTS web cache")
        return
    print("loading the filing once with Arelle to pull the DTS (first run only)...")
    from spike.graph import load_model  # imported lazily; arelle startup is heavy

    model = load_model(filing.primary_path, allow_network=True)
    concepts = len(model.qnameConcepts)
    model.close()
    DTS_WARMED_SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    DTS_WARMED_SENTINEL.write_text("dts cache warmed\n", encoding="utf-8")
    _note(True, f"Arelle DTS web cache ({concepts} concepts resolvable)")


def main() -> Filing:
    DATA_DIR.mkdir(exist_ok=True)
    filing = fetch_filing()
    warm_arelle_cache(filing)
    return filing


if __name__ == "__main__":
    main()
