# 09: Retrospective pilot

**What to build:** Before anything is sealed, the method is tried on trials each model cannot have seen: its knowledge around the stated cutoff is probed, its forecasts on later readouts are scored, and the numbers needed for the sample-size statement are measured.

**Blocked by:** 05, 08

**Status:** ready-for-human

- [x] Each model is probed for recall of readouts by month around its stated cutoff, and a buffer is chosen from the result
- [x] Each model is tested on recalling results from trial identifiers alone
- [x] Each model's pilot trials are those with a readout after its cutoff plus buffer
- [ ] Pilot outcomes are adjudicated by both adjudicators and their agreement is reported
- [ ] The pilot reports the variance of per-trial score differences between forecasters and a revised sample-size statement, including one for the effect-size analysis
- [x] A model showing recall beyond its buffer is dropped from the pilot or given a longer buffer
- [x] The report states plainly that the pilot tests the method and is not the evidence

## Comments

**2026-10-08, built and run; waiting on the two adjudicators.** `pilot.py` holds the pilot and `trialseal-pilot probe | forecast | report` runs it (README, "The retrospective pilot"). Tests are in `tests/test_pilot.py`. Two boxes stay open because they need people: the pilot outcomes have to be adjudicated by both adjudicators, and the variance and sample-size statement in the report are provisional until they are.

**What is left for the study lead and the second adjudicator.**

1. Adjudicate the pilot trials listed in `results/pilot/adjudication_worklist.csv`, each of you independently, without opening anything under `private/pilot/`. Readings go in `adjudication/pilot/adjudications.jsonl` (and `reconciliations.jsonl` where you differ). There is no entry form yet: ticket 16 builds one, and until then readings are appended with `record_adjudication`. Record a hazard ratio under the scored endpoint's exact name, as the worklist gives it.
2. Run `uv run trialseal-pilot report` again. It replaces traced results with adjudicated ones as they arrive, re-draws each model's pilot trials from the adjudicated readout dates, and reports your agreement.
3. Done 2026-10-09: with credit added, Claude Opus 5.5 forecast its 5 pilot trials and the report was regenerated.
4. Fix the Google key's billing if Gemini is to be in the pilot: it failed nearly every call, so it has not been probed.
5. Look again at the sources for the trials the report lists under "the right result with a date more than 3 months before the readout on record". One such check has already moved a traced date by seven months.

**What the run found** (2026-10-08, 110 traced trials: 80 with a readout and a clear result, 30 with none found).

- Asked only "do you know the result?", Claude Opus 5.5 said it knew eight results that the trace dated after its stated cutoff, and had all eight right. A second look at five of them found four traced dates correct: the model had inferred the results, usually from a sibling trial, and placed the announcements a year early. The fifth traced date was seven and a half months late (IMpower030 was first disclosed as a line in a Roche pipeline document). So the first wording of the probes could not tell memory from inference.
- The probes now also ask when the result was first reported, and recall means the right result dated to within three months. Asked this way, neither model recalled any result disclosed after its stated cutoff, and neither said it knew a result for any of the 30 trials with no readout.
- Dated recall stops well before the stated cutoffs: about five months before for Claude Opus 5.5 (stated June 2026) and four months before for gpt-6.1-sol (stated 30 April 2026).
- Each model therefore gets the minimum buffer of one month: 5 pilot trials for Claude Opus 5.5 (the minimum that is kept) and 17 for gpt-6.1-sol. Only 1 and 6 of those have a hazard ratio public within six months, so the effect-size part of the sample-size statement rests on very little.
- Scores so far are for gpt-6.1-sol only, on traced outcomes: its Brier score is 0.058 below the base rate's over 17 pilot trials, and its CRPS 0.043 below the baseline's over the 6 with a hazard ratio. The standard deviation of the per-trial Brier differences is 0.114 (95% interval 0.085 to 0.174). With that spread a paired comparison on 120 trials detects a mean difference of about 0.03 (0.044 if the spread is at the top of its interval), and on 60 trials about 0.04.
- These numbers are in `results/pilot/report.md`. They are provisional, they come from a frontier model as shipped rather than the Span forecaster, and 17 trials pin the spread down only roughly.
- Cost of the whole run: about $8.70 in model replies ($5.02 Anthropic, $3.63 OpenAI, a few cents Google).

**Two reviews found defects, all fixed with tests that fail without the fix.** The stand-in model in the file-level tests never produced a forecast, so some assertions were empty. A buffer could be chosen from half-finished probes, and a model that refused every probe counted as having no recall. Adjudicated results replaced outcomes but not readout dates, pilot membership or base rates, and a void trial kept the pilot provisional for good. A registry time frame naming a data cut-off was shown to the forecaster. A forecast lost to an outage was billed but not counted against the budget, and a model without prices was never stopped. The score "without the trials it said it knew" could give away a single forecast when only one trial was removed.

**Rules introduced here.** The study lead said on 2026-10-09 to go with all recommendations, which I have taken to confirm these.

1. Recall is the right result with the month of first report right to within three months.
2. The buffer runs through the last month with recall on either probe and is never less than one month. A model left with fewer than 5 pilot trials is dropped; so is one that gives a usable answer to fewer than 90% of probe questions.
3. Each probe question is asked once. A refusal or unusable reply is recorded and not asked again; a provider outage is not recorded and is asked again.
4. A model is shown today's registry record without status, registry completion date and enrolment, because past versions of records could not be fetched. Forecasts are also not shown outcome time frames. This hides the planned enrolment too, so a pilot forecast rests on less than a prospective one.
5. The pilot's reference is the base rate among traced readouts no later than the model's cutoff month, by reference class, pooled where a class has fewer than 5; the typical hazard ratio is their median with the 10th and 90th centiles as its interval. At least 10 such readouts are required.
6. A traced hazard ratio is used only if public within six months of the readout (ADR-0011).
7. Agreement is measured on first readings; kappa is not reported when both adjudicators called every source the same way; hazard ratios agree when they name the same endpoint and match to two decimal places.
8. The sample-size statement is for a paired comparison at two-sided 5% with 80% power, treats trials of one drug as independent, and states the trials needed for assumed mean differences of 0.01, 0.02, 0.03 and 0.05.
9. Scores without the trials a model said it knew are shown only when at least 3 trials are removed and at least 3 remain.

**Known limits.** The pilot is small because the models are new: there are few months between a stated cutoff and today. A wider but less clean estimate of the spread is possible from every readout after a model's last month of recall (about 30 trials for each model) and has not been run. The first wording of the probes (version 1) is kept in the private files and is not counted.

**2026-10-09.** `study/pilot_traces.json` now records each trace file with its SHA-256, and the pilot refuses to run if one has changed or gone. The four files are as they were when the pilot was begun.
