"""Core data types shared across the bot.

Kept deliberately simple (dataclasses, no external deps) so every layer —
data feed, strategy, broker, portfolio — speaks the same vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass(frozen=True)
class Bar:
    """A single OHLCV price bar for one symbol."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class SignalType(str, Enum):
    ENTER_LONG = "enter_long"
    EXIT_LONG = "exit_long"
    HOLD = "hold"


@dataclass(frozen=True)
class Signal:
    """A strategy's intent for a symbol on a given bar.

    `strength` is a 0..1 conviction used by risk sizing; 1.0 means "size this
    as large as the risk limits allow".
    """

    symbol: str
    type: SignalType
    timestamp: datetime
    strength: float = 1.0
    reason: str = ""


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class Order:
    symbol: str
    side: Side
    quantity: float
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float | None = None
    filled_at: datetime | None = None
    reason: str = ""


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    # Risk levels attached at entry, evaluated each bar by the engine.
    stop_loss: float | None = None
    take_profit: float | None = None

    def market_value(self, price: float) -> float:
        return self.quantity * price

    def unrealized_pnl(self, price: float) -> float:
        return (price - self.avg_price) * self.quantity


@dataclass
class Trade:
    """A completed round-trip (or a single fill) recorded for reporting."""

    symbol: str
    side: Side
    quantity: float
    price: float
    timestamp: datetime
    pnl: float = 0.0
    reason: str = ""


@dataclass
class PortfolioSnapshot:
    timestamp: datetime
    cash: float
    equity: float
    positions: dict[str, Position] = field(default_factory=dict)
