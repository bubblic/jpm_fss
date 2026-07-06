"""Run manifest and audit primitives.

Every acceptance run records exactly what it consumed and produced:
input file hashes, package versions, configuration, and the random seed,
so any number in any output can be reproduced bit for bit.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tool_versions() -> dict[str, str]:
    import arelle.Version
    import networkx
    import pdfplumber
    import pypdf
    import requests

    import fss

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "fss": fss.__version__,
        "arelle": arelle.Version.version,
        "networkx": networkx.__version__,
        "pdfplumber": pdfplumber.__version__,
        "pypdf": pypdf.__version__,
        "requests": requests.__version__,
    }


def write_manifest(path: Path, inputs: dict[str, Path], extra: dict[str, Any]) -> None:
    payload = {
        "inputs": {
            name: {"path": str(file), "sha256": sha256_of(file)}
            for name, file in sorted(inputs.items())
        },
        "tools": tool_versions(),
        **extra,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
