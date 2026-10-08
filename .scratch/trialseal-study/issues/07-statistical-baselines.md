# 07: Statistical baselines

**What to build:** Two families of baseline forecasters exist and can be sealed like any other: a simple model on registry fields, and class-level effect-size baselines.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] A registry-feature model predicts the probability of a positive trial from fields available before readout, trained only on reference-set outcomes
- [ ] Its accuracy on held-out reference-set trials is reported next to the base rate
- [ ] Three effect-size baselines exist for every trial: the empirical distribution for its reference class, the average effect sponsors assume, and that average shrunk toward no effect
- [ ] A trial-specific sponsor-assumed effect is used only where it was public before readout, under a rule for missing values fixed in advance
- [ ] All baselines implement the forecaster contract
- [ ] No baseline uses any information dated after the batch

**2026-10-08, from ticket 13.** The effect-size baselines are named in `study/analysis_plan.json`, which the first seal carries and no later seal may change. It currently lists only `base_rate`. The names of the baselines built here must be added to it before the first sealing, and each must be a forecaster in every batch.
