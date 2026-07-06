"""Knowledge-graph services over a filing's discovered taxonomy (DTS).

The graph's nodes are taxonomy concepts carrying the attributes the
simulator relies on (periodType for stock/flow, balance for sign
conventions, monetary flags, labels); its edges are calculation arcs.
This module also provides statement-role discovery and the label index used
by the PDF-only semantic mapper.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
from arelle import XbrlConst
from arelle.ModelXbrl import ModelXbrl

STANDARD_NAMESPACE_MARKERS = ("fasb.org", "xbrl.sec.gov", "xbrl.org", "xbrl.ifrs.org")

# Statement-role text heuristics (lowercased match on the role definition).
ROLE_HINTS: dict[str, tuple[str, ...]] = {
    "balance_sheet": ("balance sheet", "statement of financial position", "statements of financial position"),
    "income_statement": (
        "statement of operations",
        "statements of operations",
        "income statement",
        "income statements",
        "statement of income",
        "statements of income",
        "statement of earnings",
        "statements of earnings",
    ),
    "cash_flow": ("cash flow",),
}
ROLE_EXCLUSIONS: dict[str, tuple[str, ...]] = {
    "balance_sheet": ("parenthetical",),
    "income_statement": ("parenthetical", "comprehensive"),
    "cash_flow": ("parenthetical", "supplement"),
}
# Structural presentation nodes that the renderer does not display as rows.
STRUCTURAL_SUFFIXES = ("Table", "Axis", "Domain", "Member", "LineItems")


def is_filing_defined(role_type: Any) -> bool:
    uri = getattr(role_type.modelDocument, "uri", "") or ""
    return not any(marker in uri for marker in STANDARD_NAMESPACE_MARKERS)


def is_extension_concept(concept: Any) -> bool:
    namespace = concept.qname.namespaceURI or ""
    return not any(marker in namespace for marker in STANDARD_NAMESPACE_MARKERS)


def is_structural(concept: Any) -> bool:
    """True for Table/Axis/Domain/Member/LineItems presentation scaffolding."""
    if getattr(concept, "isDimensionItem", False) or getattr(concept, "isHypercubeItem", False):
        return True
    local = concept.qname.localName
    return any(local.endswith(suffix) for suffix in STRUCTURAL_SUFFIXES)


def find_statement_roles(model: ModelXbrl) -> dict[str, tuple[str, str]]:
    """Locate the three core statement linkroles.

    Returns {statement: (roleURI, definition)}. Filing-defined roles are
    preferred (standard taxonomies ship template roles matching the same
    text), and among survivors the largest presentation tree wins.
    """

    def presentation_size(uri: str) -> int:
        return len(model.relationshipSet(XbrlConst.parentChild, uri).modelRelationships)

    chosen: dict[str, tuple[str, str]] = {}
    for statement, hints in ROLE_HINTS.items():
        exclusions = ROLE_EXCLUSIONS[statement]
        candidates: list[tuple[str, str]] = []
        for uri, role_types in sorted(model.roleTypes.items()):
            for role_type in role_types:
                definition = role_type.definition or ""
                lowered = definition.lower()
                if any(term in lowered for term in exclusions):
                    continue
                if any(hint in lowered for hint in hints):
                    if is_filing_defined(role_type) and presentation_size(uri) > 0:
                        candidates.append((uri, definition))
                    break
        if not candidates:
            raise RuntimeError(f"no filing-defined linkrole found for {statement}")
        uri, definition = max(candidates, key=lambda cand: presentation_size(cand[0]))
        chosen[statement] = (uri, definition)
    return chosen


def normalize_label(text: str) -> str:
    """Canonical form for label comparison across extraction paths."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'").replace("‘", "'")
    text = text.lower()
    # unit and note parentheticals ("(in millions)", "(euro per share)",
    # "(note 7)") vanish; semantic parentheticals ("(expense)") stay
    text = re.sub(
        r"\((?:in )?[^)]*(?:share|€|eur\b|euro|usd|dollar|million|thousand|note)[^)]*\)",
        " ",
        text,
    )
    text = re.sub(r"[^a-z0-9%]+", " ", text)
    return " ".join(text.split())


@dataclass(frozen=True)
class LabelIndex:
    """Normalized label -> candidate concept qnames, from the DTS linkbases."""

    by_label: dict[str, tuple[str, ...]]

    def candidates(self, label: str) -> tuple[str, ...]:
        return self.by_label.get(normalize_label(label), ())


def build_label_index(model: ModelXbrl) -> LabelIndex:
    label_rels = model.relationshipSet(XbrlConst.conceptLabel)
    collected: dict[str, set[str]] = {}
    for rel in label_rels.modelRelationships:
        concept = rel.fromModelObject
        label_obj = rel.toModelObject
        if concept is None or label_obj is None:
            continue
        text = (label_obj.textValue or "").strip()
        if not text:
            continue
        collected.setdefault(normalize_label(text), set()).add(str(concept.qname))
    return LabelIndex({label: tuple(sorted(qnames)) for label, qnames in collected.items()})


def build_graph(model: ModelXbrl) -> nx.DiGraph:
    """Concept graph with calc edges, as in the KG spike."""
    graph = nx.DiGraph()
    for qname, concept in sorted(model.qnameConcepts.items(), key=lambda kv: str(kv[0])):
        if not concept.isItem:
            continue
        label = concept.label(fallbackToQname=False, lang="en-US")
        graph.add_node(
            str(qname),
            qname=str(qname),
            periodType=concept.periodType or "",
            balance=concept.balance or "",
            isMonetary=bool(concept.isMonetary),
            label=label or "",
        )
    for arcrole in XbrlConst.summationItems:
        for rel in model.relationshipSet(arcrole).modelRelationships:
            parent, child = rel.fromModelObject, rel.toModelObject
            if parent is None or child is None:
                continue
            source, target = str(parent.qname), str(child.qname)
            if graph.has_node(source) and graph.has_node(target):
                graph.add_edge(source, target, weight=float(rel.weight))
    return graph


def export_graphml(graph: nx.DiGraph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, str(path))
