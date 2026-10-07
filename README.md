# trialforecast

Sealed forecasting of randomised phase 3 oncology trial results: for each trial,
forecast before readout the probability the primary endpoint is met and the hazard
ratio, lock the forecast with a public time-stamp, and score it when the result is
announced.

Vocabulary is in `CONTEXT.md`, decisions in `docs/adr/`, the spec and tickets in `.scratch/trialseal-study/`. Background research: `../reports/Oncology trial forecasting prebuild research.md`.

## Layout

- `scripts/snapshot_universe.py` — pull a time-stamped superset of candidate trials from the ClinicalTrials.gov API into `snapshots/<dataTimestamp>/`.
- `src/trialforecast/universe.py` — flatten a snapshot into candidates (time-to-event primary endpoint, not withdrawn), each with its scored endpoint, reference class, alias record and any exclusion-review tag; writes `data/universe/`.
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

Built: snapshot, candidate universe with reference classes and aliases, scoring harness. Not built yet: readout detection,
outcome adjudication log, baselines, forecast elicitation, sealing. Nothing has been
registered or sealed.
