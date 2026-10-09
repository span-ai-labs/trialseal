"""The reference set: traced past trials, and the base rates and hazard-ratio distributions drawn from them.

Past trials are traced to their readouts by one reader, re-checked where the
trace was unsure, and adjudicated by the two adjudicators on a random sample,
which measures how far the rest of the trace can be relied on. From the trials
with a clear result come the base rate of each reference class, which is the bar
the registered claim must beat (ADR-0002, ADR-0009), and the typical hazard ratio
that effect-size forecasts are compared with. Both are frozen once, for registration.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import random
from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np

from trialforecast import scoring, traces, universe
from trialforecast.adjudication import (
    LOG_KINDS, NOTHING_FOUND, TrialResult, adjudicator_agreement, awaiting_result, no_result_found, read_log,
    read_nothing_found, require_nothing_from_the_future, results,
)
from trialforecast.analysis import scored_hazard_ratio
from trialforecast.forecasting import BaseRateForecaster, Candidate
from trialforecast.screening import AWAITING_DESIGN_REVIEW, EXCLUDED_DESIGN, DesignReview, design_status
from trialforecast.studyfiles import (
    DESIGN_REVIEWS, REFERENCE_ADJUDICATION, REFERENCE_WORKLIST, TRACES, latest_snapshot, read_records, registry_records,
    sealed_as, write_table,
)
from trialforecast.traces import CLEAR, IN_DOUBT, NEGATIVE, POSITIVE, UNRESOLVED, VOID
from trialforecast.universe import ENDPOINT_TYPES, SPONSOR_TYPES
from trialforecast.wording import counted

AWAITING_RECHECK = "awaiting_recheck"
NOT_YET_COUNTED = (IN_DOUBT, AWAITING_RECHECK, AWAITING_DESIGN_REVIEW)
MINIMUM_CLASS_TRIALS = 20  # a reference class with fewer clear results takes its sponsor type's base rate
MINIMUM_CLASS_HAZARD_RATIOS = 10  # and one with fewer hazard ratios takes its sponsor type's typical hazard ratio
SAMPLE_SIZE, SAMPLE_SEED = 40, 20261009  # the adjudicators' sample is one draw, kept once made
# If the adjudicators contradict the trace on more of their sample than this allows, the traces they did not read
# cannot be relied on, and nothing is frozen until they have read those too.
TRACE_ACCURACY_NEEDED = 0.9
SAMPLE = REFERENCE_ADJUDICATION / "sample.json"
FROZEN = pathlib.Path("study") / "base_rates.json"

# What published studies report, shown beside our own figures and never used in their place (ADR-0009).
LITERATURE_RATES = (
    ("43.4% of 824 registry-identified phase 3 cancer trials, 2007 to 2023", "Yamamoto et al.", "https://doi.org/10.1111/cts.70635"),
    ("53% of 791 published trials", "Sherry et al., JAMA Oncology", "https://doi.org/10.1001/jamaoncol.2025.1002"),
    ("69% of trials published in ten leading journals in 2023", "Lamp and Mazza", "https://pmc.ncbi.nlm.nih.gov/articles/PMC12415963/"),
    ("57% industry-led against 30% not, in a cohort of 385", "Noticewala et al.", "https://pmc.ncbi.nlm.nih.gov/articles/PMC12342805/"),
    ("21.5% of NCI cooperative-group trials", "Zakeri et al.", "https://doi.org/10.1093/annonc/mdy340"),
)


class NotFrozen(Exception):
    """The base rates cannot be frozen yet, or are frozen already."""


@dataclass(frozen=True)
class ReferenceTrial:
    """A past trial's place in the reference set, and what is known of its result."""

    nct: str
    reference_class: str
    place: str  # positive, negative, void, unresolved, or one of the reasons it is not yet counted or is left out
    readout_date: dt.date | None = None
    hazard_ratio: float | None = None  # for the scored endpoint, if public within six months of the readout
    traced_in: str = ""
    rechecked: bool = False
    adjudicated: bool = False

    @property
    def sponsor_type(self) -> str:
        return self.reference_class.split("/")[0]

    @property
    def clear(self) -> bool:
        """Whether the trial has a result that counts towards a base rate."""
        return self.place in CLEAR

    @property
    def typical(self) -> bool:
        """Whether the trial's hazard ratio counts towards a typical hazard ratio."""
        return self.clear and self.hazard_ratio is not None


