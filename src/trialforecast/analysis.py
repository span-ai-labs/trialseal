"""The registered analysis plan: sealed forecasts and adjudicated results in, every registered table out.

Every comparison is paired, trial by trial: a forecaster against a reference, each
on the forecast it had sealed for that trial. The primary comparison uses first
forecasts in the primary analysis set (ADR-0003, ADR-0005). Where a forecaster has
no forecast to score, it is scored at the reference's (ADR-0013). The descriptive
look and the final analysis are each made once, on a fixed date (ADR-0007).
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
import pathlib
import re
from dataclasses import dataclass
from functools import cached_property
from typing import Iterable

import numpy as np
from scipy.stats import norm

from trialforecast import records, scoring
from trialforecast.adjudication import (
    HAZARD_RATIO_WINDOW_MONTHS, LOG_KINDS, WITH_READOUT, AdjudicationLog, TrialResult, awaiting_result, entered_on,
    results, set_aside,
)
from trialforecast.batch import Batch, BatchTrial
from trialforecast.dates import add_months
from trialforecast.forecasting import Forecast
from trialforecast.screening import ScreeningRecord, found_no_result
from trialforecast.sealing import Plan

PRIMARY_ANALYSIS_SET = "industry"  # sponsor type; see ADR-0003
ALL_SPONSORS = None

# ADR-0007: one look, one final analysis, one extension.
DESCRIPTIVE_LOOK_ON = dt.date(2027, 4, 15)
FINAL_ANALYSIS_MONTHS, EXTENDED_MONTHS = 18, 24
TRIALS_NEEDED, TRIALS_NEEDED_AFTER_EXTENSION = 120, 60
# Resampling drug groups says little about uncertainty when there are few of them, so no claim rests on fewer.
DRUG_GROUPS_NEEDED = 30

RESAMPLES = 10_000
CALIBRATION_BINS = 10
INTERVAL_LEVEL = 0.8  # a hazard-ratio forecast gives its median and this central interval
# Days from the forecast to the readout; the last band has no upper limit.
LEAD_TIME_BANDS = (("under 3 months", 91), ("3 to 6 months", 183), ("6 to 12 months", 366), ("over 12 months", None))

# Each sensitivity analysis is the primary comparison with one thing changed.
SENSITIVITY_ANALYSES = {
    "all sponsors": {"sponsor_type": ALL_SPONSORS},
    "last forecast before readout": {"last_forecast": True},
    "without non-English disclosures": {"english_only": True},
    "void counted as negative": {"void_as_negative": True},
    "unresolved imputed as negative": {"impute_unresolved": "negative"},
    "unresolved imputed as positive": {"impute_unresolved": "positive"},
}


class NotDue(Exception):
    """A registered analysis was asked for before its fixed date."""


class NotReady(Exception):
    """The final analysis was asked for before every sealed trial was accounted for."""


class AlreadyRun(Exception):
    """A registered analysis was asked for again, and what it was first run on has changed since."""


def in_date_order(batches: Iterable[Batch]) -> list[Batch]:
    """Batches from earliest to latest. Two on one date would leave the first forecast undefined."""
    ordered = sorted(batches, key=lambda b: b.batch_date)
    for earlier, later in zip(ordered, ordered[1:]):
        if earlier.batch_date == later.batch_date:
            raise ValueError(f"two batches are dated {later.batch_date}")
    return ordered


# --- what an analysis may use --------------------------------------------------------


@dataclass(frozen=True)
class StudyState:
    """The study as an analysis sees it: the batches sealed and the results disclosed by its date."""

    batches: tuple[Batch, ...]  # in date order
    results: dict[str, TrialResult]
    awaiting_adjudication: dict[str, str]
    readouts_to: dt.date
    set_aside: dict[str, list[str]] = dataclasses.field(default_factory=dict)  # later sources read after a reveal (ADR-0015)

    @cached_property
    def batches_of(self) -> dict[str, list[tuple[Batch, BatchTrial]]]:
        """Each trial's batches in date order, with what each fixed about it. The first is where it was first sealed."""
        found: dict[str, list[tuple[Batch, BatchTrial]]] = {}
        for batch in self.batches:
            for trial in batch.trials:
                found.setdefault(trial.nct, []).append((batch, trial))
        return found

    @cached_property
    def _forecasts(self) -> dict[tuple[dt.date, str], dict[str, Forecast]]:
        return {(batch.batch_date, name): {f.nct: f for f in forecasts}
                for batch in self.batches for name, forecasts in batch.forecasts.items()}

    def forecast(self, batch: Batch, forecaster: str, nct: str) -> Forecast | None:
        """What a forecaster sealed for a trial in a batch, or None if it was not a forecaster in that batch."""
        return self._forecasts.get((batch.batch_date, forecaster), {}).get(nct)

    @property
    def forecasters(self) -> list[str]:
        return sorted({name for batch in self.batches for name in batch.forecasts})


