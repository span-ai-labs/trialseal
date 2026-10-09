"""The retrospective pilot: what each model already knows, which trials it cannot know, and what that measures.

Before anything is sealed, the method is tried on trials that have already read
out. Each model is first probed for what it recalls: shown a trial's registry
record (the cutoff probe) or its identifiers alone (the memorisation probe) and
asked what the trial showed and when that was first reported. Recall by month of
readout checks the training cutoff its provider states and sets a buffer after
it. The model then forecasts, with no web access, only its pilot trials: those
that read out after its cutoff plus buffer.

The pilot tests the method. It is not the evidence: every one of its forecasts
was made after the result was public.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import hashlib
import json
import math
import pathlib
import re
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

import numpy as np
from scipy.stats import chi2, norm

from trialforecast import records, scoring, traces
from trialforecast.adjudication import (
    LOG_KINDS, TrialResult, adjudicator_agreement, no_result_found, read_log, read_nothing_found,
    require_nothing_from_the_future, results,
)
from trialforecast.analysis import log_hazard_ratio, scored_hazard_ratio
from trialforecast.forecasting import BaseRateForecaster, Candidate, Forecast
from trialforecast.models import (
    OUTAGE, Ask, ModelForecaster, ModelSpec, ModelUnavailable, ask_provider, ask_through_outages, last_json_object,
    load_keys, read_models, trial_information, writable,
)
from trialforecast.studyfiles import (
    PILOT_ADJUDICATION, PILOT_WORKLIST, latest_snapshot, read_records, registry_records, sealed_as, write_table,
)
from trialforecast.wording import counted

NOT_THE_EVIDENCE = (
    "This pilot tests the method: the rules, the tooling and the adjudicators' agreement. It is not the evidence "
    "for the study's claim, because every forecast in it was made after the trial's result was public."
)

# The two probes, under the names their answers are stored by.
CUTOFF_PROBE, MEMORISATION_PROBE = "record", "identifiers"
PROBES = (CUTOFF_PROBE, MEMORISATION_PROBE)
PROBE_VERSION = "2"  # raise whenever the wording of a probe changes; answers to an earlier wording are not counted
# A result is recalled only if the model also says when it was first reported and is right to within this many
# months. Version 1 of the probes asked for no date, and a model then "knew" results that had not yet been
# announced at its cutoff: it had inferred them, usually from a sibling trial, and placed them a year early.
RECALL_DATE_TOLERANCE_MONTHS = 3
MINIMUM_BUFFER_MONTHS = 1  # a stated cutoff names a month, and the weeks after it are thinly covered, not absent
MINIMUM_PILOT_TRIALS = 5  # with fewer there is no spread worth reporting
USABLE_PROBE_SHARE_NEEDED = 0.9  # a model that will not answer the probes has not been shown to lack recall
MINIMUM_CLASS_READOUTS = 5  # a reference class with fewer earlier readouts takes the figures of all classes together
MINIMUM_REFERENCE_READOUTS = 10  # and with fewer than this in all, there is no base rate to speak of
FEWEST_SHOWN_APART = 3  # a mean over fewer trials than this would give away single forecasts

# What today's registry record can show only because the trial is over. Past versions of records could not be
# fetched, so a model is shown today's record without these.
HIDDEN_FROM_MODELS = ("status", "primary_completion_date", "primary_completion_type", "enrollment", "enrollment_type")
# Some records name a data cut-off in the time frame of an outcome, which says the primary analysis has happened.
# A forecast must not see that. The cutoff probe, which asks what is already known, was put with the time frames shown.
ALSO_HIDDEN_FROM_FORECASTS = ("primary_time_frames",)
ASSUMED_DIFFERENCES = (0.01, 0.02, 0.03, 0.05)  # improvements in score for which the trials needed are stated
PLANNED_TRIALS = (120, 60)  # the trials needed to test the claim at 18 months and after the extension (ADR-0007)
POWER, ALPHA = 0.8, 0.05

# Replies and forecasts stay out of the public record: some probed trials have no readout yet, and the
# adjudicators have still to read the pilot trials.
PRIVATE = pathlib.Path("private") / "pilot"
PILOT_TRACES = pathlib.Path("study") / "pilot_traces.json"


class ProbesIncomplete(Exception):
    """A model has not answered both probes for every past trial, so no buffer can be chosen for it."""


# --- past trials --------------------------------------------------------------------------


@dataclass(frozen=True)
class PastTrial:
    """A past trial as the pilot knows it: when it read out and what it showed, or that no readout was found.

    It starts as a traced trial, looked up from public sources by one reader, and
    is replaced by the adjudicated result once both adjudicators have settled it.
    """

    nct: str
    readout_date: dt.date | None  # None where no readout was found
    positive: bool | None
    hazard_ratio: float | None = None  # for the scored endpoint, if public within six months of the readout
    adjudicated: bool = False


def traced_trials(trace_files: Iterable[pathlib.Path]) -> list[PastTrial]:
    """Traced readouts with a clear result, and trials with no readout found. Anything in doubt is left out.

    A traced hazard ratio is kept only if it became public within six months of the readout (ADR-0011).
    """
    found = []
    for row in traces.read_traces(trace_files):
        if row.found in traces.CLEAR:
            found.append(PastTrial(row.nct, row.readout_date, row.found == traces.POSITIVE, row.hazard_ratio))
        elif row.found == traces.UNRESOLVED:
            found.append(PastTrial(row.nct, None, None))
    return found


def with_adjudicated(
    trials: Iterable[PastTrial], adjudicated: Mapping[str, TrialResult], candidates: Mapping[str, Candidate], as_of: dt.date,
    no_result_found: Iterable[str] = (),
) -> list[PastTrial]:
    """Past trials with each traced result replaced by the adjudicated one, wherever there is one.

    The adjudicated readout date and outcome stand in for the traced ones, and the
    hazard ratio is taken only if recorded for the scored endpoint. A trial
    adjudicated as void had no readout, so it is no longer a past readout at all.
    One for which both adjudicators searched and found nothing is a trial with no
    readout found, whatever the trace said.
    """
    nothing_found = set(no_result_found)
    merged = []
    for trial in trials:
        result = adjudicated.get(trial.nct)
        if result is None:
            merged.append(PastTrial(trial.nct, None, None, None, adjudicated=True) if trial.nct in nothing_found else trial)
        elif result.readout_date is not None:
            hazard_ratio, _ = scored_hazard_ratio(result, sealed_as(candidates[trial.nct]), as_of)
            merged.append(PastTrial(trial.nct, result.readout_date, result.outcome == "positive", hazard_ratio, adjudicated=True))
    return merged


# --- the two probes -----------------------------------------------------------------------


def as_before_readout(candidate: Candidate, also_hidden: Iterable[str] = ()) -> dict:
    """A registry record without what it can show only because the trial is over.

    A pilot forecast therefore rests on less than a prospective one, which sees the
    planned enrolment and the registry completion date.
    """
    return {**candidate, **{field: None for field in (*HIDDEN_FROM_MODELS, *also_hidden)}}


_ANSWER_FORM = ('End with one line of JSON in exactly this form: {"result_known": true or false, '
                '"result": "positive", "negative" or null, "first_reported": "YYYY-MM" or null}')


def probe_prompt(candidate: Candidate, probe: str) -> str:
    """What a model is asked in a probe: the registry record for the cutoff probe, identifiers alone for the other."""
    if probe == CUTOFF_PROBE:
        shown = f"Trial record from ClinicalTrials.gov:\n{trial_information(as_before_readout(candidate))}"
    elif probe == MEMORISATION_PROBE:
        names = [("Registry number", candidate["nct"]), ("Acronym", candidate.get("acronym")),
                 ("Sponsor's study number", candidate.get("org_study_id"))]
        shown = "\n".join(f"{label}: {value}" for label, value in names if isinstance(value, str) and value)
    else:
        raise ValueError(f"{probe!r} is not one of the probes {PROBES}")
    return (
        "This is a question about what you already know, not a request to forecast. Do not guess.\n\n"
        f"{shown}\n\n"
        "Has the primary analysis of this randomised phase 3 cancer trial been publicly reported, as far as you "
        "know? If you know the result, say whether the trial was positive (a statistically significant benefit on "
        "its primary endpoint, or an early stop for efficacy) or negative, and the year and month in which the "
        "result was first made public. If you do not know, say so. "
        f"{_ANSWER_FORM}"
    )


_STATED_MONTH = re.compile(r"(\d{4})-(\d{1,2})(?:-\d{1,2})?")


def _month(stated: object) -> str | None:
    """A stated date as a year and month, whether given to the month or to the day; anything else is no date."""
    found = _STATED_MONTH.fullmatch(stated) if isinstance(stated, str) else None
    if found is None or not 1 <= int(found.group(2)) <= 12:
        return None
    return f"{found.group(1)}-{int(found.group(2)):02d}"


def probe_answer(text: str | None) -> tuple[bool, bool | None, str | None] | None:
    """From the last JSON object in a reply: whether the model says it knows the result, which, and reported when.

    A reply that says it knows without naming a result, or names anything else, is unusable.
    """
    try:
        stated = json.loads(last_json_object(text) or "")
        known, result = stated["result_known"], stated["result"]
    except (ValueError, KeyError, TypeError):
        return None
    if known is False:
        return False, None, None
    if known is True and result in ("positive", "negative"):
        return True, result == "positive", _month(stated.get("first_reported"))
    return None


@dataclass(frozen=True)
class ProbeRecord:
    """One model's answer to one probe of one trial, with the reply as received."""

    nct: str
    model: str
    probe: str
    asked_on: dt.date
    known: bool | None  # None where the reply gave no usable answer
    positive: bool | None
    reply: str
    failure: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    model_served: str | None = None
    probe_version: str = PROBE_VERSION
    first_reported: str | None = None  # the year and month the model says the result was first public
    snapshot: str | None = None  # the registry snapshot the record shown was taken from