def _as_traced(row: traces.TracedRow, candidate: Candidate) -> tuple[str, dt.date | None, float | None]:
    """A traced row's place, readout date and hazard ratio. The hazard ratio counts only if the reader traced it
    for an endpoint of the same type as the trial's scored endpoint."""
    same_type = universe.endpoint_type(row.endpoint) == candidate["endpoint_type"]
    return row.found, row.readout_date, row.hazard_ratio if same_type else None


def reference_trials(
    trace_files: Iterable[pathlib.Path], candidates: Mapping[str, Candidate], rechecks: Iterable[pathlib.Path] = (),
    adjudicated: Mapping[str, TrialResult] | None = None, awaiting_adjudication: Iterable[str] = (),
    design_reviews: Iterable[DesignReview] = (), as_of: dt.date | None = None, no_result_found: Iterable[str] = (),
) -> list[ReferenceTrial]:
    """Every traced candidate with a reference class, each in one place.

    The design comes first: a trial whose design was ruled out is left out, and one
    tagged for exclusion review waits for a ruling. Then the result, from the most
    careful reading there is. The adjudicators' settled result stands above all,
    and so does their finding that no source states a result: the trial is then
    unresolved, or void if the trace found it had ended without an analysis. While they have read a trial and not yet
    settled it, it is in doubt. Next a
    re-check, which replaces the first trace unless the re-check is itself unsure.
    A first trace of low confidence does not count until it has been re-checked.
    """
    adjudicated, awaiting, reviews = adjudicated or {}, set(awaiting_adjudication), list(design_reviews)
    nothing_found = set(no_result_found)
    rechecked = {row.nct: row for row in traces.read_traces(rechecks)}
    trials = []
    for row in traces.read_traces(trace_files):
        candidate = candidates.get(row.nct)
        if candidate is None or not isinstance(candidate.get("reference_class"), str):
            continue
        again = rechecked.get(row.nct)
        known = dict(nct=row.nct, reference_class=candidate["reference_class"], traced_in=row.traced_in, rechecked=again is not None)
        design, result = design_status(candidate, reviews), adjudicated.get(row.nct)
        if design is not None:
            trials.append(ReferenceTrial(**known, place=design))
        elif result is not None and result.readout_date is None:
            trials.append(ReferenceTrial(**known, place=VOID, adjudicated=True))
        elif result is not None:
            hazard_ratio, _ = scored_hazard_ratio(result, sealed_as(candidate), as_of or dt.date.max)
            trials.append(ReferenceTrial(**known, place=result.outcome, readout_date=result.readout_date,
                                         hazard_ratio=hazard_ratio, adjudicated=True))
        elif row.nct in nothing_found:
            # No source states a result. If the trace found the trial had ended without one, the two agree: it is void.
            ended_without_analysis = _as_traced(again or row, candidate)[0] == VOID
            trials.append(ReferenceTrial(**known, place=VOID if ended_without_analysis else UNRESOLVED, adjudicated=True))
        elif row.nct in awaiting:
            trials.append(ReferenceTrial(**known, place=IN_DOUBT))
        elif again is not None:
            place, readout, hazard_ratio = _as_traced(again, candidate)
            unsure = again.confidence == traces.LOW
            trials.append(ReferenceTrial(**known, place=IN_DOUBT if unsure else place, readout_date=readout,
                                         hazard_ratio=None if unsure else hazard_ratio))
        elif row.confidence == traces.LOW:
            trials.append(ReferenceTrial(**known, place=AWAITING_RECHECK))
        else:
            place, readout, hazard_ratio = _as_traced(row, candidate)
            trials.append(ReferenceTrial(**known, place=place, readout_date=readout, hazard_ratio=hazard_ratio))
    return trials


# --- the tables --------------------------------------------------------------------------


def _groups(trials: Iterable[ReferenceTrial]) -> list[tuple[str, list[ReferenceTrial]]]:
    """Each reference class, then each sponsor type, then every trial: the rows of both tables."""
    trials = list(trials)
    classes = [f"{sponsor}/{endpoint}" for sponsor in SPONSOR_TYPES for endpoint in ENDPOINT_TYPES]
    return ([(name, [t for t in trials if t.reference_class == name]) for name in classes]
            + [(sponsor, [t for t in trials if t.sponsor_type == sponsor]) for sponsor in SPONSOR_TYPES]
            + [("all sponsors", trials)])


