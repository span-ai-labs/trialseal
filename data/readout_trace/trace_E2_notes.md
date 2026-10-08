# Readout trace, sample E2 (28 trials, non-company sponsors) — notes

Traced 2026-10-09. Data: `trace_E2.csv` (one row per trial, same order as `sample_E2.csv`). Input: `sample_E2.csv`.

## Search coverage: read this first

The web-search budget for the session ran out part-way through. Seven trials had a full search and were opened and read: MILES-3, BCG+MM, RAMIE, Precision Promise, S2302, A071801, Neotorch. Three more had one web search each before the budget ended (LOMAC, utidelone vs docetaxel, cadonilimab NPC). The other 18 were traced with a lighter search only:

- PubMed and Europe PMC (full text) by registry number;
- PubMed and Crossref by drug, design and acronym keywords (Crossref covers ASCO, ESMO, ASH, AACR and ESTRO meeting abstracts);
- the current ClinicalTrials.gov record.

For those rows there was **no sponsor news page, no trade press and no Chinese- or Japanese-language search**. They are `confidence = low`, or `medium` where the registry itself was updated recently enough to show the trial is still running. A `no` in this tranche is weaker evidence than a `no` in tranches A to C.

## Conventions used

Same as `trace_A_notes.md`. Points that mattered here:

- ASCO abstracts were read through the Crossref record of the abstract DOI (ascopubs.org returns 403 to scripts); the row gives the Crossref URL that was opened.
- A conference result is dated by the presentation day where a dated source confirms it, and `hr_in_first_disclosure = yes` where the presentation carried the hazard ratio even if the earliest item I opened did not print it (A071801; noted in the row).
- Month-only registry dates (MILES-3 2024-11, BCG+MM 2024-12) were taken as the 15th.
- Summary statistics use the 7 `disclosed = yes` rows.

## Counts

| disclosed | n |
|---|---|
| yes | 7 |
| no | 21 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 3 |
| not_met | 3 |
| stopped_futility | 1 |
| blank (not read out or nothing found) | 21 |

Of the 7 disclosed: 3 met (RAMIE, A071801, Neotorch), 3 not met (MILES-3, BCG+MM, Precision Promise), 1 released early for futility (S2302).

Of the 21 `no` rows: 2 have reached an actual primary completion date with no primary result public (DEC3-VEN, LOMAC), 1 never started (Burzynski DIPG), and 18 have stale or still-recruiting registry records with nothing found.

## Lag from registry primary completion date to first disclosure

- All 7 disclosed: median **-177 days**, range **-2,736 to +485 days**.
- 4 of 7 were disclosed *before* the registry date: MILES-3 (-2,736; registry still carries an estimated 2024 date for a trial reported in 2017), Neotorch (-1,187; interim win), Precision Promise (-1,106; first arm dropped for futility), S2302 (-177; interim futility release).
- The 3 disclosed after the registry date: +168 (BCG+MM), +288 (A071801), +485 (RAMIE; probably about +220 if the preprint counts, see below).
- By registry date type: ACTUAL (n=4) -1,187, -1,106, -177, +288; ESTIMATED (n=3) -2,736, +168, +485.

## Hazard ratios

- Numeric HR in the first disclosure: **5 of 7** (the four conference readouts and the RAMIE paper).
- The other two came later: Neotorch 93 days after the topline (ASCO Plenary Series abstract), Precision Promise 916 days after (and for a different arm than the first disclosure).

## Which source came first

| first source | n |
|---|---|
| conference abstract or presentation | 4 |
| press release (a partner company's, not the sponsor's) | 2 |
| journal paper | 1 |

No academic sponsor issued a topline release of its own before the data. The two press releases came from the drug companies attached to the trial (TYME for the Precision Promise SM-88 arm, Junshi for Neotorch).

## Rows to treat with care

- **NCT04158440 (Neotorch)**: the lead sponsor is Shanghai Junshi Bioscience, a company, in a tranche meant to be non-company. Traced anyway. Row is for EFS in the stage III population at the interim analysis; the registry has four primary outcomes. First-disclosure date is the Junshi release of 17 Jan 2023 as cited by OncLive on 18 Jan; the original was not opened.
- **NCT04229004 (Precision Promise)**: a platform trial with two arm-level readouts. The row is dated to the earlier one (SM-88 arm dropped for futility, 26 Jan 2022, TYME release), coded `not_met` at trial level, with the HR columns holding the **pamrevlumab** arm (FibroGen, 30 July 2024). The SM-88 arm never reached the phase 3 stage; if the trial is scored on the pamrevlumab comparison, first disclosure is 2024-07-30, HR in first disclosure, lag -190 days. No result found for the canakinumab + spartalizumab arm.
- **NCT03094351 (RAMIE)**: dated to the Lancet Gastroenterology & Hepatology paper (31 Mar 2026). An SSRN preprint with the same title and authors has a Crossref record created 2025-07-10, but SSRN was blocked and its abstract could not be read. The true first disclosure is probably about 8.5 months earlier. Non-inferiority design.
- **NCT01405586 (MILES-3)**: closed early for slow accrual; the only primary analysis is the joint analysis with MILES-4, reported at ASCO 2017. Coded `not_met`; `terminated_no_analysis` is arguable for MILES-3 alone. Dated by the JCO supplement issue date (20 May 2017), about three days after ASCO put abstracts online.
- **NCT05633602 (S2302)**: coded `stopped_futility` because the result was released when the second interim analysis crossed the futility boundary. Accrual was already complete, so `not_met` is a fair alternative. The final analysis (AACR, Apr 2026) agrees.
- **NCT04114981 (A071801)**: `met` with p=0.046 and an upper confidence bound of 1.00. The HR was read from coverage dated 2 Oct of the 28 Sept presentation; the two items dated 28 Sept that I opened give only the rates and p-value.
- **NCT02948543 (BCG+MM)**: `not_met` on a superiority design; the investigators present it as similar efficacy with fewer BCG doses. Session day is 1 or 2 June 2025.
- **NCT06073730 (DEC3-VEN)**: `no`, but response-rate interim data favouring the experimental arm were shown at ASH 2024 and ASH 2025. The primary endpoint (EFS) was explicitly not reported. Likely to read out at ASH in December 2026.
- **NCT03399110 (LOMAC)**: primary completion only eight weeks ago; ESMO 2026 abstracts were not yet available. Non-inferiority design.
- **Sibling trials that look like hits and are not**: PECORINO (NCT04937738) for the CUHK FLOT trial; ADVANCE (ChiCTR2000040590) for the Laibin aumolertinib trial; JCOG2101C PRESTIGE for the Kochi GS vs GnP trial; NCT05198609 (HAIC + apatinib + camrelizumab in PVTT) for TRIPLET-III; BCTOP-T-A01 for BCTOP-T-A02; the Flu-Mel vs Flu-Bu meta-analysis at ASH 2025 for the Wuhan conditioning trial.
- **The 16 `low` rows** (NCT04880746, NCT05313282, NCT05264896, NCT06095167, NCT05189067, NCT02062489, NCT05430399, NCT05427669, NCT05994339, NCT06664983, NCT05674539, NCT05268692, NCT05701436, NCT05236972, NCT04448522, NCT05044117): absence of evidence from bibliographic databases and the registry only. These are mostly Chinese hospital trials whose first disclosure, if any, would be a Chinese-language meeting (CSCO) or hospital news item. They need a proper web search in Chinese before being relied on.
