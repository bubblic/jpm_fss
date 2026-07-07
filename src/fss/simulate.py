"""Monte Carlo simulation and the directional scenario battery.

The stochastic fan runs in TensorFlow (fss.tfsim): all paths of a scenario
execute as one vectorized float64 pass, following the batched-tensor
pattern of previous_llm_extractor, with per-path numeric identity checks.
Selected paths (the median-net-income path and the noise-free path) are
replayed bit-exactly through the Decimal engine, fed with the very shocks
TensorFlow drew, to produce the audit artifacts: full native statements
and the flow journal. Common random numbers across scenarios make mean
differences measure the scenario response.

Before any simulation, the firm's flow system is verified symbolically
(fss.symbolic): the accounting identity must cancel for all parameter
values and the computation DAG must be acyclic.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal
from statistics import median

from fss.config import MONTE_CARLO_PATHS, RANDOM_SEED
from fss.drivers import SCENARIOS, Scenario, draw_from_shocks, realize
from fss.engine.project import ProjectedPeriod, Projector
from fss.statements import StructuredStatement
from fss.symbolic import SymbolicVerdict, verify_engine_closure


@dataclass
class ScenarioResult:
    scenario: Scenario
    paths: int
    metrics: dict[str, list[Decimal]]  # metric -> per-path values
    representative: ProjectedPeriod  # the median-net-income path
    deterministic: ProjectedPeriod  # noise-free path (scenario response only)
    violations: int  # paths with any identity/plausibility violation
    max_residual: Decimal = Decimal(0)  # largest |A-(L+E)| delta across paths

    def mean(self, metric: str) -> Decimal:
        values = self.metrics[metric]
        return sum(values, Decimal(0)) / len(values)

    def quantile(self, metric: str, q: Decimal) -> Decimal:
        values = sorted(self.metrics[metric])
        index = int(q * (len(values) - 1))
        return values[index]


def run_scenario_tf(
    projector: Projector,
    compiled_firm,
    scenario: Scenario,
    paths: int,
    seed: int,
) -> ScenarioResult:
    """The TensorFlow fan plus Decimal replays of the paths that matter."""
    import numpy as np

    from fss import tfsim

    base_growth = projector.base_growth()
    fan = tfsim.simulate_paths(compiled_firm, scenario, paths, seed)
    metrics = {
        name: [Decimal(repr(float(value))) for value in values]
        for name, values in fan.metrics.items()
    }
    ni = fan.metrics["net_income"]
    median_index = int(np.argsort(ni)[len(ni) // 2])
    eps = fan.shocks[median_index]
    representative = projector.project(
        draw_from_shocks(
            scenario,
            base_growth,
            Decimal(repr(float(eps[0]))),
            Decimal(repr(float(eps[1]))),
            Decimal(repr(float(eps[2]))),
        )
    )
    deterministic = projector.project(
        draw_from_shocks(scenario, base_growth, Decimal(0), Decimal(0), Decimal(0))
    )
    violations = fan.identity_violations
    if representative.violations or deterministic.violations:
        violations += 1
    return ScenarioResult(
        scenario=scenario,
        paths=paths,
        metrics=metrics,
        representative=representative,
        deterministic=deterministic,
        violations=violations,
        max_residual=Decimal(repr(fan.max_residual)),
    )


def run_scenario(
    company: str,
    statements: dict[str, StructuredStatement],
    scenario: Scenario,
    paths: int = MONTE_CARLO_PATHS,
    seed: int = RANDOM_SEED,
    backend: str = "tf",
) -> ScenarioResult:
    projector = Projector(company, statements)
    if backend == "tf":
        from fss import tfsim

        return run_scenario_tf(projector, tfsim.compile_firm(projector), scenario, paths, seed)
    base_growth = projector.base_growth()
    metrics: dict[str, list[Decimal]] = {}
    results: list[ProjectedPeriod] = []
    violations = 0
    for path_index in range(paths):
        # common random numbers: the noise stream depends on the path index,
        # not the scenario, so scenario mean differences measure the scenario
        # response rather than sampling noise
        rng = random.Random(f"{seed}:{company}:{path_index}")
        draw = realize(scenario, base_growth, rng, stochastic=True)
        period = projector.project(draw)
        results.append(period)
        if period.violations:
            violations += 1
        for name, value in period.metrics.items():
            metrics.setdefault(name, []).append(value)
    deterministic = projector.project(
        realize(scenario, base_growth, random.Random(f"{seed}:{company}:det"), stochastic=False)
    )
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
    backend: str = "tf",
) -> tuple[dict[str, ScenarioResult], SymbolicVerdict]:
    """Symbolic verification first, then every scenario's fan.

    Mirrors the interns' pipeline: SymPy equations -> symbolic checking ->
    TensorFlow operations -> numerical checking. A firm whose flow system
    does not cancel symbolically is refused simulation outright.
    """
    projector = Projector(company, statements)
    verdict = verify_engine_closure(projector)
    if not verdict.balanced or not verdict.acyclic:
        raise RuntimeError(
            f"symbolic verification failed for {company}: residual "
            f"{verdict.residual}, culprits {verdict.culprits}, acyclic {verdict.acyclic}"
        )
    if backend == "tf":
        from fss import tfsim

        compiled_firm = tfsim.compile_firm(projector)
        results = {
            key: run_scenario_tf(projector, compiled_firm, scenario, paths, seed)
            for key, scenario in SCENARIOS.items()
        }
    else:
        results = {
            key: run_scenario(company, statements, scenario, paths, seed, backend)
            for key, scenario in SCENARIOS.items()
        }
    return results, verdict


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
