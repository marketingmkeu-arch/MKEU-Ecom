"""Comp-Set: Vergleichbarkeitsbewertung, Radien und angebotene Preise.

Alle Preise aus price_snapshots.csv sind ANGEBOTENE Preise (Listing-Kalender),
keine realisierten Buchungspreise.
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .event_calendar import haversine_km


def _f(v: str) -> float | None:
    v = (v or "").strip()
    return float(v) if v else None


def _b(v: str) -> bool | None:
    v = (v or "").strip().lower()
    if v in ("1", "true", "ja", "yes"):
        return True
    if v in ("0", "false", "nein", "no"):
        return False
    return None


@dataclass
class CompListing:
    listing_id: str
    neighbourhood: str
    lat: float | None
    lon: float | None
    size_m2: float | None
    bedrooms: float | None
    max_guests: float | None
    entire_home: bool | None
    renovated: bool | None
    balcony: bool | None
    kitchen: bool | None
    rating: float | None
    reviews_count: float | None
    cleaning_fee: float | None
    min_nights: float | None
    weekly_discount: float | None
    monthly_discount: float | None
    url: str = ""
    distance_km: float | None = None
    score: float = 0.0
    comp_class: str = ""
    radius_band_km: float | None = None


def load_comps(path: Path) -> list[CompListing]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [
        CompListing(
            r["listing_id"], r["neighbourhood"], _f(r["lat"]), _f(r["lon"]),
            _f(r["size_m2"]), _f(r["bedrooms"]), _f(r["max_guests"]), _b(r["entire_home"]),
            _b(r["renovated"]), _b(r["balcony"]), _b(r["kitchen"]), _f(r["rating"]), _f(r["reviews_count"]),
            _f(r["cleaning_fee"]), _f(r["min_nights"]), _f(r["weekly_discount"]),
            _f(r["monthly_discount"]), r["url"],
        )
        for r in rows
        if r.get("listing_id")
    ]


def similarity_score(comp: CompListing, prop: dict) -> float:
    """Score 0..100. Fehlende Merkmale geben halbe Punkte (unbekannt ≠ schlecht)."""
    score = 0.0
    # Lage (30): linear bis 5 km; unbekannte Lage = halbe Punkte
    if comp.distance_km is None:
        score += 15
    else:
        score += 30 * max(0.0, 1 - comp.distance_km / 5.0)
    # Größe (20): voll innerhalb 45–75 m², linear abfallend bis ±25 m² darüber hinaus
    if comp.size_m2 is None:
        score += 10
    else:
        gap = max(0.0, 45 - comp.size_m2, comp.size_m2 - 75)
        score += 20 * max(0.0, 1 - gap / 25)
    # Schlafzimmer (15)
    if comp.bedrooms is None:
        score += 7.5
    else:
        score += 15 if comp.bedrooms == prop["bedrooms"] else (5 if abs(comp.bedrooms - prop["bedrooms"]) == 1 else 0)
    # Gesamte Wohnung (15) – Pflichtkriterium, sonst nur eingeschränkt vergleichbar
    score += {True: 15, None: 7.5, False: 0}[comp.entire_home]
    # Ausstattung (20)
    for flag, pts in ((comp.renovated, 8), (comp.balcony, 6), (comp.kitchen, 6)):
        score += {True: pts, None: pts / 2, False: 0}[flag]
    return round(score, 1)


def classify(comps: list[CompListing], prop: dict, radius_bands: list[float]) -> list[CompListing]:
    for c in comps:
        if c.lat is not None and c.lon is not None:
            c.distance_km = haversine_km(prop["lat"], prop["lon"], c.lat, c.lon)
            c.radius_band_km = next((r for r in radius_bands if c.distance_km <= r), None)
        c.score = similarity_score(c, prop)
        if c.entire_home is False:
            c.comp_class = "nicht vergleichbar"
        elif c.distance_km is None:
            # Ohne Koordinaten nie voll vergleichbar (Lage ist der wichtigste Faktor)
            c.comp_class = "eingeschränkt vergleichbar (Lage unbekannt)" if c.score >= 45 else "nicht vergleichbar"
        elif c.radius_band_km is None:
            c.comp_class = "nicht vergleichbar"
        elif c.score >= 75:
            c.comp_class = "vergleichbar"
        elif c.score >= 55:
            c.comp_class = "eingeschränkt vergleichbar"
        else:
            c.comp_class = "nicht vergleichbar"
    return sorted(comps, key=lambda c: c.score, reverse=True)


@dataclass(frozen=True)
class CompDay:
    stay_date: date
    median_offered: float
    n_listings: int
    availability_ratio: float


def load_snapshot_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("listing_id")]


def comp_days(snapshots: list[dict], comp_ids: set[str]) -> dict[date, CompDay]:
    """Median angebotener Preis + Verfügbarkeit je Aufenthaltsdatum (letzter Snapshot je Listing)."""
    latest: dict[tuple[str, date], dict] = {}
    for r in snapshots:
        if r["listing_id"] not in comp_ids:
            continue
        key = (r["listing_id"], date.fromisoformat(r["stay_date"]))
        if key not in latest or r["snapshot_date"] > latest[key]["snapshot_date"]:
            latest[key] = r
    by_day: dict[date, list[dict]] = {}
    for (_, d), r in latest.items():
        by_day.setdefault(d, []).append(r)
    result: dict[date, CompDay] = {}
    for d, rows in by_day.items():
        available = [r for r in rows if _b(r["available"])]
        prices = [float(r["nightly_price"]) for r in available if r["nightly_price"]]
        result[d] = CompDay(
            d,
            statistics.median(prices) if prices else float("nan"),
            len(rows),
            len(available) / len(rows) if rows else 1.0,
        )
    return result


@dataclass(frozen=True)
class CompBase:
    """Aus angebotenen Comp-Preisen abgeleiteter Normaltagspreis (Index 1.0)."""

    value: float
    n_listings: int
    n_observations: int
    normalized: dict[str, float]


def base_from_snapshots(snapshots: list[dict], listing_ids: set[str], index_by_day: dict[date, float]) -> CompBase | None:
    """Median über Listings von (angebotener Preis ÷ Nachfrageindex des Aufenthaltstags).

    So werden Beobachtungen an Wochenenden oder in starken Monaten auf einen Normaltag
    zurückgerechnet. Nutzt nur verfügbare Nächte innerhalb des Kalenderhorizonts.
    """
    per_listing: dict[str, list[float]] = {}
    for r in snapshots:
        if r["listing_id"] not in listing_ids or not _b(r["available"]) or not r["nightly_price"]:
            continue
        idx = index_by_day.get(date.fromisoformat(r["stay_date"]))
        if not idx:
            continue
        per_listing.setdefault(r["listing_id"], []).append(float(r["nightly_price"]) / idx)
    if not per_listing:
        return None
    normalized = {lid: statistics.median(v) for lid, v in per_listing.items()}
    return CompBase(
        statistics.median(normalized.values()), len(normalized),
        sum(len(v) for v in per_listing.values()), normalized,
    )
