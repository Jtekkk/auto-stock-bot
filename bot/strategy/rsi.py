"""RSI mean-reversion.

Enter long when RSI climbs back above the oversold threshold (a bounce), exit
when it reaches the overbought threshold. Counter-trend complement to the SMA
crossover strategy.
"""

from __future__ import annotations

from bot.indicators import rsi as rsi_series
from bot.strategy.base import Strategy, _hold, register
from bot.types import Bar, Signal, SignalType


@register("rsi")
class RSIReversion(Strategy):
    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        if not 0 < oversold < overbought < 100:
            raise ValueError("rsi: require 0 < oversold < overbought < 100")
        self.period = int(period)
        self.oversold = float(oversold)
        self.overbought = float(overbought)

    @property
    def warmup(self) -> int:
        return self.period + 2

    def evaluate(self, bars: list[Bar], holding: bool) -> Signal:
        if len(bars) < self.warmup:
            return _hold(bars, "warming up")

        closes = [b.close for b in bars]
        values = rsi_series(closes, self.period)
        now, prev = values[-1], values[-2]
        if now is None or prev is None:
            return _hold(bars, "insufficient data")

        last = bars[-1]
        # Entry: crossing up out of oversold territory.
        if not holding and prev <= self.oversold < now:
            strength = max(0.3, min(1.0, (self.oversold - prev + 5) / 20))
            return Signal(
                last.symbol,
                SignalType.ENTER_LONG,
                last.timestamp,
                strength,
                f"RSI({self.period}) recovered from oversold ({prev:.1f} -> {now:.1f})",
            )
        # Exit: reached overbought.
        if holding and now >= self.overbought:
            return Signal(
                last.symbol,
                SignalType.EXIT_LONG,
                last.timestamp,
                1.0,
                f"RSI({self.period})={now:.1f} reached overbought",
            )
        return _hold(bars)
