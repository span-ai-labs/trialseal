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

**2026-10-09, second review.** Fixed with tests:

- The sample is not drawn while any trace awaits a re-check, and it records the trials it was drawn from. Freezing refuses if a trial joined the reference set after the draw.
- Freezing refuses if the trace had the outcome right for fewer than nine in ten of the trials the adjudicators read (rule 8 below), and records the trace's accuracy in the frozen file.
- A sampled trial that has since left the reference set (a re-check found no readout) no longer blocks freezing.
- The frozen file records a SHA-256 of every trace, re-check, reference adjudication and design ruling it was made from. The base-rate forecaster refuses to load if any has changed.
- A hazard ratio that is not a finite positive number is refused when a trace is read.

8. *(confirmed by the study lead, 2026-10-09)* Nine in ten is the number for how often the trace must match the adjudicators before the unread traces are relied on. Below it, the adjudicators read every trace.

**Known limit.** A traced hazard ratio is matched to the scored endpoint by type (overall survival, progression-type), not by the endpoint's exact words; the adjudicated ones are matched exactly.

**2026-10-09, re-checks made.** All 81 trials of `recheck_worklist.csv` were looked at again, in six batches run three at a time (`recheck_sample_R1..R6.csv` in, `rechecks_R1..R6.csv` and their notes out; method in `data/readout_trace/RECHECK_BRIEF.md`). No batch ran out of web searches. 55 re-checks are of high confidence, 26 of medium, none of low, so no trace now awaits a re-check.

- The finding is unchanged for 69 of the 81; what changed for them is that a real search now stands behind it.
- Three trials went from not disclosed to disclosed; three from unclear to not disclosed; five kept a readout with a different result coding (mostly `unclear` or `mixed` resolved); two first-disclosure dates moved earlier, by about two weeks and by 26 days.
- For the 12 trials where a model had given an earlier date than the trace, an earlier disclosure was found for one. For most of the others a dated sponsor document from shortly before the traced date still describes the result as awaited, so the trace stands and the model's date was not recall.

**Figures now** (`results/reference_set/report.md`, still provisional, nothing adjudicated): 122 positive, 58 negative, 19 void, 135 with no readout found, 3 in doubt. Industry-led base rate 69.1% (114 of 165, 95% interval 61.7% to 75.6%); overall survival 45.0% (18 of 40), progression-type 77.4% (96 of 124). Not industry-led: 8 of 15.

**What still stands between here and freezing.**

1. Non-industry has 15 clear results; 20 are needed. About one traced non-industry trial in four has a clear result, so about 20 to 30 more should be traced. This comes before the sample: a trial that joins the reference set after the sample is drawn makes freezing refuse.
2. Three trials are in doubt after the re-check (NCT03520686, NCT04765059, NCT05118776): the source reports the primary analysis without a clear met or not met. Both adjudicators must read them.
3. One traced trial is tagged for exclusion review and has no design ruling (NCT03399110).
4. Then the sample, the adjudicators' readings and the freeze, as above.

**What the re-checks taught about the method.** Web search finds almost nothing for hospital-led trials and for small Chinese sponsors: it returns registry mirrors. What worked: the registry API; Crossref title searches on the drug name, which reach ASCO, ESMO and ASH abstracts; Europe PMC by registry number; the Hong Kong exchange's list of a company's announcements by date; cninfo for mainland-listed sponsors; the EU trial register's public API, which records early terminations that ClinicalTrials.gov still shows as recruiting. What stays out of reach: Chinese domestic meetings and journals (CSCO, CNKI, Wanfang), lapsed Hong Kong listing applications, and the exact release date of an ASCO abstract. A finding of nothing for a small unlisted sponsor is weaker than its label: such a sponsor can drop a trial without saying so. The batch notes list those rows for the adjudicators.

