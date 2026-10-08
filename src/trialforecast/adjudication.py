"""Adjudication: how two people's readings of a trial's sources become one result.

Each adjudication is one person's reading of one source. A source's reading stands
when two adjudicators record the same reading, or when a reconciliation settles
their disagreement. A trial has a result only when every source recorded for it
stands; the most authoritative source then decides the outcome (ADR-0008).

Everything is computed "as of" an analysis date from entries recorded by then, in
order of recording, so the same log always gives the same result.
"""
from __future__ import annotations

import datetime as dt
import pathlib
from dataclasses import dataclass, field
from typing import Iterable, NamedTuple

from trialforecast import records
from trialforecast.dates import add_months
from trialforecast.records import require_plain_date, require_trial_id

OUTCOMES = ("positive", "negative", "void")
WITH_READOUT = ("positive", "negative")  # a void trial has no readout

# Most authoritative first. A registry posting ranks last because it is entered by the sponsor unreviewed.
SOURCE_TYPES = ("paper_or_regulator", "conference", "press_release_or_filing", "registry")

# How a trial's primary endpoints combine: one endpoint, any one of several, or all of several.
ENDPOINT_RULES = ("single", "any_of", "co_primary")
ENDPOINT_RESULTS = ("met", "not_met", "not_reported")
EARLY_STOPS = ("efficacy", "futility", "no_analysis")

HAZARD_RATIO_WINDOW_MONTHS = 6  # ADR-0011
HAZARD_RATIO_STATUSES = ("reported", "awaited", "missing", "not_applicable")

# Why a trial with adjudications has no result yet, most serious first.
NOT_BLIND, DISAGREEMENT, ONE_READING = (
    "adjudicated after opening the forecasts", "disagreement", "awaiting second adjudication")


class NotBlind(Exception):
    """An adjudication was made by someone who had already opened that trial's forecasts."""


def normalised_name(name: str) -> str:
    """One spelling per person: "Abhijoy" and "abhijoy " must not count as two adjudicators."""
    return name.strip().casefold()


def derive_outcome(endpoint_rule: str, endpoint_results: Iterable[str], early_stop: str | None = None) -> str | None:
    """The outcome a trial's primary endpoint results imply, or None if not yet decidable.

    Where any one endpoint suffices, one met endpoint makes the trial positive. Where
    all are needed, one missed endpoint makes it negative. An early stop for
    efficacy is positive and for futility negative; a trial ended without a
    primary analysis is void.
    """
    if early_stop is not None:
        return {"efficacy": "positive", "futility": "negative", "no_analysis": "void"}[early_stop]
    shown = list(endpoint_results)
    if endpoint_rule == "co_primary":
        if "not_met" in shown:
            return "negative"
        return "positive" if shown and all(r == "met" for r in shown) else None
    if "met" in shown:
        return "positive"
    return "negative" if shown and all(r == "not_met" for r in shown) else None


def _check_reading(nct: str, source_type: str, outcome: str, hazard_ratio: float | None,
                   hazard_ratio_endpoint: str | None) -> None:
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"{nct}: source type must be one of {SOURCE_TYPES}, not {source_type!r}")
    if outcome not in OUTCOMES:
        raise ValueError(f"{nct}: outcome must be one of {OUTCOMES}, not {outcome!r}")
    if hazard_ratio is None:
        return
    if outcome == "void":
        raise ValueError(f"{nct}: a void trial has no hazard ratio")
    if hazard_ratio <= 0:
        raise ValueError(f"{nct}: hazard ratio {hazard_ratio} must be positive")
    if not (hazard_ratio_endpoint or "").strip():
        raise ValueError(f"{nct}: a hazard ratio must say which endpoint it is for")