def _rate(of: list[ReferenceTrial]) -> tuple[int, int, float | None]:
    """Trials with a clear result, how many were positive, and the share. Void and unresolved trials never count."""
    clear = [t for t in of if t.clear]
    positive = sum(t.place == POSITIVE for t in clear)
    return len(clear), positive, positive / len(clear) if clear else None


def base_rate_table(trials: Iterable[ReferenceTrial]) -> list[dict]:
    """For each reference class: trials with a clear result, the share positive with its 95% interval, and beside
    them the void, the unresolved and those not yet counted."""
    rows = []
    for name, of in _groups(trials):
        clear, positive, rate = _rate(of)
        rows.append({"reference_class": name, "trials": clear, "positive": positive, "rate": rate,
                     "interval": scoring.wilson_interval(positive, clear),
                     "void": sum(t.place == VOID for t in of), "unresolved": sum(t.place == UNRESOLVED for t in of),
                     "not_yet_counted": sum(t.place in NOT_YET_COUNTED for t in of)})
    return rows


def _typical(of: list[ReferenceTrial]) -> tuple[float, float, float] | None:
    """The median hazard ratio and its 10th and 90th centiles, taken on the log scale the forecasts are scored on."""
    ratios = [math.log(t.hazard_ratio) for t in of if t.typical]
    if not ratios:
        return None
    low, median, high = (math.exp(float(np.quantile(ratios, q))) for q in (0.1, 0.5, 0.9))
    return median, low, high


def hazard_ratio_table(trials: Iterable[ReferenceTrial]) -> list[dict]:
    """For each reference class: how many trials have a hazard ratio, its median, and the 10th and 90th centiles."""
    rows = []
    for name, of in _groups(trials):
        typical = _typical(of) or (None, None, None)
        rows.append({"reference_class": name, "trials": sum(t.typical for t in of),
                     "median": typical[0], "low": typical[1], "high": typical[2]})
    return rows


def frozen_base_rates(trials: Iterable[ReferenceTrial], frozen_on: dt.date) -> dict:
    """What the base-rate forecaster is given, fixed on one day for registration.

    A reference class with at least 20 clear results uses its own base rate; one
    with fewer takes the rate of its sponsor type, which must itself rest on at
    least 20. The typical hazard ratio is chosen the same way, with 10 hazard
    ratios as the bar. Without those numbers for a sponsor type there is no bar
    to hold a forecast to, and nothing is frozen.
    """
    trials = list(trials)
    base_rates, hazard_ratios, pooled, pooled_ratios, counts = {}, {}, [], [], {}
    for sponsor in SPONSOR_TYPES:
        of_sponsor = [t for t in trials if t.sponsor_type == sponsor]
        clear_of_sponsor, _, sponsor_rate = _rate(of_sponsor)
        ratios_of_sponsor = sum(t.typical for t in of_sponsor)
        if clear_of_sponsor < MINIMUM_CLASS_TRIALS or ratios_of_sponsor < MINIMUM_CLASS_HAZARD_RATIOS:
            raise NotFrozen(f"{sponsor} trials have {clear_of_sponsor} clear results and {ratios_of_sponsor} hazard ratios; "
                            f"{MINIMUM_CLASS_TRIALS} and {MINIMUM_CLASS_HAZARD_RATIOS} are needed for a base rate")
        for endpoint in ENDPOINT_TYPES:
            name = f"{sponsor}/{endpoint}"
            of_class = [t for t in of_sponsor if t.reference_class == name]
            clear, _, rate = _rate(of_class)
            with_ratio = sum(t.typical for t in of_class)
            own_rate, own_typical = clear >= MINIMUM_CLASS_TRIALS, with_ratio >= MINIMUM_CLASS_HAZARD_RATIOS
            base_rates[name] = rate if own_rate else sponsor_rate
            hazard_ratios[name] = list(_typical(of_class if own_typical else of_sponsor))
            counts[name] = {"clear_results": clear, "hazard_ratios": with_ratio}
            pooled += [] if own_rate else [name]
            pooled_ratios += [] if own_typical else [name]
    return {"frozen_on": frozen_on.isoformat(), "base_rates": base_rates, "hazard_ratios": hazard_ratios,
            "pooled": sorted(pooled), "hazard_ratios_pooled": sorted(pooled_ratios), "counts": counts}


