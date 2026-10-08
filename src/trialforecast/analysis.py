"""The registered comparison: a forecaster against a reference, on first forecasts."""
from __future__ import annotations

from typing import Iterable

from trialforecast import scoring
from trialforecast.adjudication import WITH_READOUT, Adjudication, agreed_outcomes
from trialforecast.batch import Batch
from trialforecast.forecasting import Forecast

PRIMARY_ANALYSIS_SET = "industry"  # sponsor type; see ADR-0003


def in_date_order(batches: Iterable[Batch]) -> list[Batch]:
    """Batches from earliest to latest. Two on one date would leave the first forecast undefined."""
    ordered = sorted(batches, key=lambda b: b.batch_date)
    for earlier, later in zip(ordered, ordered[1:]):
        if earlier.batch_date == later.batch_date:
            raise ValueError(f"two batches are dated {later.batch_date}")
    return ordered


def first_forecasts(batches: Iterable[Batch], forecaster: str) -> dict[str, Forecast]:
    """Each trial's first forecast from one forecaster; later batches never replace it."""
    first: dict[str, Forecast] = {}
    for batch in in_date_order(batches):
        for forecast in batch.forecasts.get(forecaster, ()):
            first.setdefault(forecast.nct, forecast)
    return first


def primary_comparison(
    batches: Iterable[Batch], adjudications: Iterable[Adjudication], forecaster: str, reference: str
) -> dict:
    """Brier scores of a forecaster and a reference on the primary analysis set.

    A trial is scored when two adjudicators agree it was positive or negative, it is
    industry-led, and both forecasters' first forecasts were issued before its readout.
    A first forecast issued on or after the readout means screening missed that readout;
    such trials are reported and left out.
    """
    batches = in_date_order(batches)
    forecaster_first = first_forecasts(batches, forecaster)
    reference_first = first_forecasts(batches, reference)
    sponsor_type: dict[str, str | None] = {}
    for batch in batches:
        for trial in batch.trials:
            sponsor_type.setdefault(trial.nct, trial.sponsor_type)

    scored, not_before_readout = [], []
    agreed = agreed_outcomes(adjudications)
    for nct in sorted(agreed):
        outcome, readout_date = agreed[nct]
        if outcome not in WITH_READOUT or sponsor_type.get(nct) != PRIMARY_ANALYSIS_SET:
            continue
        if nct not in forecaster_first or nct not in reference_first:
            continue
        if max(forecaster_first[nct].batch_date, reference_first[nct].batch_date) >= readout_date:
            not_before_readout.append(nct)
            continue
        scored.append(nct)

    positive = [1.0 if agreed[nct].outcome == "positive" else 0.0 for nct in scored]
    return {
        "n_trials": len(scored),
        "brier": {
            name: scoring.brier([first[nct].probability_positive for nct in scored], positive) if scored else None
            for name, first in ((forecaster, forecaster_first), (reference, reference_first))
        },
        "forecast_not_before_readout": not_before_readout,
    }
