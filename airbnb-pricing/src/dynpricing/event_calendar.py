"""Event- und Messekalender: Laden, Entfernungen und Nachtgewichte."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _opt_float(value: str) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


@dataclass(frozen=True)
class Event:
    event_id: str
    name: str
    category: str
    venue: str
    city: str
    lat: float
    lon: float
    start: date
    end: date
    impact_tier: str
    expected_visitors: int | None = None
    visitors_basis: str = ""
    international_share: float | None = None
    applies_to: tuple[str, ...] = ()
    pre_night_weight: float | None = None
    last_night_weight: float | None = None
    source_url: str = ""
    source_type: str = ""
    confidence: str = ""
    notes: str = ""

    def distance_km(self, lat: float, lon: float) -> float:
        return haversine_km(lat, lon, self.lat, self.lon)

    def night_weights(self, default_pre: float, default_last: float) -> dict[date, float]:
        """Gewicht je Übernachtung (Datum = Anreisetag der Nacht)."""
        pre = default_pre if self.pre_night_weight is None else self.pre_night_weight
        last = default_last if self.last_night_weight is None else self.last_night_weight
        weights: dict[date, float] = {}
        if pre > 0:
            weights[self.start - timedelta(days=1)] = pre
        day = self.start
        while day < self.end:
            weights[day] = 1.0
            day += timedelta(days=1)
        if last > 0:
            weights[self.end] = max(weights.get(self.end, 0.0), last)
        if self.applies_to:
            weights = {d: w for d, w in weights.items() if WEEKDAY_KEYS[d.weekday()] in self.applies_to}
        return weights


def load_events(path: Path) -> list[Event]:
    events: list[Event] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            visitors = _opt_float(r["expected_visitors"])
            events.append(
                Event(
                    event_id=r["event_id"],
                    name=r["name"],
                    category=r["category"],
                    venue=r["venue"],
                    city=r["city"],
                    lat=float(r["lat"]),
                    lon=float(r["lon"]),
                    start=date.fromisoformat(r["start_date"]),
                    end=date.fromisoformat(r["end_date"]),
                    impact_tier=r["impact_tier"].strip().upper(),
                    expected_visitors=int(visitors) if visitors is not None else None,
                    visitors_basis=r["visitors_basis"],
                    international_share=_opt_float(r["international_share"]),
                    applies_to=tuple(x for x in r["applies_to"].split(";") if x),
                    pre_night_weight=_opt_float(r["pre_night_weight"]),
                    last_night_weight=_opt_float(r["last_night_weight"]),
                    source_url=r["source_url"],
                    source_type=r["source_type"],
                    confidence=r["confidence"],
                    notes=r["notes"],
                )
            )
    return events


@dataclass
class EventEffect:
    """Event-Wirkung auf eine einzelne Nacht."""

    uplift: float = 0.0
    contributions: list[tuple[Event, float]] = field(default_factory=list)
    max_tier: str | None = None

    @property
    def names(self) -> str:
        return " + ".join(e.name for e, _ in self.contributions)


TIER_ORDER = "SABCD"


def event_effects(events: list[Event], cfg_events: dict) -> dict[date, EventEffect]:
    """Kombinierte Event-Uplifts pro Nacht (stärkstes Event voll, weitere abgeschwächt)."""
    tier_uplift = cfg_events["tier_uplift"]
    decay = cfg_events["overlap_decay"]
    per_night: dict[date, list[tuple[Event, float]]] = {}
    for ev in events:
        for night, w in ev.night_weights(cfg_events["pre_night_weight"], cfg_events["last_night_weight"]).items():
            per_night.setdefault(night, []).append((ev, tier_uplift[ev.impact_tier] * w))
    effects: dict[date, EventEffect] = {}
    for night, contribs in per_night.items():
        contribs.sort(key=lambda c: c[1], reverse=True)
        uplift = sum(u * decay**i for i, (_, u) in enumerate(contribs))
        max_tier = min((e.impact_tier for e, u in contribs if u > 0), key=TIER_ORDER.index, default=None)
        effects[night] = EventEffect(uplift, contribs, max_tier)
    return effects
