"""Forecasts and the contract every forecaster meets."""
from __future__ import annotations

import datetime as dt
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from trialforecast.records import require_plain_date, require_trial_id

Candidate = Mapping[str, Any]

# A forecaster's name is also a file name in the batch directory.
FORECASTER_NAME = re.compile(r"[a-z0-9][a-z0-9_]*")


def valid_numbers(probability: float, hazard_ratio: float, low: float, high: float) -> bool:
    """Whether four numbers form a forecast: a probability, and a positive, ordered, finite interval."""
    return (
        all(math.isfinite(x) for x in (probability, hazard_ratio, low, high))
        and 0.0 <= probability <= 1.0
        and 0.0 < low <= hazard_ratio <= high
    )


@dataclass(frozen=True)
class Forecast:
    """One forecaster's forecast for one trial in one batch, or the record that it produced none.

    The hazard ratio is for the trial's scored endpoint: a median with an 80% interval.
    A forecaster built on a model also records which model, what its provider states
    about it, when it was used, the raw text of every reply, and what the replies cost.
    """

    nct: str
    forecaster: str
    version: str
    batch_date: dt.date
    probability_positive: float | None
    hazard_ratio: float | None
    hazard_ratio_low: float | None
    hazard_ratio_high: float | None
    no_forecast: str | None = None  # why there is none; the four numbers are then all absent
    model: str | None = None  # the model asked for
    model_served: str | None = None  # the model the provider says answered
    model_training_cutoff: str | None = None  # as the provider states it
    model_released_on: dt.date | None = None
    used_on: dt.date | None = None
    replies: tuple[str, ...] = ()
    provider_failures: int | None = None  # attempts lost to outages at the provider
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        if not FORECASTER_NAME.fullmatch(self.forecaster):
            raise ValueError(f"forecaster name {self.forecaster!r} must be lower-case letters, digits and underscores")
        require_plain_date(self.batch_date, f"{self.nct}: batch date")
        for label, day in (("release date", self.model_released_on), ("date of use", self.used_on)):
            if day is not None:
                require_plain_date(day, f"{self.nct}: model {label}")
        object.__setattr__(self, "replies", tuple(self.replies))
        numbers = ("probability_positive", "hazard_ratio", "hazard_ratio_low", "hazard_ratio_high")
        if self.no_forecast is not None:
            if not self.no_forecast.strip() or any(getattr(self, name) is not None for name in numbers):
                raise ValueError(f"{self.nct}: a record of no forecast gives its reason and no numbers")
            return
        if any(getattr(self, name) is None for name in numbers):
            raise ValueError(f"{self.nct}: a forecast needs all four numbers, or a reason there is none")
        # Stored as floats so that equal forecasts have identical canonical lines.
        for name in numbers:
            object.__setattr__(self, name, float(getattr(self, name)))
        if not valid_numbers(*(getattr(self, name) for name in numbers)):
            raise ValueError(
                f"{self.nct}: probability {self.probability_positive} with hazard ratio {self.hazard_ratio_low}.."
                f"{self.hazard_ratio}..{self.hazard_ratio_high} is not a probability with a positive, ordered interval"
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
