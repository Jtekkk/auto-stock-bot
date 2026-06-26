"""Live / paper trading loop.

Polls the data feed on an interval, advances the engine one step per poll, and
prints portfolio status. Intended for the Alpaca paper endpoint by default. The
loop is intentionally simple and synchronous — clarity over throughput.
"""

from __future__ import annotations

import time
from datetime import datetime

from bot.broker.base import Broker
from bot.config import Config
from bot.data.feed import DataFeed
from bot.engine import TradingEngine
from bot.portfolio import Portfolio
from bot.risk import RiskManager
from bot.strategy.base import build_strategy
from bot.types import Bar


def run_live(
    config: Config,
    feed: DataFeed,
    broker: Broker,
    poll_seconds: int = 60,
    max_iterations: int | None = None,
) -> Portfolio:
    strategy = build_strategy(config.strategy.name, config.strategy.params)
    portfolio = Portfolio(config.starting_cash)
    risk = RiskManager(config.risk)
    engine = TradingEngine(strategy, risk, portfolio, broker, verbose=True)

    print(f"Live loop started: strategy={strategy.name} symbols={config.symbols}")
    print(f"Polling every {poll_seconds}s. Ctrl-C to stop.\n")

    iteration = 0
    try:
        while max_iterations is None or iteration < max_iterations:
            histories: dict[str, list[Bar]] = {}
            # Pull enough history to satisfy the strategy warmup each poll.
            lookback = max(strategy.warmup + 5, 50)
            for symbol in config.symbols:
                bars = feed.latest(symbol, lookback)
                if bars:
                    histories[symbol] = bars
            if histories:
                ts = _now(histories)
                engine.step(ts, histories)
                _print_status(portfolio, histories)
            iteration += 1
            if max_iterations is None or iteration < max_iterations:
                time.sleep(poll_seconds)
    except KeyboardInterrupt:
        print("\nStopping live loop (Ctrl-C).")

    return portfolio


def _now(histories: dict[str, list[Bar]]) -> datetime:
    # Use the most recent bar timestamp across symbols as the engine clock.
    return max(bars[-1].timestamp for bars in histories.values())


def _print_status(portfolio: Portfolio, histories: dict[str, list[Bar]]) -> None:
    prices = {sym: bars[-1].close for sym, bars in histories.items()}
    equity = portfolio.equity(prices)
    held = ", ".join(
        f"{p.quantity:.0f}{s}@{p.avg_price:.2f}" for s, p in portfolio.positions.items()
    )
    print(
        f"  equity={equity:,.2f} cash={portfolio.cash:,.2f} "
        f"positions=[{held}] realized={portfolio.realized_pnl:+,.2f}"
    )
