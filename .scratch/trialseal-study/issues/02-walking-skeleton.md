# 02: Walking skeleton: one trial from snapshot to score

**What to build:** A single made-up trial travels the whole path: it is screened as having no public result, a base-rate forecaster issues a forecast in the common forecast shape, the batch is fingerprinted, two adjudicators record the same outcome, and the primary comparison scores the first forecast. Thin everywhere, complete end to end.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] A forecaster contract exists: frozen registry record and batch date in; probability of a positive trial, median hazard ratio and 80% interval out, with forecaster name and version
- [ ] A base-rate forecaster implements the contract
- [ ] A screening record marks a trial as eligible or as already read out, with evidence and date
- [ ] Building a batch refuses any trial recorded as already read out
- [ ] A batch produces one canonical record set per forecaster and a single fingerprint over all of them
- [ ] An adjudication record needs two adjudicators; a result exists only when they agree
- [ ] The primary comparison scores only the first forecast each forecaster sealed for a trial
- [ ] The whole path runs in one test with no network access
