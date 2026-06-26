import pytest

from bot.config import Config
from bot.optimize import grid_search, parse_grid


def test_parse_grid_coerces_types():
    grid = parse_grid("fast=5,10,15;slow=20,30")
    assert grid == {"fast": [5, 10, 15], "slow": [20, 30]}


def test_parse_grid_handles_floats_and_strings():
    grid = parse_grid("num_std=1.5,2.0;mode=fast")
    assert grid == {"num_std": [1.5, 2.0], "mode": ["fast"]}


def test_parse_grid_rejects_bad_segment():
    with pytest.raises(ValueError):
        parse_grid("fast")


def test_grid_search_ranks_and_skips_invalid_combos():
    config = Config.from_dict(
        {
            "symbols": ["AAPL"],
            "strategy": {"name": "sma_crossover"},
            "data": {"source": "synthetic", "synthetic_bars": 200},
        }
    )
    # Includes invalid combos (fast >= slow) which must be skipped, not crash.
    report = grid_search(
        config, {"fast": [5, 10, 30], "slow": [10, 30]}, metric="total_return_pct"
    )
    assert report.results, "expected at least one valid combo"
    # fast=30, slow=10 and fast=10,slow=10 etc. are invalid and excluded.
    for r in report.results:
        assert r.params["fast"] < r.params["slow"]
    # Results sorted descending by the chosen metric.
    values = [getattr(r.metrics, "total_return_pct") for r in report.results]
    assert values == sorted(values, reverse=True)


def test_grid_search_rejects_unrankable_metric():
    config = Config.from_dict({"symbols": ["AAPL"], "data": {"source": "synthetic"}})
    with pytest.raises(ValueError):
        grid_search(config, {"fast": [5]}, metric="max_drawdown_pct")
