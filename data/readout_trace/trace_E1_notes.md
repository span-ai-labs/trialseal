# Readout trace, sample E1 (28 trials) — notes

Traced 2026-10-09. Data: `trace_E1.csv` (one row per trial, same order as `sample_E1.csv`). Input: `sample_E1.csv`.

## Conventions used

Same as `trace_A_notes.md`. Points that mattered in this tranche:

- The tranche is meant to be non-company sponsors, but four rows have a company as lead sponsor (Junshi x3: NCT03924050, NCT04085276, NCT06170489; Shouyao: NCT06254599). They were traced like the rest and are marked in the notes.
- `first_disclosure_date` is the earliest source I could open and read. Conference rows carry the usual uncertainty: FIRE-4 is dated by the Crossref deposit of its ASCO abstract (as in tranche C1); CASSANDRA, DREAM3R and Pola-R-ICE are dated by the earliest meeting coverage opened; IFM2017-03 is dated by the publication date of the ASH abstract.
- A trial closed for poor accrual with a handful of patients is `disclosed = no`, `terminated_no_analysis` (NCT05413915, ALPHABET). A trial that stopped accrual early but still reported its primary comparison is `not_met` (DREAM3R).
- CASSANDRA is a 2x2 factorial with two registry primaries. The row describes the first randomisation, disclosed first and met; the second was not met and is named in `which_endpoint`.
- Month-only registry dates occur only on `no` rows, so no mid-month assumption entered the lag figures.
- **Search limit.** The session's web search budget ran out after about 16 trials. The remaining rows were checked only against the registry record, PubMed, Europe PMC and Crossref, plus pages fetched directly. Those rows say so in `search_notes` and are `confidence = low`. All of them are `no` rows for small hospital or university trials whose registry records are stale.
- Summary statistics use the 7 `disclosed = yes` rows only.

## Counts

| disclosed | n |
|---|---|
| yes | 7 |
| no | 21 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 4 |
| not_met | 3 |
| terminated_no_analysis | 2 |
| blank (not read out or nothing found) | 19 |

Of the 7 disclosed trials: 4 met (KEYNOTE-483/IND.227, TORCHLIGHT, CASSANDRA, IFM2017-03), 3 not met (FIRE-4, DREAM3R, Pola-R-ICE). Confidence: 8 high, 9 medium, 11 low.

Of the 19 blank rows, 2 have a registry status of completed with nothing public (NCT03924050 Junshi CT25, completed Oct 2024; NCT05840341 QYHJ, completed Dec 2025); 1 has closed enrolment (NItCHE-MITO33); 1 is confirmed in follow-up by the sponsor (SY-3505); the other 15 are recruiting, not yet recruiting or status unknown, most with registry records untouched since 2021-2024.

## Lag from registry primary completion date to first disclosure

- All 7 disclosed: median **78 days**, range **-680 to +174 days**.
- 3 of 7 were disclosed *before* the registry date (-680, -661, -581 days; median -661): an interim-analysis win (TORCHLIGHT), a final-analysis topline (KEYNOTE-483) and a congress abstract (IFM2017-03), each with a registry "actual" primary completion date 19 to 22 months later.
- The 4 disclosed after the registry date: 78, 118, 121 and 174 days (median 119.5). All four are congress-first results with no topline release.
- All 7 registry dates are ACTUAL.

## Hazard ratios

- Numeric HR in the first disclosure: **4 of 7** (FIRE-4, CASSANDRA, DREAM3R, IFM2017-03), all conference abstracts or presentations.
- A numeric HR is public for all 7. For the three where it came later: KEYNOTE-483 85 days, TORCHLIGHT 104 days, Pola-R-ICE 1 day (an artefact of which coverage was opened; the HR there is a multivariable HR of 1.0 with no CI).
- FIRE-4 and Pola-R-ICE have no confidence interval in any source opened.

## Which source came first

| first source | n |
|---|---|
| conference abstract or presentation | 5 |
| press release | 2 |

The two press releases are the two trials with a company behind them: Merck for the CCTG trial, Junshi for its own. None of the five academic-group results had a topline release, a registry posting or a paper before the congress; DREAM3R's registry results were posted almost a year after ESMO.

## Rows to treat with care

- **NCT04793932 (CASSANDRA)**: `met` on the first randomisation (PAXG vs mFOLFIRINOX); the second randomisation (long vs short course), also a registry primary, was not met (paper 5 Sep 2026). `mixed` is arguable, by analogy with NILE in tranche B. Date is coverage of 1 Jun 2025; the presentation was probably 31 May.
- **NCT05063786 (ALPHABET)**: `terminated_no_analysis` is inferred from 27 enrolled of about 300 planned and an EU CTIS end date of 23 Dec 2025. No sponsor statement was found and the registry still says active, not recruiting.
- **NCT04833114 (Pola-R-ICE)**: dated 11 Jun 2026 from congress-day coverage; the EHA abstract was probably online some weeks earlier and was not found. HR cell is a multivariable HR without CI.
- **NCT02934529 (FIRE-4)**: dated 28 May 2025 from the Crossref deposit; ASCO probably had the abstract online about a week earlier. HR has no CI. Only 87 patients entered the randomisation that carries the primary endpoint.
- **NCT04334759 (DREAM3R)**: `not_met` although accrual stopped at 214 of 480 and the presenters called the result inconclusive. Could be argued as a terminated trial; I kept `not_met` because the primary OS comparison was reported with an HR.
- **NCT04085276 (TORCHLIGHT)**: `met` on the PD-L1-positive primary at an interim analysis; whether the ITT primary (HR 0.77, nominal p=0.0445) crossed its boundary was not verified. The exchange notice was not opened, only the company press release of the same day.
- **NCT02784171 (KEYNOTE-483 / IND.227)**: Merck's own page for the 10 Mar 2023 release was not found; the row cites same-day coverage quoting it.
- **NCT03924050 (Junshi CT25)**: completed two years ago with OS as primary and nothing public. `no` is absence of evidence; Junshi's full annual and interim reports were not opened, and a one-line mention there is the tranche C1 failure mode.
- **NCT05840341 (QYHJ)**: completed Dec 2025, nothing found; Chinese-language databases and CSCO abstracts were not searched.
- **NCT04679064 (NItCHE-MITO33)**: `no` on the strength of the MITO dashboard and empty databases; the ESMO 2026 programme (23-27 Oct) was not checked.
- **The 11 `confidence = low` rows** (NCT06089382, NCT05194878, NCT04338191, NCT06097416, NCT05527470, NCT04861558, NCT06441565, NCT05766605, NCT06485466, NCT05919030, NCT01917552): no general web or Chinese-language search was run because the search budget was exhausted. They rest on the registry, PubMed, Europe PMC and Crossref. A congress abstract at CSCO, a national meeting or a Chinese-language journal would not have been seen. These rows should be re-searched before adjudication.
- **NCT04829708 (PCI vs MRI)** and **NCT06254599 (SY-3505)**: `no` rests on a positive statement that the trial is still running (a protocol paper of Sep 2026; a company reply of Jun 2026), which is stronger than the other `no` rows.
