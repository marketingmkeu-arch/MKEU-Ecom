"""Umsatz- und Auszahlungsprognose unter 90-Nächte-Limit und Vermietungsfenstern.

Alle Wahrscheinlichkeiten sind ANNAHMEN (config [revenue]); die Prognose ist eine
Erwartungswert-Rechnung, keine Zusage. Sie wird mit jeder echten Buchung überprüfbar.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .pricing_engine import DayPrice, round_price


def airbnb_nightly_price(p: DayPrice, cfg: dict) -> int:
    """In Airbnb einzutragender Nachtpreis: Gastpreis minus anteilige Reinigungspauschale."""
    fees = cfg.get("fees", {})
    cleaning = fees.get("cleaning_fee", 0)
    stay = max(p.min_nights, fees.get("assumed_avg_stay_nights", 2.5))
    return round_price(p.recommended - cleaning / stay, cfg["output"].get("round_to_nine", False))


@dataclass
class MonthForecast:
    nights: float = 0.0
    gross: float = 0.0


@dataclass
class Forecast:
    scenario: str
    multiplier: float
    by_month: dict[str, MonthForecast] = field(default_factory=dict)
    nights_by_year: dict[int, float] = field(default_factory=dict)
    cap_binding: dict[int, bool] = field(default_factory=dict)

    @property
    def nights(self) -> float:
        return sum(m.nights for m in self.by_month.values())

    @property
    def gross(self) -> float:
        return sum(m.gross for m in self.by_month.values())


def forecast(prices: list[DayPrice], cfg: dict, scenario: str, multiplier: float, include=None) -> Forecast:
    """include: optionale Auswahl der Nächte (Standard: alle nicht geschlossenen)."""
    probs = cfg["revenue"]["booking_probability"]
    reg = cfg["regulation"]
    cap = reg.get("annual_night_cap", 0)
    used = {int(k): v for k, v in reg.get("nights_already_used", {}).items()}
    for p in prices:
        if p.quota_recommendation == "gebucht":
            used[p.demand.day.year] = used.get(p.demand.day.year, 0) + 1
    result = Forecast(scenario, multiplier)
    by_year: dict[int, list[tuple[DayPrice, float]]] = defaultdict(list)
    for p in prices:
        if p.quota_recommendation in ("gebucht", "blockiert"):
            continue
        if (include is not None and not include(p)) or (include is None and p.quota_recommendation == "geschlossen"):
            continue
        by_year[p.demand.day.year].append((p, min(0.95, probs[p.demand.level] * multiplier)))
    months: dict[str, MonthForecast] = defaultdict(MonthForecast)
    for year, items in sorted(by_year.items()):
        remaining = max(0.0, cap - used.get(year, 0)) if cap else float("inf")
        expected = sum(q for _, q in items)
        result.cap_binding[year] = expected > remaining
        # Bei bindendem Limit werden die wertvollsten Nächte zuerst verkauft (Preis absteigend)
        taken = 0.0
        for p, q in sorted(items, key=lambda x: x[0].static_price, reverse=True):
            if taken >= remaining:
                break
            q = min(q, remaining - taken)
            taken += q
            m = months[p.demand.day.strftime("%Y-%m")]
            m.nights += q
            m.gross += q * p.static_price
        result.nights_by_year[year] = taken
    result.by_month = dict(sorted(months.items()))
    return result


def all_forecasts(prices: list[DayPrice], cfg: dict) -> list[Forecast]:
    return [forecast(prices, cfg, name, mult) for name, mult in cfg["revenue"]["scenarios"].items()]


def payout(gross: float, cfg: dict) -> float:
    return gross * cfg.get("fees", {}).get("payout_ratio", 1.0)


def compare_windows(prices: list[DayPrice], cfg: dict, windows: dict[str, tuple]) -> dict[str, Forecast]:
    """Realistisches Szenario für alternative Vermietungsfenster (z. B. 2027: Sommer vs. Frühjahr)."""
    mult = cfg["revenue"]["scenarios"].get("realistisch", 1.0)
    return {
        name: forecast(prices, cfg, name, mult, include=lambda p, a=a, b=b: a <= p.demand.day <= b)
        for name, (a, b) in windows.items()
    }
