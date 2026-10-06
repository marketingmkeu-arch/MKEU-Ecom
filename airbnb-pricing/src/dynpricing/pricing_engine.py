"""Pricing-Engine: Basispreis, Preisgrenzen, Tagespreis, Lead-Time, Pace, Mindestaufenthalt."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

from .competitor_analysis import CompDay
from .demand_model import DayDemand

WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


@dataclass(frozen=True)
class PriceBands:
    base: float
    minimum: float
    target: float
    high_demand: float
    event: float
    maximum: float

    def as_dict(self) -> dict[str, float]:
        return {
            "Minimum Price": self.minimum,
            "Normal/Base Price": self.base,
            "Target Price": self.target,
            "High-Demand Price": self.high_demand,
            "Event Price": self.event,
            "Maximum Price": self.maximum,
        }


@dataclass(frozen=True)
class BaseDerivation:
    anchor_adr: float
    anchor_steps: list[str]
    adjusted_anchor: float
    demand_weighted_index: float
    base: float
    market_base: float = 0.0
    comp_base: float | None = None
    comp_n: int = 0
    comp_weight: float = 0.0
    launch_factor: float = 1.0


def derive_base(anchor_adr: float, anchor_steps: list[str], demand: list[DayDemand], cfg: dict) -> BaseDerivation:
    """Basispreis = angepasste Anker-ADR / nachfragegewichteter Ø-Index.

    Die Markt-ADR ist ein Durchschnitt über *gebuchte* Nächte, die überproportional auf
    nachfragestarke Tage fallen. Gewichtet man den Index mit sich selbst (Proxy für die
    Buchungswahrscheinlichkeit), ergibt sich der Preis eines Normaltages (Index 1.0),
    bei dem die erwartete Modell-ADR der Markt-ADR entspricht.
    """
    m = cfg["market_anchor"]
    adjusted = anchor_adr * m["unit_size_adjustment"] * m["quality_premium"]
    idx = [d.index for d in demand]
    weighted = sum(i * i for i in idx) / sum(idx) if idx else 1.0
    base = adjusted / weighted if m.get("calibrate_base_to_anchor", True) else adjusted
    return BaseDerivation(anchor_adr, anchor_steps, adjusted, weighted, base, market_base=base)


def blend_comp_base(d: BaseDerivation, comp_base: float | None, comp_n: int, cfg: dict) -> BaseDerivation:
    """Marktbasis mit beobachteter Comp-Basis mischen; Startrabatt-Faktor festhalten.

    Gewicht der Comps steigt mit der Zahl der Listings (beobachtete Daten schlagen
    Anbieter-Aggregate), begrenzt auf base_blend_max_weight.
    """
    c = cfg["competition"]
    weight = 0.0
    base = d.market_base
    if comp_base is not None and comp_n >= c.get("min_comps_for_base", 5):
        weight = min(c["base_blend_max_weight"], comp_n * c["base_blend_per_listing"])
        base = (1 - weight) * d.market_base + weight * comp_base * c["position_vs_median"]
    launch = cfg.get("launch", {})
    factor = 1 - launch.get("discount", 0.0) if launch.get("active") else 1.0
    return BaseDerivation(
        d.anchor_adr, d.anchor_steps, d.adjusted_anchor, d.demand_weighted_index, base,
        market_base=d.market_base, comp_base=comp_base, comp_n=comp_n, comp_weight=weight, launch_factor=factor,
    )


def price_bands(base: float, cfg: dict) -> PriceBands:
    b = cfg["bounds"]
    return PriceBands(
        base=base,
        minimum=max(b["absolute_minimum_eur"], base * b["minimum"]),
        target=base * b["target"],
        high_demand=base * b["high_demand"],
        event=base * b["event"],
        maximum=base * b["maximum"],
    )


def round_price(p: float, to_nine: bool, floor: float | None = None) -> int:
    """Rundung (optional auf 9er-Endung); fällt nie unter `floor`."""
    if not to_nine:
        r = int(round(p))
        return max(r, math.ceil(floor)) if floor is not None else r
    r = int(math.floor((p + 1) / 10 + 0.5) * 10 - 1)
    if floor is not None and r < floor:
        r = int(math.ceil((floor + 1) / 10) * 10 - 1)
    return r


def lead_time_factor(days_ahead: int, demand: DayDemand, cfg: dict, comp: CompDay | None = None) -> tuple[float, str]:
    """Multiplikator nach Buchungsvorlauf. Bei Verknappung kein Rabatt, ggf. Aufschlag."""
    lt = cfg["lead_time"]
    bucket = next(b for b in lt["buckets"] if days_ahead <= b["max_days"])
    scarce = comp is not None and comp.availability_ratio < lt["scarcity_availability_threshold"]
    if demand.level in ("hoch", "Spitze") or scarce:
        column = "high"
    elif demand.level == "niedrig":
        column = "low"
    else:
        column = "normal"
    return bucket[column], column


@dataclass
class DayPrice:
    demand: DayDemand
    base: float
    static_price: float
    recommended: int
    lead_time_factor: float
    lead_time_mode: str
    pace_factor: float
    comp_median: float | None
    min_nights: int
    band: str
    reasons: list[str] = field(default_factory=list)
    quota_priority: int | None = None
    quota_recommendation: str = ""


def min_nights_for(d: DayDemand, cfg: dict) -> int:
    """Wochentagsregel des Eigentümers (Fr/Sa länger), Events können sie nur verlängern."""
    los = cfg["length_of_stay"]
    base = los["weekend_min_nights"] if d.day.weekday() in (4, 5) else los["default_min_nights"]
    if d.event.max_tier:
        base = max(base, los["event_min_nights"][d.event.max_tier])
    return base


def _band_label(price: float, bands: PriceBands) -> str:
    if price >= bands.event:
        return "Event"
    if price >= bands.high_demand:
        return "High-Demand"
    if price >= bands.target:
        return "Target"
    if price > bands.minimum + 0.5:
        return "Base"
    return "Minimum"


def price_day(
    d: DayDemand,
    bands: PriceBands,
    cfg: dict,
    as_of: date,
    comp: CompDay | None = None,
    pace_ratio: float | None = None,
) -> DayPrice:
    reasons = [f"Saison {d.season:.2f}", f"Wochentag {d.weekday:.2f}"]
    if d.holiday_label:
        reasons.append(f"{d.holiday_label} ({d.holiday_adj:+.0%})")
    if d.school_holiday:
        reasons.append(f"Schulferien NRW ({cfg['holiday']['school_holiday_nrw']:+.0%})")
    if d.event.contributions:
        reasons.append(f"Event: {d.event.names} ({d.event.uplift:+.0%})")
    reasons.append(f"Nachfrageindex {d.index:.2f}")

    price = bands.base * d.index
    tier = d.event.max_tier
    # Untergrenzen nur für volle Eventnächte (nicht An-/Abreisenächte)
    full_night = tier is not None and d.event.uplift >= cfg["events"]["tier_uplift"][tier] * 0.99
    if tier == "S" and full_night and price < bands.event:
        price = bands.event
        reasons.append("Untergrenze Event Price (Leitmesse)")
    elif tier == "A" and full_night and price < bands.high_demand:
        price = bands.high_demand
        reasons.append("Untergrenze High-Demand Price (große Messe/Event)")

    comp_median = None
    if comp and comp.n_listings >= cfg["competition"]["min_comps_for_blend"] and not math.isnan(comp.median_offered):
        comp_median = comp.median_offered
        w = cfg["competition"]["comp_blend_weight"]
        target = comp_median * cfg["competition"]["position_vs_median"]
        price = (1 - w) * price + w * target
        reasons.append(f"Comp-Median angeboten {comp_median:.0f} EUR (Gewicht {w:.0%}, Verfügbarkeit {comp.availability_ratio:.0%})")

    launch = cfg.get("launch", {})
    if launch.get("active") and d.level not in ("hoch", "Spitze"):
        # Startrabatt nur an normalen Tagen; an Messe-/Spitzentagen bucht auch ein neues Listing
        price *= 1 - launch["discount"]
        reasons.append(f"Startrabatt neues Listing ({-launch['discount']:.0%})")

    static_price = min(max(price, bands.minimum), bands.maximum)

    days_ahead = (d.day - as_of).days
    lt, mode = lead_time_factor(days_ahead, d, cfg, comp)
    if lt != 1.0:
        reasons.append(f"Vorlauf {days_ahead} T ({lt - 1:+.0%}, Modus {mode})")

    pace = 1.0
    if pace_ratio is not None:
        occ = cfg["occupancy"]
        pace = occ["ahead_of_pace"] if pace_ratio > 1.1 else occ["behind_pace"] if pace_ratio < 0.9 else 1.0
        pace = min(max(pace, 1 - occ["max_pace_adjustment"]), 1 + occ["max_pace_adjustment"])
        if pace != 1.0:
            reasons.append(f"Buchungs-Pace {pace_ratio:.2f} ({pace - 1:+.0%})")

    final = min(max(static_price * lt * pace, bands.minimum), bands.maximum)
    if final == bands.minimum and static_price * lt * pace < bands.minimum:
        reasons.append("auf Minimum Price begrenzt")
    if final == bands.maximum:
        reasons.append("auf Maximum Price begrenzt")
    rounded = round_price(final, cfg["output"].get("round_to_nine", False), floor=bands.minimum)
    return DayPrice(
        d, bands.base, static_price, rounded, lt, mode, pace, comp_median,
        min_nights_for(d, cfg), _band_label(final, bands), reasons,
    )


def apply_night_cap(prices: list[DayPrice], cfg: dict) -> dict[int, int] | None:
    """Bei 90-Nächte-Limit (pro Kalenderjahr): Nächte nach Wert priorisieren.

    Je Kalenderjahr werden die wertvollsten Nächte freigegeben, bis
    (Limit - bereits genutzte Nächte) / Sell-Through erreicht ist. Der niedrigste
    freigegebene statische Preis ist der Schattenpreis: Zurückgehaltene Nächte werden
    (optional) nicht darunter angeboten, weil jede verkaufte Nacht das Kontingent verbraucht.
    Liefert je Jahr den Schattenpreis oder None ohne Limit.
    """
    reg = cfg["regulation"]
    cap = reg.get("annual_night_cap", 0)
    if not cap:
        return None
    to_nine = cfg["output"].get("round_to_nine", False)
    used = {int(k): v for k, v in reg.get("nights_already_used", {}).items()}
    for p in prices:
        if p.quota_recommendation == "gebucht":
            used[p.demand.day.year] = used.get(p.demand.day.year, 0) + 1
    windows = [(date.fromisoformat(a), date.fromisoformat(b)) for a, b in reg.get("rental_windows", [])]
    rentable = []
    for p in prices:
        if p.quota_recommendation in ("gebucht", "blockiert"):
            continue
        if windows and not any(a <= p.demand.day <= b for a, b in windows):
            p.quota_priority = None
            p.quota_recommendation = "geschlossen"
        else:
            rentable.append(p)
    shadow: dict[int, int] = {}
    for year in sorted({p.demand.day.year for p in rentable}):
        year_prices = [p for p in rentable if p.demand.day.year == year]
        open_n = max(0, math.ceil((cap - used.get(year, 0)) / reg["assumed_sell_through"]))
        ranked = sorted(year_prices, key=lambda p: (p.static_price, p.demand.index), reverse=True)
        for rank, p in enumerate(ranked, start=1):
            p.quota_priority = rank
            p.quota_recommendation = "freigeben" if rank <= open_n else "zurückhalten"
        if open_n >= len(ranked) or not ranked:
            continue
        floor = round_price(ranked[open_n - 1].static_price, to_nine) if open_n else round_price(ranked[0].static_price, to_nine)
        shadow[year] = floor
        if reg.get("floor_held_nights_at_shadow_price", True):
            for p in ranked[open_n:]:
                if p.recommended < floor:
                    p.recommended = floor
                    p.reasons.append(f"90-Nächte-Limit: nicht unter Schattenpreis {floor} EUR verkaufen")
    return shadow


def german_weekday(day: date) -> str:
    return WEEKDAYS_DE[day.weekday()]
