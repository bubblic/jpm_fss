"""Carry-forward seeding: a prior artifact's reviewed mapping resolves
labels the lexicon misses, under the same polarity discipline."""
from types import SimpleNamespace

from fss.reconcile import canon_label
from fss.untagged import ConceptInfo, _artifact_overlay, map_rows


def _reconciled(*rows):
    return SimpleNamespace(
        rows=[SimpleNamespace(label=label, section=section) for label, section in rows]
    )


def _overlay(label: str, concept: str, balance: str, period_type: str = "instant"):
    return _artifact_overlay(
        [
            {
                "label": label,
                "concept": concept,
                "balance": balance,
                "period_type": period_type,
            }
        ]
    )


def test_carried_overlay_resolves_lexicon_miss():
    overlay = _overlay(
        "Frobnicated receivables", "us-gaap:ReceivablesNetCurrent", "debit"
    )
    concepts, stats, sources = map_rows(
        "balance_sheet",
        _reconciled(("Frobnicated receivables", "assets")),
        {},
        {},
        None,
        None,
        overlay=overlay,
        overlay_source="carried",
    )
    assert concepts[0].concept == "us-gaap:ReceivablesNetCurrent"
    assert sources == {0: "carried"}
    assert stats["carried"] == 1 and stats["llm"] == 0


def test_carried_entry_still_faces_balance_sheet_polarity_veto():
    overlay = _overlay("Accounts payable", "us-gaap:MispolarizedThing", "debit")
    concepts, stats, _ = map_rows(
        "balance_sheet",
        _reconciled(("Accounts payable", "liabilities")),
        {},
        {},
        None,
        None,
        overlay=overlay,
        overlay_source="carried",
    )
    assert concepts == {}
    assert stats["unmapped"] == 1


def test_lexicon_outranks_carried_overlay():
    lexicon = {
        canon_label("Total assets"): ConceptInfo(
            "us-gaap:Assets", "debit", "instant", True
        )
    }
    overlay = _overlay("Total assets", "us-gaap:SomethingElse", "debit")
    concepts, stats, sources = map_rows(
        "balance_sheet",
        _reconciled(("Total assets", "assets")),
        lexicon,
        {},
        None,
        None,
        overlay=overlay,
        overlay_source="carried",
    )
    assert concepts[0].concept == "us-gaap:Assets"
    assert sources == {0: "lexical"}
    assert stats["carried"] == 0


def test_statement_scoped_lexicon_prefers_flow_concepts_on_cash_flow():
    from fss.untagged import _load_dictionary

    global_dict, by_statement, _ = _load_dictionary()
    key = canon_label("Inventories")
    assert global_dict[key].concept == "us-gaap:InventoryNet"
    assert (
        by_statement["cash_flow"][key].concept
        == "us-gaap:IncreaseDecreaseInInventories"
    )


def test_snap_validates_llm_page_picks():
    """LLM page picks face a density bar: a proposed page number cannot
    smuggle in a sparse page."""
    from fss.untagged import _snap_llm_pages

    pages = [
        SimpleNamespace(value_rows=0, text="prose page"),
        SimpleNamespace(value_rows=30, text="total assets\n1,234"),
        SimpleNamespace(value_rows=1, text="notes"),
    ]
    assert _snap_llm_pages([2], pages, {}, "balance_sheet") == [1]
    assert _snap_llm_pages([1, 3], pages, {}, "balance_sheet") == []


def test_runtime_overlay_source_defaults_to_artifact():
    overlay = _overlay(
        "Frobnicated receivables", "us-gaap:ReceivablesNetCurrent", "debit"
    )
    _, stats, sources = map_rows(
        "balance_sheet",
        _reconciled(("Frobnicated receivables", "assets")),
        {},
        {},
        None,
        None,
        overlay=overlay,
    )
    assert sources == {0: "artifact"}
    assert stats["artifact"] == 1
