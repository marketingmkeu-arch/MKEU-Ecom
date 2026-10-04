import math
from datetime import date

import pytest

from dynpricing.config import load_config
from dynpricing.demand_model import DayDemand
from dynpricing.event_calendar import Event, EventEffect
from dynpricing.pipeline import run
from dynpricing.pricing_engine import price_bands, price_day, round_price

AS_OF = date(2026, 10, 4)


@pytest.fixture(scope="module")
def result():
    return run(AS_OF, load_config())


def _price(result, day):
    return next(p for p in result.prices if p.demand.day == day)


def _demand(day, index, level, tier=None, uplift=0.0):
    effect = EventEffect()
    if tier:
        ev = Event("x", "X", "trade_fair", "Messe", "D", 0, 0, day, day, tier)
        effect = EventEffect(uplift, [(ev, uplift)], tier)
    return DayDemand(day, 1.0, 1.0, 0.0, "", None, effect, index, level)


def test_calendar_covers_horizon(result):
    assert len(result.prices) == 365
    assert result.prices[0].demand.day == AS_OF


def test_prices_within_bounds(result):
    for p in result.prices:
        assert result.bands.minimum <= p.recommended <= result.bands.maximum + 10


def test_weekend_above_weekday(result):
    tue = _price(result, date(2027, 3, 2))
    sat = _price(result, date(2027, 3, 13))
    assert sat.static_price > tue.static_price


def test_medica_priced_far_above_normal_tuesday(result):
    medica = _price(result, date(2026, 11, 17))
    normal = _price(result, date(2026, 11, 24))
    assert medica.static_price >= result.bands.event
    assert medica.static_price > 1.6 * normal.static_price
    assert medica.min_nights == 3


def test_strong_fair_beats_small_fair(result):
    medica = _price(result, date(2026, 11, 17)).static_price
    eurocis = _price(result, date(2027, 2, 16)).static_price
    assert medica > eurocis


def test_last_minute_discount_only_without_high_demand():
    cfg = load_config()
    bands = price_bands(120, cfg)
    day = date(2027, 3, 2)
    low = price_day(_demand(day, 0.9, "niedrig"), bands, cfg, as_of=day)
    high = price_day(_demand(day, 1.9, "Spitze", "S", cfg["events"]["tier_uplift"]["S"]), bands, cfg, as_of=day)
    assert low.lead_time_factor < 1.0
    assert high.lead_time_factor > 1.0


def test_last_minute_never_below_minimum():
    cfg = load_config()
    bands = price_bands(120, cfg)
    day = date(2027, 1, 10)
    p = price_day(_demand(day, 0.6, "niedrig"), bands, cfg, as_of=day)
    assert p.recommended >= bands.minimum


def test_night_cap_marks_priorities(result):
    open_2027 = [p for p in result.prices if p.demand.day.year == 2027 and p.quota_recommendation == "freigeben"]
    cfg = result.cfg["regulation"]
    assert len(open_2027) == math.ceil(cfg["annual_night_cap"] / cfg["assumed_sell_through"])
    medica = _price(result, date(2026, 11, 17))
    assert medica.quota_recommendation == "freigeben"


def test_base_calibrated_to_anchor(result):
    d = result.derivation
    weighted_model_adr = sum(p.demand.index ** 2 for p in result.prices) / sum(p.demand.index for p in result.prices) * d.base
    assert abs(weighted_model_adr - d.adjusted_anchor) < 0.01


def test_round_to_nine():
    assert round_price(117.98, True) == 119
    assert round_price(131, True) == 129
    assert round_price(131.4, False) == 131
    assert round_price(92, True, floor=92) == 99


def test_held_nights_not_sold_below_shadow_price(result):
    shadow = result.shadow_prices[2027]
    held = [p for p in result.prices if p.demand.day.year == 2027 and p.quota_recommendation == "zurückhalten"]
    assert held
    assert all(p.recommended >= shadow for p in held)


def test_no_shadow_price_when_quota_covers_all_nights(result):
    # Okt.–Dez. 2026: 89 Nächte im Fenster < 90 / 0,6 freigegebene Nächte
    assert 2026 not in result.shadow_prices
