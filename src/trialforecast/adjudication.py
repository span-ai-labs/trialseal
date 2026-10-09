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
import math
import pathlib
import unicodedata
import dataclasses
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
    """One spelling per person: "Abhijoy S", "abhijoy s " and "Abhijoy  S" must not count as two adjudicators."""
    return " ".join(unicodedata.normalize("NFKC", name).split()).casefold()


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
    if not math.isfinite(hazard_ratio) or hazard_ratio <= 0:
        raise ValueError(f"{nct}: hazard ratio {hazard_ratio} must be a positive, finite number")
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
    language: str | None = None  # settled only where the two read the language of the disclosure differently

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        object.__setattr__(self, "adjudicators", tuple(sorted({normalised_name(a) for a in self.adjudicators} - {""})))
        object.__setattr__(self, "language", (self.language or "").strip().casefold() or None)
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
class Dissent:
    """An adjudicator's record that a source the other adjudicator cited does not state the trial's result.

    It is how the two come to differ on a source that only one of them finds
    anything in. From then on the source is one they have read differently.
    """

    nct: str
    adjudicator: str
    source_type: str
    source: str
    reason: str  # what the source holds instead of the result
    recorded_on: dt.date

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        object.__setattr__(self, "adjudicator", normalised_name(self.adjudicator))
        if not self.adjudicator:
            raise ValueError(f"{self.nct}: a dissent must name its adjudicator")
        if not self.reason.strip():
            raise ValueError(f"{self.nct}: a dissent must say what the source holds instead of the result")
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
    """Everything recorded about adjudication: readings, reconciliations, withdrawals, dissents, and who opened forecasts.

    Each kind of entry is kept in the order it was recorded: the log is only ever added to.
    """

    adjudications: tuple[Adjudication, ...] = ()
    reconciliations: tuple[Reconciliation, ...] = ()
    withdrawals: tuple[Withdrawal, ...] = ()
    forecast_access: tuple[ForecastAccess, ...] = ()
    dissents: tuple[Dissent, ...] = ()

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

    def with_reconciliation(self, reconciliation: Reconciliation) -> AdjudicationLog:
        """The log as it would stand with one more reconciliation."""
        return dataclasses.replace(self, reconciliations=(*self.reconciliations, reconciliation))

    def with_entry(self, entry) -> AdjudicationLog:
        """The log as it would stand with one more entry of whatever kind it is."""
        kind = next(kind for kind, (_, record_type) in LOG_KINDS.items() if isinstance(entry, record_type))
        return dataclasses.replace(self, **{kind: (*getattr(self, kind), entry)})

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
    "dissents": ("dissents.jsonl", Dissent),
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
class SourceState:
    """Where one source of one trial stands: who has read it, and whether they differed and have settled it."""

    readings: dict[str, Adjudication] = field(default_factory=dict)  # each adjudicator's current reading
    disputed: bool = False  # once two adjudicators have differed, only a reconciliation settles it
    disputed_on: dt.date | None = None  # the day they first differed
    # First read while the two differed on another source of the trial, when they may have talked about the trial:
    # its readings were not made independently, so it is disputed from the start.
    after_talk: bool = False
    reconciliation: Reconciliation | None = None
    dissents: dict[str, Dissent] = field(default_factory=dict)  # who finds, of the readings in force, that it states no result


def what_was_read(a: Adjudication) -> tuple:
    """Everything two adjudicators must agree on for a source's reading to stand."""
    endpoint = None if a.hazard_ratio_endpoint is None else " ".join(a.hazard_ratio_endpoint.casefold().split())
    return (a.outcome, a.hazard_ratio, endpoint, a.disclosed_on, a.language,
            a.endpoint_rule, a.endpoint_results, a.early_stop)


def _first_opened(log: AdjudicationLog) -> dict[tuple[str, str], dt.date]:
    opened: dict[tuple[str, str], dt.date] = {}
    for access in log.forecast_access:
        key = (access.nct, access.person)
        opened[key] = min(access.opened_on, opened.get(key, access.opened_on))
    return opened


