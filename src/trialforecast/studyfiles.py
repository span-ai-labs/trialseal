"""Where a study directory keeps things, and the few ways every command reads and writes them."""
from __future__ import annotations

import csv
import pathlib
from typing import Iterable

from trialforecast import records, universe
from trialforecast.batch import BatchTrial
from trialforecast.forecasting import Candidate

SCREENING_LOG = pathlib.Path("screening") / "screening.jsonl"
DESIGN_REVIEWS = pathlib.Path("screening") / "design_reviews.jsonl"
TRACES = pathlib.Path("data") / "readout_trace"
# Each set of past trials the adjudicators read has its own log, and a list of the trials they are to read.
REFERENCE_ADJUDICATION = pathlib.Path("adjudication") / "reference"
REFERENCE_WORKLIST = REFERENCE_ADJUDICATION / "worklist.csv"
PILOT_ADJUDICATION = pathlib.Path("adjudication") / "pilot"
PILOT_WORKLIST = pathlib.Path("results") / "pilot" / "adjudication_worklist.csv"


def latest_snapshot(root: pathlib.Path) -> pathlib.Path:
    """The most recent registry snapshot in a study directory."""
    held = sorted(d for d in (root / "snapshots").iterdir() if (d / "studies.jsonl.gz").exists()) \
        if (root / "snapshots").exists() else []
    if not held:
        raise ValueError(f"no registry snapshot under {root / 'snapshots'}")
    return held[-1]


def registry_records(snapshot: pathlib.Path) -> dict[str, dict]:
    """Every trial in a snapshot by registry number. Where the registry had nothing, the field is None."""
    table, _ = universe.load_snapshot(snapshot)
    # A record read from a table carries NaN where the registry had nothing.
    return {row["nct"]: {field: None if value != value else value for field, value in row.items()}
            for row in table.to_dict("records")}


def read_records(path: pathlib.Path, record_type: type) -> list:
    """A log's records, or none if the log has not been started."""
    return records.read(path, record_type) if path.exists() else []


def read_table(path: pathlib.Path) -> list[dict]:
    """A CSV as rows of trimmed text. A cell with no column to belong to makes the file unreadable."""
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except UnicodeDecodeError:
        raise ValueError(f"{path} is not saved as UTF-8: in a spreadsheet, save it as \"CSV UTF-8\"") from None
    if any(None in row for row in rows):
        raise ValueError(f"{path}: a row has more cells than the header has columns")
    return [{key: (value or "").strip() for key, value in row.items()} for row in rows]


def write_table(path: pathlib.Path, columns: Iterable[str], rows: Iterable[Iterable]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows([["" if value is None else value for value in row] for row in rows])


def sealed_as(candidate: Candidate) -> BatchTrial:
    """A registry record as a batch would fix it, for rules that are written against sealed trials."""
    def text(field: str) -> str | None:
        return candidate.get(field) if isinstance(candidate.get(field), str) else None

    return BatchTrial(candidate["nct"], candidate["scored_endpoint"], text("sponsor_type"), candidate["endpoint_type"])
