"""MACD crossover.

Enter long when the MACD line crosses above its signal line (momentum turning
up); exit when it crosses back below. Like an EMA-based, smoother cousin of the
SMA crossover.
"""

from __future__ import annotations

from bot.indicators import macd as macd_series
from bot.strategy.base import Strategy, _hold, register
from bot.types import Bar, Signal, SignalType


@register("macd")
class MACDCross(Strategy):
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        if fast >= slow:
            raise ValueError("macd: fast period must be < slow period")
        self.fast = int(fast)
        self.slow = int(slow)
        self.signal = int(signal)

    @property
    def warmup(self) -> int:
        # slow EMA + signal EMA to populate, plus one bar to detect a cross.
        return self.slow + self.signal + 1

    def evaluate(self, bars: list[Bar], holding: bool) -> Signal:
        if len(bars) < self.warmup:
            return _hold(bars, "warming up")

        closes = [b.close for b in bars]
        macd_line, signal_line, _ = macd_series(closes, self.fast, self.slow, self.signal)
        m_now, m_prev = macd_line[-1], macd_line[-2]
        s_now, s_prev = signal_line[-1], signal_line[-2]
        if None in (m_now, m_prev, s_now, s_prev):
            return _hold(bars, "insufficient data")

        last = bars[-1]
        crossed_up = m_prev <= s_prev and m_now > s_now
        crossed_down = m_prev >= s_prev and m_now < s_now

        if crossed_up and not holding:
            strength = max(0.3, min(1.0, abs(m_now - s_now) / (abs(s_now) + 1e-9)))
            return Signal(
                last.symbol,
                SignalType.ENTER_LONG,
                last.timestamp,
                strength,
                f"MACD {m_now:.3f} crossed above signal {s_now:.3f}",
            )
        if crossed_down and holding:
            return Signal(
                last.symbol,
                SignalType.EXIT_LONG,
                last.timestamp,
                1.0,
                f"MACD {m_now:.3f} crossed below signal {s_now:.3f}",
            )
        return _hold(bars)
