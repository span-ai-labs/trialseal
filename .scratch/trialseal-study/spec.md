# TrialSeal study: sealed forecasting of phase 3 cancer trial results

**Status:** ready-for-agent

Vocabulary follows `CONTEXT.md`. Decisions referenced as ADR-NNNN are in `docs/adr/`.

## Problem Statement

Span needs evidence that it can do something measurable, verifiable by outsiders, and produced without hospital data, sponsors or clinicians. An investor declined citing missing clinical and technical validation, and two earlier preprints were null results on retrospective data.

Claims about predicting trial results are common and unverifiable: vendors publish headline accuracy without trial lists, and retrospective tests on language models are contaminated because the models have already read the results. Nobody can tell from the outside whether any forecaster, Span's included, beats simply quoting the base rate. No published work seals hazard-ratio forecasts before readout.

## Solution

A pre-registered study in which forecasters issue a forecast for every eligible trial each month, the batch is sealed so its date can be proven, and each forecast is revealed and scored after the trial's readout by two adjudicators who cannot see the forecasts.

The registered claim is that the Span forecaster's probability of a positive trial scores better than the base rate of each trial's reference class (ADR-0002). The hazard-ratio forecast is the named key secondary. Every result is reported, including a null (ADR-0006).

The study produces, in order: a registered protocol and a sealed first batch; a retrospective pilot; a public scoreboard of resolved trials; a descriptive look in mid-April 2027; and a final analysis 18 months after the first sealing (ADR-0007).

## User Stories

Actors: the **study lead** (runs the study), the **second adjudicator**, a **reviewer** (journal or conference referee), a **reader** (investor, sponsor, journalist looking at the scoreboard), and an **invited academic**.

### Registry and candidates

1. As the study lead, I want a time-stamped snapshot of the registry taken every day, so that I can prove what the registry said on any date.
2. As the study lead, I want each snapshot to carry a fingerprint and the exact query that produced it, so that anyone can verify it was not altered.
3. As the study lead, I want the snapshot to cover trials whose registry completion date is years away in either direction, so that trials reading out early or late are not missed.
4. As the study lead, I want a candidate list of randomised phase 3 cancer trials with a time-to-event primary endpoint, so that only trials with a scoreable hazard ratio are considered.
5. As the study lead, I want each candidate tagged with sponsor type, endpoint type, number of primary endpoints and whether its registry date is stale, so that I can assign reference classes and spot hard cases.
6. As the study lead, I want an alias table per trial (acronym, sponsor study number, drug names and code names, partner companies), so that readouts published under a different name are still found.
7. As the study lead, I want to see which registry records changed between two snapshots, so that only changed trials are re-researched in later batches.

### Screening and eligibility

8. As the study lead, I want every candidate screened for an existing public primary result before sealing, so that no forecast is made on a result that is already known.
9. As the study lead, I want each screening decision logged with its evidence and date, so that eligibility can be audited.
10. As a reviewer, I want it to be impossible to seal a forecast for a trial marked as already read out, so that the prospective arm is clean by construction.
11. As the study lead, I want the scored endpoint named and frozen for each eligible trial at sealing, so that the effect-size target cannot be chosen after the fact.
12. As the study lead, I want each eligible trial assigned to a reference class at sealing, so that its base rate is fixed before any result.
13. As the study lead, I want non-inferiority designs and other excluded designs listed with the reason, so that exclusions are transparent.

### Reference set and base rates

14. As the study lead, I want the remaining past industry-led trials traced to their readouts, so that base rates come from our own reference set (ADR-0009).
15. As the second adjudicator, I want to adjudicate a sample of the reference set independently, so that agreement between us is measured before the study starts.
16. As a reviewer, I want the base-rate table published with counts and uncertainty for each reference class and frozen at registration, so that the bar cannot move.
17. As a reviewer, I want the flat overall base rate and the published literature rates reported alongside, so that I can judge how hard the bar is.
18. As the study lead, I want the distribution of reported hazard ratios by reference class from the reference set, so that effect-size forecasts have an empirical baseline.

### Forecasters

