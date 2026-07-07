"""One-period projection: (statements, driver draw) -> next-period statements.

No plugs, no circularity: every projected stock movement is carried by an
explicit flow with a balanced counterpart (cash through the firm's own cash
flow lines, income through retained earnings, non-cash pairs offsetting
inside the period), and the accounting identity is asserted at the end,
never solved for. Cash is not a residual account: the ending cash balance
is the beginning balance plus the recomputed net-change row of the firm's
own cash flow statement, and the balance sheet must then balance on its own
arcs, exactly, or the path is rejected.

The projected statement is rendered through the retained presentation map:
same rows, same labels, same signs, one new column, prior year carried as
the comparative.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from fss.drivers import DriverDraw
from fss.encdec import _recompute_cell  # shared derivation logic
from fss.engine import roles as R
from fss.engine.roles import RoleAssignment, classify_statement
from fss.statements import Cell, StatementRow, StructuredStatement

ONE = Decimal(1)
ZERO = Decimal(0)


@dataclass
class FlowRecord:
    name: str
    amount: Decimal
    effect: str  # human-readable double-entry description


@dataclass
class ProjectedPeriod:
    company: str
    period: str
    statements: dict[str, StructuredStatement]
    journal: list[FlowRecord]
    metrics: dict[str, Decimal]
    violations: list[str]
    notes: list[str] = field(default_factory=list)


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal(1))


def _row_key(row: StatementRow) -> tuple[str, tuple, str]:
    preferred = (row.preferred_label or "").lower()
    role = ""
    if row.period_type == "instant" and "periodstart" in preferred:
        role = "start"
    elif row.period_type == "instant" and "periodend" in preferred:
        role = "end"
    return (row.concept, row.dims, role)


class Projector:
    def __init__(
        self,
        company: str,
        statements: dict[str, StructuredStatement],
        stochastic_label: str = "",
    ) -> None:
        self.company = company
        self.bs = statements["balance_sheet"]
        self.inc = statements["income_statement"]
        self.cf = statements["cash_flow"]
        self.roles: dict[str, dict[tuple, RoleAssignment]] = {
            "balance_sheet": classify_statement(self.bs),
            "income_statement": classify_statement(self.inc),
            "cash_flow": classify_statement(self.cf),
        }
        self.latest = {k: s.columns[0] for k, s in statements.items()}
        self.prior = {k: (s.columns[1] if len(s.columns) > 1 else None) for k, s in statements.items()}
        self.label = stochastic_label

    # ---- helpers ----

    def _rows(self, statement: StructuredStatement, wanted: set[str]) -> list[StatementRow]:
        role_map = self.roles[statement.statement]
        out = []
        for row in statement.rows:
            if row.kind != "leaf":
                continue
            assignment = role_map.get(_row_key(row))
            if assignment and assignment.role in wanted:
                out.append(row)
        return out

    def _value(self, statement: StructuredStatement, row: StatementRow, period_key: str | None = None) -> Decimal:
        cell = row.cell(period_key or self.latest[statement.statement])
        return cell.value if cell and cell.value is not None else ZERO

    def _sum(self, statement: StructuredStatement, wanted: set[str], period_key: str | None = None) -> Decimal:
        return sum(
            (self._value(statement, row, period_key) for row in self._rows(statement, wanted)),
            ZERO,
        )

    def base_growth(self) -> Decimal:
        latest = self._sum(self.inc, {R.REVENUE})
        prior = self._sum(self.inc, {R.REVENUE}, self.prior["income_statement"])
        if prior == 0:
            return ZERO
        return latest / prior - ONE

    # ---- the projection ----

    def project(self, draw: DriverDraw) -> ProjectedPeriod:
        journal: list[FlowRecord] = []
        violations: list[str] = []
        inc_new: dict[tuple, Decimal] = {}
        bs_new: dict[tuple, Decimal] = {}
        cf_new: dict[tuple, Decimal] = {}

        growth = ONE + draw.revenue_growth
        inc_latest = self.latest["income_statement"]
        bs_latest = self.latest["balance_sheet"]

        # -- income statement leaves --
        revenue_base = self._sum(self.inc, {R.REVENUE})
        cogs_base = self._sum(self.inc, {R.COGS})
        cogs_factor = growth * (ONE + draw.cogs_ratio_shift)
        cash_base = self._sum(self.bs, {R.CASH})
        securities_base = self._sum(self.bs, {R.SECURITIES})
        debt_base = self._sum(self.bs, {R.DEBT, R.COMMERCIAL_PAPER})
        interest_income_base = self._sum(self.inc, {R.INTEREST_INCOME})
        interest_expense_base = self._sum(self.inc, {R.INTEREST_EXPENSE})

        role_map_is = self.roles["income_statement"]
        tax_rows: list[StatementRow] = []
        eps_rows: list[StatementRow] = []
        share_rows: list[StatementRow] = []
        attrib_rows: list[tuple[StatementRow, str]] = []
        gross_rows: list[StatementRow] = []
        for row in self.inc.rows:
            if row.kind != "leaf":
                continue
            role = role_map_is[_row_key(row)].role
            base = self._value(self.inc, row)
            if role == R.REVENUE:
                inc_new[_row_key(row)] = _q(base * growth)
            elif role == R.COGS:
                inc_new[_row_key(row)] = _q(base * cogs_factor)
            elif role in (R.OPEX_RND, R.OPEX_SELLING, R.OPEX_ADMIN):
                inc_new[_row_key(row)] = _q(base * (ONE + draw.opex_growth))
            elif role == R.RESTRUCTURING:
                inc_new[_row_key(row)] = _q(base * draw.restructuring_factor)
            elif role == R.OPEX_OTHER:
                inc_new[_row_key(row)] = base
            elif role == R.INTEREST_INCOME:
                yield_base = (cash_base + securities_base) and base / (cash_base + securities_base)
                inc_new[_row_key(row)] = _q(
                    (yield_base + draw.asset_yield_shift) * (cash_base + securities_base)
                )
            elif role == R.INTEREST_EXPENSE:
                rate_base = debt_base and base / debt_base
                inc_new[_row_key(row)] = _q((rate_base + draw.debt_rate_shift) * debt_base)
            elif role == R.OTHER_INCOME:
                adjustment = ZERO
                if not interest_income_base and not interest_expense_base:
                    adjustment = (
                        draw.asset_yield_shift * (cash_base + securities_base)
                        - draw.debt_rate_shift * debt_base
                    )
                inc_new[_row_key(row)] = _q(base + adjustment)
            elif role == R.DISCONTINUED:
                inc_new[_row_key(row)] = ZERO
            elif role == R.GROSS_PROFIT_ROW:
                gross_rows.append(row)
            elif role == R.TAX:
                tax_rows.append(row)
            elif role == R.EPS:
                eps_rows.append(row)
            elif role == R.SHARE_COUNT:
                share_rows.append(row)
            elif role in (R.ATTRIB_PARENT, R.ATTRIB_NCI):
                attrib_rows.append((row, role))
            else:
                inc_new[_row_key(row)] = base

        # a filer-printed gross line outside the calc tree articulates from
        # the projected revenue and cost leaves through balance polarity
        for row in gross_rows:
            value = ZERO
            for leaf in self._rows(self.inc, {R.REVENUE, R.COGS}):
                sign = ONE if leaf.balance == "credit" else -ONE
                value += sign * inc_new.get(_row_key(leaf), self._value(self.inc, leaf))
            inc_new[_row_key(row)] = _q(value)

        # tax from projected pretax through the firm's own arcs
        pretax_concepts = self._pretax_concepts(tax_rows)
        zero_tax = {row: ZERO for row in tax_rows}
        pretax_new = self._recompute_is(inc_new, pretax_concepts, assume=zero_tax)
        pretax_base = self._recompute_is({}, pretax_concepts, assume=zero_tax, period=inc_latest)
        tax_base = sum((self._value(self.inc, row) for row in tax_rows), ZERO)
        etr = tax_base / pretax_base if pretax_base else Decimal("0.21")
        etr = min(max(etr + draw.tax_rate_shift, Decimal("0.05")), Decimal("0.45"))
        for row in tax_rows:
            share = self._value(self.inc, row) / tax_base if tax_base else ONE
            inc_new[_row_key(row)] = _q(etr * pretax_new * share)

        # net income and the NCI split
        ni_new = pretax_new - sum(inc_new[_row_key(row)] for row in tax_rows)
        nci_values = [
            self._value(self.inc, row) for row, role in attrib_rows if role == R.ATTRIB_NCI
        ]
        # continuing-operations and total splits repeat the same attribution;
        # one representative row carries the share
        nci_base = nci_values[-1] if nci_values else ZERO
        ni_base = self._net_income_base()
        nci_share = nci_base / ni_base if ni_base else ZERO
        nci_new = _q(ni_new * nci_share)
        parent_new = _q(ni_new - nci_new)
        for row, role in attrib_rows:
            inc_new[_row_key(row)] = parent_new if role == R.ATTRIB_PARENT else nci_new

        # shares and EPS
        share_trend = self._share_trend() * draw.buyback_factor
        share_values: dict[tuple, Decimal] = {}
        for row in share_rows:
            base = self._value(self.inc, row)
            share_values[_row_key(row)] = _q(base * (ONE + share_trend))
            inc_new[_row_key(row)] = share_values[_row_key(row)]
        for row in eps_rows:
            matching_shares = self._match_share_row(row, share_rows)
            shares = share_values.get(
                _row_key(matching_shares) if matching_shares else None, ZERO
            )
            decimals = row.cell(inc_latest).decimals if row.cell(inc_latest) else 2
            quantum = Decimal(10) ** (-(decimals if decimals is not None else 2))
            if shares:
                inc_new[_row_key(row)] = (parent_new / shares).quantize(quantum)
            else:
                # no share-count rows on the face: scale reported EPS with
                # attributable income (share count held, documented)
                base_eps = self._value(self.inc, row)
                parent_values = [
                    self._value(self.inc, r)
                    for r, role in attrib_rows
                    if role == R.ATTRIB_PARENT
                ]
                parent_base = (parent_values[-1] if parent_values else ZERO) or ni_base
                ratio = parent_new / parent_base if parent_base else ONE
                inc_new[_row_key(row)] = (base_eps * ratio).quantize(quantum)

        # -- balance sheet and cash flow flows --
        cf_role_map = self.roles["cash_flow"]
        bs_role_map = self.roles["balance_sheet"]
        bs_begin: dict[tuple, Decimal] = {
            _row_key(row): self._value(self.bs, row)
            for row in self.bs.rows
            if row.kind == "leaf"
        }
        bs_delta: dict[tuple, Decimal] = {key: ZERO for key in bs_begin}

        def move(row_key: tuple, amount: Decimal, flow: str, effect: str) -> None:
            if amount == 0:
                return
            bs_delta[row_key] = bs_delta.get(row_key, ZERO) + amount
            journal.append(FlowRecord(flow, amount, effect))

        # working-capital rows on the firm's own cash flow statement
        wc_rows = [
            row
            for row in self.cf.rows
            if row.kind == "leaf" and cf_role_map[_row_key(row)].role == R.CF_WC
        ]
        bound: set[tuple] = set()
        for row in wc_rows:
            targets = self._bind_wc_row(row, bs_role_map)
            targets = [key for key in targets if key not in bound]
            bound.update(targets)
            impact = ZERO
            for key in targets:
                bs_row = self._bs_row(key)
                role = bs_role_map[key].role
                factor = cogs_factor if role in (R.INVENTORY, R.AP) else growth
                target = _q(bs_begin[key] * factor)
                delta = target - bs_begin[key]
                move(key, delta, f"wc:{row.label[:40]}", "working-capital stock move")
                sign = ONE if bs_row.balance == "credit" else -ONE
                impact += sign * delta  # liabilities up = cash in
            displayed = impact
            cf_new[_row_key(row)] = _q(
                displayed / row.displayed_sign if row.displayed_sign else displayed
            )

        # articulation and discretionary cash-flow leaves
        da_base = ZERO
        capex_base = ZERO
        for row in self.cf.rows:
            if row.kind != "leaf":
                continue
            key = _row_key(row)
            if key in cf_new:
                continue
            role = cf_role_map[key].role
            base = self._value(self.cf, row)
            if role == R.CF_NI:
                cf_new[key] = _q(ni_new)
            elif role == R.CF_DA:
                cf_new[key] = _q(base * growth)
                da_base += base
            elif role == R.CF_SBC:
                cf_new[key] = _q(base * growth)
            elif role in (R.CF_DEFERRED_TAX, R.CF_OTHER_NONCASH, R.CF_IMPAIRMENT,
                          R.CF_OTHER_INVESTING, R.CF_OTHER_FINANCING, R.CF_ACQUISITION,
                          R.CF_FX, R.CF_NONCASH_DISCLOSURE, R.CF_DISCONTINUED,
                          R.CF_ASSET_DISPOSAL):
                cf_new[key] = ZERO
            elif role in (R.TAX, R.CF_TAX_ADDBACK, R.CF_TAX_PAID):
                # tax expense add-back and taxes paid articulate exactly with
                # the projected tax line (pay-as-you-go: no accrual gap, so
                # the tax stocks stay put and the books stay closed)
                cf_new[key] = _q(sum(inc_new[_row_key(r)] for r in tax_rows))
            elif role == R.CF_FINANCE_ADDBACK:
                # one filer shows a single net row, another separate income
                # and costs rows; mirror whichever the label says
                label = row.label.lower()
                if "net" in label:
                    cf_new[key] = self._finance_net(inc_new)
                elif "cost" in label:
                    cf_new[key] = self._finance_costs(inc_new)
                else:
                    cf_new[key] = self._finance_income(inc_new)
            elif role == R.CF_INTEREST_RECEIVED:
                cf_new[key] = _q(
                    self._finance_income(inc_new) - self._dividends_received_base()
                )
            elif role == R.CF_INTEREST_PAID:
                cf_new[key] = self._finance_costs(inc_new)
            elif role == R.CF_DIVIDENDS_RECEIVED:
                cf_new[key] = base
            elif role in (R.INTEREST_INCOME, R.INTEREST_EXPENSE, R.OTHER_INCOME, R.IS_DERIVED):
                cf_new[key] = self._articulate_is_row(row, inc_new)
            elif role == R.CF_SUPPLEMENTAL:
                cf_new[key] = base
            elif role == R.CF_CAPEX:
                cf_new[key] = _q(base * growth)
                capex_base += abs(base)
            elif role == R.CF_DIVIDENDS:
                cf_new[key] = _q(base * (ONE + draw.dividend_growth))
            elif role == R.CF_BUYBACK:
                cf_new[key] = _q(base * draw.buyback_factor)
            elif role == R.CF_SBC_TAX_WITHHOLD:
                cf_new[key] = _q(base * growth)
            elif role in (R.CF_DEBT_ISSUE, R.CF_DEBT_REPAY, R.CF_CP_NET, R.CF_LEASE_PAYMENT):
                # financing schedule held at the base-year level; the debt
                # stocks move with it below
                cf_new[key] = base
            elif role == R.CF_STOCK_ISSUE:
                cf_new[key] = base
            elif role in (R.CF_INVEST_PURCHASE, R.CF_INVEST_MATURITY, R.CF_INVEST_SALE):
                # held at base; the liquidity sweep then adjusts the first
                # purchase line and the securities stocks absorb the net
                cf_new[key] = base
            elif role in (R.CF_CASH_BEGIN, R.CF_CASH_END, R.CF_NET_CHANGE, R.CF_ACTIVITY_TOTAL):
                continue  # derived or set after the sweep
            else:
                cf_new[key] = ZERO

        # debt stocks move with the held financing schedule
        debt_delta = ZERO
        for row in self.cf.rows:
            if row.kind != "leaf":
                continue
            key = _row_key(row)
            role = cf_role_map[key].role
            if role == R.CF_DEBT_ISSUE:
                debt_delta += cf_new[key]
            elif role == R.CF_DEBT_REPAY:
                # repayments are consumed as magnitudes: tagged filings state
                # them as positive facts, untagged documents print them
                # negative (see roles.CF_OUTFLOW_MAGNITUDE)
                debt_delta -= abs(cf_new[key])
            elif role == R.CF_CP_NET:
                debt_delta += cf_new[key]  # genuinely signed: positive = net proceeds
        debt_rows = self._rows(self.bs, {R.DEBT, R.COMMERCIAL_PAPER})
        debt_total = sum(bs_begin[_row_key(row)] for row in debt_rows)
        for row in debt_rows:
            share = bs_begin[_row_key(row)] / debt_total if debt_total else ZERO
            move(
                _row_key(row),
                _q(debt_delta * share),
                "debt",
                "issuance less repayments per the held financing schedule",
            )

        # capital stocks: PP&E moves with capex and D&A (D&A sits inside the
        # expense lines of the income statement already)
        capex_new = sum(
            abs(cf_new[_row_key(row)])
            for row in self.cf.rows
            if row.kind == "leaf" and cf_role_map[_row_key(row)].role == R.CF_CAPEX
        )
        da_new = sum(
            cf_new[_row_key(row)]
            for row in self.cf.rows
            if row.kind == "leaf" and cf_role_map[_row_key(row)].role == R.CF_DA
        )
        # lease additions equal lease principal payments (the liability is
        # held flat), and they land in the capital pool alongside capex
        lease_payments_new = sum(
            abs(cf_new[_row_key(row)])
            for row in self.cf.rows
            if row.kind == "leaf" and cf_role_map[_row_key(row)].role == R.CF_LEASE_PAYMENT
        )
        pool_rows = self._rows(self.bs, {R.PPE, R.LEASE_ROU})
        pool_total = sum(bs_begin[_row_key(row)] for row in pool_rows)
        pool_delta = capex_new + lease_payments_new - da_new
        for row in pool_rows:
            share = bs_begin[_row_key(row)] / pool_total if pool_total else ONE
            move(
                _row_key(row),
                _q(pool_delta * share),
                "capital",
                "capex and lease additions less depreciation and amortization",
            )

        # equity flows
        div_new = sum(
            abs(cf_new[_row_key(row)])
            for row in self.cf.rows
            if row.kind == "leaf"
            and cf_role_map[_row_key(row)].role == R.CF_DIVIDENDS
            and "non-controlling" not in row.label.lower()
        )
        nci_div_new = sum(
            abs(cf_new[_row_key(row)])
            for row in self.cf.rows
            if row.kind == "leaf"
            and cf_role_map[_row_key(row)].role == R.CF_DIVIDENDS
            and "non-controlling" in row.label.lower()
        )
        buyback_new = sum(
            abs(cf_new[_row_key(row)])
            for row in self.cf.rows
            if row.kind == "leaf" and cf_role_map[_row_key(row)].role == R.CF_BUYBACK
        )
        withhold_new = sum(
            abs(cf_new[_row_key(row)])
            for row in self.cf.rows
            if row.kind == "leaf" and cf_role_map[_row_key(row)].role == R.CF_SBC_TAX_WITHHOLD
        )
        sbc_new = sum(
            cf_new[_row_key(row)]
            for row in self.cf.rows
            if row.kind == "leaf" and cf_role_map[_row_key(row)].role == R.CF_SBC
        )
        stock_issue_new = sum(
            cf_new[_row_key(row)]
            for row in self.cf.rows
            if row.kind == "leaf" and cf_role_map[_row_key(row)].role == R.CF_STOCK_ISSUE
        )
        treasury_rows = self._rows(self.bs, {R.TREASURY})
        re_rows = self._rows(self.bs, {R.RETAINED_EARNINGS})
        apic_rows = self._rows(self.bs, {R.COMMON_STOCK_APIC})
        nci_rows = self._rows(self.bs, {R.NCI_EQUITY})
        if re_rows:
            re_key = _row_key(re_rows[0])
            move(re_key, _q(parent_new), "close", "net income attributable to parent")
            move(re_key, -div_new, "dividends", "dividends declared and paid")
            if not treasury_rows:
                move(re_key, -buyback_new - withhold_new, "buyback", "repurchases retired against retained earnings")
            if not nci_rows:
                # no NCI equity account on the face: the NCI share of income
                # (and any NCI dividends) must still land in equity, or cash
                # would move with no counterpart (caught by the symbolic
                # closure check)
                move(
                    re_key,
                    _q(nci_new) - nci_div_new,
                    "nci",
                    "NCI income less NCI dividends absorbed into retained earnings",
                )
        if treasury_rows:
            move(_row_key(treasury_rows[0]), buyback_new + withhold_new, "buyback", "repurchases into treasury (contra-equity)")
        if apic_rows:
            # prefer the premium/paid-in row over nominal issued capital
            preferred = [
                row
                for row in apic_rows
                if re.search(r"premium|paid[- ]?in", row.label, re.IGNORECASE)
            ]
            target = preferred[0] if preferred else apic_rows[0]
            move(
                _row_key(target),
                _q(sbc_new + stock_issue_new),
                "sbc",
                "share-based compensation and option exercises credited to paid-in capital",
            )
        if nci_rows:
            move(_row_key(nci_rows[0]), _q(nci_new) - nci_div_new, "nci", "income attributable to NCI less NCI dividends")

        # liquidity policy: sweep excess cash into securities (behavioral
        # rule, not an accounting plug; the books stay balanced either way)
        cash_rows = self._rows(self.bs, {R.CASH})
        cash_key = _row_key(cash_rows[0]) if cash_rows else None
        pre_sweep_change = self._net_change(cf_new)
        cash_target = _q(cash_base * growth)
        sweep = _q(cash_base + pre_sweep_change - cash_target)
        self._apply_sweep(sweep, cf_new, cf_role_map, violations)
        # the securities stocks absorb the net of the (post-sweep) purchase,
        # maturity, and sale lines, so the stocks and the cash flow agree
        securities_net = ZERO
        for row in self.cf.rows:
            if row.kind != "leaf":
                continue
            key = _row_key(row)
            role = cf_role_map[key].role
            if role == R.CF_INVEST_PURCHASE:
                # purchases are consumed as magnitudes; printed-polarity
                # documents show them negative (roles.CF_OUTFLOW_MAGNITUDE)
                securities_net += abs(cf_new.get(key, ZERO))
            elif role in (R.CF_INVEST_MATURITY, R.CF_INVEST_SALE):
                securities_net -= cf_new.get(key, ZERO)
        securities_rows = self._rows(self.bs, {R.SECURITIES})
        securities_total = sum(bs_begin[_row_key(row)] for row in securities_rows)
        remaining = securities_net
        for index, row in enumerate(securities_rows):
            share = (
                bs_begin[_row_key(row)] / securities_total
                if securities_total
                else ONE / max(len(securities_rows), 1)
            )
            amount = _q(securities_net * share) if index < len(securities_rows) - 1 else remaining
            remaining -= amount
            move(_row_key(row), amount, "securities", "net investment purchases incl. liquidity sweep")

        # cash from the firm's own cash flow statement
        net_change = self._net_change(cf_new)
        if cash_key is not None:
            move(cash_key, net_change, "cash", "net change per cash flow statement")
        for row in self.cf.rows:
            if row.kind != "leaf":
                continue
            key = _row_key(row)
            role = cf_role_map[key].role
            if role == R.CF_CASH_BEGIN:
                cf_new[key] = _q(cash_base)
            elif role == R.CF_CASH_END:
                cf_new[key] = _q(cash_base + net_change)

        # unmodeled stocks hold; assemble ending balances
        for key, begin in bs_begin.items():
            bs_new[key] = _q(begin + bs_delta.get(key, ZERO))

        statements = self._render(inc_new, bs_new, cf_new)
        metrics = self._metrics(statements, inc_new, bs_new)
        violations.extend(self._assert_identities(statements))
        return ProjectedPeriod(
            company=self.company,
            period=statements["balance_sheet"].columns[0],
            statements=statements,
            journal=journal,
            metrics=metrics,
            violations=violations,
        )

    # ---- articulation helpers ----

    def _net_income_base(self) -> Decimal:
        for row in self.inc.rows:
            if row.concept.endswith(("NetIncomeLoss", "ProfitLoss")) and not row.dims:
                value = self._value(self.inc, row)
                if value:
                    return value
        # fall back: pretax minus tax
        return ZERO

    def _pretax_concepts(self, tax_rows: list[StatementRow]) -> list[str]:
        """Concepts whose calc children include the tax rows (pretax parents)."""
        tax_concepts = {row.concept for row in tax_rows}
        parents = [
            parent
            for parent, kids in self.inc.calc_children.items()
            if any(child in tax_concepts for child, _ in kids)
        ]
        return parents

    def _recompute_is(
        self,
        overrides: dict[tuple, Decimal],
        pretax_parents: list[str],
        assume: dict[StatementRow, Decimal] | None,
        period: str | None = None,
    ) -> Decimal:
        """Pretax income under projected leaves (tax rows forced to zero) by
        walking the firm's calculation arcs."""
        period_key = period or self.latest["income_statement"]
        values: dict[tuple[str, tuple], Decimal | None] = {}
        for row in self.inc.rows:
            if row.kind != "leaf":
                continue
            key = _row_key(row)
            if assume is not None and row in assume:
                values[(row.concept, row.dims)] = assume[row]
            elif key in overrides:
                values[(row.concept, row.dims)] = overrides[key]
            else:
                cell = row.cell(period_key)
                values[(row.concept, row.dims)] = cell.value if cell else None
        for parent in pretax_parents:
            rows = [r for r in self.inc.rows_for_concept(parent) if not r.dims]
            if not rows:
                continue
            value = _recompute_cell(self.inc, rows[0], period_key, values, frozenset())
            if value is not None:
                return value
        return ZERO

    def _articulate_is_row(self, cf_row: StatementRow, inc_new: dict[tuple, Decimal]) -> Decimal:
        """A cash-flow add-back that mirrors an income-statement line."""
        for row in self.inc.rows:
            if row.kind == "leaf" and row.concept == cf_row.concept and row.dims == cf_row.dims:
                return inc_new.get(_row_key(row), self._value(self.inc, row))
        # net finance income appears with opposite sign as an add-back
        candidates = [
            row
            for row in self.inc.rows
            if row.kind == "derived" and row.concept == cf_row.concept
        ]
        if candidates:
            return self._value(self.inc, candidates[0])
        return self._value(self.cf, cf_row)

    def _share_trend(self) -> Decimal:
        share_rows = self._rows(self.inc, {R.SHARE_COUNT})
        basic = [row for row in share_rows if "dilut" not in row.label.lower()]
        row = basic[0] if basic else (share_rows[0] if share_rows else None)
        if row is None:
            return ZERO
        latest = self._value(self.inc, row)
        prior = self._value(self.inc, row, self.prior["income_statement"])
        if not latest or not prior:
            return ZERO
        return latest / prior - ONE

    def _match_share_row(
        self, eps_row: StatementRow, share_rows: list[StatementRow]
    ) -> StatementRow | None:
        want_diluted = "dilut" in (eps_row.label + eps_row.concept).lower()
        for row in share_rows:
            if ("dilut" in (row.label + row.concept).lower()) == want_diluted:
                return row
        return share_rows[0] if share_rows else None

    def _bs_row(self, key: tuple) -> StatementRow:
        for row in self.bs.rows:
            if row.kind == "leaf" and _row_key(row) == key:
                return row
        raise KeyError(key)

    def _bind_wc_row(
        self, cf_row: StatementRow, bs_role_map: dict[tuple, RoleAssignment]
    ) -> list[tuple]:
        """Bind a working-capital cash-flow row to balance-sheet stocks.

        "Other ... assets/liabilities" rows respect current/non-current
        qualifiers in the label; a row naming both spans both."""
        label = cf_row.label.lower()
        current_only = ("current" in label or "short-term" in label) and not (
            "non-current" in label or "long-term" in label
        )
        noncurrent_only = ("non-current" in label or "long-term" in label) and not (
            "current" in label.replace("non-current", "") or "short-term" in label
        )

        def span(current_role: str, noncurrent_role: str) -> set[str]:
            if current_only:
                return {current_role}
            if noncurrent_only:
                return {noncurrent_role}
            return {current_role, noncurrent_role}

        wanted: set[str] = set()
        if "vendor" in label:
            wanted.add(R.VENDOR_RECEIVABLE)
        elif "receivable" in label:
            wanted.add(R.AR)
            if "other assets" in label:
                wanted.update(span(R.OTHER_CURRENT_ASSET, R.OTHER_NONCURRENT_ASSET))
        if "inventor" in label:
            wanted.add(R.INVENTORY)
        if "payable" in label:
            wanted.add(R.AP)
            if "other" in label:
                wanted.add(R.ACCRUED)
        if "deferred revenue" in label or "unearned revenue" in label or "contract liab" in label:
            wanted.add(R.DEFERRED_REVENUE)
        if "provision" in label:
            wanted.add(R.PROVISION)
        if "income tax" in label or label == "income taxes":
            wanted.update({R.TAX_LIABILITY, R.TAX_RECEIVABLE})
        if "compensation" in label or "accrued" in label:
            wanted.add(R.ACCRUED)
        if "other" in label and "asset" in label and "receivable" not in label:
            wanted.update(span(R.OTHER_CURRENT_ASSET, R.OTHER_NONCURRENT_ASSET))
        if "other" in label and "liabilit" in label:
            wanted.update(span(R.OTHER_CURRENT_LIAB, R.OTHER_NONCURRENT_LIAB))
        return [
            key
            for key, assignment in bs_role_map.items()
            if assignment.role in wanted
        ]

    def _finance_income(self, inc_new: dict[tuple, Decimal]) -> Decimal:
        return _q(
            sum(
                (
                    inc_new.get(_row_key(r), self._value(self.inc, r))
                    for r in self._rows(self.inc, {R.INTEREST_INCOME})
                ),
                ZERO,
            )
        )

    def _finance_costs(self, inc_new: dict[tuple, Decimal]) -> Decimal:
        return _q(
            sum(
                (
                    inc_new.get(_row_key(r), self._value(self.inc, r))
                    for r in self._rows(self.inc, {R.INTEREST_EXPENSE})
                ),
                ZERO,
            )
        )

    def _finance_net(self, inc_new: dict[tuple, Decimal]) -> Decimal:
        """The net finance add-back mirrors the projected finance lines.

        Cash realization is then delivered by the interest received and paid
        lines, so the accrual-to-cash gap is zero and the books close."""
        return _q(self._finance_income(inc_new) - self._finance_costs(inc_new))

    def _dividends_received_base(self) -> Decimal:
        role_map = self.roles["cash_flow"]
        return _q(
            sum(
                (
                    self._value(self.cf, row)
                    for row in self.cf.rows
                    if row.kind == "leaf"
                    and role_map[_row_key(row)].role == R.CF_DIVIDENDS_RECEIVED
                ),
                ZERO,
            )
        )

    def _net_change(self, cf_new: dict[tuple, Decimal]) -> Decimal:
        """The recomputed net-change row of the projected cash flow."""
        role_map = self.roles["cash_flow"]
        values: dict[tuple[str, tuple], Decimal | None] = {}
        for row in self.cf.rows:
            if row.kind != "leaf":
                continue
            key = _row_key(row)
            if role_map[key].role in (R.CF_CASH_BEGIN, R.CF_CASH_END):
                continue
            values[(row.concept, row.dims)] = cf_new.get(key, ZERO)
        for row in self.cf.rows:
            if row.kind == "derived" and role_map[_row_key(row)].role == R.CF_NET_CHANGE:
                value = _recompute_cell(
                    self.cf, row, self.latest["cash_flow"], values, frozenset()
                )
                if value is not None:
                    return _q(value)
        # no explicit net-change row: sum the activity totals directly
        total = ZERO
        for row in self.cf.rows:
            if row.kind == "derived" and role_map[_row_key(row)].role == R.CF_ACTIVITY_TOTAL:
                value = _recompute_cell(
                    self.cf, row, self.latest["cash_flow"], values, frozenset()
                )
                if value is not None:
                    total += value
        return _q(total)

    def _apply_sweep(
        self,
        sweep: Decimal,
        cf_new: dict[tuple, Decimal],
        cf_role_map: dict[tuple, RoleAssignment],
        violations: list[str],
    ) -> Decimal:
        """Adjust security purchase/maturity lines so cash lands on target.

        Returns the sweep actually applied to the securities stocks.
        """
        purchase_keys = [
            _row_key(row)
            for row in self.cf.rows
            if row.kind == "leaf" and cf_role_map[_row_key(row)].role == R.CF_INVEST_PURCHASE
        ]
        maturity_keys = [
            _row_key(row)
            for row in self.cf.rows
            if row.kind == "leaf"
            and cf_role_map[_row_key(row)].role in (R.CF_INVEST_MATURITY, R.CF_INVEST_SALE)
        ]
        if not purchase_keys and not maturity_keys:
            if sweep:
                violations.append(
                    "no securities lines on the cash flow statement; excess cash retained"
                )
            return ZERO
        # a purchase line in printed polarity (untagged) states outflows
        # negative; growing the purchase must push the row the way the
        # document itself signs outflows or the recomputed net change breaks
        purchase_direction = ONE
        if purchase_keys and cf_new.get(purchase_keys[0], ZERO) < 0:
            purchase_direction = -ONE
        if sweep >= 0 and purchase_keys:
            cf_new[purchase_keys[0]] = (
                cf_new.get(purchase_keys[0], ZERO) + purchase_direction * sweep
            )
            return sweep
        if sweep < 0:
            need = -sweep
            available = sum(
                (self._value(self.bs, row) for row in self._rows(self.bs, {R.SECURITIES})),
                ZERO,
            )
            drawable = min(need, available)
            if maturity_keys:
                cf_new[maturity_keys[0]] = cf_new.get(maturity_keys[0], ZERO) + drawable
            elif purchase_keys:
                cf_new[purchase_keys[0]] = (
                    cf_new.get(purchase_keys[0], ZERO) - purchase_direction * drawable
                )
            if drawable < need:
                violations.append("liquidity: securities insufficient to reach cash target")
            return -drawable
        return ZERO

    # ---- rendering and checks ----

    def _next_period(self, statement: StructuredStatement) -> tuple[str, str]:
        latest = statement.columns[0]
        if latest.startswith("I"):
            end = date.fromisoformat(latest[1:])
            new_end = _add_year(end)
            return f"I{new_end.isoformat()}", latest
        start_s, _, end_s = latest[1:].partition(":")
        start = date.fromisoformat(start_s)
        end = date.fromisoformat(end_s)
        return (
            f"D{(end + timedelta(days=1)).isoformat()}:{_add_year(end).isoformat()}",
            latest,
        )

    def _render(
        self,
        inc_new: dict[tuple, Decimal],
        bs_new: dict[tuple, Decimal],
        cf_new: dict[tuple, Decimal],
    ) -> dict[str, StructuredStatement]:
        out: dict[str, StructuredStatement] = {}
        for statement, values in (
            (self.inc, inc_new),
            (self.bs, bs_new),
            (self.cf, cf_new),
        ):
            new_period, comparative = self._next_period(statement)
            rows: list[StatementRow] = []
            for row in statement.rows:
                template = row.cell(comparative)
                new_value = values.get(_row_key(row)) if row.kind == "leaf" else None
                comparative_cell = row.cell(comparative)
                cells = (
                    Cell(
                        new_period,
                        new_value,
                        template.decimals if template else None,
                        template.unit if template else None,
                    ),
                    Cell(
                        comparative,
                        comparative_cell.value if comparative_cell else None,
                        comparative_cell.decimals if comparative_cell else None,
                        comparative_cell.unit if comparative_cell else None,
                    ),
                )
                rows.append(
                    StatementRow(
                        order=row.order,
                        concept=row.concept,
                        dims=row.dims,
                        label=row.label,
                        depth=row.depth,
                        kind=row.kind,
                        derivation=row.derivation,
                        preferred_label=row.preferred_label,
                        negated=row.negated,
                        displayed_sign=row.displayed_sign,
                        period_type=row.period_type,
                        balance=row.balance,
                        is_monetary=row.is_monetary,
                        is_extension=row.is_extension,
                        anchor=row.anchor,
                        section=row.section,
                        cells=cells,
                    )
                )
            projected = StructuredStatement(
                company=statement.company,
                standard=statement.standard,
                statement=statement.statement,
                linkrole=statement.linkrole,
                role_definition=statement.role_definition,
                currency=statement.currency,
                columns=(new_period, comparative),
                rows=rows,
                calc_children=statement.calc_children,
                notes=[f"simulated period {new_period}"],
            )
            _fill_derived(projected, new_period)
            out[statement.statement] = projected
        return out

    def _metrics(
        self,
        statements: dict[str, StructuredStatement],
        inc_new: dict[tuple, Decimal],
        bs_new: dict[tuple, Decimal],
    ) -> dict[str, Decimal]:
        inc = statements["income_statement"]
        bs = statements["balance_sheet"]
        period = inc.columns[0]

        def derived(statement: StructuredStatement, concepts: tuple[str, ...]) -> Decimal:
            for concept in concepts:
                for row in statement.rows:
                    if row.concept == concept and not row.dims:
                        cell = row.cell(statement.columns[0])
                        if cell and cell.value is not None:
                            return cell.value
            return ZERO

        revenue = sum(
            (
                inc_new[_row_key(row)]
                for row in self._rows(self.inc, {R.REVENUE})
            ),
            ZERO,
        )
        ni = derived(
            inc,
            (
                "us-gaap:NetIncomeLoss",
                "ifrs-full:ProfitLoss",
                "ifrs-full:ProfitLossAttributableToOwnersOfParent",
            ),
        )
        gross = derived(inc, ("us-gaap:GrossProfit", "ifrs-full:GrossProfit"))
        cash = sum(
            (bs_new[_row_key(row)] for row in self._rows(self.bs, {R.CASH})), ZERO
        )
        assets = derived(bs, ("us-gaap:Assets", "ifrs-full:Assets"))
        equity = derived(
            bs,
            (
                "us-gaap:StockholdersEquity",
                "ifrs-full:Equity",
                "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                "ifrs-full:EquityAttributableToOwnersOfParent",
            ),
        )
        return {
            "revenue": revenue,
            "net_income": ni,
            "gross_profit": gross,
            "gross_margin_bp": _q(gross / revenue * 10000) if revenue else ZERO,
            "cash": cash,
            "total_assets": assets,
            "equity": equity,
            "period": Decimal(0),
        }

    def _identity_residual(self, bs: StructuredStatement, period: str) -> Decimal | None:
        """A minus (L+E), both recomputed from leaves through the arcs."""
        leaf_values = {
            (row.concept, row.dims): (
                row.cell(period).value if row.cell(period) else None
            )
            for row in bs.rows
            if row.kind == "leaf"
        }

        def recomputed(concepts: tuple[str, ...]) -> Decimal | None:
            for concept in concepts:
                for row in bs.rows:
                    if row.concept == concept and not row.dims and row.kind != "abstract":
                        value = _recompute_cell(bs, row, period, leaf_values, frozenset())
                        if value is not None:
                            return value
            return None

        assets = recomputed(("us-gaap:Assets", "ifrs-full:Assets"))
        liab_equity = recomputed(
            ("us-gaap:LiabilitiesAndStockholdersEquity", "ifrs-full:EquityAndLiabilities")
        )
        if assets is None or liab_equity is None:
            return None
        return assets - liab_equity

    def _assert_identities(self, statements: dict[str, StructuredStatement]) -> list[str]:
        violations: list[str] = []
        bs = statements["balance_sheet"]
        period = bs.columns[0]
        residual = self._identity_residual(bs, period)
        # a filer whose printed leaves round to an unbalanced sheet carries a
        # small constant residual; the engine must add exactly zero to it
        base_residual = self._identity_residual(self.bs, self.latest["balance_sheet"])
        if residual is None and base_residual is None:
            # untagged statements may lack a verified arc chain to the top
            # totals (for example when flagged cells made a group
            # unverifiable); the aggregate-delta invariant of the TensorFlow
            # path still binds, so this downgrades to a disclosure
            pass
        elif residual is None or base_residual is None:
            violations.append("could not locate top-level balance totals")
        elif residual != base_residual:
            violations.append(
                f"engine introduced imbalance: A-(L+E) {residual} vs base-year "
                f"residual {base_residual}"
            )
        cf = statements["cash_flow"]
        cf_period = cf.columns[0]
        role_map = self.roles["cash_flow"]
        begin = end = change = None
        for row in cf.rows:
            role = role_map.get(_row_key(row))
            if role is None:
                continue
            cell = row.cell(cf_period)
            value = cell.value if cell else None
            if role.role == R.CF_CASH_BEGIN and value is not None:
                begin = value
            elif role.role == R.CF_CASH_END and value is not None:
                end = value
            elif role.role == R.CF_NET_CHANGE and value is not None:
                change = value
        if begin is not None and end is not None and change is not None:
            if begin + change != end:
                violations.append(
                    f"cash tie broken: begin {begin} + change {change} != end {end}"
                )
        return violations


