"""Vectorized Monte Carlo in TensorFlow, after previous_llm_extractor.

The user's forecast stack runs batched float64 tensors of shape
``[n_samples, state]`` through graph-compiled steps; this module gives the
FSS engine the same treatment. The flow system executed here is exactly
the one the symbolic verifier proves closed (fss.symbolic), and every path
is numerically re-checked: the debit-signed sum of balance-sheet deltas
must vanish to the dollar.

Division of labor with the Decimal engine: TensorFlow computes the fan
(all paths, one vectorized pass); the Decimal engine replays selected
paths (median, deterministic) bit-exactly for the audit artifacts, fed
with the very shocks TensorFlow drew, and an agreement test holds the two
implementations together.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import numpy as np
import tensorflow as tf

from fss.drivers import (
    BETA_DEMAND,
    BETA_GDP,
    COMPETITION_MARGIN,
    COMPETITION_REVENUE,
    INFLATION_COGS_PASS,
    INFLATION_OPEX_PASS,
    INFLATION_REVENUE_PASS,
    MOMENTUM_WEIGHT,
    OPEX_REVENUE_BETA,
    RATE_PASSTHROUGH_ASSETS,
    RATE_PASSTHROUGH_DEBT,
    Scenario,
)
from fss.config import MARGIN_SIGMA, OPEX_SIGMA, REVENUE_SIGMA
from fss.engine import roles as R
from fss.engine.project import Projector, _row_key
from fss.statements import StatementRow

F = tf.float64


def _f(value: Decimal | int) -> float:
    return float(value)


@dataclass
class CompiledFirm:
    """Per-firm constants for the vectorized step (floats, precomputed once)."""

    company: str
    base_growth: float
    # income statement leaves
    is_base: np.ndarray  # [n_is]
    is_role: list[str]  # per-leaf role
    pretax_weight: np.ndarray  # effective weight of each IS leaf in pretax
    gross_sign: np.ndarray  # +1 revenue, -1 cogs (balance-signed), 0 otherwise
    etr_base: float
    nci_share: float
    # rate effects
    cash_base: float
    securities_base: float
    debt_base: float
    has_interest_rows: bool
    other_income_index: int  # -1 when absent
    # balance sheet leaves
    bs_begin: np.ndarray  # [n_bs]
    bs_beta: np.ndarray  # +1 debit, -1 credit
    wc_growth_mask: np.ndarray  # 1 where stock follows revenue growth
    wc_cogs_mask: np.ndarray  # 1 where stock follows the cogs factor
    wc_cash_sign: np.ndarray  # cash effect sign of each wc-bound stock
    pool_share: np.ndarray  # capex/D&A pool allocation
    debt_share: np.ndarray
    securities_share: np.ndarray
    cash_index: int
    re_index: int
    treasury_index: int  # -1 when absent
    apic_index: int
    nci_index: int
    # flow bases (from the firm's own cash flow statement)
    da_base: float
    sbc_base: float
    capex_base: float
    lease_base: float
    debt_delta_base: float
    securities_flow_base: float
    div_base: float
    nci_div_base: float
    buyback_base: float
    withhold_base: float
    stock_issue_base: float
    has_sweep_lines: bool


def _cf_sum(projector: Projector, roles: set[str], predicate=None) -> Decimal:
    role_map = projector.roles["cash_flow"]
    total = Decimal(0)
    for row in projector.cf.rows:
        role = role_map[_row_key(row)].role
        if row.kind != "leaf" or role not in roles:
            continue
        if predicate and not predicate(row):
            continue
        value = projector._value(projector.cf, row)
        if role in R.CF_OUTFLOW_MAGNITUDE:
            # printed-polarity documents show outflows negative; the engine
            # works with outflow magnitudes (see roles.py)
            value = abs(value)
        total += value
    return total


def _pretax_weights(projector: Projector, is_rows: list[StatementRow]) -> dict[tuple, Decimal]:
    """Effective weight of each IS leaf inside pretax income.

    The calculation arcs are linear, so pretax is an exact weighted sum of
    the leaves; tax and post-tax rows carry weight zero by construction
    (pretax is net income recomputed with tax forced to zero).
    """
    role_map = projector.roles["income_statement"]
    tax_rows = [row for row in is_rows if role_map[_row_key(row)].role == R.TAX]
    parents = projector._pretax_concepts(tax_rows)
    weights: dict[tuple, Decimal] = {}
    skip_roles = {R.TAX, R.EPS, R.SHARE_COUNT, R.ATTRIB_PARENT, R.ATTRIB_NCI}

    def descend(concept: str, weight: Decimal, visiting: frozenset) -> None:
        if concept in visiting:
            return
        rows = [
            row
            for row in projector.inc.rows_for_concept(concept)
            if not row.dims and row.kind != "abstract"
        ]
        row = rows[0] if rows else None
        if row is not None and row.kind == "leaf":
            if role_map[_row_key(row)].role not in skip_roles:
                key = _row_key(row)
                weights[key] = weights.get(key, Decimal(0)) + weight
            return
        if row is not None and row.derivation == "member_agg":
            for member in projector.inc.rows_for_concept(concept):
                if member.dims and member.kind == "leaf":
                    key = _row_key(member)
                    weights[key] = weights.get(key, Decimal(0)) + weight
            return
        for child, child_weight in projector.inc.calc_children.get(concept, []):
            descend(child, weight * child_weight, visiting | {concept})

    for parent in parents:
        descend(parent, Decimal(1), frozenset())
        break  # one pretax parent suffices; arcs are shared
    return weights


def compile_firm(projector: Projector) -> CompiledFirm:
    inc_roles = projector.roles["income_statement"]
    bs_roles = projector.roles["balance_sheet"]

    is_rows = [row for row in projector.inc.rows if row.kind == "leaf"]
    weights = _pretax_weights(projector, is_rows)
    is_base = np.array(
        [_f(projector._value(projector.inc, row)) for row in is_rows], dtype=np.float64
    )
    is_role = [inc_roles[_row_key(row)].role for row in is_rows]
    pretax_weight = np.array(
        [_f(weights.get(_row_key(row), Decimal(0))) for row in is_rows], dtype=np.float64
    )
    gross_sign = np.array(
        [
            (1.0 if row.balance == "credit" else -1.0)
            if is_role[index] in (R.REVENUE, R.COGS)
            else 0.0
            for index, row in enumerate(is_rows)
        ],
        dtype=np.float64,
    )

    tax_base = _f(sum(
        (projector._value(projector.inc, row) for row in is_rows
         if inc_roles[_row_key(row)].role == R.TAX),
        Decimal(0),
    ))
    pretax_base = float(np.dot(pretax_weight, is_base))
    etr_base = tax_base / pretax_base if pretax_base else 0.21
    nci_values = [
        _f(projector._value(projector.inc, row))
        for row in is_rows
        if inc_roles[_row_key(row)].role == R.ATTRIB_NCI
    ]
    ni_base = pretax_base - tax_base
    nci_share = (nci_values[-1] / ni_base) if nci_values and ni_base else 0.0

    other_income_index = -1
    for index, row in enumerate(is_rows):
        if is_role[index] == R.OTHER_INCOME and other_income_index < 0:
            other_income_index = index
    has_interest_rows = any(
        role in (R.INTEREST_INCOME, R.INTEREST_EXPENSE) for role in is_role
    )

    bs_rows = [row for row in projector.bs.rows if row.kind == "leaf"]
    index_of = {_row_key(row): i for i, row in enumerate(bs_rows)}
    bs_begin = np.array(
        [_f(projector._value(projector.bs, row)) for row in bs_rows], dtype=np.float64
    )
    bs_beta = np.array(
        [1.0 if row.balance == "debit" else -1.0 for row in bs_rows], dtype=np.float64
    )

    wc_growth_mask = np.zeros(len(bs_rows))
    wc_cogs_mask = np.zeros(len(bs_rows))
    wc_cash_sign = np.zeros(len(bs_rows))
    cf_roles = projector.roles["cash_flow"]
    bound: set[tuple] = set()
    for cf_row in projector.cf.rows:
        if cf_row.kind != "leaf" or cf_roles[_row_key(cf_row)].role != R.CF_WC:
            continue
        for key in projector._bind_wc_row(cf_row, bs_roles):
            if key in bound or key not in index_of:
                continue
            bound.add(key)
            i = index_of[key]
            role = bs_roles[key].role
            if role in (R.INVENTORY, R.AP):
                wc_cogs_mask[i] = 1.0
            else:
                wc_growth_mask[i] = 1.0
            wc_cash_sign[i] = 1.0 if bs_rows[i].balance == "credit" else -1.0

    def share_vector(roles: set[str]) -> np.ndarray:
        vector = np.zeros(len(bs_rows))
        members = [i for i, row in enumerate(bs_rows) if bs_roles[_row_key(row)].role in roles]
        total = sum(bs_begin[i] for i in members)
        for i in members:
            vector[i] = (bs_begin[i] / total) if total else (1.0 / len(members))
        return vector

    def first_index(roles: set[str]) -> int:
        for i, row in enumerate(bs_rows):
            if bs_roles[_row_key(row)].role in roles:
                return i
        return -1

    dividends = _cf_sum(
        projector, {R.CF_DIVIDENDS}, lambda row: "non-controlling" not in row.label.lower()
    )
    nci_dividends = _cf_sum(
        projector, {R.CF_DIVIDENDS}, lambda row: "non-controlling" in row.label.lower()
    )
    debt_delta = (
        _cf_sum(projector, {R.CF_DEBT_ISSUE})
        - _cf_sum(projector, {R.CF_DEBT_REPAY})
        + _cf_sum(projector, {R.CF_CP_NET})
    )
    securities_flow = (
        _cf_sum(projector, {R.CF_INVEST_PURCHASE})
        - _cf_sum(projector, {R.CF_INVEST_MATURITY, R.CF_INVEST_SALE})
    )
    has_sweep_lines = bool(
        [
            row
            for row in projector.cf.rows
            if row.kind == "leaf"
            and cf_roles[_row_key(row)].role
            in (R.CF_INVEST_PURCHASE, R.CF_INVEST_MATURITY, R.CF_INVEST_SALE)
        ]
    ) and first_index({R.SECURITIES}) >= 0

    return CompiledFirm(
        company=projector.company,
        base_growth=_f(projector.base_growth()),
        is_base=is_base,
        is_role=is_role,
        pretax_weight=pretax_weight,
        gross_sign=gross_sign,
        etr_base=etr_base,
        nci_share=nci_share,
        cash_base=_f(projector._sum(projector.bs, {R.CASH})),
        securities_base=_f(projector._sum(projector.bs, {R.SECURITIES})),
        debt_base=_f(projector._sum(projector.bs, {R.DEBT, R.COMMERCIAL_PAPER})),
        has_interest_rows=has_interest_rows,
        other_income_index=other_income_index,
        bs_begin=bs_begin,
        bs_beta=bs_beta,
        wc_growth_mask=wc_growth_mask,
        wc_cogs_mask=wc_cogs_mask,
        wc_cash_sign=wc_cash_sign,
        pool_share=share_vector({R.PPE, R.LEASE_ROU}),
        debt_share=share_vector({R.DEBT, R.COMMERCIAL_PAPER}),
        securities_share=share_vector({R.SECURITIES}),
        cash_index=first_index({R.CASH}),
        re_index=first_index({R.RETAINED_EARNINGS}),
        treasury_index=first_index({R.TREASURY}),
        apic_index=first_index({R.COMMON_STOCK_APIC}),
        nci_index=first_index({R.NCI_EQUITY}),
        da_base=_f(_cf_sum(projector, {R.CF_DA})),
        sbc_base=_f(_cf_sum(projector, {R.CF_SBC})),
        capex_base=_f(_cf_sum(projector, {R.CF_CAPEX})),
        lease_base=_f(_cf_sum(projector, {R.CF_LEASE_PAYMENT})),
        debt_delta_base=_f(debt_delta),
        securities_flow_base=_f(securities_flow),
        div_base=_f(dividends),
        nci_div_base=_f(nci_dividends),
        buyback_base=_f(_cf_sum(projector, {R.CF_BUYBACK})),
        withhold_base=_f(_cf_sum(projector, {R.CF_SBC_TAX_WITHHOLD})),
        stock_issue_base=_f(_cf_sum(projector, {R.CF_STOCK_ISSUE})),
        has_sweep_lines=has_sweep_lines,
    )


@dataclass
class TFFanResult:
    metrics: dict[str, np.ndarray]  # per-path float64 arrays
    shocks: np.ndarray  # [paths, 3]: eps_g, eps_m, eps_o
    identity_violations: int
    max_residual: float


def simulate_paths(
    firm: CompiledFirm, scenario: Scenario, paths: int, seed: int
) -> TFFanResult:
    """All Monte Carlo paths in one vectorized TensorFlow pass."""
    firm_hash = zlib.crc32(firm.company.encode()) & 0x7FFFFFFF
    # common random numbers: the seed ignores the scenario
    shocks = tf.random.stateless_normal(
        [paths, 3], seed=[seed, firm_hash], dtype=F
    ) * tf.constant(
        [_f(REVENUE_SIGMA), _f(MARGIN_SIGMA), _f(OPEX_SIGMA)], dtype=F
    )
    eps_g, eps_m, eps_o = shocks[:, 0], shocks[:, 1], shocks[:, 2]

    # driver map (single source of truth: fss.drivers.draw_from_shocks)
    momentum = _f(MOMENTUM_WEIGHT) * firm.base_growth
    macro = (
        _f(BETA_GDP) * _f(scenario.gdp_growth_pp)
        + _f(INFLATION_REVENUE_PASS) * _f(scenario.inflation_pp)
    ) / 100.0
    demand = _f(BETA_DEMAND) * _f(scenario.demand_z)
    drag = _f(COMPETITION_REVENUE) * _f(scenario.competition_z)
    g = tf.maximum(momentum + macro + demand - drag + eps_g, -0.35)
    cogs_shift = (
        _f(COMPETITION_MARGIN) * _f(scenario.competition_z)
        + _f(INFLATION_COGS_PASS) * _f(scenario.inflation_pp) / 100.0
        + eps_m
    )
    opex_growth = (
        _f(OPEX_REVENUE_BETA) * g
        + _f(INFLATION_OPEX_PASS) * _f(scenario.inflation_pp) / 100.0
        + eps_o
    )
    restructuring = 1.0 if (scenario.gdp_growth_pp < 0 or scenario.competition_z > 1) else 0.5
    yield_shift = _f(RATE_PASSTHROUGH_ASSETS) * _f(scenario.rate_shift_bp) / 10000.0
    debt_rate_shift = _f(RATE_PASSTHROUGH_DEBT) * _f(scenario.rate_shift_bp) / 10000.0
    dividend_growth = tf.clip_by_value(g, 0.0, 0.10)
    buyback_factor = 1.0 if scenario.gdp_growth_pp >= Decimal("-1") else 0.5

    growth = 1.0 + g  # [P]
    cogs_factor = growth * (1.0 + cogs_shift)

    # income statement leaves [P, n_is]
    base = tf.constant(firm.is_base, dtype=F)[None, :]
    ones = tf.ones_like(g)[:, None]
    factors = []
    for index, role in enumerate(firm.is_role):
        if role == R.REVENUE:
            factors.append(growth)
        elif role == R.COGS:
            factors.append(cogs_factor)
        elif role in (R.OPEX_RND, R.OPEX_SELLING, R.OPEX_ADMIN):
            factors.append(1.0 + opex_growth)
        elif role == R.RESTRUCTURING:
            factors.append(tf.fill(tf.shape(g), tf.constant(restructuring, dtype=F)))
        elif role == R.DISCONTINUED:
            factors.append(tf.zeros_like(g))
        else:
            factors.append(tf.ones_like(g))
    is_values = base * tf.stack(factors, axis=1)

    # rate repricing (mirrors the engine's per-row adjustments)
    adjustments = tf.zeros_like(is_values)
    for index, role in enumerate(firm.is_role):
        if role == R.INTEREST_INCOME:
            adjust = yield_shift * (firm.cash_base + firm.securities_base)
        elif role == R.INTEREST_EXPENSE:
            adjust = debt_rate_shift * firm.debt_base
        elif index == firm.other_income_index and not firm.has_interest_rows:
            adjust = (
                yield_shift * (firm.cash_base + firm.securities_base)
                - debt_rate_shift * firm.debt_base
            )
        else:
            continue
        one_hot = tf.constant(
            np.eye(len(firm.is_role))[index], dtype=F
        )[None, :]
        adjustments = adjustments + one_hot * adjust * ones
    is_values = is_values + adjustments

    pretax = tf.linalg.matvec(is_values, tf.constant(firm.pretax_weight, dtype=F))
    etr = min(max(firm.etr_base, 0.05), 0.45)
    tax = etr * pretax
    ni = pretax - tax
    nci = ni * firm.nci_share
    parent = ni - nci

    revenue = tf.linalg.matvec(
        is_values,
        tf.constant((np.array(firm.is_role) == R.REVENUE).astype(np.float64), dtype=F),
    )
    gross = tf.linalg.matvec(is_values, tf.constant(firm.gross_sign, dtype=F))

    # balance sheet deltas [P, n_bs]
    begin = tf.constant(firm.bs_begin, dtype=F)[None, :]
    growth_col = growth[:, None]
    cogs_col = cogs_factor[:, None]
    wc_delta = begin * (
        tf.constant(firm.wc_growth_mask, dtype=F)[None, :] * (growth_col - 1.0)
        + tf.constant(firm.wc_cogs_mask, dtype=F)[None, :] * (cogs_col - 1.0)
    )
    wc_cash = tf.linalg.matvec(wc_delta, tf.constant(firm.wc_cash_sign, dtype=F))

    da = firm.da_base * growth
    sbc = firm.sbc_base * growth
    capex = firm.capex_base * growth
    lease = tf.fill(tf.shape(g), tf.constant(firm.lease_base, dtype=F))
    dividends = firm.div_base * (1.0 + dividend_growth)
    nci_dividends = firm.nci_div_base * (1.0 + dividend_growth)
    buyback = firm.buyback_base * buyback_factor * tf.ones_like(g)
    withhold = firm.withhold_base * growth
    stock_issue = firm.stock_issue_base * tf.ones_like(g)

    pre_sweep = (
        ni
        + da
        + sbc
        + wc_cash
        - capex
        - lease
        + firm.debt_delta_base
        - firm.securities_flow_base
        - dividends
        - nci_dividends
        - buyback
        - withhold
        + stock_issue
    )
    cash_target = firm.cash_base * growth
    if firm.has_sweep_lines:
        sweep = firm.cash_base + pre_sweep - cash_target
        sweep = tf.maximum(sweep, -firm.securities_base)
    else:
        sweep = tf.zeros_like(g)
    securities_net = firm.securities_flow_base + sweep
    net_change = pre_sweep - sweep
    cash_end = firm.cash_base + net_change

    pool_delta = (capex + lease - da)[:, None] * tf.constant(firm.pool_share, dtype=F)[None, :]
    debt_delta = firm.debt_delta_base * tf.constant(firm.debt_share, dtype=F)[None, :] * ones
    securities_delta = securities_net[:, None] * tf.constant(firm.securities_share, dtype=F)[None, :]

    n_bs = len(firm.bs_begin)
    equity_delta = tf.zeros_like(begin) * ones

    def one_hot(index: int) -> tf.Tensor:
        return tf.constant(np.eye(n_bs)[index], dtype=F)[None, :]

    re_flow = parent - dividends
    if firm.treasury_index < 0:
        re_flow = re_flow - buyback - withhold
    else:
        equity_delta = equity_delta + one_hot(firm.treasury_index) * (buyback + withhold)[:, None]
    if firm.nci_index < 0:
        re_flow = re_flow + nci - nci_dividends
    else:
        equity_delta = equity_delta + one_hot(firm.nci_index) * (nci - nci_dividends)[:, None]
    equity_delta = equity_delta + one_hot(firm.re_index) * re_flow[:, None]
    if firm.apic_index >= 0:
        equity_delta = equity_delta + one_hot(firm.apic_index) * (sbc + stock_issue)[:, None]
    cash_delta = one_hot(firm.cash_index) * net_change[:, None]

    total_delta = wc_delta + pool_delta + debt_delta + securities_delta + equity_delta + cash_delta
    residual = tf.linalg.matvec(total_delta, tf.constant(firm.bs_beta, dtype=F))
    max_residual = float(tf.reduce_max(tf.abs(residual)))
    violations = int(tf.reduce_sum(tf.cast(tf.abs(residual) > 1.0, tf.int32)))

    bs_end = begin + total_delta
    assets_end = tf.linalg.matvec(
        bs_end, tf.constant(np.maximum(firm.bs_beta, 0.0), dtype=F)
    )

    metrics = {
        "revenue": revenue.numpy(),
        "net_income": ni.numpy(),
        "gross_profit": gross.numpy(),
        "gross_margin_bp": np.where(
            revenue.numpy() != 0, gross.numpy() / revenue.numpy() * 10000, 0.0
        ),
        "cash": cash_end.numpy(),
        "total_assets": assets_end.numpy(),
        "equity": np.zeros(paths),  # rendered by the Decimal engine per path
    }
    return TFFanResult(
        metrics=metrics,
        shocks=shocks.numpy(),
        identity_violations=violations,
        max_residual=max_residual,
    )
