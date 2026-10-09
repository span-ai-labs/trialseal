# How a trial is adjudicated

Two adjudicators each read the public sources about a trial and record what they show. Neither sees the other's reading until both have recorded their own. A trial has a result when both have read every source cited for it and read it the same way, or have settled their difference in a reconciliation. The rules are in `CONTEXT.md` and ADR-0008; this is how to follow them with the command.

## Working alone

- Do not open the log files under `adjudication/reference/` or `adjudication/pilot/` (the `.jsonl` files), the trace files under `data/readout_trace/`, or anything under `private/` or `results/pilot/` other than the list of trials.
- Do not talk to the other adjudicator about a trial until `status` shows it as `settled`, `no result found` or `read differently`. One exception is given under "When something is wrong".
- For trials with sealed forecasts, never open the forecasts.

The command cannot tell who is typing. That each of you works alone, and that both of you are present for a reconciliation, rests on you.

## Before you start

Your name must be in `study/adjudicators.json`, which holds the adjudicators' names as `["First Name", "Second Name"]`.

Open the form in a spreadsheet. Before typing, format the `disclosed_on` column as text, or the spreadsheet will rewrite the dates. Save as **CSV UTF-8**, not plain CSV.

## The steps

Replace `reference` with `pilot` for the pilot's trials.

```bash
uv run trialseal-adjudicate form --set reference --by "Your Name"
```

This writes your form to `adjudication/working/reference/form_your-name.csv`. There is one row for each source waiting for your reading.

- Where the other adjudicator has cited a source, its type and address are filled in and nothing else. Leave both exactly as they are and read that source yourself. If you know of another source that states the result, copy the row and give the other source on the copy.
- Where a row has no source, find the trial's sources yourself, starting with the first public disclosure of the primary analysis.

Fill in the rows you have read, save, then:

```bash
uv run trialseal-adjudicate record --set reference --by "Your Name"
```

Every filled row is recorded, dated today, or none is and each problem is listed by row. The form is then written again with what is left. You can record a few trials at a time.

```bash
uv run trialseal-adjudicate status --set reference
```

This lists every trial and where it stands. When both of you have read every source of a trial and read one of them differently:

```bash
uv run trialseal-adjudicate disagreements --set reference
```

This writes `adjudication/working/reference/disagreements.csv` with both readings side by side. Go back to the source together, fill in the `settled_` cells and the `reason`, then:

```bash
uv run trialseal-adjudicate reconcile --set reference --by "First Name" --by "Second Name"
```

## What goes in each cell of the form

