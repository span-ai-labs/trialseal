# 11: Span forecaster, first version

**What to build:** The Span forecaster gathers evidence about a trial and issues a forecast, leaving a full record of what it read. Its cost is measured so the monthly ceiling can be set.

**Blocked by:** 08, 10

**Status:** ready-for-agent

- [ ] For each trial it gathers prior evidence such as earlier-phase results, sister trials of the same drug and results for the drug class
- [ ] Everything it retrieves is logged with source and date
- [ ] It implements the forecaster contract and is sealed with a version tag
- [ ] A forecast repeated without new research is recorded as a carried forecast
- [ ] A full pass is priced on 20 trials and a monthly ceiling is proposed to the study lead
- [ ] It never runs with web access on a trial whose readout is already public
- [ ] Needs the study lead: approval of the monthly ceiling
