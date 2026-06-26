"""Grid-search parameter optimization for strategies.

Sweeps a strategy's parameters over a grid, runs a backtest for each
combination on the same data, and ranks them by a chosen metric. Useful for
finding sensible defaults — but beware overfitting: a result that looks great
in-sample may not generalize. Validate winners on held-out / out-of-sample data.
"""

from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass, field
from typing import Any

from bot.backtest import run_backtest
from bot.config import Config
from bot.data.feed import build_feed
from bot.metrics import Metrics
from bot.strategy.base import build_strategy

# Metrics where larger is better (used for ranking direction).
_RANKABLE = {
    "total_return_pct",
    "sharpe",
    "profit_factor",
    "win_rate_pct",
    "ending_equity",
}


@dataclass
class OptimizationResult:
    params: dict[str, Any]
    metrics: Metrics


@dataclass
class OptimizationReport:
    metric: str
    results: list[OptimizationResult] = field(default_factory=list)

    @property
    def best(self) -> OptimizationResult | None:
        return self.results[0] if self.results else None

    def render(self, top: int = 10) -> str:
        lines = [
            "=" * 64,
            f"  OPTIMIZATION (ranked by {self.metric}, {len(self.results)} combos)",
            "=" * 64,
        ]
        for i, r in enumerate(self.results[:top], 1):
            value = getattr(r.metrics, self.metric)
            params = ", ".join(f"{k}={v}" for k, v in r.params.items())
            lines.append(
                f"  {i:>2}. {value:>10.3f}  "
                f"[ret {r.metrics.total_return_pct:+6.2f}%  "
                f"dd {r.metrics.max_drawdown_pct:5.2f}%  "
                f"trades {r.metrics.num_trades:>3}]  {params}"
            )
        lines.append("=" * 64)
        return "\n".join(lines)


def grid_search(
    config: Config,
    param_grid: dict[str, list[Any]],
    metric: str = "sharpe",
) -> OptimizationReport:
    """Backtest every combination in ``param_grid`` and rank by ``metric``."""
    if metric not in _RANKABLE:
        raise ValueError(f"Cannot rank by {metric!r}. Choose one of: {sorted(_RANKABLE)}")
    if not param_grid:
        raise ValueError("param_grid is empty")

    keys = list(param_grid)
    combos = list(itertools.product(*(param_grid[k] for k in keys)))
    results: list[OptimizationResult] = []

    for combo in combos:
        params = dict(zip(keys, combo))
        trial = copy.deepcopy(config)
        trial.strategy.params = {**config.strategy.params, **params}

        # Skip parameter combinations the strategy rejects (e.g. fast >= slow).
        try:
            build_strategy(trial.strategy.name, trial.strategy.params)
        except ValueError:
            continue

        # Fresh feed per trial so cached state never leaks between runs.
        feed = build_feed(trial.data, trial.symbols)
        metrics = run_backtest(trial, feed)
        results.append(OptimizationResult(params, metrics))

    # Rank descending; treat non-finite (e.g. inf profit factor) as worst-last.
    def sort_key(r: OptimizationResult) -> float:
        v = getattr(r.metrics, metric)
        return v if v != float("inf") else float("1e18")

    results.sort(key=sort_key, reverse=True)
    return OptimizationReport(metric=metric, results=results)


def parse_grid(spec: str) -> dict[str, list[Any]]:
    """Parse a CLI grid spec like ``fast=5,10,15;slow=20,30`` into a dict.

    Numeric-looking values are coerced to int/float; everything else stays str.
    """
    grid: dict[str, list[Any]] = {}
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Bad grid segment {part!r} (expected key=v1,v2,...)")
        key, values = part.split("=", 1)
        grid[key.strip()] = [_coerce(v.strip()) for v in values.split(",") if v.strip()]
    return grid


def _coerce(value: str) -> Any:
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            continue
    return value