19. As the study lead, I want every forecaster to answer in one common shape, so that all are sealed and scored identically.
20. As the study lead, I want a base-rate forecaster, so that the registered bar is itself a sealed forecast.
21. As the study lead, I want a simple model on registry fields trained only on reference-set results, so that there is an honest statistical comparator.
22. As the study lead, I want class-level effect-size baselines (the empirical distribution, the average sponsor-assumed effect, and that average shrunk toward no effect), so that hazard-ratio forecasts have comparators that exist for every trial.
23. As the study lead, I want frontier models as shipped queried without web access, all given identical trial information, several times each, so that their forecasts are comparable and their variability is known.
24. As a reviewer, I want each model's identifier, stated training cutoff, release date and date of use recorded, so that leakage can be assessed.
25. As the study lead, I want the Span forecaster to gather evidence about each trial and then forecast, with everything it retrieved logged, so that a later leak audit is possible.
26. As the study lead, I want the Span forecaster's version sealed with every batch, so that upgrades cannot be confused with earlier forecasts.
27. As the study lead, I want a forecast that is repeated unchanged to be recorded as a carried forecast, so that the record shows what was and was not re-researched.
28. As a reviewer, I want a forecaster's failure to produce a forecast recorded as such, so that nothing can be quietly dropped.
29. As the study lead, I want the cost of each batch tracked against a ceiling, so that the study stays affordable for 18 months.

### Batches and sealing

30. As the study lead, I want batches issued monthly on dates fixed at registration, so that the timing of forecasts cannot be chosen opportunistically.
31. As a reviewer, I want each batch to contain every forecaster's forecast for every eligible trial, including the baselines, so that the whole denominator is committed.
32. As a reviewer, I want each batch fingerprinted and that fingerprint anchored by two independent time-stamping methods and a public posting, so that its date does not depend on trusting Span.
33. As a reader, I want the list of trials in each batch public while the forecasts stay hidden (ADR-0001), so that I know what was forecast without the forecasts moving markets.
34. As a reader, I want to check a revealed forecast against the fingerprint published months earlier, so that I can verify it myself.
35. As the study lead, I want sealing to refuse to run if the protocol is not registered or any eligibility check fails, so that an invalid batch cannot exist.

### Readouts and adjudication

36. As the study lead, I want candidate readouts surfaced from company announcements, US and Asian exchange filings, conferences, the literature and the registry, so that readouts are found wherever they first appear.
37. As the study lead, I want every candidate readout queued for human confirmation and never resolved automatically, so that detection errors cannot become results.
38. As an adjudicator, I want to record a trial as positive, negative or void, with the reported hazard ratio, its source, date and language, without seeing any forecast, so that adjudication is blind.
39. As a reviewer, I want a result to count only when both adjudicators agree, with disagreements and their reconciliation logged, so that outcomes are not one person's opinion.
40. As a reviewer, I want the most authoritative source available on the analysis date to decide the result and the earliest disclosure to set the readout date (ADR-0008), so that corrected results are handled by rule.
41. As the study lead, I want a result revised by a later, more authoritative source to keep its history, so that changes are visible.
42. As the study lead, I want a hazard ratio awaited for six months after readout and then recorded as missing (ADR-0011), so that the effect-size analysis has an end.
43. As an adjudicator, I want the original announcement and a translation side by side for non-English disclosures (ADR-0010), so that I can judge them properly.
44. As a reader, I want the adjudication log published with the reveal, so that I can see how each outcome was decided.

### Reveal and scoreboard

45. As the study lead, I want reveal to be impossible until a recorded legal sign-off exists, so that nothing is published early by accident.
46. As a reader, I want a public scoreboard of resolved trials showing each forecast, the outcome and the running scores of every forecaster against the base rate, so that I can see who is ahead.
47. As a reader, I want the scoreboard to show how many trials were sealed, resolved, unresolved and void, so that I can see nothing is hidden.
48. As a reader, I want a plain research-only notice and the conflict-of-interest statement on the scoreboard, so that I know who built it and why.

### Scoring and analysis

