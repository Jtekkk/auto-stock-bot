from datetime import datetime, timedelta

from bot.strategy.base import build_strategy
from bot.types import Bar, SignalType


def make_bars(closes: list[float], symbol: str = "TEST") -> list[Bar]:
    start = datetime(2023, 1, 1)
    return [
        Bar(symbol, start + timedelta(days=i), c, c, c, c, 1000)
        for i, c in enumerate(closes)
    ]


def test_sma_crossover_validates_periods():
    import pytest

    with pytest.raises(ValueError):
        build_strategy("sma_crossover", {"fast": 30, "slow": 10})


def test_sma_crossover_enters_on_golden_cross():
    strat = build_strategy("sma_crossover", {"fast": 3, "slow": 5})
    # Flat, then a jump on the final bar makes the fast SMA cross above the slow.
    closes = [10] * 8 + [20]
    bars = make_bars(closes)
    signal = strat.evaluate(bars, holding=False)
    assert signal.type == SignalType.ENTER_LONG
    assert 0 < signal.strength <= 1.0


def test_sma_crossover_holds_during_warmup():
    strat = build_strategy("sma_crossover", {"fast": 3, "slow": 5})
    bars = make_bars([10, 11, 12])
    assert strat.evaluate(bars, holding=False).type == SignalType.HOLD


def test_sma_crossover_exits_on_death_cross():
    strat = build_strategy("sma_crossover", {"fast": 3, "slow": 5})
    # High plateau (fast above slow), then a drop on the final bar crosses down.
    closes = [10] * 3 + [20] * 5 + [10]
    bars = make_bars(closes)
    signal = strat.evaluate(bars, holding=True)
    assert signal.type == SignalType.EXIT_LONG


def test_rsi_strategy_validates_thresholds():
    import pytest

    with pytest.raises(ValueError):
        build_strategy("rsi", {"oversold": 80, "overbought": 20})


def test_rsi_exits_when_overbought():
    strat = build_strategy("rsi", {"period": 5, "oversold": 30, "overbought": 70})
    # Strictly rising series drives RSI to 100 -> overbought exit when holding.
    bars = make_bars([float(i) for i in range(20)])
    signal = strat.evaluate(bars, holding=True)
    assert signal.type == SignalType.EXIT_LONG
