"""Simulated broker for backtests and offline paper trading.

Fills market orders immediately at the current bar's price, optionally adjusted
by slippage and commission so backtests aren't unrealistically optimistic.
"""

from __future__ import annotations

from datetime import datetime

from bot.broker.base import Broker
from bot.types import Order, OrderStatus, Side


class PaperBroker(Broker):
    def __init__(
        self,
        slippage_pct: float = 0.0005,
        commission_per_share: float = 0.0,
    ):
        self.slippage_pct = slippage_pct
        self.commission_per_share = commission_per_share
        self._prices: dict[str, float] = {}
        self._clock: datetime | None = None

    def set_market(self, prices: dict[str, float], clock: datetime) -> None:
        """Engine calls this each bar to advance the simulated market."""
        self._prices.update(prices)
        self._clock = clock

    def get_price(self, symbol: str) -> float:
        if symbol not in self._prices:
            raise KeyError(f"no market price set for {symbol}")
        return self._prices[symbol]

    def submit(self, symbol: str, side: Side, quantity: float, reason: str = "") -> Order:
        if quantity <= 0:
            return Order(symbol, side, quantity, OrderStatus.REJECTED, reason="non-positive qty")
        price = self.get_price(symbol)
        # Buys pay up, sells receive less — slippage always works against us.
        if side == Side.BUY:
            fill = price * (1 + self.slippage_pct)
        else:
            fill = price * (1 - self.slippage_pct)
        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            status=OrderStatus.FILLED,
            filled_price=fill,
            filled_at=self._clock,
            reason=reason,
        )

    @property
    def commission(self) -> float:
        return self.commission_per_share