def ask_probe(
    spec: ModelSpec, ask: Ask, candidate: Candidate, probe: str, today: dt.date, snapshot: str | None = None,
    wait: Callable[[float], None] = time.sleep,
) -> ProbeRecord:
    """Ask a model one probe about one trial. A refusal or an unusable reply is recorded as such, never asked again."""
    reply, _ = ask_through_outages(ask, spec, probe_prompt(candidate, probe), wait)
    answer = probe_answer(reply.text) if reply.failure is None else None
    known, positive, first_reported = answer if answer is not None else (None, None, None)
    return ProbeRecord(
        nct=candidate["nct"], model=spec.model, probe=probe, asked_on=today, known=known, positive=positive,
        reply=writable(reply.text), failure=reply.failure, input_tokens=reply.input_tokens,
        output_tokens=reply.output_tokens, cost_usd=spec.cost(reply.input_tokens, reply.output_tokens),
        model_served=reply.model_served, first_reported=first_reported, snapshot=snapshot,
    )


def current_answers(probe_records: Iterable[ProbeRecord]) -> dict[tuple[str, str], ProbeRecord]:
    """A model's answer to each probe of each trial, as the probes are now worded.

    Answers to an earlier wording are not counted. If a question was somehow
    recorded twice, the first answer stands.
    """
    answers: dict[tuple[str, str], ProbeRecord] = {}
    for record in probe_records:
        if record.probe_version == PROBE_VERSION:
            answers.setdefault((record.nct, record.probe), record)
    return answers


