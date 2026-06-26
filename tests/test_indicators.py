from bot.indicators import ema, rsi, sma


def test_sma_basic():
    values = [1, 2, 3, 4, 5]
    result = sma(values, 3)
    assert result[:2] == [None, None]
    assert result[2] == 2.0  # (1+2+3)/3
    assert result[3] == 3.0
    assert result[4] == 4.0


def test_sma_window_slides_correctly():
    values = [10, 20, 30, 40, 50, 60]
    result = sma(values, 2)
    assert result[1] == 15.0
    assert result[-1] == 55.0


def test_ema_seeds_with_sma_and_tracks_trend():
    values = [float(i) for i in range(1, 21)]
    result = ema(values, 5)
    assert result[3] is None
    assert result[4] == 3.0  # first EMA == SMA of first 5
    # On a rising series the EMA must be monotonically increasing afterwards.
    tail = [v for v in result if v is not None]
    assert all(b >= a for a, b in zip(tail, tail[1:]))


def test_rsi_all_gains_is_100():
    values = [float(i) for i in range(1, 30)]
    result = rsi(values, 14)
    assert result[14] == 100.0


def test_rsi_bounds():
    values = [100, 102, 101, 105, 107, 106, 110, 108, 112, 115, 113, 117, 120, 118, 121, 119]
    result = rsi([float(v) for v in values], 14)
    non_null = [v for v in result if v is not None]
    assert non_null, "expected at least one RSI value"
    assert all(0.0 <= v <= 100.0 for v in non_null)
