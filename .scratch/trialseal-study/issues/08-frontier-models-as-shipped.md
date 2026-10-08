# 08: Frontier models as shipped

**What to build:** Each chosen frontier model forecasts every eligible trial without web access, from identical trial information, several times, with everything needed to judge leakage recorded.

**Blocked by:** 02

**Status:** done

- [x] Each model is called through its plain interface with no tools and no added system
- [x] Every model receives the same trial information, taken from the frozen registry record
- [x] Each trial is forecast several times per model and the runs are combined by a rule fixed in advance
- [x] Model identifier, stated training cutoff, release date and date of use are recorded with every forecast
- [x] Raw model output is kept with each forecast
- [x] A model's failure to answer is recorded as no forecast produced
- [x] Cost per batch is tracked
- [x] Model keys come from the environment and never enter the repository
- [x] Needs the study lead: model keys on the machine

## Comments

**2026-10-08, implemented.** Each model in `study/models.json` is asked one plain prompt through its provider's own library, five times per trial, with no system prompt and no tools. The usable answers are combined (mean probability; geometric mean for the hazard ratio and each end of its interval). Every forecast records the model asked for and the model that answered, the provider's stated cutoff and release date, the date of use, the raw text of every reply, outages, tokens and cost. 144 tests pass. A live check on a trial that has already read out (so it can never be in the study) produced forecasts from Claude Opus 5.5 and GPT-6.1 Sol for about nine cents.

Verified from the providers' own pages on 2026-10-08, and recorded in the roster: Claude Opus 5.5 training cutoff June 2026, $4/$20 per million tokens; GPT-6.1 Sol knowledge cutoff 30 April 2026, $2/$10; Gemini 3.8 Flash knowledge cutoff March 2026 (some domains January 2025), published 2 September 2026, $0.75/$3.75 until the end of 2026.

Review found, and tests now cover: a wrong key or model name was retried and then recorded as a permanent missing forecast (it now stops the batch); refusals were mislabelled; several provider errors crashed the batch; `Infinity` was accepted as a hazard ratio; an earlier draft answer could stand in for a malformed final one; Google got no output cap; unpriced models showed a cost of zero.

Rules introduced here that the study lead has not confirmed:

- The roster itself: one model per provider (Claude Opus 5.5, GPT-6.1 Sol, Gemini 3.8 Flash), with effort `high` where the provider has the setting.
- Asked five times; at least three usable answers are needed, otherwise no forecast is recorded.
- A reply that was refused or cut off is never used, even if an answer can be read from it.
- Only the last answer in a reply counts.
- After an outage at the provider a reply is asked for again up to three more times; a refusal is never asked again.
- A forecaster that produces no forecast is scored at the reference's probability (ADR-0013, proposed).
- A refusal is never passed to another model. Anthropic's library offers an automatic fallback to another model on refusal; it is deliberately not used, because a forecast must be the named model's own.

Known limits:

- Gemini 3.8 Flash returned "high demand" errors on most attempts during the check, and the Pro model returned "quota exceeded", which suggests the Google key is on the free tier.
- Nothing yet builds a real batch from the roster; ticket 15 does that.
- The date of use is recorded but not checked against the batch date.
