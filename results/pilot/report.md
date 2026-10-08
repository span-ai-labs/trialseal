# Retrospective pilot

Written 2026-10-08.

This pilot tests the method: the rules, the tooling and the adjudicators' agreement. It is not the evidence for the study's claim, because every forecast in it was made after the trial's result was public.

A model is counted as recalling a result when it says it knows it, gives the right result, and dates its first report to within 3 months. The right result without the right date is shown separately: a model can infer a result and say it knows.

Past trials: 80 with a readout and a clear result, 30 with no readout found.

**Outcomes are provisional.** 0 of the 80 readouts are adjudicated by both adjudicators; the rest were traced from public sources by one reader, an AI research agent, and are not yet adjudicated.

Agreement between the adjudicators is not yet measured.

## claude-opus-5-5

Stated training cutoff 2026-06; released 2026-09-21.

### Cutoff probe (registry record shown)

| Months from stated cutoff | Trials probed | Said it knew | Right result | Right result and date |
|---|---|---|---|---|
| -100 | 1 | 1 | 1 | 1 |
| -83 | 1 | 1 | 1 | 1 |
| -75 | 1 | 1 | 1 | 1 |
| -58 | 1 | 1 | 1 | 1 |
| -49 | 1 | 1 | 1 | 1 |
| -46 | 1 | 1 | 1 | 1 |
| -31 | 1 | 1 | 1 | 0 |
| -30 | 1 | 1 | 1 | 0 |
| -27 | 2 | 2 | 2 | 2 |
| -25 | 1 | 1 | 1 | 1 |
| -24 | 2 | 2 | 2 | 0 |
| -23 | 1 | 1 | 1 | 1 |
| -21 | 1 | 0 | 0 | 0 |
| -18 | 2 | 2 | 2 | 1 |
| -16 | 1 | 1 | 1 | 1 |
| -15 | 1 | 1 | 1 | 1 |
| -14 | 4 | 2 | 2 | 1 |
| -13 | 3 | 2 | 2 | 1 |
| -12 | 2 | 2 | 2 | 1 |
| -9 | 1 | 1 | 1 | 0 |
| -8 | 3 | 3 | 3 | 3 |
| -7 | 6 | 4 | 4 | 4 |
| -6 | 5 | 3 | 3 | 2 |
| -5 | 4 | 2 | 2 | 1 |
| -4 | 2 | 0 | 0 | 0 |
| -3 | 3 | 1 | 1 | 0 |
| -2 | 8 | 0 | 0 | 0 |
| -1 | 3 | 0 | 0 | 0 |
| +0 | 5 | 0 | 0 | 0 |
| +1 | 7 | 0 | 0 | 0 |
| +2 | 3 | 0 | 0 | 0 |
| +3 | 2 | 1 | 1 | 0 |

For trials with no readout it said it knew a result in 0 of 30. 0 replies gave no usable answer.

### Memorisation probe (identifiers alone)

| Months from stated cutoff | Trials probed | Said it knew | Right result | Right result and date |
|---|---|---|---|---|
| -100 | 1 | 1 | 1 | 1 |
| -83 | 1 | 1 | 1 | 1 |
| -75 | 1 | 1 | 1 | 1 |
| -58 | 1 | 1 | 1 | 1 |
| -49 | 1 | 1 | 1 | 1 |
| -46 | 1 | 1 | 1 | 1 |
| -31 | 1 | 1 | 1 | 0 |
| -30 | 1 | 1 | 1 | 0 |
| -27 | 2 | 2 | 2 | 2 |
| -25 | 1 | 1 | 1 | 1 |
| -24 | 2 | 2 | 2 | 0 |
| -23 | 1 | 1 | 1 | 1 |
| -21 | 1 | 0 | 0 | 0 |
| -18 | 2 | 2 | 2 | 1 |
| -16 | 1 | 1 | 1 | 1 |
| -15 | 1 | 1 | 1 | 1 |
| -14 | 4 | 2 | 2 | 1 |
| -13 | 3 | 2 | 2 | 1 |
| -12 | 2 | 2 | 2 | 1 |
| -9 | 1 | 0 | 0 | 0 |
| -8 | 3 | 3 | 3 | 2 |
| -7 | 6 | 3 | 3 | 3 |
| -6 | 5 | 4 | 4 | 3 |
| -5 | 4 | 1 | 1 | 0 |
| -4 | 2 | 0 | 0 | 0 |
| -3 | 3 | 0 | 0 | 0 |
| -2 | 8 | 0 | 0 | 0 |
| -1 | 3 | 0 | 0 | 0 |
| +0 | 5 | 0 | 0 | 0 |
| +1 | 7 | 0 | 0 | 0 |
| +2 | 3 | 0 | 0 | 0 |
| +3 | 2 | 0 | 0 | 0 |