**2026-10-09, tranche F: 40 more trials that are not industry-led.** Drawn from the same pool as tranche E (the 305 trials of the two-year pool that are not industry-led, from `snapshots/2026-10-07T090006-wide` refined as of 2026-10-07). Tranche E was `random.Random(20261009).sample(sorted(pool), 56)`; I confirmed that reproduces the 56 traced. Tranche F is `random.Random(20261010).sample(sorted(untraced), 40)` from the 249 left, split by completion date into `sample_F1..F3.csv`. Traced three at a time under `TRACING_BRIEF.md` with the search rules of `RECHECK_BRIEF.md`; 32 rows of high confidence, 8 of medium, none of low.

**Figures now** (378 traced, still provisional, nothing adjudicated): 127 positive, 62 negative, 23 void, 156 with no readout found, 6 in doubt, 4 awaiting a design ruling. Industry-led is unchanged at 69.1% (114 of 165). Not industry-led: 13 of 24 clear results (54.2%, 95% interval 35.1% to 72.1%) and 19 hazard ratios, so both sponsor types now have enough to freeze. Not industry-led by endpoint: overall survival 2 of 9, progression-type 11 of 15.

**What stands between here and freezing, in order.**

1. **Four design rulings on traced trials, before the sample is drawn.** NCT02166788, NCT03399110, NCT04909684, NCT05674305 are tagged for exclusion review; each is proposed for exclusion as a stated non-inferiority design (`screening/design_review_proposals.csv`). A ruling to include one after the draw would add a trial to the reference set and make freezing refuse, so they come first.
2. **The sample**: `uv run trialseal-reference sample`.
3. **Both adjudicators read** the 40 sampled trials and the six in doubt (NCT00268476, NCT02416388, NCT03520686, NCT04765059, NCT05118776, NCT05549037).
4. **Freeze.**

**Two faults in the candidate universe that the tracers surfaced.** Neither changes a figure above by much; both matter before the first sealing and belong to ticket 01.

1. *Companies the registry classes as "other".* The sponsor type comes from the registry's sponsor class. It classes some companies as OTHER: 24 candidates led by five companies sit in the non-industry group, 15 of them Shanghai Junshi's. Five are traced, and two of those are positive results counted in the non-industry base rate. The primary comparison is on industry-led trials, so these would be left out of it wrongly. Recommended: a short list of sponsor corrections, fixed before the first sealing and published with the protocol.
2. *Candidates that are not cancer trials.* A time-to-event endpoint worded like a cancer one lets a few through: at least NCT04047628 (multiple sclerosis) and NCT03654053 (cirrhosis), and two trials in people who do not yet have cancer, for the study lead to rule on (NCT07609901, a vaccine for Lynch syndrome carriers; NCT06950385, familial adenomatous polyposis). This is from a word search of 2,425 candidates' conditions and titles, so it may not be all of them. Recommended: exclude by design ruling, which already holds for any candidate.

**Method notes from tranche F.** For academic trials, Crossref title scans on the drug or intervention name found disclosures that neither the registry number, PubMed, Europe PMC nor web search did, because abstracts rename trials and omit registry numbers. Congress abstract dates taken from Crossref are index dates and can be up to a week late. Six registry records in ten were stale. The tracers listed further designs for exclusion review that the tag had not caught (fixed-time survival rates, factorial and multi-randomisation designs, a platform trial); those are in the `trace_F*_notes.md` files.

**2026-10-09, rulings made, sponsor types corrected, sample drawn.** The study lead said to go with every recommendation above.

