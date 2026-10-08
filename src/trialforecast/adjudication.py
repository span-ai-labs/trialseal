"""Adjudication: two people independently deciding what a trial's readout showed."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, NamedTuple

from trialforecast.records import require_plain_date

OUTCOMES = ("positive", "negative", "void")
WITH_READOUT = ("positive", "negative")  # a void trial has no readout


@dataclass(frozen=True)
class Adjudication:
    nct: str
    adjudicator: str
    outcome: str
    readout_date: dt.date | None
    source: str
    hazard_ratio: float | None = None

    def __post_init__(self) -> None:
        # "Abhijoy" and "abhijoy " are one adjudicator, and must not count as two.
        object.__setattr__(self, "adjudicator", self.adjudicator.strip().casefold())
        if not self.adjudicator:
            raise ValueError(f"{self.nct}: an adjudication must name its adjudicator")
        if self.outcome not in OUTCOMES:
            raise ValueError(f"{self.nct}: outcome must be one of {OUTCOMES}, not {self.outcome!r}")
        if self.outcome in WITH_READOUT:
            require_plain_date(self.readout_date, f"{self.nct}: readout date")
        elif self.readout_date is not None:
            raise ValueError(f"{self.nct}: a void trial has no readout date")


class AgreedOutcome(NamedTuple):
    outcome: str
    readout_date: dt.date | None


def agreed_outcomes(adjudications: Iterable[Adjudication]) -> dict[str, AgreedOutcome]:
    """Each trial's outcome, for trials where at least two adjudicators recorded the same one.

    The readout date is the earliest the agreeing adjudicators recorded.
    """
    by_trial: dict[str, dict[str, Adjudication]] = {}
    for adjudication in adjudications:
        by_trial.setdefault(adjudication.nct, {})[adjudication.adjudicator] = adjudication
    agreed = {}
    for nct, by_adjudicator in by_trial.items():
        outcomes = {a.outcome for a in by_adjudicator.values()}
        if len(by_adjudicator) >= 2 and len(outcomes) == 1:
            dates = [a.readout_date for a in by_adjudicator.values() if a.readout_date is not None]
            agreed[nct] = AgreedOutcome(outcomes.pop(), min(dates) if dates else None)
    return agreed
