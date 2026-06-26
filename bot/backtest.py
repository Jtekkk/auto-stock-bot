"""Backtest runner: replay historical bars through the engine.

Aligns all symbols on a shared timeline and feeds the engine one timestamp at a
time, passing only the history visible up to that point (no look-ahead). At the
end it liquidates open positions and computes performance metrics.
"""

from __future__ import annotations

from datetime import datetime

from bot.broker.paper import PaperBroker
from bot.config import Config
from bot.data.feed import DataFeed
from bot.engine import TradingEngine
from bot.metrics import Metrics, compute_metrics
from bot.portfolio import Portfolio
from bot.risk import RiskManager
from bot.strategy.base import build_strategy
from bot.types import Bar


def run_backtest(config: Config, feed: DataFeed, verbose: bool = False) -> Metrics:
    strategy = build_strategy(config.strategy.name, config.strategy.params)
    portfolio = Portfolio(config.starting_cash)
    risk = RiskManager(config.risk)
    broker = PaperBroker()
    engine = TradingEngine(strategy, risk, portfolio, broker, verbose=verbose)

    # Load and index every symbol's bars by timestamp.
    series: dict[str, list[Bar]] = {}
    by_time: dict[str, dict[datetime, Bar]] = {}
    for symbol in config.symbols:
        bars = feed.history(symbol)
        series[symbol] = bars
        by_time[symbol] = {b.timestamp: b for b in bars}

    timeline = _shared_timeline(series)
    if not timeline:
        raise ValueError("No bars available for backtest (check data source/symbols).")

    # Incrementally grow each symbol's visible history as the clock advances.
    cursor = {symbol: 0 for symbol in config.symbols}
    visible: dict[str, list[Bar]] = {symbol: [] for symbol in config.symbols}

    last_prices: dict[str, float] = {}
    for ts in timeline:
        histories: dict[str, list[Bar]] = {}
        for symbol in config.symbols:
            bar = by_time[symbol].get(ts)
            if bar is not None:
                visible[symbol].append(bar)
                cursor[symbol] += 1
                last_prices[symbol] = bar.close
            if visible[symbol]:
                histories[symbol] = visible[symbol]
        if histories:
            engine.step(ts, histories)

    # Liquidate whatever is still open at the final price so metrics are clean.
    final_ts = timeline[-1]
    for symbol in list(portfolio.positions):
        price = last_prices.get(symbol, portfolio.positions[symbol].avg_price)
        broker.set_market({symbol: price}, final_ts)
        portfolio.close_long(symbol, price, final_ts, reason="end-of-backtest liquidation")

    return compute_metrics(
        config.starting_cash, portfolio.equity_curve, portfolio.trades, portfolio.realized_pnl
    )


def _shared_timeline(series: dict[str, list[Bar]]) -> list[datetime]:
    timestamps: set[datetime] = set()
    for bars in series.values():
        timestamps.update(b.timestamp for b in bars)
    return sorted(timestamps)
