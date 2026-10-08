---
status: accepted
---

# A forecaster that produces no forecast is scored at the reference's probability

When a forecaster's first forecast for a trial records that none was produced (its replies were refused, cut off or unusable), the primary comparison scores that trial as if the forecaster had given the reference's probability, and lists the trial. Leaving such trials out was the simpler rule, but a forecaster could then improve its score by declining the trials it finds hardest, and because the first forecast is the one scored (ADR-0005) the exclusion would be permanent. Scoring at the reference makes declining worth exactly nothing. The study lead confirmed this on 2026-10-08.

The same rule covers a forecaster that was not in the batch at all, for example one that joined the study after a trial was first sealed or was renamed: its later forecast for that trial is not a first forecast, so it is scored at the reference's. It applies to every score, not only the Brier score: calibration and discrimination are computed with the reference's probability standing in, and an effect-size forecast that was not produced is scored at the baseline's hazard ratio. In the analysis of the last forecast before readout, a record of no forecast in that last batch is likewise scored at the reference's; the forecaster's earlier forecast is not brought forward.
