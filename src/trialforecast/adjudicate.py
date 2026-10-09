"""The adjudicators' command: each fills in a form, the command records it, and disagreements are settled between them.

    <study>/study/adjudicators.json        the adjudicators' names
    <study>/adjudication/<set>/            the record: readings, reconciliations, withdrawals, findings of nothing
    <study>/adjudication/working/<set>/    each adjudicator's form and the list of disagreements; never published

    form            write an adjudicator's form: a row for every source waiting for their reading
    record          record the filled rows of that form, all of them or none
    status          say where each trial stands
    disagreements   lay the two readings of each source read differently side by side, and name each dissent
    reconcile       record what the two settled for those sources, with their reason
    withdraw        take back a reading of a source cited by mistake

An adjudicator's form gives the sources the other adjudicator has cited, with
nothing of what was read in them, and a blank row for each trial nobody has
read. A filled row becomes a reading dated the day it is recorded; or a finding
of nothing, where the adjudicator searched and found no source that states the
trial's result; or a dissent, where they find that a source the other cited
does not state it.

The command cannot tell who is typing. That each adjudicator works alone, and
that both are present for a reconciliation, rests on the two of them.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import pathlib
import re
from dataclasses import dataclass
from typing import Callable, Iterable

from trialforecast.adjudication import (
    EARLY_STOPS, ENDPOINT_RESULTS, ENDPOINT_RULES, LOG_KINDS, NOT_BLIND, NOTHING_FOUND, OUTCOMES, SOURCE_TYPES,
    Adjudication, AdjudicationLog, Dissent, NotBlind, NothingFound, Reconciliation, SourceState, Withdrawal,
    awaiting_result, derive_outcome, no_result_found, normalised_name, read_log, read_nothing_found, record_adjudication,
    record_dissent, record_nothing_found, record_reconciliation, record_withdrawal, require_dissent_recordable,
    require_fits_the_log, require_nothing_found_recordable, require_nothing_from_the_future, require_reconcilable,
    require_recordable, results, source_states, what_was_read,
)
from trialforecast.reference import FROZEN
from trialforecast.studyfiles import (
    PILOT_ADJUDICATION, PILOT_WORKLIST, REFERENCE_ADJUDICATION, REFERENCE_WORKLIST, latest_snapshot, read_table,
    registry_records, write_table,
)
from trialforecast.wording import counted

ADJUDICATORS = pathlib.Path("study") / "adjudicators.json"
WORKING_FILES = pathlib.Path("adjudication") / "working"

# The trials each log is about: the directory of the log, the list of trials to read, the command that writes the
# list, and the file whose existence closes the log because figures made from it have been fixed.
SETS = {
    "reference": (REFERENCE_ADJUDICATION, REFERENCE_WORKLIST, "trialseal-reference sample", FROZEN),
    "pilot": (PILOT_ADJUDICATION, PILOT_WORKLIST, "trialseal-pilot report", None),
}

ABOUT_THE_TRIAL = ("nct", "title", "scored_endpoint")
WHAT_IS_READ = ("disclosed_on", "original_text", "translation", "endpoint_results", "early_stop", "hazard_ratio")
SEARCHED = "nothing_found"  # where the adjudicator looked, or what a cited source holds instead of the result
AS_GIVEN = "as_given"  # a mark on a row the command filled in with a source, to tell it from one the adjudicator typed
FORM_COLUMNS = (*ABOUT_THE_TRIAL, "primary_outcomes", "source_type", "source", "disclosed_on", "language", "original_text",
                "translation", "endpoint_rule", "endpoint_results", "early_stop", "hazard_ratio", "hazard_ratio_endpoint",
                SEARCHED, AS_GIVEN)
ONE_ADJUDICATORS_CELLS = ("adjudicator", "outcome", "disclosed_on", "hazard_ratio", "hazard_ratio_endpoint", "endpoint_rule",
                          "endpoint_results", "early_stop", "language", "original_text", "translation")
AS_LISTED = "as_listed"  # a mark of the two readings a row was written from, to tell if either has changed since
SETTLED = ("settled_outcome", "settled_disclosed_on", "settled_hazard_ratio", "settled_hazard_ratio_endpoint",
           "settled_language", "reason")
DISAGREEMENT_COLUMNS = (*ABOUT_THE_TRIAL, "source_type", "source",
                        *(f"{which}_{cell}" for which in ("first", "second") for cell in ONE_ADJUDICATORS_CELLS), AS_LISTED,
                        *SETTLED)

# A hazard ratio outside this range is far more likely a slipped decimal point than a trial's result.
PLAUSIBLE_HAZARD_RATIOS = (0.05, 20.0)

SourceKey = tuple[str, str, str]  # registry number, source type, source


class RowsRefused(Exception):
    """Rows of a file that cannot be recorded, each with why. Nothing of the file is recorded."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class _Study:
    """What the command reads from a study directory: one set of trials, its log, and the day."""

    root: pathlib.Path
    set: str
    today: dt.date
    trials: dict[str, dict]  # the worklist by registry number, in its order, then any other trial the log holds
    adjudicators: dict[str, str]  # each name as the log spells it, and as the study lists it
    log: AdjudicationLog
    nothing_found: list[NothingFound]
    sources: dict[SourceKey, SourceState]

    @property
    def log_dir(self) -> pathlib.Path:
        return self.root / SETS[self.set][0]

    @property
    def working_files(self) -> pathlib.Path:
        return self.root / WORKING_FILES / self.set

    def log_file(self, kind: str) -> pathlib.Path:
        return self.log_dir / LOG_KINDS[kind][0]

    def named(self, adjudicator: str) -> str:
        return self.adjudicators.get(adjudicator, adjudicator)

    def read_by(self, nct: str) -> dict[SourceKey, SourceState]:
        """The trial's sources with a reading in force."""
        return {key: state for key, state in self.sources.items() if key[0] == nct and state.readings}

    def found_nothing(self, nct: str) -> set[str]:
        """Who has searched for the trial and found nothing."""
        return {finding.adjudicator for finding in self.nothing_found if finding.nct == nct}

    @property
    def dissented(self) -> dict[SourceKey, tuple[str, ...]]:
        """Sources one adjudicator has read and the other finds not to state the result, and who finds so."""
        return {key: tuple(sorted(state.dissents)) for key, state in self.sources.items() if state.dissents}