# --- recall around the cutoff, and the buffer ------------------------------------------------


def months_after(month: str, day: dt.date) -> int:
    """Whole calendar months from a month, or the month a date falls in, to the month of a day."""
    return (day.year - int(month[:4])) * 12 + (day.month - int(month[5:7]))


def _right_result(record: ProbeRecord, trial: PastTrial) -> bool:
    return record.known is True and record.positive == trial.positive


def recalled(record: ProbeRecord, trial: PastTrial) -> bool:
    """Recall is knowing the result and when it was reported.

    The right result alone is not recall: a model can infer it and say it knows.
    What it cannot infer is a date it has not seen, so the date is the test.
    """
    if not _right_result(record, trial) or record.first_reported is None:
        return False
    return abs(months_after(record.first_reported, trial.readout_date)) <= RECALL_DATE_TOLERANCE_MONTHS


def _with_readout(answers: Iterable[ProbeRecord], trials: Iterable[PastTrial]) -> list[tuple[ProbeRecord, PastTrial]]:
    readouts = {t.nct: t for t in trials if t.readout_date is not None}
    return [(record, readouts[record.nct]) for record in answers if record.nct in readouts]


def recall_by_month(answers: Iterable[ProbeRecord], trials: Iterable[PastTrial], training_cutoff: str) -> list[dict]:
    """For trials that read out, by months from the cutoff: how many were probed, how often the model said it knew,
    gave the right result, and recalled it (the right result with the right date)."""
    months: dict[int, dict] = {}
    for record, trial in _with_readout(answers, trials):
        month = months_after(training_cutoff, trial.readout_date)
        row = months.setdefault(month, {"months_after_cutoff": month, "trials": 0, "said_known": 0, "right_result": 0,
                                        "recalled": 0})
        row["trials"] += 1
        row["said_known"] += record.known is True
        row["right_result"] += _right_result(record, trial)
        row["recalled"] += recalled(record, trial)
    return [months[month] for month in sorted(months)]


def said_known_without_readout(answers: Iterable[ProbeRecord], trials: Iterable[PastTrial]) -> dict:
    """For trials with no readout: how often a model still said it knew the result."""
    without = {t.nct for t in trials if t.readout_date is None}
    asked = [r for r in answers if r.nct in without]
    return {"trials": len(asked), "said_known": sum(r.known is True for r in asked)}


def dates_to_check(answers: Iterable[ProbeRecord], trials: Iterable[PastTrial]) -> list[str]:
    """Trials for which a model gave the right result and a date well before the readout on record.

    Either the model inferred the result, or the readout on record is late: an
    earlier disclosure was missed. Only a second look at the sources can tell.
    """
    return sorted({trial.nct for record, trial in _with_readout(answers, trials)
                   if _right_result(record, trial) and record.first_reported is not None
                   and months_after(record.first_reported, trial.readout_date) > RECALL_DATE_TOLERANCE_MONTHS})


@dataclass(frozen=True)
class PilotPlan:
    """What the probes decide for one model: its buffer and its pilot trials, or why it is dropped from the pilot."""

    latest_recall: int | None  # the latest month, counted from the stated cutoff, in which it recalled a result
    buffer_months: int
    trials: tuple[PastTrial, ...]
    dropped: str | None = None


