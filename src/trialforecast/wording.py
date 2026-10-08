"""Small helpers for the sentences the commands print and the reports contain."""
from __future__ import annotations


def counted(n: int, noun: str, plural: str | None = None) -> str:
    """A count with its noun in the right number: "1 trial", "4 trials", "2 batches"."""
    return f"{n} {noun if n == 1 else plural or noun + 's'}"
