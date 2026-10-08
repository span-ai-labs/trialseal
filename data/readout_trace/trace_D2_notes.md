# Readout trace, sample D2 (26 trials) — notes

Traced 2026-10-09. Data: `trace_D2.csv` (one row per trial, same order as `sample_D2.csv`). Input: `sample_D2.csv`.

## Conventions used

Same as `trace_A_notes.md` and `trace_C1_notes.md`. Points that mattered in this tranche:

- **The web search allowance ran out after about 20 queries** (it is shared across tracers). From then on every source was reached directly: sponsor press-release and news index pages, SEC EDGAR company filing lists, the Hong Kong exchange title register, the Shanghai exchange and cninfo announcement lists, PubMed, Crossref and ClinicalTrials.gov. No search engine, reader, proxy or archive was used as a substitute. Rows whose search was thin for that reason are `confidence = low`.
- `first_disclosure_date` is the earliest source I could open and read. One row (DP303c) is knowingly about two months late for that reason; see below.
- Dual primary endpoints on the same comparison: one met is `met`, with the other named in `which_endpoint` (CHIPRO, KN026-001, OptiTROP-Breast03). SKYSCRAPER-14 missed PFS with OS immature and no trend: `not_met`.
- A win at an interim analysis with the trial continuing is `met` (PSMAddition, KN026-001, DP303c, RASolute 302, OptiTROP-Breast03). EMPOWER-Lung 3 was stopped on the committee's recommendation: `stopped_efficacy`.
- Six registry dates are month-only and were taken as the 15th.
- Summary statistics use the 12 `disclosed = yes` rows only.

## Counts

| disclosed | n |
|---|---|
| yes | 12 |
| no | 14 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 9 |
| not_met | 2 |
| stopped_efficacy | 1 |
| terminated_no_analysis | 2 |
| blank (not read out or nothing found) | 12 |

Of the 12 disclosed trials: 9 met and 1 stopped for efficacy (83% positive), 2 not met (both Roche: IMpassion132, SKYSCRAPER-14). The 14 `no` rows are 2 ended without a primary analysis (KarMMa-9, orelabrutinib + R-CHOP) and 12 with no result found, of which 5 have sponsor documents from late 2025 or 2026 showing the trial still running or unreported (ASCERTAIN, JSKN003-302, FDA018, sintilimab perioperative, BL-M07D1-301) and 7 rest on absence of evidence (FERMATA, SHR-1701-III-310, DIRECT, SURTORI-01, AK105-303, SHR-A1811-310, SSGJ-707).

## Lag from registry primary completion date to first disclosure

- All 12 disclosed: median **-6.5 days**, range **-1,302 to +514 days**.
- 6 of 12 (50%) were disclosed *before* the registry date (median -180 days): two old interim or primary readouts whose registry date tracks final follow-up (EMPOWER-Lung 3 -1,302; CodeBreaK 300 -713), IMpassion132 (-161), and three interim-analysis wins ahead of an estimated date (KN026-001 -199, RASolute 302 -63, OptiTROP-Breast03 -55).
- The 6 disclosed after the registry date: median **94.5 days**, range 42 to 514. The 514 is CHIPRO, whose registry record still shows a stale estimated date.
- By registry date type: ACTUAL (n=7) median 42 days; ESTIMATED (n=5) median -55 days.

## Hazard ratios

- Numeric HR for the primary endpoint in the first disclosure: **4 of 12 (33%)** — IMpassion132, CHIPRO and DP303c (conference data) and EMPOWER-Lung 3 (press release). RASolute 302 gave an HR in its first disclosure but for the overall population, not the registry primary population, so it is counted as no.
- A numeric HR is public for 11 of 12. Delay from first disclosure to first HR: median **19 days** across all 11; median **80 days** (range 13 to 170) for the 7 where it came later (TROPION-Breast02 13, camrelizumab + famitinib 19, RASolute 302 48, CodeBreaK 300 80, SKYSCRAPER-14 87, PSMAddition 139, KN026-001 170).
- No HR public yet for 1: OptiTROP-Breast03 (SKB264-III-11).
- Two HR rows have no confidence interval in the source read (KN026-001, RASolute 302).

