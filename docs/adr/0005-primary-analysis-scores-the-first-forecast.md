# The primary analysis scores each trial's first forecast

Every eligible trial is forecast again in every monthly batch, and the Span forecaster may be upgraded between batches under a sealed version tag. The registered primary comparison nonetheless scores only the first forecast each forecaster sealed for a trial. Scoring the latest forecast would look better, since forecasts sharpen as readout approaches, but it would let later upgrades and late information rescue early misses. The last forecast before readout, accuracy against lead time, and scores by forecaster version are secondary.
