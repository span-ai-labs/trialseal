# 05: Full adjudication rules

**What to build:** The adjudication log handles the hard cases by rule: conflicting sources, revised results, void trials, late hazard ratios, non-English disclosures and disagreements between adjudicators.

**Blocked by:** 02

**Status:** done

- [x] Sources are ranked: journal paper or regulator document, conference presentation, press release or exchange filing, registry posting
- [x] The highest-ranked source available on the analysis date decides the result; the earliest disclosure of any rank sets the readout date
- [x] A later, higher-ranked source revises a result and the earlier result stays in the history
- [x] Positive, negative and void follow the definitions in the glossary, including several primary endpoints and early stops
- [x] A hazard ratio arriving more than six months after readout is recorded as missing for the effect-size analysis
- [x] Each adjudication records the disclosure language and holds the original text with a translation where needed
- [x] A disagreement blocks the result until a reconciliation is recorded with its reason
- [x] Adjudication entries cannot be made by someone who has opened that trial's forecasts

## Comments

**2026-10-08, from ticket 02's review.** Agreement between adjudicators is currently on the outcome only: two adjudications that agree a trial was positive but record hazard ratios of 0.6 and 0.95, or readout dates months apart, still produce a result, with the earliest date taken. This ticket should require agreement on the hazard ratio and settle the readout date by the source-ranking rule. A second entry by the same adjudicator currently replaces their first silently; it should be recorded as a revision with its history.

**2026-10-08, implemented.** An adjudication is now one person's reading of one source. A source's reading stands when two adjudicators record the same reading or a reconciliation settles their disagreement; a trial has a result only when every source recorded for it stands. 82 tests pass.

Review found the first version could be bypassed; each finding became a failing test and was fixed. In particular: a reconciliation must settle a recorded disagreement between the people who actually read the source; results no longer depend on the order of the log; the disclosure date is part of what must be agreed; and an entry made after its author opened the forecasts removes only that trial's result, and can be withdrawn and replaced by a blind reading.

Rules introduced here. The study lead said on 2026-10-08 to go with all recommendations, which I have taken to cover these; they belong in the protocol:

- Between two sources of the same rank, the later disclosure decides.
- Any source read by only one adjudicator, or in dispute, holds back the whole trial's result.
- Once two adjudicators have differed on a source, only a reconciliation with a reason settles it. Changing an entry to match is not enough.
- Agreement covers everything read from the source: outcome, hazard ratio and its endpoint, disclosure date, language, and how the primary endpoints combine.
- With an early stop, no per-endpoint results are recorded beside it.

Known limits:

- Blindness rests on the record of who opened forecasts. Nothing writes that record yet; ticket 16 (reveal) must write it, and the recording date of an adjudication is self-declared.
- The hazard ratio's endpoint is recorded as text and is not yet checked against the scored endpoint named in the batch. Ticket 13 should check it.
- "As of the analysis date" means entries recorded by that date, so a paper published before it but adjudicated after is not counted.

**2026-10-09, the adjudicators' command.** `trialseal-adjudicate form|record|status|disagreements|reconcile|withdraw --set reference|pilot` (`adjudicate.py`, tests in `tests/test_adjudicate.py`; how to use it is in `adjudication/ADJUDICATION_BRIEF.md`). Each adjudicator fills in a spreadsheet form; filled rows become readings dated the day they are recorded, all or none. The other adjudicator's form shows the sources cited and nothing of what was read. Forms and the list of disagreements are working files under `adjudication/working/`, which is not tracked.

**A finding of nothing** is new (`NothingFound`, kept in `nothing_found.jsonl` beside the log). An adjudicator records that they searched and found no source that states a trial's result; when both have, and neither has a reading in force, the trial has no result found. In the reference set it is then unresolved (void if the trace had it as ended without analysis), counts against the trace where the trace had a result, and no longer blocks the freeze. In the pilot it is a trial with no readout found. The same record, naming a source, says that a source the other cited does not state the result; the two then differ and may talk, and it is resolved by a withdrawal or by reading the source.

**Two adversarial reviews and a standards review** drove the command against the rules. Fixed with a failing test first, in the rules themselves:

- A reading made blind cannot be withdrawn by someone who has since opened the forecasts; a reading of a reconciled source cannot be withdrawn at all.
- A source read differently stays so after both withdraw their readings; reading it alike later does not settle it.
- A reconciliation cannot change what both readings share: the outcome, the hazard ratio, its endpoint, the disclosure date or the language. Where the languages differ it must say which.
- A reading that only puts a quote right does not reopen a reconciled source.
- A reading of a source is refused on a day when a reading of it was withdrawn or it was reconciled, because one day's entries are replayed readings, then withdrawals, then reconciliations. A reviewer ran 1,800 random sequences through the command against a model that applied them in real order; the replayed state matched every time.
- Hazard ratios must be finite; names are compared without case, spacing or Unicode form; endpoint names without case or spacing.