def study_state(
    batches: Iterable[Batch], log: AdjudicationLog, adjudicated_by: dt.date, readouts_to: dt.date | None = None,
    count_set_aside: bool = False,
) -> StudyState:
    """Gather what an analysis may use.

    An analysis fixed for a date passes it as `readouts_to`. Batches sealed after
    it and sources disclosed after it are then left out, however long after that
    date adjudication went on, so that the day the analysis is run decides nothing.
    Sources read after a trial's forecasts were opened are set aside unless
    `count_set_aside` is given, as one sensitivity analysis does (ADR-0015).
    """
    readouts_to = readouts_to or adjudicated_by
    ordered = tuple(b for b in in_date_order(batches) if b.batch_date <= readouts_to)
    sealed = {trial.nct for batch in ordered for trial in batch.trials}
    found = results(log, adjudicated_by, readouts_to, count_set_aside)
    aside = {} if count_set_aside else set_aside(log, adjudicated_by, readouts_to)
    return StudyState(
        batches=ordered,
        results={nct: result for nct, result in found.items() if nct in sealed},
        awaiting_adjudication={nct: why for nct, why in sorted(awaiting_result(log, adjudicated_by, readouts_to).items())
                               if nct in sealed},
        readouts_to=readouts_to,
        set_aside={nct: refs for nct, refs in sorted(aside.items()) if nct in sealed},
    )


# --- paired comparisons ----------------------------------------------------------------


@dataclass(frozen=True)
class Pair:
    """One trial in a paired comparison: what happened, and what each side had sealed for it."""

    trial: BatchTrial
    positive: bool
    result: TrialResult | None  # None where the outcome was imputed
    own: Forecast | None  # None where the forecaster had no forecast and is scored at the reference's
    reference: Forecast

    @property
    def scored(self) -> Forecast:
        return self.own or self.reference

    @property
    def drug_group(self) -> str:
        """Trials of one investigational drug are resampled together; a trial with none recorded stands alone."""
        return self.trial.investigational_drug or self.trial.nct

    @property
    def lead_days(self) -> int | None:
        """Days from the batch scored to the readout. Both sides' forecasts come from that one batch."""
        if self.result is None or self.result.readout_date is None:
            return None
        return (self.result.readout_date - self.reference.batch_date).days


@dataclass(frozen=True)
class Comparison:
    """A forecaster paired with a reference on every trial that could be scored, with what was left out or filled in."""

    forecaster: str
    reference: str
    pairs: tuple[Pair, ...]
    scored_at_reference: dict[str, str]  # trial, then why the forecaster had no forecast of its own
    forecast_not_before_readout: tuple[str, ...]


def _last_day(registry_date: str) -> dt.date:
    """The last day a registry date can mean: the registry often gives only a month."""
    if len(registry_date) == 10:
        return dt.date.fromisoformat(registry_date)
    return add_months(dt.date.fromisoformat(f"{registry_date}-01"), 1) - dt.timedelta(days=1)


def _what_happened(
    state: StudyState, trial: BatchTrial, void_as_negative: bool, impute_unresolved: str | None
) -> tuple[bool, dt.date | None, TrialResult | None] | None:
    """Whether a trial counts as positive, and the day that became known, or None if it is not scored.

    An unresolved trial is imputed only once the registry completion date fixed at
    its first sealing has passed, and never while it awaits adjudication.
    """
    result = state.results.get(trial.nct)
    if result is None:
        completion = trial.registry_completion_date
        overdue = completion is not None and _last_day(completion) <= state.readouts_to
        if impute_unresolved is None or not overdue or trial.nct in state.awaiting_adjudication:
            return None
        return impute_unresolved == "positive", None, None
    if result.outcome in WITH_READOUT:
        return result.outcome == "positive", result.readout_date, result
    return (False, result.first_disclosed_on, result) if void_as_negative else None


def paired(
    state: StudyState,
    forecaster: str,
    reference: str,
    *,
    sponsor_type: str | None = PRIMARY_ANALYSIS_SET,
    last_forecast: bool = False,
    void_as_negative: bool = False,
    english_only: bool = False,
    impute_unresolved: str | None = None,
) -> Comparison:
    """Pair a forecaster with a reference on every trial that can be scored.

    By default: trials of the primary analysis set with a positive or negative
    result, each scored on the forecasts in the batch that first sealed it. A trial
    first sealed on or after its readout is one screening missed; it is listed
    and not scored. A forecaster that was not in the batch, or recorded that it
    produced no forecast, is scored at the reference's forecast and listed, so that
    neither declining a trial nor joining late can improve a score.

    The options each change one thing: `sponsor_type=ALL_SPONSORS`; the last
    batch sealed before the readout in place of the first; a void trial counted
    as negative; trials disclosed in a language other than English left out; and
    unresolved trials counted as "negative" or as "positive".
    """
    if impute_unresolved not in (None, "negative", "positive"):
        raise ValueError(f"unresolved trials are imputed as negative or as positive, not {impute_unresolved!r}")
    pairs, at_reference, not_before_readout = [], {}, []
    for nct, sealed_in in sorted(state.batches_of.items()):
        first_batch, trial = sealed_in[0]
        if sponsor_type is not ALL_SPONSORS and trial.sponsor_type != sponsor_type:
            continue
        happened = _what_happened(state, trial, void_as_negative, impute_unresolved)
        if happened is None:
            continue
        positive, known_on, result = happened
        if english_only and result is not None and result.disclosure_language != "en":
            continue
        if known_on is not None and first_batch.batch_date >= known_on:
            not_before_readout.append(nct)
            continue
        batch = first_batch
        if last_forecast:
            batch = [b for b, _ in sealed_in if known_on is None or b.batch_date < known_on][-1]
        theirs = state.forecast(batch, reference, nct)
        if theirs is None or theirs.no_forecast:
            raise ValueError(f"{reference} has no forecast for {nct} in the batch of {batch.batch_date}, "
                             f"so it cannot be the reference of a comparison")
        own = state.forecast(batch, forecaster, nct)
        if own is None:
            at_reference[nct] = f"not a forecaster in the batch of {batch.batch_date}"
        elif own.no_forecast:
            at_reference[nct], own = own.no_forecast, None
        pairs.append(Pair(trial, positive, result, own, theirs))
    return Comparison(forecaster, reference, tuple(pairs), at_reference, tuple(not_before_readout))


