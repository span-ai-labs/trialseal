# Readout re-check, batch R3 (14 trials) — notes

Re-checked 2026-10-09. Data: `rechecks_R3.csv` (one row per trial, in the order of the batch). Input: `recheck_sample_R3.csv`. Method: `TRACING_BRIEF.md` and `RECHECK_BRIEF.md`. Every row records only sources opened and read in this re-check; the first trace was used as a lead.

## Conventions used

- As in `trace_A_notes.md`. A company announcement read from an SEC 6-K copy is `press_release`; a quarterly results release is also `press_release` (the trace A treatment); `exchange_announcement` is used for Hong Kong exchange filings.
- A trial that crossed its efficacy boundary at an interim analysis but was not stopped is `met` (AK104-302, ICP-CL-00111).
- One month-only registry date (NCT05118776, 2025-06) is taken as the 15th for the lag.

## Counts

| disclosed | n |
|---|---|
| yes | 7 |
| no | 6 |
| unclear | 1 |

| primary_result | n |
|---|---|
| met | 3 |
| not_met | 3 |
| unclear | 2 |
| blank (not read out) | 6 |

| confidence | n |
|---|---|
| high | 12 |
| medium | 2 |
| low | 0 |

Lag from registry primary completion date to first disclosure, the 7 `yes` rows: median 56 days, range -636 to +450; three were disclosed before the registry date (BURAN, AK104-302, CAPItello-290). A hazard ratio was in the first disclosure for 2 of 7 (COMPEL, ICP-CL-00111); one disclosed trial has no public hazard ratio yet (NILE).

## What changed from the first trace

Ten of 14 rows differ from the first trace in some cell; only one differs in the finding itself.

- **Result changed, 1 row.** NCT03682068 (NILE): `mixed` to `met`, on the rule that one of several sufficient primary endpoints is enough. Date and source are unchanged; the source type label changed from `exchange_announcement` to `press_release` by convention only.
- **Confidence raised with the finding unchanged, 8 rows.** Six `no` rows from `low` to `high` after a proper search (NCT05244642, NCT04884360, NCT06998108, NCT04834024, NCT05594927, NCT05868707); NCT04578613 from `low` to `medium`; NCT04765059 from `medium` to `high`.
- **Source address only, 1 row.** NCT05450692 (LATIFY): same announcement, read from the SEC copy.
- **Unchanged, 4 rows.** NCT04338399, NCT05008783, NCT03997123, NCT05118776.

No first-disclosure date moved. For the four rows flagged "a model gave the right result with a date well before the traced one" (BURAN, AK104-302, CAPItello-290, LATIFY) the traced date stands: in each case a dated company document from before the traced date still describes the result as awaited, or a complete list of the company's filings shows nothing earlier.

## Web searches

19 of the 30 allowed. Everything else came from direct fetches: the ClinicalTrials.gov API, Europe PMC, Crossref, EDGAR full-text search, the Hong Kong exchange title search (which lists every announcement of a company by date without a search), company results documents and news pages.

## Rows to treat with care

- **NCT03682068 (NILE)**: `met` on one of two dual primaries (durvalumab plus chemotherapy, PD-L1 high); the durvalumab plus tremelimumab comparison missed. The registry lists a single OS outcome. If both comparisons must succeed, this is `mixed`.
- **NCT04765059 (COMPEL)**: `yes / unclear`, confidence high for what was read, not for the coding. The paper states that no hypothesis test was done after enrolment was cut to 98 patients; the hazard ratio is 0.43 (0.27-0.70). It is neither `met` nor `not_met` under the rule as written; a reader could argue `met`. The first-disclosure date may be up to two days early (coverage page dated 6 Sept, paper dated 8 Sept 2025).
- **NCT05118776 (ASC40-301)**: `unclear / unclear`. The sponsor said only that it ended the programme "after analysis" of the phase 3 study; no document states a PFS or OS result. Confidence is medium because of what the source says, not because the search was thin.
- **NCT04578613 (ICP-CL-00111)**: `met`, but the date (25 Mar 2026) is probably late. The interim analysis was in May 2024, the filing accepted in Aug 2024 and the approval granted on 25 Apr 2025; eight sponsor documents between those dates state no result and no conference abstract was found. The Chinese label and Shanghai-only filings were not read. The source misnames the comparator.
- **NCT05008783 (AK104-302)**: the hazard ratio value 0.62 is from the sponsor's release of 8 Apr 2024; the coverage dated 7 Apr prints it rounded as 0.6 with the interval 0.5-0.78.
- **NCT04338399 (BURAN)** and **NCT05450692 (LATIFY)**: hazard ratio dates are those of the earliest coverage opened; the congress session day is not confirmed for BURAN.
- **NCT06998108 (BEBT-209 + fulvestrant)**: `no`, but the trial is absent from the sponsor's 2026 pipeline descriptions. It may have been dropped without an analysis; no source says so.
- **NCT04834024 (MIL62), NCT05868707 (OH2), NCT05594927 (BESTPOP), NCT05244642 (AK105-303)**: `no` rests on the registry, literature search, web searches and sponsor material (news reports of listing documents for MIL62 and OH2, the sponsor's own news pages for BESTPOP, five results announcements for AK105-303). The listing documents themselves were not opened, and three of the four sponsors are unlisted or newly applying, so a negative result could go unannounced.
- **NCT04884360 (MONO-OLA1)**: `no` as of 9 Oct 2026; the sponsor expects data in H2 2026, so this row can go stale within weeks.

## What did not work

- `www.sec.gov/Archives` refuses scripted requests that carry no contact address in the User-Agent. Filings were read through the page-fetch tool instead; `data.sec.gov` and EDGAR full-text search accepted a generic descriptive User-Agent.
- The Adlai Nortye investor site timed out; its releases were read from the newswire's company list and SEC filings.
- Europe PMC searched by registry number returns mostly reviews that cite the trial; title-field searches were needed to find the trial's own papers.
- Long documents read through the page-fetch tool are summarised in 100,000-character windows, so a 20-F took several calls to cover.
