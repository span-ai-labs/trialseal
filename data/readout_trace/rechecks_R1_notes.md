# Readout trace, re-check batch R1 (14 trials) — notes

Re-checked 2026-10-09. Data: `rechecks_R1.csv` (one row per trial, in the batch's order). Input: `recheck_sample_R1.csv`. Method: `TRACING_BRIEF.md` and `RECHECK_BRIEF.md`.

All 14 trials are led by hospitals, universities or academic groups (11 in China and Hong Kong, 1 each in Korea, Japan and Sweden). None issues press releases or exchange notices, so the search went to the registry record, the literature and conference abstract indexes.

## Conventions used

- As in `trace_A.csv`: a trial that has simply not read out has `disclosed = no`, a blank `primary_result`, `hr_in_first_disclosure = no` and blank date, hazard ratio and lag cells.
- `registry_pcd` and `registry_pcd_type` are copied unchanged from the batch file. Five of the 14 are month-only dates (YYYY-MM) and are left that way. No lag is computed because no trial is disclosed.
- Every registry statement in `search_notes` is from the ClinicalTrials.gov API record fetched on 2026-10-09. "Opened" means I read the passage in the full text or the abstract myself. Where only a title was seen (Crossref) or only a web search summary, the note says so.

## Counts

| disclosed | n |
|---|---|
| yes | 0 |
| no | 14 |
| unclear | 0 |

| primary_result | n |
|---|---|
| blank (not read out) | 14 |
| any result | 0 |

| confidence | n |
|---|---|
| high | 10 |
| medium | 4 |
| low | 0 |

No trial is disclosed, so there is no lag summary and no first disclosure carrying a hazard ratio. No registry record has results posted and none gives a reason for stopping.

## What changed from the first trace

- Finding: unchanged in all 14 rows. The first trace had `disclosed = no` with a blank result for every trial, and the re-check found the same.
- Confidence: changed in all 14 rows, from `low` to `high` (10) or `medium` (4). The first traces were made with the registry record, PubMed, Europe PMC and Crossref only. The re-check repeated those, added searches by investigator name, searches restricted to the ASCO, ESMO and ASH abstract supplements, reading of recent papers that cite each registry number, and web searches in English and in Chinese or Japanese.
- New since the first trace: for EFFIPEC the full text of the phase 1 paper could now be read, and it states that the randomised phase 3 part is ongoing.

## How confidence was given

`high` (10): a real search found nothing, the registry shows no results, and at least one of these holds: the estimated completion date is recent or not yet reached (CATALYSIS, the nasopharyngeal dose trial, CMHN, PACE); a dated source I opened says the trial is ongoing (EFFIPEC Oct 2026, nasopharyngeal trial Mar 2026, PACE Aug 2026, AFFORD Apr 2026); or the registry dates make a mature primary analysis implausible (FANTASTIC and the Hong Kong FLOT trial were still recruiting in late 2023 with a 3-year DFS endpoint; the Zhejiang stage I HER2 trial and the Sun Yat-sen neoadjuvant FOLFOXIRI trial started in 2021-2022 with 5-year and 2-year DFS endpoints).

`medium` (4): a real search found nothing, but the completion date is well past, the record is stale, and the most likely place for a first disclosure could not be searched directly. See below.

## Web searches

30 of the 30 allowed were used (standard mode), one to three per trial: CATALYSIS 2, tamoxifen 2, FANTASTIC 2, nasopharyngeal 2, EFFIPEC 1, cladribine-BEAC 3, CMHN 2, stage I HER2 2, neoadjuvant FOLFOXIRI 3, PACE 2, FLOT 2, Kochi 2, TRIPLET-III 3, AFFORD 2. None found a result. The search tool did not refuse or run out; searching stopped at the limit.

Sources used without a web search: ClinicalTrials.gov API (14 records), Europe PMC (by registry number, by keywords, full text of 14 papers), PubMed tools (keyword and investigator searches, abstracts), Crossref (general, and restricted to Journal of Clinical Oncology, Annals of Oncology and Blood for 2024-2026 meeting abstracts).

## Rows to treat with care

- **NCT05313282 (TRIPLET-III)**, medium. A 140-patient PFS trial with an estimated completion date of Nov 2024 and Hengrui as collaborator could well have read out. Nothing was found in PubMed, Europe PMC, the ASCO and ESMO supplements or in English and Chinese web searches, but Chinese meeting abstracts (CSCO) are not searchable from here. The published TRIPLET data are a single-arm phase 2 and retrospective comparisons. Two sibling randomised trials of the same regimen exist (NCT05198609, and the intravenous FOLFOX vs HAIC trial of ASCO 2024 TPS4193).
- **NCT04880746 (cladribine + BEAC)**, medium. Record never updated since May 2021; completion date two years past. EHA abstract books are not available as searchable text, and ASH was checked only through Crossref titles.
- **NCT05268692 (Kochi, GS vs GnP)**, medium. Record never updated since Mar 2022. Japanese society meeting abstracts are not indexed in the sources used. Three other Japanese GS vs GnP neoadjuvant trials exist and are easy to confuse with it (JCOG2101C PRESTIGE, CSGO-HBP-015, a Tohoku-led trial in patients aged 70-79).
- **NCT02062489 (tamoxifen, ER-beta positive)**, medium. Running since 2014, completion date May 2025, record stale since Apr 2022. The latest statement of status I could open is a Feb 2025 review calling it ongoing.
- **NCT05189067 (stage I HER2, Zhejiang)** and **NCT05427669 (AFFORD)**: the registry still shows an estimated start date or "not yet recruiting" from 2022. Either trial may have enrolled late or not as planned; `disclosed = no` holds either way. AFFORD was presented as a trial in progress at ASCO 2024 (title seen through Crossref only, the ASCO page returned 403).
- **NCT05194878 (neoadjuvant FOLFOXIRI, Sun Yat-sen)**: a July 2026 news item in Cancer about "no DFS benefit from neoadjuvant chemotherapy versus upfront surgery" is about the Scandinavian NeoCol trial, according to a web search summary; the item itself has no abstract and was not opened.
- **NCT04448522 (reduced-dose radiotherapy)**: the design looks like non-inferiority (equal control, less toxicity); flag for the exclusion review. A sibling Sun Yat-sen trial, NCT05304468 (60 vs 70 Gy), was seen in search listings only.
- **NCT04338191 (FANTASTIC)**: a Japanese phase 2 of the same name (mFOLFOXIRI after metastasectomy) has ESMO 2024 and 2025 abstracts; they are not this trial.
- **NCT04861558 (EFFIPEC)**: the phase 1 paper does not print the registry number; it is tied to this record by the acronym, the sponsor group and the cited protocol (PMID 38437211).

## What did not work

- ASCO pages: `ascopubs.org` returned 403 and `ace.asco.org` did not resolve, so ASCO abstracts were seen as Crossref titles only. One institutional repository page returned 404.
- Europe PMC returns no full text for meeting abstract books (EHA, UEG, Japanese Cancer Association), so its keyword hits inside them could not be checked and count as noise.
- Europe PMC keyword searches run over full text and return mostly reviews; PubMed title and abstract searches and Crossref title searches were the usable ones.
- Web searches by registry number return registry mirror sites almost exclusively. For this kind of trial they added nothing beyond the registry record and the literature indexes.
- Registry records are stale for 13 of the 14 trials (12 last updated in 2020-2023, one in Feb 2024); only EFFIPEC was updated in 2025. Status and dates from the registry say little about whether a trial has read out.
- Chinese and Japanese domestic meeting abstracts (CSCO, Chinese haematology meetings, JSCO) are not reachable through any source used. That is the main residual gap for the four medium rows.
