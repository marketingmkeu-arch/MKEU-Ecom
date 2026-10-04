"""Feiertage (NRW), Schulferien und lange Wochenenden."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


def easter_sunday(year: int) -> date:
    """Gaußsche Osterformel (anonymer gregorianischer Algorithmus)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def nrw_public_holidays(year: int) -> dict[date, str]:
    """Gesetzliche Feiertage in Nordrhein-Westfalen."""
    easter = easter_sunday(year)
    return {
        date(year, 1, 1): "Neujahr",
        easter - timedelta(days=2): "Karfreitag",
        easter + timedelta(days=1): "Ostermontag",
        date(year, 5, 1): "Tag der Arbeit",
        easter + timedelta(days=39): "Christi Himmelfahrt",
        easter + timedelta(days=50): "Pfingstmontag",
        easter + timedelta(days=60): "Fronleichnam",
        date(year, 10, 3): "Tag der Deutschen Einheit",
        date(year, 11, 1): "Allerheiligen",
        date(year, 12, 25): "1. Weihnachtstag",
        date(year, 12, 26): "2. Weihnachtstag",
    }


def holidays_between(start: date, end: date) -> dict[date, str]:
    result: dict[date, str] = {}
    for year in range(start.year, end.year + 2):
        result.update(nrw_public_holidays(year))
    return {d: n for d, n in result.items() if start - timedelta(days=7) <= d <= end + timedelta(days=7)}


@dataclass(frozen=True)
class SchoolHoliday:
    name: str
    start: date
    end: date


def load_school_holidays(path: Path) -> list[SchoolHoliday]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            SchoolHoliday(r["name"], date.fromisoformat(r["start_date"]), date.fromisoformat(r["end_date"]))
            for r in csv.DictReader(fh)
        ]


def school_holiday_on(day: date, holidays: list[SchoolHoliday]) -> str | None:
    for h in holidays:
        if h.start <= day <= h.end:
            return h.name
    return None


def long_weekend_nights(holidays: dict[date, str]) -> dict[date, str]:
    """Nächte eines verlängerten Wochenendes.

    Feiertag am Do -> Nächte Mi..Sa (Brückentag Fr); Feiertag am Fr -> Do..Sa;
    Feiertag am Mo -> Fr..So; Feiertag am Di -> Fr..Mo (Brückentag Mo).
    """
    nights: dict[date, str] = {}
    offsets = {3: range(-1, 3), 4: range(-1, 2), 0: range(-3, 0), 1: range(-4, 0)}
    for day, name in holidays.items():
        for off in offsets.get(day.weekday(), ()):
            nights.setdefault(day + timedelta(days=off), f"Langes Wochenende ({name})")
    return nights