def _saw_forecasts_first(opened: dict, nct: str, who: Iterable[str], recorded_on: dt.date) -> list[str]:
    return [name for name in who if (nct, name) in opened and opened[(nct, name)] <= recorded_on]


def _differing_since(sources: dict, nct: str, before: dt.date | None = None, on: dt.date | None = None) -> bool:
    """Whether the trial has a source its adjudicators differ on and have not reconciled, since before a day or from a day."""
    return any(key[0] == nct and source.disputed and source.reconciliation is None
               and ((before is not None and source.disputed_on < before) or source.disputed_on == on)
               for key, source in sources.items())


def _replay(
    log: AdjudicationLog, analysis_date: dt.date
) -> tuple[dict[tuple[str, str, str], SourceState], set[tuple[str, str, str]], set[tuple[str, str, str]]]:
    """Replay entries recorded by the analysis date, in order of recording.

    Returns each source's final state; the sources where a reading or reconciliation
    still in force was made by someone who had already opened that trial's forecasts;
    and, among those, the sources that were disclosed only after every such person
    had opened them. Those last are later sources read after a reveal (ADR-0015).
    """
    # On one day: readings, then dissents, then withdrawals, then reconciliations. Position in the log breaks
    # remaining ties.
    in_order = (Adjudication, Dissent, Withdrawal, Reconciliation)
    entries = sorted(
        (e for kind in (log.adjudications, log.dissents, log.withdrawals, log.reconciliations) for e in kind
         if e.recorded_on <= analysis_date),
        key=lambda e: (e.recorded_on, in_order.index(type(e))),
    )
    sources: dict[tuple[str, str, str], SourceState] = {}
    for entry in entries:
        key = (entry.nct, entry.source_type, entry.source)
        if isinstance(entry, Adjudication):
            if key not in sources:
                sources[key] = SourceState()
                if _differing_since(sources, entry.nct, before=entry.recorded_on):
                    sources[key].disputed = sources[key].after_talk = True
                    sources[key].disputed_on = entry.recorded_on
            source = sources[key]
            earlier = source.readings.get(entry.adjudicator)
            changed = earlier is None or what_was_read(earlier) != what_was_read(entry)
            source.readings[entry.adjudicator] = entry
            # A reading entered after a reconciliation reopens the source, unless it only puts a quote right.
            if changed:
                source.reconciliation = None
            if len({what_was_read(a) for a in source.readings.values()}) > 1 and not source.disputed:
                source.disputed, source.disputed_on = True, entry.recorded_on
            # A dissent is from the readings as they stood. A new or changed reading is one its author has not seen
            # the source against; and once they read the source themselves it is no longer a dissent.
            if changed:
                source.dissents.clear()
        elif isinstance(entry, Dissent):
            source = sources.get(key)
            if source is None or not source.readings or entry.adjudicator in source.readings:
                raise ValueError(f"{entry.nct}: {entry.adjudicator} has nobody else's reading of {entry.source!r} to dissent from")
            if not source.disputed:  # the two differ on whether it states a result at all
                source.disputed, source.disputed_on = True, entry.recorded_on
            source.dissents[entry.adjudicator] = entry
        elif isinstance(entry, Withdrawal):
            if key not in sources or entry.adjudicator not in sources[key].readings:
                raise ValueError(f"{entry.nct}: {entry.adjudicator} has nothing to withdraw for {entry.source!r}")
            del sources[key].readings[entry.adjudicator]
            sources[key].reconciliation = None  # what the two settled rested on both readings
            # A source that was read differently stays, with nobody's reading: reading it alike later does not
            # dissolve the disagreement.
            if not sources[key].readings:
                sources[key].dissents.clear()
                if not sources[key].disputed:
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
    after_reveal: set[tuple[str, str, str]] = set()
    for key, source in sources.items():
        in_force = [(a.adjudicator, a.recorded_on) for a in source.readings.values()]
        disclosed = [a.disclosed_on for a in source.readings.values()]
        if source.reconciliation is not None:
            in_force += [(name, source.reconciliation.recorded_on) for name in source.reconciliation.adjudicators]
            disclosed.append(source.reconciliation.disclosed_on)
        saw_first = [name for name, recorded_on in in_force if _saw_forecasts_first(opened, key[0], [name], recorded_on)]
        if saw_first:
            not_blind.add(key)
            if all(opened[(key[0], name)] < min(disclosed) for name in saw_first):
                after_reveal.add(key)
    return sources, not_blind, after_reveal