## Which source came first

| first source | n |
|---|---|
| press release (incl. 8-K exhibits) | 6 |
| conference abstract or presentation | 3 |
| exchange announcement (HKEX, SSE) | 2 |
| other (Roche results-presentation pipeline appendix) | 1 |

Two of the 12 were not stand-alone announcements, and both were found only by reading quarterly documents: **CodeBreaK 300** is one sentence in Amgen's Q2 2023 results release (3 Aug 2023), 80 days before the ESMO and NEJM data that a conference-first search would have dated it by; **SKYSCRAPER-14** is one status line in Roche's HY2025 pipeline appendix, 87 days before ESMO. A third, the camrelizumab + famitinib cervical trial, was disclosed inside a filing-acceptance notice. Seven of the 12 first disclosures came from sponsors that do not file with the SEC (Roche x2, Chipscreen, Hengrui, Alphamab/JMT-Bio, CSPC, Kelun).

## Rows to treat with care

- **NCT06313086 (DP303c vs T-DM1)**: the date 2026-02-17 is the Crossref deposit of the published SABCS abstract, the only text I could open. The result was presented at SABCS in December 2025, so the true first disclosure is about two months earlier; an adjudicator with search access should replace the date. Matched by design, not by registry number.
- **NCT04921527 (CHIPRO)**: `met` on PFS; OS, the other dual primary, was not significant (HR 0.932). Arguably `mixed`. Lag of 514 days is against a stale estimated registry date.
- **NCT05015621 (SURTORI-01)**: `no`, confidence low. The trial was "ongoing" in HUTCHMED's July 2024 results and is absent from every results document since March 2025, with no explanation. Could be a quiet termination or an undisclosed failed analysis; I found nothing that says which.
- **NCT04736394 (ASCERTAIN)**: `no`, but the sponsor has said since February 2024 that "existing data" show similar recurrence-free proportions in the two arms. That is a descriptive remark on an enrolling trial, not a primary analysis; could be argued as `unclear`.
- **NCT06625320 (RASolute 302)**: HR cells hold OS in the RAS G12 population from the NEJM abstract (no CI there); the first disclosure's HR 0.40 was for the overall population. Coded `met` rather than `stopped_efficacy` because nothing read says the trial was stopped.
- **NCT06279364 (SKB264-III-11)**: matched to Kelun's OptiTROP-Breast03 release by design; the release gives no registry number.
- **NCT04906993 (SHR-1210-III-329)**: the first-disclosure notice names no protocol number (confirmed by the later Hengrui article). Hengrui says the endpoint was reached in July 2025; its half-year report of August 2025 was not checked and may carry an earlier line.
- **NCT03409614 (EMPOWER-Lung 3)**: the row describes Part 2 (cemiplimab + chemotherapy). The registry lists a Part 1 OS primary for which nothing was found. Release read in a reposted copy.
- **NCT05051891 (orelabrutinib + R-CHOP)**: `terminated_no_analysis` rests on the registry showing 3 patients enrolled and on the sponsor describing a different first-line MCL trial; no statement of why it stopped.
- **NCT05198934 (CodeBreaK 300)**: HR cells hold the 960 mg arm; the 240 mg arm (HR 0.58, 0.36-0.93) is in the note.
- **NCT05374512 (TROPION-Breast02)**: HR cells hold OS; PFS (HR 0.57, 0.47-0.69) is in the note.
- **Low-confidence "no" rows — NCT03912415 (FERMATA), NCT05132413 (SHR-1701-III-310), NCT05244642 (AK105-303), NCT06430437 (SHR-A1811-310), NCT06980272 (SSGJ-707)**: each had at most one web search, or none. FERMATA in particular may have a Russian-language disclosure I could not look for; Hengrui's exchange notices have generic titles and were not read individually. These five should be re-searched before being relied on.
- **NCT03899636 (DIRECT)**: `no` from one search and AngioDynamics filings to July 2026; its 8-K of 8 Oct 2026 was not read.
