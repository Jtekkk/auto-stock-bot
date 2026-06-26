"""Bollinger Band mean reversion.

Enter long when price closes back above the lower band after dipping below it
(a bounce); exit when price reaches the middle band (the moving average) or the
upper band. Counter-trend, like RSI but volatility-scaled.
"""

from __future__ import annotations

from bot.indicators import bollinger as bollinger_series
from bot.strategy.base import Strategy, _hold, register
from bot.types import Bar, Signal, SignalType


@register("bollinger")
class BollingerReversion(Strategy):
    def __init__(self, period: int = 20, num_std: float = 2.0):
        if period <= 1:
            raise ValueError("bollinger: period must be > 1")
        if num_std <= 0:
            raise ValueError("bollinger: num_std must be > 0")
        self.period = int(period)
        self.num_std = float(num_std)

    @property
    def warmup(self) -> int:
        return self.period + 1

    def evaluate(self, bars: list[Bar], holding: bool) -> Signal:
        if len(bars) < self.warmup:
            return _hold(bars, "warming up")

        closes = [b.close for b in bars]
        middle, _, lower = bollinger_series(closes, self.period, self.num_std)
        mid_now = middle[-1]
        low_now, low_prev = lower[-1], lower[-2]
        if None in (mid_now, low_now, low_prev):
            return _hold(bars, "insufficient data")

        price_now, price_prev = closes[-1], closes[-2]
        last = bars[-1]

        # Entry: dipped below the lower band, then closed back above it.
        if not holding and price_prev < low_prev and price_now >= low_now:
            band_width = (mid_now - low_now) or 1e-9
            strength = max(0.3, min(1.0, (low_prev - price_prev) / band_width + 0.3))
            return Signal(
                last.symbol,
                SignalType.ENTER_LONG,
                last.timestamp,
                strength,
                f"price {price_now:.2f} reclaimed lower band {low_now:.2f}",
            )
        # Exit: reverted up to the middle band (mean).
        if holding and price_now >= mid_now:
            return Signal(
                last.symbol,
                SignalType.EXIT_LONG,
                last.timestamp,
                1.0,
                f"price {price_now:.2f} reached mean band {mid_now:.2f}",
            )
        return _hold(bars)
