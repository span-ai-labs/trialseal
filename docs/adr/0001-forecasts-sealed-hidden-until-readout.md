# Forecasts stay hidden until each trial reads out

At sealing we publish the list of trials and one commitment per forecast, and reveal a trial's forecasts after its readout. A commitment is a fingerprint of the forecast mixed with a secret value, so it discloses nothing, yet lets that one forecast be checked later without revealing any other. Publishing forecasts in clear on day one would be better publicity, but it creates securities exposure around market-moving readouts and could influence investigators or enrolment. The public scoreboard therefore shows resolved trials only.

A single fingerprint over the whole batch was the simpler design. It was rejected because proving one trial's forecast would then mean disclosing every other forecast in the batch.
