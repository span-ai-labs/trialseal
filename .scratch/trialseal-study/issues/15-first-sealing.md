# 15: First sealing

**What to build:** Batch 1 is issued for every eligible trial by every forecaster, sealed, and its list of trials published.

**Blocked by:** 03, 06, 07, 08, 11, 14

**Status:** ready-for-agent

- [ ] The protocol registration is recorded before the batch is built
- [ ] Every eligible trial has a forecast, or a recorded failure, from every forecaster including the baselines
- [ ] The Span forecaster's version is sealed with the batch
- [ ] The fingerprint is anchored by both time-stamping methods and pushed publicly with the list of trials
- [ ] No forecast content is public
- [ ] The verifier confirms the sealed batch
- [ ] The cost of the batch is recorded against the ceiling
- [ ] Needs the study lead: go-ahead on the day