def _probabilities(comparison: Comparison) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For each trial: whether it was positive, the probability scored for the forecaster, and the reference's."""
    positive = np.array([float(p.positive) for p in comparison.pairs], dtype=float)
    own = np.array([p.scored.probability_positive for p in comparison.pairs], dtype=float)
    theirs = np.array([p.reference.probability_positive for p in comparison.pairs], dtype=float)
    return positive, own, theirs


def _mean(values) -> float | None:
    return float(np.mean(values)) if len(values) else None


def _difference(own_scores, reference_scores, pairs: Iterable[Pair], n_boot: int) -> dict | None:
    """The mean paired difference in a score, resampling whole drug groups. Negative favours the forecaster.

    With fewer drug groups than a claim may rest on, resampling them says little
    (one group gives an interval of no width), so the difference is then given
    without an interval or a p-value.
    """
    groups = [p.drug_group for p in pairs]
    if not groups:
        return None
    if len(set(groups)) < DRUG_GROUPS_NEEDED:
        return {"mean_diff": float(np.mean(np.asarray(own_scores) - np.asarray(reference_scores))), "ci_low": None,
                "ci_high": None, "p_two_sided": None, "n_trials": len(groups), "n_clusters": len(set(groups))}
    return scoring.paired_cluster_bootstrap(own_scores, reference_scores, groups, n_boot=n_boot)


def summarise(comparison: Comparison, n_boot: int = RESAMPLES) -> dict:
    """A paired comparison of probabilities: Brier scores and their difference, with what was left out or filled in."""
    positive, own, theirs = _probabilities(comparison)
    own, theirs = (own - positive) ** 2, (theirs - positive) ** 2
    return {
        "n_trials": len(comparison.pairs),
        "n_drug_groups": len({p.drug_group for p in comparison.pairs}),
        "brier": {comparison.forecaster: _mean(own), comparison.reference: _mean(theirs)},
        "difference": _difference(own, theirs, comparison.pairs, n_boot),
        "forecast_not_before_readout": list(comparison.forecast_not_before_readout),
        "scored_at_reference": dict(comparison.scored_at_reference),
    }


def primary_comparison(state: StudyState, forecaster: str, reference: str, n_boot: int = RESAMPLES) -> dict:
    """The registered comparison: first forecasts, primary analysis set, Brier score."""
    return {**summarise(paired(state, forecaster, reference), n_boot),
            "awaiting_adjudication": dict(state.awaiting_adjudication)}


AFTER_REVEAL = "with sources read after the forecasts were opened"


def sensitivity_analyses(
    state: StudyState, with_set_aside: StudyState, forecaster: str, reference: str, n_boot: int = RESAMPLES
) -> dict[str, dict]:
    """The primary comparison repeated with one thing changed each time.

    The last of them counts the later sources that were set aside because they
    were read after a trial's forecasts had been opened (ADR-0015), which needs
    the study's state gathered with those readings counted.
    """
    analyses = {name: summarise(paired(state, forecaster, reference, **selection), n_boot)
                for name, selection in SENSITIVITY_ANALYSES.items()}
    analyses[AFTER_REVEAL] = summarise(paired(with_set_aside, forecaster, reference), n_boot)
    return analyses


def _brier_by(comparison: Comparison, label: str, group_of, groups: Iterable[str]) -> list[dict]:
    positive, own, theirs = _probabilities(comparison)
    belongs = np.array([group_of(pair) for pair in comparison.pairs], dtype=object)
    return [{label: group, "n_trials": int((belongs == group).sum()),
             "brier": {comparison.forecaster: _mean(((own - positive) ** 2)[belongs == group]),
                       comparison.reference: _mean(((theirs - positive) ** 2)[belongs == group])}}
            for group in groups]


def by_lead_time(state: StudyState, forecaster: str, reference: str) -> list[dict]:
    """Brier scores of the primary comparison by how long before the readout the first forecast was sealed."""
    def band(pair: Pair) -> str:
        return next(name for name, below in LEAD_TIME_BANDS if below is None or pair.lead_days < below)

    return _brier_by(paired(state, forecaster, reference), "lead_time", band, [name for name, _ in LEAD_TIME_BANDS])


def by_forecaster_version(state: StudyState, forecaster: str, reference: str) -> list[dict]:
    """Brier scores of the primary comparison by the version of the forecaster that issued each first forecast."""
    comparison = paired(state, forecaster, reference)

    def version(pair: Pair) -> str:
        return pair.own.version if pair.own else "scored at reference"

    return _brier_by(comparison, "version", version, sorted({version(pair) for pair in comparison.pairs}))


# --- every forecaster's scores -------------------------------------------------------


