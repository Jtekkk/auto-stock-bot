"""Risk management: position sizing and entry gating.

Sits between the strategy and the broker. The strategy says "I want to enter
SYMBOL"; the risk manager decides *how much* (or vetoes the trade entirely)
based on portfolio-level limits.
"""

from __future__ import annotations

from dataclasses import dataclass

from bot.config import RiskConfig


@dataclass
class SizingDecision:
    quantity: float
    stop_loss: float | None
    take_profit: float | None
    approved: bool
    reason: str = ""


class RiskManager:
    def __init__(self, config: RiskConfig):
        self.cfg = config

    def can_open(self, open_positions: int, equity: float, peak_equity: float) -> tuple[bool, str]:
        """Portfolio-level gate checked before sizing a new entry."""
        if open_positions >= self.cfg.max_open_positions:
            return False, f"max open positions reached ({self.cfg.max_open_positions})"
        if peak_equity > 0 and self.cfg.max_drawdown_pct > 0:
            drawdown = (peak_equity - equity) / peak_equity
            if drawdown >= self.cfg.max_drawdown_pct:
                return False, (
                    f"drawdown {drawdown:.1%} >= limit {self.cfg.max_drawdown_pct:.1%}; "
                    "halting new entries"
                )
        return True, ""

    def size_entry(
        self,
        price: float,
        equity: float,
        cash: float,
        strength: float = 1.0,
    ) -> SizingDecision:
        """Compute share quantity and protective levels for a long entry."""
        if price <= 0:
            return SizingDecision(0, None, None, False, "non-positive price")

        strength = max(0.0, min(1.0, strength))
        target_value = equity * self.cfg.max_position_pct * strength
        target_value = min(target_value, cash)  # never spend cash we don't have
        quantity = int(target_value // price)

        if quantity <= 0:
            return SizingDecision(0, None, None, False, "position size rounds to zero shares")

        stop_loss = price * (1 - self.cfg.stop_loss_pct) if self.cfg.stop_loss_pct > 0 else None
        take_profit = (
            price * (1 + self.cfg.take_profit_pct) if self.cfg.take_profit_pct > 0 else None
        )
        return SizingDecision(quantity, stop_loss, take_profit, True, "approved")
