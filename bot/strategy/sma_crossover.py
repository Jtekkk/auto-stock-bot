"""Simple moving-average crossover.

Enter long when the fast SMA crosses above the slow SMA (momentum turning up);
exit when it crosses back below. A classic trend-following baseline.
"""

from __future__ import annotations

from bot.indicators import sma
from bot.strategy.base import Strategy, _hold, register
from bot.types import Bar, Signal, SignalType


@register("sma_crossover")
class SMACrossover(Strategy):
    def __init__(self, fast: int = 10, slow: int = 30):
        if fast >= slow:
            raise ValueError("sma_crossover: fast period must be < slow period")
        self.fast = int(fast)
        self.slow = int(slow)

    @property
    def warmup(self) -> int:
        # Need one extra bar to detect a crossover (compare prev vs current).
        return self.slow + 1

    def evaluate(self, bars: list[Bar], holding: bool) -> Signal:
        if len(bars) < self.warmup:
            return _hold(bars, "warming up")

        closes = [b.close for b in bars]
        fast = sma(closes, self.fast)
        slow = sma(closes, self.slow)

        fast_now, fast_prev = fast[-1], fast[-2]
        slow_now, slow_prev = slow[-1], slow[-2]
        if None in (fast_now, fast_prev, slow_now, slow_prev):
            return _hold(bars, "insufficient data")

        last = bars[-1]
        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now

        if crossed_up and not holding:
            gap = (fast_now - slow_now) / slow_now
            strength = max(0.3, min(1.0, gap * 50))
            return Signal(
                last.symbol,
                SignalType.ENTER_LONG,
                last.timestamp,
                strength,
                f"fast SMA({self.fast})={fast_now:.2f} crossed above "
                f"slow SMA({self.slow})={slow_now:.2f}",
            )
        if crossed_down and holding:
            return Signal(
                last.symbol,
                SignalType.EXIT_LONG,
                last.timestamp,
                1.0,
                f"fast SMA({self.fast}) crossed below slow SMA({self.slow})",
            )
        return _hold(bars)