def pilot_plan(spec: ModelSpec, probe_records: Iterable[ProbeRecord], trials: Iterable[PastTrial]) -> PilotPlan:
    """A model's buffer and pilot trials.

    The buffer runs through the last month in which either probe found the model
    recalling a result, and is never less than one month. A single recalled trial
    is enough, because too long a buffer costs only a smaller pilot and too short
    a one gives a pilot that measures memory. Its pilot trials are the readouts
    more than that many months after its stated cutoff.

    No buffer is chosen from half the evidence: the model must have answered both
    probes for every past trial. A model that mostly gave no usable answer has
    not been shown to lack recall, and one left with too few pilot trials has
    nothing to measure; both are dropped.
    """
    trials = sorted(trials, key=lambda t: t.nct)
    answers = current_answers(probe_records)
    asked_for = [(trial.nct, probe) for trial in trials for probe in PROBES]
    unanswered = [question for question in asked_for if question not in answers]
    if unanswered:
        raise ProbesIncomplete(f"{spec.model} has not been probed on {len(unanswered)} of {len(asked_for)} questions, "
                               f"so no buffer can be chosen for it")
    answered = [answers[question] for question in asked_for]
    recalls = [months_after(spec.training_cutoff, trial.readout_date)
               for record, trial in _with_readout(answered, trials) if recalled(record, trial)]
    latest, buffer = max(recalls, default=None), max([MINIMUM_BUFFER_MONTHS, *recalls])
    usable = sum(record.known is not None for record in answered) / len(answered)
    if usable < USABLE_PROBE_SHARE_NEEDED:
        return PilotPlan(latest, buffer, (), f"it gave a usable answer to only {usable:.0%} of the probe questions, so "
                                             f"the probes cannot show what it recalls")
    after = tuple(t for t in trials if t.readout_date is not None and months_after(spec.training_cutoff, t.readout_date) > buffer)
    if len(after) < MINIMUM_PILOT_TRIALS:
        return PilotPlan(latest, buffer, after, f"fewer than {MINIMUM_PILOT_TRIALS} past trials read out more than "
                                                f"{counted(buffer, 'month')} after its stated cutoff of {spec.training_cutoff}")
    return PilotPlan(latest, buffer, after)


# --- what the pilot measures ---------------------------------------------------------------


def pilot_reference(trials: Iterable[PastTrial], candidates: Mapping[str, Candidate], training_cutoff: str) -> BaseRateForecaster:
    """The pilot's reference: base rates and typical hazard ratios from readouts no later than a model's cutoff month.

    No pilot trial can be among them, since pilot trials read out after the
    cutoff. A reference class with fewer than five such readouts takes the figures
    of all classes together. The typical hazard ratio is the median of those
    known, with their 10th and 90th centiles as its interval.
    The registered study takes its base rates from the reference set (ADR-0009); this stands in for it.
    """
    earlier = [t for t in trials if t.readout_date is not None and t.nct in candidates
               and months_after(training_cutoff, t.readout_date) <= 0]
    known_ratios = [math.log(t.hazard_ratio) for t in earlier if t.hazard_ratio is not None]
    if len(earlier) < MINIMUM_REFERENCE_READOUTS or not known_ratios:
        raise ValueError(f"{len(earlier)} past readouts, {len(known_ratios)} with a hazard ratio, are as early as the "
                         f"cutoff {training_cutoff}: too few for a base rate")

    def figures(of: list[PastTrial]) -> tuple[float, tuple[float, float, float]]:
        ratios = [math.log(t.hazard_ratio) for t in of if t.hazard_ratio is not None] or known_ratios
        low, median, high = (math.exp(float(np.quantile(ratios, q))) for q in (0.1, 0.5, 0.9))
        return sum(t.positive for t in of) / len(of), (median, low, high)

    overall = figures(earlier)
    base_rates, hazard_ratios = {}, {}
    for reference_class in sorted({c["reference_class"] for c in candidates.values() if isinstance(c.get("reference_class"), str)}):
        of_class = [t for t in earlier if candidates[t.nct].get("reference_class") == reference_class]
        base_rates[reference_class], hazard_ratios[reference_class] = (
            figures(of_class) if len(of_class) >= MINIMUM_CLASS_READOUTS else overall)
    return BaseRateForecaster(base_rates, hazard_ratios, version=f"pilot/readouts to {training_cutoff[:7]}")


def score_differences(own: Mapping[str, Forecast], reference: Mapping[str, Forecast], trials: Iterable[PastTrial]) -> dict:
    """Trial by trial, the model's score minus the reference's: Brier for every trial, CRPS where a hazard ratio is known.

    As in the registered analysis, a trial the model gave no forecast for is scored at the reference's (ADR-0013).
    """
    brier, crps = [], []
    for trial in trials:
        theirs = reference[trial.nct]
        mine = theirs if own[trial.nct].no_forecast else own[trial.nct]
        happened = float(trial.positive)
        brier.append((mine.probability_positive - happened) ** 2 - (theirs.probability_positive - happened) ** 2)
        if trial.hazard_ratio is not None:
            observed = math.log(trial.hazard_ratio)
            mine_score, theirs_score = (float(scoring.crps_normal(*log_hazard_ratio(f)[:2], observed)) for f in (mine, theirs))
            crps.append(mine_score - theirs_score)
    return {"brier": brier, "crps": crps}