def source_states(log: AdjudicationLog, as_of: dt.date) -> dict[tuple[str, str, str], SourceState]:
    """Every source by trial, source type and source, as the log stood on a day.

    Each has a reading in force, except a source that was read differently and
    then withdrawn by both: that one is kept, with no readings, so that the
    disagreement is remembered if it is read again.
    """
    return _replay(log, as_of)[0]


class _Standing(NamedTuple):
    """Where adjudication stands: each settled trial's readings, why others have no result yet, and what was set aside."""

    readings: dict[str, list[SourceReading]]
    held_back: dict[str, str]
    set_aside: dict[str, list[str]]
    unsettled: dict[str, list[str]]  # sources read once, or read differently and not reconciled, whoever read them


def _standing_readings(
    log: AdjudicationLog, analysis_date: dt.date, disclosed_by: dt.date | None = None, count_set_aside: bool = False
) -> _Standing:
    """Per trial: its standing source readings, or the most serious reason it has no result yet.

    A source that every entry dates after `disclosed_by` is outside the analysis, settled or not.

    A source read by someone who had already opened the trial's forecasts decides
    nothing (ADR-0015). If it was disclosed only after they opened them, it is a
    later source read after the reveal: it is set aside, and the trial's blind
    readings stand; if the trial has none, it has no result. If the source was
    already public when the forecasts were opened, reading it late is simply not
    blind, and the trial is held back until a blind reading replaces it. With
    `count_set_aside`, settled later sources are counted like any other, as one
    sensitivity analysis does.
    """
    sources, not_blind, after_reveal = _replay(log, analysis_date)
    standing: dict[str, list[SourceReading]] = {}
    held_back: dict[str, str] = {}
    aside: dict[str, list[str]] = {}
    open_sources: dict[str, list[str]] = {}

    def hold_back(nct: str, reason: str) -> None:
        order = (NOT_BLIND, DISAGREEMENT, ONE_READING)
        if nct not in held_back or order.index(reason) < order.index(held_back[nct]):
            held_back[nct] = reason

    for key, source in sources.items():
        nct, source_type, source_ref = key
        if not source.readings:
            continue  # read differently once and since withdrawn by both: nothing is in force, and it decides nothing
        any_reading = next(iter(source.readings.values()))
        dated = [a.disclosed_on for a in source.readings.values()]
        if source.reconciliation is not None:
            dated = [source.reconciliation.disclosed_on]
        if disclosed_by is not None and min(dated) > disclosed_by:
            continue
        unsettled = source.reconciliation is None and (source.disputed or len(source.readings) < 2)
        if unsettled:
            open_sources.setdefault(nct, []).append(source_ref)
        if key in not_blind:
            if key not in after_reveal:
                hold_back(nct, NOT_BLIND)
                continue
            if not count_set_aside or unsettled:
                aside.setdefault(nct, []).append(source_ref)
                continue
        if source.reconciliation is not None:
            settled = source.reconciliation
            reading = SourceReading(source_type, source_ref, settled.disclosed_on, settled.outcome,
                                    settled.hazard_ratio, settled.hazard_ratio_endpoint,
                                    settled.language or any_reading.language)
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
    for nct in aside:
        if nct not in standing:
            hold_back(nct, NOT_BLIND)
    settled_trials = {nct: readings for nct, readings in standing.items() if nct not in held_back}
    return _Standing(settled_trials, held_back, {nct: sorted(refs) for nct, refs in aside.items() if nct in settled_trials},
                     {nct: sorted(refs) for nct, refs in open_sources.items()})


