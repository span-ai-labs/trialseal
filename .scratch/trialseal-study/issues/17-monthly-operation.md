# 17: Monthly operation

**What to build:** Each month a new batch is issued on its registered date with little manual work: changed trials are re-researched, the rest are carried, newly eligible trials are added and the batch is sealed.

**Blocked by:** 15

**Status:** ready-for-agent

- [ ] Registry records that changed since the previous batch are identified from the daily snapshots
- [ ] Changed trials are re-researched by the Span forecaster; unchanged ones are recorded as carried forecasts
- [ ] Newly eligible trials are screened and added; trials that have read out leave the eligible list
- [ ] The batch is sealed on the registered date and its cost recorded
- [ ] A missed or late batch is recorded in the deviations log
- [ ] A short monthly report lists what changed
