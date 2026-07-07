"""Symbolic closure and TF-vs-Decimal agreement on the tagged set.

Skipped when the cached extracted statements are absent (clean clone
before `fss extract`).
"""
from decimal import Decimal
from pathlib import Path

import pytest

DATA = Path("data/extracted")
COMPANIES = ("apple", "microsoft", "sap", "spotify")

pytestmark = pytest.mark.skipif(
    not (DATA / "apple_balance_sheet.json").exists(),
    reason="extracted statements not present; run `python -m fss extract`",
)


def _statements(key):
    from fss.statements import StructuredStatement

    return {
        kind: StructuredStatement.load(DATA / f"{key}_{kind}.json")
        for kind in ("balance_sheet", "income_statement", "cash_flow")
    }


@pytest.mark.parametrize("key", COMPANIES)
def test_symbolic_closure_proven(key):
    from fss.engine.project import Projector
    from fss.symbolic import verify_engine_closure

    verdict = verify_engine_closure(Projector(key, _statements(key)))
    assert verdict.balanced, f"residual {verdict.residual}, culprits {verdict.culprits}"
    assert verdict.acyclic
    assert verdict.execution_order  # topological order exists


@pytest.mark.parametrize("key", COMPANIES)
def test_tf_agrees_with_decimal_engine(key):
    from fss import tfsim
    from fss.drivers import SCENARIOS, draw_from_shocks
    from fss.engine.project import Projector

    statements = _statements(key)
    projector = Projector(key, statements)
    firm = tfsim.compile_firm(projector)
    fan = tfsim.simulate_paths(firm, SCENARIOS["recession"], paths=16, seed=11)
    assert fan.identity_violations == 0
    assert fan.max_residual <= 1.0
    eps = fan.shocks[0]
    period = projector.project(
        draw_from_shocks(
            SCENARIOS["recession"],
            projector.base_growth(),
            Decimal(repr(float(eps[0]))),
            Decimal(repr(float(eps[1]))),
            Decimal(repr(float(eps[2]))),
        )
    )
    assert not period.violations
    for metric in ("revenue", "net_income", "cash"):
        tf_value = float(fan.metrics[metric][0])
        decimal_value = float(period.metrics[metric])
        assert abs(tf_value - decimal_value) <= max(abs(decimal_value), 1.0) * 5e-6
