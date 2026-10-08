"""Forecasts and the contract every forecaster meets."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from trialforecast.records import require_plain_date

Candidate = Mapping[str, Any]

# A forecaster's name is also a file name in the batch directory.
FORECASTER_NAME = re.compile(r"[a-z0-9][a-z0-9_]*")


@dataclass(frozen=True)
class Forecast:
    """One forecaster's forecast for one trial in one batch.

    The hazard ratio is for the trial's scored endpoint: a median with an 80% interval.
    """

    nct: str
    forecaster: str
    version: str
    batch_date: dt.date
    probability_positive: float
    hazard_ratio: float
    hazard_ratio_low: float
    hazard_ratio_high: float

    def __post_init__(self) -> None:
        if not FORECASTER_NAME.fullmatch(self.forecaster):
            raise ValueError(f"forecaster name {self.forecaster!r} must be lower-case letters, digits and underscores")
        require_plain_date(self.batch_date, f"{self.nct}: batch date")
        # Stored as floats so that equal forecasts have identical canonical lines.
        for name in ("probability_positive", "hazard_ratio", "hazard_ratio_low", "hazard_ratio_high"):
            object.__setattr__(self, name, float(getattr(self, name)))
        if not 0.0 <= self.probability_positive <= 1.0:
            raise ValueError(f"{self.nct}: probability {self.probability_positive} is outside 0..1")
        if not 0.0 < self.hazard_ratio_low <= self.hazard_ratio <= self.hazard_ratio_high:
            raise ValueError(
                f"{self.nct}: hazard ratio interval {self.hazard_ratio_low}..{self.hazard_ratio}.."
                f"{self.hazard_ratio_high} is not positive and ordered"
            )


class Forecaster(Protocol):
    """Anything that issues forecasts: a fixed rule, a model, or a system built on models."""

    name: str
    version: str

    def forecast(self, candidate: Candidate, batch_date: dt.date) -> Forecast: ...


class BaseRateForecaster:
    """Forecasts every trial at the base rate and typical hazard ratio of its reference class."""

    name = "base_rate"

    def __init__(
        self,
        base_rates: Mapping[str, float],
        hazard_ratios: Mapping[str, tuple[float, float, float]],
        version: str,
    ) -> None:
        self._base_rates = base_rates
        self._hazard_ratios = hazard_ratios  # median, low, high of the 80% interval
        self.version = version

    def forecast(self, candidate: Candidate, batch_date: dt.date) -> Forecast:
        reference_class = candidate["reference_class"]
        for what, table in (("base rate", self._base_rates), ("hazard ratio", self._hazard_ratios)):
            if reference_class not in table:
                raise LookupError(f"{candidate['nct']}: no {what} for reference class {reference_class}")
        median, low, high = self._hazard_ratios[reference_class]
        return Forecast(
            nct=candidate["nct"], forecaster=self.name, version=self.version, batch_date=batch_date,
            probability_positive=self._base_rates[reference_class],
            hazard_ratio=median, hazard_ratio_low=low, hazard_ratio_high=high,
        )
