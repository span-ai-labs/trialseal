# trialforecast

Sealed forecasting of randomised phase 3 oncology trial results: for each trial,
forecast before readout the probability the primary endpoint is met and the hazard
ratio, lock the forecast with a public time-stamp, and score it when the result is
announced.

Background and design decisions: `../reports/Oncology trial forecasting prebuild research.md`.

## Layout

- `scripts/snapshot_universe.py` — pull a time-stamped superset of candidate trials from the ClinicalTrials.gov API into `snapshots/<dataTimestamp>/`.
- `src/trialforecast/universe.py` — flatten a snapshot and apply the refined filter (time-to-event primary endpoint, not withdrawn); writes `data/universe/`.
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

Built: snapshot, universe filter, scoring harness. Not built yet: readout detection,
outcome adjudication log, baselines, forecast elicitation, sealing. Nothing has been
registered or sealed.
