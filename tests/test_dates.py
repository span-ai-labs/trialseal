import datetime as dt

from trialforecast.dates import add_months


def test_add_months_clamps_to_the_end_of_a_shorter_month():
    assert add_months(dt.date(2026, 10, 31), -8) == dt.date(2026, 2, 28)
    assert add_months(dt.date(2026, 10, 6), 15) == dt.date(2028, 1, 6)
    assert add_months(dt.date(2027, 8, 31), 6) == dt.date(2028, 2, 29)
