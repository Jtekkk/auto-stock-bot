import pytest

from bot.indicators import bollinger, macd


def test_macd_rejects_bad_periods():
    with pytest.raises(ValueError):
        macd([1.0, 2.0, 3.0], fast=26, slow=12)


def test_macd_lengths_and_alignment():
    values = [float(i % 7) + i * 0.1 for i in range(60)]
    macd_line, signal_line, hist = macd(values, fast=12, slow=26, signal=9)
    assert len(macd_line) == len(signal_line) == len(hist) == len(values)
    # Early entries lack enough history.
    assert macd_line[0] is None
    # Where both lines exist, histogram == macd - signal.
    for m, s, h in zip(macd_line, signal_line, hist):
        if m is not None and s is not None:
            assert h == pytest.approx(m - s)


def test_macd_line_is_positive_on_uptrend():
    values = [float(i) for i in range(60)]  # steady uptrend
    macd_line, _, _ = macd(values)
    last = [v for v in macd_line if v is not None][-1]
    assert last > 0  # fast EMA above slow EMA on a rising series


def test_bollinger_bands_order_and_width():
    values = [10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17]
    middle, upper, lower = bollinger([float(v) for v in values], period=5, num_std=2.0)
    for m, u, low in zip(middle, upper, lower):
        if m is not None:
            assert low <= m <= u


def test_bollinger_zero_width_on_flat_series():
    values = [100.0] * 30
    middle, upper, lower = bollinger(values, period=10, num_std=2.0)
    idx = next(i for i, m in enumerate(middle) if m is not None)
    assert upper[idx] == pytest.approx(lower[idx])  # zero std -> bands collapse
