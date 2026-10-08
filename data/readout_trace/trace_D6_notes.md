# Readout trace, sample D6 (25 trials) — notes

Traced 2026-10-09. Data: `trace_D6.csv` (one row per trial, same order as `sample_D6.csv`). Input: `sample_D6.csv`.

## Conventions used

Same as `trace_A_notes.md`. Points that mattered in this tranche:

- `first_disclosure_date` is the earliest source I could open and read. Three hazard-ratio dates and one first-disclosure date come from a conference abstract dated by its Crossref deposit (COREMAP, COSTAR Lung, AdvanTIG-302), which is probably about two weeks after the congress. One hazard-ratio date is a later company document because the congress coverage could not be opened (FORTITUDE-101).
- A result stated inside a quarterly results announcement is `press_release` (KEYNOTE-937, COSTAR Lung), as in tranche A.
- A win at an interim analysis with the trial continuing is `met` (MATTERHORN, FORTITUDE-101, LEAP-012, eXalt3, BL-B01D1-306, BRUIN CLL-322). EMPOWER-Lung 1 is `stopped_efficacy` because the monitoring committee recommended stopping the trial early.
- Dual primary endpoints where either suffices: one met is `met`, with the missed one named (LEAP-012: PFS met, OS later missed).
- Month-only registry dates were taken as the 15th (SHR-A1811-309, BL-B01D1-306, BRUIN CLL-322 among the disclosed rows).
- Summary statistics use the 15 `disclosed = yes` rows only.

**Search limit.** The session's shared web-search budget ran out about a third of the way through. After that I used only primary sources reached directly: SEC EDGAR full-text search and filings, Hong Kong exchange announcement lists and documents, ClinicalTrials.gov, PubMed, Crossref records of congress abstracts, and company or journal pages opened by URL. Rows that never had a web search, or had only one, are marked `confidence = low` and say so. No personal name or email address was sent in any request; SEC documents were read through a browser because sec.gov refuses scripted requests without a contact address.

## Counts

| disclosed | n |
|---|---|
| yes | 15 |
| no | 10 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 10 |
| not_met | 2 |
| stopped_efficacy | 1 |
| stopped_futility | 1 |
| unclear | 1 |
| blank (not read out, or nothing found) | 10 |

Of the 15 disclosed trials: 10 met (67%), 1 stopped early for efficacy, 2 not met, 1 stopped for futility, 1 unclear (COREMAP). None of the 10 `no` rows is a confirmed termination without analysis: 2 are confirmed as not yet read out by a recent sponsor filing (REGAL, fianlimab adjuvant melanoma, the latter guided to Q4 2026), 2 are described by the sponsor as ongoing or have no filing (pucotenlimab CRC, SHR2554-301), and 6 are absence of evidence on a light search.

## Lag from registry primary completion date to first disclosure

- All 15 disclosed: median **10 days**, range **-1,970 to +521 days**.
- 7 of 15 (47%) were disclosed *before* the registry date (median -239 days): eXalt3 -1,970, EMPOWER-Lung 1 -1,817, LEAP-012 -339, frontMIND -239, BRUIN CLL-322 -185, SHR-A1811-309 -64, AdvanTIG-302 -57. These are interim-analysis results or records whose registry date tracks final follow-up.
- The 8 disclosed after the registry date: median **104 days**, range 10 to 521 (FORTITUDE-101 10, BL-B01D1-306 11, COSTAR Lung 55, MATTERHORN 77, KEYNOTE-937 131, AMPLITUDE 147, FIGHT-302 318, COREMAP 521).
- By registry date type: ACTUAL (n=10) median 66 days; ESTIMATED (n=5) median -185 days.

## Hazard ratios

