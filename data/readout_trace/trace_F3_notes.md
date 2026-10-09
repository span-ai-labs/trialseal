# Readout trace, sample F3 (13 trials) — notes

Traced 2026-10-09. Data: `trace_F3.csv` (one row per trial, in the sample's order). Input: `sample_F3.csv`. Method: `TRACING_BRIEF.md`, with the search limits and confidence definitions of `RECHECK_BRIEF.md` and the lessons of `rechecks_R1_notes.md` and `rechecks_R2_notes.md`.

The sample is trials not led by companies: cooperative groups (NSABP, CCTG, HOVON, SWOG/NCI, MASC Trials), universities and hospitals in Australia, China, India, the US, the UK and France. One row is in fact company-led: NCT06465446 (ImmuneOnco, listed in Hong Kong); its exchange filings were read.

## Conventions used

- As in `trace_A.csv`: a trial that has simply not read out has `disclosed = no`, a blank `primary_result`, `hr_in_first_disclosure = no` and blank date, hazard ratio and lag cells. A trial stopped for enrolment reasons with no primary analysis public is `disclosed = no`, `primary_result = terminated_no_analysis`.
- `registry_pcd` and `registry_pcd_type` are copied unchanged from the sample file, including five month-only dates. For the lag a month-only date is taken as the 15th (HOVON 156, 2025-10; COSI, 2026-05).
- Every registry statement in `search_notes` is from the ClinicalTrials.gov API record fetched on 2026-10-09. "Opened" means I read the passage myself in the page, abstract or full text. "Not opened" and "web search summary" are said where they apply.
- A meeting result read from trade-press coverage has `first_source_type = conference` and the coverage date. A meeting abstract read from its Crossref record has the supplement's online or issue date, and the URL given is the Crossref record I read.
- "Crossref title scan" means fetching the 100 to 400 most relevant Crossref records for a set of title words and reading only the titles that contain the required terms.

## Counts

| disclosed | n |
|---|---|
| yes | 5 |
| no | 8 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 1 |
| not_met | 4 |
| terminated_no_analysis | 3 |
| blank (not read out) | 5 |

| confidence | n |
|---|---|
| high | 11 |
| medium | 2 |
| low | 0 |

Of the 5 disclosed trials: 1 met (FINER), 4 not met (NSABP B-59, HOVON 156, COSI, the low grade glioma trial).

## Lag from registry primary completion date to first disclosure

- All 5 disclosed: median **-18 days**, range **-439 to +145 days** (-439, -193, -18, 8, 145).
- 3 of 5 were disclosed before the registry date. Two of those registry dates are estimates on stale or forward-dated records (NSABP B-59, COSI); the third is an actual date set 14 months after the result was presented (glioma trial).
- By registry date type: ACTUAL (n=2) 8 and -439 days; ESTIMATED (n=3) -193, -18 and 145 days.

## Hazard ratios

- Numeric hazard ratio in the first disclosure: **2 of 5** (NSABP B-59 and FINER, both meeting presentations).
- A hazard ratio is public for 3 of 5. HOVON 156 was a press release without numbers; the hazard ratio came 97 days later at a congress.
- No hazard ratio public for 2: COSI and the glioma trial report survival rates and log-rank p values only.

## Which source came first

| first source | n |
|---|---|
| conference (read from trade-press coverage dated the day of presentation) | 2 |
| conference (read from the abstract supplement record) | 2 |
| press release (collaborator and group jointly) | 1 |

No trial was first disclosed by a journal paper or by registry results. The one press release came from the industry collaborator (Astellas, with HOVON). The cooperative group news item found (CCTG, for FINER) could not be dated reliably.

## How confidence was given

`high`, disclosed (4): the source was opened, states the result and is plainly this trial. NSABP B-59, FINER and HOVON 156 coverage name the registry number; COSI is tied by trial name, sponsor group, design and numbers.

`high`, not disclosed (7):

- a registry record or opened source shows accrual ended early for enrolment reasons and no primary result is public anywhere searched: EAGLE FM, VAPOR-C, the Tata trastuzumab trial (record changed to terminated this week);
- the completion date is recent or just past and searches by number, acronym, drug plus condition and investigator were empty: S1418 (2026-08-03 actual), ONCOCOL01 (2026-09), IMM01-008 (2026-06, company filings read to 2026-10-06), Escape (2026-02-17).

`medium` (2): NACVCAC (nothing found, completion date well past, Chinese venues not searchable) and the glioma trial (result read, but see below).

## Web searches

11 of the 12 allowed were used (standard mode): NSABP B-59 1, FINER 1, S1418 1, HOVON 156 1, EAGLE FM 1, IMM01-008 1, Escape 1 (Chinese), NACVCAC 1 (Chinese), Tata 1, COSI 1, glioma 1. None for VAPOR-C and ONCOCOL01. Three found what the indexes could not: the two dated trade-press articles for the meeting presentations, and the HOVON 156 press release, which is in no literature index. The other eight returned registry mirrors and unrelated papers. The search tool did not refuse or run out.

Sources used without a web search: ClinicalTrials.gov API (13 records, including FINER's posted results); Europe PMC (by registry number for all 13, by acronym, three full texts); PubMed E-utilities and the PubMed tool (acronym, drug plus condition, investigator; four abstracts read); Crossref (title scans; full records of four meeting abstracts); OpenAlex (dates of the same four); the Hong Kong exchange filing index for ImmuneOnco (99 filing titles, five documents read); the web archive index (one page); direct fetches of four news pages and one group news item.

## Rows to treat with care

- **NCT04650581 (FINER), the date.** Recorded as 2025-05-31 from trade-press coverage of ASCO 2025 LBA1005. The CCTG news item announcing the result is stamped 23 May 2025, the same day as the registry's primary completion date, but it speaks of the ASCO presentation in the past tense and was first archived on 2025-06-01. If the stamp is right, the first disclosure is a group news item a week earlier, with no hazard ratio, and the lag is 0 rather than 8. The result is not in doubt.
- **NCT02455245 (carboplatin regimens, low grade glioma)**, medium. The abstract does not print the registry number; the match is by identical title, patient number and first author. The research arm (carboplatin alone) was significantly worse than standard in patients without NF1 (p=0.04) and not significantly different, on few patients, in those with NF1 (p=0.08). Recorded `not_met` for the research arm; a reader who treats the two strata as separate primary comparisons might call it `mixed`. The registry frames the question as whether the single agent "works as well as" the standard, with no margin. No hazard ratio exists. The abstract predates the registry's actual completion date by 14 months, so a later, fuller report may differ.
- **NCT04217278 (COSI), the date and the scope.** The date is the Blood supplement issue date, 2025-11-03; the Crossref record was created on 2025-12-04 (lag -162 if that is preferred). The abstract covers randomisations 2 and 3 (thiotepa conditioning), which hold 317 of the 333 patients. Randomisation 1 (Vyxeos) is closed and unreported. Phase II/III, three randomisations, one registered primary outcome across all of them.
- **NCT02166788 (EAGLE FM).** Accrual closed at about 100 of 634 patients (88, 98 and 101 in three papers). Follow-up continued on the monitoring committee's advice and the registry calls the trial completed, not terminated. No DFS result is public; an overall-survival comparison (p=0.49) is, in an economic paper. Recorded `terminated_no_analysis`; if a descriptive DFS report appears, this row changes. Non-inferiority design according to a web search summary.
- **NCT01785420 (Tata, preoperative trastuzumab).** The registry changed between the sample and the trace: recruiting with 2025-04 estimated in the sample, terminated with 2026-09-11 actual on 2026-10-09. The number enrolled over 13 years is not public, so an analysis of those enrolled cannot be ruled out later.
- **NCT04027309 (HOVON 156).** The press release is titled "confirm"; I did not look for an earlier mention in Astellas quarterly documents. The hazard ratio date is the coverage date and may be a few days late.
- **NCT03281954 (NSABP B-59).** The coverage article is dated 13 Dec 2024 and does not give the session day. The PubMed abstract of the 2026 paper prints the lower confidence limit as 0.062.
- **NCT06465446 (IMM01-008).** Company-led. The trial drops out of the company's August 2026 results announcement without explanation, and the registry record was never updated after registration.
- **NCT03011060 (NACVCAC)**, medium. Record untouched since January 2017; no trace of the trial anywhere after registration.
- **NCT02954874 (S1418).** Primary completion two months ago; a first report at a meeting this autumn would not yet be indexed. Three registered primary outcomes, two of them patient-reported.
- **Designs to flag for the exclusion review**: EAGLE FM (non-inferiority, surgery extent); the glioma trial (equivalence-type question); VAPOR-C (2x2 factorial, two primary comparisons, anaesthetic technique); COSI (phase II/III, three randomisations); S1418 (three primary outcomes).

## What did not work

- Web searches by trial name returned registry mirrors for eight of eleven trials. They worked only where a trade-press article or a company press release existed.
- The glioma and COSI results were found only by scanning Crossref titles on the drug names. Neither abstract prints a registry number, neither was returned by the PubMed or Europe PMC searches, and web searches aimed at each returned nothing.
- Crossref title relevance is noisy: several scans of 200 to 400 records returned no matching title at all, which is weak evidence of absence. Its date fields disagree for meeting abstracts (issue date against record creation date, a month apart for ASH).
- The printed SABCS abstract for NSABP B-59 holds no result, so the supplement record could not date or state the finding; trade-press coverage was needed.
- A cooperative group's news item carried a date stamp that its own text contradicts.
- Registry records: 6 of 13 were last updated in 2024 or earlier (one in 2017); four of the five disclosed trials have no results posted, and the registry completion date is more than four months away from the first disclosure in three of them. One record's change of status (Tata) was submitted three days before the trace and posted on the day of it.
- The EU trial register was not used: the two trials with an EU number had already been found.
- Chinese-language journals and domestic meetings remain unreachable; that is the residual gap for NACVCAC and, less so, Escape.
