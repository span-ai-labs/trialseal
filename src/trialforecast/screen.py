"""The screening command: `trialseal-screening`.

It keeps the screening log of a study directory and reports where every candidate stands:

    <study>/snapshots/<latest>/                 the registry snapshot the candidates come from
    <study>/screening/screening.jsonl           the screening log
    <study>/screening/design_reviews.jsonl      rulings on designs that may rule a candidate out
    <study>/screening/worklist.csv              what `worklist` writes for a searcher
    <study>/results/screening/                  what `summary` writes

`worklist` lists the candidates that need a search, with every name a readout may
be announced under. `import` takes a searcher's findings into the log, all or
none. `registry` and `import-trace` record what the registry and a readout trace
already show. `summary` reports where each candidate stands and writes the queues
for the study lead, who marks them and gives them back with `confirm` and `design`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
from typing import Iterable

from trialforecast import records, traces, universe
from trialforecast.dates import add_months
from trialforecast.screening import (
    AWAITING_CONFIRMATION, ELIGIBLE, VOID, EXCLUDE, HIGH, INCLUDE, LOW, MEDIUM, NOT_SCREENED, READ_OUT,
    SCREENING_VALID_DAYS, DesignReview, ScreeningRecord, confirmed, screening_status, screening_summary,
)
from trialforecast.studyfiles import (
    DESIGN_REVIEWS, SCREENING_LOG, TRACES, latest_snapshot, read_records, read_table, registry_records, write_table,
)
from trialforecast.wording import counted

DESIGN_PROPOSALS = pathlib.Path("screening") / "design_review_proposals.csv"
# The registry completion date only bounds the search (ADR-0003): candidates dated within this many months
# either side of today are searched. The study runs for up to 24 months, and a readout can trail its date by as long.
SEARCH_MONTHS_EITHER_SIDE = 24
REGISTRY, TRACE = "registry record", "readout trace"
WORKLIST_COLUMNS = ("nct", "acronym", "title_names", "sponsor_study_id", "other_ids", "intervention_names",
                    "investigational_drug", "lead_sponsor", "collaborators", "brief_title", "conditions", "status",
                    "primary_completion_date", "primary_outcomes", "exclusion_review")
QUEUE_COLUMNS = ("nct", "decision", "confidence", "screened_on", "readout_date", "evidence", "evidence_links", "confirm", "note")
TRIAL_COLUMNS = ("nct", "acronym", "brief_title", "lead_sponsor", "sponsor_type", "primary_completion_date",
                 "scored_endpoint", "reference_class", "investigational_drug")


def _candidates(root: pathlib.Path, today: dt.date) -> list[dict]:
    """Every candidate in the latest registry snapshot."""
    table, _ = universe.load_snapshot(latest_snapshot(root))
    ncts = set(universe.refine(table, today)["nct"])
    return [record for nct, record in registry_records(latest_snapshot(root)).items() if nct in ncts]


def _log(root: pathlib.Path) -> list[ScreeningRecord]:
    return read_records(root / SCREENING_LOG, ScreeningRecord)


def _in_search_window(candidate: dict, today: dt.date) -> bool:
    registry_date = universe.parse_date(candidate.get("primary_completion_date"))
    return registry_date is not None and add_months(today, -SEARCH_MONTHS_EITHER_SIDE) <= registry_date <= add_months(
        today, SEARCH_MONTHS_EITHER_SIDE)


def _add(root: pathlib.Path, new: Iterable[ScreeningRecord]) -> int:
    """Append records the log does not already hold, and say how many were new."""
    held = set(_log(root))
    added = [record for record in dict.fromkeys(new) if record not in held]
    for record in added:
        records.append(root / SCREENING_LOG, record)
    return len(added)


# --- the steps -------------------------------------------------------------------------------


def worklist(root: pathlib.Path, today: dt.date) -> int:
    """Candidates in the search window with no standing decision for today, soonest registry date first."""
    status, candidates = screening_status(_log(root), today), _candidates(root, today)
    in_window = [c for c in candidates if _in_search_window(c, today)]
    to_search = [c for c in in_window if status.get(c["nct"], NOT_SCREENED) in (NOT_SCREENED, AWAITING_CONFIRMATION)]
    rows = []
    for candidate in sorted(to_search, key=lambda c: (c["primary_completion_date"], c["nct"])):
        names = json.loads(candidate["aliases"])
        joined = {key: "; ".join(value) if isinstance(value, list) else value for key, value in names.items()}
        rows.append([{**candidate, **joined}.get(column) for column in WORKLIST_COLUMNS])
    write_table(root / "screening" / "worklist.csv", WORKLIST_COLUMNS, rows)
    print(f"{counted(len(rows), 'candidate')} to search, listed in {root / 'screening' / 'worklist.csv'}; "
          f"{len(candidates) - len(in_window)} more have a registry completion date outside the "
          f"{SEARCH_MONTHS_EITHER_SIDE} months either side of today that are searched")
    return 0


def _finding(row: dict, screened_on: dt.date, screened_by: str) -> ScreeningRecord:
    return ScreeningRecord(
        nct=row["nct"], decision=row["decision"], screened_on=screened_on, evidence=row.get("evidence", ""),
        confidence=row.get("confidence", ""), evidence_links=tuple((row.get("evidence_links") or "").replace(";", " ").split()),
        screened_by=screened_by, readout_date=dt.date.fromisoformat(row["readout_date"]) if row.get("readout_date") else None,
        # A searcher writes the drug as they found it; it is held in its one spelling.
        investigational_drug=universe.drug_name(row["investigational_drug"]) if row.get("investigational_drug") else None,
    )


def import_findings(root: pathlib.Path, today: dt.date, findings: pathlib.Path, screened_by: str, screened_on: dt.date | None) -> int:
    """Take a searcher's findings into the log. One row that cannot be a record refuses the whole file.

    A finding is for a candidate in the latest snapshot, or for a trial screening
    already knows: a sealed trial is screened again even after the snapshot has moved on.
    """
    known = {c["nct"] for c in _candidates(root, today)} | {r.nct for r in _log(root)}
    searched_on = screened_on or today
    taken, refused = [], []
    for row in read_table(findings):
        try:
            if row["nct"] not in known:
                raise ValueError("not a candidate in the snapshot, nor a trial screened before")
            taken.append(_finding(row, searched_on, screened_by))
        except (ValueError, KeyError) as problem:
            refused.append(f"{row.get('nct', '?')}: {problem}")
    if not screened_by.strip():
        refused.append("say who or what searched, with --screened-by")
    if not 0 <= (today - searched_on).days <= SCREENING_VALID_DAYS:
        refused.append(f"a search dated {searched_on} cannot be entered on {today}: it is entered within "
                       f"{SCREENING_VALID_DAYS} days of being made, and never before")
    if refused:
        print("NOT IMPORTED: " + "; ".join(refused))
        return 1
    print(f"{counted(_add(root, taken), 'screening record')} added from {findings}")
    return 0


def from_registry(root: pathlib.Path, today: dt.date) -> int:
    """Results posted on the registry are a public primary result: record each such candidate as read out, once."""
    already = {r.nct for r in _log(root) if r.screened_by == REGISTRY}
    found = []
    for candidate in _candidates(root, today):
        posted = universe.parse_date(candidate.get("results_first_posted"))
        if candidate.get("has_results") and posted is not None and candidate["nct"] not in already:
            found.append(ScreeningRecord(
                nct=candidate["nct"], decision=READ_OUT, screened_on=today, confidence=HIGH,
                evidence=f"the registry record shows results first posted on {posted}; an earlier disclosure is likely",
                evidence_links=(f"https://clinicaltrials.gov/study/{candidate['nct']}",), screened_by=REGISTRY,
                readout_date=posted))
    print(f"{counted(_add(root, found), 'screening record')} added from the registry")
    return 0


def _from_trace(row: traces.TracedRow, screened_on: dt.date) -> ScreeningRecord:
    """The screening record a traced row implies.

    A result found is a readout at the trace's own confidence. A trace in doubt is
    a possible readout of low confidence, for the study lead to rule on, never a
    clearance. A trial void is recorded as that, and one with
    nothing found as eligible on the day it was traced.
    """
    common = dict(nct=row.nct, screened_on=screened_on, confidence=row.confidence, screened_by=TRACE,
                  evidence=row.notes or f"traced in {row.traced_in}")
    if row.found in (*traces.CLEAR, traces.IN_DOUBT):
        doubtful = row.found == traces.IN_DOUBT
        return ScreeningRecord(**{**common, "confidence": LOW if doubtful else row.confidence}, decision=READ_OUT,
                               readout_date=row.readout_date or screened_on,
                               evidence_links=(row.source or f"https://clinicaltrials.gov/study/{row.nct}",))
    return ScreeningRecord(**common, decision=VOID if row.found == traces.VOID else ELIGIBLE)


def import_trace(root: pathlib.Path, today: dt.date, trace_files: list[pathlib.Path], screened_on: dt.date) -> int:
    """Give each traced candidate the screening record its trace implies, dated the day it was traced."""
    if screened_on > today:
        print(f"NOT IMPORTED: a trace cannot have been made on {screened_on}, after today")
        return 1
    known = {c["nct"] for c in _candidates(root, today)}
    implied = [_from_trace(row, screened_on) for row in traces.read_traces(trace_files) if row.nct in known]
    print(f"{counted(_add(root, implied), 'screening record')} added from {counted(len(trace_files), 'trace file')}")
    return 0


def _row_of(record: ScreeningRecord) -> tuple:
    """A queued decision as its row in the queue file, by which the study lead's mark finds it again."""
    return (record.nct, record.decision, record.confidence, record.screened_on.isoformat(),
            record.readout_date.isoformat() if record.readout_date else "", record.evidence)


