"""Data feed abstraction plus the offline feeds (synthetic + CSV).

A feed yields historical bars per symbol for backtesting, and (for live feeds)
can also return the most recent bars on demand. The Alpaca live feed lives in
``bot.data.alpaca_feed`` and is only imported when selected.
"""

from __future__ import annotations

import csv
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path

from bot.types import Bar


class DataFeed(ABC):
    """Yields bars for a set of symbols."""

    @abstractmethod
    def history(self, symbol: str) -> list[Bar]:
        """Return all available historical bars for a symbol, oldest first."""

    def latest(self, symbol: str, n: int = 1) -> list[Bar]:
        """Return the most recent ``n`` bars (default: just the last one)."""
        return self.history(symbol)[-n:]


class SyntheticFeed(DataFeed):
    """Deterministic pseudo-random walk — lets the bot run with zero setup.

    Seeded per symbol so results are reproducible across runs (important for
    tests and for comparing strategy tweaks).
    """

    def __init__(self, symbols: list[str], bars: int = 500, start_price: float = 100.0):
        self.symbols = symbols
        self.bars = bars
        self.start_price = start_price
        self._cache: dict[str, list[Bar]] = {}

    def history(self, symbol: str) -> list[Bar]:
        if symbol not in self._cache:
            self._cache[symbol] = self._generate(symbol)
        return self._cache[symbol]

    def _generate(self, symbol: str) -> list[Bar]:
        # A small LCG seeded from the symbol gives reproducible, dependency-free
        # randomness without touching the global random module.
        seed = abs(hash(symbol)) % (2**31)
        state = seed or 1

        def rand() -> float:
            nonlocal state
            state = (1103515245 * state + 12345) & 0x7FFFFFFF
            return state / 0x7FFFFFFF

        bars: list[Bar] = []
        price = self.start_price
        start = datetime(2023, 1, 1)
        # Gentle upward drift with mean-reverting noise and a slow cycle so
        # trend strategies have something to grab onto.
        for i in range(self.bars):
            cycle = math.sin(i / 40.0) * 0.004
            shock = (rand() - 0.5) * 0.03
            drift = 0.0003
            ret = drift + cycle + shock
            new_price = max(1.0, price * (1 + ret))
            high = max(price, new_price) * (1 + rand() * 0.005)
            low = min(price, new_price) * (1 - rand() * 0.005)
            volume = 1_000_000 + rand() * 500_000
            bars.append(
                Bar(
                    symbol=symbol,
                    timestamp=start + timedelta(days=i),
                    open=round(price, 4),
                    high=round(high, 4),
                    low=round(low, 4),
                    close=round(new_price, 4),
                    volume=round(volume),
                )
            )
            price = new_price
        return bars


class CSVFeed(DataFeed):
    """Reads ``<csv_dir>/<SYMBOL>.csv`` with header: date,open,high,low,close,volume."""

    def __init__(self, csv_dir: str):
        self.csv_dir = Path(csv_dir)
        self._cache: dict[str, list[Bar]] = {}

    def history(self, symbol: str) -> list[Bar]:
        if symbol in self._cache:
            return self._cache[symbol]
        path = self.csv_dir / f"{symbol}.csv"
        if not path.exists():
            raise FileNotFoundError(f"No CSV data for {symbol} at {path}")
        bars: list[Bar] = []
        with path.open(newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                bars.append(
                    Bar(
                        symbol=symbol,
                        timestamp=_parse_date(row["date"]),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row.get("volume", 0) or 0),
                    )
                )
        bars.sort(key=lambda b: b.timestamp)
        self._cache[symbol] = bars
        return bars


def _parse_date(value: str) -> datetime:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # Last resort: ISO 8601 with timezone handling.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_feed(data_config, symbols: list[str]) -> DataFeed:
    """Factory: construct the configured feed.

    Importing the Alpaca feed lazily keeps ``alpaca-py`` an optional dependency.
    """
    source = data_config.source.lower()
    if source == "synthetic":
        return SyntheticFeed(symbols, bars=data_config.synthetic_bars)
    if source == "csv":
        return CSVFeed(data_config.csv_dir)
    if source == "alpaca":
        from bot.data.alpaca_feed import AlpacaFeed

        return AlpacaFeed(symbols, timeframe=data_config.timeframe)
    raise ValueError(f"Unknown data source: {data_config.source!r}")
