"""Marktaggregate externer Anbieter und Ableitung der Anker-ADR."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MarketMetric:
    provider: str
    geography: str
    metric: str
    value: float
    unit: str
    period: str
    url: str
    data_class: str
    confidence: str
    method_note: str


def load_market_aggregates(path: Path) -> list[MarketMetric]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            MarketMetric(
                r["provider"], r["geography"], r["metric"], float(r["value"]), r["unit"],
                r["period"], r["url"], r["data_class"], r["confidence"], r["method_note"],
            )
            for r in csv.DictReader(fh)
        ]


def anchor_adr(metrics: list[MarketMetric], weights: dict[str, float]) -> tuple[float, list[str]]:
    """Gewichtete EUR-ADR der Nachbarviertel. Liefert Wert und Herleitungsschritte."""
    adr = {m.geography: m.value for m in metrics if m.metric == "adr" and m.unit == "EUR"}
    missing = [g for g in weights if g not in adr]
    if missing:
        raise ValueError(f"Keine ADR für: {', '.join(missing)}")
    total_w = sum(weights.values())
    value = sum(adr[g] * w for g, w in weights.items()) / total_w
    steps = [f"{g}: {adr[g]:.0f} EUR × {w / total_w:.2f}" for g, w in weights.items()]
    return value, steps