def sample_size_statement(differences: Iterable[float]) -> dict:
    """What the spread of per-trial score differences implies for the study's size.

    For a paired comparison at two-sided 5% with 80% power: the smallest mean
    difference detectable with the planned numbers of trials, and the trials
    needed to detect each of a few assumed differences. A spread measured on a
    handful of trials is itself uncertain, so its 95% interval is given, and the
    detectable differences are restated at its upper end. Trials of one drug are
    treated as independent here, so the true requirement is somewhat larger.
    """
    differences = np.asarray(list(differences), dtype=float)
    statement = {"trials": len(differences), "mean": float(differences.mean()) if len(differences) else None,
                 "sd": None, "sd_interval": None, "detectable_difference": {}, "detectable_at_upper_sd": {},
                 "trials_needed": {}}
    if len(differences) < 2 or np.isclose(differences.std(ddof=1), 0):
        return statement
    n, sd = len(differences), float(differences.std(ddof=1))
    sd_low, sd_high = (sd * math.sqrt((n - 1) / chi2.ppf(q, n - 1)) for q in (1 - ALPHA / 2, ALPHA / 2))
    both_tails_and_power = norm.ppf(1 - ALPHA / 2) + norm.ppf(POWER)
    statement.update(
        sd=sd, sd_interval=(sd_low, sd_high),
        detectable_difference={planned: both_tails_and_power * sd / math.sqrt(planned) for planned in PLANNED_TRIALS},
        detectable_at_upper_sd={planned: both_tails_and_power * sd_high / math.sqrt(planned) for planned in PLANNED_TRIALS},
        trials_needed={d: math.ceil((both_tails_and_power * sd / d) ** 2) for d in ASSUMED_DIFFERENCES},
    )
    return statement


# --- the report ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelPilot:
    """One model's part of the pilot: its probe answers and plan, and its forecasts once every pilot trial has one."""

    spec: ModelSpec
    answers: tuple[ProbeRecord, ...]
    plan: PilotPlan
    forecasts: Mapping[str, Forecast] | None = None  # None until made for every pilot trial
    reference: Mapping[str, Forecast] | None = None


def _recall_table(rows: list[dict]) -> list[str]:
    lines = ["| Months from stated cutoff | Trials probed | Said it knew | Right result | Right result and date |",
             "|---|---|---|---|---|"]
    return lines + [f"| {r['months_after_cutoff']:+d} | {r['trials']} | {r['said_known']} | {r['right_result']} | "
                    f"{r['recalled']} |" for r in rows]


def _mean_line(label: str, values: list[float]) -> str:
    """A mean score difference, unless it rests on so few trials that it would give a single forecast away."""
    if 0 < len(values) < FEWEST_SHOWN_APART:
        return f"- {label}: not shown for {counted(len(values), 'trial')}, since it would give single forecasts away."
    mean = "not measured" if not values else f"{sum(values) / len(values):+.3f}"
    return f"- {label}: {mean} over {counted(len(values), 'trial')}."


def _size_lines(what: str, statement: dict) -> list[str]:
    if statement["sd"] is None:
        return [f"- {what}: too few trials, or no spread among them, to measure one."]
    low, high = statement["sd_interval"]
    detectable = "; ".join(f"{planned} trials detect a mean difference of {d:.3f} (or {statement['detectable_at_upper_sd'][planned]:.3f} "
                           f"if the spread is at the upper end of its interval)"
                           for planned, d in statement["detectable_difference"].items())
    needed = "; ".join(f"{d:.2f} needs {trials}" for d, trials in statement["trials_needed"].items())
    return [f"- {what}: mean difference {statement['mean']:+.3f}, standard deviation {statement['sd']:.3f} "
            f"(95% interval {low:.3f} to {high:.3f}) over {counted(statement['trials'], 'trial')}.",
            f"  - With that spread, {detectable}.",
            f"  - Trials needed to detect an assumed mean difference: {needed}."]


def _model_lines(pilot: ModelPilot, trials: list[PastTrial]) -> tuple[list[str], list[tuple[str, dict]]]:
    """One model's section of the report, and the sample-size statements its scores give."""
    spec, plan = pilot.spec, pilot.plan
    lines = [f"## {spec.model}", "", f"Stated training cutoff {spec.training_cutoff}; released {spec.released_on}.", ""]
    for probe, title in ((CUTOFF_PROBE, "Cutoff probe (registry record shown)"),
                         (MEMORISATION_PROBE, "Memorisation probe (identifiers alone)")):
        of_probe = [r for r in pilot.answers if r.probe == probe]
        without = said_known_without_readout(of_probe, trials)
        unusable = sum(r.known is None for r in of_probe)
        lines += [f"### {title}", "", *_recall_table(recall_by_month(of_probe, trials, spec.training_cutoff)), "",
                  f"For trials with no readout it said it knew a result in {without['said_known']} of "
                  f"{without['trials']}. {counted(unusable, 'reply', 'replies')} gave no usable answer.", ""]
    seen = ("recalled no result that was disclosed after the month of its stated cutoff" if (plan.latest_recall or 0) < 1 else
            f"recalled a result disclosed {counted(plan.latest_recall, 'month')} after the month of its stated cutoff")
    lines += [f"On the two probes together it {seen}. A buffer of {counted(plan.buffer_months, 'month')} is used, "
              f"leaving {counted(len(plan.trials), 'pilot trial')}.", ""]
    to_check = dates_to_check(pilot.answers, trials)
    if to_check:
        lines += [f"It gave the right result with a date more than {RECALL_DATE_TOLERANCE_MONTHS} months before the "
                  f"readout on record for: {', '.join(to_check)}. Either it inferred these, or an earlier disclosure "
                  f"was missed; their sources should be looked at again.", ""]
    if plan.dropped:
        return lines + [f"Dropped from the pilot: {plan.dropped}.", ""], []
    if pilot.forecasts is None:
        return lines + [f"Forecasts have not yet been made for all {counted(len(plan.trials), 'pilot trial')}.", ""], []

    no_forecast = sum(pilot.forecasts[t.nct].no_forecast is not None for t in plan.trials)
    said_known = {r.nct for r in pilot.answers if r.known is True}
    others = [t for t in plan.trials if t.nct not in said_known]
    removed = len(plan.trials) - len(others)
    apart = removed >= FEWEST_SHOWN_APART and len(others) >= FEWEST_SHOWN_APART
    lines += ["### Scores", "",
              f"Forecasts made with no web access for {counted(len(plan.trials), 'pilot trial')}; {no_forecast} scored at "
              f"the reference because no forecast was produced. On one probe or the other it said it knew the result "
              f"of {removed} of them, without recalling it by the test above."
              + (" The second line of each pair leaves those out." if apart else
                 " Scores without those are not shown apart: the difference would give away single forecasts."
                 if removed else ""), ""]
    differences = score_differences(pilot.forecasts, pilot.reference, plan.trials)
    without_them = score_differences(pilot.forecasts, pilot.reference, others)
    sizes = []
    for what, key in (("Brier score, model minus base rate", "brier"),
                      ("CRPS of the log hazard ratio, model minus effect-size baseline", "crps")):
        lines.append(_mean_line(what, differences[key]))
        if apart:
            lines.append(_mean_line("  without the trials it said it knew", without_them[key]))
        sizes.append((f"{spec.model}, {what}", sample_size_statement(differences[key])))
    return lines + [""], sizes


