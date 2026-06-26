"""Portfolio bookkeeping: cash, positions, equity, realized P&L.

Broker-agnostic. The simulated broker drives it directly; a live broker would
reconcile it against the account on each loop. Tracks an equity curve and peak
equity so the risk manager can enforce drawdown limits.
"""

from __future__ import annotations

from datetime import datetime

from bot.types import Position, Side, Trade


class Portfolio:
    def __init__(self, starting_cash: float):
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.equity_curve: list[tuple[datetime, float]] = []
        self.realized_pnl = 0.0
        self.peak_equity = starting_cash

    # --- queries ----------------------------------------------------------

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions

    def open_position_count(self) -> int:
        return len(self.positions)

    def equity(self, prices: dict[str, float]) -> float:
        total = self.cash
        for sym, pos in self.positions.items():
            price = prices.get(sym, pos.avg_price)
            total += pos.market_value(price)
        return total

    # --- mutations --------------------------------------------------------

    def open_long(
        self,
        symbol: str,
        quantity: float,
        price: float,
        timestamp: datetime,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        reason: str = "",
    ) -> None:
        cost = quantity * price
        if cost > self.cash + 1e-9:
            raise ValueError(f"insufficient cash: need {cost:.2f}, have {self.cash:.2f}")
        self.cash -= cost
        self.positions[symbol] = Position(
            symbol=symbol,
            quantity=quantity,
            avg_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.trades.append(
            Trade(symbol, Side.BUY, quantity, price, timestamp, pnl=0.0, reason=reason)
        )

    def close_long(self, symbol: str, price: float, timestamp: datetime, reason: str = "") -> float:
        pos = self.positions.get(symbol)
        if pos is None:
            return 0.0
        proceeds = pos.quantity * price
        pnl = (price - pos.avg_price) * pos.quantity
        self.cash += proceeds
        self.realized_pnl += pnl
        self.trades.append(
            Trade(symbol, Side.SELL, pos.quantity, price, timestamp, pnl=pnl, reason=reason)
        )
        del self.positions[symbol]
        return pnl

    def mark(self, timestamp: datetime, prices: dict[str, float]) -> float:
        """Record an equity-curve point and update the peak. Returns equity."""
        eq = self.equity(prices)
        self.equity_curve.append((timestamp, eq))
        self.peak_equity = max(self.peak_equity, eq)
        return eq
