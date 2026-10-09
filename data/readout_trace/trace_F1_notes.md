# Readout trace, sample F1 (14 trials) — notes

Traced 2026-10-09. Data: `trace_F1.csv` (one row per trial, in the sample's order). Input: `sample_F1.csv`. Method: `TRACING_BRIEF.md`, the search and confidence rules of `RECHECK_BRIEF.md`, and the lessons of `rechecks_R1_notes.md` and `rechecks_R2_notes.md`.

None of the 14 trials is led by a company: 6 Chinese hospitals or universities, 1 Korean hospital, 2 German and French centres, 2 UK academic sponsors, 1 US university and 1 US national institute. One is not a cancer trial (BEAT-MS, multiple sclerosis) and one is a platform of about ten comparisons (STAMPEDE).

## Conventions used

- As in `trace_A.csv`: a trial that has simply not read out has `disclosed = no`, a blank `primary_result`, `hr_in_first_disclosure = no` and blank date, hazard ratio and lag cells. A trial closed with no primary analysis is `disclosed = no`, `terminated_no_analysis`.
- `registry_pcd` and `registry_pcd_type` are copied unchanged from the sample, including six month-only dates. For the lag a month-only date is taken as the 15th (this affects one disclosed row, STAMPEDE).
- Every registry statement is from the ClinicalTrials.gov API record fetched on 2026-10-09. "Read" means I read the abstract or full-text passage myself. "Title seen" means a Crossref title only. A web search summary is named as such.
- ASCO abstracts were read through the Crossref record of the abstract's DOI (and OpenAlex, which repeats the text), because ascopubs.org refuses scripted fetches. `first_source_url` is the address actually fetched. The date of such an abstract is the supplement's online date as Crossref and OpenAlex give it, not the date ASCO first put the abstract on its own site; see the two rows below.
- "Crossref title scan" means: fetch the 200 to 500 most relevant Crossref records for a few title words within a date range, keep only titles containing the required terms, and read those titles.

## Counts

| disclosed | n |
|---|---|
| yes | 3 |
| no | 11 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 2 |
| mixed | 1 |
| terminated_no_analysis | 1 |
| blank (not read out) | 10 |

| confidence | n |
|---|---|
| high | 11 |
| medium | 3 |
| low | 0 |

First source type of the 3 disclosed: conference abstract 2, journal paper 1. No press release, exchange notice or cooperative-group news item was the first disclosure of any trial.

## Lag from registry primary completion date to first disclosure

- GAIN: **+230 days** (registry date actual, 2024-10-10; ASCO 2025 abstract).
- Tislelizumab in nasopharyngeal carcinoma (BEACON): **-731 days** (registry date estimated, 2026-06-02; interim analysis of the first of two primary endpoints at ASCO 2024).
- STAMPEDE: **-5,102 days** (registry date estimated, 2026-03; first arm-level readout 2012). This figure is an artefact of scoring a platform as one trial and should not enter a lag summary.
- Median of the three: -731 days; of the two ordinary trials, one is +230 and one is -731, so no summary is meaningful.

## Hazard ratios

- A hazard ratio was in the first disclosure for 1 of 3 (GAIN: OS HR 0.46, 95% CI 0.22-0.96).
- BEACON's reported primary endpoint is a complete response rate, so no hazard ratio applies; the PFS primary endpoint has not been reported.
- STAMPEDE's cells hold the first public overall survival hazard ratio I read (docetaxel comparison, ASCO 2015 abstract 5001, issue date 2015-05-20), not the failure-free survival figure of the 2012 paper.

## How confidence was given

`high`, disclosed (2): GAIN and BEACON. Each abstract was read in full, names the registry number and states the result of a primary endpoint.

`high`, not disclosed (9):

- completion date ahead or recent, registry shows no results and literature searches were empty: CRYOMUNE (2026-08, recruiting, a review of Aug 2026 calls it recruiting), BEAT-MS (2026-10, recruiting, record updated Sep 2026), APEX (2026-05), EMT2 (2025-11; trial unit said to expect results in 2026);
- a dated source or the registered design shows the primary analysis cannot have happened: NeoFOL-R (protocol paper of Feb 2026 says ongoing, started Feb 2024), HELEN-008 (still recruiting in Nov 2024, 1,979 patients, iDFS), the Fudan nasopharyngeal trial (enrolling in 2023, 2-year PFS), the Zhejiang gastric trial (half enrolled by Jan 2023, 3-year DFS endpoint);
- ended with five patients, stated in the registry results: the Wake Forest trial.

`medium` (3): STAMPEDE (result read, but the date is probably late by six months and the row is not really one trial), and the two cervical cancer trials (Sun Yat-sen and Shantou), where the completion date is past, the record is stale and Chinese domestic venues could not be searched.

## Web searches

10 of the 12 allowed were used (standard mode): EMT2 two; GAIN, BEACON, APEX, the Zhejiang gastric trial, the Sun Yat-sen cervical trial, the Shantou cervical trial, the Fudan nasopharyngeal trial and STAMPEDE one each (five in Chinese). None for NeoFOL-R, the Wake Forest trial, HELEN-008, CRYOMUNE, BEAT-MS. No web search found a disclosure that the indexes had not: the three disclosures and the three interim gastric abstracts all came from Crossref title scans. The GAIN search did surface two secondary reports of the ASCO 2025 abstract (one opened), and the second EMT2 search gave the "results due in 2026" statement in summary only. The search tool did not refuse or run out.

Sources used without a web search: ClinicalTrials.gov API (14 records, plus one sibling record); Europe PMC (by registry number for 13 trials, by title and investigator, abstracts of 6 papers, full-text passages of 7 papers citing the registry numbers); PubMed E-utilities (11 searches by design terms, acronym and investigator); Crossref (about 35 title scans, by subject and by investigator, and the full records of 8 abstracts, one of them without text); OpenAlex (abstract text and dates); the EU trial register search page (3 EudraCT numbers); SEC full-text search (EMT2).

## Rows to treat with care

- **NCT00268476 (STAMPEDE)**, `yes / mixed`, medium. A multi-arm multi-stage platform: celecoxib arms stopped for lack of benefit (2011-2012), docetaxel positive and zoledronic acid negative on OS (2015), abiraterone, M1 radiotherapy and abiraterone + enzalutamide (2017-2021, not re-read), metformin negative on OS (ESMO 2024; Lancet Oncol July 2025), transdermal oestradiol non-inferior on metastasis-free survival (ESMO 2024; NEJM March 2026). The row is dated to the earliest readout I could read (Lancet Oncol, online 2012-03-26); a congress abstract of the same title was deposited on 2011-09-23 and could not be opened, so the true first date is probably Sept 2011. The registry date of 2026-03 is an estimate on a record untouched since 2023 and matches none of the readouts. I would exclude this row from any per-trial scoring, or score it by comparison; if scored on the last comparisons, the first disclosures are the two ESMO 2024 late-breaking abstracts (deposited 2024-09-17, titles seen only).
- **NCT03673072 (GAIN)**, `yes / met`, high. The trial stopped recruiting for slow enrolment at 68 patients of a planned 300, and the reported OS analysis (62 patients, median follow-up 11.8 months, p=0.04) is called final. It is `met` on the abstract's own statement, but it is an early-closed, underpowered trial with no stated significance boundary, the same pattern as FIGHT-302 in an earlier tranche. Date 2025-05-28 is the Crossref deposit; ASCO's own release may be a few days earlier.
- **NCT05211232 (BEACON)**, `yes / met`, high. `met` is for complete response rate after induction, the first of two primary endpoints, tested at an interim analysis; the PFS primary endpoint is still unreported two years on, and the registry's completion date (2026-06-02) refers to it. Date 2024-06-01 is the supplement issue date; the Crossref deposit (2024-06-10) is after the meeting and was not used, and the true first public date is probably late May 2024. The trial name BEACON appears only in a 2026 review. A phase 2 at another institute (NCT05448885) has the same registry title.
- **NCT04135781 (Zhejiang, nab-paclitaxel + S-1 vs XELOX)**, `no`, high. Three interim abstracts (ASCO 2022, ASCO GI 2023, ASCO 2023) report 1-year DFS rates that favour the experimental arm, with no hypothesis test, while enrolment was at 146, 233 and 313 of 616. I did not count them as the primary analysis (3-year DFS rate), which the last abstract says was not reached. If the adjudicators count an interim descriptive report as a disclosure, the row becomes `unclear / unclear`, first date 2022-06-06 (Crossref deposit of abstract 4052). A web search summary gave the same reading.
- **NCT03867175 (Wake Forest, SBRT + pembrolizumab)**, `no / terminated_no_analysis`, high. The registry says completed, not terminated, and has results posted (2025-06-13), but with five patients and a statement that no statistical analysis is possible. Coded like the earlier trials closed with a handful of patients; the alternative coding is in the row's note.
- **NCT03468010 (Sun Yat-sen, adjuvant chemotherapy after chemoradiation)**, medium. Record never updated since Mar 2018; the trial may not have completed accrual. Nothing in PubMed, Europe PMC, the ASCO, ESMO and ASTRO supplements or a Chinese web search. Easy to confuse with OUTBACK, ACTLACC and the postoperative trials (STARS, JGOG1082).
- **NCT05189028 (Shantou, neoadjuvant chemotherapy vs chemoradiotherapy)**, medium. Single centre, status unknown. A 2025 PLoS One paper from the same group compares neoadjuvant chemotherapy plus surgery with chemoradiotherapy retrospectively and is not this trial.
- **NCT05674305 (Fudan, radiotherapy alone)**: non-inferiority design. The registry's completion date (2025-01-01) is not credible for a 2-year PFS endpoint in a trial still enrolling in 2023. A retrospective cohort from the same centre on the same question (Cancers 2023; ASCO 2023 abstract 6064) is not this trial. No investigator is named in the record, so the investigator search used the retrospective study's authors only as they appeared in title scans.
- **NCT03428477 (EMT2)**: the weakest of the high rows. The estimated completion date passed in Nov 2025 and the trial website could not be opened (403); "results due in 2026" is from a search summary. A result at ESMO 2026 (late October) or in a journal this autumn is plausible.
- **NCT04762459 (APEX)**: Hansoh's sponsored placebo-controlled trial ARTS (NCT04687241) is positive and published; it is not this trial. Hansoh's exchange filings were not read.
- **NCT05529940 (NeoFOL-R)**: the registry's completion date (2024-12) precedes the trial's own minimum follow-up; treat the date, not the finding, with care.
- **NCT04047628 (BEAT-MS)**: multiple sclerosis, not cancer. In the sample presumably because of the transplant procedure and a "relapse-free survival" endpoint; flag for exclusion.
- **Designs to flag for the exclusion review**: NCT05674305 (non-inferiority, stated in the registry summary); the STAMPEDE oestradiol comparison (non-inferiority); NCT04135781 and NCT05529940 (primary endpoint a survival rate at a fixed time); NCT04339218 (1-year OS rate).

## What did not work

- Web searches again added almost nothing: ten searches, no new disclosure. The search aimed at the ASCO 2024 abstract by its own figures and wording did not find it, although it exists.
- `ascopubs.org` was not fetched (known 403); `ace.asco.org` did not resolve and `meetings.asco.org` returned an empty script page, so ASCO's own release dates could not be read. Both ASCO first-disclosure dates in this batch are supplement dates and may be up to a week late.
- Elsevier supplement abstracts (ESMO late-breaking abstracts, the 2011 Eur J Cancer congress abstract) have no text in Crossref, OpenAlex or Semantic Scholar, and the publisher page redirects through a script; they were seen as titles only. This is why the STAMPEDE date is the 2012 paper, not the 2011 abstract.
- The EMT2 trial website (Leeds trials unit) returned 403 to both the script and the page-fetch tool. One trade article (MDedge) came back with a title and no body.
- Crossref relevance search is noisy for short acronyms (GAIN, EMT2, HELEN, STAMPEDE match unrelated titles); the scans needed a second required term. Requests were spaced four seconds apart and no rate limit was hit.
- Registry records are stale for 6 of the 14 (last updated between 2018 and Feb 2024), and at least two trials whose registry completion date is past are still running or in follow-up (NeoFOL-R, EMT2).
- Chinese domestic meetings and journals (CSCO, CSTRO, CNKI, Wanfang) are not reachable through any source used. That is the residual gap for the two medium cervical rows.
- One request to the SEC full-text search was sent with a placeholder contact (`admin@example.org`) in the User-Agent after the first, sent with a generic string, had already answered. It is not a personal address, but a generic string alone was enough and should be used.