- Numeric HR in the first disclosure: **7 of 15 (47%)** — three press releases (AMPLITUDE, EMPOWER-Lung 1, frontMIND) and four congress abstracts or presentations (COREMAP, FIGHT-302, LEAP-012, eXalt3). The COREMAP number is for OS, not the registry primary endpoint.
- A numeric HR is public for 14 of 15. Delay from first disclosure to first HR: median **31 days** across all 14; median **127 days** (range 62 to 267) for the 7 where it came later (BRUIN CLL-322 62, MATTERHORN 86, SHR-A1811-309 106, FORTITUDE-101 127, COSTAR Lung 149, KEYNOTE-937 164, AdvanTIG-302 267). Three of those seven dates are late by two to three weeks for the reasons given under Conventions.
- No numeric HR public yet for 1: BL-B01D1-306.

## Which source came first

| first source | n |
|---|---|
| press release | 9 |
| conference abstract or presentation | 4 |
| exchange announcement (Shanghai notices: Hengrui, Sichuan Biokin) | 2 |

Two of the nine press releases were not stand-alone: KEYNOTE-937 is one sentence in Merck's Q2 2025 results release and COSTAR Lung one paragraph in GSK's Q2 2025 results. Both are negative, and neither had any other announcement before the congress presentation five months later. Both Shanghai notices are Chinese only, and the Hengrui one does not name the protocol.

## Rows to treat with care

- **NCT04914598 (COREMAP, Endostar)**: `yes / unclear`, confidence low. The only source is a congress abstract: no significant difference on the registry primary endpoint (puncture/drainage-free survival), but it names OS as a second primary and reports HR 0.807 (0.625-1.042), Peto P=0.0338, as "clinically meaningful" without saying it met its boundary. On the registry endpoint alone this is `not_met`. The HR cells are for OS. Date is a Crossref deposit date. Simcere's NDA was accepted in February 2026, so a Chinese-language statement of the result may predate the abstract.
- **NCT03656536 (FIGHT-302)**: `yes / met`, confidence medium. The trial was closed early for enrolment at 167 patients, then reported PFS HR 0.58 (0.39-0.87) with a P value the paper calls nominal. It could be argued as `terminated_no_analysis` or `unclear`.
- **NCT06110663 (HS-10241-301)**: `no`, confidence low. Hansoh's NDA for the same combination and population was accepted on 27 February 2026, but no document read says which study supports it or states a phase 3 result. Could become `unclear` or `yes` if a Chinese-language source names the trial.
- **NCT04246177 (LEAP-012)**: the 14 September 2024 date is the session date from a search summary; the article opened is dated 16 September. `met` is on PFS; OS, the other primary, was missed and the trial closed in October 2025. Eisai's quarterly materials were not checked for an earlier line.
- **NCT06199973 (SHR-A1811-309)**: the Hengrui notice gives no protocol number; matched by design and confirmed by the ASCO abstract, which cites the registry number.
- **NCT04497844 (AMPLITUDE)**: HR cells are the all-HRR population; three hierarchical primary populations exist. Johnson & Johnson's quarterly pipeline documents were not opened, only searched through SEC full text.
- **NCT05052801 (FORTITUDE-101)**: `met` at the interim (primary) analysis; the benefit attenuated at follow-up (HR 0.82, 0.62-1.08). `hr_first_public_date` is a later company document, about two to three weeks after the congress.
- **NCT04746924 (AdvanTIG-302)** and **NCT04655976 (COSTAR Lung)**: `hr_first_public_date` is a Crossref deposit date, about two weeks after the congress.
- **NCT04965493 (BRUIN CLL-322)**: Lilly's own release was not opened; the date and content come from two trade reports of it.
- **NCT03088540 (EMPOWER-Lung 1)** and **NCT02767804 (eXalt3)**: readouts of 2020 with registry dates in 2025; they dominate the negative tail of the lag distribution.
- **Light-search `no` rows — NCT03613181 (ANGLeD), NCT04834024 (MIL62), NCT05797831 (navtemadlin), NCT06241755 (BCG), NCT06182592 (CSPC bridging study)**: absence of evidence from a thin search, not proof. For the last three no web search was possible. Chinese-language sources were not searched for the BCG and MIL62 trials.
- **NCT06122389 (SHR2554-301)** and **NCT05652894 (pucotenlimab CRC)**: `no` rests on sponsor documents of August 2026 that list the trials without a result.
