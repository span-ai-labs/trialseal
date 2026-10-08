"""Readout traces: one reader's finding, for each past trial, of whether and when it read out and what it showed.

Every module that uses a trace reads it here, so that a traced row means one thing.
"""
from __future__ import annotations

import datetime as dt
import pathlib
from dataclasses import dataclass
from typing import Iterable

from trialforecast.adjudication import HAZARD_RATIO_WINDOW_MONTHS
from trialforecast.dates import add_months
from trialforecast.studyfiles import read_table

POSITIVE, NEGATIVE, VOID, UNRESOLVED, IN_DOUBT = "positive", "negative", "void", "unresolved", "in_doubt"
CLEAR = (POSITIVE, NEGATIVE)
HIGH, MEDIUM, LOW = "high", "medium", "low"
_READ_AS = {"met": POSITIVE, "stopped_efficacy": POSITIVE, "not_met": NEGATIVE, "stopped_futility": NEGATIVE}


@dataclass(frozen=True)
class TracedRow:
    """One trial as one reader traced it."""

    nct: str
    found: str  # positive, negative, void, unresolved, or in doubt
    readout_date: dt.date | None  # the first disclosure the reader could open, where one was found
    hazard_ratio: float | None  # the first public for the traced endpoint, if within six months of the readout
    endpoint: str  # the primary endpoint the result is for, as the reader named it
    confidence: str
    source: str  # the first source's address
    notes: str
    traced_in: str  # the trace file's name


def _date(text: str, what: str, nct: str) -> dt.date | None:
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError as unreadable:
        raise ValueError(f"{nct}: {what} {text!r} is not a date given to the day") from unreadable


def _traced(row: dict, traced_in: str) -> TracedRow:
    """What a traced row is taken to say.

    A result counts as positive or negative only where the reader said the primary
    analysis was disclosed and gave the date. A trial ended without a primary
    analysis is void; one with no disclosure and no result is unresolved; anything
    else is in doubt. A hazard ratio is kept only if it became public on or after
    the readout and within six months of it (ADR-0011). A confidence that is not
    plainly high or medium is low.
    """
    nct, result = row["nct"], row.get("primary_result", "")
    disclosed, readout = row.get("disclosed", ""), _date(row.get("first_disclosure_date", ""), "the disclosure date", row["nct"])
    if result == "terminated_no_analysis":
        found = VOID
    elif disclosed == "no" and not result:
        found = UNRESOLVED
    elif disclosed == "yes" and result in _READ_AS and readout is not None:
        found = _READ_AS[result]
    else:
        found = IN_DOUBT
    hazard_ratio, public_on = None, _date(row.get("hr_first_public_date", ""), "the hazard ratio's date", nct)
    if found in CLEAR and row.get("hr_value") and public_on is not None:
        try:
            value = float(row["hr_value"])
        except ValueError as unreadable:
            raise ValueError(f"{nct}: hazard ratio {row['hr_value']!r} is not a number") from unreadable
        if value <= 0:
            raise ValueError(f"{nct}: hazard ratio {value} must be positive")
        if readout <= public_on <= add_months(readout, HAZARD_RATIO_WINDOW_MONTHS):
            hazard_ratio = value
    confidence = row.get("confidence", "").casefold()
    return TracedRow(nct, found, readout if found in (*CLEAR, IN_DOUBT) else None, hazard_ratio, row.get("which_endpoint", ""),
                     confidence if confidence in (HIGH, MEDIUM) else LOW, row.get("first_source_url", ""),
                     row.get("search_notes", ""), traced_in)


def read_traces(trace_files: Iterable[pathlib.Path]) -> list[TracedRow]:
    """Every traced trial, in registry-number order. A trial traced in two files is refused: one of them is wrong."""
    rows: dict[str, TracedRow] = {}
    for trace_file in trace_files:
        for row in read_table(trace_file):
            if "nct" not in row or "disclosed" not in row:
                raise ValueError(f"{trace_file}: a trace names each trial and says whether its result was disclosed")
            if row["nct"] in rows:
                raise ValueError(f"{row['nct']} is traced in both {rows[row['nct']].traced_in} and {trace_file.stem}")
            rows[row["nct"]] = _traced(row, trace_file.stem)
    return [rows[nct] for nct in sorted(rows)]