@dataclass(frozen=True)
class Adjudication:
    """One adjudicator's reading of one source about one trial."""

    nct: str
    adjudicator: str
    recorded_on: dt.date
    source_type: str
    source: str
    disclosed_on: dt.date
    language: str
    original_text: str
    translation: str | None
    endpoint_rule: str
    endpoint_results: tuple[str, ...]
    early_stop: str | None
    outcome: str
    hazard_ratio: float | None = None
    hazard_ratio_endpoint: str | None = None

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        object.__setattr__(self, "adjudicator", normalised_name(self.adjudicator))
        object.__setattr__(self, "language", self.language.strip().casefold())
        object.__setattr__(self, "endpoint_results", tuple(self.endpoint_results))
        if self.hazard_ratio is not None:
            object.__setattr__(self, "hazard_ratio", float(self.hazard_ratio))
        if not self.adjudicator:
            raise ValueError(f"{self.nct}: an adjudication must name its adjudicator")
        if not self.source.strip():
            raise ValueError(f"{self.nct}: an adjudication must cite its source")
        require_plain_date(self.recorded_on, f"{self.nct}: recording date")
        require_plain_date(self.disclosed_on, f"{self.nct}: disclosure date")
        if self.disclosed_on > self.recorded_on:
            raise ValueError(f"{self.nct}: a source must be disclosed before it is adjudicated")
        if not self.language:
            raise ValueError(f"{self.nct}: an adjudication must record the disclosure language")
        if not self.original_text.strip():
            raise ValueError(f"{self.nct}: an adjudication must hold the original text it relies on")
        if self.language != "en" and not (self.translation or "").strip():
            raise ValueError(f"{self.nct}: a disclosure in {self.language!r} needs a translation beside the original")
        _check_reading(self.nct, self.source_type, self.outcome, self.hazard_ratio, self.hazard_ratio_endpoint)
        self._check_basis()

    def _check_basis(self) -> None:
        if self.endpoint_rule not in ENDPOINT_RULES:
            raise ValueError(f"{self.nct}: endpoint rule must be one of {ENDPOINT_RULES}, not {self.endpoint_rule!r}")
        if any(r not in ENDPOINT_RESULTS for r in self.endpoint_results):
            raise ValueError(f"{self.nct}: endpoint results must be among {ENDPOINT_RESULTS}")
        if self.early_stop is not None and self.early_stop not in EARLY_STOPS:
            raise ValueError(f"{self.nct}: early stop must be one of {EARLY_STOPS}, not {self.early_stop!r}")
        count = len(self.endpoint_results)
        if self.early_stop is not None:
            expected = count == 0  # the stop decides; per-endpoint results beside it would contradict it
        elif self.endpoint_rule == "single":
            expected = count == 1
        else:
            expected = count >= 2
        implied = derive_outcome(self.endpoint_rule, self.endpoint_results, self.early_stop)
        if not expected or implied != self.outcome:
            raise ValueError(
                f"{self.nct}: outcome {self.outcome!r} does not follow from its basis "
                f"({self.endpoint_rule}, {self.endpoint_results}, early stop {self.early_stop})"
            )


@dataclass(frozen=True)
class Reconciliation:
    """The adjudicators' settled reading of a source they first read differently."""

    nct: str
    source_type: str
    source: str
    outcome: str
    hazard_ratio: float | None
    hazard_ratio_endpoint: str | None
    disclosed_on: dt.date
    reason: str
    adjudicators: tuple[str, ...]
    recorded_on: dt.date

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        object.__setattr__(self, "adjudicators", tuple(sorted({normalised_name(a) for a in self.adjudicators} - {""})))
        if self.hazard_ratio is not None:
            object.__setattr__(self, "hazard_ratio", float(self.hazard_ratio))
        if len(self.adjudicators) < 2:
            raise ValueError(f"{self.nct}: a reconciliation needs both adjudicators")
        if not self.reason.strip():
            raise ValueError(f"{self.nct}: a reconciliation needs its reason")
        require_plain_date(self.recorded_on, f"{self.nct}: recording date")
        require_plain_date(self.disclosed_on, f"{self.nct}: disclosure date")
        if self.disclosed_on > self.recorded_on:
            raise ValueError(f"{self.nct}: a source must be disclosed before its reading is reconciled")
        _check_reading(self.nct, self.source_type, self.outcome, self.hazard_ratio, self.hazard_ratio_endpoint)


@dataclass(frozen=True)
class Withdrawal:
    """An adjudicator taking back their reading of a source, for example one cited by mistake."""

    nct: str
    adjudicator: str
    source_type: str
    source: str
    reason: str
    recorded_on: dt.date

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        object.__setattr__(self, "adjudicator", normalised_name(self.adjudicator))
        if not self.reason.strip():
            raise ValueError(f"{self.nct}: a withdrawal needs its reason")
        require_plain_date(self.recorded_on, f"{self.nct}: recording date")


@dataclass(frozen=True)
class ForecastAccess:
    """A record that someone opened a trial's forecasts."""

    nct: str
    person: str
    opened_on: dt.date

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        object.__setattr__(self, "person", normalised_name(self.person))
        require_plain_date(self.opened_on, f"{self.nct}: date the forecasts were opened")