def unsettled_sources(log: AdjudicationLog, analysis_date: dt.date, disclosed_by: dt.date | None = None) -> dict[str, list[str]]:
    """Trials with a source that one adjudicator has read alone, or two have read differently and not reconciled.

    This counts set-aside sources too: they decide no outcome, but a hazard ratio
    taken from one must be a number both readers recorded.
    """
    return _standing_readings(log, analysis_date, disclosed_by).unsettled


def set_aside(log: AdjudicationLog, analysis_date: dt.date, disclosed_by: dt.date | None = None) -> dict[str, list[str]]:
    """Trials with a result whose later sources were read after the forecasts were opened, and those sources."""
    return _standing_readings(log, analysis_date, disclosed_by).set_aside


def awaiting_result(log: AdjudicationLog, analysis_date: dt.date, disclosed_by: dt.date | None = None) -> dict[str, str]:
    """Trials with adjudications but no result yet, and the most serious reason for each."""
    return _standing_readings(log, analysis_date, disclosed_by).held_back


def results(
    log: AdjudicationLog, analysis_date: dt.date, disclosed_by: dt.date | None = None, count_set_aside: bool = False
) -> dict[str, TrialResult]:
    """Each trial's result, from what had been adjudicated by the analysis date.

    The most authoritative standing source decides the outcome (the later of two
    of one rank); the earliest disclosure sets the readout date; the hazard ratio
    is the first reported, if it came within six months of the readout.

    An analysis fixed for a date passes it as `disclosed_by`: only sources
    disclosed by then count, and a hazard ratio is awaited or missing as of then,
    however long after that date the adjudication was finished. Sources read
    after the forecasts were opened count only with `count_set_aside`.
    """
    as_of = analysis_date if disclosed_by is None else min(analysis_date, disclosed_by)
    found = {}
    for nct, readings in _standing_readings(log, analysis_date, disclosed_by, count_set_aside).readings.items():
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


def _require_today(what: str, nct: str, recorded_on: dt.date, today: dt.date) -> None:
    if recorded_on != today:
        raise ValueError(f"{nct}: {what} is recorded on the day it is made, {today}, not dated {recorded_on}; "
                         f"an entry dated earlier could pass for one made before the forecasts were opened")


def record_adjudication(log_file: pathlib.Path, adjudication: Adjudication, log: AdjudicationLog, today: dt.date) -> None:
    """Append an adjudication to its log, if it may be recorded and the log can place it among the day's entries."""
    require_recordable(adjudication, log.forecast_access, today)
    require_fits_the_log(adjudication, log, today)
    records.append(log_file, adjudication)


def require_recordable(adjudication: Adjudication, forecast_access: Iterable[ForecastAccess], today: dt.date) -> None:
    """A reading is recorded on the day it is made, and not if its author could have read the source blind and did not.

    Someone who has opened a trial's forecasts may still read a source disclosed
    after they opened them: that reading is set aside in every registered analysis
    (ADR-0015). A source that was already public when they opened the forecasts
    is refused, since nothing but a blind reading of it will ever count.
    """
    _require_today("a reading", adjudication.nct, adjudication.recorded_on, today)
    opened = _first_opened(AdjudicationLog(forecast_access=tuple(forecast_access)))
    first_seen = opened.get((adjudication.nct, adjudication.adjudicator))
    if first_seen is not None and first_seen <= adjudication.recorded_on and adjudication.disclosed_on <= first_seen:
        raise NotBlind(f"{adjudication.adjudicator} opened the forecasts for {adjudication.nct} before adjudicating it")