def _calibration(probability: np.ndarray, positive: np.ndarray) -> list[dict]:
    """Mean forecast against the share of positive trials, in equal-width bins that hold a forecast."""
    which = np.minimum((probability * CALIBRATION_BINS).astype(int), CALIBRATION_BINS - 1)
    return [{"from": b / CALIBRATION_BINS, "to": (b + 1) / CALIBRATION_BINS, "n": int((which == b).sum()),
             "mean_forecast": float(probability[which == b].mean()), "share_positive": float(positive[which == b].mean())}
            for b in sorted(set(which.tolist()))]


def forecaster_scores(state: StudyState, reference: str, sponsor_type: str | None = PRIMARY_ANALYSIS_SET) -> dict[str, dict]:
    """Each forecaster's Brier score, log score, calibration and discrimination on first forecasts.

    Every score covers every scored trial, with the reference's probability where
    the forecaster had none. Rows are then comparable, and a forecaster cannot
    look better calibrated or more discriminating by declining its hardest trials.
    """
    table = {}
    for name in state.forecasters:
        comparison = paired(state, name, reference, sponsor_type=sponsor_type)
        positive, said, _ = _probabilities(comparison)
        row = {"n_trials": len(comparison.pairs), "scored_at_reference": len(comparison.scored_at_reference),
               "brier": None, "log_score": None, "auc": None, "reliability": None, "resolution": None,
               "uncertainty": None, "calibration": []}
        if comparison.pairs:
            discrimination = scoring.auc(said, positive)
            row.update(scoring.murphy_decomposition(said, positive, bins=CALIBRATION_BINS),
                       brier=scoring.brier(said, positive), log_score=scoring.log_score(said, positive),
                       auc=None if math.isnan(discrimination) else discrimination,
                       calibration=_calibration(said, positive))
        table[name] = row
    return table


# --- effect size -------------------------------------------------------------------


