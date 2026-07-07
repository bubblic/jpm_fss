"""Scenario schema and the driver-to-flow layer.

A Scenario is the macro/industry conditioning; a DriverDraw is one realized
set of firm-level driver values (deterministic response plus sampled noise)
that the engine consumes. Responses are reasoned and nonlinear where the
economics demand it, per the proposal's Part I bar: solid, robust,
directionally credible, not fitted.

All arithmetic is Decimal; noise is drawn from a seeded generator and
rounded to six places so runs reproduce bit for bit.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal

from fss.config import MARGIN_SIGMA, OPEX_SIGMA, REVENUE_SIGMA


@dataclass(frozen=True)
class Scenario:
    key: str
    description: str
    gdp_growth_pp: Decimal  # real GDP growth deviation from trend, percentage points
    inflation_pp: Decimal  # inflation deviation from target, percentage points
    rate_shift_bp: Decimal  # parallel shift in short rates, basis points
    competition_z: Decimal  # industry competitive-intensity shock, z-score
    demand_z: Decimal  # firm-specific demand shock, z-score


SCENARIOS: dict[str, Scenario] = {
    "baseline": Scenario(
        "baseline",
        "Trend growth, target inflation, unchanged rates and competition.",
        Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"),
    ),
    "expansion": Scenario(
        "expansion",
        "GDP 2pp above trend with mild demand tailwind.",
        Decimal("2"), Decimal("0.5"), Decimal("50"), Decimal("0"), Decimal("0.5"),
    ),
    "recession": Scenario(
        "recession",
        "GDP 2.5pp below trend, easing rates, weak demand.",
        Decimal("-2.5"), Decimal("-0.5"), Decimal("-150"), Decimal("0"), Decimal("-1"),
    ),
    "competition": Scenario(
        "competition",
        "Intensified industry competition; macro on trend.",
        Decimal("0"), Decimal("0"), Decimal("0"), Decimal("1.5"), Decimal("0"),
    ),
    "rate_hike": Scenario(
        "rate_hike",
        "Rates 200bp higher; growth briefly unchanged.",
        Decimal("0"), Decimal("0.5"), Decimal("200"), Decimal("0"), Decimal("0"),
    ),
    "inflation": Scenario(
        "inflation",
        "Cost inflation 3pp above target without extra demand; a pure "
        "cost-side shock (rate response isolated in the rate_hike scenario).",
        Decimal("0"), Decimal("3"), Decimal("0"), Decimal("0"), Decimal("0"),
    ),
}

# Response parameters (documented in the proposal).
BETA_GDP = Decimal("1.6")  # tech revenue elasticity to GDP surprises
BETA_DEMAND = Decimal("0.02")  # revenue response per demand z-score
COMPETITION_REVENUE = Decimal("0.015")  # revenue drag per competition z
COMPETITION_MARGIN = Decimal("0.012")  # gross-margin ratio drag per competition z
INFLATION_COGS_PASS = Decimal("0.5")  # share of inflation not recovered in price
INFLATION_OPEX_PASS = Decimal("0.5")
INFLATION_REVENUE_PASS = Decimal("0.2")  # partial nominal passthrough to revenue
OPEX_REVENUE_BETA = Decimal("0.6")  # semi-variable opex response to revenue growth
RATE_PASSTHROUGH_ASSETS = Decimal("0.6")  # cash/securities reprice quickly
RATE_PASSTHROUGH_DEBT = Decimal("0.15")  # mostly fixed-rate term debt
MOMENTUM_WEIGHT = Decimal("0.6")  # weight on the firm's own trailing growth


@dataclass(frozen=True)
class DriverDraw:
    """One realized driver path for one simulated period."""

    revenue_growth: Decimal
    cogs_ratio_shift: Decimal  # additive shift to cogs/revenue ratio
    opex_growth: Decimal
    restructuring_factor: Decimal
    asset_yield_shift: Decimal  # additive shift to yield on cash + securities
    debt_rate_shift: Decimal
    tax_rate_shift: Decimal
    dividend_growth: Decimal
    buyback_factor: Decimal


def _dec(value: float) -> Decimal:
    return Decimal(str(round(value, 6)))


def draw_from_shocks(
    scenario: Scenario,
    base_growth: Decimal,
    eps_g: Decimal,
    eps_m: Decimal,
    eps_o: Decimal,
) -> DriverDraw:
    """The deterministic scenario response for given noise shocks.

    This is the single source of truth for the driver map: the Decimal
    engine and the TensorFlow simulation both express exactly these
    formulas, and the agreement test in tests/ holds them together.
    """
    momentum = MOMENTUM_WEIGHT * base_growth
    macro = (
        BETA_GDP * scenario.gdp_growth_pp + INFLATION_REVENUE_PASS * scenario.inflation_pp
    ) / 100
    demand = BETA_DEMAND * scenario.demand_z
    competition_drag = COMPETITION_REVENUE * scenario.competition_z
    revenue_growth = momentum + macro + demand - competition_drag + eps_g
    # a floor: even severe scenarios rarely halve a large firm's revenue
    revenue_growth = max(revenue_growth, Decimal("-0.35"))

    cogs_ratio_shift = (
        COMPETITION_MARGIN * scenario.competition_z
        + INFLATION_COGS_PASS * scenario.inflation_pp / 100
        + eps_m
    )
    opex_growth = (
        OPEX_REVENUE_BETA * revenue_growth
        + INFLATION_OPEX_PASS * scenario.inflation_pp / 100
        + eps_o
    )
    restructuring_factor = Decimal("0.5") + (
        Decimal("0.5") if scenario.gdp_growth_pp < 0 or scenario.competition_z > 1 else Decimal(0)
    )
    asset_yield_shift = RATE_PASSTHROUGH_ASSETS * scenario.rate_shift_bp / 10000
    debt_rate_shift = RATE_PASSTHROUGH_DEBT * scenario.rate_shift_bp / 10000
    dividend_growth = max(Decimal(0), min(revenue_growth, Decimal("0.10")))
    buyback_factor = Decimal(1) if scenario.gdp_growth_pp >= Decimal("-1") else Decimal("0.5")
    return DriverDraw(
        revenue_growth=revenue_growth,
        cogs_ratio_shift=cogs_ratio_shift,
        opex_growth=opex_growth,
        restructuring_factor=restructuring_factor,
        asset_yield_shift=asset_yield_shift,
        debt_rate_shift=debt_rate_shift,
        tax_rate_shift=Decimal(0),
        dividend_growth=dividend_growth,
        buyback_factor=buyback_factor,
    )


def realize(
    scenario: Scenario,
    base_growth: Decimal,
    rng: random.Random,
    stochastic: bool = True,
) -> DriverDraw:
    """Map (scenario, firm momentum, sampled noise) to one driver draw."""
    eps_g = _dec(rng.gauss(0.0, float(REVENUE_SIGMA))) if stochastic else Decimal(0)
    eps_m = _dec(rng.gauss(0.0, float(MARGIN_SIGMA))) if stochastic else Decimal(0)
    eps_o = _dec(rng.gauss(0.0, float(OPEX_SIGMA))) if stochastic else Decimal(0)
    return draw_from_shocks(scenario, base_growth, eps_g, eps_m, eps_o)