def report(pilots: Iterable[ModelPilot], trials: Iterable[PastTrial], agreement: dict | None, written_on: dt.date) -> str:
    """The pilot report, in Markdown. No trial is named beside a forecast, so the adjudicators can still read them blind."""
    trials = list(trials)
    readouts = [t for t in trials if t.readout_date is not None]
    settled = sum(t.adjudicated for t in readouts)
    lines = ["# Retrospective pilot", "", f"Written {written_on}.", "", NOT_THE_EVIDENCE, "",
             "A model is counted as recalling a result when it says it knows it, gives the right result, and dates its "
             f"first report to within {RECALL_DATE_TOLERANCE_MONTHS} months. The right result without the right date is "
             "shown separately: a model can infer a result and say it knows.", "",
             f"Past trials: {len(readouts)} with a readout and a clear result, {len(trials) - len(readouts)} with no "
             f"readout found.", ""]
    if settled < len(readouts):
        lines += [f"**Outcomes are provisional.** {settled} of the {len(readouts)} readouts are adjudicated by both "
                  f"adjudicators; the rest were traced from public sources by one reader, an AI research agent, and are "
                  f"not yet adjudicated.", ""]
    else:
        lines += ["Every readout here was adjudicated by both adjudicators.", ""]
    if agreement is None or not agreement["sources"]:
        lines += ["Agreement between the adjudicators is not yet measured.", ""]
    else:
        kappa = "not defined, since both called every source the same way" if agreement["kappa"] is None else f"{agreement['kappa']:.2f}"
        lines += [f"The adjudicators' first readings agreed on the outcome for {agreement['outcome_agreed']} of "
                  f"{counted(agreement['sources'], 'source')} (Cohen's kappa {kappa}), on the date of disclosure for "
                  f"{agreement['disclosure_date_agreed']}, and on the hazard ratio for {agreement['hazard_ratio_agreed']} "
                  f"of the {agreement['hazard_ratio_compared']} where either recorded one. "
                  f"{counted(agreement['not_read_by_two'], 'source')} had not been read by exactly two people. Counted apart, "
                  f"as not read independently: {agreement['one_found_no_result_stated']} that one of them found not to state "
                  f"the result, and {agreement['read_after_the_two_had_talked']} first read while they differed on another "
                  f"source of the trial.", ""]

    sizes = []
    for pilot in pilots:
        model_lines, model_sizes = _model_lines(pilot, trials)
        lines += model_lines
        sizes += model_sizes
    lines += ["## Sample size", "", NOT_THE_EVIDENCE, "",
              "From the spread of per-trial score differences, for a paired comparison at two-sided 5% with 80% power. "
              "Trials of one drug are treated as independent, so the true requirement is somewhat larger. The spread "
              "is that of frontier models as shipped against the base rate; the forecaster that carries the registered "
              "claim may differ.", ""]
    for what, statement in sizes:
        lines += _size_lines(what, statement)
    if not sizes:
        lines += ["No model has forecasts for enough pilot trials to measure a spread."]
    return "\n".join(lines) + "\n"


# --- the command -------------------------------------------------------------------


class BudgetSpent(Exception):
    """The pilot has spent what it was allowed for one invocation."""


class ProviderDown(Exception):
    """Some trials could not be asked about because a provider was unavailable; nothing was recorded for them."""