def _file_name(adjudicator: str) -> str:
    return re.sub(r"\W+", "-", adjudicator).strip("-")


def _adjudicators(root: pathlib.Path) -> dict[str, str]:
    """The study's adjudicators: one or two people, each under one spelling and one file name."""
    listed = root / ADJUDICATORS
    how = f'{listed} must hold the adjudicators\' names, as ["First Name", "Second Name"]'
    try:
        names = json.loads(listed.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"the study's adjudicators are not named: {how}") from None
    except json.JSONDecodeError:
        raise ValueError(how) from None
    if not isinstance(names, list) or not all(isinstance(name, str) and name.strip() for name in names):
        raise ValueError(how)
    by_spelling = {normalised_name(name): " ".join(name.split()) for name in names}
    file_names = {_file_name(name) for name in by_spelling}
    if not 1 <= len(names) <= 2 or len(by_spelling) != len(names) or len(file_names) != len(names) or "" in file_names:
        raise ValueError(f"{how}: one or two people, each named once")
    return by_spelling


def _registry(root: pathlib.Path) -> dict[str, dict]:
    """The latest registry snapshot's records, or none where the study directory holds no snapshot."""
    try:
        return registry_records(latest_snapshot(root))
    except ValueError:
        return {}


def _load(root: pathlib.Path, name: str, today: dt.date) -> _Study:
    log_dir, worklist, written_by, _ = SETS[name]
    if not (root / worklist).exists():
        raise ValueError(f"there is no list of trials to adjudicate at {root / worklist}; `{written_by}` writes it")
    listed = read_table(root / worklist)
    if listed and "nct" not in listed[0]:
        raise ValueError(f"{root / worklist} is not a list of trials: it has no column 'nct'")
    log, nothing_found = read_log(root / log_dir), read_nothing_found(root / log_dir)
    trials = {row["nct"]: row for row in listed}
    # A trial leaves its worklist once it is settled. The adjudicators must still be able to come back to it.
    left = sorted({entry.nct for entry in (*log.adjudications, *log.dissents, *nothing_found)} - set(trials))
    registry = _registry(root) if left else {}
    for nct in left:
        trials[nct] = {"nct": nct, "title": registry.get(nct, {}).get("brief_title") or "",
                       "scored_endpoint": registry.get(nct, {}).get("scored_endpoint") or "", "left_the_worklist": "yes"}
    require_nothing_from_the_future([*nothing_found, *(entry for kind in LOG_KINDS for entry in getattr(log, kind))], today)
    return _Study(root, name, today, trials, _adjudicators(root), log, nothing_found, source_states(log, today))


def _require_open(study: _Study) -> None:
    """Nothing is added to a log once figures made from it are fixed: they would no longer be what the log gives."""
    closed_by = SETS[study.set][3]
    if closed_by is not None and (study.root / closed_by).exists():
        raise ValueError(f"the {study.set} log is closed: {study.root / closed_by} was made from it and is fixed")


