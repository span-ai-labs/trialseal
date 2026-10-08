---
status: proposed
---

# A forecaster that produces no forecast is scored at the reference's probability

When a forecaster's first forecast for a trial records that none was produced (its replies were refused, cut off or unusable), the primary comparison scores that trial as if the forecaster had given the reference's probability, and lists the trial. Leaving such trials out was the simpler rule, but a forecaster could then improve its score by declining the trials it finds hardest, and because the first forecast is the one scored (ADR-0005) the exclusion would be permanent. Scoring at the reference makes declining worth exactly nothing. Proposed during ticket 08; it needs the study lead's confirmation before the protocol is written.
