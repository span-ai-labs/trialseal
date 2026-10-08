# 05: Full adjudication rules

**What to build:** The adjudication log handles the hard cases by rule: conflicting sources, revised results, void trials, late hazard ratios, non-English disclosures and disagreements between adjudicators.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Sources are ranked: journal paper or regulator document, conference presentation, press release or exchange filing, registry posting
- [ ] The highest-ranked source available on the analysis date decides the result; the earliest disclosure of any rank sets the readout date
- [ ] A later, higher-ranked source revises a result and the earlier result stays in the history
- [ ] Positive, negative and void follow the definitions in the glossary, including several primary endpoints and early stops
- [ ] A hazard ratio arriving more than six months after readout is recorded as missing for the effect-size analysis
- [ ] Each adjudication records the disclosure language and holds the original text with a translation where needed
- [ ] A disagreement blocks the result until a reconciliation is recorded with its reason
- [ ] Adjudication entries cannot be made by someone who has opened that trial's forecasts

## Comments

**2026-10-08, from ticket 02's review.** Agreement between adjudicators is currently on the outcome only: two adjudications that agree a trial was positive but record hazard ratios of 0.6 and 0.95, or readout dates months apart, still produce a result, with the earliest date taken. This ticket should require agreement on the hazard ratio and settle the readout date by the source-ranking rule. A second entry by the same adjudicator currently replaces their first silently; it should be recorded as a revision with its history.
