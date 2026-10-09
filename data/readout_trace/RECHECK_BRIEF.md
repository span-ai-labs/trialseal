# How a trace is re-checked

A re-check is a second look at a traced trial whose first trace cannot be counted: it was of low confidence, its result was in doubt, or there is reason to think an earlier disclosure exists. The re-check replaces the first trace for that trial. It follows `TRACING_BRIEF.md` in every rule; read that first. This file says only what differs.

## What you are given

`recheck_sample_<batch>.csv`: one row per trial, with the registry columns of a sample file and then:

- `why_rechecked`: why the first trace does not stand.
- `first_traced_in`, `first_trace_*`: what the first tracer found, the URL they gave and their notes.

The first trace is a lead, not a finding. Many first traces were made after the tracer had run out of web searches, so "nothing found" in them often means "not looked for". Do not copy a result, date or hazard ratio from it. Record only what you have opened and read yourself in this re-check.

Where `why_rechecked` says a model gave the right result with a date well before the traced one, the traced result is probably right and the traced date probably late: look for an earlier first disclosure (a one-line statement in a quarterly results announcement or pipeline document, an exchange notice, a conference abstract published ahead of the meeting).

## Spend searches carefully

Web searches are a shared and limited allowance. **Use at most 30 web searches in this batch**, about two a trial, and stop searching when they are gone. Before any web search, use sources that need none:

- the registry record: fetch `https://clinicaltrials.gov/api/v2/studies/<NCT>` (results posted, status, why stopped, linked publications in `referencesModule`);
- PubMed, through the PubMed tools if you have them, or Europe PMC by fetching `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=<NCT or acronym>&format=json&resultType=core` (it indexes registry numbers in abstracts and full text, and many conference abstracts);
- for companies with US filings, EDGAR full-text search by fetching `https://efts.sec.gov/LATEST/search-index?q=%22<acronym or study number>%22`;
- a company's own news or investor page, fetched directly when you know its address.

Fetching a page you already have the address of is not a web search. Keep web searches for what these cannot reach: press releases, exchange notices in Chinese or Japanese, trade press.

## What to write

`rechecks_<batch>.csv`, with exactly the columns of `trace_A.csv`, one row for every trial in your batch file. `rechecks_<batch>_notes.md`, short: date, counts by `disclosed` and `primary_result`, how many rows changed from the first trace and how, how many web searches you used, and a "Rows to treat with care" list.

Confidence is what decides whether the trial is counted, so give it honestly:

- `high`: you opened and read a source that states the result of the primary analysis (or that there was none), it is plainly this trial, and you have reason to think it is the first disclosure.
- `medium`: you read a source that states the result, but an earlier disclosure may well exist, or the source is a snippet you could not open.
- `low`: you could not look properly. A row of low confidence will not be counted, so do not use it to hedge a finding you actually read.

`disclosed = no` with `high` confidence means a real search found nothing and the registry record shows no results: for a trial whose registry completion date is recent or still ahead, the registry record and one literature search are enough for that.

Do not put any personal email address or name in a User-Agent header, URL or request. Edit no file other than the two you create. Do not commit.