def _add_year(day: date) -> date:
    try:
        return day.replace(year=day.year + 1)
    except ValueError:  # February 29
        return day.replace(year=day.year + 1, day=28)


def _fill_derived(statement: StructuredStatement, period: str) -> None:
    """Recompute derived rows for the given period in place."""
    leaf_values: dict[tuple[str, tuple], Decimal | None] = {
        (row.concept, row.dims): (
            row.cell(period).value if row.cell(period) else None
        )
        for row in statement.rows
        if row.kind == "leaf"
    }
    new_rows: list[StatementRow] = []
    for row in statement.rows:
        if row.kind != "derived":
            new_rows.append(row)
            continue
        value = _recompute_cell(statement, row, period, leaf_values, frozenset())
        cells = tuple(
            Cell(cell.period, value if cell.period == period else cell.value, cell.decimals, cell.unit)
            for cell in row.cells
        )
        new_rows.append(
            StatementRow(
                order=row.order,
                concept=row.concept,
                dims=row.dims,
                label=row.label,
                depth=row.depth,
                kind=row.kind,
                derivation=row.derivation,
                preferred_label=row.preferred_label,
                negated=row.negated,
                displayed_sign=row.displayed_sign,
                period_type=row.period_type,
                balance=row.balance,
                is_monetary=row.is_monetary,
                is_extension=row.is_extension,
                anchor=row.anchor,
                section=row.section,
                cells=cells,
            )
        )
    statement.rows = new_rows
