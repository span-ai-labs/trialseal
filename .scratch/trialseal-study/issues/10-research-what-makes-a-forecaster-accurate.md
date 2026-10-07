# 10: Research: what makes a forecaster accurate

**What to build:** A cited note on the published methods for building accurate forecasters with language models, so that the Span forecaster starts from what is known.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Covers evidence retrieval, combining several forecasts, calibration, and the use of base rates as a starting point
- [x] Covers what the competing trial-forecasting platform and related studies found about which methods help
- [x] Each claim is traced to its primary source
- [x] Ends with a short list of design choices recommended for the Span forecaster and the evidence for each
- [x] Saved with the other research notes

## Comments

**2026-10-08, done.** The note is at `docs/research/what-makes-a-forecaster-accurate.md` (the project's own research folder, so it travels with the repository). Every claim is tagged by how much of its source was read. It ends with eight design choices for the first Span forecaster and a list of what could not be verified.

Points that bear on later tickets:

- Ticket 11: supply the base rate as a number and blend outside the model with a weight fixed before sealing; compare against several distinct prior trials one difference at a time; average five to ten runs by a plain mean; one plain frozen prompt; no fine-tuning.
- Ticket 11 and 07: build the hazard-ratio interval from reference-set errors, never from the width the model states.
- Ticket 09: fit no calibration; at most one parameter, fixed before sealing, and only if the pilot shows a consistent distortion.
- Ticket 16 and 17: treat the retrieval log as the leak control, with an audit after each readout.
