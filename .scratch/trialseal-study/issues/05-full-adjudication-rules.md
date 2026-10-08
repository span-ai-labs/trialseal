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
