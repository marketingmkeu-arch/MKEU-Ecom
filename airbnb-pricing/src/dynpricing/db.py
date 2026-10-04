"""SQLite-Ablage: Rohdaten-Spiegel und berechnete Ergebnisse (getrennte Tabellen)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .event_calendar import Event
from .market_data import MarketMetric
from .pricing_engine import DayPrice

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_events (
  event_id TEXT PRIMARY KEY, name TEXT, category TEXT, venue TEXT, city TEXT,
  start_date TEXT, end_date TEXT, expected_visitors INTEGER, impact_tier TEXT,
  distance_km REAL, source_url TEXT, source_type TEXT, confidence TEXT
);
CREATE TABLE IF NOT EXISTS raw_market_aggregates (
  provider TEXT, geography TEXT, metric TEXT, value REAL, unit TEXT, period TEXT,
  url TEXT, data_class TEXT, confidence TEXT,
  PRIMARY KEY (provider, geography, metric, period)
);
CREATE TABLE IF NOT EXISTS calc_runs (
  run_id TEXT PRIMARY KEY, created_at TEXT, as_of TEXT, base_price REAL, config_json TEXT
);
CREATE TABLE IF NOT EXISTS calc_pricing_calendar (
  run_id TEXT, stay_date TEXT, weekday TEXT, base_price REAL, recommended_price INTEGER,
  demand_index REAL, demand_level TEXT, event TEXT, event_uplift REAL, min_nights INTEGER,
  lead_time_factor REAL, band TEXT, quota_priority INTEGER, reasons TEXT,
  PRIMARY KEY (run_id, stay_date)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def store_raw(con: sqlite3.Connection, events: list[Event], metrics: list[MarketMetric], lat: float, lon: float) -> None:
    con.executemany(
        "INSERT OR REPLACE INTO raw_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (e.event_id, e.name, e.category, e.venue, e.city, e.start.isoformat(), e.end.isoformat(),
             e.expected_visitors, e.impact_tier, round(e.distance_km(lat, lon), 2), e.source_url,
             e.source_type, e.confidence)
            for e in events
        ],
    )
    con.executemany(
        "INSERT OR REPLACE INTO raw_market_aggregates VALUES (?,?,?,?,?,?,?,?,?)",
        [(m.provider, m.geography, m.metric, m.value, m.unit, m.period, m.url, m.data_class, m.confidence) for m in metrics],
    )
    con.commit()


def store_run(con: sqlite3.Connection, as_of: str, base: float, config_json: str, prices: list[DayPrice]) -> str:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    con.execute("INSERT OR REPLACE INTO calc_runs VALUES (?,?,?,?,?)",
                (run_id, datetime.now(timezone.utc).isoformat(), as_of, base, config_json))
    con.executemany(
        "INSERT OR REPLACE INTO calc_pricing_calendar VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (run_id, p.demand.day.isoformat(), p.demand.day.strftime("%a"), round(p.base, 2), p.recommended,
             p.demand.index, p.demand.level, p.demand.event.names, round(p.demand.event.uplift, 3),
             p.min_nights, p.lead_time_factor, p.band, p.quota_priority, "; ".join(p.reasons))
            for p in prices
        ],
    )
    con.commit()
    return run_id