def confirm(root: pathlib.Path, today: dt.date, queue: pathlib.Path, by: str) -> int:
    """Take the study lead's marks on the queue.

    "yes" confirms the decision on that row. "no" on a report that a trial read
    out or is void overrules it: the lead has looked, and records with a note
    that the trial is eligible. Each marked row must be exactly a decision still
    waiting in the log, so nothing is confirmed that the lead did not see; and a
    trial is overruled only if every report waiting for it was marked, so that a
    newer report the lead has not seen is not swept away with an older one.
    """
    waiting = {_row_of(r): r for r in screening_summary(
        _candidates(root, today), _log(root), read_records(root / DESIGN_REVIEWS, DesignReview), today)["queue"]}
    marked, rulings, refused, left = {}, [], [], 0
    for row in read_table(queue):
        mark = row.get("confirm", "").casefold()
        if mark not in ("yes", "no"):
            continue
        record = waiting.get(tuple(row.get(column, "") for column in ("nct", "decision", "confidence", "screened_on", "readout_date", "evidence")))
        if record is None:
            refused.append(f"{row.get('nct', '?')}: the row is not a decision waiting in the log as it now stands")
            continue
        marked[_row_of(record)] = mark
        if mark == "yes":
            rulings.append(confirmed(record, by, today))
        elif record.decision == ELIGIBLE:
            left += 1  # a finding of nothing that the lead will not confirm simply goes on waiting
        elif not row.get("note"):
            refused.append(f"{record.nct}: overruling a report needs a note of what the study lead found")
        else:
            rulings.append(ScreeningRecord(
                nct=record.nct, decision=ELIGIBLE, screened_on=today, confidence=MEDIUM, screened_by=by,
                confirmed_by=by, confirmed_on=today,
                evidence=f"the report of {record.screened_on} that the trial had {record.decision.replace('_', ' ')} was looked "
                         f"at and overruled: {row['note']}"))
    overruled = {key[0] for key, mark in marked.items() if mark == "no" and key[1] != ELIGIBLE}
    unseen = sorted({key[0] for key in waiting if key[0] in overruled and key[1] != ELIGIBLE and key not in marked})
    refused += [f"{nct}: another report is waiting for this trial that the marked queue does not rule on" for nct in unseen]
    if refused:
        print("NOT CONFIRMED: " + "; ".join(refused))
        return 1
    print(f"{counted(_add(root, rulings), 'decision')} ruled on by {by}"
          + (f"; {counted(left, 'finding')} of nothing marked \"no\" left waiting" if left else ""))
    return 0


