# Readout re-check, batch R6 (12 trials) — notes

Re-checked 2026-10-09. Data: `rechecks_R6.csv` (one row per trial, in the order of the batch). Input: `recheck_sample_R6.csv`. Method: `TRACING_BRIEF.md` and `RECHECK_BRIEF.md`; conventions as in `trace_A_notes.md`.

Every row records only what was opened and read in this re-check; the first trace was used as a lead. `disclosed = no` rows have a blank `primary_result` and `hr_in_first_disclosure = no`, as in the earlier traces. `registry_pcd` is copied unchanged from the batch file, including the two month-only dates.

## Counts

| disclosed | n |
|---|---|
| yes | 2 |
| no | 10 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 2 |
| blank (not read out, or nothing public) | 10 |

| confidence | n |
|---|---|
| high | 11 |
| medium | 1 |
| low | 0 |

Lag from registry primary completion date to first disclosure, the 2 `yes` rows: 50 days (FIRST, actual date) and 107 days (XZP-3621, estimated date). Neither first disclosure carried a hazard ratio; both trials have one public now (FIRST 164 days after the headline result, XZP-3621 26 days after). First source: one press release (GSK), one exchange announcement (Sihuan Pharmaceutical, Hong Kong).

## What changed from the first trace

11 of 12 rows differ from the first trace.

- **`disclosed` changed, 1 row.** NCT05755048 (FS-1502): `unclear` to `no`. Nothing read hints at a result; Fosun still lists the product in its pipeline chart in Aug 2026 with no filing and no result.
- **First-disclosure date and source changed, 1 row.** NCT05204628 (XZP-3621): 2025-09-17 to 2025-08-22 (26 days earlier), source now Sihuan's approval announcement; confidence `low` to `medium`. Result (`met`) and hazard ratio (0.422, dated 2025-09-17) unchanged; the confidence interval is now filled in.
- **Confidence only, 9 rows** (`no` at low, now `no` at high after a real search): NCT05576272, NCT06548347, NCT06980272, NCT06082635, NCT05767892, NCT05132413, NCT06394492, NCT03002103, NCT06313983.
- **Unchanged, 1 row.** NCT03602859 (FIRST).

The two rows flagged "a model gave the right result with a date well before the traced one":

- **FIRST**: the traced date stands. GSK's results announcement of 30 Oct 2024 lists the readout as still anticipated in H2 2024, and full-text search of GSK's filings finds the trial's name nowhere before 20 Dec 2024.
- **XZP-3621**: an earlier disclosure was found (22 Aug 2025) and a still earlier one almost certainly exists that could not be opened (see below). The interim analysis that met the endpoint had a data cut-off of 8 Jan 2024, so a model recalling a positive result from 2024 is consistent with the record.

## Web searches

**13 of the 30 allowed** (XZP-3621 3, FS-1502 2, and one each for QL1706-302, TGRX-326, linperlisib, YK-029A, SHR-A1921, SHR-1701, SSGJ-707 and EndoTAG-1; none for FIRST or Hemay022). No search was refused and the allowance did not run out. Everything else came from direct fetches: the ClinicalTrials.gov API, Europe PMC, Crossref title queries, EDGAR full-text search, the Hong Kong exchange title-search service (Sihuan, Xuanzhu, Fosun, 3SBio, Hengrui, Simcere) and its listing-application index, cninfo (Hengrui), and the sponsors' own sites (Qilu, YingLi, Puhe, Xuanzhu, SynCore).

## Rows to treat with care