def _made_from(root: pathlib.Path) -> dict[str, str | None]:
    """Every file the figures rest on, with its SHA-256; or None for one that could hold something and does not exist.

    The absent ones are named so that a file appearing later is noticed as surely as one that changes.
    """
    log = root / REFERENCE_ADJUDICATION
    files = {*(root / TRACES).glob("trace_*.csv"), *(root / TRACES).glob("rechecks*.csv"), *log.glob("*.json*"),
             *(log / file_name for file_name, _ in LOG_KINDS.values()), log / NOTHING_FOUND, root / DESIGN_REVIEWS}
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            for path in sorted(files)}


def base_rate_forecaster(root: pathlib.Path) -> BaseRateForecaster:
    """The reference forecaster, from the figures frozen for registration.

    Refuses if anything the figures were made from has changed since, or a file
    they would have been made from has appeared: the frozen file would then no
    longer be what the traces and adjudications give.
    """
    figures = json.loads((root / FROZEN).read_text(encoding="utf-8"))
    then, now = figures["made_from"], _made_from(root)
    changed = sorted(name for name in {*then, *now} if then.get(name) != now.get(name))
    if changed:
        raise ValueError(f"the base rates were frozen on {figures['frozen_on']} from files that have since changed, "
                         f"gone or appeared: {', '.join(changed)}")
    return BaseRateForecaster(figures["base_rates"], {name: tuple(triple) for name, triple in figures["hazard_ratios"].items()},
                              version=f"frozen {figures['frozen_on']}")


def _traced_as(trials: Iterable[ReferenceTrial]) -> dict[str, str]:
    """A mark of how each trial was traced, to tell later whether its trace has changed. It gives nothing away."""
    return {t.nct: hashlib.sha256(f"{t.nct}|{t.place}|{t.readout_date}|{t.hazard_ratio}".encode()).hexdigest()[:12]
            for t in trials}


def _design_as(trials: Iterable[ReferenceTrial]) -> dict[str, str]:
    """Where each trial's design stood: ruled out, awaiting a ruling, or in."""
    return {t.nct: t.place if t.place in (EXCLUDED_DESIGN, AWAITING_DESIGN_REVIEW) else "in" for t in trials}


def _snapshot_mark(snapshot: pathlib.Path) -> dict[str, str]:
    return {"name": snapshot.name, "sha256": hashlib.sha256((snapshot / "studies.jsonl.gz").read_bytes()).hexdigest()}


def _to_read(trials: Iterable[ReferenceTrial]) -> list[str]:
    """The trials an adjudicator has something to read for: those traced as read out, or as void."""
    return sorted(t.nct for t in trials if t.clear or t.place == VOID)


def _draw(pool: list[str], size: int = SAMPLE_SIZE) -> list[str]:
    return sorted(random.Random(SAMPLE_SEED).sample(pool, min(size, len(pool))))


def adjudication_sample(trials: Iterable[ReferenceTrial], size: int = SAMPLE_SIZE) -> list[str]:
    """The random sample both adjudicators read: one draw from the trials traced as read out or as void."""
    return _draw(_to_read(trials), size)


def trace_accuracy(
    traced: Iterable[ReferenceTrial], adjudicated: Mapping[str, TrialResult], no_result_found: Iterable[str] = ()
) -> dict:
    """How often one reader's trace matched what the adjudicators settled, for trials both have read.

    This is what says whether the traced trials the adjudicators did not read can
    be relied on. A trial the trace took to be positive or negative, for which
    both adjudicators searched and found nothing, is one the trace got wrong. One
    the trace took to have ended without an analysis, for which they found
    nothing, is one it got right: there is no result.
    """
    nothing_found = set(no_result_found) - set(adjudicated)
    both = [(t, adjudicated[t.nct]) for t in traced if t.nct in adjudicated and (t.clear or t.place == VOID)]
    missed = sum(t.clear and t.nct in nothing_found for t in traced)
    no_result_either = sum(t.place == VOID and t.nct in nothing_found for t in traced)
    dated = [(t.readout_date, r.readout_date) for t, r in both if t.readout_date and r.readout_date]
    return {"trials": len(both) + missed + no_result_either,
            "outcome_matched": sum(t.place == r.outcome for t, r in both) + no_result_either,
            "no_result_found": missed,
            "date_within_a_week": sum(abs((mine - theirs).days) <= 7 for mine, theirs in dated),
            "date_later_than_adjudicated": sum((mine - theirs).days > 7 for mine, theirs in dated)}