def _words(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def same_endpoint(reported_for: str, trial: BatchTrial) -> bool:
    """Whether a hazard ratio was recorded as being for the trial's scored endpoint: the same words, whatever the case.

    Nothing looser is accepted. Whether "PFS by investigator" answers a scored
    endpoint of "PFS by central review" is for the adjudicators to judge, blind;
    they say yes by recording the hazard ratio under the scored endpoint's own name.
    """
    return _words(reported_for) == _words(trial.scored_endpoint)


def scored_hazard_ratio(result: TrialResult, trial: BatchTrial, as_of: dt.date) -> tuple[float | None, str]:
    """The hazard ratio a trial's effect-size forecast is scored against, and where that stands.

    It is the first reported for the scored endpoint within six months of the
    readout (ADR-0011). A hazard ratio for another endpoint that came first is
    passed over. Until the six months are up one is still awaited; on the day they are up it is missing.
    """
    deadline = add_months(result.readout_date, HAZARD_RATIO_WINDOW_MONTHS)
    in_time = [r for r in result.history if r.hazard_ratio is not None and r.disclosed_on <= deadline]
    for reading in in_time:
        if same_endpoint(reading.hazard_ratio_endpoint, trial):
            return reading.hazard_ratio, "reported"
    if as_of < deadline:
        return None, "awaited"
    return None, "another_endpoint" if in_time else "missing"


def log_hazard_ratio(forecast: Forecast) -> tuple[float, float, float, float]:
    """A hazard-ratio forecast on the log scale: median, the spread its interval implies if normal, and the interval."""
    low, high = math.log(forecast.hazard_ratio_low), math.log(forecast.hazard_ratio_high)
    half_interval_in_sds = norm.ppf(0.5 + INTERVAL_LEVEL / 2)
    return math.log(forecast.hazard_ratio), (high - low) / (2 * half_interval_in_sds), low, high


def effect_size_comparison(
    state: StudyState, forecaster: str, baseline: str, sponsor_type: str | None = PRIMARY_ANALYSIS_SET,
    n_boot: int = RESAMPLES, missing_as_no_effect: bool = False, hazard_ratios_from: StudyState | None = None,
) -> dict:
    """Hazard-ratio forecasts against a baseline's, on first forecasts, scored on the log scale.

    The continuous ranked probability score treats each forecast as a normal
    distribution on the log scale; the interval score uses the stated 80% interval
    as given. A forecaster with no forecast is scored at the baseline's (ADR-0013).

    Trials whose hazard ratio never came are more often negative, so leaving them
    out flatters a forecaster that expects benefit. The sensitivity analysis of
    ADR-0011 counts each as a hazard ratio of 1; one still awaited is left out of both.

    The trials scored are those of `state`. Their hazard ratios may be taken from
    another state: one that counts sources set aside for the outcome, since a
    hazard ratio is a number copied from a source and is used whoever read it
    (ADR-0015); and, for the follow-up, the study as it stands six months after
    the final analysis (ADR-0014).
    """
    later = hazard_ratios_from or state
    comparison = paired(state, forecaster, baseline, sponsor_type=sponsor_type)
    left_out: dict[str, list[str]] = {"awaited": [], "missing": [], "another_endpoint": []}
    scored, observed, read_after_reveal = [], [], []
    for pair in comparison.pairs:
        seen_later = later.results.get(pair.trial.nct)
        if seen_later is None or seen_later.readout_date is None:  # a later reading may have made the trial void
            seen_later = pair.result
        hazard_ratio, status = scored_hazard_ratio(seen_later, pair.trial, later.readouts_to)
        if hazard_ratio is not None and scored_hazard_ratio(pair.result, pair.trial, later.readouts_to)[0] != hazard_ratio:
            read_after_reveal.append(pair.trial.nct)
        if hazard_ratio is None:
            left_out[status].append(pair.trial.nct)
            if missing_as_no_effect and status != "awaited":
                hazard_ratio = 1.0
        if hazard_ratio is not None:
            scored.append(pair)
            observed.append(math.log(hazard_ratio))
    observed = np.array(observed)
    crps, interval, covered = {}, {}, {}
    for name, forecasts in ((forecaster, [p.scored for p in scored]), (baseline, [p.reference for p in scored])):
        median, spread, low, high = np.array([log_hazard_ratio(f) for f in forecasts], dtype=float).reshape(-1, 4).T
        crps[name] = scoring.crps_normal(median, spread, observed)
        interval[name] = scoring.interval_score(low, high, observed, alpha=1 - INTERVAL_LEVEL)
        covered[name] = (low <= observed) & (observed <= high)
    return {
        "n_trials": len(scored),
        "crps": {name: _mean(each) for name, each in crps.items()},
        "interval_score": {name: _mean(each) for name, each in interval.items()},
        "coverage": {name: _mean(each) for name, each in covered.items()},
        "difference": _difference(crps[forecaster], crps[baseline], scored, n_boot),
        "scored_at_baseline": {p.trial.nct: comparison.scored_at_reference[p.trial.nct] for p in scored if p.own is None},
        "hazard_ratio_read_after_reveal": read_after_reveal if later.set_aside == {} and later is not state else [],
        "hazard_ratio_awaited": left_out["awaited"],
        "hazard_ratio_missing": left_out["missing"],
        "hazard_ratio_for_another_endpoint": left_out["another_endpoint"],
    }


# --- one row per model ---------------------------------------------------------------


def _one_or_all(values: Iterable):
    """The value every forecast agreed on, or all of them, so that a change mid-study cannot go unseen."""
    distinct = sorted({v for v in values if v is not None})
    if len(distinct) <= 1:
        return distinct[0] if distinct else None
    return "; ".join(str(v) for v in distinct)


def model_table(state: StudyState) -> list[dict]:
    """For each forecaster built on a model: what its provider states, when it was used, and the readouts it is scored on.

    A readout counts if the model sealed a forecast for the trial in any batch
    before it, for any sponsor, since some registered analysis scores that
    forecast. A reader checks from this that every such readout came after the
    model's training cutoff.
    """
    rows = []
    for name in state.forecasters:
        issued = [f for batch in state.batches for f in batch.forecasts.get(name, ()) if f.model is not None]
        if not issued:
            continue
        readouts = []
        for nct, sealed_in in state.batches_of.items():
            readout = getattr(state.results.get(nct), "readout_date", None)
            sealed = [state.forecast(batch, name, nct) for batch, _ in sealed_in]
            if readout is not None and any(f and not f.no_forecast and f.batch_date < readout for f in sealed):
                readouts.append(readout)
        used = [f.used_on for f in issued if f.used_on is not None]
        rows.append({
            "forecaster": name,
            "model": _one_or_all(f.model for f in issued),
            "model_served": _one_or_all(f.model_served for f in issued),
            "training_cutoff": _one_or_all(f.model_training_cutoff for f in issued),
            "released_on": _one_or_all(f.model_released_on for f in issued),
            "first_used_on": min(used, default=None), "last_used_on": max(used, default=None),
            "trials_scored": len(readouts),
            "earliest_readout_scored": min(readouts, default=None), "latest_readout_scored": max(readouts, default=None),
        })
    return rows


# --- the two registered analyses ---------------------------------------------------------

LOOK, EXTENSION, FINAL, FOLLOW_UP = "descriptive_look", "extension", "final_analysis", "effect_size_follow_up"


@dataclass(frozen=True)
class AnalysisRecord:
    """That a registered analysis was run, on what and with what outcome, so that it cannot be run again on anything else.

    The file of these records is part of the public record of the study: it is
    published when written, and its absence after the date of an analysis is itself a finding.
    """

    kind: str
    run_on: dt.date
    readouts_to: dt.date
    n_trials: int
    batches: tuple[str, ...]  # the fingerprint of every batch sealed when it was run, including any it did not use
    log_entries: tuple[int, ...]  # how much of the adjudication log existed when it was run
    resamples: int
    inputs_sha256: str
    outputs_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "batches", tuple(self.batches))
        object.__setattr__(self, "log_entries", tuple(self.log_entries))
        if self.kind not in (LOOK, EXTENSION, FINAL, FOLLOW_UP):
            raise ValueError(f"{self.kind!r} is not a registered analysis")