@dataclass(frozen=True)
class AdjudicationLog:
    """Everything recorded about adjudication: readings, reconciliations, withdrawals, and who opened forecasts.

    Each kind of entry is kept in the order it was recorded: the log is only ever added to.
    """

    adjudications: tuple[Adjudication, ...] = ()
    reconciliations: tuple[Reconciliation, ...] = ()
    withdrawals: tuple[Withdrawal, ...] = ()
    forecast_access: tuple[ForecastAccess, ...] = ()

    def __post_init__(self) -> None:
        for kind in LOG_KINDS:
            object.__setattr__(self, kind, tuple(getattr(self, kind)))

    def sizes(self) -> tuple[int, ...]:
        """How many entries of each kind the log holds, which fixes its state at a moment."""
        return tuple(len(getattr(self, kind)) for kind in LOG_KINDS)

    def first(self, sizes: Iterable[int]) -> AdjudicationLog:
        """The log as it stood when it held this many entries of each kind."""
        sizes = tuple(sizes)
        if len(sizes) != len(LOG_KINDS) or any(not 0 <= n <= held for n, held in zip(sizes, self.sizes())):
            raise ValueError(f"the log holds fewer entries {self.sizes()} than it once did {sizes}")
        return AdjudicationLog(*(getattr(self, kind)[:n] for kind, n in zip(LOG_KINDS, sizes)))

    def added_after(self, sizes: Iterable[int]) -> list:
        """Every entry added since the log held this many of each kind."""
        self.first(sizes)
        return [entry for kind, n in zip(LOG_KINDS, sizes) for entry in getattr(self, kind)[n:]]


def entered_on(log_entry) -> dt.date:
    """The day a log entry says it was made."""
    return log_entry.opened_on if isinstance(log_entry, ForecastAccess) else log_entry.recorded_on


# Each kind of entry, in the order of the log's fields: the file that holds it and its record type.
LOG_KINDS = {
    "adjudications": ("adjudications.jsonl", Adjudication),
    "reconciliations": ("reconciliations.jsonl", Reconciliation),
    "withdrawals": ("withdrawals.jsonl", Withdrawal),
    "forecast_access": ("forecast_access.jsonl", ForecastAccess),
}


def read_log(directory: pathlib.Path) -> AdjudicationLog:
    """Everything recorded about adjudication, from the directory that holds it. A kind with no file has no entries."""
    return AdjudicationLog(**{
        kind: records.read(directory / file_name, record_type) if (directory / file_name).exists() else ()
        for kind, (file_name, record_type) in LOG_KINDS.items()
    })


class SourceReading(NamedTuple):
    """What one source is taken to show, once its reading stands."""

    source_type: str
    source: str
    disclosed_on: dt.date
    outcome: str
    hazard_ratio: float | None
    hazard_ratio_endpoint: str | None
    language: str

    @property
    def rank(self) -> int:
        """0 for the most authoritative source type."""
        return SOURCE_TYPES.index(self.source_type)


@dataclass(frozen=True)
class TrialResult:
    nct: str
    outcome: str
    readout_date: dt.date | None  # the earliest disclosure of any rank; None for a void trial
    disclosure_language: str  # of the source that set the readout date (ADR-0010)
    hazard_ratio: float | None  # the first reported, if within the window (ADR-0011)
    hazard_ratio_endpoint: str | None
    hazard_ratio_status: str  # one of HAZARD_RATIO_STATUSES
    decided_by: SourceReading
    history: tuple[SourceReading, ...]  # every standing reading, in order of disclosure

    @property
    def first_disclosed_on(self) -> dt.date:
        """The readout date, or for a void trial the earliest disclosure that it had ended."""
        return self.readout_date or self.history[0].disclosed_on

    @property
    def revised(self) -> bool:
        """Whether a source disclosed before the deciding one showed a different outcome."""
        return any(
            r.disclosed_on < self.decided_by.disclosed_on and r.outcome != self.outcome for r in self.history
        )


@dataclass
class _Source:
    """The state of one source of one trial while the log is replayed."""

    readings: dict[str, Adjudication] = field(default_factory=dict)  # each adjudicator's current reading
    disputed: bool = False  # once two adjudicators have differed, only a reconciliation settles it
    reconciliation: Reconciliation | None = None