# --- the command -------------------------------------------------------------------------


@dataclass(frozen=True)
class _Study:
    """What the reference command reads from a study directory."""

    root: pathlib.Path
    today: dt.date
    candidates: dict[str, dict]
    traced: list[ReferenceTrial]  # as one reader traced them, with re-checks
    trials: list[ReferenceTrial]  # with the adjudicators' results in place of the trace wherever they have settled one
    adjudicated: dict[str, TrialResult]
    no_result_found: set[str]  # trials both adjudicators searched for and found nothing
    agreement: dict
    snapshot: dict[str, str]  # the registry snapshot the trials' reference classes are taken from
    begun: bool  # whether the adjudicators have recorded anything


def _load(root: pathlib.Path, today: dt.date) -> _Study:
    # Once the sample is drawn the reference set keeps to the registry snapshot it was drawn on: a later snapshot
    # can reclass a sponsor or reword an endpoint, and the set the adjudicators are checking would shift under them.
    drawn = _drawn(root)
    if drawn is not None and "snapshot" in drawn:
        snapshot = root / "snapshots" / drawn["snapshot"]["name"]
        if not (snapshot / "studies.jsonl.gz").exists() or _snapshot_mark(snapshot) != drawn["snapshot"]:
            raise ValueError(f"{snapshot} is not the snapshot the sample was drawn on: it is gone or has changed")
    else:
        snapshot = latest_snapshot(root)
    candidates = registry_records(snapshot)
    trace_files = sorted((root / TRACES).glob("trace_*.csv"))
    sources = dict(trace_files=trace_files, candidates=candidates, rechecks=sorted((root / TRACES).glob("rechecks*.csv")),
                   design_reviews=read_records(root / DESIGN_REVIEWS, DesignReview))
    log, findings = read_log(root / REFERENCE_ADJUDICATION), read_nothing_found(root / REFERENCE_ADJUDICATION)
    require_nothing_from_the_future([*findings, *(entry for kind in LOG_KINDS for entry in getattr(log, kind))], today)
    adjudicated = results(log, today)
    nothing_found = set(no_result_found(findings, log, today))
    return _Study(root, today, candidates, reference_trials(**sources),
                  reference_trials(**sources, adjudicated=adjudicated, awaiting_adjudication=awaiting_result(log, today),
                                   as_of=today, no_result_found=nothing_found),
                  adjudicated, nothing_found, adjudicator_agreement(log), _snapshot_mark(snapshot),
                  bool(findings or any(log.sizes())))


def _share(value: float | None) -> str:
    return "" if value is None else f"{value:.1%}"