- **NCT05204628 (XZP-3621 / dirozalkib, DIAMOND-2)**: `yes / met`, confidence medium, and the date is the weak cell. The 22 Aug 2025 announcement says the pivotal phase III showed "significantly superior efficacy" but names neither PFS nor crizotinib; if a first disclosure must name the endpoint, the date is 17 Sep 2025 (the listing document, which gives the hazard ratio). The true first disclosure is probably Xuanzhu's first listing application of 25 Nov 2024, which the exchange has withdrawn and no archive holds; before that, Sihuan's annual results of 28 Mar 2024 say only that the trial "has achieved phased results". `met` is on an interim analysis (cut-off 8 Jan 2024) that the trial continued past; the AACR 2026 presentation reports HR 0.47, read in news reports of the company notice, not in the abstract itself.
- **NCT03602859 (FIRST)**: hazard-ratio date is that of the earliest coverage and of the paper's e-publication (2 June 2025); the congress session may have been a day earlier.
- **NCT06394492 (SHR-A1921-303)**: `no`, but the drug is in Hengrui's pipeline chart of Aug 2025 and absent from the 2025 annual report's pipeline tables and from the H1 2026 report. It may have been dropped without an analysis; no source says so. Hengrui issues no notices on trial endpoints, so a stopped or negative trial would not be announced.
- **NCT05132413 (SHR-1701-III-310)**: `no`. The lung indication has disappeared from Hengrui's pipeline (the Aug 2025 chart lists retlirafusp alfa for gastric cancer only); the registry record has not been touched since 2021. Same caveat as above. Two-stage design with a safety run-in.
- **NCT03002103 (EndoTAG-1, CT4005)**: `no` with a blank result rather than `terminated_no_analysis`: the registry says suspended, the sponsor's 2023 deck calls it a dose-safety trial, and its 2026 deck drops it, but no source says it was terminated. The two "termination" notices of 18 May 2022 that the first trace mentioned concern the pancreatic trial CTA68.
- **NCT05576272 (QL1706-302), NCT05767892 (YK-029A), NCT06548347 (linperlisib + CHOP)**: `no / high` rests on the registry, literature and conference-abstract searches, one web search each, and the sponsor's own news list, which was read in each case. All three sponsors are unlisted, so a negative or abandoned trial could go unannounced; China's CDE trial register was seen only through a third-party mirror or not at all. The linperlisib trial appears never to have started; the single-arm LINCH study (ASCO 2026) is a sibling.
- **NCT05755048 (FS-1502)**: `no` as of 9 Oct 2026, but the estimated completion date is 14 months past and Korean press in Jan 2026 called the trial "nearing completion"; this row can go stale quickly.
- **NCT06082635 (TGRX-326)**: `no`. The partner reports a pre-NDA submission in June 2026 without saying on which data; a pivotal single-arm phase 2 exists, so this is not read as a hint of a phase 3 result. Could also go stale quickly.
- **NCT06980272 (SSGJ-707)**: `no`; do not attach results of Pfizer's global phase 3s or of the phase 2 monotherapy study (ASCO 2026).
- **NCT06313983 (Hemay022)**: `no / high` from the group's own listing document (June 2026): enrolment not expected to finish until the end of 2026.

## What did not work

- **Lapsed Hong Kong listing applications cannot be read.** The exchange removes the documents of a lapsed or superseded application (the index keeps the entry with dead links). This blocked the two likeliest first-disclosure documents for XZP-3621 and Simcere Zaiming's application for TGRX-326. The Wayback Machine's index answered but held only error-page captures of those files.
- **Exchange titles are generic for mainland-listed sponsors.** Hengrui's and Fosun's Hong Kong notices carry titles such as "acceptance of a drug registration application" with no drug name, so each had to be opened (40 Hengrui notices via cninfo, 67 Fosun notices). cninfo's title search by keyword worked well for this.
- **Pipeline charts lose their columns as text.** Hengrui's and Fosun's charts show a drug's stage as a bar; the extracted text gives the drug and indication but not the phase, so "listed" is all that can be said from them.
- **Crossref title queries sorted newest-first fail for hyphenated drug codes** (QL1706, SHR-A1921, FS-1502, YK-029A): the match is loose and the newest 20 are unrelated. The same query in default relevance order, filtered to titles that contain the code, worked. Crossref returned one HTTP 429; EDGAR full-text search returned HTTP 500 on three queries and answered on retry.
- **Sponsor sites**: targetrx.com is another company's site and the TargetRx site (tjrbiosciences.com) has no readable news section; Xuanzhu's news list is loaded by a script but its underlying year query could be fetched; the SynCore decks sit behind a download-manager link that had to be found in the page source. sec.gov archive pages were read through the page-fetch tool, as in earlier batches.
- Web search for these small Chinese sponsors returned almost only registry mirrors, as earlier batches found; none of the 13 searches produced a first disclosure. The one earlier disclosure found (XZP-3621) came from reading the parent company's exchange announcements in date order.
