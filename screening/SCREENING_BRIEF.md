# How a candidate is screened

A screen answers one question about a randomised phase 3 cancer trial: **has its primary analysis been publicly disclosed, anywhere, in any language, as of today?** A trial with a public primary result can never be forecast, so a missed disclosure is the costly error. A screen is lighter than a full readout trace: it needs the decision, the evidence and, where there is a readout, its date and a source. It does not need the hazard ratio.

## Read first

- Your worklist file. Each row gives every name the readout may be announced under: acronym, names from the title, the sponsor's study number, other registry numbers, intervention names (code names are often replaced by a later drug name: look it up), the sponsor and its partners.
- `data/readout_trace/trace_A_notes.md`, "Patterns that make automatic detection hard", and the correction at the end of `data/readout_trace/trace_C1_notes.md`.

## Where to look

Company press releases and investor pages; SEC 8-K and 6-K exhibits; **quarterly results announcements and pipeline documents** (a result is often first a single line there); Hong Kong, Shanghai, Shenzhen and Tokyo exchange notices, including Chinese- and Japanese-language ones; conference abstracts (ASCO, ESMO, ASH, SABCS, WCLC, AACR and national meetings); PubMed; the ClinicalTrials.gov record (results posted, "why stopped", status); trade press. Search by each name on the row, not only by the registry number. Watch for sibling trials of the same drug.

A result at an interim analysis counts: a trial stopped early for efficacy or futility has read out. A disclosed result for one of several primary endpoints counts.

## What to write

One CSV with exactly these columns, one row per trial of your worklist, every trial present:

| Column | Content |
|---|---|
| `nct` | registry number |
| `decision` | `eligible` (no public primary result found), `already_read_out`, or `void` (ended for business, safety or enrolment reasons with no primary analysis) |
| `confidence` | `high`, `medium` or `low` |
| `evidence` | what you searched and what you found, in a sentence or two: enough for a second person to repeat it |
| `evidence_links` | the URLs you opened, separated by spaces; at least the source of the readout where there is one |
| `readout_date` | for `already_read_out` only: YYYY-MM-DD of the earliest disclosure you could open |
| `investigational_drug` | leave blank unless the worklist's `investigational_drug` is wrong or empty; then the drug under test, lower case, no dose |

## Confidence

- `high` for `eligible`: you searched every name on the row, the sponsor's news and (for a company) its latest pipeline or results document, and found the trial described as ongoing or found nothing; and nothing suggests the registry record is stale.
- `high` for `already_read_out`: you opened a source that states the primary result for this trial.
- `medium`: one of those searches could not be done (a site was blocked, the sponsor publishes nothing in a language you could search), or the registry record has not been updated for over a year.
- `low`: sources conflict, or hint at a result without stating it, or you could not tell this trial from a sibling.

Decisions of medium or low confidence go to the study lead before they count, so do not round up.

## Rules

- Never guess a date. Never record `already_read_out` without a link you opened.
- Do not put any personal email address or name in a User-Agent header, URL or request.
- Write only your one output file. Do not commit.
