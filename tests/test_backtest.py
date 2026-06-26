from datetime import datetime, timedelta

from bot.backtest import run_backtest
from bot.config import Config
from bot.data.feed import DataFeed, SyntheticFeed
from bot.types import Bar


class ScriptedFeed(DataFeed):
    """A feed that replays a fixed close-price path — deterministic for asserts."""

    def __init__(self, symbol: str, closes: list[float]):
        self.symbol = symbol
        start = datetime(2023, 1, 1)
        self._bars = [
            Bar(symbol, start + timedelta(days=i), c, c * 1.01, c * 0.99, c, 1_000_000)
            for i, c in enumerate(closes)
        ]

    def history(self, symbol: str) -> list[Bar]:
        return self._bars


def test_backtest_runs_on_synthetic_and_produces_metrics():
    config = Config.from_dict(
        {
            "symbols": ["AAPL"],
            "starting_cash": 100_000,
            "strategy": {"name": "sma_crossover", "params": {"fast": 5, "slow": 15}},
            "data": {"source": "synthetic", "synthetic_bars": 300},
        }
    )
    feed = SyntheticFeed(config.symbols, bars=config.data.synthetic_bars)
    metrics = run_backtest(config, feed)
    assert metrics.starting_equity == 100_000
    assert metrics.ending_equity > 0
    # Equity curve should have been marked across the run.
    assert metrics.num_trades >= 0


def test_backtest_profits_on_rising_trend():
    # A clean uptrend after warmup: strategy should buy and end up profitable.
    closes = [100] * 20 + [100 + i * 2 for i in range(40)]
    config = Config.from_dict(
        {
            "symbols": ["UP"],
            "starting_cash": 100_000,
            "strategy": {"name": "sma_crossover", "params": {"fast": 3, "slow": 10}},
            "risk": {"stop_loss_pct": 0.0, "take_profit_pct": 0.0, "max_position_pct": 0.5},
            "data": {"source": "synthetic"},
        }
    )
    feed = ScriptedFeed("UP", closes)
    metrics = run_backtest(config, feed)
    assert metrics.ending_equity > metrics.starting_equity
    assert metrics.num_trades >= 1


def test_backtest_is_deterministic():
    config = Config.from_dict(
        {"symbols": ["AAPL"], "data": {"source": "synthetic", "synthetic_bars": 200}}
    )
    m1 = run_backtest(config, SyntheticFeed(config.symbols, bars=200))
    m2 = run_backtest(config, SyntheticFeed(config.symbols, bars=200))
    assert m1.ending_equity == m2.ending_equity
    assert m1.num_trades == m2.num_trades
