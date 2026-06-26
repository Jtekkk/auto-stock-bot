"""Alpaca paper/live broker (optional).

Defaults to the **paper** endpoint. Switching to live trading requires
explicitly setting ALPACA_BASE_URL to the live URL — there is no accidental
path to real-money orders.
"""

from __future__ import annotations

import os

from bot.broker.base import Broker
from bot.types import Order, OrderStatus, Side

_PAPER_URL = "https://paper-api.alpaca.markets"


class AlpacaBroker(Broker):
    def __init__(self) -> None:
        try:
            from alpaca.trading.client import TradingClient
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "alpaca-py is required for the Alpaca broker. "
                "Install it with: pip install -r requirements-live.txt"
            ) from exc

        key = os.environ.get("ALPACA_API_KEY")
        secret = os.environ.get("ALPACA_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError("ALPACA_API_KEY / ALPACA_SECRET_KEY must be set.")

        base_url = os.environ.get("ALPACA_BASE_URL", _PAPER_URL)
        self.is_paper = "paper" in base_url
        if not self.is_paper:
            # Make real-money trading a loud, deliberate choice.
            if os.environ.get("ALPACA_ALLOW_LIVE") != "yes":
                raise RuntimeError(
                    "Live trading endpoint configured but ALPACA_ALLOW_LIVE != 'yes'. "
                    "Refusing to trade real money without explicit opt-in."
                )
        self._client = TradingClient(key, secret, paper=self.is_paper)

    def get_price(self, symbol: str) -> float:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestTradeRequest

        key = os.environ["ALPACA_API_KEY"]
        secret = os.environ["ALPACA_SECRET_KEY"]
        data_client = StockHistoricalDataClient(key, secret)
        req = StockLatestTradeRequest(symbol_or_symbols=symbol)
        trade = data_client.get_stock_latest_trade(req)[symbol]
        return float(trade.price)

    def submit(self, symbol: str, side: Side, quantity: float, reason: str = "") -> Order:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        order_side = OrderSide.BUY if side == Side.BUY else OrderSide.SELL
        request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        try:
            submitted = self._client.submit_order(request)
        except Exception as exc:  # pragma: no cover - network/broker errors
            return Order(symbol, side, quantity, OrderStatus.REJECTED, reason=str(exc))

        filled_price = float(submitted.filled_avg_price) if submitted.filled_avg_price else None
        status = OrderStatus.FILLED if filled_price else OrderStatus.PENDING
        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            status=status,
            filled_price=filled_price,
            filled_at=submitted.filled_at,
            reason=reason,
        )
