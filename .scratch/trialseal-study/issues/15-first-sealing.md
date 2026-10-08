# 15: First sealing

**What to build:** Batch 1 is issued for every eligible trial by every forecaster, sealed, and its list of trials published.

**Blocked by:** 03, 06, 07, 08, 11, 14

**Status:** ready-for-agent

- [ ] The protocol registration is recorded before the batch is built
- [ ] Every eligible trial has a forecast, or a recorded failure, from every forecaster including the baselines
- [ ] The Span forecaster's version is sealed with the batch
- [ ] The fingerprint is anchored by both time-stamping methods and pushed publicly with the list of trials
- [ ] No forecast content is public
- [ ] The verifier confirms the sealed batch
- [ ] The cost of the batch is recorded against the ceiling
- [ ] Needs the study lead: go-ahead on the day

## Comments

**2026-10-08, from ticket 06.** Sealing takes the two services from `study/anchors.json` (written by the setup wizard) and the registration from `study/registration.json`; this ticket wires them into a command. A batch can only be sealed on its own date. The OpenTimestamps anchor is incomplete at sealing: it reaches the block chain some hours later and must then be upgraded with the official client (`ots upgrade`) and the upgraded file published. The private openings are written under `private/`, which git ignores and which has no backup yet; losing them would make every forecast in the batch unrevealable.

**2026-10-08, from ticket 08.** `model_forecasters(study/models.json)` gives one forecaster per model; keys load with `load_keys(.env)`. A wrong key or model name raises `ModelUnavailable` and stops the batch, so a long batch should save each forecaster's forecasts as it goes, or paid work is lost. Check the Google key's billing before the first batch: Gemini returned capacity and quota errors on 2026-10-08.

**2026-10-08, from ticket 13.** Sealing now takes two more things. The registered plan, read with `read_plan(study/analysis_plan.json)`: every forecaster it names must be in the batch, and it can never change after the first seal. And the previous seal (none for the first batch): each seal names the one before it, and the analysis refuses a set of seals that is not one unbroken chain. Before any analysis the OpenTimestamps anchor of every seal must have been upgraded, because an anchor that has not reached the block chain is refused. `study/analyses.jsonl`, the record that each registered analysis was run, should be published as soon as it is written: deleting it is the one way left to run an analysis twice, and only its publication makes that visible.
