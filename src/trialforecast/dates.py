"""Calendar arithmetic shared by the study's rules."""
from __future__ import annotations

import datetime as dt


def add_months(d: dt.date, months: int) -> dt.date:
    """The same day of the month some months away, or that month's last day if it is shorter."""
    y, m = divmod(d.year * 12 + d.month - 1 + months, 12)
    last = [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m]
    return dt.date(y, m + 1, min(d.day, last))