@dataclass
class _Invocation:
    """What one invocation of the command works with, and what it has spent."""

    root: pathlib.Path
    specs: list[ModelSpec]
    ask: Ask
    today: dt.date
    wait: Callable[[float], None]
    budget_usd: float
    snapshot: str
    candidates: dict[str, dict]
    trials: list[PastTrial]
    spent: float = 0.0
    not_asked: int = 0  # trials no provider answered for

    def pay(self, cost_usd: float | None) -> None:
        """Count what a reply cost, and stop once the budget is reached. The reply that reaches it is kept."""
        self.spent += cost_usd or 0.0
        if self.spent >= self.budget_usd:
            raise BudgetSpent(f"stopped: the budget of ${self.budget_usd:.2f} for this invocation is spent; "
                              f"run the same command again to carry on")

    def name(self, spec: ModelSpec) -> str:
        return ModelForecaster(spec, self.ask).name

    def answers(self, spec: ModelSpec) -> list[ProbeRecord]:
        return read_records(self.root / PRIVATE / "probes" / f"{self.name(spec)}.jsonl", ProbeRecord)

    def forecasts(self, spec: ModelSpec) -> dict[str, Forecast]:
        return {f.nct: f for f in read_records(self.root / PRIVATE / f"{self.name(spec)}.jsonl", Forecast)}