def record_forecast_access(log_file: pathlib.Path, access: ForecastAccess, today: dt.date) -> None:
    """Record that someone opened a trial's forecasts, on the day they did. An entry dated any other day is refused,
    because a back-dated one could be used to set aside a reading that was made blind."""
    if access.opened_on != today:
        raise ValueError(f"{access.nct}: forecasts are recorded as opened today, {today}, not on {access.opened_on}")
    records.append(log_file, access)


def record_reconciliation(log_file: pathlib.Path, reconciliation: Reconciliation, log: AdjudicationLog, today: dt.date) -> None:
    """Append a reconciliation to its log, if it may be recorded."""
    require_reconcilable(reconciliation, log, today)
    records.append(log_file, reconciliation)


def require_reconcilable(reconciliation: Reconciliation, log: AdjudicationLog, today: dt.date) -> None:
    """A reconciliation settles a recorded disagreement between the two who read the source, on the day it is made.

    Its adjudicators must still be blind, unless the source is a later one read
    after a reveal: that is set aside for the outcome whoever settles it, and
    settling it is how its hazard ratio comes to be one number (ADR-0015).
    """
    _require_today("a reconciliation", reconciliation.nct, reconciliation.recorded_on, today)
    sources, not_blind, after_reveal = _replay(log.with_reconciliation(reconciliation), reconciliation.recorded_on)
    source = (reconciliation.nct, reconciliation.source_type, reconciliation.source)
    if source in not_blind and source not in after_reveal:
        raise NotBlind(f"{reconciliation.nct}: reconciled after an adjudicator opened its forecasts")
    # A reconciliation settles what the two differed on. What they agreed on is not reopened by it.
    first, second = (what_was_read(reading) for reading in sources[source].readings.values())
    settled_endpoint = (None if reconciliation.hazard_ratio_endpoint is None
                        else " ".join(reconciliation.hazard_ratio_endpoint.casefold().split()))
    no_hazard_ratio = reconciliation.hazard_ratio is None  # settling that the source gives none leaves no endpoint either
    for what, settled, position, may_differ in (
        ("the outcome", reconciliation.outcome, 0, False),
        ("the hazard ratio", reconciliation.hazard_ratio, 1, False),
        ("the hazard ratio's endpoint", settled_endpoint, 2, no_hazard_ratio),
        ("the disclosure date", reconciliation.disclosed_on, 3, False),
        ("the language", reconciliation.language, 4, reconciliation.language is None),
    ):
        if first[position] == second[position] and settled != first[position] and not may_differ:
            raise ValueError(f"{reconciliation.nct}: both adjudicators read {what} the same way, so the reconciliation "
                             f"cannot change it")
    if first[4] != second[4] and reconciliation.language not in (first[4], second[4]):
        raise ValueError(f"{reconciliation.nct}: the adjudicators recorded different languages for the disclosure "
                         f"({first[4]}, {second[4]}), so the reconciliation must say which language it was in")


def record_withdrawal(log_file: pathlib.Path, withdrawal: Withdrawal, log: AdjudicationLog, today: dt.date) -> None:
    """Append an adjudicator's withdrawal of a reading they have in force, on the day it is made.

    A reading made blind cannot be taken back by someone who has since opened
    the trial's forecasts: they would be choosing, with the forecasts in view,
    which sources decide the result. A reading they made after opening them
    counts for nothing and may be withdrawn. Withdrawing a reading of a
    reconciled source reopens it, since what the two settled rested on both
    readings; on the day it was reconciled the log could not tell which came
    first, so that waits a day.
    """
    _require_today("a withdrawal", withdrawal.nct, withdrawal.recorded_on, today)
    source = source_states(log, today).get((withdrawal.nct, withdrawal.source_type, withdrawal.source))
    if source is None or withdrawal.adjudicator not in source.readings:
        raise ValueError(f"{withdrawal.nct}: {withdrawal.adjudicator} has no reading of {withdrawal.source!r} to withdraw")
    if source.reconciliation is not None and source.reconciliation.recorded_on == today:
        raise ValueError(f"{withdrawal.nct}: {withdrawal.source!r} was reconciled today; a reading of it can be "
                         f"withdrawn from tomorrow")
    opened = _first_opened(log).get((withdrawal.nct, withdrawal.adjudicator))
    if opened is not None and opened <= today and source.readings[withdrawal.adjudicator].recorded_on < opened:
        raise NotBlind(f"{withdrawal.adjudicator} opened the forecasts for {withdrawal.nct} before withdrawing a reading "
                       f"made blind")
    records.append(log_file, withdrawal)


