# 03: Screen the real candidates for existing public results

**What to build:** Every real candidate is checked for a public primary result before the first batch. Each check leaves a screening record with its evidence, and the study lead confirms the uncertain ones. The output is the list of eligible trials for batch 1.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Every candidate in the latest snapshot has a screening record with a decision, evidence links, search date and confidence
- [ ] Searches use the alias record, not only the registry number
- [ ] Decisions of low or medium confidence are queued for the study lead and are not eligible until confirmed
- [ ] Trials already read out are listed with their readout date and source, and feed the reference set where they qualify
- [ ] Excluded designs are listed with the reason
- [ ] A summary reports how many candidates are eligible, already read out, excluded and awaiting confirmation
- [ ] Needs the study lead: confirmation of the queued decisions

## Comments

**2026-10-08, from ticket 02's review.** A candidate tagged for exclusion review can currently be screened as eligible and enter a batch. This ticket should add an explicit screening decision for an excluded design, and refuse to clear a tagged candidate until a person has settled the review. Note also that a screening clears a trial for a batch only if it is no more than 14 days old, so the first batch needs the whole screen done inside that window.

**2026-10-08, from ticket 13.** Three things the analysis now expects of screening. The screening log is read from `screening/screening.jsonl`. Each candidate carries a default investigational drug (the first drug the registry lists in experimental arms only); it groups trials when uncertainty is estimated, it is wrong where a backbone is listed ahead of the drug under test or a code name was later replaced, and screening is where a person corrects it before the trial is sealed. And the final analysis will not run until every sealed trial without a result has a screening dated on or after the analysis date that found no public result, so the screening pass has to be repeatable for every sealed trial, not only for new candidates.
