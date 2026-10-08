# How a readout is traced

This is the method every tranche of the readout trace follows. A tracer is given a sample file of randomised phase 3 cancer trials and finds, from public sources, whether each trial's primary analysis has been publicly disclosed, when it was first disclosed, and what it showed.

A trace is one reader's finding. It is provisional until the two adjudicators have read the sources themselves.

## Read first

- Your sample file (`sample_<tranche>.csv`): registry number, acronym, sponsor study number, title, lead sponsor, status, registry primary completion date, primary outcomes, interventions, conditions.
- `trace_A_notes.md`: the conventions and the pitfalls found in the first tranche.
- `trace_A.csv`: the output format, with examples.
- `trace_C1_notes.md`, the correction at the end: a first disclosure that was a single line in a company's pipeline document, missed at first.

## Where to look

Search for the **first** public disclosure of the primary analysis, not the best-known one:

- company press releases and investor pages; SEC EDGAR 8-K and 6-K exhibits;
- **quarterly and annual results announcements and pipeline documents** (a result is often first stated there as one line, such as "did not meet primary endpoint" or the trial moving to "removed from phase III"), for large sponsors check the documents of each quarter around the registry completion date;
- Hong Kong, Shanghai, Shenzhen and Tokyo exchange announcements, including Chinese- and Japanese-language notices;
- conference abstracts and coverage (ASCO, ESMO, ASH, SABCS, WCLC, AACR and others);
- journal papers (PubMed);
- the ClinicalTrials.gov record itself (results posted, "why stopped");
- trade press.

Search by acronym, sponsor study number, every drug name **including later names for code-named drugs**, and sponsor. Many trials are run by academic groups or hospitals that issue no press release: for those, conference abstracts, journal papers and the registry record are the likely first disclosure.

Open and read the source where you can. Do not rely on a search snippet for the result or the date unless nothing can be opened, and say so in `search_notes` when you did. Beware sibling trials of the same drug: make sure a source is about this registry number or its named protocol.

## What to write

`trace_<tranche>.csv`, with exactly the columns of `trace_A.csv`, one row per trial, every trial of the sample present:

| Column | Content |
|---|---|
| `nct` | registry number |
| `disclosed` | `yes`, `no` or `unclear` |
| `first_disclosure_date` | YYYY-MM-DD of the earliest source you could open and read |
| `first_source_type` | `press_release`, `exchange_announcement`, `conference`, `paper`, `registry` or `other` |
| `first_source_url` | the URL you opened |
| `primary_result` | `met`, `not_met`, `stopped_futility`, `stopped_efficacy`, `terminated_no_analysis`, `mixed` or `unclear`; blank if simply not read out |
| `which_endpoint` | the primary endpoint the result is for, such as OS, PFS, EFS, DFS |
| `hr_in_first_disclosure` | `yes` or `no` |
| `hr_first_public_date`, `hr_value`, `hr_ci_low`, `hr_ci_high`, `hr_source_url` | the first public hazard ratio for that endpoint |
| `registry_pcd`, `registry_pcd_type` | copied from the sample file |
| `lag_days_pcd_to_disclosure` | first disclosure date minus registry date, in days; a month-only registry date is taken as the 15th |
| `search_notes` | what you searched, what you found, any doubt: enough for a second person to find the source again |
| `confidence` | `high`, `medium` or `low` |

## Rules

- `met` means the source reports a statistically significant benefit on the primary endpoint. Where several primary endpoints each suffice, one met is enough; say which in `which_endpoint` and the notes. `not_met` means it did not.
- A trial stopped early at an interim analysis for efficacy is `stopped_efficacy`; for futility, `stopped_futility`.
- A trial ended for business, safety or enrolment reasons with no primary analysis is `terminated_no_analysis` with `disclosed = no`.
- A non-inferiority or single-arm design is still traced; say so in the notes, since such designs are reviewed for exclusion.
- The hazard ratio must be for the primary endpoint named in `which_endpoint`. If the only public hazard ratio is for another endpoint, leave the cells blank and say so.
- Never guess a date or a number. If you find no disclosure after a real search (at least the acronym, the study number, each drug name, the sponsor's news page and, for large sponsors, their pipeline documents), record `disclosed = no` with a note of what you searched. Use `unclear` only when sources conflict or hint at a result without stating it.
- Do not put any personal email address or name in a User-Agent header, URL or request to any site. If a site wants a contact in the User-Agent, use a generic descriptive string without an email, or reach the document another way.
- Edit no file other than the two you create. Do not commit.

Also write `trace_<tranche>_notes.md` in the style of `trace_A_notes.md`, short: date traced, counts by `disclosed` and by `primary_result`, the lag summary, how many first disclosures carried a hazard ratio, and a "Rows to treat with care" list.

Work through every trial; do not stop early. If the session is running long, finish the remaining trials with a lighter search rather than leaving rows out, and mark those rows `confidence = low`.