49. As a reviewer, I want the primary comparison computed on first forecasts (ADR-0005) in the primary analysis set, with uncertainty that accounts for several trials of the same drug, so that the headline is conservative.
50. As a reviewer, I want calibration, discrimination and a second scoring rule reported for every forecaster, so that a single number is not the whole story.
51. As a reviewer, I want hazard-ratio forecasts scored with proper scoring rules against the class-level baselines, so that the key secondary is rigorous.
52. As a reviewer, I want the pre-registered secondary and sensitivity analyses (all sponsors, last forecast before readout, accuracy by lead time, by forecaster version, without non-English disclosures, void counted as negative, unresolved trials imputed), so that I can test how robust the result is.
53. As the study lead, I want the descriptive look produced on its fixed date with no test of the registered claim, so that the final analysis is not weakened.
54. As the study lead, I want the final analysis to run once, on its fixed date, from sealed inputs only, with the extension rule applied automatically (ADR-0007), so that stopping cannot be influenced by the results.
55. As a reviewer, I want one command to regenerate every table and figure from the public record, so that the analysis is reproducible.
56. As a reviewer, I want one table per model showing its cutoff, release date, dates of use, and the earliest and latest readout in its evaluation, so that temporal integrity is visible at a glance.

### Retrospective pilot

57. As the study lead, I want each model probed for knowledge of readouts around its stated cutoff, so that the stated cutoff is checked and a buffer chosen.
58. As the study lead, I want each model tested on recalling results from identifiers alone, so that memorisation is measured.
59. As the study lead, I want a closed-book pilot on each model's own post-cutoff trials, adjudicated by both of us, so that the method, the rules and our agreement are tested before sealing.
60. As the study lead, I want the pilot to give the variance of score differences between forecasters, so that the sample-size statement in the registration uses measured numbers.

### Registration and governance

61. As the study lead, I want the protocol assembled from the recorded decisions (claim, sets, rules, dates, baselines, analyses), so that the registration cannot drift from what was decided.
62. As an invited academic, I want to read and comment on the protocol before registration, so that my involvement is real.
63. As a reviewer, I want the no-trading policy and conflict of interest stated in the registration, so that the incentives are disclosed.
64. As a reviewer, I want the reporting checklist for language-model studies completed, so that the paper meets the journal standard.
65. As the study lead, I want a log of any deviation from the registered protocol with its date and reason, so that changes are honest and visible.
66. As a reviewer, I want anonymised access to data and code at submission, so that double-blind review is possible.
67. As the study lead, I want the human-only steps (model keys, registration account, public repository, time-stamp setup) walked through once and recorded, so that they do not need re-explaining.

## Implementation Decisions

**Modules.** Each is a deep module with a small interface:

- **Registry snapshot**: fetches and fingerprints the registry state. Exists.
- **Candidate universe**: turns a snapshot into tagged candidates. Exists; needs reference-class tagging and the alias table.
- **Screening log**: records, per candidate and date, whether a public primary result exists, with evidence. Produces the eligible trials for a batch.
- **Reference set**: traced and adjudicated past trials; produces the base-rate table and the empirical hazard-ratio distributions.
- **Forecaster contract and forecasters**: one contract; implementations are the base rate, the registry-feature model, the class-level effect-size baselines, frontier models as shipped, and the Span forecaster.
- **Batch builder**: runs every forecaster over every eligible trial and writes one canonical record set per forecaster, including carried forecasts and failures.
- **Sealer and verifier**: fingerprints a batch, anchors the fingerprint, and lets anyone check a revealed forecast against it.
- **Readout monitor**: proposes candidate readouts for human confirmation.
- **Adjudication log**: two blind adjudications per trial, agreement, reconciliation, source ranking, revision history.
- **Reveal**: discloses forecasts for resolved trials, gated on legal sign-off.
- **Scoring**: proper scoring rules and paired comparisons. Exists.
- **Analysis**: applies the registered analysis plan to sealed forecasts and adjudicated outcomes; produces the descriptive look and the final analysis.
- **Scoreboard**: a static public page generated from revealed records.
- **Protocol generator**: assembles the registration document from the decision records and frozen tables.
- **Retrospective pilot**: cutoff probe, memorisation probe, closed-book forecasts on post-cutoff trials.

**Storage.** Append-only records in plain files inside the repository; no database. Registry payloads stay out of git and need their own backup; their manifests are tracked.

**Forecast shape.** One eligible trial, one forecaster, one batch: probability of a positive trial; median hazard ratio and an 80% interval for the scored endpoint, treated as a distribution on the log scale; forecaster version; whether carried; raw output and, for the Span forecaster, the retrieval log; cost.

**Reference class.** Sponsor type by endpoint type (ADR-0002).

