from datetime import datetime

from bot.portfolio import Portfolio


def test_open_long_deducts_cash_and_records_position():
    p = Portfolio(10_000)
    p.open_long("AAPL", 10, 100, datetime(2023, 1, 1))
    assert p.cash == 9_000
    assert p.has_position("AAPL")
    assert p.open_position_count() == 1


def test_open_long_rejects_when_insufficient_cash():
    import pytest

    p = Portfolio(500)
    with pytest.raises(ValueError):
        p.open_long("AAPL", 10, 100, datetime(2023, 1, 1))


def test_close_long_realizes_pnl():
    p = Portfolio(10_000)
    p.open_long("AAPL", 10, 100, datetime(2023, 1, 1))
    pnl = p.close_long("AAPL", 110, datetime(2023, 1, 2))
    assert pnl == 100
    assert p.realized_pnl == 100
    assert p.cash == 10_100
    assert not p.has_position("AAPL")


def test_equity_includes_open_position_value():
    p = Portfolio(10_000)
    p.open_long("AAPL", 10, 100, datetime(2023, 1, 1))  # cash now 9000
    assert p.equity({"AAPL": 120}) == 9_000 + 10 * 120


def test_mark_tracks_peak_equity():
    p = Portfolio(10_000)
    p.open_long("AAPL", 10, 100, datetime(2023, 1, 1))
    p.mark(datetime(2023, 1, 2), {"AAPL": 150})  # equity 10500
    p.mark(datetime(2023, 1, 3), {"AAPL": 90})   # equity 9900
    assert p.peak_equity == 10_500
    assert len(p.equity_curve) == 2