def _adjudicator(study: _Study, given: str) -> str:
    """The adjudicator's name as the log spells it, if they are one of those the study names."""
    if normalised_name(given) not in study.adjudicators:
        raise ValueError(f"{given!r} is not one of the adjudicators named in {study.root / ADJUDICATORS}: "
                         f"{', '.join(study.adjudicators.values())}")
    return normalised_name(given)


def _form_path(study: _Study, adjudicator: str) -> pathlib.Path:
    return study.working_files / f"form_{_file_name(adjudicator)}.csv"


def _disagreements_path(study: _Study) -> pathlib.Path:
    return study.working_files / "disagreements.csv"


# --- reading a filled file ---------------------------------------------------------------


def _date(text: str) -> dt.date:
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{text!r} is not a date (write it as 2026-03-01; in a spreadsheet, format the column as "
                         f"text first, or it will be rewritten)") from None


def _hazard_ratio(text: str) -> float | None:
    if not text:
        return None
    try:
        hazard_ratio = float(text)
    except ValueError:
        raise ValueError(f"hazard ratio {text!r} is not a number (write it as 0.72)") from None
    low, high = PLAUSIBLE_HAZARD_RATIOS
    if not low <= hazard_ratio <= high:  # also refuses nan and inf
        raise ValueError(f"hazard ratio {text} is not between {low} and {high}: check the decimal point")
    return hazard_ratio


def _one_of(value: str, allowed: Iterable[str], what: str) -> str:
    if value not in allowed:
        raise ValueError(f"{what} must be one of {', '.join(allowed)}" + (f", not {value!r}" if value else ""))
    return value


def _filled(row: dict, cells: Iterable[str]) -> bool:
    return any(row.get(cell) for cell in cells)


def _why(problem: Exception, nct: str) -> str:
    """A record's complaint without the registry number it begins with, which the row already gives."""
    return str(problem).removeprefix(f"{nct}: ")


def _rows(path: pathlib.Path, columns: Iterable[str], what: str) -> list[tuple[int, dict]]:
    """A file's rows with their spreadsheet row numbers. A file missing a column is not what it should be."""
    rows = read_table(path)
    missing = [column for column in columns if rows and column not in rows[0]]
    if missing:
        raise ValueError(f"{path} is not {what}: it has no column {missing[0]!r}")
    return list(enumerate(rows, start=2))


def _made_from(rows: Iterable[tuple[int, dict]], make: Callable[[dict], object]) -> list:
    """What each row makes, leaving out rows that make nothing; or every row's refusal, and nothing made."""
    made, problems = [], []
    for line, row in rows:
        try:
            made.append(make(row))
        except (ValueError, NotBlind) as problem:
            problems.append(f"row {line} ({row['nct']}): {_why(problem, row['nct'])}")
    if problems:
        raise RowsRefused(problems)
    return [entry for entry in made if entry is not None]


def _address_key(source: str) -> str:
    """A source's address without what two people copying the same address most often differ in.

    The scheme, a leading "www.", the case of the host, a trailing slash, and a
    fragment that is a place on the page. It catches slips, not evasions.
    """
    doi = re.match(r"(?:https?://)?(?:www\.|dx\.)?doi\.org/(.+)$|doi:\s*(.+)$|(10\.\d{4,9}/.+)$", source.strip(), flags=re.IGNORECASE)
    if doi:  # a DOI is the same paper however it is written, and in any case
        return "doi:" + next(part for part in doi.groups() if part).split("#")[0].rstrip("/").casefold()
    host, _, rest = re.sub(r"^https?://", "", source.strip(), flags=re.IGNORECASE).partition("/")
    path, _, fragment = rest.partition("#")
    if fragment.startswith(("/", "!")):  # a fragment some sites use as the page's own address
        path = f"{path}#{fragment}"
    return f"{re.sub(r'^www[.]', '', host.casefold())}/{path}".rstrip("/")


