"""Strategy interface and registry.

A strategy is a pure function of price history: given the bars seen *so far*
for a symbol and whether we currently hold it, it emits a :class:`Signal`. It
must never look ahead — the engine only ever passes bars up to "now".
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from bot.types import Bar, Signal, SignalType


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def evaluate(self, bars: list[Bar], holding: bool) -> Signal:
        """Decide what to do given history `bars` (oldest..current).

        `bars[-1]` is the current bar. `holding` is True if the portfolio
        currently has an open long position in this symbol.
        """

    @property
    @abstractmethod
    def warmup(self) -> int:
        """Minimum bars needed before the strategy emits non-HOLD signals."""


# --- registry -------------------------------------------------------------

_REGISTRY: dict[str, Callable[[dict[str, Any]], Strategy]] = {}


def register(name: str) -> Callable[[type[Strategy]], type[Strategy]]:
    def deco(cls: type[Strategy]) -> type[Strategy]:
        _REGISTRY[name] = lambda params: cls(**params)  # type: ignore[call-arg]
        cls.name = name
        return cls

    return deco


def build_strategy(name: str, params: dict[str, Any] | None = None) -> Strategy:
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise ValueError(f"Unknown strategy {name!r}. Available: {available}")
    return _REGISTRY[name](params or {})


def available_strategies() -> list[str]:
    return sorted(_REGISTRY)


def _hold(bars: list[Bar], reason: str = "") -> Signal:
    last = bars[-1]
    return Signal(last.symbol, SignalType.HOLD, last.timestamp, 0.0, reason)


# Importing the built-ins registers them. Done at the bottom to avoid cycles.
from bot.strategy import bollinger as _bollinger  # noqa: E402,F401
from bot.strategy import macd as _macd  # noqa: E402,F401
from bot.strategy import rsi as _rsi  # noqa: E402,F401
from bot.strategy import sma_crossover as _sma  # noqa: E402,F401
