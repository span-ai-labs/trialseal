# 18: Discovery loop on the reference set

**What to build:** A ledger of hypotheses about what predicts a positive trial or its effect size, each tested on the reference set under rules that keep chance findings out. Confirmed findings are passed to the Span forecaster.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] A confirmation portion of the reference set is held back before any exploration and used only to confirm
- [ ] Every hypothesis is logged with its test and its stop condition before the test is run
- [ ] Every result is logged, including nulls
- [ ] A finding counts only if it holds on the held-back portion, with the number of hypotheses tried reported beside it
- [ ] Each confirmed finding is written up as a proposed change to the Span forecaster for a later version
- [ ] Nothing learned here alters a forecast that is already sealed