def require_fits_the_log(adjudication: Adjudication, log: AdjudicationLog, today: dt.date) -> None:
    """Refuse a reading the log could not place in order among the day's other entries.

    Entries of one day are replayed readings first, then dissents, withdrawals
    and reconciliations, whatever order they were made in. So a reading of a
    source made on a day when a reading of it was withdrawn would be replayed
    beside the withdrawn one; one made on the day the source was reconciled
    would be replayed before the reconciliation and not reopen it; and one made
    on the day of a dissent would be replayed as if the dissent were from it.
    Each waits a day. So does a new source for a trial on the day its
    adjudicators first differed on another: the log could not tell whether it
    was read before the two talked or after, and after is not independent.
    """
    source = (adjudication.nct, adjudication.source_type, adjudication.source)

    def today_holds(entries) -> bool:
        return any((e.nct, e.source_type, e.source) == source and e.recorded_on == today for e in entries)

    if today_holds(log.withdrawals):
        raise ValueError(f"{adjudication.nct}: a reading of this source was withdrawn today; it can be read again from tomorrow")
    if today_holds(log.reconciliations):
        raise ValueError(f"{adjudication.nct}: this source was reconciled today; a new reading of it can be recorded from tomorrow")
    if today_holds(log.dissents):
        raise ValueError(f"{adjudication.nct}: this source was found today not to state the result; a reading of it "
                         f"can be recorded from tomorrow")
    sources = source_states(log, today)
    if source not in sources and _differing_since(sources, adjudication.nct, on=today):
        raise ValueError(f"{adjudication.nct}: a source of this trial was first read differently today; a new source for "
                         f"it can be recorded from tomorrow")


def require_dissent_recordable(dissent: Dissent, log: AdjudicationLog, today: dt.date) -> None:
    """A dissent is made on the day, blind, from someone else's reading of a source its author has not read."""
    _require_today("a dissent", dissent.nct, dissent.recorded_on, today)
    source = source_states(log, today).get((dissent.nct, dissent.source_type, dissent.source))
    if source is not None and dissent.adjudicator in source.readings:
        raise ValueError(f"{dissent.nct}: {dissent.adjudicator} has a reading of this source in force; withdraw it "
                         f"to say the source does not state the result")
    if source is None or not source.readings:
        raise ValueError(f"{dissent.nct}: nobody has a reading of this source in force, so there is nothing to differ "
                         f"with; a source that states no result is simply not recorded")
    if any((w.nct, w.adjudicator, w.source_type, w.source, w.recorded_on) ==
           (dissent.nct, dissent.adjudicator, dissent.source_type, dissent.source, today) for w in log.withdrawals):
        # Entries of a day are replayed dissents before withdrawals, so it would be a dissent from one's own reading.
        raise ValueError(f"{dissent.nct}: you withdrew your reading of this source today; a dissent from it can be "
                         f"recorded from tomorrow")
    # Like a reading: someone who has opened the forecasts may only take up a source disclosed after they opened them.
    opened = _first_opened(log).get((dissent.nct, dissent.adjudicator))
    if opened is not None and opened <= today and any(r.disclosed_on <= opened for r in source.readings.values()):
        raise NotBlind(f"{dissent.adjudicator} opened the forecasts for {dissent.nct} before reading this source")
    source_states(log.with_entry(dissent), today)  # whatever else the replay would refuse


