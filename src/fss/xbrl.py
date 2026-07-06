"""Arelle model loading with a local, offline-capable web cache."""
from __future__ import annotations

import os
from pathlib import Path

from arelle import Cntlr
from arelle.ModelXbrl import ModelXbrl

from fss.paths import ARELLE_CACHE_DIR


def load_model(filing_path: Path, allow_network: bool = False) -> ModelXbrl:
    """Load an inline-XBRL document; DTS resolution uses data/arelle_cache.

    With allow_network False (the default for every pipeline step other than
    acquisition) the web cache runs in offline mode, so no code path outside
    the fetch step touches the network.
    """
    controller = Cntlr.Cntlr(logFileName="logToStdErr", disable_persistent_config=True)
    controller.webCache.cacheDir = str(ARELLE_CACHE_DIR)
    controller.webCache.workOffline = not allow_network
    agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if agent:
        controller.webCache.httpUserAgent = agent
    model = controller.modelManager.load(str(filing_path))
    if model is None or model.modelDocument is None:
        raise RuntimeError(f"Arelle failed to load {filing_path}")
    return model
