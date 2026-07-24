"""Taxonomy-label tier for the untagged concept mapper.

Build: python -m fss.taxlabels

Walks the US GAAP and IFRS taxonomies (through the cached Apple and SAP
filings, whose DTSes carry them) and writes data/taxonomy_labels.json:
every standard concept's label, keyed by the same canonical and condensed
forms the lexicon uses, with the attributes the polarity veto needs.

At mapping time only the UNIQUE entries participate: a label that names
exactly one concept across both taxonomies resolves deterministically
("Commercial paper"); a label the taxonomies reuse ("Other assets" and
its dozens of variants) stays ambiguous and falls through to the model
or the flag. The index is a local build product under data/ (like the
rest of the caches); when the file is absent the tier is simply inactive
and mapping behaves exactly as before.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from fss.config import COMPANIES
from fss.edgar import latest_annual
from fss.paths import DATA_DIR

INDEX_PATH = DATA_DIR / "taxonomy_labels.json"
STANDARD_PREFIXES = ("us-gaap:", "ifrs-full:")


def _entry_points() -> list[str]:
    """The standard setters' own full entry points, with their label
    linkbases, at the exact versions the validation filings pin.

    A filer's DTS carries labels only for the concepts the filer uses, so
    the full label set must come from the taxonomy's own entry point; the
    URL is derived from the schema URL the filer's DTS already imports,
    never guessed from memory."""
    import re

    from fss.xbrl import load_model

    entries: list[str] = []
    for key, pattern, template in (
        (
            "apple",
            r"us-gaap/(\d{4})/elts/us-gaap-\d{4}\.xsd$",
            "https://xbrl.fasb.org/us-gaap/{0}/entire/us-gaap-entryPoint-std-{0}.xsd",
        ),
        (
            "sap",
            r"taxonomy/(\d{4}-\d{2}-\d{2})/full_ifrs/full_ifrs-cor_",
            "https://xbrl.ifrs.org/taxonomy/{0}/full_ifrs_entry_point_{0}.xsd",
        ),
    ):
        filing = latest_annual(COMPANIES[key])
        model = load_model(filing.primary_path)
        version = None
        for url in model.urlDocs:
            found = re.search(pattern, url)
            if found:
                version = found.group(1)
                break
        model.close()
        if version is None:
            sys.exit(f"{key}: no standard schema URL matching {pattern!r} in the DTS")
        entries.append(template.format(version))
    return entries


def build_index() -> dict[str, list[dict[str, Any]]]:
    from fss.reconcile import canon_label
    from fss.untagged import _condensed
    from fss.xbrl import load_model

    merged: dict[str, dict[str, dict[str, Any]]] = {}
    for entry_point in _entry_points():
        print(f"loading {entry_point}")
        model = load_model(entry_point, allow_network=True)
        count = 0
        for qname, concept in model.qnameConcepts.items():
            name = str(qname)
            if not name.startswith(STANDARD_PREFIXES):
                continue
            if concept.isAbstract or concept.periodType is None:
                continue
            label = concept.label(fallbackToQname=False)
            if not label:
                continue
            entry = {
                "concept": name,
                "balance": concept.balance or "",
                "period_type": concept.periodType,
                "monetary": bool(concept.isMonetary),
            }
            for form in (canon_label(label), _condensed(label)):
                if form:
                    merged.setdefault(form, {})[name] = entry
            count += 1
        print(f"{entry_point.rsplit('/', 1)[-1]}: indexed {count} standard concepts")
        model.close()
    index = {form: sorted(by_concept.values(), key=lambda e: e["concept"])
             for form, by_concept in merged.items()}
    INDEX_PATH.write_text(json.dumps(index, indent=0), encoding="utf-8")
    unique = sum(1 for entries in index.values() if len(entries) == 1)
    print(f"wrote {INDEX_PATH}: {len(index)} label forms, {unique} unique")
    return index


def unique_entries(index: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """The deterministic tier: label forms naming exactly one concept.

    Returns label form -> ConceptInfo. Ambiguous forms are dropped here,
    which is the entire safety argument of the tier: it can only ever
    assert a mapping no other standard concept shares a label with.
    """
    from fss.untagged import ConceptInfo

    tier: dict[str, Any] = {}
    for form, entries in index.items():
        if len(entries) != 1:
            continue
        entry = entries[0]
        tier[form] = ConceptInfo(
            entry["concept"], entry["balance"], entry["period_type"], entry["monetary"]
        )
    return tier


def load_unique() -> dict[str, Any]:
    """Load the tier from the local index; empty (tier inactive) if absent."""
    if not INDEX_PATH.exists():
        return {}
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return unique_entries(index)


def main() -> None:
    build_index()
    return None


if __name__ == "__main__":
    sys.exit(main())
