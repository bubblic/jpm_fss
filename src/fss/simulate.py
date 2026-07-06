"""Monte Carlo simulation and the directional scenario battery.

For a fixed scenario the driver noise is sampled N times and every path is
propagated through the engine, so the output is a distribution of complete,
internally consistent statements. The directional battery compares scenario
means against the baseline with the signs economics requires.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal
from statistics import median

from fss.config import MONTE_CARLO_PATHS, RANDOM_SEED
from fss.drivers import SCENARIOS, Scenario, realize
from fss.engine.project import ProjectedPeriod, Projector
from fss.statements import StructuredStatement


@dataclass
class ScenarioResult:
    scenario: Scenario
    paths: int
    metrics: dict[str, list[Decimal]]  # metric -> per-path values
    representative: ProjectedPeriod  # the median-net-income path
    deterministic: ProjectedPeriod  # noise-free path (scenario response only)
    violations: int  # paths with any identity/plausibility violation

    def mean(self, metric: str) -> Decimal:
        values = self.metrics[metric]
        return sum(values, Decimal(0)) / len(values)

    def quantile(self, metric: str, q: Decimal) -> Decimal:
        values = sorted(self.metrics[metric])
        index = int(q * (len(values) - 1))
        return values[index]


def run_scenario(
    company: str,
    statements: dict[str, StructuredStatement],
    scenario: Scenario,
    paths: int = MONTE_CARLO_PATHS,
    seed: int = RANDOM_SEED,
) -> ScenarioResult:
    projector = Projector(company, statements)
    base_growth = projector.base_growth()
    rng = random.Random(f"{seed}:{company}:{scenario.key}")
    metrics: dict[str, list[Decimal]] = {}
    results: list[ProjectedPeriod] = []
    violations = 0
    for _ in range(paths):
        draw = realize(scenario, base_growth, rng, stochastic=True)
        period = projector.project(draw)
        results.append(period)
        if period.violations:
            violations += 1
        for name, value in period.metrics.items():
            metrics.setdefault(name, []).append(value)
    deterministic = projector.project(realize(scenario, base_growth, rng, stochastic=False))
    ni_values = metrics["net_income"]
    med = median(ni_values)
    representative = min(results, key=lambda r: abs(r.metrics["net_income"] - med))
    return ScenarioResult(
        scenario=scenario,
        paths=paths,
        metrics=metrics,
        representative=representative,
        deterministic=deterministic,
        violations=violations,
    )


def run_all_scenarios(
    company: str,
    statements: dict[str, StructuredStatement],
    paths: int = MONTE_CARLO_PATHS,
    seed: int = RANDOM_SEED,
) -> dict[str, ScenarioResult]:
    return {
        key: run_scenario(company, statements, scenario, paths, seed)
        for key, scenario in SCENARIOS.items()
    }


@dataclass(frozen=True)
class DirectionalCheck:
    name: str
    detail: str
    passed: bool


def directional_battery(
    results: dict[str, ScenarioResult], net_cash_position: Decimal
) -> list[DirectionalCheck]:
    """Scenario means must move the way the economics says they must."""
    base = results["baseline"]
    checks: list[DirectionalCheck] = []

    def compare(name: str, scenario: str, metric: str, direction: int) -> None:
        moved = results[scenario].mean(metric) - base.mean(metric)
        passed = moved > 0 if direction > 0 else moved < 0
        checks.append(
            DirectionalCheck(
                name,
                f"{scenario} vs baseline, mean {metric}: "
                f"{moved:+,.0f}" if metric != "gross_margin_bp" else
                f"{scenario} vs baseline, mean {metric}: {moved:+.0f}bp",
                passed,
            )
        )

    compare("expansion raises revenue", "expansion", "revenue", +1)
    compare("expansion raises net income", "expansion", "net_income", +1)
    compare("recession lowers revenue", "recession", "revenue", -1)
    compare("recession lowers net income", "recession", "net_income", -1)
    compare("competition lowers net income", "competition", "net_income", -1)
    compare("competition compresses gross margin", "competition", "gross_margin_bp", -1)
    compare("inflation lowers net income", "inflation", "net_income", -1)
    rate_direction = +1 if net_cash_position > 0 else -1
    compare(
        "rate hike moves income with the firm's net cash position",
        "rate_hike",
        "net_income",
        rate_direction,
    )
    return checks
