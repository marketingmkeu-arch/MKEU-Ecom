from datetime import date

from dynpricing.calendar_data import easter_sunday, long_weekend_nights, nrw_public_holidays


def test_easter_dates():
    assert easter_sunday(2026) == date(2026, 4, 5)
    assert easter_sunday(2027) == date(2027, 3, 28)


def test_rosenmontag_2027_matches_published_date():
    from datetime import timedelta
    assert easter_sunday(2027) - timedelta(days=48) == date(2027, 2, 8)


def test_nrw_holidays_include_fronleichnam_and_allerheiligen():
    h = nrw_public_holidays(2027)
    assert h[date(2027, 5, 27)] == "Fronleichnam"
    assert date(2027, 11, 1) in h
    assert len(h) == 11


def test_long_weekend_for_thursday_holiday():
    nights = long_weekend_nights({date(2027, 5, 6): "Christi Himmelfahrt"})
    assert set(nights) == {date(2027, 5, 5), date(2027, 5, 6), date(2027, 5, 7), date(2027, 5, 8)}
