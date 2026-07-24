"""The unified CLI must scrub sys.argv before calling subcommand mains
that read argv for company keys (the subcommand token is not a key)."""
import sys

import fss.cli as cli


def test_cli_scrubs_argv_for_measure(monkeypatch):
    import fss.measure as measure

    seen: dict[str, list[str]] = {}
    monkeypatch.setattr(
        measure, "main", lambda: seen.setdefault("argv", list(sys.argv))
    )
    monkeypatch.setattr(sys, "argv", ["fss", "measure"])
    assert cli.main() == 0
    assert seen["argv"] == ["measure"]


def test_cli_scrubs_argv_for_extract(monkeypatch):
    import fss.tagread as tagread

    seen: dict[str, list[str]] = {}
    monkeypatch.setattr(
        tagread, "main", lambda: seen.setdefault("argv", list(sys.argv))
    )
    monkeypatch.setattr(sys, "argv", ["fss", "extract"])
    assert cli.main() == 0
    assert seen["argv"] == ["extract"]
