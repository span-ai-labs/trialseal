# Readout trace, sample C1 (29 trials) — notes

Traced 2026-10-08. Data: `trace_C1.csv` (one row per trial, same order as `sample_C1.csv`). Input: `sample_C1.csv`.

## Conventions used

Same as `trace_A_notes.md`. Points that mattered in this tranche:

- `first_disclosure_date` is the earliest source I could open and read. Where the sponsor's own page was blocked, the row carries the reposted or same-day trade copy I did open and says so.
- Two ASCO 2026 abstracts (ATTRACTION-6, IBI310) were read through the Crossref record of the abstract DOI and are dated by its deposit date (27 May 2026). ASCO probably put them online about a week earlier.
- Dual primary endpoints tested on the same comparison, where either suffices: one met is recorded as `met`, with the missed one named in `which_endpoint` (STELLAR-303, CLARITY-Gastric01). Tranche B's `mixed` (NILE) was two different experimental arms, which does not occur here.
- A win at an interim analysis with the trial continuing is `met`, not `stopped_efficacy` (MagnetisMM-5, MonumenTAL-6, CheckMate 9DW, KEYNOTE-204).
- All 29 registry primary completion dates are ACTUAL and full dates; no mid-month assumption was needed.
- Summary statistics use the 19 `disclosed = yes` rows only.

## Counts

| disclosed | n |
|---|---|
| yes | 19 |
| no | 9 |
| unclear | 1 |

| primary_result | n |
|---|---|
| met | 8 |
| not_met | 10 |
| unclear | 2 |
| terminated_no_analysis | 4 |
| blank (not read out) | 5 |

Of the 19 disclosed trials: 8 met (42%), 10 not met, 1 unclear (IBI310). The second `unclear` is QUILT-2.023, which is also `disclosed = unclear`. The 9 `no` rows are 4 terminations without a primary analysis (MAGNOLIA, AIPAC-003, VERSATILE-003, KontRASt-02) and 5 not yet read out, of which two are scheduled for ESMO on 23-27 Oct 2026 (ENERGIZE, KEYNOTE-B49) and one is guided to Q4 2026 (DYNASTY-Breast02).

## Lag from registry primary completion date to first disclosure

- All 19 disclosed: median **62 days**, range **-2,144 to +346 days**.
- 5 of 19 (26%) were disclosed *before* the registry date (median -454 days; KEYNOTE-204, CheckMate 9DW, SKYSCRAPER-07, STELLAR-303, BURAN). These are interim-analysis wins, an early negative topline, or records where the registry date tracks final follow-up or a second primary endpoint.
- The 14 disclosed after the registry date: median **74.5 days**, range 35 to 346. Eleven of the 14 fall between 35 and 113 days; the tail is three congress-first results with no topline release (IBI310 147, ATTRACTION-6 219, IMpower030 346).

## Hazard ratios

- Numeric HR in the first disclosure: **5 of 19 (26%)** — EPCORE DLBCL-1, fianlimab, MonumenTAL-6 (press releases), ATTRACTION-6 (conference abstract), IMpower030 (conference; the number itself was not verified in an opened source, see below).
- A numeric HR is public for 12 of 19. Delay from first disclosure to first HR: median **74 days** across all 12; median **104 days** (range 72 to 179) for the 7 where the HR came later (KEYNOTE-204 72, CheckMate 9DW 76, persevERA 85, LIBRETTO-432 104, STELLAR-303 120, BURAN 143, SKYSCRAPER-07 179).
- No numeric HR public yet for 7: IBI310, KEYNOTE-975, LITESPARK-012, MagnetisMM-5, EMERALD-2, Krascendo 1, CLARITY-Gastric01.

## Which source came first

| first source | n |
|---|---|
| press release | 14 |
| conference abstract or presentation | 3 |
| exchange announcement (AstraZeneca results announcement) | 1 |
| other (trade press on a quarterly slide) | 1 |

Three of the 19 were not stand-alone announcements: KEYNOTE-975 is one sentence in Merck's Q1 2026 results release, EMERALD-2 a row in AstraZeneca's H1 2026 results, SKYSCRAPER-07 a pipeline change in Roche's Q1 2025 slides. All three are negative. Eight of the 29 trials have a lead sponsor that does not file with the SEC (Roche x4, Ono, Innovent, Arog, DualityBio); 6 of the 19 first disclosures came from them.

## Rows to treat with care

- **NCT03520686 (QUILT-2.023)**: `unclear / unclear`. The sponsor reported one registry primary (lymphocyte count) as significant and said nothing about PFS in a trial closed at 102 patients. Could be argued as `yes / met` on a strict reading of the registry, which would be misleading.
- **NCT04720716 (IBI310, HCC)**: `yes / unclear`, confidence low. The ASCO abstract gives medians and response rates that favour the combination but no HR, no p-value for OS and no statement that the primary endpoint was met; the dose was changed mid-trial and Innovent has since started a new phase 2/3 in the same setting.
- **NCT03456063 (IMpower030)**: the HR cells (0.77, 0.58-1.02) come from a search summary of a paywalled article, not an opened page. The result (`not_met`) and the date are from opened coverage. A silent removal from Roche's pipeline tables may predate the congress.
- **NCT04543617 (SKYSCRAPER-07)**: first disclosure rests on the opening lines of a paywalled ApexOnco article; the Roche slide was not opened. HR cells have no CI because the dated source I opened gave none (CI is in the note).
- **NCT05144854 (ATTRACTION-6)** and **NCT04720716**: dated 27 May 2026 from the DOI deposit; the true first public date is probably a few days earlier. The ATTRACTION-6 interval is a 95.8% CI.
- **NCT05425940 (STELLAR-303)** and **NCT06346392 (CLARITY-Gastric01)**: `met` on one of two dual primaries; the other was missed.
- **NCT04210115 (KEYNOTE-975)**: population described only as "certain patients"; Merck's 10-K and 10-Q were not checked for an earlier mention.
- **NCT05352672 (fianlimab)**: release dated 15 May 2026 in the copy I opened; two other outlets say 16 and 17 May.
- **NCT05171075 (MAGNOLIA)**: `terminated_no_analysis` rests on a Fierce Biotech article read only in a search summary. Its sibling ASTER was coded `stopped_futility` in tranche A; nothing found says MAGNOLIA was stopped on its own data.
- **NCT04628494 (EPCORE DLBCL-1)**: `not_met` on OS, the registry primary. Outside the US, PFS was a dual primary and was met.
- **NCT07226752 (EPCORE China sub-study)**: `no` because nothing China-specific was found; the global topline may be all that is ever reported.
- **NCT02684292 (KEYNOTE-204)** and **NCT04039607 (CheckMate 9DW)**: rows describe the interim readout of 2020 and 2024; the registry date is years later and no final-analysis disclosure was traced.
- **"no" rows for NCT03258931 (ARO-021), NCT03661320 (ENERGIZE), NCT04895358 (KEYNOTE-B49)**: absence of evidence from the acronym, study number, drug names and sponsor materials, not proof. The last two should resolve at ESMO within three weeks.

## Correction, 2026-10-08

A second check of five dates (prompted by a model that claimed to recall results the trace dated after its training cutoff) found four traced dates right and one late. **NCT03456063 (IMpower030)** was first disclosed on 2026-01-29 in Roche's FY2025 pipeline document ("Study did not meet primary endpoint Q4 2025"), not at the conference presentation of 2026-09-12. The row is corrected; the summary statistics above were computed before the correction. One late date in five checked is a reminder that a single reader's first-disclosure date can be months late when a result first appears as a line in a pipeline document.

