"""Konfiguration und Projektpfade."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "pricing.toml"


@dataclass(frozen=True)
class Paths:
    root: Path = PROJECT_ROOT

    @property
    def raw(self) -> Path:
        return self.root / "data" / "raw"

    @property
    def processed(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def output(self) -> Path:
        return self.root / "output"

    @property
    def reports(self) -> Path:
        return self.root / "reports"


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)