def _reading(row: dict, adjudicator: str, study: _Study) -> Adjudication:
    """One row of a form as the reading it records. The outcome is not asked for: it follows from what was read."""
    source_type = _one_of(row["source_type"], SOURCE_TYPES, "source type")
    if not row["source"]:
        raise ValueError("the source's address is needed")
    endpoint_rule = _one_of(row["endpoint_rule"] or "single", ENDPOINT_RULES, "endpoint rule")
    endpoint_results = tuple(part for part in re.split(r"[;,\s]+", row["endpoint_results"]) if part)
    for result in endpoint_results:
        _one_of(result, ENDPOINT_RESULTS, "each endpoint result")
    early_stop = _one_of(row["early_stop"], EARLY_STOPS, "early stop, if not blank,") if row["early_stop"] else None
    if early_stop is not None and endpoint_results:
        raise ValueError("leave endpoint_results blank for an early stop: the stop decides the outcome")
    if early_stop is None and endpoint_rule == "single" and len(endpoint_results) != 1:
        raise ValueError("`single` takes one endpoint result; use any_of or co_primary for several primary endpoints")
    if early_stop is None and endpoint_rule != "single" and len(endpoint_results) < 2:
        raise ValueError(f"{endpoint_rule} needs a result for each primary endpoint, at least two")
    outcome = derive_outcome(endpoint_rule, endpoint_results, early_stop)
    if outcome is None:
        raise ValueError("these endpoint results do not say whether the trial was positive or negative")
    hazard_ratio = _hazard_ratio(row["hazard_ratio"])
    return Adjudication(
        nct=row["nct"], adjudicator=adjudicator, recorded_on=study.today, source_type=source_type,
        source=row["source"], disclosed_on=_date(row["disclosed_on"]), language=row["language"] or "en",
        original_text=row["original_text"], translation=row["translation"] or None, endpoint_rule=endpoint_rule,
        endpoint_results=endpoint_results, early_stop=early_stop, outcome=outcome, hazard_ratio=hazard_ratio,
        hazard_ratio_endpoint=(row["hazard_ratio_endpoint"] or None) if hazard_ratio is not None else None,
    )


def _same_reading(one: Adjudication, other: Adjudication) -> bool:
    return (what_was_read(one), one.original_text, one.translation) == (what_was_read(other), other.original_text, other.translation)


def _given_mark(source_type: str, source: str) -> str:
    return "g-" + hashlib.sha256(f"{source_type}\n{source}".encode()).hexdigest()[:8]


def _typed_rows(study: _Study, rows: Iterable[tuple[int, dict]], path: pathlib.Path) -> dict[SourceKey, dict]:
    """Rows on which the adjudicator typed a source and has not yet read it, by the source they name.

    A row the command filled in carries its mark; once its source is no longer
    cited it is simply dropped. A typed row for a trial that is not on the
    worklist is a slip the adjudicator must put right, not one to drop.
    """
    typed = {}
    for line, row in rows:
        if not row["source"] or _filled(row, (*WHAT_IS_READ, SEARCHED)) or row[AS_GIVEN] == _given_mark(row["source_type"], row["source"]):
            continue
        if row["nct"] not in study.trials:
            raise ValueError(f"{path}: row {line} gives a source for {row['nct']}, which is not on the worklist; "
                             f"correct the registry number or remove the row")
        typed[(row["nct"], row["source_type"], row["source"])] = row
    return typed


Entry = Adjudication | NothingFound | Dissent


def _entries_of_form(study: _Study, adjudicator: str, path: pathlib.Path, revise: bool) -> list[Entry]:
    """The readings, findings of nothing and dissents a form holds that the record does not, if every filled row can be recorded.

    A reading of a source the adjudicator has already read differently replaces
    the earlier one only when they say so; both stay in the log. A row with
    `nothing_found` filled is a finding of nothing if it names no source, and a
    dissent from the other adjudicator's reading if it names one.
    """
    new: dict[SourceKey, Adjudication] = {}
    searched_for: set[str] = set()
    dissented_from: set[SourceKey] = set()

    def without_a_reading(row: dict) -> NothingFound | Dissent | None:
        if _filled(row, WHAT_IS_READ):
            raise ValueError("a row records a reading or that nothing was found, not both")
        if row["source"]:
            dissent = Dissent(row["nct"], adjudicator, _one_of(row["source_type"], SOURCE_TYPES, "source type"), row["source"],
                              row[SEARCHED], study.today)
            key = (dissent.nct, dissent.source_type, dissent.source)
            if key in new:
                raise ValueError("this file also records a reading of this source; it either states the result or does not")
            if adjudicator in study.dissented.get(key, ()) or key in dissented_from:
                return None
            require_dissent_recordable(dissent, study.log, study.today)
            dissented_from.add(key)
            return dissent
        found = NothingFound(row["nct"], adjudicator, row[SEARCHED], study.today)
        if any(key[0] == found.nct for key in new):
            raise ValueError("this file also records a reading for this trial; a trial with a source has not found nothing")
        if adjudicator in study.found_nothing(found.nct) or found.nct in searched_for:
            return None
        require_nothing_found_recordable(found, study.log, study.today)
        searched_for.add(found.nct)
        return found

    def entry(row: dict) -> Entry | None:
        if row["nct"] not in study.trials:
            raise ValueError("not on the worklist")
        if row[SEARCHED]:
            return without_a_reading(row)
        reading = _reading(row, adjudicator, study)
        key = (reading.nct, reading.source_type, reading.source)
        if key in new:
            raise ValueError("the same source is read twice in this file")
        if reading.nct in searched_for:
            raise ValueError("this file also records a search that found nothing for this trial")
        if key in dissented_from:
            raise ValueError("this file also says this source does not state the result; it either does or does not")
        # Every source the log has known for the trial, including one read differently and since withdrawn by both.
        known = (*(k for k in study.sources if k[0] == reading.nct), *(k for k in new if k[0] == reading.nct))
        for (_, source_type, source) in known:
            if _address_key(source) == _address_key(reading.source) and (source_type, source) != key[1:]:
                raise ValueError(f"this looks like the source already cited as {source_type}, {source!r}; "
                                 f"use that source type and address exactly")
        mine = study.sources[key].readings.get(adjudicator) if key in study.sources else None
        if mine is not None and _same_reading(mine, reading):
            return None
        if mine is not None and not revise:
            raise ValueError(f"you have already read this source differently on {mine.recorded_on}; "
                             f"record with --revise to replace that reading")
        require_recordable(reading, study.log.forecast_access, study.today)
        require_fits_the_log(reading, study.log, study.today)
        new[key] = reading
        return reading

    rows = _rows(path, FORM_COLUMNS, "an adjudication form")
    _typed_rows(study, rows, path)
    return _made_from([(line, row) for line, row in rows if _filled(row, (*WHAT_IS_READ, SEARCHED))], entry)


