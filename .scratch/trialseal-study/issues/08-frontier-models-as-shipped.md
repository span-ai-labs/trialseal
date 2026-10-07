# 08: Frontier models as shipped

**What to build:** Each chosen frontier model forecasts every eligible trial without web access, from identical trial information, several times, with everything needed to judge leakage recorded.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Each model is called through its plain interface with no tools and no added system
- [ ] Every model receives the same trial information, taken from the frozen registry record
- [ ] Each trial is forecast several times per model and the runs are combined by a rule fixed in advance
- [ ] Model identifier, stated training cutoff, release date and date of use are recorded with every forecast
- [ ] Raw model output is kept with each forecast
- [ ] A model's failure to answer is recorded as no forecast produced
- [ ] Cost per batch is tracked
- [ ] Model keys come from the environment and never enter the repository
- [ ] Needs the study lead: model keys on the machine
