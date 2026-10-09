# Re-check, batch R5 (14 trials) — notes

Re-checked 2026-10-09. Data: `rechecks_R5.csv` (one row per trial, batch order). Input: `recheck_sample_R5.csv`. Method: `TRACING_BRIEF.md` and `RECHECK_BRIEF.md`; conventions as in `trace_A_notes.md` and `rechecks_R4_notes.md`.

Every row records only what was opened and read in this re-check. `disclosed = no` rows have a blank first-disclosure date and `hr_in_first_disclosure = no`, as in the earlier traces. `registry_pcd` is copied from the batch file unchanged, month-only where it is month-only.

## Counts

| disclosed | n |
|---|---|
| yes | 5 |
| no | 8 |
| unclear | 1 |

| primary_result | n |
|---|---|
| met | 4 |
| not_met | 1 |
| unclear | 1 |
| terminated_no_analysis | 2 |
| blank (not read out, or nothing public) | 6 |

| confidence | n |
|---|---|
| high | 5 |
| medium | 9 |
| low | 0 |

## Lag, hazard ratios, sources (5 disclosed rows)

- Lag from registry primary completion date to first disclosure: median **147 days**, range **27 to 506**. The two longest (485 and 506 days) are trials whose result surfaced only as a preprint or a congress poster more than a year after the data cutoff. The `unclear` row (QUILT-2.023, 92 days) is not in the summary.
- Numeric HR in the first disclosure: **3 of 5** (a preprint and two congress abstracts). A numeric HR is public for the same 3; none for CELESTIMO (topline only) or the IBI310 trial (medians only).
- First source: congress abstract 3, press release 1, other 1 (a preprint). None of the five was first disclosed in an exchange notice or a results announcement.

## What changed from the first trace

13 of 14 rows differ from the first trace.

- **3 rows, `disclosed` changed**
  - NCT06759857 (FHND9041 vs afatinib): `no` to `yes / met`. A Research Square preprint posted 2 Jul 2026, found through Europe PMC by registry number.
  - NCT04233151 (QL1203): `no` to `yes / met`. ASCO GI 2025 abstract 190, found by a Crossref title query on the drug code. This disclosure is 20 months old.
  - NCT03008148 (JP001): `unclear` to `no`. Nothing found hints at a result.
- **2 rows, result changed** (disclosed stays `yes`)
  - NCT04720716 (IBI310, HCC): `unclear` to `met` on ORR, confidence low to medium. Same abstract, same date.
  - NCT04914598 (COREMAP): `unclear` to `not_met`, confidence low to medium, date 16 Jul to 1 Jul 2026.
- **2 rows, `no` now labelled `terminated_no_analysis`**: NCT05797831 (navtemadlin, endometrial; low to high) and NCT05254171 (ASPIRE; low to medium). Both rest on the EU trial register, which records an early termination by sponsor decision that ClinicalTrials.gov does not show.
- **5 rows, confidence only** (`no` at low, now `no` after a real search): NCT05015621, NCT06110663, NCT05751850 (medium); NCT06430437, NCT02546102 (high).
- **1 row, same coding with new evidence**: NCT03520686 (QUILT-2.023) stays `unclear / unclear`, dated 13 Jan 2026, medium. The source is now the company's own page, and a PFS figure for a subset has since been published (see below).
- **1 row unchanged**: NCT04712097 (CELESTIMO).

The one row flagged "a model gave the right result with a date well before the traced one" is CELESTIMO. **No earlier disclosure was found.** Roche's half-year document of 23 Jul 2026 still lists CELESTIMO among the readouts expected in 2026, so the first statement falls between 23 Jul and 17 Sep 2026, and the 17 Sep release is the first document found.

## Web searches

**18 of the 30 allowed** web searches were used: COREMAP 3; SURTORI-01, HS-10241-301 and JP001 2 each; one each for FHND9041, HR070803-301, navtemadlin, ASPIRE, ICT-107, QL1203, SHR-A1811-310, the IBI310 trial and CELESTIMO. No search was refused and the allowance did not run out. Everything else came from direct fetches: ClinicalTrials.gov API, the EU register's public API, Europe PMC, Crossref, OpenAlex, Semantic Scholar, EDGAR full-text search, the HKEX title-search service (Innovent, Hansoh, Hengrui, Simcere, HUTCHMED, Sino Biopharmaceutical), company sites (Roche, ImmunityBio, Hengrui, Kartos, Johnpro), and the browser pane for publisher pages.

