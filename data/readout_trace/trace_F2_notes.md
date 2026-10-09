# Readout trace, sample F2 (13 trials) — notes

Traced 2026-10-09. Data: `trace_F2.csv` (one row per trial, in the sample's order). Input: `sample_F2.csv`. Method: `TRACING_BRIEF.md`, with the search and confidence rules of `RECHECK_BRIEF.md` and the lessons of `rechecks_R1_notes.md` and `rechecks_R2_notes.md`.

All 13 trials are led by hospitals, universities, cooperative groups or a national institute: 5 in China, 2 run through the US NCI (Alliance, NRG), 1 each from Alliance Foundation Trials, the Children's Oncology Group, France, the Netherlands and 2 from Germany. Two have an industry funder that announced or co-announced a result (Pfizer for PATINA; Genentech funded ATOMIC but no company release was found).

## Conventions used

- As in `trace_A.csv`: a trial that has simply not read out has `disclosed = no`, a blank `primary_result`, `hr_in_first_disclosure = no` and blank date, hazard ratio and lag cells. A trial ended with no primary analysis is `disclosed = no`, `primary_result = terminated_no_analysis`.
- `registry_pcd` and `registry_pcd_type` are copied unchanged from the sample file, including the three month-only dates (NCT04909684, NCT02429700, NCT03697343). None of those three is disclosed, so no lag needed the 15th-of-month rule.
- Every registry statement in `search_notes` is from the ClinicalTrials.gov API record fetched on 2026-10-09. "Opened" means I read the passage myself. "Title only" means a Crossref or OpenAlex title. A web search summary is named as such.
- The date of a congress abstract is the date its supplement record went online in Crossref (creation date, or the issue date where the record was deposited later); each such row says which. I could not open ASCO's, ESMO's or ASH's own pages.
- "Crossref title scan" means fetching the few hundred most relevant Crossref records for a set of title words and reading only the titles that contain the required terms.

## Counts

| disclosed | n |
|---|---|
| yes | 4 |
| no | 9 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 2 |
| mixed | 1 |
| unclear | 1 |
| terminated_no_analysis | 1 |
| blank (not read out) | 8 |

| confidence | n |
|---|---|
| high | 10 |
| medium | 3 |
| low | 0 |

## Lag from registry primary completion date to first disclosure

Four disclosed trials: 58 days (PATINA), 117 (ATOMIC), 177 (LungTIME-C01) and -636 (BIG-1). Median 87.5 days; the three positive lags have a median of 117. All four registry dates are "actual". The negative lag is BIG-1, whose registry date (2025-07-30) falls 21 months after its main survival results were shown.

## Hazard ratios

All four first disclosures carried a hazard ratio for the primary endpoint (4 of 4). For BIG-1 the cells hold the hazard ratio of the induction comparison only; the consolidation comparison's hazard ratio came 19 months later in the paper. For LungTIME-C01 the cells hold a figure that has since been retracted.

## Which source came first

| first source | n |
|---|---|
| conference abstract or presentation | 3 |
| press release | 1 |

No registry record was the first disclosure. Two records have results posted (PATINA 2026-02-12, ATOMIC 2026-04-14), each more than a year after the result was public.

## How confidence was given

`high`, disclosed (2): PATINA and ATOMIC. The source was read, names the registry number or protocol, and no earlier disclosure was found.

`medium`, disclosed (2): LungTIME-C01 (the reported result was later retracted, so its classification is a judgement) and BIG-1 (which of several primary analyses counts is a judgement, and another registered primary outcome was disclosed three years earlier).

`high`, not disclosed (8):

- completion date recent or ahead: NRG-GY020 (2025-12-30), FSRT-Trial (2026-05), BCTOP-T-M01 (2026-05-01), ASCT2031 (2026-06-30), GP vs PF nasopharyngeal (2026-08-31);
- the design makes a primary analysis impossible by now: DEDICATION-1 (EU register: recruitment ended 2026-06-25, endpoint is 1-year overall survival) and AlloRelapseMM (terminated with 28 patients, endpoint is 5-year overall survival);
- searches by number, study name, drug plus condition and investigator all empty, and the likely venues searched: FAVORE.

`medium`, not disclosed (1): SCST-01. See below.

## Web searches

9 of the 12 allowed were used (standard mode): NRG-GY020 two, and one each for PATINA, ATOMIC, DEDICATION-1, LungTIME-C01 (the retraction), SCST-01 (in Chinese), ASCT2031 and FAVORE (in Chinese). Three were useful: PATINA (found the release and dated coverage), DEDICATION-1 (found coverage of the interim analysis) and LungTIME-C01 (found coverage quoting the retraction note). The other six returned registry mirrors and trial-listing pages. The search tool did not refuse or run out.

Sources used without a web search: ClinicalTrials.gov API (13 records); Europe PMC (by registry number, study name, investigator; full text of about 30 citing papers); the PubMed tools (four abstracts); Crossref (title scans and the full records of about a dozen abstracts and notices); OpenAlex (title and abstract searches, abstract text of ASH abstracts); the EU CTIS public API (DEDICATION-1); the NRG Oncology protocol page; the Dutch trial register; the Wayback Machine (one press release); Alliance Foundation Trials' news page; trade-press pages fetched by address.

## Rows to treat with care

- **NCT05549037 (LungTIME-C01): result `unclear`, retracted.** First reported at ASCO 2025 as a clear win on PFS (HR 0.43, 95% CI 0.31-0.60), then published in Nature Medicine (Feb 2026). The paper was retracted on 2026-06-24, the editors saying they "no longer have confidence in the integrity of the results" (quoted in a news article I opened; the note itself could not be opened), and the ASCO abstract was retracted on 2026-07-07. I recorded `unclear` rather than `met`. As first disclosed it was `met`; the adjudicators should decide which the study wants, or whether to exclude the trial. The hazard ratio cells hold the retracted figure. A commentary says the registered primary endpoint changed during the trial.
- **NCT05549037, the date.** 2025-05-28 is the creation date of the abstract's Crossref record. ASCO's regular abstracts are usually released some days before that; I could not confirm the release date on ASCO's site. If it was earlier, the date and the 177-day lag move by a few days.
- **NCT02416388 (BIG-1): `mixed`, and a judgement about what the primary analysis is.** The trial has four kinds of randomisation and three registered primary outcomes. I recorded the first disclosure of the two overall-survival analyses the trial is named for (ASH 2023): idarubicin vs daunorubicin, a superiority question, was not met (HR 1.04, 0.88-1.23); intermediate- vs high-dose cytarabine, a non-inferiority question, was met. If one sufficient endpoint is enough, this row is `met`, on a non-inferiority comparison. An earlier disclosure exists for a different registered primary outcome: the nested vosaroxin comparison at ASH 2020 (not met, phase 2 stage only). The GVHD comparison (ASH 2024) and the dexamethasone comparison (ASH 2025) were also not met. A multi-randomisation phase 2/3 with a non-inferiority arm: flag for the exclusion review.
- **NCT02416388, the date.** 2023-11-02 is the issue date of the Blood supplement in Crossref and OpenAlex; the Crossref record itself was created on 2023-12-01. The abstract does not print the registry number; the NEJM Evidence paper of the same analysis does.
- **NCT02912559 (ATOMIC), the dates.** The first disclosure date (2025-06-01) rests on an ASCO Daily News record whose title states the result; its page returned 403. The hazard ratio was read in the abstract's Crossref record, created 2025-06-04, so `hr_first_public_date` is three days later than `first_disclosure_date` although the hazard ratio was almost certainly shown at the plenary on 2025-06-01. The result came from the second interim analysis after accrual was complete; recorded as `met`, not `stopped_efficacy`.
- **NCT02947685 (PATINA).** The release is dated 2024-12-12 but its Business Wire address carries 20241211, and a SABCS press-programme file named with 12-11-24 could not be opened. The true first disclosure may be one day earlier.
- **NCT04909684 (DEDICATION-1): `no`, although an interim analysis is public.** ESMO 2024 (2024-09-14): 1-year survival 57.7% vs 55.0%, enrolment allowed to continue. I did not count this as the primary analysis. The 1-year survival figures in the abstract itself (seen only in a web search summary) differ slightly from those in the coverage I opened. Non-inferiority design. The ClinicalTrials.gov record is stale and its completion date (2024-11) is wrong by more than two years; the EU register has the current dates.
- **NCT02429700 (SCST-01)**, medium. Running since 2015, still "recruiting" on a record last touched in Apr 2023, completion date 17 months past. A 132-patient trial in a rare tumour led by an individual investigator could be reported in a Chinese-language journal, which is not reachable from here. A US randomised phase 2 of the same comparison (NRG/GOG-0264) has reported and is easy to mistake for it.
- **NCT03671252 (FAVORE)**, high on the rule but the weakest of the high rows: the record has not been updated since Jan 2019, so whether the trial enrolled as planned is unknown. Possibly non-inferiority.
- **NCT04214067 (NRG-GY020).** Completed 2025-12-30 with a 3-year endpoint and accrual closed in Aug 2022, so a result could appear at any meeting from now on. Nothing in the SGO 2025 or 2026, ASCO 2025 or 2026, IGCS or ASTRO supplements. The endpoint is a 3-year recurrence-free rate, classified as success or failure.
- **NCT05457556 (ASCT2031).** Only 66 patients, and the primary outcomes are worded as estimates within each arm. The trial may have closed early and may never report a comparison; the registry gives no reason. If so it belongs with `terminated_no_analysis`, but nothing I could open says that.
- **NCT05675319 (AlloRelapseMM).** `terminated_no_analysis` on the registry's own statement; no other source.
- **Designs to flag for the exclusion review**: DEDICATION-1 and BIG-1's cytarabine comparison (non-inferiority); FAVORE and SCST-01 (possibly non-inferiority, not stated); the nasopharyngeal trial (two active regimens, no stated hypothesis); LungTIME-C01 (a timing strategy, retracted); ASCT2031 (descriptive primary outcomes).

## What did not work

- Six of nine web searches returned only registry mirrors and trial-listing pages, as in earlier batches.
- Pages that refused a scripted fetch: businesswire.com and pfizer.com (403; the release was read from the Wayback Machine), annalsofoncology.org (403), ASCO Daily News (403), a Mayo Clinic news search (403), nature.com (redirect to a sign-in page, so the retraction note was not read). Two addresses given by web search no longer exist (a sabcs.org PDF and an ESMO abstract page, both 404). The Wayback Machine availability API returned 429 once; the archived page itself loaded.
- Crossref and OpenAlex hold no abstract text for the Annals of Oncology (ESMO) supplements, and Semantic Scholar had none for the one tried, so the ESMO 2024 abstract was read only through trade-press coverage. The SABCS 2024 late-breaking abstract is not in Crossref at all.
- Site searches on trade-press sites are rendered by script and return nothing to a plain fetch.
- Free-text Crossref queries are noisy: a short acronym that is also an ordinary word (PATINA, FAVORE, ATOMIC, DEDICATION) needs a second required term, and a required term such as "rectal" also matches "colorectal".
- Registry records: 5 of 13 are stale (last updated 2019 to early 2025), and one current record (BIG-1) gives an "actual" completion date long after its results. My own recollection of a meeting presentation for NRG-GY020 turned out to have no support in any source; nothing was recorded from memory.
- Chinese-language journals and domestic meeting abstracts are not reachable through any source used. That is the residual gap for SCST-01 and, less so, FAVORE.
