"""Driver responses move the way the economics requires."""
import random
from decimal import Decimal

from fss.drivers import SCENARIOS, realize

BASE_GROWTH = Decimal("0.06")


def _draw(key):
    return realize(SCENARIOS[key], BASE_GROWTH, random.Random(0), stochastic=False)


def test_expansion_raises_growth():
    assert _draw("expansion").revenue_growth > _draw("baseline").revenue_growth


def test_recession_lowers_growth():
    assert _draw("recession").revenue_growth < _draw("baseline").revenue_growth


def test_competition_squeezes_margin_and_revenue():
    base, comp = _draw("baseline"), _draw("competition")
    assert comp.cogs_ratio_shift > base.cogs_ratio_shift
    assert comp.revenue_growth < base.revenue_growth


def test_rate_hike_moves_yields():
    hike = _draw("rate_hike")
    assert hike.asset_yield_shift > 0
    assert hike.debt_rate_shift > 0
    assert hike.asset_yield_shift > hike.debt_rate_shift  # assets reprice faster


def test_inflation_hits_costs():
    inflation = _draw("inflation")
    assert inflation.cogs_ratio_shift > 0
    assert inflation.opex_growth > _draw("baseline").opex_growth
