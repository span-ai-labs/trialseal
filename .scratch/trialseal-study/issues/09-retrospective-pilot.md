# 09: Retrospective pilot

**What to build:** Before anything is sealed, the method is tried on trials each model cannot have seen: its knowledge around the stated cutoff is probed, its forecasts on later readouts are scored, and the numbers needed for the sample-size statement are measured.

**Blocked by:** 05, 08

**Status:** ready-for-agent

- [ ] Each model is probed for recall of readouts by month around its stated cutoff, and a buffer is chosen from the result
- [ ] Each model is tested on recalling results from trial identifiers alone
- [ ] Each model's pilot trials are those with a readout after its cutoff plus buffer
- [ ] Pilot outcomes are adjudicated by both adjudicators and their agreement is reported
- [ ] The pilot reports the variance of per-trial score differences between forecasters and a revised sample-size statement, including one for the effect-size analysis
- [ ] A model showing recall beyond its buffer is dropped from the pilot or given a longer buffer
- [ ] The report states plainly that the pilot tests the method and is not the evidence