- **Design rulings** (`screening/design_rulings_2026-10-09b.csv`): the four traced non-inferiority designs are excluded, and so are the two candidates that are not cancer trials (NCT04047628, NCT03654053). The two trials in people who do not yet have cancer (NCT07609901, NCT06950385) are still his to rule on; neither is traced.
- **Sponsor corrections** (ADR-0016): ten companies the registry classes as "other" are industry-led. A wider read of sponsor names found ten, not the five first named. The list is `COMPANIES_THE_REGISTRY_CLASSES_OTHERWISE` in `universe.py`.
- **Tranche G**: the correction moved four untraced trials into the industry-led pool of the two years, which is traced in full, so they were traced (`trace_G.csv`) before the sample was drawn. The draw recipes for tranches E and F above reproduce at commit `2c618bd`, before the correction; after it the pool of trials that are not industry-led is smaller.
- **The sample is drawn** (`adjudication/reference/sample.json`: 40 trials, seed 20261009, from the 213 traced as read out or void). `adjudication/reference/worklist.csv` lists 46 trials for both adjudicators: the 40 and the six the trace left in doubt, without saying which are which.

**Figures now** (382 traced, provisional): 127 positive, 63 negative, 23 void, 158 with no readout found, 6 in doubt, 5 left out for their design. Industry-led 69.0% (116 of 168; overall survival 18 of 41, progression-type 98 of 126), 111 hazard ratios. Not industry-led 50.0% (11 of 22, 95% interval 30.7% to 69.3%), 17 hazard ratios.

**What is left: the adjudicators' readings, then the freeze.** `trialseal-reference freeze` now refuses for one reason only, the six trials in doubt; once both adjudicators have read the 46 it will also check that the trace matched them on nine in ten. Readings go in `adjudication/reference/adjudications.jsonl`. No trace may be added or re-checked from here on without redrawing the sample: a trial that joins the reference set after the draw makes the freeze refuse.

**Known limit.** The tool that records an adjudicator's reading (ticket 05's rules behind a command or form) is not built: readings can be recorded only through `record_adjudication` in code. That is the next thing the adjudicators need.

**2026-10-09, the adjudicators can now record.** `trialseal-adjudicate --set reference` is built (see ticket 05). A sampled trial for which both adjudicators search and find nothing is settled as such: it counts against the trace in the nine-in-ten check where the trace had a result, and as agreement where the trace had the trial ended without analysis. A trial in doubt is settled the same way when neither finds a source that states its result. Once `study/base_rates.json` exists the reference log takes no more entries.

**2026-10-09, after the third review.** `adjudication/reference/sample.json` now carries a mark of how each of the 213 trials it was drawn from was traced. I added the marks to the draw already made, after checking that the reference set and the 40 sampled trials are exactly what the draw recorded; the draw itself is unchanged. From here a re-check of any of those trials stops the freeze. If the adjudicators and the trace match on fewer than nine in ten, `trialseal-reference sample` lists every traced trial for them.

**2026-10-09, after the fourth review.** The freeze was the weakest part. Fixed with a failing test first:

- The trace is judged on the 40 sampled trials only. Below nine in ten on those, every trial traced with a result must be settled before the freeze; reading a few more that agree no longer gets round it.
- The sample is not drawn again once the reference log holds any entry, so deleting `sample.json` cannot refresh the marks of a changed trace.
- The freeze checks that the sample file is the seeded draw of 40 from the trials it names.
- The draw records the registry snapshot, and the reference set keeps to it: a later snapshot that reclasses a sponsor no longer moves it. It also records the trials in doubt, a mark for every traced trial, and where each one's design stood. After the draw, a trace, a re-check or a design ruling that changes a trial with a result or in doubt stops the freeze, saying which it was. A design ruling on a trial with no readout does not, since such a trial is in no figure and may yet be sealed.

`adjudication/reference/sample.json` was brought to this form in place, after checking that nothing has been adjudicated, that the reference set and the 40 are what the draw recorded, and that no trace mark has changed. The draw is unchanged; the snapshot recorded is `2026-10-08T090005`.

**Designs the tracers flagged.** I checked the 18 traced trials the tracers' notes flag for their design. Fourteen have no readout and are in no figure; two are in doubt and go to the adjudicators (the STAMPEDE platform and BIG-1); two count as negative results (NCT04504825 and NCT04512235, flagged for a win-ratio endpoint, which is not a ground for exclusion under ADR-0012). None is excluded, and the reference set stands as drawn.