## Rows to treat with care

- **NCT03520686 (QUILT-2.023)**: `unclear / unclear`. The sponsor's own documents disagree about what was analysed. The January 2026 release says the primary endpoint was PFS, enrolment closed early, and reports only the lymphocyte-count result (p=0.0065). The ASCO 2026 abstract says 98 subjects "were unblinded for exploratory analysis", calls the findings interim and says enrolment is ongoing, while the registry says terminated with 102 enrolled. That abstract reports PFS for the PD-L1 TPS ≥50% subset only (about 45 patients): HR 0.40 (0.17–0.94), p=0.0298; nothing for the second hierarchical step. A strict reading of the registry, where lymphocyte count is a listed primary outcome, gives `met`. HR cells are left blank on purpose; the subset figure is in the note.
- **NCT04720716 (IBI310, HCC)**: `met` rests on one sentence, that confirmed ORR was "significantly higher" (41.7% and 22.1% vs 2.6%), with ORR a registry primary endpoint. No p-value, no hazard ratio, and no statistical statement on OS, the other primary endpoint (medians 44.0 and 36.1 vs 22.9 months). The IBI310 dose changed mid-trial, splitting the experimental arm. A reader who requires the OS result would keep it `unclear`.
- **NCT04914598 (COREMAP)**: `not_met`. The registry's only primary endpoint (PuFS) showed "no statistically significant difference". The abstract names OS as a second, dual primary endpoint and reports HR 0.807 (95% CI 0.625–1.042), Peto P=0.0338, described as "clinically meaningful" and never as statistically significant; no significance boundary is given. **The HR cells are for OS, not PuFS.** The NMPA accepted a filing for this indication in Feb 2026. Date is the journal's citation date and the first day of the congress (1–4 July 2026); the poster day was not verified.
- **NCT06759857 (FHND9041)**: the source is a preprint, not peer reviewed, coded `other`. The data cutoff was March 2025, fifteen months before posting, so a Chinese congress presentation or filing notice may predate it; none was found. The abstract does not say whether PFS was centrally reviewed. Registered on ClinicalTrials.gov three and a half years after the trial started.
- **NCT04233151 (QL1203)**: dated 27 Jan 2025 from the journal page; the symposium released its abstracts a few days earlier (not verified). The interval in the HR cells is the 97.42% CI of the interim analysis. QL1203 is a panitumumab biosimilar tested for superiority over placebo: review for exclusion if biosimilar trials are out of scope. The lag of 27 days is against an estimated registry date; the data cutoff was March 2024.
- **NCT05254171 (ASPIRE)**: `terminated_no_analysis` is the EU register's "Sponsor Decision" of 28 Mar 2025 plus the sponsor's collapse. An interim analysis had been planned for the first quarter of 2025, and nothing says whether it was run. An undisclosed interim result cannot be ruled out.
- **NCT05797831 (navtemadlin, endometrial)**: terminated in July 2024, a year after starting, before the phase 3 part. A summary of results was filed with the EU register in Oct 2025 and could not be opened; it can only concern the dose-selection part. Phase 2/3 with a dose-finding first part: review for exclusion.
- **NCT05751850 (HR070803-301)**: Hengrui opened a second phase 3 of the same design in Dec 2025 (HR070803-308, NCT07238283), which is the "entered phase III" item in its 2025 annual results. Do not read that item as progress on this trial, and do not attach the second-line PAN-HEROIC-1 result here. What happened to this trial is not stated anywhere I could reach.
- **NCT06110663 (HS-10241-301)**: Hansoh filed for approval in exactly this population in Feb 2026 and has published only single-arm phase 1b data. The filing may rest on this trial, which would imply a positive result, but no source says so. Likely to resolve at a congress soon.
- **NCT05015621 (SURTORI-01)**: dropped from HUTCHMED's pipeline table between 31 Jul 2024 and 19 Mar 2025 with no explanation. Not coded `terminated_no_analysis` because no source says it was stopped.
- **NCT02546102 (ICT-107)**: `no` with a blank result. In substance the trial stopped in 2017 for lack of funds; the registry says suspended, not terminated.
- **NCT03008148 (JP001)**: the sponsor's site has not changed since 2020 and the licensee's last word (Aug 2021) was six patients randomised. The trial may never have run.
- **NCT04720716, NCT04233151, NCT03520686**: ASCO abstract dates are the journal supplement's "published online" dates. The meeting library releases abstracts earlier, by days.

