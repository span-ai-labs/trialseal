"""Batches: every forecaster's forecast for every eligible trial on one date, with one fingerprint."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
from dataclasses import dataclass
from typing import Iterable

from trialforecast import records
from trialforecast.forecasting import Candidate, Forecast, Forecaster
from trialforecast.screening import ScreeningRecord, eligible_on

TRIALS_FILE = "_trials.jsonl"  # cannot collide with a forecaster's file: names never start with an underscore


class IneligibleTrial(Exception):
    """A batch was asked to include a trial that screening has not cleared."""


class InvalidForecast(Exception):
    """A forecaster returned something other than its own forecast for the trial and batch asked."""


class TamperedBatch(Exception):
    """A batch on disk no longer matches the fingerprint recorded when it was written."""


@dataclass(frozen=True)
class BatchTrial:
    """What is fixed about a trial when it enters a batch: its scored endpoint and reference class."""

    nct: str
    scored_endpoint: str
    sponsor_type: str | None
    endpoint_type: str


@dataclass(frozen=True)
class Batch:
    batch_date: dt.date
    trials: tuple[BatchTrial, ...]
    forecasts: dict[str, tuple[Forecast, ...]]  # by forecaster name, each ordered by trial

    @property
    def fingerprint(self) -> str:
        """One SHA-256 over the batch date, the trials and every forecaster's record set."""
        digest = hashlib.sha256(self.batch_date.isoformat().encode())
        digest.update(_digest(self.trials))
        for name in sorted(self.forecasts):
            digest.update(f"\n{name}\n".encode())
            digest.update(_digest(self.forecasts[name]))
        return digest.hexdigest()


def record_set(batch_records: Iterable[BatchTrial | Forecast]) -> bytes:
    """The canonical bytes of a batch's trials or of one forecaster's forecasts: one JSON line each, in trial order."""
    lines = [records.to_line(record) for record in sorted(batch_records, key=lambda r: r.nct)]
    return ("\n".join(lines) + "\n").encode()


def _digest(batch_records: Iterable[BatchTrial | Forecast]) -> bytes:
    return hashlib.sha256(record_set(batch_records)).hexdigest().encode()


def _text_or_none(value: object) -> str | None:
    # A candidate read from a table carries NaN where the registry had nothing.
    return value if isinstance(value, str) else None


def build_batch(
    batch_date: dt.date,
    trials: Iterable[Candidate],
    screening: Iterable[ScreeningRecord],
    forecasters: Iterable[Forecaster],
) -> Batch:
    """Issue every forecaster's forecast for every trial.

    Refuses any trial screening has not cleared for this date, and any forecast
    that is not the forecaster's own for the trial and batch asked.
    """
    trials = sorted(trials, key=lambda c: c["nct"])
    forecasters = list(forecasters)
    names = [f.name for f in forecasters]
    repeated = sorted({n for n in names if names.count(n) > 1})
    if repeated:
        raise ValueError(f"forecaster names must be unique; repeated: {', '.join(repeated)}")

    cleared = eligible_on(batch_date, screening)
    refused = [c["nct"] for c in trials if c["nct"] not in cleared]
    if refused:
        raise IneligibleTrial(f"not screened as eligible for {batch_date}: {', '.join(refused)}")

    forecasts: dict[str, tuple[Forecast, ...]] = {}
    for forecaster in forecasters:
        issued = []
        for trial in trials:
            forecast = forecaster.forecast(trial, batch_date)
            asked = (trial["nct"], forecaster.name, forecaster.version, batch_date)
            if (forecast.nct, forecast.forecaster, forecast.version, forecast.batch_date) != asked:
                raise InvalidForecast(f"{forecaster.name} was asked for {asked} and returned {forecast}")
            issued.append(forecast)
        forecasts[forecaster.name] = tuple(issued)

    batch_trials = tuple(
        BatchTrial(nct=c["nct"], scored_endpoint=c["scored_endpoint"],
                   sponsor_type=_text_or_none(c["sponsor_type"]), endpoint_type=c["endpoint_type"])
        for c in trials
    )
    return Batch(batch_date=batch_date, trials=batch_trials, forecasts=forecasts)


def write_batch(batch: Batch, root: pathlib.Path) -> pathlib.Path:
    """Write the trials, one record set per forecaster, and a manifest carrying the fingerprint."""
    directory = root / batch.batch_date.isoformat()
    directory.mkdir(parents=True)
    (directory / TRIALS_FILE).write_bytes(record_set(batch.trials))
    for name, forecasts in batch.forecasts.items():
        (directory / f"{name}.jsonl").write_bytes(record_set(forecasts))
    manifest = {
        "batch_date": batch.batch_date.isoformat(),
        "fingerprint": batch.fingerprint,
        "forecasters": sorted(batch.forecasts),
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return directory


def read_batch(directory: pathlib.Path) -> Batch:
    """Read a batch back, refusing it if its contents no longer match the recorded fingerprint."""
    manifest = json.loads((directory / "manifest.json").read_text())
    batch = Batch(
        batch_date=dt.date.fromisoformat(manifest["batch_date"]),
        trials=tuple(records.read(directory / TRIALS_FILE, BatchTrial)),
        forecasts={
            name: tuple(records.read(directory / f"{name}.jsonl", Forecast)) for name in manifest["forecasters"]
        },
    )
    if batch.fingerprint != manifest["fingerprint"]:
        raise TamperedBatch(f"{directory}: contents do not match the fingerprint in the manifest")
    return batch
