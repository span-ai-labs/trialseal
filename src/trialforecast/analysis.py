"""The registered comparison: a forecaster against a reference, on first forecasts."""
from __future__ import annotations

import datetime as dt
from typing import Iterable

from trialforecast import scoring
from trialforecast.adjudication import WITH_READOUT, AdjudicationLog, awaiting_result, results
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
    batches: Iterable[Batch], log: AdjudicationLog, forecaster: str, reference: str, analysis_date: dt.date
) -> dict:
    """Brier scores of a forecaster and a reference on the primary analysis set, as of the analysis date.

    A trial is scored when its adjudicated result is positive or negative, it is
    industry-led, and both forecasters' first forecasts were issued before its readout.
    A first forecast issued on or after the readout means screening missed that readout;
    such trials are reported and left out, as are trials whose adjudication is not yet settled.
    Where the forecaster's first forecast records that none was produced, the trial is scored
    at the reference's probability and reported.
    """
    batches = in_date_order(batches)
    forecaster_first = first_forecasts(batches, forecaster)
    reference_first = first_forecasts(batches, reference)
    sponsor_type: dict[str, str | None] = {}
    for batch in batches:
        for trial in batch.trials:
            sponsor_type.setdefault(trial.nct, trial.sponsor_type)

    scored, not_before_readout, no_forecast = [], [], []
    adjudicated = results(log, analysis_date)
    for nct in sorted(adjudicated):
        result = adjudicated[nct]
        if result.outcome not in WITH_READOUT or sponsor_type.get(nct) != PRIMARY_ANALYSIS_SET:
            continue
        if nct not in forecaster_first or nct not in reference_first:
            continue
        if reference_first[nct].no_forecast:
            continue
        if forecaster_first[nct].no_forecast:
            no_forecast.append(nct)  # scored below at the reference's probability (ADR-0013)
        if max(forecaster_first[nct].batch_date, reference_first[nct].batch_date) >= result.readout_date:
            not_before_readout.append(nct)
            continue
        scored.append(nct)

    positive = [1.0 if adjudicated[nct].outcome == "positive" else 0.0 for nct in scored]
    reference_said = [reference_first[nct].probability_positive for nct in scored]
    # Where the forecaster produced no forecast it is scored as if it had given the reference's,
    # so that declining to forecast a hard trial can never improve its score.
    forecaster_said = [
        theirs if forecaster_first[nct].no_forecast else forecaster_first[nct].probability_positive
        for nct, theirs in zip(scored, reference_said)
    ]
    return {
        "n_trials": len(scored),
        "brier": {
            name: scoring.brier(said, positive) if scored else None
            for name, said in ((forecaster, forecaster_said), (reference, reference_said))
        },
        "forecast_not_before_readout": not_before_readout,
        "no_forecast": no_forecast,
        "awaiting_adjudication": {
            nct: reason for nct, reason in sorted(awaiting_result(log, analysis_date).items()) if nct in sponsor_type
        },
    }