def record_dissent(log_file: pathlib.Path, dissent: Dissent, log: AdjudicationLog, today: dt.date) -> None:
    """Append a dissent to its log, if it may be recorded."""
    require_dissent_recordable(dissent, log, today)
    records.append(log_file, dissent)


def require_nothing_from_the_future(entries: Iterable, today: dt.date) -> None:
    """Everything here is worked out as of today, so an entry dated later would be quietly left out of all of it."""
    latest = max((entered_on(entry) for entry in entries), default=today)
    if latest > today:
        raise ValueError(f"the log holds an entry dated {latest}, after today ({today}): check this computer's date")


# --- a search that found nothing ---------------------------------------------------------------


@dataclass(frozen=True)
class NothingFound:
    """An adjudicator's finding, after searching, that no public source states the result of a trial's primary analysis.

    It is kept beside the adjudication log and is no part of it: it gives a trial
    no result. It is how two adjudicators say that a trial someone else took to
    have read out has, as far as either can find, not.
    """

    nct: str
    adjudicator: str
    searched: str  # where they looked, in their own words
    recorded_on: dt.date

    def __post_init__(self) -> None:
        require_trial_id(self.nct)
        object.__setattr__(self, "adjudicator", normalised_name(self.adjudicator))
        if not self.adjudicator:
            raise ValueError(f"{self.nct}: a finding of nothing must name its adjudicator")
        if not self.searched.strip():
            raise ValueError(f"{self.nct}: a finding of nothing must say where the adjudicator looked")
        require_plain_date(self.recorded_on, f"{self.nct}: recording date")


NOTHING_FOUND = "nothing_found.jsonl"


def read_nothing_found(directory: pathlib.Path) -> list[NothingFound]:
    """The findings of nothing kept in a log's directory, in the order they were recorded."""
    return records.read(directory / NOTHING_FOUND, NothingFound) if (directory / NOTHING_FOUND).exists() else []


def _with_a_reading(log: AdjudicationLog, as_of: dt.date) -> dict[str, set[str]]:
    """For each trial, the adjudicators with a reading of any of its sources in force."""
    readers: dict[str, set[str]] = {}
    for (nct, _, _), source in source_states(log, as_of).items():
        if source.readings:
            readers.setdefault(nct, set()).update(source.readings)
    return readers


def no_result_found(findings: Iterable[NothingFound], log: AdjudicationLog, as_of: dt.date) -> dict[str, tuple[str, ...]]:
    """Trials that two adjudicators searched for and found nothing, and who they were, as things stood on a day.

    A reading in force outweighs a finding of nothing: once either adjudicator
    has read a source for the trial, it is waiting for the other to read that
    source, and is no longer a trial with nothing found. A source both have
    withdrawn, each with a reason, no longer counts for the trial, even one they
    had read differently: the withdrawals are the record of why.
    """
    readers = _with_a_reading(log, as_of)
    found: dict[str, set[str]] = {}
    for finding in findings:
        if finding.recorded_on <= as_of and finding.nct not in readers:
            found.setdefault(finding.nct, set()).add(finding.adjudicator)
    return {nct: tuple(sorted(who)) for nct, who in found.items() if len(who) >= 2}


def require_nothing_found_recordable(finding: NothingFound, log: AdjudicationLog, today: dt.date) -> None:
    """A finding of nothing is made on the day, blind, by someone with no reading of the trial in force.

    Blind, because someone who has seen the forecasts could decline to find a
    result they would rather not count. And an adjudicator who has read a source
    for the trial has found something: they withdraw that reading first if it
    was a mistake.
    """
    _require_today("a finding of nothing", finding.nct, finding.recorded_on, today)
    if finding.adjudicator in _with_a_reading(log, today).get(finding.nct, ()):
        raise ValueError(f"{finding.nct}: {finding.adjudicator} has a reading of a source for {finding.nct} in force, "
                         f"so cannot also have found nothing")
    if _saw_forecasts_first(_first_opened(log), finding.nct, [finding.adjudicator], finding.recorded_on):
        raise NotBlind(f"{finding.adjudicator} opened the forecasts for {finding.nct} before searching for its result")