# --- the steps ---------------------------------------------------------------------------


def form(study: _Study, adjudicator: str, reread: Iterable[str] = ()) -> int:
    """Write the adjudicator's form: a row for each source waiting for their reading.

    A source the other adjudicator has cited is given with its type and address
    and nothing else. A trial with no source from anyone gets a blank row, unless
    this adjudicator has already searched and found nothing. A row on which the
    adjudicator typed an address and no reading yet is kept as typed. Trials
    named to be read again get a row for each source the adjudicator has read or
    dissented from, or a blank row. A form that holds rows not yet recorded is
    never written over.
    """
    path, typed = _form_path(study, adjudicator), {}
    if path.exists():
        rows = _rows(path, FORM_COLUMNS, "an adjudication form")
        try:
            unrecorded = len(_entries_of_form(study, adjudicator, path, revise=True))
        except RowsRefused:
            unrecorded = sum(_filled(row, (*WHAT_IS_READ, SEARCHED)) for _, row in rows)
        if unrecorded:
            raise ValueError(f"{path} holds {counted(unrecorded, 'row')} not yet recorded; run record, or delete the file")
        typed = _typed_rows(study, rows, path)
    strangers = [nct for nct in reread if nct not in study.trials]
    if strangers:
        raise ValueError(f"not on the worklist: {', '.join(strangers)}")
    registry = _registry(study.root)
    dissented_by_me = {key for key, who in study.dissented.items() if adjudicator in who}
    rows = []
    for nct, trial in study.trials.items():
        cited = study.read_by(nct)
        mine = [key for key, state in cited.items() if adjudicator in state.readings]
        given = sorted((key for key, state in cited.items() if adjudicator not in state.readings and key not in dissented_by_me),
                       key=lambda key: (SOURCE_TYPES.index(key[1]), key[2]))
        if nct in reread:
            given += [*mine, *(key for key in dissented_by_me if key[0] == nct)]
        to_read = given + [key for key in typed if key[0] == nct and key not in (*given, *mine)]
        if not to_read and (nct in reread or (not cited and adjudicator not in study.found_nothing(nct)
                                               and "left_the_worklist" not in trial)):
            to_read = [(nct, "", "")]
        for key in to_read:
            as_typed = typed.get(key, {}) if key not in given else {}
            rows.append((nct, trial.get("title"), trial.get("scored_endpoint"), registry.get(nct, {}).get("primary_outcomes"),
                         key[1], key[2], "", as_typed.get("language") or "en", "", "", as_typed.get("endpoint_rule") or "single",
                         "", "", "", as_typed.get("hazard_ratio_endpoint") or trial.get("scored_endpoint"), "",
                         _given_mark(key[1], key[2]) if key in given else ""))
    write_table(path, FORM_COLUMNS, rows)
    print(f"{counted(len(rows), 'row')} for {study.named(adjudicator)} in {path}")
    return 0


