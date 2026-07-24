"""EDGAR acquisition and PDF rendering for the FSS test set.

Entry point: python -m fss.edgar   (fetches everything, renders PDFs)

All network access for filings happens here (plus the one-time Arelle DTS
warm-up per filing, triggered from here). Downloads are cached under data/
and never repeated. Every request carries the SEC_USER_AGENT identity and
stays far below the SEC rate limit.

PDF policy: the PDF used by the PDF-only extraction mode is rendered from
the filing's official primary document with headless Microsoft Edge, so the
PDF content is exactly the document the issuer filed. The rendering step is
recorded in the acceptance manifest.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from fss.config import COMPANIES, Company
from fss.paths import ARELLE_CACHE_DIR, DATA_DIR, FILINGS_DIR, PDF_DIR

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}"
REQUEST_GAP_SECONDS = 0.25
FILING_FILE_PATTERN = re.compile(r"\.xsd$|_(cal|def|lab|pre)\.xml$", re.IGNORECASE)
EDGE_CANDIDATES = (
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
)

_last_request = 0.0


@dataclass(frozen=True)
class Filing:
    company: Company
    accession: str  # without dashes
    primary_document: str
    filing_date: str
    report_date: str

    @property
    def directory(self) -> Path:
        return FILINGS_DIR / self.company.key / self.accession

    @property
    def primary_path(self) -> Path:
        return self.directory / self.primary_document

    @property
    def pdf_path(self) -> Path:
        return PDF_DIR / f"{self.company.key}_{self.accession}.pdf"

    @property
    def warm_sentinel(self) -> Path:
        return ARELLE_CACHE_DIR / f".dts_warmed_{self.company.key}_{self.accession}"


def user_agent() -> str:
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
    response = requests.get(url, headers={"User-Agent": user_agent()}, timeout=120)
    _last_request = time.monotonic()
    response.raise_for_status()
    return response.content


def _download(url: str, target: Path) -> bool:
    if target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_get(url))
    return True


def _note(downloaded: bool, what: str) -> None:
    print(("downloaded " if downloaded else "cached     ") + what)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _columnar_rows(payload: dict[str, Any]) -> list[tuple[str, str, str, str, str]]:
    return list(
        zip(
            payload["form"],
            payload["accessionNumber"],
            payload["primaryDocument"],
            payload["filingDate"],
            payload["reportDate"],
        )
    )


def _annual_filings(
    company: Company, include_older: bool = False
) -> list[tuple[str, str, str, str, str]]:
    """(form, accession, primary document, filing date, report date) rows
    for the company's annual form, newest filing first.

    The submissions API's recent window holds roughly the last thousand
    filings; a prolific filer (JPMorgan files thousands of prospectuses a
    year) pushes even last year's annual report out of it, into paged
    older-filings files. Those pages are fetched only when asked for,
    so the common latest-filing path stays exactly as cheap as before."""
    submissions_path = DATA_DIR / f"submissions_CIK{company.cik}.json"
    _note(
        _download(SUBMISSIONS_URL.format(cik=company.cik), submissions_path),
        f"{company.key}: submissions API response",
    )
    payload = _read_json(submissions_path)
    rows = _columnar_rows(payload["filings"]["recent"])
    if include_older:
        for extra in payload["filings"].get("files", []):
            name = extra["name"]
            extra_path = DATA_DIR / name
            _note(
                _download(f"https://data.sec.gov/submissions/{name}", extra_path),
                f"{company.key}: {name}",
            )
            rows.extend(_columnar_rows(_read_json(extra_path)))
    matches = [row for row in rows if row[0] == company.form]
    if not matches:
        sys.exit(f"no {company.form} found for {company.name} (CIK {company.cik})")
    matches.sort(key=lambda row: row[3], reverse=True)
    return matches


def latest_annual(company: Company, offset: int = 0) -> Filing:
    matches = _annual_filings(company)
    if offset >= len(matches):
        sys.exit(
            f"{company.name} has {len(matches)} {company.form} filings in the "
            f"submissions window; offset {offset} is out of range"
        )
    _, accession, primary, filed, period = matches[offset]
    return Filing(company, accession.replace("-", ""), primary, filed, period)


def annual_by_period(company: Company, period_prefix: str) -> Filing:
    """The annual filing whose fiscal period end starts with the prefix
    (e.g. "2022-02" for a fiscal year that ended in February 2022)."""
    matches = [
        row for row in _annual_filings(company) if row[4].startswith(period_prefix)
    ]
    if not matches:
        # not in the recent window; look through the paged older filings
        matches = [
            row
            for row in _annual_filings(company, include_older=True)
            if row[4].startswith(period_prefix)
        ]
    if not matches:
        sys.exit(
            f"no {company.form} with report date {period_prefix}* for {company.name}"
        )
    _, accession, primary, filed, period = matches[0]
    return Filing(company, accession.replace("-", ""), primary, filed, period)


def fetch_filing_files(filing: Filing) -> None:
    base = ARCHIVE_BASE.format(cik_int=int(filing.company.cik), accession=filing.accession)
    index_path = filing.directory / "index.json"
    _note(_download(f"{base}/index.json", index_path), f"{filing.company.key}: file index")
    names = [item["name"] for item in _read_json(index_path)["directory"]["item"]]
    wanted = [
        name
        for name in names
        if name == filing.primary_document or FILING_FILE_PATTERN.search(name)
    ]
    for name in sorted(wanted):
        _note(_download(f"{base}/{name}", filing.directory / name), f"{filing.company.key}: {name}")
    if not filing.primary_path.exists():
        sys.exit(f"primary document missing for {filing.company.key}")


def _edge_binary() -> Path:
    for candidate in EDGE_CANDIDATES:
        if candidate.exists():
            return candidate
    sys.exit("Microsoft Edge not found; cannot render filing PDFs")


def render_pdf(filing: Filing) -> bool:
    """Render the official primary document to PDF with headless Edge."""
    if filing.pdf_path.exists():
        _note(False, f"{filing.company.key}: filing PDF")
        return False
    filing.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(_edge_binary()),
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={filing.pdf_path}",
        filing.primary_path.resolve().as_uri(),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if not filing.pdf_path.exists():
        raise RuntimeError(
            f"Edge failed to render {filing.company.key} PDF: rc={result.returncode} "
            f"stderr={result.stderr[-400:]}"
        )
    _note(True, f"{filing.company.key}: filing PDF ({filing.pdf_path.stat().st_size:,} bytes)")
    return True


def warm_arelle_cache(filing: Filing) -> None:
    """One-time Arelle load per filing so its DTS lands in the local cache."""
    if filing.warm_sentinel.exists():
        _note(False, f"{filing.company.key}: Arelle DTS web cache")
        return
    print(f"{filing.company.key}: loading once with Arelle to pull the DTS...")
    from fss.xbrl import load_model  # lazy: arelle startup is heavy

    model = load_model(filing.primary_path, allow_network=True)
    concepts = len(model.qnameConcepts)
    model.close()
    filing.warm_sentinel.parent.mkdir(parents=True, exist_ok=True)
    filing.warm_sentinel.write_text("dts cache warmed\n", encoding="utf-8")
    _note(True, f"{filing.company.key}: Arelle DTS web cache ({concepts} concepts)")


def acquire(company: Company) -> Filing:
    filing = latest_annual(company)
    print(
        f"{company.key}: {company.form} filed {filing.filing_date}, period "
        f"{filing.report_date}, accession {filing.accession}"
    )
    fetch_filing_files(filing)
    warm_arelle_cache(filing)
    render_pdf(filing)
    return filing


def acquire_all() -> dict[str, Filing]:
    DATA_DIR.mkdir(exist_ok=True)
    return {key: acquire(company) for key, company in COMPANIES.items()}


def main() -> None:
    acquire_all()


if __name__ == "__main__":
    main()
