# Readout trace, re-check batch R2 (13 trials) — notes

Re-checked 2026-10-09. Data: `rechecks_R2.csv` (one row per trial, in the batch's order). Input: `recheck_sample_R2.csv`. Method: `TRACING_BRIEF.md` and `RECHECK_BRIEF.md`, with the lessons of `rechecks_R1_notes.md`.

All 13 trials are led by hospitals or universities (12 in China, 1 in Ireland). None issues press releases. One has a listed company as collaborator (Beijing Biostar, for the utidelone trial), and its exchange filings were read.

## Conventions used

- As in `trace_A.csv`: a trial that has simply not read out has `disclosed = no`, a blank `primary_result`, `hr_in_first_disclosure = no` and blank date, hazard ratio and lag cells.
- `registry_pcd` and `registry_pcd_type` are copied unchanged from the batch file, including the one month-only date (NCT06097416, 2025-10).
- Every registry statement in `search_notes` is from the ClinicalTrials.gov API record fetched on 2026-10-09. "Opened" means I read the passage in the abstract or full text myself. "Title seen" means a Crossref or PubMed title only. A web search summary is named as such.
- "Crossref title scan" means: fetch the 400 to 800 most relevant Crossref records for a set of title words, then keep only titles containing the required terms (for example utidelone; or camrelizumab + apatinib + TACE) and read those titles. This reaches the ASCO, ESMO, ASH, SABCS and ASTRO supplement abstracts.

## Counts

| disclosed | n |
|---|---|
| yes | 1 |
| no | 12 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 1 |
| blank (not read out) | 12 |

| confidence | n |
|---|---|
| high | 11 |
| medium | 2 |
| low | 0 |

Lag, the one disclosed trial: 218 days from the registry's estimated primary completion date (2025-10-21) to the recorded first disclosure (2026-05-27); 212 days if the abstract went public on 2026-05-21, see below. The first disclosure carried a hazard ratio (1 of 1). First source type: conference abstract. No registry record has results posted and none gives a reason for stopping.

## What changed from the first trace

- **Finding changed in 1 row.** NCT06664983 (TPC + cadonilimab vs TPC, Sun Yat-sen): first trace `no`, now `yes`, `met` on PFS, HR 0.47 (95% CI 0.28-0.80), from ASCO 2026 abstract 6033 (the CONQUEST trial). The abstract's title says "chemotherapy" and "immunotherapy-refractory" where the registry says "TPC" and "anti-PD-1 resistant", and it carries a trial name the registry does not, so searches in the registry's words do not reach it. It was found from a German review of ASCO 2026 indexed in PubMed under cadonilimab + nasopharyngeal, then by a Crossref title scan.
- Finding unchanged in 12 rows (`no`, blank result).
- Confidence changed in all 13 rows: from `low` to `high` (11) or `medium` (2).

## How confidence was given

`high`, disclosed (1): NCT06664983. The abstract was read in full and names the registry number.

`high`, not disclosed (10): the registry shows no results and searches by registry number, acronym or study ID, drug plus condition, and investigator all came back empty, and one of these holds:

- the estimated completion date is recent or the record was recently updated: NCT05527470 (2025-11), NCT05674539 (2025-12), NCT05701436 and NCT05766605 (2026-01), NCT06441565 (2025-12), NCT05919030 (2026-07), NCT06485466 (2026-06, record updated Apr 2026 and still recruiting);
- the registered design makes a primary analysis impossible by now: NCT06095167 (3-year endpoint, start no earlier than 2024), NCT06097416 (5-year overall survival, never shown as recruiting), and also NCT05527470 (3-year endpoint, 440 patients, first patient Nov 2022);
- the completion date is well past but the likely venues were all searched: NCT05430399 (utidelone vs docetaxel), where every utidelone title in the ASCO, ESMO and SABCS supplements was read, the collaborator's exchange filings were read, and a paper of Aug 2025 calls the trial ongoing.

`medium`, not disclosed (2): NCT05994339 (Laibin) and NCT06089382 (Tongji). Completion date well past, record never updated after registration, and the likely venue could not be searched. See below.

## Web searches

10 of the 10 allowed were used (standard mode): NCT06664983 three (two for the abstract, one for the ASCO 2026 abstract release date), and one each for NCT05430399, NCT05919030, NCT06441565, NCT05994339, NCT06089382, NCT05701436 and NCT05674539 (six of these in Chinese). None for NCT05527470, NCT05766605, NCT06095167, NCT06097416, NCT06485466. No web search found a result: all returned registry mirrors or other trials, including the two aimed at the ASCO abstract already in hand. The search tool did not refuse or run out.

Sources used without a web search: ClinicalTrials.gov API (13 records); PubMed (E-utilities and the PubMed tools: number, acronym, drug plus condition, investigator; 9 abstracts read); Europe PMC (by registry number and study ID; 11 citing passages read in full text, a twelfth could not be opened); Crossref (title scans; the full record of the ASCO abstract); OpenAlex (the same abstract); the Hong Kong exchange filing index for Beijing Biostar (118 filing titles, three documents fetched).

## Rows to treat with care

- **NCT06664983 (CONQUEST), the date.** Recorded as 2026-05-27, the date the abstract's DOI record was created in Crossref. I could not open the abstract on ASCO's own pages. A third-party listing of the ASCO 2026 schedule says regular abstracts were released on 2026-05-21; if the adjudicators can confirm that on ASCO's site, the first disclosure date and the hazard ratio date should both move to 2026-05-21 and the lag to 212 days. The journal issue is dated 2026-06-01. The result itself is not in doubt.
- **NCT06664983, the endpoint.** The registry specifies PFS by independent review; the abstract says only PFS. The registry record has not been updated since Oct 2024 and still gives an estimated completion date. The trial name CONQUEST appears only in the abstract. Akeso's exchange filings were not checked for a mention on or after the abstract release.
- **NCT05994339 (Laibin, almonertinib + radiotherapy)**, medium. Last known status was "not yet recruiting" in Aug 2023 and no sites are listed; it may never have enrolled. A 40-patient single-hospital trial would most likely be reported in a Chinese-language journal, which is not reachable from here. The ADVANCE trial (ChiCTR2000040590, published 2026-09-21) has the same design and is easy to mistake for it. The registry summary names erlotinib where the arms name almonertinib.
- **NCT06089382 (Tongji, adjuvant sintilimab + lenvatinib)**, medium. Still "not yet recruiting" on a record untouched since Oct 2023. If it enrolled as planned, an RFS analysis in this population could have been reached by 2026 and shown at CSCO, which is not searchable. Nothing in ASCO, ESMO, PubMed or Europe PMC; a review of June 2026 still lists it without a result.
- **NCT05701436 and NCT05766605 (Zhujiang, assay-guided adjuvant TACE)**, high on the rule, but the weakest of the high rows: both records are stale since Mar 2023 with status unknown, the endpoint is only a 1-year DFS rate, and Chinese-language journals could not be searched. The two trials share an investigator and a control arm and differ only in the assay.
- **NCT05430399 (utidelone vs docetaxel)**: three sibling trials compare utidelone with a taxane (lung cancer, neoadjuvant breast, and a capecitabine combination). Biostar's interim announcement of 2026-08-26 reports a PFS advantage over docetaxel, but for the lung cancer trial; that is not this trial.
- **NCT06485466 (Sichuan, TACE + camrelizumab + apatinib)**: other randomised trials of the same triplet have reported (titles seen), against TACE alone or as phase 2; this trial's control arm is camrelizumab + apatinib. A retrospective cohort of the same comparison with the same investigator as co-author (CHANCE 2311, 2026) is not this trial.
- **NCT05919030 (RENMIN-236)**: one of the three reviews citing it (Future Oncol, Apr 2025) could not be opened.
- **Designs to flag for the exclusion review**: NCT05527470 and NCT06095167 (omitting concurrent chemotherapy, probably non-inferiority, not stated in the records); NCT05674539 (two active regimens, no stated hypothesis); NCT06441565 (primary endpoint is a 6-month PFS rate); NCT05701436 and NCT05766605 (a 1-year DFS rate, strategy trials).

## What did not work

- Web searches, again: 10 used, none found anything the registry and the indexes had not, and the two searches for the ASCO 2026 abstract by its exact title words did not find it although it exists.
- `ascopubs.org` returned 403 and the ASCO meeting site returned an empty page, so the abstract's own page and its release date could not be read. The Crossref record held the full abstract text, and OpenAlex repeated it.
- Searching by the registry's wording misses abstracts that rename the trial or reword the arms. Scanning every title that contains the drug name was what found the one disclosure.
- Crossref's relevance search is noisy and returned HTTP 429 after several large requests in a row; pausing a few seconds between requests fixed it.
- Europe PMC returned an error for one full text and holds no ASCO supplement abstracts (the abstract's DOI is not in it).
- Registry records are stale: 10 of 13 were last updated in 2023 or 2024, two in 2025 (NCT05674539 in Feb, NCT06441565 in July), and only NCT06485466 in 2026 (Apr). The one trial that read out still shows an estimated completion date and no results.
- Chinese-language journals and domestic meeting abstracts (CNKI, Wanfang, CSCO) are not reachable through any source used. That is the residual gap for the two medium rows and the two Zhujiang rows.