def record(study: _Study, adjudicator: str, revise: bool) -> int:
    """Record every filled row of the adjudicator's form, each as what it is and made today, or none of them."""
    path = _form_path(study, adjudicator)
    if not path.exists():
        raise ValueError(f"there is no form at {path}; run form first")
    entries = _entries_of_form(study, adjudicator, path, revise)
    made = {kind: [entry for entry in entries if isinstance(entry, kind)] for kind in (Adjudication, NothingFound, Dissent)}
    for reading in made[Adjudication]:
        record_adjudication(study.log_file("adjudications"), reading, study.log, study.today)
    for finding in made[NothingFound]:
        record_nothing_found(study.log_dir / NOTHING_FOUND, finding, study.log, study.today)
    for dissent in made[Dissent]:
        record_dissent(study.log_file("dissents"), dissent, study.log, study.today)
    others = [counted(len(made[NothingFound]), "finding") + " of nothing"] * bool(made[NothingFound]) \
        + [counted(len(made[Dissent]), "dissent")] * bool(made[Dissent])
    print(" and ".join([", ".join([counted(len(made[Adjudication]), "reading"), *others[:-1]]), *others[-1:]])
          + f" recorded for {study.named(adjudicator)}")
    return form(_load(study.root, study.set, study.today), adjudicator)


def _in_disagreement(study: _Study) -> dict[SourceKey, SourceState]:
    """Sources both adjudicators have read, differently, and not reconciled."""
    return {key: state for key, state in study.sources.items()
            if state.disputed and state.reconciliation is None and len(state.readings) == 2}


def _with_a_source_still_to_read(study: _Study) -> set[str]:
    """Trials with a source one adjudicator has read and the other has neither read nor dissented from.

    Nothing the two differ on in such a trial is shown to either of them yet:
    one of them still has a reading to make without knowing the other's.
    """
    return {key[0] for key, state in study.sources.items() if len(state.readings) == 1 and not state.dissents}


def _laid_open(study: _Study) -> tuple[dict[SourceKey, SourceState], dict[SourceKey, tuple[str, ...]]]:
    """What the two may now look at together: sources both read, differently, and sources one read and the other dissents from."""
    waiting = _with_a_source_still_to_read(study)
    return ({key: state for key, state in _in_disagreement(study).items() if key[0] not in waiting},
            {key: who for key, who in study.dissented.items() if key[0] not in waiting})


def _where_it_stands(study: _Study, nct: str, settled: dict, waiting: dict, nothing: dict) -> str:
    if nct in settled:
        return "settled"
    if nct in nothing:
        return "no result found"
    if waiting.get(nct) == NOT_BLIND:
        return "read by someone who had opened the forecasts"
    if any(key[0] == nct for differing in _laid_open(study) for key in differing):
        return "read differently"
    if study.read_by(nct) or study.found_nothing(nct):
        return "awaiting the second adjudicator"
    return "not yet read"


def status(study: _Study) -> int:
    """Say where each trial stands, and how many stand where."""
    settled, waiting = results(study.log, study.today), awaiting_result(study.log, study.today)
    nothing = no_result_found(study.nothing_found, study.log, study.today)
    stands = {nct: _where_it_stands(study, nct, settled, waiting, nothing) for nct in study.trials}
    for nct, where in stands.items():
        print(f"{nct}  {where}" + ("  (no longer on the worklist)" if "left_the_worklist" in study.trials[nct] else ""))
    counts = list(stands.values())
    line = (f"{counted(len(stands), 'trial')}: {counts.count('settled')} settled, {counts.count('no result found')} with no "
            f"result found, {counts.count('awaiting the second adjudicator')} awaiting the second adjudicator, "
            f"{counts.count('read differently')} read differently, {counts.count('not yet read')} not yet read")
    not_blind = counts.count("read by someone who had opened the forecasts")
    print(line + (f", {not_blind} read by someone who had opened the forecasts" if not_blind else ""))
    return 0


def _cells(reading: Adjudication) -> tuple[str, ...]:
    """One adjudicator's reading as the cells of the list of disagreements."""
    return tuple("" if value is None else str(value) for value in (
        reading.adjudicator, reading.outcome, reading.disclosed_on, reading.hazard_ratio, reading.hazard_ratio_endpoint,
        reading.endpoint_rule, "; ".join(reading.endpoint_results), reading.early_stop, reading.language,
        reading.original_text, reading.translation))


def _as_listed(state: SourceState) -> str:
    """A mark of the two readings in force, which a spreadsheet will leave alone where it would rewrite a date or a number."""
    both = repr([_cells(reading) for _, reading in sorted(state.readings.items())])
    return "r-" + hashlib.sha256(both.encode()).hexdigest()[:12]


def _reconcilable(state: SourceState | None) -> bool:
    return state is not None and state.disputed and len(state.readings) == 2


