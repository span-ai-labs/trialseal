"""Append-only logs of study records, one canonical JSON line each."""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import pathlib
from typing import TypeVar, get_args, get_type_hints

Record = TypeVar("Record")


def require_plain_date(value: object, label: str) -> None:
    """Records hold calendar dates only: a datetime or a string would not read back as written."""
    if type(value) is not dt.date:
        raise ValueError(f"{label} must be a date, not {value!r}")


def to_line(record) -> str:
    """One record as canonical JSON: sorted keys, no spaces, dates as ISO text."""
    fields = {
        name: value.isoformat() if isinstance(value, dt.date) else value
        for name, value in dataclasses.asdict(record).items()
    }
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def from_line(record_type: type[Record], line: str) -> Record:
    values = json.loads(line)
    for name, declared in get_type_hints(record_type).items():
        holds_date = declared is dt.date or dt.date in get_args(declared)
        if holds_date and values.get(name) is not None:
            values[name] = dt.date.fromisoformat(values[name])
    return record_type(**values)


def append(path: pathlib.Path, record) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(to_line(record) + "\n")


def read(path: pathlib.Path, record_type: type[Record]) -> list[Record]:
    with path.open(encoding="utf-8") as f:
        return [from_line(record_type, line) for line in f if line.strip()]
