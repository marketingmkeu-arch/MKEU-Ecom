"""End-to-End-Lauf: Rohdaten laden -> Nachfrage -> Preise -> Ergebnisobjekt."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from .calendar_data import load_school_holidays
from .competitor_analysis import CompBase, CompDay, CompListing, base_from_snapshots, classify, comp_days, load_comps, load_snapshot_rows
from .config import Paths
from .demand_model import DayDemand, build_demand
from .event_calendar import Event, load_events
from .historical_data import DailyObservation, EventImpact, estimate_event_uplift, estimate_factors, load_market_daily
from .market_data import MarketMetric, anchor_adr, load_market_aggregates
from .pricing_engine import BaseDerivation, DayPrice, PriceBands, apply_night_cap, blend_comp_base, derive_base, price_bands, price_day


@dataclass
class RunResult:
    as_of: date
    cfg: dict
    events: list[Event]
    metrics: list[MarketMetric]
    comps: list[CompListing]
    comp_by_day: dict[date, CompDay]
    history: list[DailyObservation]
    estimated_factors: dict
    event_impacts: list[EventImpact]
    demand: list[DayDemand]
    comp_base: CompBase | None
    derivation: BaseDerivation
    bands: PriceBands
    prices: list[DayPrice]
    shadow_prices: dict[int, int] | None
    bookings: dict[date, float] = None
    observed_dates: dict = None


def run(as_of: date, cfg: dict, paths: Paths = Paths(), pace: dict[date, float] | None = None) -> RunResult:
    raw = paths.raw
    events = load_events(raw / "events" / "events.csv")
    school = load_school_holidays(raw / "calendar" / "school_holidays_nrw.csv")
    metrics = load_market_aggregates(raw / "market" / "market_aggregates.csv")
    history = load_market_daily(raw / "historical" / "market_daily.csv")

    prop = cfg["property"]
    comps = classify(load_comps(raw / "comps" / "comp_listings.csv"), prop, cfg["competition"]["radius_bands_km"])
    comp_ids = {c.listing_id for c in comps if c.comp_class == "vergleichbar"}
    snapshots = load_snapshot_rows(raw / "comps" / "price_snapshots.csv")
    comp_by_day = comp_days(snapshots, comp_ids)

    # Historische Faktoren ersetzen die Priors nur, wenn genügend Daten vorliegen
    factors = estimate_factors(history, events)
    for section in ("weekday", "season"):
        cfg[section].update(factors.get(section, {}))
    impacts = estimate_event_uplift(history, events)

    demand = build_demand(as_of, cfg["output"]["horizon_days"], cfg, events, school)
    anchor, steps = anchor_adr(metrics, cfg["market_anchor"]["weights"])
    derivation = derive_base(anchor, steps, demand, cfg)
    usable = {c.listing_id for c in comps if c.comp_class != "nicht vergleichbar"}
    comp_base = base_from_snapshots(snapshots, usable, {d.day: d.index for d in demand})
    derivation = blend_comp_base(derivation, comp_base.value if comp_base else None,
                                 comp_base.n_listings if comp_base else 0, cfg)
    bands = price_bands(derivation.base, cfg)
    pace = pace or {}
    prices = [price_day(d, bands, cfg, as_of, comp_by_day.get(d.day), pace.get(d.day)) for d in demand]
    bookings = load_bookings(raw / "bookings" / "own_bookings.csv")
    for p in prices:
        if p.demand.day in bookings:
            p.quota_recommendation = "gebucht"
            paid = bookings[p.demand.day]
            p.reasons.append(f"bereits gebucht (Auszahlung {paid:.0f} EUR)" if paid is not None else "bereits gebucht (Auszahlung unbekannt)")
    for a, b in cfg.get("availability", {}).get("blocked_nights", []):
        start, end = date.fromisoformat(a), date.fromisoformat(b)
        for p in prices:
            if start <= p.demand.day <= end and p.quota_recommendation != "gebucht":
                p.quota_recommendation = "blockiert"
                p.reasons.append("blockiert (Urlaub) – nur als Gesamtzeitraum vermietbar")
    shadow = apply_night_cap(prices, cfg)
    # Mindestaufenthalt nie länger als die freie Lücke bis zur nächsten belegten/gesperrten Nacht
    unavailable = {"gebucht", "blockiert", "geschlossen"}
    for i, p in enumerate(prices):
        if p.quota_recommendation in unavailable:
            continue
        gap = 0
        for q in prices[i:]:
            if q.quota_recommendation in unavailable:
                break
            gap += 1
        if gap < p.min_nights and i + gap < len(prices):
            p.min_nights = gap
            p.reasons.append(f"Mindestaufenthalt auf {gap} verkürzt (freie Lücke)")
    import statistics
    per_day: dict[date, list[float]] = {}
    for r in snapshots:
        if r["listing_id"] in usable and r.get("nightly_price"):
            per_day.setdefault(date.fromisoformat(r["stay_date"]), []).append(float(r["nightly_price"]))
    observed = {d: statistics.median(v) for d, v in per_day.items() if len(v) >= 5}
    # Manuelle Entscheidungen des Eigentümers / nach Evidenzprüfung (Gastpreis inkl. allem)
    for day_str, ov in cfg.get("overrides", {}).items():
        for p in prices:
            if p.demand.day == date.fromisoformat(day_str) and p.quota_recommendation not in unavailable:
                p.recommended = int(ov["price"])
                p.reasons.append(f"Manuell gesetzt: {ov['reason']}")
    return RunResult(as_of, cfg, events, metrics, comps, comp_by_day, history, factors, impacts,
                     demand, comp_base, derivation, bands, prices, shadow, bookings, observed)


def load_bookings(path) -> dict[date, float]:
    """Eigene Buchungen (Datenklasse 1, realisiert): Aufenthaltsdatum -> Auszahlung."""
    import csv
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as fh:
        return {date.fromisoformat(r["stay_date"]): (float(r["payout_eur"]) if r.get("payout_eur") else None)
                for r in csv.DictReader(fh) if r.get("stay_date")}


def median_price(prices: list[DayPrice], pred) -> float | None:
    vals = [p.static_price for p in prices if pred(p)]
    return statistics.median(vals) if vals else None
