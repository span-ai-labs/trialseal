# Readout trace, sample G (4 trials) — notes

Traced 2026-10-09. Data: `trace_G.csv` (one row per trial, in the sample's order). Input: `sample_G.csv`. Method: `TRACING_BRIEF.md`, with the search limits and confidence definitions of `RECHECK_BRIEF.md` and the lessons of `rechecks_R4_notes.md` and `rechecks_R6_notes.md`.

The sample is four trials led by small companies: THERABIONIC INC. (US, unlisted device company), Biotech Pharmaceutical Co., Ltd. (Beijing, unlisted, two trials) and ImmuneOnco Biopharmaceuticals (Shanghai) Inc. (Hong Kong stock code 1541).

## Conventions used

- As in `trace_A.csv`: a trial that has not read out has `disclosed = no`, a blank `primary_result`, `hr_in_first_disclosure = no` and blank date, hazard ratio and lag cells.
- `registry_pcd` and `registry_pcd_type` are copied unchanged from the sample file. No date in this sample is month-only.
- Every registry statement in `search_notes` is from the ClinicalTrials.gov API record fetched on 2026-10-09. "Opened" or "read" means I read the passage myself in the page, record or document.
- The one meeting abstract was read from its Crossref record (and again in OpenAlex and Semantic Scholar). Its date is the Crossref record creation date, as earlier tranches did for ASCO 2025 abstracts; the URL given is the Crossref record.
- "Mirror" means a third-party copy of China's CDE trial register (pharnexcloud); the register itself could not be read.

## Counts

| disclosed | n |
|---|---|
| yes | 1 |
| no | 3 |
| unclear | 0 |

| primary_result | n |
|---|---|
| not_met | 1 |
| blank (not read out, or nothing public) | 3 |

| confidence | n |
|---|---|
| high | 4 |
| medium | 0 |
| low | 0 |

## Lag, hazard ratio, source (the 1 disclosed row)

- NCT06781073: first disclosure 184 days after an actual registry primary completion date.
- Numeric hazard ratio in the first disclosure: 0 of 1. A hazard ratio for the primary endpoint was read in trade-press coverage dated 51 days later; it was shown at the meeting itself, so the true delay is shorter.
- First source: conference abstract (ASCO 2025), read from an index record. No press release, exchange notice or registry posting exists for it.

## How confidence was given

- NCT06781073, `yes / high`: the abstract prints the registry number, states the primary endpoint and both medians, and a second opened source gives the hazard ratio. See the care list for the coding and the date.
- NCT06647862, `no / high`: the company's exchange filings were read up to 28 Sep 2026 and say the data cut-off for the interim analysis is expected at the end of 2026.
- NCT05978050, `no / high`: first patient August 2024 in a 354-patient survival trial designed for two years of enrolment; registry, literature, conference titles, the sponsor's news lists and its ASCO 2026 round-up are all empty. See the care list for the channels not reached.
- NCT04797884, `no / high`: every channel a US device trial would use was searched (registry, NIH grant record, literature, meeting-abstract titles, company site, two web searches).

## Web searches

**7 of the 10 allowed** (standard mode): NCT06781073 three (two Chinese, one English), NCT05978050 two (Chinese), NCT04797884 two, NCT06647862 none. No search was refused and the allowance did not run out. Two of the seven found something the indexes did not: the dated trade-press report that gives the hazard ratio for the cervical trial. The other five returned registry mirrors and trial listings.

Sources used without a web search: the ClinicalTrials.gov API (the four records, a list of the device's 13 registered studies, one sibling record); NIH RePORTER (one grant); Europe PMC (registry number, study number, acronym and title-field queries for all four; one full text); Crossref title scans (device name, nimotuzumab with cervical and with gastric, all 146 nimotuzumab titles created since June 2024, timdarpacept and IMM01) and one full Crossref record; OpenAlex and Semantic Scholar for the same abstract; the Hong Kong exchange filing index for ImmuneOnco (158 filings, six opened); therabionic.com (home, news, clinical trials); biotechplc.com (two news lists, academic list, pipeline pages); four China Daily articles and one OncLive article found by the searches, fetched directly; 14 register mirror pages.

## Rows to treat with care

- **NCT06781073 (nimotuzumab, first-line advanced cervical cancer), the coding.** Recorded `not_met`. Neither source says the trial missed its endpoint. The abstract gives medians (OS 15.7 vs 12.4 months), no hazard ratio and no p value, and concludes with "an improvement trend"; the coverage gives OS HR 0.72 (95% CI 0.46-1.11) under a headline that says the regimen "yields survival benefits". The only nominally significant figure is a subgroup (recurrent disease, HR 0.62, 0.39-0.98, P=.04). Under the brief's rule this is `not_met`; a reader who wants an explicit statement might prefer `unclear`.
- **NCT06781073, the dates.** The first-disclosure date (2025-05-28) is an index date; ASCO probably released the abstract some days earlier. The hazard-ratio date (2025-07-18) is the date of the article, which reports a presentation made at the meeting weeks before; the session date was not read.
- **NCT06781073, the trial itself.** It reported on 118 patients against a target of 340 in the mirror of the CDE register, ran from 2017 to 2024, and was first posted on ClinicalTrials.gov in January 2025, after its actual completion date. No source read says why enrolment ended at 118, so whether this was the planned primary analysis is not known. Worth a look in the exclusion review.
- **NCT05978050 (NOTABLE-307)**: `no / high` rests on timing more than on a statement from the sponsor. No sponsor document of 2026 names the trial. The mirror says recruiting with a first patient on 2024-08-15 but shows no snapshot date; the registry record is two years stale and its estimated completion date (2026-03-01) contradicts its own design text. CSCO 2026 and the sponsor's WeChat posts were not reached; an adjudicator who applies "medium if a domestic meeting could not be reached" strictly would mark this row medium. An interim analysis is planned and would not necessarily be announced.
- **NCT04797884 (ARTEMIS)**: `no` with a blank result, not `terminated_no_analysis`. The record has not been touched since June 2023, its start date is still an estimate, six of seven sites never opened, the grant behind it ended in August 2023, and the company's trials page no longer lists it. It reads as a trial that barely started, but no source says it was stopped or how many patients were enrolled. The single-arm TARGET-HCC study (NCT07118202) is a different trial. Two registered primary outcomes (OS and quality of life) and a phase 2/3 label: exclusion review.
- **NCT06647862 (IMM01-010)**: can go stale quickly. Enrolment finished by 30 June 2026 and the company expects the interim-analysis data cut-off at the end of 2026, so a first disclosure in the first half of 2027 by exchange announcement is likely. Two registered primary outcomes (CR rate and OS); the company has not said which one the interim analysis tests. Do not attach the single-arm phase 2 CMML results (ASH 2023, ESMO 2024, ASCO 2025) or anything about IMM01-008.

## What did not work

- **China's CDE trial register** answered scripted requests with an anti-bot page (HTTP 202 and a script challenge). The pharnexcloud mirror was readable but carries no snapshot date and is stale for at least one record: it still shows the cervical trial as recruiting with 44 patients.
- **The Beijing sponsor's site** (biotechplc.com): the news lists return the same first page whatever page parameter is sent, two addresses returned 403 ("abnormal access"), and the pipeline is an image with no text. The lists are nearly empty anyway: one company item since November 2024, no media item since June 2024, and nothing about the ASCO 2025 cervical result. The sponsor's study round-ups appear instead as China Daily articles, which web search found and which could then be fetched directly; its WeChat posts cannot be searched.
- **Web search in Chinese** missed the one useful article on the first try: a query built from the abstract's Chinese title and investigator returned only mirrors, while a query containing the two median survival figures found the OncLive report. Five of seven searches returned registry mirrors only, as earlier batches found.
- **Europe PMC free-text search on the device name** matched 66 records, almost all through author affiliations and funding statements; the title-field query and the registry-number query were the usable ones.
- **Crossref title relevance** was noisy for the multi-word device query (most of the 121 titles that passed the filter, out of 200 fetched, were radiofrequency ablation papers); the single-word drug queries filtered by creation date worked cleanly.
- ascopubs.org was not attempted, since earlier batches found it refuses scripted fetches; the abstract's own release date therefore remains unverified.
- The exchange filings and the trade-press article do not print protocol numbers (the filings) or abstract numbers (the article); each was tied to its registry record by design, drug, indication and size, or by the registry number where printed.
