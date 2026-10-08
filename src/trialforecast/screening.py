"""Screening: checking each candidate for an existing public primary result before a batch."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable

from trialforecast.forecasting import Candidate
from trialforecast.records import require_plain_date

DECISIONS = ("eligible", "already_read_out")

# A screening older than this may have been overtaken by a readout.
SCREENING_VALID_DAYS = 14


@dataclass(frozen=True)
class ScreeningRecord:
    nct: str
    decision: str
    screened_on: dt.date
    evidence: str

    def __post_init__(self) -> None:
        if self.decision not in DECISIONS:
            raise ValueError(f"{self.nct}: screening decision must be one of {DECISIONS}, not {self.decision!r}")
        if not self.evidence.strip():
            raise ValueError(f"{self.nct}: a screening decision needs its evidence")
        require_plain_date(self.screened_on, f"{self.nct}: screening date")


def eligible_on(batch_date: dt.date, log: Iterable[ScreeningRecord]) -> set[str]:
    """Trials cleared for a batch on this date.

    A trial is cleared by a recent screening that found no public primary result,
    dated on or before the batch. A trial ever recorded as read out is never cleared.
    """
    log = list(log)
    read_out = {r.nct for r in log if r.decision == "already_read_out"}
    cleared = {
        r.nct for r in log
        if r.decision == "eligible" and 0 <= (batch_date - r.screened_on).days <= SCREENING_VALID_DAYS
    }
    return cleared - read_out


def eligible_trials(
    candidates: Iterable[Candidate], log: Iterable[ScreeningRecord], batch_date: dt.date
) -> list[Candidate]:
    """The candidates that are eligible trials for a batch on this date. Unscreened candidates are not."""
    cleared = eligible_on(batch_date, log)
    return [c for c in candidates if c["nct"] in cleared]
