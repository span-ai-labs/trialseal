"""Screening: checking each candidate for an existing public primary result before a batch.

A screening record is one search of one candidate on one day, with what it found
and how sure the searcher was. A decision of high confidence stands by itself; one
of low or medium confidence waits for the study lead to confirm it. A candidate
whose design may rule it out also needs a person's ruling before it can be eligible.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
from dataclasses import dataclass
from typing import Iterable

from trialforecast.forecasting import Candidate
from trialforecast.records import require_plain_date, require_trial_id
from trialforecast.universe import drug_name

ELIGIBLE, READ_OUT, VOID = "eligible", "already_read_out", "void"
DECISIONS = (ELIGIBLE, READ_OUT, VOID)
HIGH, MEDIUM, LOW = "high", "medium", "low"
CONFIDENCES = (HIGH, MEDIUM, LOW)
INCLUDE, EXCLUDE = "include", "exclude"
AWAITING_CONFIRMATION, NOT_SCREENED = "awaiting_confirmation", "not_screened"
EXCLUDED_DESIGN, AWAITING_DESIGN_REVIEW = "excluded_design", "awaiting_design_review"

# A screening older than this may have been overtaken by a readout.
SCREENING_VALID_DAYS = 14


class IneligibleTrial(Exception):
    """A trial that screening has not cleared was about to enter a batch or a seal."""


@dataclass(frozen=True)
class ScreeningRecord:
    """One search of one candidate for a public primary result: what was decided, on what evidence, how surely."""

    nct: str
    decision: str
    screened_on: dt.date  # the day of the search; a confirmation does not move it
    evidence: str  # what was searched and what was found
    confidence: str
    evidence_links: tuple[str, ...] = ()
    screened_by: str = ""  # the person or the tool that searched
    confirmed_by: str | None = None  # the study lead, where a decision of low or medium confidence was confirmed
    confirmed_on: dt.date | None = None
    readout_date: dt.date | None = None  # for a trial that has read out: the earliest disclosure found
    investigational_drug: str | None = None  # the drug under test, where the registry's default needed correcting

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        object.__setattr__(self, "evidence_links", tuple(self.evidence_links))
        if self.decision not in DECISIONS:
            raise ValueError(f"{self.nct}: screening decision must be one of {DECISIONS}, not {self.decision!r}")
        if self.confidence not in CONFIDENCES:
            raise ValueError(f"{self.nct}: confidence must be one of {CONFIDENCES}, not {self.confidence!r}")
        if not self.evidence.strip():
            raise ValueError(f"{self.nct}: a screening decision needs its evidence")
        require_plain_date(self.screened_on, f"{self.nct}: screening date")
        if (self.confirmed_by is None) != (self.confirmed_on is None) or (self.confirmed_by is not None and not self.confirmed_by.strip()):
            raise ValueError(f"{self.nct}: a confirmation names who confirmed and gives the day")
        if self.confirmed_on is not None:
            require_plain_date(self.confirmed_on, f"{self.nct}: confirmation date")
            if self.confirmed_on < self.screened_on:
                raise ValueError(f"{self.nct}: a decision cannot be confirmed before the search it rests on")
        if self.decision == READ_OUT:
            if self.readout_date is None or not self.evidence_links:
                raise ValueError(f"{self.nct}: a trial recorded as read out needs its readout date and a link to the source")
            require_plain_date(self.readout_date, f"{self.nct}: readout date")
            if self.readout_date > self.screened_on:
                raise ValueError(f"{self.nct}: a readout cannot be dated {self.readout_date}, before it was found")
        elif self.readout_date is not None:
            raise ValueError(f"{self.nct}: only a trial that has read out has a readout date")
        drug = self.investigational_drug
        if drug is not None and (not drug or drug != drug_name(drug)):
            raise ValueError(f"{self.nct}: a drug is held in one spelling, {drug_name(str(drug))!r}, not {drug!r}")

    @property
    def stands(self) -> bool:
        """Whether the decision counts: it was made with high confidence, or the study lead confirmed it."""
        return self.confidence == HIGH or self.confirmed_by is not None


def confirmed(record: ScreeningRecord, by: str, on: dt.date) -> ScreeningRecord:
    """The study lead's confirmation of a decision, as a new record: the log is only ever added to.

    The search keeps its own date, so confirming a decision does not make an old search a recent one.
    """
    return dataclasses.replace(record, confirmed_by=by.strip(), confirmed_on=on)


@dataclass(frozen=True)
class DesignReview:
    """A person's ruling on whether a candidate's design keeps it in the study or rules it out."""

    nct: str
    decision: str  # INCLUDE or EXCLUDE
    reason: str
    reviewed_by: str
    reviewed_on: dt.date

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        if self.decision not in (INCLUDE, EXCLUDE):
            raise ValueError(f"{self.nct}: a design review rules to include or exclude, not {self.decision!r}")
        if not self.reason.strip() or not self.reviewed_by.strip():
            raise ValueError(f"{self.nct}: a design review gives its reason and names the person who ruled")
        require_plain_date(self.reviewed_on, f"{self.nct}: review date")


def _latest(its_records: list[ScreeningRecord]) -> ScreeningRecord:
    """A trial's latest search; of two on one day, the last recorded."""
    latest = its_records[0]
    for record in its_records[1:]:
        if record.screened_on >= latest.screened_on:
            latest = record
    return latest