For trials with no readout it said it knew a result in 0 of 30. 0 replies gave no usable answer.

On the two probes together it recalled no result that was disclosed after the month of its stated cutoff. A buffer of 1 month is used, leaving 5 pilot trials.

It gave the right result with a date more than 3 months before the readout on record for: NCT03456063, NCT03602859, NCT03997123, NCT04182204, NCT04338399, NCT04475939, NCT04712097, NCT05008783, NCT05204628, NCT05450692, NCT05668988. Either it inferred these, or an earlier disclosure was missed; their sources should be looked at again.

Forecasts have not yet been made for all 5 pilot trials.

## gpt-6.1-sol

Stated training cutoff 2026-04-30; released 2026-09-28.

### Cutoff probe (registry record shown)

| Months from stated cutoff | Trials probed | Said it knew | Right result | Right result and date |
|---|---|---|---|---|
| -98 | 1 | 1 | 1 | 1 |
| -81 | 1 | 1 | 1 | 1 |
| -73 | 1 | 1 | 1 | 1 |
| -56 | 1 | 1 | 1 | 1 |
| -47 | 1 | 1 | 1 | 1 |
| -44 | 1 | 1 | 1 | 1 |
| -29 | 1 | 1 | 1 | 1 |
| -28 | 1 | 1 | 1 | 1 |
| -25 | 2 | 2 | 2 | 2 |
| -23 | 1 | 1 | 1 | 1 |
| -22 | 2 | 2 | 2 | 1 |
| -21 | 1 | 1 | 1 | 1 |
| -19 | 1 | 0 | 0 | 0 |
| -16 | 2 | 2 | 2 | 1 |
| -14 | 1 | 1 | 1 | 1 |
| -13 | 1 | 1 | 1 | 1 |
| -12 | 4 | 1 | 1 | 1 |
| -11 | 3 | 1 | 1 | 0 |
| -10 | 2 | 2 | 2 | 1 |
| -7 | 1 | 0 | 0 | 0 |
| -6 | 3 | 0 | 0 | 0 |
| -5 | 6 | 2 | 2 | 2 |
| -4 | 5 | 3 | 3 | 3 |
| -3 | 4 | 0 | 0 | 0 |
| -2 | 2 | 0 | 0 | 0 |
| -1 | 3 | 0 | 0 | 0 |
| +0 | 8 | 0 | 0 | 0 |
| +1 | 3 | 0 | 0 | 0 |
| +2 | 5 | 0 | 0 | 0 |
| +3 | 7 | 0 | 0 | 0 |
| +4 | 3 | 0 | 0 | 0 |
| +5 | 2 | 0 | 0 | 0 |

For trials with no readout it said it knew a result in 0 of 30. 0 replies gave no usable answer.

### Memorisation probe (identifiers alone)