def _settlement(row: dict, adjudicators: Iterable[str], recorded_on: dt.date) -> Reconciliation:
    """A row of the list of disagreements as the reconciliation its settled cells make."""
    hazard_ratio = _hazard_ratio(row["settled_hazard_ratio"])
    if hazard_ratio is None and row["settled_hazard_ratio_endpoint"]:
        raise ValueError("an endpoint is named for a hazard ratio that is left blank; give the number, or clear the "
                         "endpoint if the source gives no hazard ratio")
    return Reconciliation(
        nct=row["nct"], source_type=row["source_type"], source=row["source"],
        outcome=_one_of(row["settled_outcome"].casefold(), OUTCOMES, "the settled outcome"), hazard_ratio=hazard_ratio,
        hazard_ratio_endpoint=row["settled_hazard_ratio_endpoint"] or None,
        disclosed_on=_date(row["settled_disclosed_on"]), reason=row["reason"], adjudicators=tuple(adjudicators),
        recorded_on=recorded_on, language=row["settled_language"] or None,
    )


def _is_what_was_recorded(row: dict, recorded: Reconciliation | None) -> bool:
    """Whether a row's settled cells are the reconciliation the log already holds for its source."""
    try:
        return recorded is not None and _settlement(row, recorded.adjudicators, recorded.recorded_on) == recorded
    except ValueError:
        return False


def disagreements(study: _Study, reopen: Iterable[str] = ()) -> int:
    """Lay the two readings of every source read differently side by side, with cells for what the pair settle on.

    A trial with a source that one of them has still to read is held back: its
    readings are not shown to either until both have read everything cited. A
    source that one read and the other dissents from cannot be reconciled,
    having one reading; it is named, for the two to resolve. A settlement
    typed and not yet recorded is kept if the readings it was typed against
    still stand, and dropped, with a word to say so, if they have changed. Trials named to be
    reopened have their reconciled sources listed again, to put a slip right.
    """
    path, (read_differently, dissented) = _disagreements_path(study), _laid_open(study)
    listed = {**read_differently, **{key: state for key, state in study.sources.items()
                                     if key[0] in reopen and state.reconciliation is not None and _reconcilable(state)}}
    typed, dropped = {}, []
    if path.exists():
        for _, row in _rows(path, DISAGREEMENT_COLUMNS, "a list of disagreements"):
            key = (row["nct"], row["source_type"], row["source"])
            state = study.sources.get(key)
            if not _filled(row, SETTLED) or (key not in listed and _is_what_was_recorded(row, state and state.reconciliation)):
                continue  # nothing typed, or typed and since recorded just so
            if _reconcilable(state) and row[AS_LISTED] == _as_listed(state):
                typed[key] = [row[cell] for cell in SETTLED]
                listed.setdefault(key, state)  # shown to them before; kept though its trial has since gained a source
            else:
                dropped.append(f"{key[0]} ({key[2]})")
    rows = [(nct, study.trials.get(nct, {}).get("title"), study.trials.get(nct, {}).get("scored_endpoint"), source_type,
             source, *(cell for _, reading in sorted(state.readings.items()) for cell in _cells(reading)), _as_listed(state),
             *typed.get((nct, source_type, source), [""] * len(SETTLED)))
            for (nct, source_type, source), state in sorted(listed.items())]
    write_table(path, DISAGREEMENT_COLUMNS, rows)
    held_back = len(_in_disagreement(study).keys() - listed.keys())
    print(f"{counted(len(rows), 'source')} read differently, listed in {path}"
          + (f"; {held_back} more wait until both have read every source of their trial" if held_back else ""))
    if dropped:
        print(f"{counted(len(dropped), 'settlement')} typed in the old list no longer fit the readings and were dropped: "
              f"{', '.join(dropped)}")
    for (nct, source_type, source), who in sorted(dissented.items()):
        reader = " and ".join(study.named(name) for name in sorted(study.sources[(nct, source_type, source)].readings))
        print(f"{nct}: {reader} read {source}; {' and '.join(study.named(name) for name in who)} finds it does not state "
              f"the result. Either the reading is withdrawn, or the source is read by both and reconciled.")
    return 0


