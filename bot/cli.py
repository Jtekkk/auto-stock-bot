"""Command-line interface.

Subcommands:
  backtest   Replay historical/synthetic data and print performance metrics.
  live       Run the paper/live trading loop (Alpaca).
  strategies List available strategies.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bot.backtest import run_backtest_detailed
from bot.config import Config
from bot.data.feed import build_feed
from bot.optimize import grid_search, parse_grid
from bot.report import export_equity_curve, export_trades
from bot.strategy.base import available_strategies


def _load_config(args: argparse.Namespace) -> Config:
    if args.config and Path(args.config).exists():
        config = Config.load(args.config)
    elif args.config:
        print(f"Config file not found: {args.config}", file=sys.stderr)
        raise SystemExit(2)
    else:
        config = Config()  # built-in defaults

    # CLI overrides take precedence over the file.
    if args.symbols:
        config.symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if args.strategy:
        config.strategy.name = args.strategy
    if getattr(args, "cash", None):
        config.starting_cash = args.cash
    if getattr(args, "source", None):
        config.data.source = args.source
    config.validate()
    return config


def _cmd_backtest(args: argparse.Namespace) -> int:
    config = _load_config(args)
    feed = build_feed(config.data, config.symbols)
    print(
        f"Backtesting {config.strategy.name} on {', '.join(config.symbols)} "
        f"({config.data.source} data)...\n"
    )
    metrics, portfolio = run_backtest_detailed(config, feed, verbose=args.verbose)
    print(metrics.render())

    if args.export:
        out = Path(args.export)
        trades_path = export_trades(portfolio, out / "trades.csv")
        equity_path = export_equity_curve(portfolio, out / "equity_curve.csv")
        print(f"\nExported {len(portfolio.trades)} trade rows -> {trades_path}")
        print(f"Exported equity curve            -> {equity_path}")
    return 0


def _cmd_live(args: argparse.Namespace) -> int:
    config = _load_config(args)
    if config.data.source == "synthetic":
        print(
            "Refusing to run 'live' on synthetic data — it never updates.\n"
            "Set data.source to 'alpaca' (or 'csv') first.",
            file=sys.stderr,
        )
        return 2

    from bot.broker.alpaca_broker import AlpacaBroker
    from bot.live import run_live

    feed = build_feed(config.data, config.symbols)
    broker = AlpacaBroker()
    mode = "PAPER" if getattr(broker, "is_paper", True) else "LIVE (REAL MONEY)"
    print(f"Trading mode: {mode}")
    run_live(config, feed, broker, poll_seconds=args.poll, max_iterations=args.iterations)
    return 0


def _cmd_optimize(args: argparse.Namespace) -> int:
    config = _load_config(args)
    try:
        grid = parse_grid(args.grid)
    except ValueError as exc:
        print(f"Invalid --grid: {exc}", file=sys.stderr)
        return 2
    print(
        f"Optimizing {config.strategy.name} on {', '.join(config.symbols)} "
        f"(ranking by {args.metric})...\n"
    )
    report = grid_search(config, grid, metric=args.metric)
    if not report.results:
        print("No valid parameter combinations were produced.", file=sys.stderr)
        return 1
    print(report.render(top=args.top))
    best = report.best
    assert best is not None
    print("\nBest params:", ", ".join(f"{k}={v}" for k, v in best.params.items()))
    return 0


def _cmd_strategies(_args: argparse.Namespace) -> int:
    print("Available strategies:")
    for name in available_strategies():
        print(f"  - {name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bot", description="A small day-trading bot.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--config", "-c", help="Path to a YAML config file.")
        p.add_argument("--symbols", "-s", help="Comma-separated symbols (overrides config).")
        p.add_argument("--strategy", help="Strategy name (overrides config).")

    bt = sub.add_parser("backtest", help="Run a historical backtest.")
    add_common(bt)
    bt.add_argument("--cash", type=float, help="Starting cash (overrides config).")
    bt.add_argument(
        "--source", choices=["synthetic", "csv", "alpaca"], help="Data source override."
    )
    bt.add_argument("--verbose", "-v", action="store_true", help="Print every trade.")
    bt.add_argument(
        "--export", metavar="DIR", help="Write trades.csv and equity_curve.csv to DIR."
    )
    bt.set_defaults(func=_cmd_backtest)

    op = sub.add_parser("optimize", help="Grid-search strategy parameters.")
    add_common(op)
    op.add_argument("--cash", type=float, help="Starting cash (overrides config).")
    op.add_argument("--source", choices=["synthetic", "csv", "alpaca"], help="Data source.")
    op.add_argument(
        "--grid",
        required=True,
        help="Parameter grid, e.g. 'fast=5,10,15;slow=20,30,40'.",
    )
    op.add_argument(
        "--metric",
        default="sharpe",
        choices=["sharpe", "total_return_pct", "profit_factor", "win_rate_pct", "ending_equity"],
        help="Metric to rank by (default: sharpe).",
    )
    op.add_argument("--top", type=int, default=10, help="How many top results to show.")
    op.set_defaults(func=_cmd_optimize)

    lv = sub.add_parser("live", help="Run the paper/live trading loop.")
    add_common(lv)
    lv.add_argument("--source", choices=["csv", "alpaca"], help="Data source override.")
    lv.add_argument("--poll", type=int, default=60, help="Seconds between polls (default 60).")
    lv.add_argument(
        "--iterations", type=int, default=None, help="Stop after N polls (default: run forever)."
    )
    lv.set_defaults(func=_cmd_live)

    st = sub.add_parser("strategies", help="List available strategies.")
    st.set_defaults(func=_cmd_strategies)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
