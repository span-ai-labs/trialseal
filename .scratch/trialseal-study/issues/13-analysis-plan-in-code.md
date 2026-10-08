# 13: Analysis plan in code

**What to build:** Every registered analysis can be produced by one command from sealed forecasts and adjudicated outcomes, including the descriptive look and the final analysis with its extension rule.

**Blocked by:** 05

**Status:** done

- [x] The primary comparison uses first forecasts in the primary analysis set, with uncertainty that groups trials of the same drug
- [x] Calibration, discrimination and a second scoring rule are reported for every forecaster
- [x] Effect-size forecasts are scored with proper scoring rules against the class-level baselines
- [x] Secondary and sensitivity analyses are produced: all sponsors, last forecast before readout, accuracy by lead time, by forecaster version, without non-English disclosures, void counted as negative, unresolved trials imputed
- [x] The descriptive look reports scores and makes no test of the registered claim
- [x] The final analysis applies the extension rule at the registered thresholds and can run only once
- [x] A table per model shows its cutoff, release date, dates of use and the earliest and latest readout scored
- [x] One command regenerates every table and figure

## Comments

**2026-10-08, from ticket 02's review.** The first forecast is found by forecaster name, so a forecaster renamed between batches would have a later forecast counted as its first. This ticket should fix a forecaster's identity across versions. The primary comparison currently returns Brier scores only: the paired uncertainty grouped by drug, and the all-sponsor secondary set, are still to add.

**2026-10-08, from ticket 05.** Each result now carries the endpoint its hazard ratio was reported for, as text. The effect-size analysis should check it against the scored endpoint named in the batch before scoring, and use each result's disclosure language for the sensitivity analysis without non-English disclosures.

**2026-10-08, from ticket 08.** A forecaster's first forecast may now be a record that none was produced. The primary comparison scores such a trial at the reference's probability (ADR-0013, proposed). The effect-size analysis needs the same rule for the hazard ratio.

**2026-10-08, built.** `analysis.py` holds the plan, `report.py` the command (`trialseal-analysis`), and the tests are in `tests/test_analysis.py` and `tests/test_report.py`. What each criterion became:

- Primary comparison: first forecasts, primary analysis set, Brier score, with a bootstrap that resamples whole groups of trials of one investigational drug. The drug is fixed in each batch trial at sealing, with the registry completion date shown that day.
- Every forecaster: Brier score, log score, calibration bins with the Murphy decomposition, and AUC.
- Effect size: CRPS and interval score on the log hazard ratio against each baseline the plan names.
- Sensitivity: all sponsors, last forecast before readout, without non-English disclosures, void as negative, unresolved imputed as negative and as positive; plus tables by lead time and by forecaster version.
- Descriptive look: scores only, fixed for 2027-04-15, made once.
- Final analysis: due 18 months after the first sealing; extends once to 24 months on a count alone; made once and afterwards only regenerated as it was.
- One row per model, and one command for every table and figure.

The carried-over comments: a forecaster is its name, and a forecaster that was not in the batch that first sealed a trial is scored at the reference's forecast for it, so a rename cannot make a later forecast a first one. A hazard ratio is scored only when recorded under the scored endpoint's own name. The no-forecast rule covers the hazard ratio and every other score (ADR-0013, extended).

**Two reviews found guards that could be got round; each is now closed with a test that fails without the fix.** The day the final analysis was run used to decide the extension; it now uses only sources disclosed by its fixed date and refuses to run until every sealed trial is accounted for. The plan was a loose file; every seal now carries it. A seal could be removed to make a later forecast look like a first; seals are now chained. The record that an analysis had run was trusted; it now stores what the analysis was run on and what it produced, and a recorded extension is recomputed before it is believed. A trial could be dropped by recording that its forecasts had been opened; that now blocks the analysis instead. One drug group gave an interval of no width; no claim now rests on fewer than 30 drug groups.

