"""Load the cached filing with Arelle and expose the taxonomy as a graph.

Nodes are DTS item concepts (qname, periodType, balance, isMonetary, label);
edges are calculation arcs, calc 1.0 and calc 1.1 merged, with weights.

Debug entry point: python -m spike.graph
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from arelle import Cntlr, XbrlConst
from arelle.ModelXbrl import ModelXbrl

from spike.paths import ARELLE_CACHE_DIR, OUT_DIR

GRAPHML_PATH = OUT_DIR / "graph.graphml"
# Sample concepts for the report table; all exist in the us-gaap taxonomy.
SAMPLE_QNAMES = (
    "us-gaap:Assets",
    "us-gaap:Liabilities",
    "us-gaap:StockholdersEquity",
    "us-gaap:CashAndCashEquivalentsAtCarryingValue",
    "us-gaap:AccountsPayableCurrent",
)


@dataclass(frozen=True)
class GraphStats:
    concepts: int
    calc_edges: int
    labeled_concepts: int
    sample: list[tuple[str, str, str]]  # (qname, periodType, balance)


def load_model(filing_path: Path, allow_network: bool = False) -> ModelXbrl:
    """Load the inline-XBRL document; the DTS resolves via data/arelle_cache."""
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


def build_graph(model: ModelXbrl) -> nx.DiGraph:
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


def graph_stats(graph: nx.DiGraph) -> GraphStats:
    labeled = sum(1 for _, data in graph.nodes(data=True) if data["label"])
    sample_qnames = [q for q in SAMPLE_QNAMES if graph.has_node(q)]
    if len(sample_qnames) < len(SAMPLE_QNAMES):
        for qname in sorted(graph.nodes):
            if graph.nodes[qname]["balance"] and qname not in sample_qnames:
                sample_qnames.append(qname)
            if len(sample_qnames) == len(SAMPLE_QNAMES):
                break
    sample = [
        (q, graph.nodes[q]["periodType"] or "(none)", graph.nodes[q]["balance"] or "(none)")
        for q in sample_qnames
    ]
    return GraphStats(graph.number_of_nodes(), graph.number_of_edges(), labeled, sample)


def export_graphml(graph: nx.DiGraph, path: Path = GRAPHML_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, str(path))


def main() -> None:
    from spike import fetch

    filing = fetch.main()
    model = load_model(filing.primary_path)
    graph = build_graph(model)
    export_graphml(graph)
    stats = graph_stats(graph)
    print(f"concepts: {stats.concepts}")
    print(f"calc edges: {stats.calc_edges}")
    print(f"labeled concepts: {stats.labeled_concepts}")
    for qname, period_type, balance in stats.sample:
        print(f"  {qname}: periodType={period_type}, balance={balance}")
    print(f"wrote {GRAPHML_PATH}")


if __name__ == "__main__":
    main()
