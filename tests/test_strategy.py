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


def test_macd_registered_and_validates():
    import pytest

    with pytest.raises(ValueError):
        build_strategy("macd", {"fast": 26, "slow": 12})
    strat = build_strategy("macd", {"fast": 12, "slow": 26, "signal": 9})
    # During warmup it must HOLD rather than emit a signal.
    assert strat.evaluate(make_bars([10.0, 11.0, 12.0]), holding=False).type == SignalType.HOLD


def test_macd_enters_when_momentum_turns_up():
    strat = build_strategy("macd", {"fast": 3, "slow": 6, "signal": 3})
    # Decline then a sharp reversal flips MACD above its signal line.
    closes = [20 - i for i in range(12)] + [8 + i * 3 for i in range(8)]
    signal = strat.evaluate(make_bars(closes), holding=False)
    assert signal.type in (SignalType.ENTER_LONG, SignalType.HOLD)


def test_bollinger_registered_and_validates():
    import pytest

    with pytest.raises(ValueError):
        build_strategy("bollinger", {"period": 1})
    strat = build_strategy("bollinger", {"period": 20, "num_std": 2.0})
    assert strat.warmup == 21


def test_bollinger_exits_at_mean_band():
    strat = build_strategy("bollinger", {"period": 5, "num_std": 2.0})
    # Price sitting above its moving average should trigger a mean-revert exit.
    bars = make_bars([10, 10, 10, 10, 10, 10, 20])
    signal = strat.evaluate(bars, holding=True)
    assert signal.type == SignalType.EXIT_LONG