def reconcile(study: _Study, adjudicators: list[str], revise: bool) -> int:
    """Record what the two adjudicators settled for each source they read differently, with their reason, or nothing.

    A source already reconciled is settled again only when they say so, to put
    a slip right; both reconciliations stay in the log and the later one stands.
    """
    if len(set(adjudicators)) != 2:
        raise ValueError("a reconciliation is recorded by both adjudicators: give --by twice, once for each")
    path = _disagreements_path(study)
    if not path.exists():
        raise ValueError(f"there is no list of disagreements at {path}; run disagreements first")
    log, seen = study.log, set()

    def reconciliation(row: dict) -> Reconciliation | None:
        nonlocal log
        key = (row["nct"], row["source_type"], row["source"])
        settled = _settlement(row, adjudicators, study.today)
        if key in seen:
            raise ValueError("the same source is settled twice in this file")
        seen.add(key)
        state = study.sources.get(key)
        recorded = state.reconciliation if state is not None else None
        if recorded is not None and dataclasses.replace(recorded, recorded_on=study.today) == settled:
            return None  # recorded by an earlier run of this file
        if not _reconcilable(state):
            raise ValueError("this source is not one the two adjudicators have both read, and read differently")
        if recorded is not None and not revise:
            raise ValueError(f"this source was reconciled on {recorded.recorded_on}; reconcile with --revise to replace that")
        if set(adjudicators) != set(state.readings):
            raise ValueError(f"it is settled by the two who read it, {' and '.join(sorted(state.readings))}")
        if row[AS_LISTED] != _as_listed(state):
            raise ValueError("the readings have changed since this list was written; run disagreements again")
        require_reconcilable(settled, log, study.today)
        log = log.with_reconciliation(settled)
        return settled

    settled = _made_from([(line, row) for line, row in _rows(path, DISAGREEMENT_COLUMNS, "a list of disagreements")
                          if _filled(row, SETTLED)], reconciliation)
    log = study.log
    for each in settled:
        record_reconciliation(study.log_file("reconciliations"), each, log, study.today)
        log = log.with_reconciliation(each)
    print(f"{counted(len(settled), 'reconciliation')} recorded")
    return 0


def withdraw(study: _Study, adjudicator: str, nct: str, source: str, source_type: str, reason: str) -> int:
    """Take back the adjudicator's reading of a source, for example one that is about another trial."""
    held = [key[1] for key, state in study.read_by(nct).items()
            if key[2] == source and adjudicator in state.readings and source_type in ("", key[1])]
    if len(held) > 1:
        raise ValueError(f"{nct}: you have read {source!r} as {' and as '.join(held)}; say which with --source-type")
    # With no reading held, the rule itself says so.
    withdrawal = Withdrawal(nct, adjudicator, held[0] if held else source_type or SOURCE_TYPES[0], source, reason, study.today)
    record_withdrawal(study.log_file("withdrawals"), withdrawal, study.log, study.today)
    print(f"{study.named(adjudicator)}'s reading of {source} for {nct} is withdrawn")
    return 0


def main(arguments: list[str] | None = None, today: dt.date | None = None) -> int:
    """Run one step of adjudication: `trialseal-adjudicate form|record|status|disagreements|reconcile|withdraw`."""
    parser = argparse.ArgumentParser(prog="trialseal-adjudicate", description=__doc__.split("\n\n")[0])
    parser.add_argument("step", choices=("form", "record", "status", "disagreements", "reconcile", "withdraw"))
    parser.add_argument("--set", required=True, choices=tuple(SETS), help="which trials are being adjudicated")
    parser.add_argument("--by", action="append", default=[], help="the adjudicator's name; twice for reconcile")
    parser.add_argument("--reread", action="append", default=[], metavar="NCT",
                        help="for form: also give a row for each source you have already read for this trial; "
                             "for disagreements: also list this trial's reconciled sources")
    parser.add_argument("--revise", action="store_true",
                        help="for record: replace a reading of yours that the form reads differently; "
                             "for reconcile: replace a reconciliation already recorded")
    parser.add_argument("--trial", default="", metavar="NCT", help="for withdraw: the trial's registry number")
    parser.add_argument("--source", default="", help="for withdraw: the address of the source")
    parser.add_argument("--source-type", default="", choices=("", *SOURCE_TYPES),
                        help="for withdraw: the source's type, if you read one address under two")
    parser.add_argument("--reason", default="", help="for withdraw: why the reading is taken back")
    parser.add_argument("--study", default=".", help="the study directory (default: the current directory)")
    options = parser.parse_args(arguments)
    root, today = pathlib.Path(options.study), today or dt.date.today()
    try:
        study = _load(root, options.set, today)
        if options.step == "status":
            return status(study)
        if options.step == "disagreements":
            return disagreements(study, options.reread)
        by = [_adjudicator(study, name) for name in options.by]
        if options.step != "form":
            _require_open(study)
        if options.step == "reconcile":
            return reconcile(study, by, options.revise)
        if len(by) != 1:
            parser.error(f"{options.step} needs --by with one adjudicator's name")
        if options.step == "form":
            return form(study, by[0], options.reread)
        if options.step == "record":
            return record(study, by[0], options.revise)
        if not (options.trial and options.source):
            parser.error("withdraw needs --trial and --source")
        return withdraw(study, by[0], options.trial, options.source, options.source_type, options.reason)
    except RowsRefused as refused:
        print("NOT RECORDED:\n  " + "\n  ".join(refused.problems))
        return 1
    except (ValueError, TypeError, OSError, NotBlind) as problem:
        # A file that cannot be read as what it should be, or an entry the rules refuse: say so, and change nothing.
        print(f"NOT DONE: {problem}")
        return 1
