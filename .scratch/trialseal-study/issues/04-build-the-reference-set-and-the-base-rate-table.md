# 04: Build the reference set and the base-rate table

**What to build:** The remaining past industry-led trials are traced to their readouts and adjudicated under the study's own rules, giving the reference set. From it come the base rate for each reference class and the distribution of reported hazard ratios, both frozen for registration.

**Blocked by:** 02

**Status:** ready-for-human

- [x] The 212 untraced trials of the two-year pool are traced in the same format as the first 70
- [ ] Both adjudicators independently adjudicate a random sample, and their agreement is reported
- [ ] Rows of low confidence are re-checked before they count
- [x] A base-rate table gives, for each reference class, the count, the share of positive trials and its uncertainty
- [x] The flat overall rate and the published literature rates are shown beside it
- [x] The distribution of reported hazard ratios is given for each reference class
- [x] Void and unresolved trials are counted separately and never treated as negative in the table
- [ ] Needs both adjudicators: the sampled adjudications

## Comments

**2026-10-09, traced and tabulated; re-checks and the adjudicators' sample remain.** `reference.py` holds the reference set and the command (`trialseal-reference report | sample | freeze`); `traces.py` is the one reader of trace files; `data/readout_trace/TRACING_BRIEF.md` is the method. Tests are in `tests/test_reference.py`.

**What was traced.** All 282 industry-led trials of the two-year pool are now traced (tranches A to D), and a seeded random sample of 56 of the 305 trials that are not industry-led (tranche E), because those reference classes need a base rate too if their trials are to be forecast. In all 338 trials: 117 positive, 57 negative, 17 void, 138 with no readout found, 9 in doubt.

**Provisional figures** (`results/reference_set/report.md`). Nothing is adjudicated yet, and 66 traces of low confidence are not counted.

- Industry-led: 68.4% positive (108 of 158 clear results; 95% interval 60.7% to 75.1%).
- By endpoint type the two industry classes are far apart: overall survival 42.1% (16 of 38), progression-type 76.7% (92 of 120). A single industry base rate would have been a poor bar.
- Not industry-led: 7 of 14. Too few to set a bar.
- Median hazard ratio: 0.82 for industry overall survival (22 trials), 0.61 for industry progression-type (82).

**What is left.**

1. **Re-checks.** `data/readout_trace/recheck_worklist.csv` lists 81 trials: the 66 traced with low confidence, those in doubt, and 12 for which a model in the pilot gave the right result with a date well before the traced one. A re-check goes in `data/readout_trace/rechecks.csv` in the trace format and replaces the trace. The tracers ran eight at a time and exhausted a shared web-search allowance part-way, which is why so many rows are of low confidence; re-checks must be run a few at a time.
2. **More trials that are not industry-led.** Freezing needs 20 clear results and 10 hazard ratios for each sponsor type. There are 14 and 12. About 60 more of the 249 untraced ones should be traced.
3. **The adjudicators' sample.** After the re-checks, `uv run trialseal-reference sample` draws 40 trials once and writes `adjudication/reference/worklist.csv`, with nothing of what the trace found. Both adjudicators read them; readings go in `adjudication/reference/`. The report then gives their agreement and how often the trace matched them.
4. **Freezing.** `uv run trialseal-reference freeze` writes `study/base_rates.json` for registration. It refuses while anything is not yet counted, the sample is unread, or a sponsor type has too little.

**Rules introduced here.** The study lead said on 2026-10-09 to go with all recommendations; these follow from that and belong in the protocol:

1. A base rate counts only clear results: positive or negative, where the reader said the result was disclosed and gave the date. A trace of low confidence does not count until re-checked; a re-check that is itself unsure leaves the trial in doubt; a trial the adjudicators have begun and not settled is in doubt.
2. A reference class with fewer than 20 clear results takes its sponsor type's base rate; one with fewer than 10 hazard ratios takes its sponsor type's typical hazard ratio. Nothing is frozen for a sponsor type below those numbers.
3. The typical hazard ratio is the median on the log scale, with the 10th and 90th centiles as the 80% interval.
4. A traced hazard ratio counts only if the reader traced it for an endpoint of the same type as the scored endpoint and it became public on or after the readout and within six months of it.
5. The adjudicators' sample is 40 trials, drawn once with a fixed seed from trials traced as read out or void.
6. The trace is compared with the adjudicators on outcome and on readout date within a week.
7. A sample of 56 trials that are not industry-led was traced, rather than all 305.