def _history(record_file: pathlib.Path, batches: list[Batch], log: AdjudicationLog) -> list[AnalysisRecord]:
    """The registered analyses already run, once each is shown to rest on batches and a log that are still there.

    Every batch sealed when an analysis was run must still be among the sealed
    batches, in the same place. The log may have grown since, but only with entries
    dated on or after the run: an earlier-dated entry that was not in the log then
    is either back-dated or was held back from the analysis.
    """
    history = records.read(record_file, AnalysisRecord) if record_file.exists() else []
    sealed = [batch.fingerprint for batch in batches]
    for record in history:
        what = f"the {record.kind.replace('_', ' ')} was recorded on {record.run_on}"
        if list(record.batches) != sealed[:len(record.batches)]:
            raise AlreadyRun(f"{what}; a batch sealed by then is no longer among the sealed batches")
        try:
            added = log.added_after(record.log_entries)
        except ValueError as shorter:
            raise AlreadyRun(f"{what}, and {shorter}") from shorter
        if any(entered_on(entry) < record.run_on for entry in added):
            raise AlreadyRun(f"{what}; the adjudication log now holds an entry dated before that day which it did not hold then")
    return history


def _inputs_fingerprint(state: StudyState, log: AdjudicationLog, plan: Plan) -> str:
    """One SHA-256 over the plan, the batches used, and the adjudication log in the order it was recorded."""
    digest = hashlib.sha256(records.to_line(plan).encode())
    for batch in state.batches:
        digest.update(batch.fingerprint.encode())
    for kind in LOG_KINDS:
        for entry in getattr(log, kind):
            digest.update(f"\n{kind} {records.to_line(entry)}".encode())
    return digest.hexdigest()


def _fingerprints(batches: Iterable[Batch]) -> tuple[str, ...]:
    return tuple(batch.fingerprint for batch in batches)


