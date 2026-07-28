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


def test_cli_passes_standard_flag_through_to_untagged(monkeypatch):
    import fss.untagged as untagged_module

    seen: dict[str, object] = {}

    def _capture(mode):
        seen["mode"] = mode
        seen["argv"] = list(sys.argv)

    monkeypatch.setattr(untagged_module, "main", _capture)
    monkeypatch.setattr(
        sys, "argv", ["fss", "onboard", "--standard", "ifrs", "doc.pdf"]
    )
    assert cli.main() == 0
    assert seen["mode"] == "onboard"
    assert seen["argv"] == ["onboard", "--standard", "ifrs", "doc.pdf"]


def test_untagged_main_rejects_an_unknown_standard(monkeypatch):
    import pytest

    import fss.untagged as untagged_module

    monkeypatch.setattr(sys, "argv", ["onboard", "--standard", "hkfrs"])
    with pytest.raises(SystemExit, match="supported: us-gaap, ifrs"):
        untagged_module.main(mode="onboard")
