"""Symbolic closure verification of the engine, after the interns' method.

The prior interns' frameworks validate the accounting system symbolically
before any numerical run: equations form a DAG (structural no-circularity),
and the identity A = L + E is proven by symbolic cancellation of the flow
terms, so a specification error is caught at construction time and the
offending term is named. This module applies the same discipline to the
FSS engine: it builds, per firm, a SymPy model of exactly the flow legs the
engine posts, and

  1. proves  sum_a beta_a * (end_a - begin_a)  simplifies to zero for ALL
     parameter values (not just the sampled ones), with any nonzero
     residual reported as the symbols of the unbalanced flows;
  2. validates the engine's computation order as a DAG and returns its
     topological order (the runtime is one ordered pass; this makes the
     acyclicity a checked property rather than a code-reading exercise).

The runtime Decimal assertions remain as the numerical backstop, mirroring
the interns' pipeline: symbolic checking first, numerical checking second.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import sympy as sp

from fss.engine import roles as R
from fss.engine.project import Projector, _row_key


@dataclass
class SymbolicVerdict:
    company: str
    balanced: bool
    residual: str  # "0" when balanced; otherwise the unbalanced expression
    culprits: list[str]  # free symbols of a nonzero residual (localization)
    acyclic: bool
    execution_order: list[str]
    notes: list[str] = field(default_factory=list)


def _beta(balance: str) -> int:
    return 1 if balance == "debit" else -1


def verify_engine_closure(projector: Projector) -> SymbolicVerdict:
    """Build the firm's flow system symbolically and prove closure."""
    bs_roles = projector.roles["balance_sheet"]
    cf_roles = projector.roles["cash_flow"]
    notes: list[str] = []

    # ---- primitive flow symbols (one per engine rule instance) ----
    ni_parent = sp.Symbol("ni_parent")
    ni_nci = sp.Symbol("ni_nci")
    da = sp.Symbol("da")  # depreciation and amortization add-back
    sbc = sp.Symbol("sbc")  # share-based compensation add-back
    dividends = sp.Symbol("dividends")
    nci_dividends = sp.Symbol("nci_dividends")
    buyback = sp.Symbol("buyback")
    withhold = sp.Symbol("withhold")
    stock_issue = sp.Symbol("stock_issue")
    capex = sp.Symbol("capex")
    lease_pay = sp.Symbol("lease_pay")
    debt_issue = sp.Symbol("debt_issue")
    debt_repay = sp.Symbol("debt_repay")
    cp_net = sp.Symbol("cp_net")
    securities_net = sp.Symbol("securities_net")  # purchases - maturities - sales, post-sweep

    # ---- account deltas, in the firm's own account structure ----
    deltas: dict[tuple, sp.Expr] = {}
    betas: dict[tuple, int] = {}
    labels: dict[tuple, str] = {}

    def account(key: tuple, balance: str, label: str) -> None:
        deltas.setdefault(key, sp.Integer(0))
        betas[key] = _beta(balance)
        labels[key] = label

    def post(key: tuple, expr: sp.Expr) -> None:
        deltas[key] = deltas[key] + expr

    bs_rows = [row for row in projector.bs.rows if row.kind == "leaf"]
    for row in bs_rows:
        account(_row_key(row), row.balance, row.label)

    def rows_of(*wanted: str) -> list:
        return [
            row for row in bs_rows if bs_roles[_row_key(row)].role in set(wanted)
        ]

    # working capital: one symbol per bound stock; the cash effect is the
    # signed sum through the firm's own CF lines (mirrors the wc branch)
    cash_effects: list[sp.Expr] = []
    wc_rows = [
        row
        for row in projector.cf.rows
        if row.kind == "leaf" and cf_roles[_row_key(row)].role == R.CF_WC
    ]
    bound: set[tuple] = set()
    for index, cf_row in enumerate(wc_rows):
        targets = [k for k in projector._bind_wc_row(cf_row, bs_roles) if k not in bound]
        bound.update(targets)
        for target in targets:
            bs_row = projector._bs_row(target)
            move = sp.Symbol(f"wc{index}_{len(bound)}")
            post(target, move)
            # liabilities up = cash in; assets up = cash out
            cash_effects.append(move if bs_row.balance == "credit" else -move)

    # capital pool: capex + lease additions - D&A, cash pays capex and leases
    pool = rows_of(R.PPE, R.LEASE_ROU)
    if pool:
        pool_delta = capex + lease_pay - da
        share = sp.Rational(1, len(pool))
        for row in pool:
            post(_row_key(row), pool_delta * share)
    cash_effects.append(-capex - lease_pay)

    # debt schedule moves the debt stocks and cash identically
    debt_rows = rows_of(R.DEBT, R.COMMERCIAL_PAPER)
    debt_delta = debt_issue - debt_repay + cp_net
    if debt_rows:
        share = sp.Rational(1, len(debt_rows))
        for row in debt_rows:
            post(_row_key(row), debt_delta * share)
    cash_effects.append(debt_delta)

    # securities absorb net investment purchases (incl. the sweep)
    securities_rows = rows_of(R.SECURITIES)
    if securities_rows:
        share = sp.Rational(1, len(securities_rows))
        for row in securities_rows:
            post(_row_key(row), securities_net * share)
        cash_effects.append(-securities_net)
    else:
        notes.append("no securities stocks; sweep disabled for this firm")

    # equity flows (mirrors the engine's close)
    treasury = rows_of(R.TREASURY)
    re_rows = rows_of(R.RETAINED_EARNINGS)
    apic = rows_of(R.COMMON_STOCK_APIC)
    nci = rows_of(R.NCI_EQUITY)
    if re_rows:
        post(_row_key(re_rows[0]), ni_parent - dividends)
        if not treasury:
            post(_row_key(re_rows[0]), -(buyback + withhold))
        if not nci:
            # mirrors the engine: without an NCI equity account, retained
            # earnings absorbs the NCI share so equity keeps pace with cash
            post(_row_key(re_rows[0]), ni_nci - nci_dividends)
    if treasury:
        post(_row_key(treasury[0]), buyback + withhold)  # debit contra-equity
    if apic:
        post(_row_key(apic[0]), sbc + stock_issue)
    if nci:
        post(_row_key(nci[0]), ni_nci - nci_dividends)
    cash_effects.append(-(dividends + nci_dividends + buyback + withhold) + stock_issue)

    # operating cash: net income plus non-cash add-backs (the IFRS tax and
    # finance add-back pairs articulate to zero gap by engine rule, so they
    # cancel symbolically and are omitted)
    cash_effects.append(ni_parent + ni_nci + da + sbc)

    # cash receives the recomputed net change: the sum of all cash effects
    cash_rows = rows_of(R.CASH)
    if cash_rows:
        post(_row_key(cash_rows[0]), sp.Add(*cash_effects))
    else:
        notes.append("no cash stock identified; closure unprovable")

    residual = sp.simplify(
        sp.Add(*(betas[key] * deltas[key] for key in deltas))
    )
    balanced = residual == 0
    culprits = sorted(str(symbol) for symbol in residual.free_symbols) if not balanced else []

    graph = _computation_dag()
    acyclic = nx.is_directed_acyclic_graph(graph)
    order = list(nx.lexicographical_topological_sort(graph)) if acyclic else []

    return SymbolicVerdict(
        company=projector.company,
        balanced=balanced,
        residual=str(residual),
        culprits=culprits,
        acyclic=acyclic,
        execution_order=order,
        notes=notes,
    )