def design(root: pathlib.Path, today: dt.date, rulings: pathlib.Path, by: str) -> int:
    """Take the study lead's rulings on designs: each row with a decision and a reason becomes a design review."""
    known = {c["nct"] for c in _candidates(root, today)}
    try:
        reviews = [DesignReview(row["nct"], row["decision"], row.get("reason", ""), by, today)
                   for row in read_table(rulings) if row.get("decision")]
        strangers = [review.nct for review in reviews if review.nct not in known]
        if strangers:
            raise ValueError(f"not candidates in the snapshot: {', '.join(strangers)}")
    except (ValueError, KeyError) as problem:
        print(f"NOT RECORDED: {problem}")
        return 1
    for review in reviews:
        records.append(root / DESIGN_REVIEWS, review)
    print(f"{counted(len(reviews), 'design ruling')} recorded by {by}")
    return 0


def summary(root: pathlib.Path, today: dt.date) -> int:
    """Report where every candidate stands today, and write the lists and the queues."""
    candidates = _candidates(root, today)
    found = screening_summary(candidates, _log(root), read_records(root / DESIGN_REVIEWS, DesignReview), today)
    counts = ", ".join(f"{name.replace('_', ' ')} {n}" for name, n in found["counts"].items())
    print(f"{counted(len(candidates), 'candidate')}: {counts}")
    out = root / "results" / "screening"
    write_table(out / "eligible.csv", TRIAL_COLUMNS, [[c.get(column) for column in TRIAL_COLUMNS] for c in found["eligible"]])
    # A readout that screening found and no trace covers is one the reference set has still to trace.
    traced = {row.nct for row in traces.read_traces(sorted((root / TRACES).glob("trace_*.csv")))}
    write_table(out / "read_out.csv", ("nct", "readout_date", "source", "confidence", "screened_by", "traced"),
                [(r.nct, r.readout_date, r.evidence_links[0], r.confidence, r.screened_by, "yes" if r.nct in traced else "no")
                 for r in found["read_out"]])
    write_table(out / "excluded.csv", ("nct", "reason", "reviewed_by", "reviewed_on"),
                [(r.nct, r.reason, r.reviewed_by, r.reviewed_on) for r in found["excluded"]])
    write_table(out / "queue.csv", QUEUE_COLUMNS,
                [(r.nct, r.decision, r.confidence, r.screened_on, r.readout_date, r.evidence, " ".join(r.evidence_links), "", "")
                 for r in found["queue"]])
    # A proposal made by a reader of the registry record is shown beside each queued design. It is never a ruling:
    # the study lead writes the decision and the reason.
    proposals = {row["nct"]: row for row in read_table(root / DESIGN_PROPOSALS)} if (root / DESIGN_PROPOSALS).exists() else {}
    proposed = ("proposed_decision", "proposed_reason", "quote")
    write_table(out / "design_queue.csv", ("nct", "brief_title", "exclusion_review", "primary_outcomes", *proposed, "decision", "reason"),
                [(c["nct"], c.get("brief_title"), c.get("exclusion_review"), c.get("primary_outcomes"),
                  *(proposals.get(c["nct"], {}).get(column, "") for column in proposed), "", "") for c in found["design_queue"]])
    lines = ["# Screening summary", "", f"As of {today}: {counted(len(candidates), 'candidate')} in the latest registry snapshot.", "",
             "| Where the candidate stands | Candidates |", "|---|---|",
             *(f"| {name.replace('_', ' ').capitalize()} | {n} |" for name, n in found["counts"].items()), "",
             f"{counted(len(found['queue']), 'decision')} and {counted(len(found['design_queue']), 'design')} wait for the study lead.", "",
             f"A screening clears a trial for a batch only if it is no more than {SCREENING_VALID_DAYS} days old on the day of "
             f"the batch, so the count of eligible trials is as of today.", ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


def main(arguments: list[str] | None = None, today: dt.date | None = None) -> int:
    """Run one step of screening: `trialseal-screening worklist|import|registry|import-trace|confirm|design|summary`."""
    parser = argparse.ArgumentParser(prog="trialseal-screening", description=__doc__.split("\n\n")[0])
    parser.add_argument("step", choices=("worklist", "import", "registry", "import-trace", "confirm", "design", "summary"))
    parser.add_argument("files", nargs="*", type=pathlib.Path, help="the findings, trace files, or marked queue to take in")
    parser.add_argument("--study", default=".", help="the study directory (default: the current directory)")
    parser.add_argument("--screened-by", default="", help="for import: who or what searched")
    parser.add_argument("--screened-on", type=dt.date.fromisoformat,
                        help="the day the search or the trace was made (import: default today)")
    parser.add_argument("--by", default="", help="for confirm and design: the person ruling")
    options = parser.parse_args(arguments)
    root, today = pathlib.Path(options.study), today or dt.date.today()
    one_file = options.files[0] if len(options.files) == 1 else None
    try:
        if options.step == "worklist":
            return worklist(root, today)
        if options.step == "registry":
            return from_registry(root, today)
        if options.step == "summary":
            return summary(root, today)
        if options.step == "import-trace" and options.files and options.screened_on:
            return import_trace(root, today, options.files, options.screened_on)
        if options.step == "import" and one_file:
            return import_findings(root, today, one_file, options.screened_by, options.screened_on)
        if options.step in ("confirm", "design") and one_file and options.by.strip():
            return (confirm if options.step == "confirm" else design)(root, today, one_file, options.by.strip())
    except (ValueError, KeyError, TypeError, OSError) as problem:
        # A file that cannot be read as what it should be: say so, and change nothing.
        print(f"NOT DONE: {problem}")
        return 1
    parser.error(f"{options.step} needs its file" + {"import-trace": "s and --screened-on", "confirm": " and --by",
                                                      "design": " and --by"}.get(options.step, ""))
