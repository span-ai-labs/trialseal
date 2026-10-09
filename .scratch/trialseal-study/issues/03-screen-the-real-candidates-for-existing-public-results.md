# 03: Screen the real candidates for existing public results

**What to build:** Every real candidate is checked for a public primary result before the first batch. Each check leaves a screening record with its evidence, and the study lead confirms the uncertain ones. The output is the list of eligible trials for batch 1.

**Blocked by:** 02

**Status:** ready-for-human

- [ ] Every candidate in the latest snapshot has a screening record with a decision, evidence links, search date and confidence
- [x] Searches use the alias record, not only the registry number
- [x] Decisions of low or medium confidence are queued for the study lead and are not eligible until confirmed
- [x] Trials already read out are listed with their readout date and source, and feed the reference set where they qualify
- [x] Excluded designs are listed with the reason
- [x] A summary reports how many candidates are eligible, already read out, excluded and awaiting confirmation
- [ ] Needs the study lead: confirmation of the queued decisions

## Comments

**2026-10-08, from ticket 02's review.** A candidate tagged for exclusion review can currently be screened as eligible and enter a batch. This ticket should add an explicit screening decision for an excluded design, and refuse to clear a tagged candidate until a person has settled the review. Note also that a screening clears a trial for a batch only if it is no more than 14 days old, so the first batch needs the whole screen done inside that window.

**2026-10-08, from ticket 13.** Three things the analysis now expects of screening. The screening log is read from `screening/screening.jsonl`. Each candidate carries a default investigational drug (the first drug the registry lists in experimental arms only); it groups trials when uncertainty is estimated, it is wrong where a backbone is listed ahead of the drug under test or a code name was later replaced, and screening is where a person corrects it before the trial is sealed. And the final analysis will not run until every sealed trial without a result has a screening dated on or after the analysis date that found no public result, so the screening pass has to be repeatable for every sealed trial, not only for new candidates.

**2026-10-09, built; the full search and the study lead's rulings remain.** `screening.py` holds the rules, `screen.py` the command (`trialseal-screening worklist | import | registry | import-trace | confirm | design | summary`), and `screening/SCREENING_BRIEF.md` is what a searcher follows. Tests are in `tests/test_screening.py`.

**What the first box still needs, and why it was not done now.** Of 2,425 candidates in the snapshot, 1,146 with a registry completion date within 24 months either side of today still need a search. A screening clears a trial for only 14 days, so a full search made today would have to be made again before the first sealing. I recommend making it once, in the 14 days before the first sealing date. Two things are needed for that: the searches must run with web search available (see below), and the snapshot window of 24 months either side should be confirmed.

**What was recorded now, at no search cost** (`screening/screening.jsonl`, summary in `results/screening/`):

- 162 candidates whose registry record shows results posted: read out.
- 338 traced trials: each given the record its trace implies.
- 60 candidates from a rehearsal of the search (below).
- As of today: 271 read out, 8 void, 14 eligible, 219 awaiting confirmation, 1,912 not screened.

**A rehearsal of the search on 60 candidates** with registry completion dates between October 2026 and December 2027 (`screening/rehearsal/`): 13 had already read out and 1 was void. That is nearly a quarter of trials whose registry date is still in the future; six of the seven read-out trials in one half still showed an active or recruiting status. So the registry date and status cannot stand in for the search, and the first batch will be smaller than the candidate count suggests. The rehearsal ran without web search, because the agents running at the same time had used up a shared allowance; it relied on the registry, PubMed, Crossref and sponsor pages, so most of its "eligible" findings are of medium confidence and wait for confirmation. The real search must be run a few searchers at a time so that each has web search.

**For the study lead.**

1. `results/screening/queue.csv`: 219 decisions of low or medium confidence. Mark `confirm` yes or no; a "no" on a report that a trial read out needs a `note`. Then `uv run trialseal-screening confirm results/screening/queue.csv --by "<your name>"`. Most are "eligible, medium" from light searches and are better re-searched than confirmed.
2. `results/screening/design_queue.csv`: 130 candidates tagged for exclusion review. Each row shows a proposed ruling with a quote from the registry record (114 exclude, 10 include, 8 unsure). The tag turned out to be right far more often than expected. Fill in `decision` and `reason` yourself; a proposal is never taken as a ruling. Then `uv run trialseal-screening design results/screening/design_queue.csv --by "<your name>"`.
3. One policy question the proposals raise: five registrations hold two trials under one number, one testing non-inferiority and one superiority. I recommend excluding them, since the registry cannot say which result a readout belongs to. **Decided 2026-10-09:** the study lead said to go with this. The five (NCT04513717, NCT05050084, NCT06493552, NCT07154069, NCT07340567) are recorded as excluded in `screening/design_reviews.jsonl`, from `screening/design_rulings_2026-10-09.csv`. The design queue is now 125.

**Rules introduced here.** The study lead said on 2026-10-09 to go with all recommendations; these follow from that and belong in the protocol:

1. A decision of high confidence stands by itself; one of low or medium confidence waits for the study lead.
2. A report that a trial read out or is void, if it does not stand, keeps the trial out until the study lead confirms or overrules it. A searcher's later finding of nothing does not answer it.
3. A confirmation does not move the date of the search; the 14 days run from the search.
4. A candidate already known to be void is never eligible.
5. Results posted on the registry count as a readout, dated at the posting.
6. A design ruling does not go stale; the latest stands; a ruling to exclude holds for any candidate, tagged or not. The same gate is applied when a batch is built and when it is sealed.
7. Candidates are searched if their registry completion date is within 24 months either side of the day.
8. The investigational drug recorded at screening, by a decision that stands, replaces the registry's default when a batch is built.

**2026-10-09, second review.** A second adversarial pass found the first round closed and a narrower set, fixed with tests: confirming a queue row now matches the whole row, not the trial alone; a report that a trial read out cannot be overruled while another such report for the same trial is unmarked; a search dated in the future or more than 14 days back is refused on import; the drug correction comes from the latest search that stands; a waiting record for a trial no longer in the snapshot still shows in the queue.

**Known limits.** `build_batch` takes design rulings as an argument and defaults to none; sealing is the gate that always has them. `exclusion_review` was added to the sealed line for a trial, so a batch sealed before today would not read back; none has been sealed.

**2026-10-09, decided on the study lead's behalf.** NCT07609901 and NCT06950385, trials in people who do not have cancer, are excluded (`screening/design_rulings_2026-10-09c.csv`). The rule this sets: the study is of treatment trials in people with cancer; a prevention trial is excluded by design ruling.