def _what_was_read(a: Adjudication) -> tuple:
    return (a.outcome, a.hazard_ratio, a.hazard_ratio_endpoint, a.disclosed_on, a.language,
            a.endpoint_rule, a.endpoint_results, a.early_stop)


def _first_opened(log: AdjudicationLog) -> dict[tuple[str, str], dt.date]:
    opened: dict[tuple[str, str], dt.date] = {}
    for access in log.forecast_access:
        key = (access.nct, access.person)
        opened[key] = min(access.opened_on, opened.get(key, access.opened_on))
    return opened


def _saw_forecasts_first(opened: dict, nct: str, who: Iterable[str], recorded_on: dt.date) -> list[str]:
    return [name for name in who if (nct, name) in opened and opened[(nct, name)] <= recorded_on]


def _replay(
    log: AdjudicationLog, analysis_date: dt.date
) -> tuple[dict[tuple[str, str, str], _Source], set[tuple[str, str, str]]]:
    """Replay entries recorded by the analysis date, in order of recording.

    Returns each source's final state and the sources where a reading or reconciliation
    still in force was made by someone who had already opened that trial's forecasts.
    """
    # On one day: readings, then withdrawals, then reconciliations. Position in the log breaks remaining ties.
    entries = sorted(
        (e for kind in (log.adjudications, log.withdrawals, log.reconciliations) for e in kind
         if e.recorded_on <= analysis_date),
        key=lambda e: (e.recorded_on, (Adjudication, Withdrawal, Reconciliation).index(type(e))),
    )
    sources: dict[tuple[str, str, str], _Source] = {}
    for entry in entries:
        key = (entry.nct, entry.source_type, entry.source)
        if isinstance(entry, Adjudication):
            source = sources.setdefault(key, _Source())
            source.readings[entry.adjudicator] = entry
            source.reconciliation = None  # a reading entered after a reconciliation reopens the source
            if len({_what_was_read(a) for a in source.readings.values()}) > 1:
                source.disputed = True
        elif isinstance(entry, Withdrawal):
            if key not in sources or entry.adjudicator not in sources[key].readings:
                raise ValueError(f"{entry.nct}: {entry.adjudicator} has nothing to withdraw for {entry.source!r}")
            del sources[key].readings[entry.adjudicator]
            if not sources[key].readings:
                del sources[key]
        else:
            source = sources.get(key)
            if source is None or not source.disputed or set(entry.adjudicators) != set(source.readings):
                raise ValueError(
                    f"{entry.nct}: the reconciliation of {entry.source!r} does not settle a recorded "
                    f"disagreement between its adjudicators"
                )
            source.reconciliation = entry

    # Judged on what is still in force, so a reading that was not blind can be withdrawn and replaced.
    opened = _first_opened(log)
    not_blind: set[tuple[str, str, str]] = set()
    for key, source in sources.items():
        in_force = [(a.adjudicator, a.recorded_on) for a in source.readings.values()]
        if source.reconciliation is not None:
            in_force += [(name, source.reconciliation.recorded_on) for name in source.reconciliation.adjudicators]
        if any(_saw_forecasts_first(opened, key[0], [name], recorded_on) for name, recorded_on in in_force):
            not_blind.add(key)
    return sources, not_blind


def _standing_readings(
    log: AdjudicationLog, analysis_date: dt.date, disclosed_by: dt.date | None = None
) -> tuple[dict[str, list[SourceReading]], dict[str, str]]:
    """Per trial: its standing source readings, or the most serious reason it has no result yet.

    A source that every entry dates after `disclosed_by` is outside the analysis, settled or not.
    """
    sources, not_blind = _replay(log, analysis_date)
    standing: dict[str, list[SourceReading]] = {}
    held_back: dict[str, str] = {}

    def hold_back(nct: str, reason: str) -> None:
        order = (NOT_BLIND, DISAGREEMENT, ONE_READING)
        if nct not in held_back or order.index(reason) < order.index(held_back[nct]):
            held_back[nct] = reason

    for (nct, source_type, source_ref), source in sources.items():
        any_reading = next(iter(source.readings.values()))
        dated = [a.disclosed_on for a in source.readings.values()]
        if source.reconciliation is not None:
            dated = [source.reconciliation.disclosed_on]
        if disclosed_by is not None and min(dated) > disclosed_by:
            continue
        if (nct, source_type, source_ref) in not_blind:
            hold_back(nct, NOT_BLIND)
            continue
        if source.reconciliation is not None:
            settled = source.reconciliation
            reading = SourceReading(source_type, source_ref, settled.disclosed_on, settled.outcome,
                                    settled.hazard_ratio, settled.hazard_ratio_endpoint, any_reading.language)
        elif source.disputed:
            hold_back(nct, DISAGREEMENT)
            continue
        elif len(source.readings) < 2:
            hold_back(nct, ONE_READING)
            continue
        else:
            reading = SourceReading(source_type, source_ref, any_reading.disclosed_on, any_reading.outcome,
                                    any_reading.hazard_ratio, any_reading.hazard_ratio_endpoint, any_reading.language)
        standing.setdefault(nct, []).append(reading)
    return {nct: readings for nct, readings in standing.items() if nct not in held_back}, held_back


