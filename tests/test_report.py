import csv
from datetime import datetime

from bot.portfolio import Portfolio
from bot.report import export_equity_curve, export_trades


def _portfolio_with_activity() -> Portfolio:
    p = Portfolio(10_000)
    p.open_long("AAPL", 10, 100, datetime(2023, 1, 1), reason="entry")
    p.mark(datetime(2023, 1, 1), {"AAPL": 100})
    p.close_long("AAPL", 110, datetime(2023, 1, 2), reason="exit")
    p.mark(datetime(2023, 1, 2), {})
    return p


def test_export_trades_writes_rows(tmp_path):
    p = _portfolio_with_activity()
    path = export_trades(p, tmp_path / "trades.csv")
    rows = list(csv.DictReader(path.open()))
    assert len(rows) == 2
    assert rows[0]["symbol"] == "AAPL"
    assert rows[0]["side"] == "buy"
    assert rows[1]["side"] == "sell"
    assert float(rows[1]["pnl"]) == 100.0


def test_export_equity_curve_writes_rows(tmp_path):
    p = _portfolio_with_activity()
    path = export_equity_curve(p, tmp_path / "equity.csv")
    rows = list(csv.DictReader(path.open()))
    assert len(rows) == 2
    assert "equity" in rows[0]
    assert float(rows[0]["equity"]) > 0


def test_export_creates_missing_parent_dirs(tmp_path):
    p = _portfolio_with_activity()
    nested = tmp_path / "a" / "b" / "trades.csv"
    path = export_trades(p, nested)
    assert path.exists()
