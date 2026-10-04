"""Historische Marktdaten: Laden, Faktor-Schätzung und Event-Wirkung.

Erwartet Tagesdaten (date, adr, occupancy) z. B. aus einem AirDNA-/PriceLabs-Export,
eigenen Buchungsdaten oder regelmäßigen Preis-Snapshots. Ohne Daten liefern die
Funktionen leere Ergebnisse – es werden keine Werte erfunden.
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .event_calendar import WEEKDAY_KEYS, Event

MONTH_KEYS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


@dataclass(frozen=True)
class DailyObservation:
    day: date
    adr: float
    occupancy: float | None
    source: str
    data_class: str


def load_market_daily(path: Path) -> list[DailyObservation]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            DailyObservation(
                date.fromisoformat(r["date"]), float(r["adr"]),
                float(r["occupancy"]) if r.get("occupancy") else None,
                r.get("source", ""), r.get("data_class", ""),
            )
            for r in csv.DictReader(fh)
            if r.get("date") and r.get("adr")
        ]


def event_nights(events: list[Event]) -> set[date]:
    nights: set[date] = set()
    for ev in events:
        nights.update(ev.night_weights(0.8, 0.3))
    return nights


def estimate_factors(obs: list[DailyObservation], events: list[Event], min_obs: int = 8) -> dict[str, dict[str, float]]:
    """Wochentags- und Monatsfaktoren aus Nicht-Event-Tagen (Median relativ zum Gesamtmedian)."""
    excluded = event_nights(events)
    clean = [o for o in obs if o.day not in excluded]
    if len(clean) < 60:
        return {}
    overall = statistics.median(o.adr for o in clean)
    result: dict[str, dict[str, float]] = {"weekday": {}, "season": {}}
    for idx, key in enumerate(WEEKDAY_KEYS):
        vals = [o.adr for o in clean if o.day.weekday() == idx]
        if len(vals) >= min_obs:
            result["weekday"][key] = round(statistics.median(vals) / overall, 3)
    for idx, key in enumerate(MONTH_KEYS, start=1):
        vals = [o.adr for o in clean if o.day.month == idx]
        if len(vals) >= min_obs:
            result["season"][key] = round(statistics.median(vals) / overall, 3)
    return result


@dataclass(frozen=True)
class EventImpact:
    event_id: str
    name: str
    event_adr: float
    baseline_adr: float
    uplift: float
    event_occupancy: float | None
    baseline_occupancy: float | None
    n_event_nights: int
    n_baseline_nights: int


def estimate_event_uplift(obs: list[DailyObservation], events: list[Event], window_weeks: int = 4) -> list[EventImpact]:
    """Event-ADR vs. Baseline gleicher Wochentage ±window_weeks ohne Events."""
    by_day = {o.day: o for o in obs}
    excluded = event_nights(events)
    impacts: list[EventImpact] = []
    for ev in events:
        nights = [d for d, w in ev.night_weights(0.0, 0.0).items() if w >= 1.0 and d in by_day]
        if not nights:
            continue
        base: list[DailyObservation] = []
        for n in nights:
            for k in range(1, window_weeks + 1):
                for d in (n - timedelta(weeks=k), n + timedelta(weeks=k)):
                    if d in by_day and d not in excluded:
                        base.append(by_day[d])
        if len(base) < 3:
            continue
        ev_adr = statistics.mean(by_day[n].adr for n in nights)
        base_adr = statistics.mean(o.adr for o in base)
        ev_occ = [by_day[n].occupancy for n in nights if by_day[n].occupancy is not None]
        base_occ = [o.occupancy for o in base if o.occupancy is not None]
        impacts.append(
            EventImpact(
                ev.event_id, ev.name, round(ev_adr, 2), round(base_adr, 2), round(ev_adr / base_adr - 1, 3),
                round(statistics.mean(ev_occ), 3) if ev_occ else None,
                round(statistics.mean(base_occ), 3) if base_occ else None,
                len(nights), len(base),
            )
        )
    return impacts