def _unanswered(its_records: list[ScreeningRecord]) -> list[ScreeningRecord]:
    """Reports that a trial read out or ended which do not stand and which the study lead has not yet answered.

    Only the study lead answers one: by confirming it, or by a confirmed decision,
    recorded afterwards from a search no older, that the trial is eligible after
    all. A searcher's later finding of nothing, however confident, does not.
    """
    waiting = []
    for position, report in enumerate(its_records):
        if report.decision == ELIGIBLE or report.stands:
            continue
        confirmed_since = any(r.decision == report.decision and r.stands and r.screened_on == report.screened_on
                              for r in its_records[position + 1:])
        overruled = any(r.decision == ELIGIBLE and r.confirmed_by is not None and r.screened_on >= report.screened_on
                        for r in its_records[position + 1:])
        if not confirmed_since and not overruled:
            waiting.append(report)
    return waiting


def _bar(its_records: list[ScreeningRecord]) -> str | None:
    """What keeps a trial out whatever its latest search says: a standing readout or end, or a report awaiting the lead."""
    settled = [r.decision for r in its_records if r.stands and r.decision != ELIGIBLE]
    if settled:
        return READ_OUT if READ_OUT in settled else VOID
    return AWAITING_CONFIRMATION if _unanswered(its_records) else None


def _by_trial(log: Iterable[ScreeningRecord], on: dt.date) -> dict[str, list[ScreeningRecord]]:
    """Each trial's records in the order they were recorded. A record dated after the day plays no part."""
    by_trial: dict[str, list[ScreeningRecord]] = {}
    for record in log:
        if record.screened_on <= on:
            by_trial.setdefault(record.nct, []).append(record)
    return by_trial


def screening_status(log: Iterable[ScreeningRecord], batch_date: dt.date) -> dict[str, str]:
    """Where screening leaves each trial for a batch on this date.

    A trial with a standing record that it read out, or is void (ended without a primary
    analysis), is never eligible again. One with such a report that does not stand
    awaits the study lead, however long ago the report was made. Otherwise its
    latest search decides: if that is older than 14 days the trial is not
    screened; if it does not stand the trial awaits confirmation; if it stands the
    trial is eligible.
    """
    status = {}
    for nct, its_records in _by_trial(log, batch_date).items():
        latest = _latest(its_records)
        if _bar(its_records) is not None:
            status[nct] = _bar(its_records)
        elif (batch_date - latest.screened_on).days > SCREENING_VALID_DAYS:
            status[nct] = NOT_SCREENED
        else:
            status[nct] = ELIGIBLE if latest.stands else AWAITING_CONFIRMATION
    return status


def _rulings(design_reviews: Iterable[DesignReview]) -> dict[str, DesignReview]:
    """The ruling that stands for each trial: the latest, and of two on one day the last recorded."""
    standing: dict[str, DesignReview] = {}
    for review in design_reviews:
        if review.nct not in standing or review.reviewed_on >= standing[review.nct].reviewed_on:
            standing[review.nct] = review
    return standing


def _design(nct: str, tagged: object, rulings: dict[str, DesignReview]) -> str | None:
    """Why a design keeps a trial out for now, or None if it does not: ruled out, or tagged and not yet ruled on."""
    ruling = rulings.get(nct)
    if ruling is not None and ruling.decision == EXCLUDE:
        return EXCLUDED_DESIGN
    return AWAITING_DESIGN_REVIEW if isinstance(tagged, str) and tagged and ruling is None else None


def design_status(candidate: Candidate, design_reviews: Iterable[DesignReview]) -> str | None:
    """Why a candidate's design keeps it out for now, or None if it does not."""
    return _design(candidate["nct"], candidate.get("exclusion_review"), _rulings(design_reviews))


def eligible_trials(
    candidates: Iterable[Candidate], log: Iterable[ScreeningRecord], batch_date: dt.date,
    design_reviews: Iterable[DesignReview] = (),
) -> list[Candidate]:
    """The candidates that are eligible trials for a batch on this date.

    Unscreened candidates are not, nor is one whose design a person has ruled out
    or has yet to rule on where the candidate is tagged for exclusion review.
    """
    status, rulings = screening_status(log, batch_date), _rulings(design_reviews)
    return [c for c in candidates
            if status.get(c["nct"]) == ELIGIBLE and _design(c["nct"], c.get("exclusion_review"), rulings) is None]