def awaiting_result(log: AdjudicationLog, analysis_date: dt.date, disclosed_by: dt.date | None = None) -> dict[str, str]:
    """Trials with adjudications but no result yet, and the most serious reason for each."""
    return _standing_readings(log, analysis_date, disclosed_by)[1]


def results(log: AdjudicationLog, analysis_date: dt.date, disclosed_by: dt.date | None = None) -> dict[str, TrialResult]:
    """Each trial's result, from what had been adjudicated by the analysis date.

    The most authoritative standing source decides the outcome (the later of two
    of one rank); the earliest disclosure sets the readout date; the hazard ratio
    is the first reported, if it came within six months of the readout.

    An analysis fixed for a date passes it as `disclosed_by`: only sources
    disclosed by then count, and a hazard ratio is awaited or missing as of then,
    however long after that date the adjudication was finished.
    """
    as_of = analysis_date if disclosed_by is None else min(analysis_date, disclosed_by)
    found = {}
    for nct, readings in _standing_readings(log, analysis_date, disclosed_by)[0].items():
        history = tuple(sorted(readings, key=lambda r: (r.disclosed_on, r.rank, r.source)))
        decided_by = min(history, key=lambda r: (r.rank, -r.disclosed_on.toordinal(), r.source))
        if decided_by.outcome == "void":
            found[nct] = TrialResult(nct, "void", None, decided_by.language, None, None, "not_applicable",
                                     decided_by, history)
            continue
        readout = next(r for r in history if r.outcome in WITH_READOUT)
        deadline = add_months(readout.disclosed_on, HAZARD_RATIO_WINDOW_MONTHS)
        first_reported = next((r for r in history if r.hazard_ratio is not None), None)
        if first_reported is not None and first_reported.disclosed_on <= deadline:
            hazard_ratio, endpoint, status = first_reported.hazard_ratio, first_reported.hazard_ratio_endpoint, "reported"
        elif first_reported is None and as_of <= deadline:
            hazard_ratio, endpoint, status = None, None, "awaited"
        else:
            hazard_ratio, endpoint, status = None, None, "missing"
        found[nct] = TrialResult(nct, decided_by.outcome, readout.disclosed_on, readout.language, hazard_ratio,
                                 endpoint, status, decided_by, history)
    return found


def record_adjudication(
    log_file: pathlib.Path, adjudication: Adjudication, forecast_access: Iterable[ForecastAccess]
) -> None:
    """Append an adjudication to its log, unless its author has already opened the trial's forecasts."""
    opened = _first_opened(AdjudicationLog(forecast_access=tuple(forecast_access)))
    if _saw_forecasts_first(opened, adjudication.nct, [adjudication.adjudicator], adjudication.recorded_on):
        raise NotBlind(f"{adjudication.adjudicator} opened the forecasts for {adjudication.nct} before adjudicating it")
    records.append(log_file, adjudication)


def record_reconciliation(log_file: pathlib.Path, reconciliation: Reconciliation, log: AdjudicationLog) -> None:
    """Append a reconciliation to its log, if it settles a recorded disagreement and its adjudicators are still blind."""
    with_it = AdjudicationLog(log.adjudications, (*log.reconciliations, reconciliation), log.withdrawals,
                              log.forecast_access)
    _, not_blind = _replay(with_it, reconciliation.recorded_on)
    if (reconciliation.nct, reconciliation.source_type, reconciliation.source) in not_blind:
        raise NotBlind(f"{reconciliation.nct}: reconciled after an adjudicator opened its forecasts")
    records.append(log_file, reconciliation)
