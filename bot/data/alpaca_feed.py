"""Alpaca historical/live market-data feed (optional).

Only imported when ``data.source: alpaca`` is selected. Requires ``alpaca-py``
and API credentials in the environment (see ``.env.example``).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from bot.data.feed import DataFeed
from bot.types import Bar

_TIMEFRAME_LOOKBACK = {
    "1Min": timedelta(days=5),
    "5Min": timedelta(days=15),
    "15Min": timedelta(days=30),
    "1Hour": timedelta(days=120),
    "1Day": timedelta(days=400),
}


class AlpacaFeed(DataFeed):
    def __init__(self, symbols: list[str], timeframe: str = "1Day"):
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        except ImportError as exc:  # pragma: no cover - depends on optional pkg
            raise ImportError(
                "alpaca-py is required for the Alpaca feed. "
                "Install it with: pip install -r requirements-live.txt"
            ) from exc

        key = os.environ.get("ALPACA_API_KEY")
        secret = os.environ.get("ALPACA_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError(
                "ALPACA_API_KEY / ALPACA_SECRET_KEY must be set for the Alpaca feed."
            )

        self.symbols = symbols
        self.timeframe_str = timeframe
        self._client = StockHistoricalDataClient(key, secret)
        self._timeframe = self._to_timeframe(timeframe, TimeFrame, TimeFrameUnit)
        self._cache: dict[str, list[Bar]] = {}

    @staticmethod
    def _to_timeframe(value: str, TimeFrame, TimeFrameUnit):  # noqa: N803
        mapping = {
            "1Min": TimeFrame(1, TimeFrameUnit.Minute),
            "5Min": TimeFrame(5, TimeFrameUnit.Minute),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
            "1Day": TimeFrame(1, TimeFrameUnit.Day),
        }
        if value not in mapping:
            raise ValueError(f"Unsupported timeframe: {value}")
        return mapping[value]

    def history(self, symbol: str) -> list[Bar]:
        if symbol in self._cache:
            return self._cache[symbol]
        bars = self._fetch(symbol)
        self._cache[symbol] = bars
        return bars

    def latest(self, symbol: str, n: int = 1) -> list[Bar]:
        # Refresh from the API rather than serving a stale cache for live use.
        self._cache.pop(symbol, None)
        return self.history(symbol)[-n:]

    def _fetch(self, symbol: str) -> list[Bar]:
        from alpaca.data.requests import StockBarsRequest

        lookback = _TIMEFRAME_LOOKBACK.get(self.timeframe_str, timedelta(days=400))
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=self._timeframe,
            start=datetime.utcnow() - lookback,
        )
        response = self._client.get_stock_bars(request)
        rows = response.data.get(symbol, [])
        return [
            Bar(
                symbol=symbol,
                timestamp=row.timestamp,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            )
            for row in rows
        ]
