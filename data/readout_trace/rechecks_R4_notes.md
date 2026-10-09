# Re-check, batch R4 (14 trials) — notes

Re-checked 2026-10-09. Data: `rechecks_R4.csv` (one row per trial, batch order). Input: `recheck_sample_R4.csv`. Method: `TRACING_BRIEF.md` and `RECHECK_BRIEF.md`; conventions as in `trace_A_notes.md`.

Every row records only what was opened and read in this re-check. `disclosed = no` rows have a blank `primary_result` and `hr_in_first_disclosure = no`, as in the earlier traces. Month-only registry dates are copied as given.

## Counts

| disclosed | n |
|---|---|
| yes | 5 |
| no | 9 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 3 |
| not_met | 2 |
| blank (not read out, or nothing public) | 9 |

| confidence | n |
|---|---|
| high | 6 |
| medium | 8 |
| low | 0 |

## Lag, hazard ratios, sources (5 disclosed rows)

- Lag from registry primary completion date to first disclosure: median **64 days**, range **-546 to +197**. DESTINY-Gastric04 was an interim-analysis readout 18 months before an estimated registry date; the other four are 63, 64, 120 and 197 days after an actual date.
- Numeric HR in the first disclosure: **1 of 5** (POLARGO, a conference presentation). A numeric HR is recorded for 4 of 5; none could be confirmed for IMpower030.
- First source: press release 3 (one of them, ZEAL-1L, is two sentences inside a quarterly results announcement), conference 1, other 1 (a line on a pipeline slide, IMpower030).

## What changed from the first trace

10 of 14 rows differ from the first trace; no first-disclosure date and no result changed.

- **1 row, `disclosed` changed**: NCT04716114 (ALIVE) `unclear` to `no`. Nothing found hints at a result; the drug silently leaves CSPC's pipeline table after Aug 2023.
- **8 rows, confidence only** (`no` at low, now `no` at medium or high after a real search): NCT03912415, NCT05901935 (high), NCT06182592, NCT06241755, NCT06469879 (high), NCT03391934, NCT05566041, NCT05518318.
- **1 row, HR cells and confidence**: NCT03456063 (IMpower030). Date (2026-01-29) and result confirmed against Roche's documents of two consecutive quarters, confidence medium to high; the HR 0.77 (0.58-1.02) of the first trace is removed because no page I could open states it.
- **4 rows unchanged in substance**: NCT04704934, NCT05668988, NCT04475939, NCT04182204 (source URLs for POLARGO differ; same date, result and HR).

The five rows flagged "a model gave the right result with a date well before the traced one": **no earlier disclosure was found for any of them.** For four, the sponsor's own document of the preceding quarter or month was opened and shows the trial as not yet read out (AstraZeneca 6 Feb 2025 for DESTINY-Gastric04; Dizal exchange notices of 13 Jan and 28 Feb 2026 for WU-KONG28; GSK 5 Feb 2025 for ZEAL-1L; Roche 23 Oct 2025 for IMpower030). The fifth, POLARGO, stays open (see below).

## Web searches

**15 of the 30 allowed** web searches were used (POLARGO 3, FERMATA 3, IMpower030 2, and one each for REPLATINUM, ALIVE, KN-BCG-III, GLS-010-31, the CinnaGen trial, ZEAL-1L and HC1702-004). No search was refused and the allowance did not run out. Everything else came from direct fetches: ClinicalTrials.gov API, Europe PMC, Crossref, EDGAR full-text search, the HKEX title-search service (CSPC, Sino Biopharm), cninfo (Dizal, Gloria Pharma), and company documents (Roche, GSK, AstraZeneca, Daiichi Sankyo, EpicentRx, Biocad's trial page, the Iranian trial registry).

## Rows to treat with care

- **NCT04182204 (POLARGO)**: `medium`. Dated 14 Jun 2025 from coverage of the EHA plenary. The EHA abstract (S101) was very probably online about a month earlier, but I could not open a dated copy (EHA library not reachable, no full text in Europe PMC, PMC behind a CAPTCHA). Roche said nothing before the congress: its 24 Apr 2025 slides say only "data update at upcoming congress". If the abstract date can be confirmed, the first disclosure moves to mid-May 2025. The CI is from an ASCO Post report of the presentation published later (issue of 25 Jul 2025); the same-day source gives "0.6" with no interval.
- **NCT03456063 (IMpower030)**: the disclosure is bracketed between 23 Oct 2025 and 29 Jan 2026 by two Roche documents; 29 Jan is the first document that states it. HR cells are blank: four opened reports of the WCLC 2026 presentation give medians (62.8 vs 34.9 months) and "not statistically significant" but no hazard ratio.
- **NCT04704934 (DESTINY-Gastric04)**: coded `met` as before; the data monitoring committee "recommended unblinding the trial based on the superior efficacy" at a planned interim analysis, which a strict reading of the rule could code `stopped_efficacy`.
- **NCT05901935 (DP303c vs trastuzumab + chemotherapy)**: `no / high`. The DP303c phase 3 that CSPC reports (topline Aug 2025, SABCS 2025) is the sibling trial against T-DM1, NCT06313086. This registry number never left "not yet recruiting". Do not attach the sibling's result.
- **NCT06182592 (HC1702-004)**: CSPC's "database lock ... for bioequivalence clinical trials" (Apr 2025) most likely concerns its separate bioequivalence studies, not this OS study, but CSPC does not say which; the product then disappears from the 2026 documents. Bridging design: exclusion review.
- **NCT04716114 (ALIVE)**: reads as a discontinued programme, but no source says the trial was stopped, so it is not coded `terminated_no_analysis`.
- **NCT03912415 (FERMATA)**: Biocad's trial page says recruitment complete and study "Conducted"; Biocad's Russian news could not be read. A Russian-only disclosure is possible.
- **NCT06241755, NCT05518318, NCT03391934, NCT05566041**: `no / medium`: absence of evidence after registry, literature, one web search and what could be reached of the sponsor. For each, a channel in the sponsor's language (China's CDE register, Persian sources, SciClone) was not searched. The sponsor of NCT05518318 has been sold and renamed; the trial may never have started.
- **NCT03391934** and **NCT06182592** are equivalence or bridging designs to be reviewed for exclusion.

## What did not work

- **sec.gov archive pages** refused scripted fetches (HTTP 403, "undeclared automated tool") with a generic user agent that carries no contact address; EDGAR full-text search worked, and one filing could be read through the page-fetch tool. Company sites were used instead.
- **Script-rendered or blocked pages**: biocad.ru and dizalpharma.com news (empty shells), eng.biocad.ru (did not resolve), the Wayback Machine (429), PMC (CAPTCHA), two trade sites (403), one page returned empty.
- **cninfo full-text search** is not a strict phrase match: a query for a small sponsor's name returned unrelated filings. It worked well for listing a known company's notices by date.
- **Crossref free-text queries** were mostly noise; title-only queries on a drug name, newest first, were useful for conference abstracts.
- The HKEX title-search service needs the exchange's internal stock id (CSPC 2467, Sino Biopharm 6833), which its own prefix lookup returns.

## Sources of the journal figures

Hazard ratios for DESTINY-Gastric04, WU-KONG28 and ZEAL-1L were read from PubMed records: N Engl J Med, [doi 10.1056/NEJMoa2503119](https://doi.org/10.1056/NEJMoa2503119); N Engl J Med, [doi 10.1056/NEJMoa2604461](https://doi.org/10.1056/NEJMoa2604461); J Thorac Oncol, [doi 10.1016/j.jtho.2026.104087](https://doi.org/10.1016/j.jtho.2026.104087).
