#!/usr/bin/env python3
"""Entrypoint: `python main.py backtest` / `live` / `strategies`."""

from bot.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
