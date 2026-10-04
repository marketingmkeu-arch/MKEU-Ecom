"""Tests für Comp-Set, historische Schätzung und Backtest.

Die hier verwendeten Zahlen sind SYNTHETISCHE Testdaten und keine Marktbeobachtungen.
"""

from datetime import date, timedelta

from dynpricing.competitor_analysis import CompListing, classify, comp_days
from dynpricing.event_calendar import Event
from dynpricing.historical_data import DailyObservation, estimate_event_uplift, estimate_factors
from dynpricing.validation import backtest, spearman

PROP = {"lat": 51.2125, "lon": 6.7665, "bedrooms": 1}


def _comp(lid, lat, lon, size=60, entire=True):
    return CompListing(lid, "Unterbilk", lat, lon, size, 1, 4, entire, True, True, True, 4.9, None, 2, None, None)


def test_comp_classification():
    comps = classify(
        [_comp("near", 51.2130, 6.7670), _comp("room", 51.2130, 6.7670, entire=False), _comp("far", 51.30, 6.90)],
        PROP, [0.5, 1, 2, 3, 5],
    )
    by_id = {c.listing_id: c for c in comps}
    assert by_id["near"].comp_class == "vergleichbar"
    assert by_id["near"].radius_band_km == 0.5
    assert by_id["room"].comp_class == "nicht vergleichbar"
    assert by_id["far"].comp_class == "nicht vergleichbar"


def test_comp_days_uses_latest_snapshot_and_availability():
    rows = [
        {"listing_id": "a", "snapshot_date": "2026-10-01", "stay_date": "2026-11-17", "nightly_price": "150", "available": "1"},
        {"listing_id": "a", "snapshot_date": "2026-10-03", "stay_date": "2026-11-17", "nightly_price": "", "available": "0"},
        {"listing_id": "b", "snapshot_date": "2026-10-03", "stay_date": "2026-11-17", "nightly_price": "200", "available": "1"},
    ]
    day = comp_days(rows, {"a", "b"})[date(2026, 11, 17)]
    assert day.n_listings == 2
    assert day.availability_ratio == 0.5
    assert day.median_offered == 200


def _synthetic_history(event: Event):
    start = date(2025, 1, 1)
    obs = []
    for i in range(365):
        d = start + timedelta(days=i)
        adr = 100 * (1.2 if d.weekday() in (4, 5) else 1.0)
        if event.start <= d < event.end:
            adr *= 2.0
        obs.append(DailyObservation(d, adr, 0.6, "synthetic", "test"))
    return obs


def test_event_uplift_estimation_recovers_synthetic_effect():
    ev = Event("m", "Messe", "trade_fair", "Messe", "D", 0, 0, date(2025, 11, 10), date(2025, 11, 13), "S")
    impacts = estimate_event_uplift(_synthetic_history(ev), [ev])
    assert len(impacts) == 1
    assert abs(impacts[0].uplift - 1.0) < 0.01


def test_factor_estimation_detects_weekend_premium():
    ev = Event("m", "Messe", "trade_fair", "Messe", "D", 0, 0, date(2025, 11, 10), date(2025, 11, 13), "S")
    f = estimate_factors(_synthetic_history(ev), [ev])
    assert f["weekday"]["sat"] > f["weekday"]["tue"]


def test_estimators_return_empty_without_data():
    assert estimate_factors([], []) == {}
    assert estimate_event_uplift([], []) == []


def test_backtest_flags_underpriced_event_days():
    days = [date(2025, 3, 1) + timedelta(days=i) for i in range(10)]
    market = [DailyObservation(d, 100.0 if i < 8 else 300.0, None, "synthetic", "test") for i, d in enumerate(days)]
    model = {d: 100.0 if i < 8 else 150.0 for i, d in enumerate(days)}
    bt = backtest(model, market, event_days=set(days[8:]))
    assert bt.underpriced_event_days == days[8:]
    assert bt.bias_normal_days == 0
    assert bt.overpriced_normal_days == []


def test_spearman():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
