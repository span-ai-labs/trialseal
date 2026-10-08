# trialforecast

Sealed forecasting of randomised phase 3 oncology trial results: for each trial,
forecast before readout the probability the primary endpoint is met and the hazard
ratio, lock the forecast with a public time-stamp, and score it when the result is
announced.

Vocabulary is in `CONTEXT.md`, decisions in `docs/adr/`, the spec and tickets in `.scratch/trialseal-study/`. Background research: `../reports/Oncology trial forecasting prebuild research.md`.

## Layout

- `scripts/snapshot_universe.py` — pull a time-stamped superset of candidate trials from the ClinicalTrials.gov API into `snapshots/<dataTimestamp>/`.
- `src/trialforecast/universe.py` — flatten a snapshot into candidates (time-to-event primary endpoint, not withdrawn), each with its scored endpoint, reference class, alias record and any exclusion-review tag; writes `data/universe/`.
- `src/trialforecast/forecasting.py` — the forecast shape, the contract every forecaster meets, and the base-rate forecaster.
- `src/trialforecast/screening.py` — screening records and which candidates are eligible.
- `src/trialforecast/batch.py` — builds a batch (refusing any trial not screened as eligible), fingerprints it, writes and reads it.
- `src/trialforecast/adjudication.py` — adjudications and the outcomes two adjudicators agree on.
- `src/trialforecast/analysis.py` — the primary comparison, on each trial's first forecast.
- `src/trialforecast/records.py` — append-only logs, one canonical JSON line per record.
- `src/trialforecast/scoring.py` — Brier, clipped log score, Murphy decomposition, AUC, CRPS and interval score on the log hazard ratio, paired cluster bootstrap.
- `tests/` — unit tests for the above.

## Use

```bash
uv sync
uv run python scripts/snapshot_universe.py   # one snapshot per registry data timestamp
uv run trialforecast-universe                # refined universe from the latest snapshot
uv run pytest
```

## Status

Built: snapshot, candidate universe, scoring, and a walking skeleton of the record pipeline
(screening, base-rate forecaster, batch with fingerprint, two-person adjudication, primary
comparison). Not built yet: real screening, the reference set, full adjudication rules,
time-stamped sealing, the other forecasters, readout detection. Nothing has been registered
or sealed.
