"""The unique-hit taxonomy-label tier: deterministic resolution for labels
that name exactly one concept across both taxonomies, under the same
polarity discipline as every other heuristic source."""
from types import SimpleNamespace

from fss.reconcile import canon_label
from fss.taxlabels import unique_entries
from fss.untagged import ConceptInfo, map_rows


def _reconciled(*rows):
    return SimpleNamespace(
        rows=[SimpleNamespace(label=label, section=section) for label, section in rows]
    )


def _tier(label: str, concept: str, balance: str, period_type: str = "instant"):
    return {
        canon_label(label): ConceptInfo(concept, balance, period_type, True)
    }


def test_unique_entries_drops_ambiguous_labels():
    index = {
        "commercial paper": [
            {
                "concept": "us-gaap:CommercialPaper",
                "balance": "credit",
                "period_type": "instant",
                "monetary": True,
            }
        ],
        "other assets": [
            {
                "concept": "us-gaap:OtherAssetsCurrent",
                "balance": "debit",
                "period_type": "instant",
                "monetary": True,
            },
            {
                "concept": "us-gaap:OtherAssetsNoncurrent",
                "balance": "debit",
                "period_type": "instant",
                "monetary": True,
            },
        ],
    }
    tier = unique_entries(index)
    assert tier["commercial paper"].concept == "us-gaap:CommercialPaper"
    assert "other assets" not in tier


def test_tier_resolves_when_lexicon_and_overlay_miss():
    tier = _tier("Frobnicated liabilities", "us-gaap:FrobnicatedThing", "credit")
    concepts, stats, sources = map_rows(
        "balance_sheet",
        _reconciled(("Frobnicated liabilities", "liabilities")),
        {},
        {},
        None,
        None,
        taxonomy=tier,
    )
    assert concepts[0].concept == "us-gaap:FrobnicatedThing"
    assert sources == {0: "taxonomy"}
    assert stats["taxonomy"] == 1


def test_lexicon_outranks_tier():
    lexicon = {
        canon_label("Total assets"): ConceptInfo(
            "us-gaap:Assets", "debit", "instant", True
        )
    }
    tier = _tier("Total assets", "us-gaap:SomethingElse", "debit")
    concepts, stats, sources = map_rows(
        "balance_sheet",
        _reconciled(("Total assets", "assets")),
        lexicon,
        {},
        None,
        None,
        taxonomy=tier,
    )
    assert concepts[0].concept == "us-gaap:Assets"
    assert sources == {0: "lexical"}
    assert stats["taxonomy"] == 0


def test_carried_overlay_outranks_tier():
    from fss.untagged import _artifact_overlay

    overlay = _artifact_overlay(
        [
            {
                "label": "Frobnicated liabilities",
                "concept": "us-gaap:ReviewedChoice",
                "balance": "credit",
                "period_type": "instant",
            }
        ]
    )
    tier = _tier("Frobnicated liabilities", "us-gaap:GenericChoice", "credit")
    concepts, _, sources = map_rows(
        "balance_sheet",
        _reconciled(("Frobnicated liabilities", "liabilities")),
        {},
        {},
        None,
        None,
        overlay=overlay,
        overlay_source="carried",
        taxonomy=tier,
    )
    assert concepts[0].concept == "us-gaap:ReviewedChoice"
    assert sources == {0: "carried"}


def test_income_statement_polarity_veto_screens_tier_hits():
    tier = _tier("Frobnicated revenue", "us-gaap:MispolarizedThing", "debit", "duration")
    concepts, stats, _ = map_rows(
        "income_statement",
        _reconciled(("Frobnicated revenue", "revenue")),
        {},
        {},
        None,
        None,
        taxonomy=tier,
    )
    assert concepts == {}
    assert stats["unmapped"] == 1
