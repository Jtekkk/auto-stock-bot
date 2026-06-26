"""Export backtest results to CSV for further analysis/plotting."""

from __future__ import annotations

import csv
from pathlib import Path

from bot.portfolio import Portfolio


def export_trades(portfolio: Portfolio, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp", "symbol", "side", "quantity", "price", "pnl", "reason"])
        for t in portfolio.trades:
            writer.writerow(
                [
                    t.timestamp.isoformat(),
                    t.symbol,
                    t.side.value,
                    f"{t.quantity:.4f}",
                    f"{t.price:.4f}",
                    f"{t.pnl:.4f}",
                    t.reason,
                ]
            )
    return path


def export_equity_curve(portfolio: Portfolio, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp", "equity"])
        for ts, equity in portfolio.equity_curve:
            writer.writerow([ts.isoformat(), f"{equity:.4f}"])
    return path