## What worked

- **The browser pane opens publisher pages that refuse scripted fetches.** annalsofoncology.org and ascopubs.org returned full abstracts and "published online" dates; researchsquare.com gave its posting date. This is how the COREMAP abstract was read after three web searches and five direct fetches failed.
- **The EU trial register has a public API** (`euclinicaltrials.eu/ctis-public-api/retrieve/<EU CT number>`, and a `search` endpoint that accepts a study number). It records early terminations with a date and a reason for each member state. Two trials in this batch are shown as recruiting on ClinicalTrials.gov and as terminated there.
- **Crossref title-only queries on the drug code** found the QL1203 abstract that PubMed and Europe PMC do not hold. OpenAlex and Semantic Scholar carry ASCO abstract text when Crossref does not.
- **Europe PMC indexes preprints by registry number**, which found the FHND9041 result.
- **Sibling trials in the registry explain odd lines in company documents**: a `query.term` search on the drug code showed the second Hengrui pancreatic trial.
- **A company's main site may be readable when its investor subdomain is not** (immunitybio.com against ir.immunitybio.com).

## What did not work

- **Refused or failed fetches**: annalsofoncology.org and sciencedirect.com (403 to the page-fetch tool and to curl), ir.immunitybio.com (403 and a timeout), the ClinicalTrials.gov version-history endpoint (403), one sec.gov filing (503), Elsevier's API (429), Crossref (429 twice, on rapid queries), EDGAR full-text search (one 500 on a query with a company filter). panbela.com and hebabiz.com did not answer at all. The page-fetch tool returned only the title of the Research Square page.
- **Image-only PDFs**: the ImmunityBio poster has no text layer; it was rendered to an image and read by eye.
- **Graphical pipeline tables**: Hengrui's tables show the phase as a drawn bar, which text extraction drops, so a row's phase cannot be read from the text; only the section heading ("NDA acceptance", "entered phase III") survives.
- **Crossref multi-word title queries** return noise; only single drug codes or names worked. WCLC 2026 abstracts were not yet deposited, so that congress could not be checked for the two lung trials.
- **The ASCO meeting library** could not be searched (its search address redirects to an error page), so abstract release dates could not be pinned to the day.
- **Not reached at all**: China's CDE trial register, Shanghai exchange notices of Hengrui, Taiwanese company filings. Rows that depend on them are medium.

## Sources of the journal and congress figures

- CELESTIMO: Roche media release, 17 Sep 2026, https://www.roche.com/media/releases/med-cor-2026-09-17
- QUILT-2.023: J Clin Oncol 44 (16_suppl), abstract 8588, [doi 10.1200/JCO.2026.44.16_suppl.8588](https://doi.org/10.1200/JCO.2026.44.16_suppl.8588)
- IBI310 in HCC: J Clin Oncol 44 (16_suppl), abstract 4148, [doi 10.1200/JCO.2026.44.16_suppl.4148](https://doi.org/10.1200/JCO.2026.44.16_suppl.4148)
- FHND9041: Research Square preprint, [doi 10.21203/rs.3.rs-10115031/v1](https://doi.org/10.21203/rs.3.rs-10115031/v1)
- COREMAP: Ann Oncol 37 (suppl 1), S247, abstract 673P, [doi 10.1016/j.annonc.2026.05.202](https://doi.org/10.1016/j.annonc.2026.05.202)
- QL1203: J Clin Oncol 43 (4_suppl), abstract 190, [doi 10.1200/JCO.2025.43.4_suppl.190](https://doi.org/10.1200/JCO.2025.43.4_suppl.190)
