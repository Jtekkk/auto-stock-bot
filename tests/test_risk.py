from bot.config import RiskConfig
from bot.risk import RiskManager


def make_manager(**overrides) -> RiskManager:
    cfg = RiskConfig(**overrides)
    return RiskManager(cfg)


def test_size_entry_respects_max_position_pct():
    rm = make_manager(max_position_pct=0.20)
    decision = rm.size_entry(price=100, equity=100_000, cash=100_000, strength=1.0)
    assert decision.approved
    # 20% of 100k = 20k -> 200 shares at $100.
    assert decision.quantity == 200


def test_size_entry_scales_with_strength():
    rm = make_manager(max_position_pct=0.20)
    full = rm.size_entry(100, 100_000, 100_000, strength=1.0)
    half = rm.size_entry(100, 100_000, 100_000, strength=0.5)
    assert half.quantity < full.quantity


def test_size_entry_capped_by_cash():
    rm = make_manager(max_position_pct=0.50)
    decision = rm.size_entry(price=100, equity=100_000, cash=5_000, strength=1.0)
    # Want 50k of stock but only 5k cash -> 50 shares.
    assert decision.quantity == 50


def test_size_entry_rejects_when_too_small():
    rm = make_manager(max_position_pct=0.20)
    decision = rm.size_entry(price=10_000, equity=1_000, cash=1_000, strength=1.0)
    assert not decision.approved


def test_size_entry_sets_stop_and_target():
    rm = make_manager(stop_loss_pct=0.03, take_profit_pct=0.06)
    decision = rm.size_entry(price=100, equity=100_000, cash=100_000)
    assert decision.stop_loss == 97.0
    assert decision.take_profit == 106.0


def test_can_open_blocks_at_max_positions():
    rm = make_manager(max_open_positions=3)
    ok, reason = rm.can_open(open_positions=3, equity=100_000, peak_equity=100_000)
    assert not ok
    assert "max open positions" in reason


def test_can_open_blocks_on_drawdown():
    rm = make_manager(max_drawdown_pct=0.10)
    ok, reason = rm.can_open(open_positions=0, equity=85_000, peak_equity=100_000)
    assert not ok
    assert "drawdown" in reason


def test_can_open_allows_within_limits():
    rm = make_manager(max_open_positions=5, max_drawdown_pct=0.15)
    ok, _ = rm.can_open(open_positions=2, equity=98_000, peak_equity=100_000)
    assert ok