| Cell | What to write |
|---|---|
| `source_type` | `paper_or_regulator` (a journal paper or a regulator's document), `conference` (an abstract or presentation), `press_release_or_filing` (a press release, an exchange or SEC filing, a results announcement), or `registry` (results or a status posted on the registry) |
| `source` | The address of the page you read. If it is filled in, leave it exactly as it is |
| `disclosed_on` | The day the source became public, as `2026-03-01`. Not the day you read it |
| `language` | `en`, or the language's two-letter code |
| `original_text` | The sentence or two in the source that state the result, copied exactly |
| `translation` | Your English translation, if the source is not in English |
| `endpoint_rule` | `single` for one primary endpoint; `any_of` where the trial is positive if any one of several primary endpoints is met; `co_primary` where all must be met |
| `endpoint_results` | For each primary endpoint, in the order of the `primary_outcomes` cell (the registry's order, if that cell is blank): `met`, `not_met` or `not_reported`, separated by semicolons. Leave blank for an early stop |
| `early_stop` | Blank, or `efficacy`, `futility` or `no_analysis`. See below |
| `hazard_ratio` | The hazard ratio the source reports for the trial's scored endpoint, as `0.72`. Blank if the source gives none |
| `hazard_ratio_endpoint` | Filled in with the trial's scored endpoint. Leave it. Only if the source gives no hazard ratio for the scored endpoint and does give one for another endpoint, record that one and type the endpoint's usual abbreviation here in capitals, such as `PFS`, `DFS` or `OS` |
| `nothing_found` | Leave blank, unless you found nothing. See below |

You are not asked whether the trial was positive or negative. That follows from the results you record. `met` means the source reports a statistically significant benefit on that primary endpoint.

Use `early_stop` only when the source says the trial itself was stopped, or its primary analysis brought forward, because of an interim result: `efficacy` for benefit, `futility` for lack of it. A positive interim analysis reported as the trial's primary result, with the trial continuing, is `met`. `no_analysis` is a trial that ended with no primary analysis at all: it is void.

A trial may have several sources: give each its own row. Record every source that states the primary result, not only the first. The most authoritative decides the outcome and the earliest sets the readout date.

## When you find nothing

**No source at all.** If you have searched and found no source that states the result of the primary analysis, leave the reading cells and the source blank and write where you looked in `nothing_found`, for example `registry record; PubMed by number, acronym and drug; sponsor's news page and filings`. When both of you have recorded this for a trial, it has no result found. If the other adjudicator then finds a source, it will appear on your form to be read. If you later find one yourself, run `form` with `--reread NCT01234567` to get a row for the trial.

A trial that ended with no primary analysis is not this case. Record the source that says so, with `early_stop` as `no_analysis`.

**A source the other adjudicator cited that does not state the result.** Leave its reading cells blank and write in `nothing_found`, on that source's row, what the source holds instead, for example `an interim safety review; no primary analysis reported`. `status` then shows the trial as `read differently` and the two of you may talk about that source. Either they withdraw their reading, or you run `form` with `--reread` and read it.

## What goes in each cell of the list of disagreements

Each row shows both readings of one source. Leave those cells and `as_listed` alone; it does not matter if the spreadsheet rewrites a date or a number in them. Format the `settled_disclosed_on` column as text before typing. Fill in what the two of you settle on:

| Cell | What to write |
|---|---|
| `settled_outcome` | `positive`, `negative` or `void` |
| `settled_disclosed_on` | The day the source became public |
| `settled_hazard_ratio` | The hazard ratio, or blank if the source gives none |
| `settled_hazard_ratio_endpoint` | The endpoint it is for. Blank if the hazard ratio is blank |
| `settled_language` | Only if you recorded different languages: which it is |
| `reason` | Why the readings differed and why this is right |

What both of you read the same way cannot be changed here. If you both recorded the same outcome and differ only on the date, the settled outcome is that outcome. Two readings can also differ only in how they were written down, for example `met` against an early stop for efficacy, or the endpoint results in another order. That is reconciled like any other difference.

## When something is wrong

- **You made a mistake in a reading you have recorded.** Run `form` with `--reread NCT01234567` to get a row for each source you have read for that trial. Fill in the row as it should be and run `record` with `--revise`. Both readings stay in the log. If the other adjudicator has already read the source differently, it stays a disagreement until you reconcile it.
- **You cited a source that is not about this trial.** `uv run trialseal-adjudicate withdraw --set reference --by "Your Name" --trial NCT01234567 --source "the address" --reason "why"`. Neither of you can record a reading of that source again until the next day.
- **You think a source the other adjudicator cited does not state the result.** Say so on its row: see "When you find nothing".
- **You think a source the other adjudicator cited has the wrong source type.** Tell them that one thing. They withdraw it and cite it again the next day under the right type.
- **A source you found yourself does not say whether the endpoint was met.** Do not record it. A source is recorded only when it states a result.
- **You want to add a source to a trial that no longer shows on your form.** Run `form` with `--reread NCT01234567` and copy one of its rows.

## Once the base rates are frozen

Nothing more can be recorded for the reference trials: the frozen figures were made from that log.

## Not yet covered

- Trials with sealed forecasts. The command has no set for them yet; it will come with the readout monitor and the reveal.
- Five trials are on both the reference and the pilot lists. Each list has its own log, so they are read once for each.
- Chinese and Japanese domestic meetings and journals are hard to search. Say so in `nothing_found` when that is where a result would be.
