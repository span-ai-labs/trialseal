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
- `src/trialforecast/adjudication.py` — adjudications of each source, reconciliations, and the rules that turn them into a trial's result (source ranking, readout date, hazard-ratio window, blindness).
- `src/trialforecast/sealing.py` — seals a batch: one commitment per forecast, a seal with no forecast in it, anchors from two time-stamping services, publication of the seal alone, and verification of a revealed forecast.
- `src/trialforecast/anchors.py` — the two kinds of time-stamping service (an RFC 3161 authority, verified with OpenSSL, and OpenTimestamps).
- `src/trialforecast/analysis.py` — the primary comparison, on each trial's first forecast.
- `src/trialforecast/records.py` — append-only logs, one canonical JSON line per record.
- `src/trialforecast/scoring.py` — Brier, clipped log score, Murphy decomposition, AUC, CRPS and interval score on the log hazard ratio, paired cluster bootstrap.
- `tests/` — unit tests for the above.

## Use

Steps only a person can do (model keys, time-stamping choices, the public repository, the protocol registration record) are walked through by one script:

```bash
scripts/setup_wizard.sh
```

Everything else:

```bash
uv sync
uv run python scripts/snapshot_universe.py   # one snapshot per registry data timestamp
uv run trialforecast-universe                # refined universe from the latest snapshot
uv run pytest
```

## Checking a seal yourself

A seal is a directory holding `seal.json` and its two anchors. The anchors are for the SHA-256 of `seal.json` exactly as published, so the standard tools check them with nothing from this project.

The RFC 3161 anchor, with OpenSSL. The first two commands take the authority's certificates out of the anchor, which older OpenSSL builds need:

```bash
openssl ts -reply -in seal.json.tsr -token_out -out token.p7
```

```bash
openssl pkcs7 -inform DER -in token.p7 -print_certs -out authority-certificates.pem
```

```bash
openssl ts -verify -data seal.json -in seal.json.tsr -CAfile /etc/ssl/cert.pem -untrusted authority-certificates.pem
```

The OpenTimestamps anchor, with the official client. It is complete only once it has reached the Bitcoin block chain, some hours after sealing:

```bash
ots verify seal.json.ots
```

When a trial's forecasts are revealed, each comes with the secret value behind its commitment. To confirm they are the forecasts committed to in the seal:

```bash
uv run trialseal-verify seals/2026-11-02 revealed/NCT00000000.jsonl
```

## Status

Built: snapshot, candidate universe, scoring, the record pipeline (screening, base-rate forecaster,
batches, adjudication rules, primary comparison), and sealing with reveal verification. Not built
yet: real screening, the reference set, the other forecasters, readout detection, the reveal step
and scoreboard, the full analysis plan. Nothing has been registered or sealed.
