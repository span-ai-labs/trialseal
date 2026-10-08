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
- `src/trialforecast/models.py` — frontier models as shipped: the prompt every model sees, one adapter per provider's own library, each trial asked about several times and the answers combined by a fixed rule, and everything recorded with the forecast. The models are listed in `study/models.json`.
- `src/trialforecast/screening.py` — screening records and which candidates are eligible.
- `src/trialforecast/batch.py` — builds a batch (refusing any trial not screened as eligible), fingerprints it, writes and reads it.
- `src/trialforecast/adjudication.py` — adjudications of each source, reconciliations, and the rules that turn them into a trial's result (source ranking, readout date, hazard-ratio window, blindness).
- `src/trialforecast/sealing.py` — seals a batch: one commitment per forecast, a seal with no forecast in it, anchors from two time-stamping services, publication of the seal alone, and verification of a revealed forecast. Every seal carries the registered plan and the fingerprint of the seal before it, and a sealed study is read back only as one unbroken chain.
- `src/trialforecast/anchors.py` — the two kinds of time-stamping service (an RFC 3161 authority, verified with OpenSSL, and OpenTimestamps).
- `src/trialforecast/analysis.py` — the registered analysis plan: the primary comparison on first forecasts with trials of one drug resampled together, every forecaster's calibration and discrimination, hazard-ratio scoring against baselines, the sensitivity analyses, and the descriptive look and final analysis, each made once on its fixed date and afterwards only regenerated as it was.
- `src/trialforecast/report.py` — the one command that regenerates every registered table and figure from the seals, the openings, the adjudication log and the screening log.
- `src/trialforecast/pilot.py` — the retrospective pilot: the cutoff and memorisation probes, the buffer after each model's stated cutoff, closed-book forecasts on later readouts, and the pilot report.
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
uv run trialseal-analysis                    # every registered table and figure that is due, into results/
uv run trialseal-pilot probe                 # then forecast, then report: the retrospective pilot, below
```

## The retrospective pilot

Before anything is sealed, the method is tried on trials that have already read out. It tests the method and is not the evidence. Three steps, each of which can be stopped and run again; `--model` works with one model of the roster and `--budget-usd` caps what one invocation spends:

```bash
uv run trialseal-pilot probe
```

asks each model what it already knows about every traced trial, from the registry record and from identifiers alone, and when the result was first reported.

```bash
uv run trialseal-pilot forecast
```

chooses each model's buffer from its probes and has it forecast, with no web access, only the trials that read out after its stated cutoff plus that buffer.

```bash
uv run trialseal-pilot report
```

writes `results/pilot/report.md`, the recall table and the list of pilot trials for the adjudicators. Replies and forecasts are kept under `private/pilot/` and are never printed, because the adjudicators have still to read the pilot trials. Their readings go in `adjudication/pilot/`; the report uses them in place of the traced results as they arrive.

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
batches, adjudication rules), sealing with reveal verification, frontier models as forecasters, and the registered
analysis plan with its one command, and the retrospective pilot (probes run for two models and forecasts for one; outcomes
await adjudication). Not built yet: real screening, the reference set, the statistical baselines and the
Span forecaster, readout detection, the reveal step and scoreboard. Nothing has been registered or sealed.