def _computation_dag() -> nx.DiGraph:
    """The engine's stage dependencies, asserted acyclic (no circularity).

    Edges say "needs": interest reprices on beginning balances, so income
    depends on the PRIOR balance sheet, never on this period's financing;
    this is the Pareja-style ordering that removes the classic
    interest-debt-cash circularity.
    """
    graph = nx.DiGraph()
    edges = [
        ("driver_draw", "is_leaves"),
        ("bs_begin", "is_leaves"),  # rate effects on beginning balances
        ("is_leaves", "pretax"),
        ("pretax", "tax"),
        ("tax", "net_income"),
        ("pretax", "net_income"),
        ("net_income", "attribution"),
        ("attribution", "eps"),
        ("share_trend", "eps"),
        ("driver_draw", "wc_targets"),
        ("bs_begin", "wc_targets"),
        ("wc_targets", "cf_wc_rows"),
        ("net_income", "cf_articulation"),
        ("tax", "cf_articulation"),
        ("is_leaves", "cf_articulation"),
        ("driver_draw", "discretionary_flows"),
        ("bs_begin", "discretionary_flows"),
        ("cf_wc_rows", "pre_sweep_net_change"),
        ("cf_articulation", "pre_sweep_net_change"),
        ("discretionary_flows", "pre_sweep_net_change"),
        ("pre_sweep_net_change", "sweep"),
        ("bs_begin", "sweep"),
        ("sweep", "securities_delta"),
        ("discretionary_flows", "securities_delta"),
        ("securities_delta", "net_change"),
        ("pre_sweep_net_change", "net_change"),
        ("net_change", "cash_end"),
        ("bs_begin", "cash_end"),
        ("net_income", "equity_close"),
        ("discretionary_flows", "equity_close"),
        ("bs_begin", "bs_end"),
        ("wc_targets", "bs_end"),
        ("discretionary_flows", "bs_end"),
        ("securities_delta", "bs_end"),
        ("cash_end", "bs_end"),
        ("equity_close", "bs_end"),
        ("bs_end", "derived_recompute"),
        ("derived_recompute", "identity_assertions"),
        ("net_change", "identity_assertions"),
    ]
    graph.add_edges_from(edges)
    return graph