def record_nothing_found(log_file: pathlib.Path, finding: NothingFound, log: AdjudicationLog, today: dt.date) -> None:
    """Append a finding of nothing to its file, if it may be recorded."""
    require_nothing_found_recordable(finding, log, today)
    records.append(log_file, finding)


def adjudicator_agreement(log: AdjudicationLog) -> dict:
    """How often the two adjudicators' first readings of a source agreed.

    First readings are compared, before any correction or reconciliation, since
    those are what two people reached independently. Two kinds of source are
    counted apart, since their readings were not independent: one that an
    adjudicator dissented from before ever reading it, and one first read while
    the two differed on another source of the trial. Cohen's kappa is given for
    the outcome, and is undefined when both called every source the same way.
    Hazard ratios are compared wherever either recorded one, and agree when they
    name the same endpoint and match to two decimal places. A source read by one
    person, or by more than two, is counted and not compared.
    """
    first: dict[tuple, dict[str, object]] = {}
    for reading in sorted(log.adjudications, key=lambda a: a.recorded_on):  # a stable sort: log order breaks ties
        first.setdefault((reading.nct, reading.source_type, reading.source), {}).setdefault(reading.adjudicator, reading)
    # A dissent made before its author ever read the source: whatever they read in it later followed the dissent.
    dissented = {(d.nct, d.source_type, d.source) for d in log.dissents
                 if not (first.get((d.nct, d.source_type, d.source), {}).get(d.adjudicator) is not None
                         and first[(d.nct, d.source_type, d.source)][d.adjudicator].recorded_on < d.recorded_on)}
    after_talk = {source for source, state in _replay(log, dt.date.max)[0].items() if state.after_talk} - dissented
    apart = dissented | after_talk
    pairs = [tuple(by_adjudicator[name] for name in sorted(by_adjudicator))
             for source, by_adjudicator in first.items() if len(by_adjudicator) == 2 and source not in apart]
    agreed = sum(a.outcome == b.outcome for a, b in pairs)
    with_ratio = [(a, b) for a, b in pairs if a.hazard_ratio is not None or b.hazard_ratio is not None]

    def same_ratio(a, b) -> bool:
        if a.hazard_ratio is None or b.hazard_ratio is None:
            return False
        same_endpoint = " ".join(a.hazard_ratio_endpoint.casefold().split()) == " ".join(b.hazard_ratio_endpoint.casefold().split())
        return same_endpoint and round(a.hazard_ratio, 2) == round(b.hazard_ratio, 2)

    kappa = None
    if pairs:
        observed = agreed / len(pairs)
        outcomes = {reading.outcome for pair in pairs for reading in pair}
        by_chance = sum(sum(a.outcome == o for a, _ in pairs) * sum(b.outcome == o for _, b in pairs)
                        for o in outcomes) / len(pairs) ** 2
        kappa = None if by_chance == 1 else (observed - by_chance) / (1 - by_chance)
    return {"sources": len(pairs), "not_read_by_two": sum(len(by) != 2 for source, by in first.items() if source not in apart),
            "one_found_no_result_stated": len(dissented), "read_after_the_two_had_talked": len(after_talk),
            "outcome_agreed": agreed, "kappa": kappa,
            "disclosure_date_agreed": sum(a.disclosed_on == b.disclosed_on for a, b in pairs),
            "hazard_ratio_compared": len(with_ratio), "hazard_ratio_agreed": sum(same_ratio(a, b) for a, b in with_ratio)}