def _outputs_fingerprint(output: dict) -> str:
    return hashlib.sha256(json.dumps(output, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def _as_first_run(
    kind: str, history: Iterable[AnalysisRecord], log: AdjudicationLog, today: dt.date
) -> tuple[AnalysisRecord | None, AdjudicationLog, dt.date]:
    """The record of an analysis already run, with the log and the day as they stood then; else the log and day as they are."""
    earlier = next((r for r in history if r.kind == kind), None)
    if earlier is None:
        return None, log, today
    return earlier, log.first(earlier.log_entries), earlier.run_on


def _require_unchanged(earlier: AnalysisRecord | None, what: str, recorded: str | None, now: str) -> None:
    if earlier is not None and recorded != now:
        raise AlreadyRun(
            f"the {earlier.kind.replace('_', ' ')} was run on {earlier.run_on}; {what} no longer what it was run on"
        )


_INPUTS, _OUTPUTS = "the plan, the sealed forecasts or the adjudications are", "what it produces is"


def descriptive_look(
    batches: Iterable[Batch], log: AdjudicationLog, plan: Plan, today: dt.date, record_file: pathlib.Path
) -> dict:
    """The single mid-study report: every forecaster's scores, and no comparison between them.

    It covers readouts up to its fixed date however late it is run. Once run it is
    recorded, and can afterwards only be regenerated as it was: from the same
    forecasts and the adjudication log as it then stood.
    """
    if today < DESCRIPTIVE_LOOK_ON:
        raise NotDue(f"the descriptive look is fixed for {DESCRIPTIVE_LOOK_ON}")
    batches = in_date_order(batches)
    earlier, log, run_on = _as_first_run(LOOK, _history(record_file, batches, log), log, today)
    state = study_state(batches, log, run_on, DESCRIPTIVE_LOOK_ON)
    inputs = _inputs_fingerprint(state, log, plan)
    _require_unchanged(earlier, _INPUTS, earlier and earlier.inputs_sha256, inputs)
    n_trials = len(paired(state, plan.forecaster, plan.reference).pairs)
    look = {
        "kind": LOOK, "run_on": run_on, "readouts_to": DESCRIPTIVE_LOOK_ON, "n_trials": n_trials,
        "forecasters": forecaster_scores(state, plan.reference),
        "forecasters_all_sponsors": forecaster_scores(state, plan.reference, sponsor_type=ALL_SPONSORS),
        "awaiting_adjudication": dict(state.awaiting_adjudication),
        "models": model_table(state),
    }
    outputs = _outputs_fingerprint(look)
    _require_unchanged(earlier, _OUTPUTS, earlier and earlier.outputs_sha256, outputs)
    if earlier is None:
        records.append(record_file, AnalysisRecord(LOOK, run_on, DESCRIPTIVE_LOOK_ON, n_trials, _fingerprints(batches),
                                                   log.sizes(), 0, inputs, outputs))
    return look


def _without_tests(value):
    """An analysis with every p-value removed, for a study too small to make its claim."""
    if isinstance(value, dict):
        return {k: _without_tests(v) for k, v in value.items() if k != "p_two_sided"}
    return [_without_tests(v) for v in value] if isinstance(value, list) else value


def _recorded_extension(
    history: Iterable[AnalysisRecord], batches: list[Batch], log: AdjudicationLog, plan: Plan
) -> AnalysisRecord | None:
    """The recorded extension, if there is one and it follows from what it was decided on."""
    extension = next((r for r in history if r.kind == EXTENSION), None)
    if extension is None:
        return None
    first_sealing = batches[0].batch_date
    decided_at = add_months(first_sealing, FINAL_ANALYSIS_MONTHS)
    _, as_decided, _ = _as_first_run(EXTENSION, [extension], log, extension.run_on)
    state = study_state(batches, as_decided, extension.run_on, decided_at)
    n_trials = len(paired(state, plan.forecaster, plan.reference).pairs)
    follows = (
        extension.run_on >= decided_at and extension.readouts_to == add_months(first_sealing, EXTENDED_MONTHS)
        and extension.n_trials == n_trials < TRIALS_NEEDED
        and extension.inputs_sha256 == _inputs_fingerprint(state, as_decided, plan)
    )
    if not follows:
        raise AlreadyRun("the recorded extension does not follow from the sealed forecasts and the adjudications "
                         "it was decided on")
    return extension


def _require_every_trial_accounted_for(
    state: StudyState, log: AdjudicationLog, screening: Iterable[ScreeningRecord], run_on: dt.date
) -> None:
    """Refuse the final analysis while any sealed trial could still turn out to have read out by its date.

    Each sealed trial needs a settled result, or a readout recorded as later than
    the date, or a screening on or after the date that found no public result.
    Without this the count that decides the extension would depend on how far
    the search for readouts and their adjudication had got on the day of the run.
    A trial adjudicated by someone who had opened its forecasts is unsettled too:
    leaving it out would let trials be removed by recording that they were opened.
    """
    if state.awaiting_adjudication:
        raise NotReady("adjudication is not settled for: "
                       + ", ".join(f"{nct} ({why})" for nct, why in state.awaiting_adjudication.items()))
    read_out_later = results(log, run_on)
    found_none = found_no_result(screening, state.readouts_to, run_on)
    unaccounted = sorted(nct for nct in state.batches_of
                         if nct not in state.results and nct not in read_out_later and nct not in found_none)
    if unaccounted:
        raise NotReady(f"these trials have neither a settled result nor a screening between {state.readouts_to} and "
                       f"{run_on} that found no public result: {', '.join(unaccounted)}")


def _effect_sizes(scored: StudyState, hazard_ratios_from: StudyState, plan: Plan, n_boot: int) -> dict:
    """The effect-size comparison against each baseline, as reported and with missing hazard ratios counted as no effect."""
    def against(baseline: str, **options) -> dict:
        return effect_size_comparison(scored, plan.forecaster, baseline, n_boot=n_boot, hazard_ratios_from=hazard_ratios_from, **options)

    return {"effect_size": {baseline: against(baseline) for baseline in plan.effect_size_baselines},
            "effect_size_missing_as_no_effect": {baseline: against(baseline, missing_as_no_effect=True)
                                                 for baseline in plan.effect_size_baselines}}


def _claim_can_be_tested(n_trials: int, n_drug_groups: int, extended: bool) -> bool:
    """Whether a study has the trials and the drug groups to test its claim, or reports an estimate only (ADR-0007)."""
    return n_trials >= (TRIALS_NEEDED_AFTER_EXTENSION if extended else TRIALS_NEEDED) and n_drug_groups >= DRUG_GROUPS_NEEDED


def final_analysis(
    batches: Iterable[Batch], log: AdjudicationLog, screening: Iterable[ScreeningRecord], plan: Plan, today: dt.date,
    record_file: pathlib.Path, n_boot: int = RESAMPLES,
) -> dict:
    """The one test of the registered claim, with the extension rule of ADR-0007 applied.

    Due 18 months after the first sealing, counting readouts up to that date. If
    fewer than 120 trials can then be scored in the primary comparison, the study
    is extended to 24 months, the extension is recorded, and nothing is scored. If
    there are fewer than 60 at 24 months, or fewer than 30 drug groups at either
    date, the difference is reported as an estimate and no claim is made. Otherwise the claim is supported when the whole 95% interval for the
    difference in Brier score favours the forecaster.

    It will not run until every sealed trial is accounted for. Once run it is
    recorded, and can afterwards only be regenerated as it was.
    """
    batches = in_date_order(batches)
    if not batches:
        raise ValueError("nothing has been sealed")
    first_sealing = batches[0].batch_date
    history = _history(record_file, batches, log)
    extension = _recorded_extension(history, batches, log, plan)
    months = EXTENDED_MONTHS if extension else FINAL_ANALYSIS_MONTHS
    readouts_to = add_months(first_sealing, months)
    if today < readouts_to:
        raise NotDue(f"the final analysis is fixed for {readouts_to}, {months} months after the first sealing")

    earlier, log, run_on = _as_first_run(FINAL, history, log, today)
    state = study_state(batches, log, run_on, readouts_to)
    inputs = _inputs_fingerprint(state, log, plan)
    _require_unchanged(earlier, _INPUTS, earlier and earlier.inputs_sha256, inputs)
    if earlier is None:
        _require_every_trial_accounted_for(state, log, screening, run_on)
    resamples = earlier.resamples if earlier else n_boot

    # The extension is decided on a count alone, before anything is scored.
    n_trials = len(paired(state, plan.forecaster, plan.reference).pairs)
    if earlier is None and extension is None and n_trials < TRIALS_NEEDED:
        extended_to = add_months(first_sealing, EXTENDED_MONTHS)
        decision = {"kind": FINAL, "decision": "extended", "n_trials": n_trials, "run_on": run_on,
                    "readouts_to": extended_to}
        records.append(record_file, AnalysisRecord(EXTENSION, run_on, extended_to, n_trials, _fingerprints(batches),
                                                   log.sizes(), resamples, inputs, _outputs_fingerprint(decision)))
        if today < extended_to:
            return decision
        # Asked for the first time when the extended date has passed too: go straight on to it.
        return final_analysis(batches, log, screening, plan, today, record_file, n_boot)

    with_set_aside = study_state(batches, log, run_on, readouts_to, count_set_aside=True)
    primary = primary_comparison(state, plan.forecaster, plan.reference, resamples)
    tested = _claim_can_be_tested(n_trials, primary["n_drug_groups"], extension is not None)
    analysis = {
        "kind": FINAL, "decision": "tested" if tested else "estimate_only",
        "run_on": run_on, "readouts_to": readouts_to, "extended": extension is not None,
        "claim_supported": primary["difference"]["ci_high"] < 0 if tested else None,
        "primary": primary,
        "forecasters": forecaster_scores(state, plan.reference),
        "forecasters_all_sponsors": forecaster_scores(state, plan.reference, sponsor_type=ALL_SPONSORS),
        **_effect_sizes(state, with_set_aside, plan, resamples),
        "sensitivity": sensitivity_analyses(state, with_set_aside, plan.forecaster, plan.reference, resamples),
        "set_aside": dict(state.set_aside),
        "lead_time": by_lead_time(state, plan.forecaster, plan.reference),
        "versions": by_forecaster_version(state, plan.forecaster, plan.reference),
        "models": model_table(state),
    }
    if not tested:
        analysis = _without_tests(analysis)
    outputs = _outputs_fingerprint(analysis)
    _require_unchanged(earlier, _OUTPUTS, earlier and earlier.outputs_sha256, outputs)
    # Recorded last, so that an analysis that could not be completed is never recorded as run.
    if earlier is None:
        records.append(record_file, AnalysisRecord(FINAL, run_on, readouts_to, n_trials, _fingerprints(batches),
                                                   log.sizes(), resamples, inputs, outputs))
    return analysis


def effect_size_follow_up(
    batches: Iterable[Batch], log: AdjudicationLog, plan: Plan, today: dt.date, record_file: pathlib.Path,
    hazard_ratios_searched_on: dt.date | None = None, n_boot: int = RESAMPLES,
) -> dict:
    """The effect-size analysis completed, six months after the date of the final analysis (ADR-0014).

    A hazard ratio is awaited for six months after a readout (ADR-0011), so at the
    final analysis the trials that read out last have none yet. This scores the
    same trials the final analysis scored, as the final analysis saw them, against
    hazard ratios disclosed up to six months after its date. It changes nothing
    about the primary comparison, and where the final analysis made no claim it
    tests nothing either.

    Like the others it is made once, so it must not be made on a search that is
    not finished: the first run needs the day on which the search for hazard
    ratios was completed, which must be on or after the date it covers.
    """
    batches = in_date_order(batches)
    history = _history(record_file, batches, log)
    final = next((r for r in history if r.kind == FINAL), None)
    if final is None:
        raise NotDue("the final analysis has not been run, so there is nothing to follow up")
    hazard_ratios_to = add_months(final.readouts_to, HAZARD_RATIO_WINDOW_MONTHS)
    if today < hazard_ratios_to:
        raise NotDue(f"the effect-size follow-up is fixed for {hazard_ratios_to}, six months after the final analysis date")

    _, as_final, final_run_on = _as_first_run(FINAL, history, log, today)
    scored_then = study_state(batches, as_final, final_run_on, final.readouts_to)
    _require_unchanged(final, _INPUTS, final.inputs_sha256, _inputs_fingerprint(scored_then, as_final, plan))
    earlier, log, run_on = _as_first_run(FOLLOW_UP, history, log, today)
    now = study_state(batches, log, run_on, hazard_ratios_to, count_set_aside=True)
    inputs = _inputs_fingerprint(now, log, plan)
    _require_unchanged(earlier, _INPUTS, earlier and earlier.inputs_sha256, inputs)
    if earlier is None:
        searched = hazard_ratios_searched_on
        if searched is None or not hazard_ratios_to <= searched <= today:
            raise NotReady(f"say when the search for hazard ratios disclosed by {hazard_ratios_to} was finished: "
                           f"a day from {hazard_ratios_to} to today")
        unsettled = {nct: why for nct, why in awaiting_result(log, run_on, hazard_ratios_to).items() if nct in scored_then.results}
        if unsettled:
            raise NotReady("adjudication is not settled for: " + ", ".join(f"{nct} ({why})" for nct, why in unsettled.items()))
    resamples = earlier.resamples if earlier else n_boot

    follow_up = {"kind": FOLLOW_UP, "run_on": run_on, "readouts_to": final.readouts_to, "hazard_ratios_to": hazard_ratios_to,
                 **_effect_sizes(scored_then, now, plan, resamples)}
    scored_in_final = paired(scored_then, plan.forecaster, plan.reference).pairs
    extended = any(r.kind == EXTENSION for r in history)
    if not _claim_can_be_tested(len(scored_in_final), len({p.drug_group for p in scored_in_final}), extended):
        follow_up = _without_tests(follow_up)
    outputs = _outputs_fingerprint(follow_up)
    _require_unchanged(earlier, _OUTPUTS, earlier and earlier.outputs_sha256, outputs)
    if earlier is None:
        records.append(record_file, AnalysisRecord(FOLLOW_UP, run_on, final.readouts_to, final.n_trials, _fingerprints(batches),
                                                   log.sizes(), resamples, inputs, outputs))
    return follow_up
