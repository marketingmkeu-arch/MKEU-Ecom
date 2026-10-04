"""Nachfrageindex je Nacht (1.0 = normaler Dienstag ohne Event in einem Durchschnittsmonat).

D = Saison × Wochentag × (1 + Feiertag + Schulferien) × (1 + Event-Uplift)

Die Komponenten bleiben einzeln erhalten, damit jede Preisempfehlung erklärbar ist.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .calendar_data import SchoolHoliday, holidays_between, long_weekend_nights, school_holiday_on
from .event_calendar import WEEKDAY_KEYS, Event, EventEffect, event_effects
from .historical_data import MONTH_KEYS

LEVELS = ["niedrig", "normal", "erhöht", "hoch", "Spitze"]


@dataclass
class DayDemand:
    day: date
    season: float
    weekday: float
    holiday_adj: float
    holiday_label: str
    school_holiday: str | None
    event: EventEffect
    index: float
    level: str

    @property
    def level_rank(self) -> int:
        return LEVELS.index(self.level)


def demand_level(index: float, thresholds: dict) -> str:
    if index < thresholds["low"]:
        return LEVELS[0]
    if index < thresholds["normal"]:
        return LEVELS[1]
    if index < thresholds["elevated"]:
        return LEVELS[2]
    if index < thresholds["high"]:
        return LEVELS[3]
    return LEVELS[4]


def build_demand(start: date, days: int, cfg: dict, events: list[Event], school: list[SchoolHoliday]) -> list[DayDemand]:
    end = start + timedelta(days=days - 1)
    holidays = holidays_between(start, end)
    long_weekends = long_weekend_nights(holidays)
    effects = event_effects(events, cfg["events"])
    hcfg = cfg["holiday"]
    neutral_tiers = set(cfg["events"]["neutralize_weekday_for_tiers"])

    result: list[DayDemand] = []
    for i in range(days):
        day = start + timedelta(days=i)
        season = cfg["season"][MONTH_KEYS[day.month - 1]]
        effect = effects.get(day, EventEffect())
        weekday = cfg["weekday"][WEEKDAY_KEYS[day.weekday()]]
        if effect.max_tier in neutral_tiers and weekday < 1.0:
            weekday = 1.0

        adj, labels = 0.0, []
        tomorrow = day + timedelta(days=1)
        if (day.month, day.day) in ((12, 24), (12, 25)):
            adj += hcfg["christmas_low"]
            labels.append("Weihnachten (schwach)")
        elif day in long_weekends:
            adj += hcfg["long_weekend"]
            labels.append(long_weekends[day])
        elif tomorrow in holidays:
            adj += hcfg["eve_of_holiday"]
            labels.append(f"Vorabend {holidays[tomorrow]}")
        if day in holidays and not labels:
            labels.append(holidays[day])
        school_name = school_holiday_on(day, school)
        if school_name:
            adj += hcfg["school_holiday_nrw"]

        index = season * weekday * (1 + adj) * (1 + effect.uplift)
        result.append(
            DayDemand(day, season, weekday, adj, "; ".join(labels), school_name, effect,
                      round(index, 4), demand_level(index, cfg["demand_levels"]))
        )
    return result
