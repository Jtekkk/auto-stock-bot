"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RiskConfig:
    max_position_pct: float = 0.20
    max_open_positions: int = 5
    stop_loss_pct: float = 0.03
    take_profit_pct: float = 0.06
    max_drawdown_pct: float = 0.15


@dataclass
class StrategyConfig:
    name: str = "sma_crossover"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataConfig:
    source: str = "synthetic"
    csv_dir: str = "data"
    synthetic_bars: int = 500
    timeframe: str = "1Day"


@dataclass
class Config:
    symbols: list[str] = field(default_factory=lambda: ["AAPL"])
    starting_cash: float = 100_000.0
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    data: DataConfig = field(default_factory=DataConfig)

    @staticmethod
    def load(path: str | Path) -> "Config":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return Config.from_dict(raw)

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "Config":
        cfg = Config()
        if "symbols" in raw and raw["symbols"]:
            cfg.symbols = [str(s).upper() for s in raw["symbols"]]
        if "starting_cash" in raw:
            cfg.starting_cash = float(raw["starting_cash"])
        if "strategy" in raw and raw["strategy"]:
            s = raw["strategy"]
            cfg.strategy = StrategyConfig(
                name=str(s.get("name", cfg.strategy.name)),
                params=dict(s.get("params") or {}),
            )
        if "risk" in raw and raw["risk"]:
            cfg.risk = _merge_dataclass(RiskConfig(), raw["risk"])
        if "data" in raw and raw["data"]:
            cfg.data = _merge_dataclass(DataConfig(), raw["data"])
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if not self.symbols:
            raise ValueError("config: at least one symbol is required")
        if self.starting_cash <= 0:
            raise ValueError("config: starting_cash must be positive")
        r = self.risk
        if not 0 < r.max_position_pct <= 1:
            raise ValueError("config: risk.max_position_pct must be in (0, 1]")
        if r.max_open_positions < 1:
            raise ValueError("config: risk.max_open_positions must be >= 1")
        for name in ("stop_loss_pct", "take_profit_pct", "max_drawdown_pct"):
            if getattr(r, name) < 0:
                raise ValueError(f"config: risk.{name} must be >= 0")


def _merge_dataclass(instance: Any, overrides: dict[str, Any]) -> Any:
    """Apply known keys from `overrides` onto a dataclass instance."""
    valid = set(instance.__dataclass_fields__)
    for key, value in overrides.items():
        if key in valid:
            current = getattr(instance, key)
            # Preserve int/float typing from the dataclass default.
            if isinstance(current, bool):
                setattr(instance, key, bool(value))
            elif isinstance(current, int) and not isinstance(current, bool):
                setattr(instance, key, int(value))
            elif isinstance(current, float):
                setattr(instance, key, float(value))
            else:
                setattr(instance, key, value)
    return instance
