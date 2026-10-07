# 13: Analysis plan in code

**What to build:** Every registered analysis can be produced by one command from sealed forecasts and adjudicated outcomes, including the descriptive look and the final analysis with its extension rule.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] The primary comparison uses first forecasts in the primary analysis set, with uncertainty that groups trials of the same drug
- [ ] Calibration, discrimination and a second scoring rule are reported for every forecaster
- [ ] Effect-size forecasts are scored with proper scoring rules against the class-level baselines
- [ ] Secondary and sensitivity analyses are produced: all sponsors, last forecast before readout, accuracy by lead time, by forecaster version, without non-English disclosures, void counted as negative, unresolved trials imputed
- [ ] The descriptive look reports scores and makes no test of the registered claim
- [ ] The final analysis applies the extension rule at the registered thresholds and can run only once
- [ ] A table per model shows its cutoff, release date, dates of use and the earliest and latest readout scored
- [ ] One command regenerates every table and figure
