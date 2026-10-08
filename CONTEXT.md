# TrialSeal

Forecasting the results of randomised phase 3 cancer trials before they are known, locking each forecast so its date can be proven, and scoring it once the result is public.

## Language

### Trials and results

**Candidate**:
A randomised phase 3 cancer trial in the registry with a time-to-event primary endpoint that has not been withdrawn. A candidate becomes an eligible trial only after screening.
_Avoid_: Universe trial, in-scope trial

**Screening**:
Checking a candidate for an existing public primary result before a batch, with the evidence recorded. Only a candidate screened as having none is an eligible trial.
_Avoid_: Filtering, vetting, pre-check

**Eligible trial**:
A randomised phase 3 cancer trial with a time-to-event primary endpoint and no public primary result on the day a forecast is sealed.
_Avoid_: In-window trial, upcoming trial

**Readout**:
The first public disclosure of a trial's primary analysis, from any source.
_Avoid_: Completion, topline date, publication date

**Registry completion date**:
The primary completion date shown in the trial registry. It is a planning field that often moves and can fall after the readout.
_Avoid_: Readout date, completion

**Positive trial**:
A trial whose readout reports a statistically significant benefit on its primary endpoint: any one endpoint where each suffices, all of them where they are co-primary, or an early stop for efficacy.
_Avoid_: Successful trial, approved, win

**Negative trial**:
A trial whose readout does not meet that bar, including an early stop for futility.
_Avoid_: Failed trial

**Void trial**:
A trial ended for safety, enrolment or strategy without a primary analysis. It has no readout.
_Avoid_: Terminated, cancelled

**Alias record**:
The names a trial's readout may be announced under: its acronym, sponsor study number, other registry numbers, intervention names and code names, and its sponsors.
_Avoid_: Synonyms, search terms

**Exclusion review**:
A flag on a candidate whose design may rule it out, such as a mention of non-inferiority, to be settled by a person before it can be eligible.
_Avoid_: Excluded, filtered out

**Unresolved trial**:
An eligible trial for which no readout has been found by the analysis date.
_Avoid_: Pending, missing, silent trial

**Scored endpoint**:
The single primary endpoint, named when a forecast is sealed, whose reported hazard ratio the effect-size forecast is scored against. It is the first time-to-event primary endpoint listed in the frozen registry record, so a response-rate endpoint listed ahead of it is passed over.
_Avoid_: Main endpoint, key endpoint

### Forecasts

**Forecast**:
For one eligible trial, a probability that it will be a positive trial and a predicted hazard ratio with an interval for its scored endpoint. Where a forecaster could not produce one, the forecast is the record of that, with the reason.
_Avoid_: Prediction, call, bet

**Forecaster**:
Anything that issues forecasts: a model, a fixed rule, or a system built on models.
_Avoid_: Model, contestant, agent

**Frontier model as shipped**:
A vendor's language model queried directly, with no retrieval and no added system, used as a forecaster.
_Avoid_: Raw model, baseline model

**Span forecaster**:
The one named forecasting system Span builds and enters, frozen before each batch.
_Avoid_: Our model, the product

**Endpoint type**:
One of overall survival, progression-type (any endpoint counting disease progression, recurrence or relapse as an event), or other time-to-event.
_Avoid_: Endpoint kind, endpoint category

**Sponsor type**:
Industry-led or not, taken from the lead sponsor.
_Avoid_: Sponsor class, funder type

**Reference class**:
A group of past trials that share sponsor type and endpoint type.
_Avoid_: Bucket, stratum, segment

**Base rate**:
The historical share of positive trials in a trial's reference class, used as its forecast. It is the bar the registered claim must beat.
_Avoid_: Prior, average

**First forecast**:
The earliest sealed forecast a forecaster issued for a trial. The registered primary comparison scores it and no later one.
_Avoid_: Initial prediction, baseline forecast

**Carried forecast**:
A forecast repeated unchanged from the previous batch because nothing new was found about the trial, and recorded as carried.
_Avoid_: Stale forecast, skipped trial

**Forecaster version**:
The tagged state of the Span forecaster sealed with a batch. Later versions never replace an earlier first forecast.
_Avoid_: Release, iteration

**Batch**:
The complete set of forecasts from every forecaster for every eligible trial on one scheduled date.
_Avoid_: Round, run, submission

**Sealing**:
Fixing a batch so that its existence on that date can be proven later, without disclosing the forecasts.
_Avoid_: Committing, locking, publishing

**Commitment**:
A fingerprint of one forecast mixed with a secret value, published at sealing. It lets the forecast be shown later to be the one made that day, without disclosing it or any other.
_Avoid_: Hash, signature, checksum

**Seal**:
What is published when a batch is sealed: its trials, one commitment per forecast, and the anchors for the whole.
_Avoid_: Manifest, snapshot, receipt

**Anchor**:
Proof from an outside time-stamping service that a seal existed on a date. Every seal has two, from independent kinds of service.
_Avoid_: Timestamp, notarisation, stamp

**Opening**:
What is disclosed at reveal for one forecast: the forecast and the secret value behind its commitment.
_Avoid_: Proof, disclosure, key

**Reveal**:
Disclosing a trial's sealed forecasts after its readout.
_Avoid_: Unsealing, release

### Scoring

**Adjudication**:
Two people independently deciding, blind to the forecasts, whether a trial was positive, negative or void, and what hazard ratio was reported.
_Avoid_: Labelling, annotation, resolution

**Awaiting adjudication**:
The state of a trial that has a readout the adjudicators have not yet settled: read by one of them only, or read differently by the two.
_Avoid_: Pending, unresolved, in review

**Reconciliation**:
The two adjudicators' settled reading of a source they first read differently, recorded with its reason. Until it exists the trial has no result.
_Avoid_: Tie-break, override, arbitration

**Primary analysis set**:
The industry-led eligible trials, on which the registered primary comparison is made. Trials from all other sponsors are sealed and scored as a secondary set.
_Avoid_: Main cohort, test set

**Reference set**:
The past trials whose readouts were traced and adjudicated by hand, from which the base rates are taken.
_Avoid_: Training set, historical cohort

**Descriptive look**:
The single mid-study report of scores on a fixed date, made without testing the registered claim.
_Avoid_: Interim analysis, checkpoint

**Final analysis**:
The one test of the registered claim, on a date fixed at registration.
_Avoid_: Readout, result

**Retrospective pilot**:
Forecasts made without web access on trials whose readout came after a model's training cutoff. It tests the method; it is not the evidence.
_Avoid_: Backtest, retrospective arm

**Prospective arm**:
The sealed batches scored against readouts that had not happened when the batch was sealed. It carries the study's claim.
_Avoid_: Live arm, forward test
