from datetime import date

from dynpricing.config import Paths, load_config
from dynpricing.event_calendar import Event, event_effects, load_events


def _event(start, end, tier="A", **kw):
    return Event("e", "E", "trade_fair", "Messe", "Düsseldorf", 51.26, 6.74, start, end, tier, **kw)


def test_night_weights_for_trade_fair():
    w = _event(date(2026, 11, 16), date(2026, 11, 19)).night_weights(0.8, 0.3)
    assert w == {
        date(2026, 11, 15): 0.8,
        date(2026, 11, 16): 1.0,
        date(2026, 11, 17): 1.0,
        date(2026, 11, 18): 1.0,
        date(2026, 11, 19): 0.3,
    }


def test_single_day_concert_affects_only_event_night():
    w = _event(date(2027, 7, 3), date(2027, 7, 3), pre_night_weight=0.0, last_night_weight=1.0).night_weights(0.8, 0.3)
    assert w == {date(2027, 7, 3): 1.0}


def test_weekday_filter():
    w = _event(date(2026, 11, 19), date(2026, 11, 29), applies_to=("fri", "sat")).night_weights(0.0, 1.0)
    assert all(d.weekday() in (4, 5) for d in w)


def test_overlapping_events_are_dampened():
    cfg = load_config()["events"]
    a = _event(date(2027, 3, 7), date(2027, 3, 9), "A")
    b = _event(date(2027, 3, 7), date(2027, 3, 9), "C")
    eff = event_effects([a, b], cfg)[date(2027, 3, 7)]
    expected = cfg["tier_uplift"]["A"] + cfg["overlap_decay"] * cfg["tier_uplift"]["C"]
    assert abs(eff.uplift - expected) < 1e-9
    assert eff.max_tier == "A"


def test_event_csv_is_valid():
    events = load_events(Paths().raw / "events" / "events.csv")
    assert events
    for e in events:
        assert e.start <= e.end
        assert e.impact_tier in "SABCD"
        assert e.confidence in ("high", "medium", "low")