def _report_text(study: _Study) -> str:
    trials, settled = study.trials, sum(t.adjudicated for t in study.trials)
    places = {place: sum(t.place == place for t in trials) for place in (
        POSITIVE, NEGATIVE, VOID, UNRESOLVED, IN_DOUBT, AWAITING_RECHECK, AWAITING_DESIGN_REVIEW, EXCLUDED_DESIGN)}
    lines = ["# Reference set and base rates", "", f"Written {study.today}. {counted(len(trials), 'past trial')} traced.", "",
             f"**These figures are provisional.** {settled} of the {len(trials)} trials are adjudicated by both adjudicators; "
             f"the others rest on one reader's trace. They are frozen only at registration.", "",
             f"Positive {places[POSITIVE]}, negative {places[NEGATIVE]}, void {places[VOID]}, unresolved {places[UNRESOLVED]}. "
             f"Not yet counted: {places[IN_DOUBT]} in doubt, {counted(places[AWAITING_RECHECK], 'trial')} "
             f"{'awaits' if places[AWAITING_RECHECK] == 1 else 'await'} a re-check, {places[AWAITING_DESIGN_REVIEW]} tagged for "
             f"exclusion review with no ruling. Left out for their design: {places[EXCLUDED_DESIGN]}.", "",
             "## Base rates", "",
             "Trials with a clear result only. Void and unresolved trials are shown beside them and never counted as negative.", "",
             "| Reference class | Clear results | Positive | Base rate | 95% interval | Void | Unresolved | Not yet counted |",
             "|---|---|---|---|---|---|---|---|"]
    for row in base_rate_table(trials):
        low, high = row["interval"]
        interval = "" if low is None else f"{low:.1%} to {high:.1%}"
        lines.append(f"| {row['reference_class']} | {row['trials']} | {row['positive']} | {_share(row['rate'])} | {interval} | "
                     f"{row['void']} | {row['unresolved']} | {row['not_yet_counted']} |")
    lines += ["", "Published rates, for comparison. They are not used: each was assembled differently from the outcome scored here (ADR-0009).", ""]
    lines += [f"- {what} ([{who}]({where}))" for what, who, where in LITERATURE_RATES]
    lines += ["", "## Hazard ratios", "",
              "The first hazard ratio reported for the scored endpoint, where it became public within six months of the readout.", "",
              "| Reference class | Trials with a hazard ratio | Median | 10th centile | 90th centile |", "|---|---|---|---|---|"]
    for row in hazard_ratio_table(trials):
        cells = " | ".join("" if row[key] is None else f"{row[key]:.2f}" for key in ("median", "low", "high"))
        lines.append(f"| {row['reference_class']} | {row['trials']} | {cells} |")
    agreement, accuracy = study.agreement, trace_accuracy(study.traced, study.adjudicated, study.no_result_found)
    lines += ["", "## Adjudication", ""]
    if not (agreement["sources"] or accuracy["trials"] or agreement["one_found_no_result_stated"]
            or agreement["read_after_the_two_had_talked"]):
        lines += ["The adjudicators have not yet read their sample, so neither their agreement nor the accuracy of the "
                  "trace is measured."]
    else:
        kappa = "not defined" if agreement["kappa"] is None else f"{agreement['kappa']:.2f}"
        lines += [f"The adjudicators' first readings agreed on the outcome for {agreement['outcome_agreed']} of "
                  f"{counted(agreement['sources'], 'source')} (Cohen's kappa {kappa}) and on the date of disclosure for "
                  f"{agreement['disclosure_date_agreed']}. Counted apart, as not read independently: "
                  f"{counted(agreement['one_found_no_result_stated'], 'source')} one of them found not to state the result, and "
                  f"{agreement['read_after_the_two_had_talked']} first read while they differed on another source of the trial.",
                  f"Of {counted(accuracy['trials'], 'trial')} both traced and adjudicated, the trace had the outcome right "
                  f"for {accuracy['outcome_matched']} and the readout date within a week for {accuracy['date_within_a_week']}; "
                  f"it dated {accuracy['date_later_than_adjudicated']} later than the adjudicators did. For "
                  f"{accuracy['no_result_found']} of them both adjudicators searched and found no source that states a result."]
    return "\n".join(lines) + "\n"


def report(study: _Study) -> int:
    """Write the base-rate table, the hazard-ratio table, the list of trials and the report."""
    out, trials = study.root / "results" / "reference_set", study.trials
    write_table(out / "base_rates.csv", ("reference_class", "trials", "positive", "rate", "interval_low", "interval_high", "void",
                                         "unresolved", "not_yet_counted"),
                [(r["reference_class"], r["trials"], r["positive"], r["rate"], *r["interval"], r["void"], r["unresolved"],
                  r["not_yet_counted"]) for r in base_rate_table(trials)])
    write_table(out / "hazard_ratios.csv", ("reference_class", "trials", "median", "low", "high"),
                [tuple(r.values()) for r in hazard_ratio_table(trials)])
    write_table(out / "trials.csv", ("nct", "reference_class", "place", "readout_date", "hazard_ratio", "traced_in", "rechecked", "adjudicated"),
                [(t.nct, t.reference_class, t.place, t.readout_date, t.hazard_ratio, t.traced_in, t.rechecked, t.adjudicated) for t in trials])
    (out / "report.md").write_text(_report_text(study), encoding="utf-8")
    clear, positive, rate = _rate([t for t in trials if t.sponsor_type == "industry"])
    print(f"{counted(len(trials), 'past trial')}; industry-led base rate {_share(rate)} ({positive} of {clear}); "
          f"report written to {out / 'report.md'}")
    return 0


def _drawn(root: pathlib.Path) -> dict | None:
    return json.loads((root / SAMPLE).read_text(encoding="utf-8")) if (root / SAMPLE).exists() else None


def _settled(study: _Study, nct: str) -> bool:
    return nct in study.adjudicated or nct in study.no_result_found