**Sealing.** A fingerprint over the complete canonical batch, raw outputs included so that a rounded probability cannot be guessed back. Anchored by two independent time-stamping methods and a push to the public repository. The registration on the registry service is the citable record; the cryptographic proofs are supporting material. Forecast content is kept out of the public repository until reveal; the trial list and fingerprints are public from sealing.

**Frontier models as shipped.** Queried through the provider's plain interface with no tools and no added system; identical trial information for every model; several runs per trial, combined by a rule fixed at registration.

**Span forecaster.** A research agent with web access in the prospective arm only (ADR-0004). Frozen and version-tagged per batch. A full pass in the first batch; afterwards only trials whose registry record or evidence changed are re-researched and the rest are carried.

**Clustering.** Paired comparisons resample whole groups of trials that test the same investigational drug.

**Guards enforced in code.** No sealing without a registered protocol; no forecast for a trial with a recorded public result; no reveal without recorded legal sign-off; no resolved outcome without two agreeing adjudications; the final analysis reads sealed inputs only and runs once.

**Secrets.** Model keys come from the environment and are never written to the repository.

## Testing Decisions

A good test here states a rule of the study and checks it from the outside with small made-up records; it does not inspect internals.

- **Main seam: the record pipeline.** Snapshot to eligible trials; eligible trials and forecaster output to a sealed batch; sealed batches and the adjudication log to scores and analysis tables. No network. Rules covered include: a trial with a public result is never sealed; only the first forecast is scored in the primary comparison; a carried forecast is recorded as carried; a disagreement between adjudicators blocks a result; the most authoritative source decides and the earliest sets the date; a later source revises a result and keeps the history; a missing hazard ratio after six months is recorded as missing; the extension rule fires at the registered thresholds; a revealed forecast verifies against its fingerprint and a tampered one does not.
- **Forecaster contract.** Stand-in forecasters with fixed answers; every real forecaster is checked for the contract and for never receiving information dated after the batch.
- **Outside services.** Thin adapters tested against recorded responses, plus one optional live check outside the normal run.
- **Not covered by automated tests.** The adjudicators' judgments, the screening decisions, and the quality of the Span forecaster. The pilot and the prospective arm measure those.
- **Prior art.** The existing tests for the candidate universe (made-up registry records) and for scoring (known values, numerical checks, simulated comparisons).

## Out of Scope

- Recruiting a panel of oncologists to forecast the same trials. It remains an upside if invited academics join.
- Patient-level data of any kind.
- Phase 1 and 2 trials, non-cancer trials, and trials without a time-to-event primary endpoint.
- Any product, pricing or customer feature beyond the public scoreboard.
- Trading, or any use of forecasts before reveal.
- Writing the papers. This spec builds the study and its record; the manuscripts are separate work.
- The legal opinion itself; the system only records that sign-off exists.
- Research into what makes a forecaster accurate. That is a separate research task to run before the Span forecaster is built.

## Further Notes

**Dates.** First sealing targeted for early November 2026. Descriptive look in mid-April 2027. Final analysis 18 months after first sealing, extendable once to 24 months.

**Venues.** A benchmark paper for the NeurIPS 2027 evaluations track, then a clinical paper offered to Nature Medicine with NEJM AI and Nature Communications as fallbacks.

**Open facts that become tickets.**

- Whether a sponsor's assumed effect size can be found before readout. No protocol document has been opened to check.
- Access to past registry versions. Scripted access was refused; this limits only the retrospective pilot.
- The price of a full Span forecaster pass, to set the monthly ceiling.
- A fresh search for overlapping work immediately before registration.
- Tracing the remaining past trials for the reference set.

**Defaults chosen here that the study lead has not yet confirmed.** They must be confirmed in the protocol before registration.

- Non-inferiority designs are excluded and listed separately.
- For trials with more than two arms, the comparison forecast is the first-listed experimental arm against control in the frozen registry record.
- Forecasts are elicited as a probability plus a median hazard ratio and 80% interval.
- Several runs of a frontier model are combined by averaging the probabilities.
- Endpoint type has three values: overall survival, progression-type endpoints, other time-to-event.

**Pending from people.** The second adjudicator's agreement to the role and to the no-trading policy; model keys on the machine; counsel engaged before the first reveal; the invitation to the academic group, which needs a two-page summary of this protocol.

**Evidence base.** The pre-build research report and notes, and the 70-trial readout trace, both in the parent project folder and under `data/`.
