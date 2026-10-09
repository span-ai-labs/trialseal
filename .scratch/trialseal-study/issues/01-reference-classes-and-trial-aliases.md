# 01: Reference classes and trial aliases

**What to build:** Every candidate trial carries its reference class (sponsor type by endpoint type) and the alternative names under which its readout may be announced. This is groundwork for screening, base rates and the readout monitor.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Each candidate has a sponsor type and an endpoint type with three possible values: overall survival, progression-type, other time-to-event
- [x] A trial whose primary endpoints span more than one endpoint type is classed by its scored endpoint, the first listed in the registry record
- [x] Each candidate has an alias record: acronym, sponsor study number, intervention names and code names, lead sponsor and collaborators
- [x] Candidates that mention a non-inferiority design are tagged for exclusion review, not silently dropped
- [x] Existing candidate counts by window are unchanged by this work
- [x] Tests use made-up registry records in the style of the existing universe tests

## Comments

**2026-10-07, implemented.** Every candidate now carries its scored endpoint, endpoint type, sponsor type, reference class, alias record and an exclusion-review tag. Candidate counts by window are unchanged on all three snapshots (past 12 months 322/160, past 24 months 586/281, next 15 months 500/250, all sponsors/industry). 30 tests pass.

Decisions taken here that need the study lead:

- The scored endpoint is the first *time-to-event* primary endpoint listed, not simply the first listed (ADR-0012, accepted by the study lead on 2026-10-08). It differs from the first-listed endpoint for 230 of 2,422 candidates.
- Survival with no qualifier ("Survival", "2-year survival rate") is classed as overall survival.
- Any mention of non-inferiority in the title, summary, description or primary outcome queues the candidate for exclusion review (131 candidates, one of them an industry-led trial in the next 15 months).

Left for later tickets:

- Title-derived trial names are unverified and include disease abbreviations ("NSCLC"); they are held apart from the registry acronym. Ticket 12 measures matching quality.
- The candidate filter itself misses a few spellings ("All cause mortality" with a space). Widening it would change candidate counts, so it was left; ticket 03's hand review is the place to catch them.
- One registry record labels a response endpoint "(OS)" and is classed as overall survival (NCT06953999).

**2026-10-09, from ticket 04.** Tracing surfaced two faults in the candidate universe. (1) The registry classes some companies as "other"; ten are now corrected to industry-led by a published list (ADR-0016). The list was found by reading sponsor names that look like company names, so a company whose name does not will have been missed. (2) A time-to-event endpoint worded like a cancer one lets a few trials through that are not cancer trials. Two are excluded by design ruling; a word search of conditions and titles is the only check so far, and the universe has no test that a candidate is a cancer trial.