def _sample_bears_the_trace_out(study: _Study, sampled: Iterable[str]) -> tuple[bool, dict]:
    """Whether the trace matched the adjudicators on enough of the sampled trials, and the counts.

    It is the sample that judges the trace. Trials read beyond it were not drawn
    at random, so they do not count for or against it.
    """
    sampled = set(sampled)
    accuracy = trace_accuracy([t for t in study.traced if t.nct in sampled], study.adjudicated, study.no_result_found)
    return accuracy["outcome_matched"] >= TRACE_ACCURACY_NEEDED * accuracy["trials"], accuracy


def sample(study: _Study) -> int:
    """Draw the adjudicators' sample, once, and list it for them with nothing of what the trace found.

    It is drawn only when no trace still awaits a re-check and before the
    adjudicators have recorded anything. It records the registry snapshot, the
    trials it was drawn from, and a mark of how every traced trial was traced and
    where its design stood, so that nothing changed afterwards can stand for what
    was drawn. The list the adjudicators are given also holds the trials the
    trace left in doubt, which only they can settle; it does not say which those
    are. If they have settled the sample and the trace did not match them often
    enough, the list becomes every traced trial with a result.
    """
    drawn = _drawn(study.root)
    if drawn is None:
        waiting = sum(t.place == AWAITING_RECHECK for t in study.traced)
        if waiting:
            raise ValueError(f"{counted(waiting, 'trace')} still await a re-check; the sample is drawn once they are made")
        if study.begun:
            raise ValueError("the adjudicators have begun: the reference log holds entries, so a sample drawn now would "
                             "not be one they read without knowing the trace would be judged on it")
        drawn_from = _to_read(study.traced)
        drawn = {"drawn_on": study.today.isoformat(), "seed": SAMPLE_SEED, "trials": _draw(drawn_from), "drawn_from": drawn_from,
                 "in_doubt": sorted(t.nct for t in study.traced if t.place == IN_DOUBT), "snapshot": study.snapshot,
                 "traced_as": _traced_as(study.traced), "design_as": _design_as(study.traced)}
        (study.root / SAMPLE).parent.mkdir(parents=True, exist_ok=True)
        (study.root / SAMPLE).write_text(json.dumps(drawn, indent=2) + "\n", encoding="utf-8")
    to_read = {*drawn["trials"], *(t.nct for t in study.traced if t.place == IN_DOUBT)}
    borne_out, accuracy = _sample_bears_the_trace_out(study, drawn["trials"])
    if all(_settled(study, nct) for nct in drawn["trials"]) and not borne_out:
        to_read |= set(_to_read(study.traced))
        print(f"the trace matched the adjudicators on only {accuracy['outcome_matched']} of the {accuracy['trials']} sampled, "
              f"so every traced trial is listed for them to read")
    worklist = study.root / REFERENCE_WORKLIST
    write_table(worklist, ("nct", "acronym", "title", "scored_endpoint"),
                [(nct, study.candidates[nct].get("acronym"), study.candidates[nct].get("brief_title"),
                  study.candidates[nct]["scored_endpoint"]) for nct in sorted(to_read)])
    print(f"{counted(len(to_read), 'trial')} for both adjudicators, listed in {worklist}; "
          f"the draw is kept in {study.root / SAMPLE}")
    return 0


def _require_as_drawn(study: _Study, drawn: dict) -> None:
    """The reference set must be what the sample was drawn from: the same draw, traces and design rulings.

    The trace is judged as it stood when the sample was drawn. A trace changed
    since, to match the adjudicators or for any other reason, is not the trace
    they checked; nor is a set from which a design ruling has since removed a
    trial they contradicted the trace on.
    """
    when = f"the sample was drawn on {drawn['drawn_on']}"
    if drawn.get("seed") != SAMPLE_SEED or _draw(list(drawn["drawn_from"])) != drawn["trials"]:
        raise NotFrozen(f"{study.root / SAMPLE} is not the draw of {SAMPLE_SIZE} from the trials it names")
    as_drawn, design_then = drawn.get("traced_as", {}), drawn.get("design_as", {})
    as_now, design_now = _traced_as(study.traced), _design_as(study.traced)
    joined = sorted(set(as_now) - set(as_drawn))
    if joined:
        raise NotFrozen(f"{counted(len(joined), 'trial')} joined the reference set after {when}, so the sample no longer "
                        f"speaks for it: {', '.join(joined[:10])}")
    # A trial with a result, or left in doubt, is part of what the adjudicators are checking. One with no readout is
    # not counted in any figure and may yet be sealed, so a ruling that later excludes its design is no concern here.
    checked = {*drawn["drawn_from"], *drawn.get("in_doubt", ())}
    ruled = sorted(nct for nct in checked if design_now.get(nct) != design_then.get(nct))
    if ruled:
        raise NotFrozen(f"a design ruling was made after {when} for {counted(len(ruled), 'trial')}: {', '.join(ruled[:10])}; "
                        f"the reference set is the one that was drawn from")
    retraced = sorted(nct for nct in as_drawn
                      if as_now.get(nct) != as_drawn[nct] and (nct in checked or design_now.get(nct) != EXCLUDED_DESIGN))
    if retraced:
        raise NotFrozen(f"{counted(len(retraced), 'trial')} have been traced or re-checked differently since {when}: "
                        f"{', '.join(retraced[:10])}")


