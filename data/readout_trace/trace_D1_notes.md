# Readout trace, sample D1 (26 trials) — notes

Traced 2026-10-09. Data: `trace_D1.csv` (one row per trial, same order as `sample_D1.csv`). Input: `sample_D1.csv`.

## A limit on this tranche: web search ran out

The session's shared web-search budget was exhausted after about 25 searches, with roughly half the sample still untraced. The rest was traced by direct lookups only: sponsor sites, SEC EDGAR exhibits, the HKEX title search, the cninfo disclosure platform (Shanghai and Shenzhen notices, title and full-text search), PR Newswire company pages, PubMed and ClinicalTrials.gov. No general search engine, trade press search or conference abstract search was available for those rows. This matters most for the eight `no` rows and for NCT04578613 and NCT05919381, where a conference abstract or Chinese-language article may predate what I found. Rows affected say so in `search_notes`.

## Conventions used

Same as `trace_A_notes.md` and `trace_C1_notes.md`. Points that mattered here:

- `first_disclosure_date` is the earliest source I could open and read. One exception: SUCCESSOR-2 is dated 9 March 2026 from the sponsor's own Q1 results release, which lists that release by date; the release itself was not opened.
- Shanghai and Shenzhen notices are dated by the date printed on the notice; cninfo posts them the evening before.
- A win at an interim analysis with the trial continuing is `met`, not `stopped_efficacy` (SERENA-6, SACHI, AK104-303, DB-1303, SYS6010, BL-B01D1-301, SUCCESSOR-2, KEYNOTE-905, orelabrutinib).
- Dual primary endpoints where either suffices: `met` if one was met, both named in `which_endpoint` (ROSELLA, AK104-303, SUNMO, BREAKWATER).
- Month-only registry dates were taken as the 15th (NCT05919381, NCT06265428, NCT06382116).
- Summary statistics use the 18 `disclosed = yes` rows.

## Counts

| disclosed | n |
|---|---|
| yes | 18 |
| no | 8 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 15 |
| not_met | 2 |
| stopped_futility | 1 |
| blank (not read out, or nothing found) | 8 |

Of the 18 disclosed trials: 15 met (83%), 2 not met (LEAP-014, IOB-013), 1 stopped for futility (ARTISTRY-7). No terminations without analysis were established; SHR-A1921-303 may be one (see below).

## Lag from registry primary completion date to first disclosure

- All 18 disclosed: median **38 days**, range **-768 to +584 days**.
- 6 of 18 (33%) were disclosed before the registry date (median -183 days): interim-analysis wins (AK104-303, SACHI, SUCCESSOR-2, DB-1303, SERENA-6) and BREAKWATER's response-rate endpoint.
- The 12 disclosed on or after the registry date: median **70 days**, range 0 to 584. Nine of the 12 fall between 0 and 82 days. The two longest (gentuximab 584, orelabrutinib 450) are Chinese trials with stale, estimated registry dates, and the orelabrutinib date is probably late.
- By registry date type: ACTUAL (n=11) median 59 days; ESTIMATED (n=7) median 3 days.

## Hazard ratios

- Numeric HR in the first disclosure: **5 of 18 (28%)** — ARTISTRY-7, SUNMO, ROSELLA, IOB-013 (press releases) and orelabrutinib (annual results announcement).
- A numeric HR is public for 14 of 18. Delay from first disclosure to first HR: median **86 days** across the 14; median **97 days** (range 67 to 328) for the 9 where it came later.
- No numeric HR found for 4: gentuximab, DB-1303 vs T-DM1, SYS6010 (SYNSTAR-01), BL-B01D1-301.

## Which source came first

| first source | n |
|---|---|
| press release | 12 |
| exchange announcement (HKEX, SSE, SZSE) | 5 |
| other (FDA approval notice) | 1 |

Four of the 18 were not stand-alone announcements of the result: LEAP-014 is one sentence in Merck's Q2 2025 results release; SACHI was first stated inside an NDA-acceptance release; gentuximab inside an NDA-acceptance notice; orelabrutinib inside an annual results announcement. SUCCESSOR-2 was found only through a quarterly results table. Three first disclosures are Chinese-only or Chinese-exchange notices (gentuximab, BL-B01D1-301, and the SSE route for Hengrui that turned up nothing).

## Rows to treat with care

- **NCT04578613 (orelabrutinib, first-line CLL)**: confidence low. `2026-03-25` is the earliest explicit result I could open, 19 months after the NDA was accepted and 11 months after approval. Four InnoCare filings in between state no result. A conference abstract or Chinese-language report almost certainly came first.
- **NCT05919381 (gentuximab)**: matched to the Changchun High-Tech notice by design and size (CTR20220815, 754 subjects), not by registry number. An earlier congress abstract was not ruled out.
- **NCT04607421 (BREAKWATER)**: the row is anchored on the response-rate endpoint (FDA notice, 20 Dec 2024) but the HR cells are for PFS (topline 3 Feb 2025, HR 30 May 2025). Anchored on PFS the lag is -26 days.
- **NCT05552976 (SUCCESSOR-2)**: 9 March 2026 release not opened; date from the sponsor's Q1 2026 results release.
- **NCT05171647 (SUNMO)**: Roche's Q1 2025 sales release has no mention, but the slide deck and pipeline appendix were not opened; a 123-day lag leaves room for an earlier line.
- **NCT05092360 (ARTISTRY-7)**: `stopped_futility` is my reading of "highly unlikely to achieve success at the final analysis"; the registry says business decision. Could be `not_met`.
- **NCT04949256 (LEAP-014)**: `not_met` at an interim analysis after which the trial was closed; could be argued as `stopped_futility`.
- **NCT05257408 (ROSELLA)**: `hr_first_public_date` (4 Apr 2025) is the page I opened; the 31 Mar release reportedly carried the same HR. No CI in the row (0.54-0.91 came with the Lancet paper, 2 Jun 2025).
- **NCT06394492 (SHR-A1921-303)**: `no`, confidence low. The drug disappeared from Hengrui's pipeline tables between the H1 2025 and FY2025 reports with no statement. Likely a quiet discontinuation; if confirmed it would be `terminated_no_analysis`.
- **NCT04233151 (QL1203)**: `no`, confidence low. Private sponsor, stale registry, and only PubMed and the registry were checked.
- **NCT06371157 (AK104-308)**: `no` rests on matching it to Akeso's COMPASSION-29 ("enrolment ongoing", Aug 2026) by regimen.
- **Other `no` rows (NCT05922345, NCT06143553, NCT04342910, NCT05943795, NCT06300177)**: absence of evidence from sponsor filings, exchange notices, PubMed and the registry, without a general web or conference search.
- **AstraZeneca rows (CAPItello-281, SERENA-6)** and **KEYNOTE-905**: the sponsor's preceding quarterly results document was not opened to rule out an earlier line; all three had prompt stand-alone toplines.
- **NCT06382116 (BL-B01D1-301)** and **NCT05919381**: dated by the notice (18 Aug and 22 Jul 2026); each was posted the evening before.
