# Readout trace, sample C2 (28 trials) — notes

Traced 2026-10-08. Data: `trace_C2.csv` (one row per trial, same order as `sample_C2.csv`). Input: `sample_C2.csv`.

## Conventions used

Same as `trace_A_notes.md`. In particular:

- `first_disclosure_date` is the earliest source I could open and read, not necessarily the true first.
- A company announcement read from a mirror (SEC exhibit copy, news relay, society page) because the company site or Business Wire returns 403 is still `press_release`; the URL is the copy actually opened, and the note says so.
- A result that appears only as a sentence in a quarterly results release is `press_release` (FORTITUDE-102, KEYNOTE-866). KRYSTAL-10, which first surfaced as a line on a pipeline-changes slide, is `other`.
- `disclosed = no` rows that have simply not read out have a blank `primary_result`. Three trials stopped with no primary analysis are `disclosed = no`, `primary_result = terminated_no_analysis`.
- HR columns come from `hr_source_url`. Where that source gave no confidence interval the CI cells are blank and the CI, if seen elsewhere, is in `search_notes`.
- All 28 registry primary completion dates are full dates of type ACTUAL, so no month-only adjustment was needed.
- Summary statistics below use the 19 `disclosed = yes` rows only.

## Counts

| disclosed | n |
|---|---|
| yes | 19 |
| no | 9 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 12 |
| not_met | 5 |
| stopped_futility | 2 |
| terminated_no_analysis | 3 |
| blank (not read out) | 6 |

Of the 19 disclosed trials: 12 met (63%), 5 not met, 2 stopped for futility.

- met: MajesTEC-9, KEYNOTE-B15, BL-B01D1-307, LITESPARK-011, TALAPRO-3, VOLGA, ARO-013, KarMMa-3, POLARIX, DESTINY-Lung04, SAFFRON, HERIZON-GEA-01
- not_met: LATIFY, KRYSTAL-10, KEYNOTE-866, LAGOON, SGNB6A-002 (SigVie-002)
- stopped_futility: FORTITUDE-102, STAR-221
- terminated_no_analysis: BGB-A317-314, TIM, PACIFIC-8
- not read out: BGB-290-302, SAMETA, MK-6482-012 China extension, vorasidenib Asian study, CheckMate 9DX, RAINFOL-02

## Lag from registry primary completion date to first disclosure

- All 19 disclosed: median **41 days**, range **-1,725 to +104 days**.
- 6 of 19 (32%) were disclosed *before* the registry primary completion date (median -249.5 days): POLARIX (-1,725), KarMMa-3 (-1,342), STAR-221 (-259), HERIZON-GEA-01 (-240), ARO-013 (-116), LITESPARK-011 (-97). These are interim-analysis readouts or records whose registry date tracks final follow-up.
- The 13 disclosed after the registry date: median **63 days**, range 21 to 104.
- All registry dates in this sample are ACTUAL.

## Hazard ratios

- Numeric HR in the first disclosure: **2 of 19 (11%)** — MajesTEC-9 (topline release with HR and CI) and LAGOON (negative topline with HRs).
- A numeric HR for the recorded primary endpoint is public for 14 of 19. Delay from first disclosure to first HR: median **73.5 days** across all 14; median **85 days** (range 2 to 203) for the 12 where the HR came later.
- No numeric HR public yet for 5: FORTITUDE-102, KEYNOTE-866, VOLGA, SGNB6A-002, SAFFRON.
- Three HR sources gave no confidence interval (ARO-013, KarMMa-3, STAR-221); the CI cells are blank.

## Which source came first

| first source | n |
|---|---|
| press release (incl. mirrors and quarterly results releases) | 16 |
| exchange announcement (Shanghai) | 1 |
| conference presentation | 1 |
| other (investor presentation slide) | 1 |

Two of the 16 press releases were a sentence inside a quarterly results release, not a stand-alone announcement (FORTITUDE-102, KEYNOTE-866).

## Rows to treat with care

- **NCT04793958 (KRYSTAL-10)**: the first-disclosure date is the BMS Q1 2026 deck, which only lists the programme as removed from phase 3. The explicit "did not meet" came from a spokesperson quote I could not open and then from ESMO GI on 2 July 2026. If a stated result is required, the date is 2026-07-03.
- **NCT03250338 (ARO-013, crenolanib)**: dated to the ASH oral session; the abstract was probably online about five weeks earlier but could not be opened. The HR (0.64, no CI) comes from a trade article two days later. The trial randomised 106 of 276 planned.
- **NCT05211895 (PACIFIC-8)**: recorded `no` / `terminated_no_analysis` on AstraZeneca's statement that it was stopped because of results in other domvanalimab trials. Arcus gave no reason, and one automated summary says futility.
- **NCT05899049 (MK-6482-012 China extension)**: recorded `no`. The global LITESPARK-012 study failed at an interim analysis in April 2026; nothing public addresses the China extension record separately.
- **NCT05111626 (FORTITUDE-102)**: the written release says only "was stopped"; the futility reason rests on the earnings call as relayed by the partner's notice and trade press.
- **NCT03924856 (KEYNOTE-866)**: recorded `not_met` from one sentence about a prespecified interim analysis; the source does not say whether the trial was stopped. Earlier Merck filings (10-K, February 2026) were not checked.
- **NCT05152147 (HERIZON-GEA-01)** and **NCT05153239 (LAGOON)**: three-arm trials. The HR recorded is zanidatamab plus chemotherapy vs control (HERIZON) and lurbinectedin monotherapy vs control (LAGOON); the other arm's HR is in the notes.
- **NCT06382142 (BL-B01D1-307)**: first-disclosure date is from a Chinese news relay of the exchange notice (stamped 23 Feb); the exchange PDF was not opened.
- **HR dates a few days late**: TALAPRO-3 (source opened 2 Jun, presented 30 May), BL-B01D1-307 (2 Jun, release 31 May to 2 Jun), STAR-221 and KRYSTAL-10 (3 Jul, presented about 2 Jul), LATIFY (27 Mar, congress 25 to 28 Mar).
- **NCT02106572 (TIM)**: stopped for slow recruitment with follow-up completed; a descriptive result on 174 patients could still be published.
- **Not-read-out rows resting on absence of evidence**: BGB-290-302 (pamiparib), SAMETA, the vorasidenib Asian study, CheckMate 9DX and RAINFOL-02. For CheckMate 9DX and RAINFOL-02 a company document from July to October 2026 says data are still to come; for the other three nothing was found either way.
- **NCT03651128 (KarMMa-3)** and **NCT03274492 (POLARIX)**: the registry primary completion dates (April 2026) are 44 and 57 months after the readouts, which dominate the negative end of the lag range.