def freeze(study: _Study) -> int:
    """Fix the figures the base-rate forecaster will use, once, and only when they are fit to be fixed.

    The reference set must be what the sample was drawn from. Nothing may still
    be waiting to be counted, and the adjudicators must have settled every
    sampled trial. Their readings of the sample must bear the trace out: if they
    contradict it too often, the traces they did not read cannot be relied on,
    and they read every traced trial with a result before anything is fixed. The
    file records what it was made from.
    """
    frozen, drawn = study.root / FROZEN, _drawn(study.root)
    if frozen.exists():
        raise NotFrozen(f"the base rates are already frozen in {frozen}")
    if drawn is not None:
        _require_as_drawn(study, drawn)
    waiting = [t.nct for t in study.trials if t.place in NOT_YET_COUNTED]
    if waiting:
        raise NotFrozen(f"{counted(len(waiting), 'trial')} are not yet counted (in doubt, awaiting a re-check or a design "
                        f"ruling): {', '.join(waiting[:10])}{' and more' if len(waiting) > 10 else ''}")
    if drawn is None:
        raise NotFrozen("the adjudicators' sample has not been drawn")
    unread = [nct for nct in drawn["trials"] if not _settled(study, nct)]
    if unread:
        raise NotFrozen(f"the adjudicators have not settled {len(unread)} of the {len(drawn['trials'])} trials in their sample")
    borne_out, of_the_sample = _sample_bears_the_trace_out(study, drawn["trials"])
    everything = _to_read(study.traced)
    unread = [nct for nct in everything if not _settled(study, nct)]
    if not borne_out and unread:
        raise NotFrozen(f"the trace had the outcome right for only {of_the_sample['outcome_matched']} of the "
                        f"{of_the_sample['trials']} sampled trials, so the traces the adjudicators did not read cannot be relied "
                        f"on. They have not settled {len(unread)} of the {len(everything)} trials now listed by "
                        f"`trialseal-reference sample`")
    figures = frozen_base_rates(study.trials, study.today)
    figures.update(made_from=_made_from(study.root), snapshot=study.snapshot, adjudicated=sum(t.adjudicated for t in study.trials),
                   trace_accuracy=trace_accuracy(study.traced, study.adjudicated, study.no_result_found),
                   trace_accuracy_on_the_sample=of_the_sample)
    frozen.parent.mkdir(parents=True, exist_ok=True)
    frozen.write_text(json.dumps(figures, indent=2) + "\n", encoding="utf-8")
    print(f"base rates frozen in {frozen}")
    return 0


def main(arguments: list[str] | None = None, today: dt.date | None = None) -> int:
    """Work with the reference set: `trialseal-reference report|sample|freeze --study <directory>`.

    `report` writes the base-rate table, the hazard-ratio table and the list of
    trials. `sample` draws, once, the trials both adjudicators are to read.
    `freeze` fixes the figures the base-rate forecaster will use, once.
    """
    parser = argparse.ArgumentParser(prog="trialseal-reference", description=__doc__.split("\n\n")[0])
    parser.add_argument("step", choices=("report", "sample", "freeze"))
    parser.add_argument("--study", default=".", help="the study directory (default: the current directory)")
    options = parser.parse_args(arguments)
    try:
        study = _load(pathlib.Path(options.study), today or dt.date.today())
        return {"report": report, "sample": sample, "freeze": freeze}[options.step](study)
    except NotFrozen as refused:
        print(f"NOT FROZEN: {refused}")
    except (ValueError, KeyError, TypeError, OSError) as problem:
        # A file that cannot be read as what it should be: say so, and change nothing.
        print(f"NOT DONE: {problem}")
    return 1