def require_eligible(
    batch_date: dt.date, trials: Iterable[tuple[str, object]], log: Iterable[ScreeningRecord],
    design_reviews: Iterable[DesignReview],
) -> None:
    """The one gate into a batch or a seal: refuse unless every trial is cleared for this date.

    Each trial is given as its registry number and its exclusion-review tag. It
    must be screened as eligible, and its design must not be ruled out, nor tagged
    for exclusion review with no ruling yet.
    """
    status, rulings = screening_status(log, batch_date), _rulings(design_reviews)
    trials = list(trials)
    unscreened = [nct for nct, _ in trials if status.get(nct) != ELIGIBLE]
    if unscreened:
        raise IneligibleTrial(f"not screened as eligible for {batch_date}: {', '.join(unscreened)}")
    for nct, tagged in trials:
        why = _design(nct, tagged, rulings)
        if why == EXCLUDED_DESIGN:
            raise IneligibleTrial(f"{nct}: its design was excluded ({rulings[nct].reason})")
        if why == AWAITING_DESIGN_REVIEW:
            raise IneligibleTrial(f"{nct}: tagged for exclusion review ({tagged}) and no person has ruled on it")


def corrected_drugs(log: Iterable[ScreeningRecord], batch_date: dt.date) -> dict[str, str]:
    """The investigational drug screening recorded for each trial, where the registry's default needed correcting."""
    corrected = {}
    for record in log:
        if record.investigational_drug and record.stands and record.screened_on <= batch_date:
            corrected[record.nct] = record.investigational_drug
    return corrected


def found_no_result(log: Iterable[ScreeningRecord], on_or_after: dt.date, by: dt.date) -> set[str]:
    """Trials that a standing search made between two dates found without a public result, with nothing since to bar them."""
    cleared = set()
    for nct, its_records in _by_trial(log, by).items():
        searched = any(r.decision == ELIGIBLE and r.stands and r.screened_on >= on_or_after for r in its_records)
        if searched and _bar(its_records) is None:
            cleared.add(nct)
    return cleared


def screening_summary(
    candidates: Iterable[Candidate], log: Iterable[ScreeningRecord], design_reviews: Iterable[DesignReview], on: dt.date
) -> dict:
    """Every candidate in exactly one place, with the lists the study lead and the reference set need.

    A design ruled out comes first, then a readout or an end without analysis,
    then what waits for confirmation or was not screened, then a design nobody
    has ruled on; what is left is eligible. The queue for the study lead holds
    every decision that waits for a ruling, not only each trial's latest.
    """
    candidates = sorted(candidates, key=lambda c: c["nct"])
    by_trial, status, rulings = _by_trial(log, on), screening_status(log, on), _rulings(design_reviews)
    places: dict[str, list[Candidate]] = {name: [] for name in (
        ELIGIBLE, READ_OUT, VOID, EXCLUDED_DESIGN, AWAITING_CONFIRMATION, AWAITING_DESIGN_REVIEW, NOT_SCREENED)}
    read_out, queue, design_queue = [], [], []
    for candidate in candidates:
        nct, its_records = candidate["nct"], by_trial.get(candidate["nct"], [])
        design, screening = _design(nct, candidate.get("exclusion_review"), rulings), status.get(nct, NOT_SCREENED)
        if design == EXCLUDED_DESIGN:
            places[EXCLUDED_DESIGN].append(candidate)
        elif screening != ELIGIBLE:
            places[screening].append(candidate)
        else:
            places[design or ELIGIBLE].append(candidate)
        if design != EXCLUDED_DESIGN and screening == READ_OUT:
            # The earliest readout any standing record found, since the reference set wants the first disclosure.
            read_out.append(min((r for r in its_records if r.decision == READ_OUT and r.stands), key=lambda r: r.readout_date))
        if design != EXCLUDED_DESIGN and screening == AWAITING_CONFIRMATION:
            waiting = _unanswered(its_records)
            queue += waiting if waiting else [_latest(its_records)]
        # A design ruling does not go stale, so every tagged candidate still in play is queued, screened or not.
        if design == AWAITING_DESIGN_REVIEW and screening not in (READ_OUT, VOID):
            design_queue.append(candidate)
    return {
        "counts": {name: len(found) for name, found in places.items()},
        "eligible": places[ELIGIBLE],
        "read_out": read_out,
        "excluded": [rulings[c["nct"]] for c in places[EXCLUDED_DESIGN]],
        "queue": queue,
        "design_queue": design_queue,
        "not_screened": places[NOT_SCREENED],
    }