| Months from stated cutoff | Trials probed | Said it knew | Right result | Right result and date |
|---|---|---|---|---|
| -98 | 1 | 1 | 1 | 1 |
| -81 | 1 | 1 | 1 | 1 |
| -73 | 1 | 1 | 1 | 1 |
| -56 | 1 | 1 | 1 | 1 |
| -47 | 1 | 1 | 1 | 1 |
| -44 | 1 | 1 | 1 | 1 |
| -29 | 1 | 1 | 1 | 1 |
| -28 | 1 | 1 | 1 | 1 |
| -25 | 2 | 2 | 2 | 2 |
| -23 | 1 | 1 | 1 | 1 |
| -22 | 2 | 2 | 2 | 2 |
| -21 | 1 | 1 | 1 | 1 |
| -19 | 1 | 0 | 0 | 0 |
| -16 | 2 | 2 | 2 | 1 |
| -14 | 1 | 1 | 1 | 1 |
| -13 | 1 | 1 | 1 | 0 |
| -12 | 4 | 1 | 1 | 1 |
| -11 | 3 | 0 | 0 | 0 |
| -10 | 2 | 2 | 2 | 1 |
| -7 | 1 | 0 | 0 | 0 |
| -6 | 3 | 1 | 1 | 0 |
| -5 | 6 | 2 | 2 | 2 |
| -4 | 5 | 3 | 3 | 3 |
| -3 | 4 | 0 | 0 | 0 |
| -2 | 2 | 0 | 0 | 0 |
| -1 | 3 | 0 | 0 | 0 |
| +0 | 8 | 0 | 0 | 0 |
| +1 | 3 | 0 | 0 | 0 |
| +2 | 5 | 0 | 0 | 0 |
| +3 | 7 | 0 | 0 | 0 |
| +4 | 3 | 0 | 0 | 0 |
| +5 | 2 | 0 | 0 | 0 |

For trials with no readout it said it knew a result in 0 of 30. 0 replies gave no usable answer.

On the two probes together it recalled no result that was disclosed after the month of its stated cutoff. A buffer of 1 month is used, leaving 17 pilot trials.

It gave the right result with a date more than 3 months before the readout on record for: NCT04704934. Either it inferred these, or an earlier disclosure was missed; their sources should be looked at again.

### Scores

Forecasts made with no web access for 17 pilot trials; 0 scored at the reference because no forecast was produced. On one probe or the other it said it knew the result of 0 of them, without recalling it by the test above.

- Brier score, model minus base rate: -0.058 over 17 trials.
- CRPS of the log hazard ratio, model minus effect-size baseline: -0.043 over 6 trials.

## Sample size

This pilot tests the method: the rules, the tooling and the adjudicators' agreement. It is not the evidence for the study's claim, because every forecast in it was made after the trial's result was public.

From the spread of per-trial score differences, for a paired comparison at two-sided 5% with 80% power. Trials of one drug are treated as independent, so the true requirement is somewhat larger. The spread is that of frontier models as shipped against the base rate; the forecaster that carries the registered claim may differ.

- gpt-6.1-sol, Brier score, model minus base rate: mean difference -0.058, standard deviation 0.114 (95% interval 0.085 to 0.174) over 17 trials.
  - With that spread, 120 trials detect a mean difference of 0.029 (or 0.044 if the spread is at the upper end of its interval); 60 trials detect a mean difference of 0.041 (or 0.063 if the spread is at the upper end of its interval).
  - Trials needed to detect an assumed mean difference: 0.01 needs 1025; 0.02 needs 257; 0.03 needs 114; 0.05 needs 41.
- gpt-6.1-sol, CRPS of the log hazard ratio, model minus effect-size baseline: mean difference -0.043, standard deviation 0.080 (95% interval 0.050 to 0.196) over 6 trials.
  - With that spread, 120 trials detect a mean difference of 0.020 (or 0.050 if the spread is at the upper end of its interval); 60 trials detect a mean difference of 0.029 (or 0.071 if the spread is at the upper end of its interval).
  - Trials needed to detect an assumed mean difference: 0.01 needs 499; 0.02 needs 125; 0.03 needs 56; 0.05 needs 20.