And in the command: one source cannot enter under two spellings of its address or two source types; a trial's readings are not laid open while either adjudicator has a cited source of it still to read; a list of disagreements is checked against the readings it was written from by a mark a spreadsheet leaves alone; nothing is added to the reference log once the base rates are frozen; a log holding an entry dated after today stops every step.

**Rules introduced here, for the protocol.**

1. A correction is a new reading recorded on purpose (`--revise`); a withdrawal is for a source that should not have been cited.
2. The second adjudicator reads the sources the first cited, under the same address and source type, and adds any other they know of.
3. A hazard ratio outside 0.05 to 20 is refused as a slipped decimal point.
4. A finding of nothing is made blind, on the day, by someone with no reading of the trial in force.

**Known limits.**

- The command cannot tell who is typing. That each adjudicator works alone, and that both are present at a reconciliation, rests on them; the logs are plain text in the repository.
- The rules trust the names in a log. Only the command checks a name against `study/adjudicators.json`, which now names one person; the second adjudicator's name is to be added by the study lead. A file edited by hand, or an adjudicator replaced part-way through a disagreement, is not caught.
- The source type cannot be disagreed about: it is part of what names a source. Changing it is a withdrawal and a new reading the next day.
- The look-alike check on addresses catches slips, not evasions (a tracking parameter, a mobile host).
- An address typed on one's own form and not yet read does not hold back the list of disagreements.
- Five trials are on both the reference and the pilot worklists and are read once for each.
- There is no set yet for trials with sealed forecasts: that needs the readout monitor (ticket 12) to say which trials are due, and the reveal (ticket 16) to write who opened which forecasts.
- A spreadsheet may turn a quote that begins with `=` into a formula.

**2026-10-09, third review.** A third adversarial pass, aimed at the second round of fixes, confirmed 13 more problems. All are fixed with a failing test first, except the limits listed below.

- *A dissent is now an entry in the log* (`Dissent`, `dissents.jsonl`), not a kind of finding of nothing. Recording that a source the other cited does not state the result makes the source one the two have read differently: if the dissenter later reads it alike, only a reconciliation settles it, and it is left out of first-reading agreement. Before, the two could talk and then "agree" with no reason recorded. A dissent lapses when the cited reading is changed or withdrawn, so a page cited again weeks later goes back on the dissenter's form. The log therefore has a fifth kind of entry, and an analysis record's count of log entries has five numbers.
- A source is reconciled once: a second reconciliation needs a new reading first. A reading is refused on the day its source was reconciled whoever records it, not only through the command.
- Withdrawing a reading of a reconciled source reopens it (from the day after the reconciliation), where before it was refused outright and a source about another trial could not be taken back.
- The frozen base rates record every file they could rest on, including log files that did not exist at the freeze, so one appearing later is noticed.
- The sample records a mark of how each trial it was drawn from was traced. The freeze refuses if any has been traced or re-checked differently since: a trace changed to match the adjudicators is not the trace they checked.
- Below nine in ten, `trialseal-reference sample` lists every traced trial, and the freeze goes through once the adjudicators have settled them all.
- On the form, a row the command filled in is told from one the adjudicator typed by a mark, so a citation the other has withdrawn no longer lingers as if typed. A stale list of disagreements is written afresh; a typed settlement that can still be recorded is not written over.
- `trialseal-reference` and the pilot report stop on a log entry dated after today, as the adjudicators' command does.

**Rules introduced here, for the protocol.**

5. A source both adjudicators have withdrawn, each with a reason, no longer counts for the trial, even one they had read differently. The trial can then have no result found. The withdrawals are the record of why.
6. After the sample is drawn, no trace or re-check of a trial it was drawn from may change before the freeze.
7. If the trace matches the adjudicators on fewer than nine in ten, they read every traced trial and the figures are frozen from their readings.

**Known limits, added.**

- The source type of a source the two have read differently cannot be changed.
- A trial that has left its worklist and is not in the latest registry snapshot is shown with no title or scored endpoint.
- The pilot scores a trial the two have read differently on the trace until they settle it; the reference set holds such a trial in doubt.
- Three passes of review have each found about a dozen or more real problems here. This is the code that guards blindness and it should be read again before the first reveal.

**2026-10-09, decided.** The study lead said to take the open decisions on his behalf. Rules 1 to 7 above stand, including rule 5: a source both adjudicators withdraw, each with a reason, no longer counts for the trial. `study/adjudicators.json` now names both adjudicators.
