"""Broker abstraction.

The engine talks to a Broker, never to an exchange directly. The simulated
``PaperBroker`` fills against the current bar; ``AlpacaBroker`` forwards orders
to Alpaca's paper/live API. Same interface either way.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from bot.types import Order, Side


class Broker(ABC):
    @abstractmethod
    def submit(self, symbol: str, side: Side, quantity: float, reason: str = "") -> Order:
        """Submit a market order and return it with fill details populated."""

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """Return the latest reference price for a symbol."""
