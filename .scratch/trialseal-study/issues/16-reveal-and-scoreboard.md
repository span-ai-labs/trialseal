# 16: Reveal and scoreboard

**What to build:** Forecasts for resolved trials are revealed and shown on a public page with the outcome and running scores, and nothing is revealed until legal sign-off is recorded.

**Blocked by:** 05, 06

**Status:** ready-for-agent

- [ ] Reveal refuses to run when no legal sign-off is recorded
- [ ] Only trials with an agreed adjudication are revealed
- [ ] The scoreboard shows, for each resolved trial, every forecaster's forecast, the outcome and the scores
- [ ] It shows each forecaster's running score against the base rate
- [ ] It shows how many trials are sealed, resolved, unresolved and void
- [ ] It carries a research-only notice and the conflict-of-interest statement
- [ ] The adjudication log for revealed trials is published with it
- [ ] Needs the study lead: counsel's sign-off

## Comments

**2026-10-08, from ticket 05.** Adjudication blindness depends on a record of who opened which trial's forecasts and when. Reveal, and any other tool that shows a forecast to a person, must write that record before showing it.

**2026-10-08, from ticket 06.** A reveal is a file of openings for one trial, one line each, taken from the private openings of the batch. `trialseal-verify` already checks such a file against a published seal. This ticket adds the step that produces and publishes it, gated on legal sign-off and on an agreed adjudication.

**2026-10-08, from ticket 13.** When adjudicators record a hazard ratio, the tool should offer the trial's scored endpoint as sealed, word for word. The effect-size analysis scores a hazard ratio only if it was recorded under exactly that name; recording it under any other name is how an adjudicator says it is for a different endpoint. Whoever opens a trial's forecasts must not have adjudication of that trial still to do: a trial adjudicated by someone who had opened its forecasts now blocks the final analysis until a blind reading replaces it.

**2026-10-09, from ticket 13 (ADR-0015).** The reveal step must call `record_forecast_access` for every person who will see the forecasts, on the day, before showing anything. The analysis decides which later sources are set aside from that record alone; an opening that is not recorded makes a non-blind reading count as blind.
