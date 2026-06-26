# auto-stock-bot

A small, readable day-trading bot in Python. It backtests trading strategies on
historical or synthetic data, paper-trades against a simulated broker, and can
(optionally) connect to **Alpaca** for paper or live trading.

The core runs on the **standard library + PyYAML** — no pandas/numpy — so you
can clone and run a backtest in seconds with zero market-data setup.

> ⚠️ **Not financial advice.** This is an educational/research tool. The default
> strategies are simple baselines and will not make you money. Trade real money
> only with paper-tested code, money you can afford to lose, and a clear
> understanding of the risks. Live trading is gated behind explicit opt-in.

## Quick start

```bash
pip install -r requirements.txt

# Backtest the default strategy on synthetic data (no API keys needed)
python main.py backtest

# Try a different strategy and symbols, printing every trade
python main.py backtest --symbols AAPL,MSFT,GOOG --strategy rsi --verbose

# List available strategies
python main.py strategies
```

Sample output:

```
================================================
  BACKTEST RESULTS
================================================
  Starting equity   :     100,000.00
  Ending equity     :     100,521.39
  Total return      :          0.52%
  Max drawdown      :          0.31%
  Sharpe (annual)   :           0.97
  Closed trades     :              3
  Win rate          :         66.67%
  Profit factor     :           3.03
================================================
```

## How it works

The bot is built from small, swappable layers that all speak the same data
types (`bot/types.py`):

```
Data feed ──► Strategy ──► Risk manager ──► Broker ──► Portfolio
 (bars)       (signals)     (sizing/gating)  (fills)   (P&L, equity)
                              ▲
                              └── Engine orchestrates one step per bar
```

| Layer | File | Responsibility |
|-------|------|----------------|
| **Data feed** | `bot/data/` | Yields OHLCV bars. `synthetic` (offline), `csv`, or `alpaca`. |
| **Strategy** | `bot/strategy/` | Pure function of price history → a signal. No look-ahead. |
| **Risk manager** | `bot/risk.py` | Position sizing, stop/target levels, drawdown & exposure limits. |
| **Broker** | `bot/broker/` | `PaperBroker` (simulated fills w/ slippage) or `AlpacaBroker`. |
| **Portfolio** | `bot/portfolio.py` | Tracks cash, positions, realized P&L, equity curve. |
| **Engine** | `bot/engine.py` | Per-bar loop: protective exits → signals → risk → orders. |
| **Backtest** | `bot/backtest.py` | Replays history through the engine, then `bot/metrics.py` scores it. |

## Strategies

- **`sma_crossover`** — trend following. Enter long when the fast SMA crosses
  above the slow SMA; exit on the reverse cross.
  Params: `fast` (10), `slow` (30).
- **`rsi`** — mean reversion. Enter when RSI recovers out of oversold; exit when
  it reaches overbought.
  Params: `period` (14), `oversold` (30), `overbought` (70).

### Adding your own

Drop a file in `bot/strategy/`, subclass `Strategy`, and register it:

```python
from bot.strategy.base import Strategy, _hold, register
from bot.types import Signal, SignalType

@register("my_strategy")
class MyStrategy(Strategy):
    def __init__(self, lookback: int = 20):
        self.lookback = lookback

    @property
    def warmup(self) -> int:
        return self.lookback + 1

    def evaluate(self, bars, holding):
        if len(bars) < self.warmup:
            return _hold(bars, "warming up")
        # ... your logic; return a Signal(ENTER_LONG / EXIT_LONG / HOLD)
        return _hold(bars)
```

Import it from `bot/strategy/base.py` (bottom of the file) so it registers, then
use it with `--strategy my_strategy`.

## Configuration

Edit `config.yaml` or pass `--config <file>`. CLI flags override the file. Key
knobs:

```yaml
symbols: [AAPL, MSFT]
starting_cash: 100000
strategy:
  name: sma_crossover
  params: { fast: 10, slow: 30 }
risk:
  max_position_pct: 0.20      # max % of equity per position
  max_open_positions: 5
  stop_loss_pct: 0.03         # 3% protective stop
  take_profit_pct: 0.06       # 6% target
  max_drawdown_pct: 0.15      # halt new entries past 15% drawdown
data:
  source: synthetic           # synthetic | csv | alpaca
```

### Using your own CSV data

Set `data.source: csv` and put `<SYMBOL>.csv` files in `data.csv_dir` with the
header `date,open,high,low,close,volume`.

## Live / paper trading with Alpaca (optional)

1. Install the extra: `pip install -r requirements-live.txt`
2. Create a **paper** account at <https://alpaca.markets> and copy `.env.example`
   to `.env`, filling in your paper keys.
3. Set `data.source: alpaca` in your config.
4. Run:

```bash
python main.py live --symbols AAPL,MSFT --poll 60
```

It defaults to the **paper** endpoint. Real-money trading additionally requires
pointing `ALPACA_BASE_URL` at the live API **and** setting `ALPACA_ALLOW_LIVE=yes`
— there is no accidental path to trading real money.

## Tests

```bash
pip install pytest
python -m pytest -q
```

## Project layout

```
bot/
  types.py          # shared dataclasses (Bar, Signal, Order, Position, Trade)
  config.py         # YAML config loading + validation
  indicators.py     # SMA / EMA / RSI over plain lists
  data/             # data feeds (synthetic, csv, alpaca)
  strategy/         # strategy interface + sma_crossover, rsi
  risk.py           # position sizing & risk gating
  portfolio.py      # cash/positions/P&L/equity curve
  broker/           # paper (simulated) + alpaca brokers
  engine.py         # per-bar trading loop
  backtest.py       # historical replay
  live.py           # live/paper polling loop
  metrics.py        # performance metrics + report
  cli.py            # argparse CLI
main.py             # entrypoint
tests/              # pytest suite
```

## Roadmap ideas

- More strategies (MACD, Bollinger bands, breakout)
- Short selling and bracket orders
- Parameter optimization / walk-forward analysis
- Equity-curve plotting and trade-log export
- Crypto support via ccxt