def _pilot_traces(root: pathlib.Path, starting: bool) -> list[pathlib.Path]:
    """The trace files the pilot rests on: those that existed when it was begun, recorded then and kept to since.

    Trials traced later would each need both probes before any model's buffer could
    be chosen again, so they join only when the list is deliberately redrawn. Each
    file is recorded with its SHA-256: the probes were scored against what the
    trace said then, so a trace edited since is refused rather than quietly used.
    A later finding about a traced trial belongs in the adjudication log.
    """
    listed, traces = root / PILOT_TRACES, root / "data" / "readout_trace"
    if not listed.exists():
        if not starting:
            raise ValueError("the pilot has not been begun: run its probe step first")
        begun_on = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(traces.glob("trace_*.csv"))}
        listed.parent.mkdir(parents=True, exist_ok=True)
        listed.write_text(json.dumps(begun_on, indent=2) + "\n", encoding="utf-8")
    begun_on = json.loads(listed.read_text(encoding="utf-8"))
    for name, digest in begun_on.items():
        if not (traces / name).exists():
            raise ValueError(f"{name}, which the pilot was begun on, is no longer in {traces}")
        if hashlib.sha256((traces / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"{name} has changed since the pilot was begun on it")
    return [traces / name for name in begun_on]


def _require_priced(spec: ModelSpec) -> None:
    if spec.cost(1, 1) is None:
        raise ValueError(f"{spec.model} has no prices in the roster, so what it spends could not be held to a budget")


def _probe(run: _Invocation, probes: Iterable[str]) -> None:
    for spec in run.specs:
        _require_priced(spec)
        probe_file = run.root / PRIVATE / "probes" / f"{run.name(spec)}.jsonl"
        answered = current_answers(run.answers(spec))
        for probe in probes:
            for trial in run.trials:
                if (trial.nct, probe) in answered:
                    continue
                record = ask_probe(spec, run.ask, run.candidates[trial.nct], probe, run.today, run.snapshot, run.wait)
                if record.failure == OUTAGE:
                    run.not_asked += 1  # an outage says nothing about the model, so it is not kept as its answer
                    continue
                records.append(probe_file, record)
                run.pay(record.cost_usd)
        print(f"{spec.model}: probed")


def _forecast(run: _Invocation) -> None:
    for spec in run.specs:
        _require_priced(spec)
        forecaster = ModelForecaster(spec, run.ask, today=lambda: run.today, wait=run.wait)
        plan = pilot_plan(spec, run.answers(spec), run.trials)
        if plan.dropped:
            print(f"{spec.model}: dropped from the pilot: {plan.dropped}")
            continue
        forecast_file, made = run.root / PRIVATE / f"{forecaster.name}.jsonl", run.forecasts(spec)
        for trial in plan.trials:
            if trial.nct in made:
                continue
            forecast = forecaster.forecast(as_before_readout(run.candidates[trial.nct], ALSO_HIDDEN_FROM_FORECASTS), run.today)
            if forecast.no_forecast and forecast.provider_failures:
                run.not_asked += 1  # lost to an outage: not the model's answer, though any replies it gave were paid for
            else:
                records.append(forecast_file, forecast)
                made[trial.nct] = forecast
            run.pay(forecast.cost_usd)
        # Counts only: the adjudicators have still to read these trials, so no forecast is shown.
        print(f"{spec.model}: buffer of {counted(plan.buffer_months, 'month')}; forecasts held for "
              f"{sum(t.nct in made for t in plan.trials)} of {counted(len(plan.trials), 'pilot trial')}")


def _report(run: _Invocation) -> None:
    log, findings = read_log(run.root / PILOT_ADJUDICATION), read_nothing_found(run.root / PILOT_ADJUDICATION)
    require_nothing_from_the_future([*findings, *(entry for kind in LOG_KINDS for entry in getattr(log, kind))], run.today)
    nothing_found = no_result_found(findings, log, run.today)
    trials = with_adjudicated(run.trials, results(log, run.today), run.candidates, run.today, nothing_found)
    pilots, recall_rows, to_adjudicate = [], [], {}
    for spec in run.specs:
        try:
            plan = pilot_plan(spec, run.answers(spec), trials)
        except ProbesIncomplete as incomplete:
            print(f"left out of the report: {incomplete}")
            continue
        answers = tuple(current_answers(run.answers(spec)).values())
        pilot, forecasts = ModelPilot(spec, answers, plan), run.forecasts(spec)
        if not plan.dropped and all(t.nct in forecasts for t in plan.trials):
            reference = pilot_reference(trials, run.candidates, spec.training_cutoff)
            pilot = dataclasses.replace(pilot, forecasts=forecasts, reference={
                t.nct: reference.forecast(run.candidates[t.nct], run.today) for t in plan.trials})
        pilots.append(pilot)
        for trial in () if plan.dropped else plan.trials:
            to_adjudicate.setdefault(trial.nct, []).append(spec.model)
        recall_rows += [(spec.model, probe, *row.values()) for probe in PROBES
                        for row in recall_by_month([r for r in answers if r.probe == probe], trials, spec.training_cutoff)]
    out = run.root / PILOT_WORKLIST.parent
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(report(pilots, trials, adjudicator_agreement(log), run.today), encoding="utf-8")
    adjudicated = {t.nct for t in trials if t.adjudicated}
    tables = (
        ("recall.csv", ("model", "probe", "months_after_cutoff", "trials", "said_known", "right_result", "recalled"), recall_rows),
        # What the two adjudicators have to read: each model's pilot trials, with nothing about any forecast.
        (PILOT_WORKLIST.name, ("nct", "acronym", "title", "scored_endpoint", "pilot_trial_for", "adjudicated"),
         [(nct, run.candidates[nct].get("acronym"), run.candidates[nct].get("brief_title"), run.candidates[nct]["scored_endpoint"],
           "; ".join(models), "yes" if nct in adjudicated else "no") for nct, models in sorted(to_adjudicate.items())]),
    )
    for name, columns, rows in tables:
        write_table(out / name, columns, rows)
    print(f"pilot report written to {out / 'report.md'}")


def main(
    arguments: list[str] | None = None, ask: Ask = ask_provider, today: dt.date | None = None,
    wait: Callable[[float], None] = time.sleep,
) -> int:
    """Run one step of the pilot: `trialseal-pilot probe|forecast|report --study <directory>`.

    `probe` asks each model in the roster both probes about every past trial.
    `forecast` chooses each model's buffer from its probes, which must be complete,
    and has it forecast its pilot trials. Replies and forecasts are kept in the
    private directory and never shown. `report` writes the pilot report and the
    list of trials for the adjudicators. The first two can be stopped and run again.
    """
    parser = argparse.ArgumentParser(prog="trialseal-pilot", description=__doc__.split("\n\n")[0])
    parser.add_argument("step", choices=("probe", "forecast", "report"))
    parser.add_argument("--study", default=".", help="the study directory (default: the current directory)")
    parser.add_argument("--model", help="work with this one model of the roster (default: every model)")
    parser.add_argument("--probe", choices=PROBES, help="ask this one probe (default: both)")
    parser.add_argument("--snapshot", help="the registry snapshot to take trial records from (default: the latest)")
    parser.add_argument("--budget-usd", type=float, default=30.0, help="what one invocation may spend on model replies")
    options = parser.parse_args(arguments)
    root = pathlib.Path(options.study)
    load_keys(root / ".env")
    run = None
    try:
        specs = read_models(root / "study" / "models.json")
        if options.model:
            specs = [spec for spec in specs if spec.model == options.model]
            if not specs:
                raise ValueError(f"{options.model} is not in the roster")
        snapshot = pathlib.Path(options.snapshot) if options.snapshot else latest_snapshot(root)
        candidates = registry_records(snapshot)
        # A trial can be probed and forecast only if the snapshot holds its record with a scored endpoint and a
        # reference class.
        trials = [t for t in traced_trials(_pilot_traces(root, starting=options.step == "probe"))
                  if all(isinstance(candidates.get(t.nct, {}).get(field), str) for field in ("scored_endpoint", "reference_class"))]
        run = _Invocation(root, specs, ask, today or dt.datetime.now(dt.timezone.utc).date(), wait, options.budget_usd,
                          snapshot.name, candidates, trials)
        if options.step == "probe":
            _probe(run, [options.probe] if options.probe else PROBES)
        elif options.step == "forecast":
            _forecast(run)
        else:
            _report(run)
        if run.not_asked:
            raise ProviderDown(f"{counted(run.not_asked, 'trial')} could not be asked about because a provider "
                               f"was unavailable; nothing was recorded for them, so run the same command again")
    except BudgetSpent as stopped:
        print(stopped)
        return 2
    except ProviderDown as down:
        print(down)
        return 3
    except (ProbesIncomplete, ModelUnavailable, ValueError, LookupError, OSError) as problem:
        print(f"NOT DONE: {problem}")
        return 1
    finally:
        if run is not None and run.spent:
            print(f"spent ${run.spent:.2f} on model replies in this invocation")
    return 0