**Rules introduced here.** The study lead said on 2026-10-09 to go with all recommendations, which I have taken to confirm these; they belong in the protocol:

1. The claim is supported when the whole 95% interval for the difference in Brier score favours the forecaster (percentile bootstrap over drug groups, 10,000 resamples, fixed seed). The p-value is reported and plays no part.
2. No claim rests on fewer than 30 drug groups; with fewer, the study reports an estimate only.
3. The extension is decided on the number of trials that can be scored in the primary comparison, not on the number with any result.
4. The descriptive look is on 2027-04-15.
5. The final analysis waits until every sealed trial has a settled result, a readout recorded as later than its date, or a screening on or after its date that found no public result. A trial adjudicated by someone who had opened its forecasts blocks it.
6. An analysis fixed for a date uses only sources disclosed by that date, and counts a hazard ratio as awaited or missing as of that date.
7. A hazard ratio counts for the scored endpoint only when the adjudicators recorded it under that endpoint's exact name.
8. Unresolved trials are imputed, both as negative and as positive, only once the registry completion date fixed at their first sealing has passed.
9. Lead-time bands of under 3, 3 to 6, 6 to 12 and over 12 months; ten calibration bins.
10. The investigational drug defaults to the first drug the registry lists in experimental arms only, to be corrected at screening. A trial with none recorded is its own group.
11. In the estimate-only case p-values are removed and intervals kept.

12. With enough trials but fewer than 30 drug groups at 18 months, the study ends as an estimate with no extension. Below 30 drug groups no comparison is given an interval or a p-value.
13. A hazard ratio still awaited at the date of the final analysis is never scored: the analysis runs once. Decided 2026-10-09 (ADR-0014): a registered follow-up runs once, six months after the final analysis date, and scores the same trials against the hazard ratios disclosed by then. It is built (`effect_size_follow_up`) and `trialseal-analysis` writes it when due.
14. Once a trial's forecasts are revealed, the two adjudicators are no longer blind for it, yet a later and more authoritative source may still need reading (ADR-0008). Today such a reading holds the trial back from any analysis that covers the source. Decided 2026-10-09 (ADR-0015): a source read after the forecasts were opened decides nothing; a blind reading of another source stands, the later one is set aside and listed, and one sensitivity analysis counts it. A trial with no blind reading still holds up the final analysis.
15. The sensitivity analysis that ADR-0011 promises for missing hazard ratios counts each as a hazard ratio of 1.
16. Trials outside the primary analysis set must also be accounted for before the final analysis.
17. A void trial is dated by its earliest disclosure. The model table counts a readout if the model sealed a forecast for the trial in any batch before it, for any sponsor.
18. A bootstrap p-value is (count + 1) / (resamples + 1), so it is never zero.

**Known limits.** Deleting `study/analyses.jsonl` would let an analysis be run again; only publishing that file when it is written makes this visible, and it is not yet anchored as seals are. A seal removed from the end of the chain is noticed only if an analysis was recorded while it existed. Two chains sealed on the same days under two plans would both read back; only the published repository tells them apart. The OpenTimestamps check confirms that an anchor carries a block-chain attestation; checking it against the chain itself still needs the official client (`ots verify`). A trial's recorded result still carries the first hazard ratio of any endpoint, while the analysis scores the first for the scored endpoint. Registry dates are parsed in three places and should share one helper.

**2026-10-08, second review.** A second adversarial pass found the earlier holes closed or partly closed and seven smaller ones, all now fixed with tests: a screening accounted for a trial even when a later one showed it had read out; a batch could go absent after an analysis was recorded; an analysis record could understate how long the log was, letting held-back adjudications be added afterwards; the command printed a traceback on an unreadable record of analyses; the floor of 30 drug groups covered only the primary comparison; a reading that was not blind held a trial back even from an analysis that did not cover its source; a reconciliation could date a source in the future. It also confirmed by mutation that the tests fail when each fix is removed.
