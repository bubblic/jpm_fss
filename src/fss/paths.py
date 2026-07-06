"""Shared filesystem locations for FSS."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "out"
FILINGS_DIR = DATA_DIR / "filings"
PDF_DIR = DATA_DIR / "pdf"
ARELLE_CACHE_DIR = DATA_DIR / "arelle_cache"
ACCEPT_DIR = OUT_DIR / "acceptance"
