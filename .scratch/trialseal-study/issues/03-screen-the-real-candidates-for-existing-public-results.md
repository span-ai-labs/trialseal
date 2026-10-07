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
