"""The trading engine — shared core for backtest and live loops.

Given the price history visible *so far*, it:
  1. checks protective stops/targets on open positions and exits if hit,
  2. asks the strategy for a signal per symbol,
  3. runs entries through the risk manager for sizing/gating,
  4. submits the resulting orders to the broker and updates the portfolio.

It never looks ahead: callers feed it bars incrementally.
"""

from __future__ import annotations

from datetime import datetime

from bot.broker.base import Broker
from bot.broker.paper import PaperBroker
from bot.portfolio import Portfolio
from bot.risk import RiskManager
from bot.strategy.base import Strategy
from bot.types import Bar, Side, SignalType


class TradingEngine:
    def __init__(
        self,
        strategy: Strategy,
        risk: RiskManager,
        portfolio: Portfolio,
        broker: Broker,
        verbose: bool = False,
    ):
        self.strategy = strategy
        self.risk = risk
        self.portfolio = portfolio
        self.broker = broker
        self.verbose = verbose

    def step(self, timestamp: datetime, histories: dict[str, list[Bar]]) -> None:
        """Process one time step across all symbols.

        `histories[symbol]` is the list of bars up to and including the current
        one. The current price for each symbol is its last bar's close.
        """
        prices = {sym: bars[-1].close for sym, bars in histories.items() if bars}

        # Let a simulated broker know the current market before it fills orders.
        if isinstance(self.broker, PaperBroker):
            self.broker.set_market(prices, timestamp)

        # 1) Protective exits first — stops/targets take priority over signals.
        for symbol in list(self.portfolio.positions):
            price = prices.get(symbol)
            if price is None:
                continue
            self._check_protective_exit(symbol, price, timestamp)

        # 2) Strategy-driven decisions.
        for symbol, bars in histories.items():
            if not bars:
                continue
            holding = self.portfolio.has_position(symbol)
            signal = self.strategy.evaluate(bars, holding)

            if signal.type == SignalType.EXIT_LONG and holding:
                self._exit(symbol, prices[symbol], timestamp, signal.reason)
            elif signal.type == SignalType.ENTER_LONG and not holding:
                self._enter(symbol, prices[symbol], timestamp, signal.strength, signal.reason)

        # 3) Mark the book to update the equity curve / drawdown peak.
        self.portfolio.mark(timestamp, prices)

    # --- internals --------------------------------------------------------

    def _check_protective_exit(self, symbol: str, price: float, ts: datetime) -> None:
        pos = self.portfolio.positions[symbol]
        if pos.stop_loss is not None and price <= pos.stop_loss:
            self._exit(symbol, price, ts, f"stop-loss hit @ {pos.stop_loss:.2f}")
        elif pos.take_profit is not None and price >= pos.take_profit:
            self._exit(symbol, price, ts, f"take-profit hit @ {pos.take_profit:.2f}")

    def _enter(self, symbol: str, price: float, ts: datetime, strength: float, reason: str) -> None:
        equity = self.portfolio.equity({symbol: price})
        ok, gate_reason = self.risk.can_open(
            self.portfolio.open_position_count(), equity, self.portfolio.peak_equity
        )
        if not ok:
            self._log(f"[{ts:%Y-%m-%d}] skip {symbol} entry: {gate_reason}")
            return

        decision = self.risk.size_entry(price, equity, self.portfolio.cash, strength)
        if not decision.approved:
            self._log(f"[{ts:%Y-%m-%d}] skip {symbol} entry: {decision.reason}")
            return

        order = self.broker.submit(symbol, Side.BUY, decision.quantity, reason)
        if order.filled_price is None:
            self._log(f"[{ts:%Y-%m-%d}] {symbol} buy not filled: {order.reason}")
            return

        self.portfolio.open_long(
            symbol,
            order.quantity,
            order.filled_price,
            ts,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            reason=reason,
        )
        self._log(
            f"[{ts:%Y-%m-%d}] BUY  {order.quantity:>6.0f} {symbol} @ {order.filled_price:8.2f}"
            f"  | {reason}"
        )

    def _exit(self, symbol: str, price: float, ts: datetime, reason: str) -> None:
        order = self.broker.submit(
            symbol, Side.SELL, self.portfolio.positions[symbol].quantity, reason
        )
        fill = order.filled_price if order.filled_price is not None else price
        pnl = self.portfolio.close_long(symbol, fill, ts, reason)
        self._log(
            f"[{ts:%Y-%m-%d}] SELL {order.quantity:>6.0f} {symbol} @ {fill:8.2f}"
            f"  | pnl {pnl:+10.2f} | {reason}"
        )

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)
