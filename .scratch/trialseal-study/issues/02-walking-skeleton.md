# 02: Walking skeleton: one trial from snapshot to score

**What to build:** A single made-up trial travels the whole path: it is screened as having no public result, a base-rate forecaster issues a forecast in the common forecast shape, the batch is fingerprinted, two adjudicators record the same outcome, and the primary comparison scores the first forecast. Thin everywhere, complete end to end.

**Blocked by:** 01

**Status:** done

- [x] A forecaster contract exists: frozen registry record and batch date in; probability of a positive trial, median hazard ratio and 80% interval out, with forecaster name and version
- [x] A base-rate forecaster implements the contract
- [x] A screening record marks a trial as eligible or as already read out, with evidence and date
- [x] Building a batch refuses any trial recorded as already read out
- [x] A batch produces one canonical record set per forecaster and a single fingerprint over all of them
- [x] An adjudication record needs two adjudicators; a result exists only when they agree
- [x] The primary comparison scores only the first forecast each forecaster sealed for a trial
- [x] The whole path runs in one test with no network access

## Comments

**2026-10-08, implemented.** One made-up trial now travels from a snapshot on disk through screening, a base-rate forecast, a fingerprinted batch written to and read back from disk, two agreeing adjudications and the primary comparison, with the network blocked in the test. 54 tests pass.

Review found the first version's guards could be bypassed; each finding became a failing test and was fixed:

- A batch read from disk is refused if its contents no longer match the recorded fingerprint.
- A trial ever recorded as read out can never be cleared again, and a screening must be dated on or before the batch and be recent.
- A forecaster must return its own forecast for the trial and batch asked; two forecasters cannot share a name.
- The batch records each trial's scored endpoint and reference class, and the fingerprint covers them.
- The primary comparison takes the adjudication log itself, scores industry-led trials only (ADR-0003), and reports, without scoring, any trial whose first forecast was not issued before its readout.
- Two adjudications by the same person under differently typed names count as one.

One rule was introduced here and needs the study lead's confirmation:

- A screening clears a trial for a batch only if it is no more than 14 days old.

Left to later tickets, with notes added there: 03, 05, 06, 13.
