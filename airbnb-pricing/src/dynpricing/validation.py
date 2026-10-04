"""Backtesting: Modellpreise gegen historische Marktpreise.

Prüft, ob das Modell Events ausreichend berücksichtigt, normale Tage nicht überpreist
und starke Nachfragetage nicht unterpreist. Ohne historische Tagesdaten wird
ausdrücklich "keine belastbaren Daten" gemeldet.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from .historical_data import DailyObservation


@dataclass(frozen=True)
class BacktestResult:
    n_days: int
    mape: float
    bias_normal_days: float
    bias_event_days: float
    rank_correlation: float
    underpriced_event_days: list[date]
    overpriced_normal_days: list[date]


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(a: list[float], b: list[float]) -> float:
    if len(a) < 3:
        return float("nan")
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    var = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return cov / var if var else float("nan")


def backtest(
    model_prices: dict[date, float],
    market: list[DailyObservation],
    event_days: set[date],
    scale: float = 1.0,
    tolerance: float = 0.15,
) -> BacktestResult | None:
    """Vergleich Modell (× scale, z. B. Positionierung ggü. Markt) mit Markt-ADR je Tag."""
    pairs = [(o.day, model_prices[o.day] * scale, o.adr) for o in market if o.day in model_prices]
    if not pairs:
        return None
    errors = [(m - a) / a for _, m, a in pairs]
    normal = [e for (d, _, _), e in zip(pairs, errors) if d not in event_days]
    events = [e for (d, _, _), e in zip(pairs, errors) if d in event_days]
    return BacktestResult(
        n_days=len(pairs),
        mape=statistics.mean(abs(e) for e in errors),
        bias_normal_days=statistics.mean(normal) if normal else float("nan"),
        bias_event_days=statistics.mean(events) if events else float("nan"),
        rank_correlation=spearman([m for _, m, _ in pairs], [a for _, _, a in pairs]),
        underpriced_event_days=[d for (d, _, _), e in zip(pairs, errors) if d in event_days and e < -tolerance],
        overpriced_normal_days=[d for (d, _, _), e in zip(pairs, errors) if d not in event_days and e > tolerance],
    )
