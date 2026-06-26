"""Performance metrics computed from the portfolio's results."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from bot.types import Side, Trade


@dataclass
class Metrics:
    starting_equity: float
    ending_equity: float
    total_return_pct: float
    realized_pnl: float
    max_drawdown_pct: float
    sharpe: float
    num_trades: int
    num_wins: int
    num_losses: int
    win_rate_pct: float
    avg_win: float
    avg_loss: float
    profit_factor: float

    def render(self) -> str:
        lines = [
            "=" * 48,
            "  BACKTEST RESULTS",
            "=" * 48,
            f"  Starting equity   : {self.starting_equity:>14,.2f}",
            f"  Ending equity     : {self.ending_equity:>14,.2f}",
            f"  Total return      : {self.total_return_pct:>13.2f}%",
            f"  Realized P&L      : {self.realized_pnl:>14,.2f}",
            f"  Max drawdown      : {self.max_drawdown_pct:>13.2f}%",
            f"  Sharpe (annual)   : {self.sharpe:>14.2f}",
            "-" * 48,
            f"  Closed trades     : {self.num_trades:>14d}",
            f"  Win / Loss        : {self.num_wins:>6d} / {self.num_losses:<6d}",
            f"  Win rate          : {self.win_rate_pct:>13.2f}%",
            f"  Avg win / loss    : {self.avg_win:>8,.2f} / {self.avg_loss:,.2f}",
            f"  Profit factor     : {self.profit_factor:>14.2f}",
            "=" * 48,
        ]
        return "\n".join(lines)


def compute_metrics(
    starting_cash: float,
    equity_curve: list[tuple[datetime, float]],
    trades: list[Trade],
    realized_pnl: float,
) -> Metrics:
    ending = equity_curve[-1][1] if equity_curve else starting_cash
    total_return = (ending / starting_cash - 1) * 100 if starting_cash else 0.0

    max_dd = _max_drawdown(equity_curve)
    sharpe = _sharpe(equity_curve)

    # Only SELL fills carry realized P&L (a closed round trip).
    closed = [t for t in trades if t.side == Side.SELL]
    wins = [t.pnl for t in closed if t.pnl > 0]
    losses = [t.pnl for t in closed if t.pnl <= 0]
    num_trades = len(closed)
    win_rate = (len(wins) / num_trades * 100) if num_trades else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    return Metrics(
        starting_equity=starting_cash,
        ending_equity=ending,
        total_return_pct=total_return,
        realized_pnl=realized_pnl,
        max_drawdown_pct=max_dd,
        sharpe=sharpe,
        num_trades=num_trades,
        num_wins=len(wins),
        num_losses=len(losses),
        win_rate_pct=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
    )


def _max_drawdown(equity_curve: list[tuple[datetime, float]]) -> float:
    peak = float("-inf")
    max_dd = 0.0
    for _, eq in equity_curve:
        peak = max(peak, eq)
        if peak > 0:
            dd = (peak - eq) / peak
            max_dd = max(max_dd, dd)
    return max_dd * 100


def _sharpe(equity_curve: list[tuple[datetime, float]], periods_per_year: int = 252) -> float:
    if len(equity_curve) < 3:
        return 0.0
    returns = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1][1]
        cur = equity_curve[i][1]
        if prev > 0:
            returns.append(cur / prev - 1)
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(periods_per_year)
