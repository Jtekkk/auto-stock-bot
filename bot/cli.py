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

from bot.backtest import run_backtest
from bot.config import Config
from bot.data.feed import build_feed
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
    metrics = run_backtest(config, feed, verbose=args.verbose)
    print(metrics.render())
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
    bt.set_defaults(func=_cmd_backtest)

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
