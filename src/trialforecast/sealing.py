"""Sealing: proving a batch existed on a date without disclosing any forecast.

Each forecast gets its own commitment: a fingerprint of the forecast mixed with a
secret salt. The seal lists the trials and every commitment and nothing else; the
SHA-256 of the seal file is anchored by two outside time-stamping services. At
reveal, a forecast and its salt are disclosed for one trial; anyone can recompute
the commitment and find it in the seal, and learns nothing about any other
forecast (ADR-0001).

The seal and its anchors are plain files that the standard tools check directly:

    openssl ts -verify -data seal.json -in seal.json.tsr -CAfile <CA bundle>
    ots verify seal.json.ots
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import secrets
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable

from trialforecast import records
from trialforecast.anchors import METHODS, AnchorCheck, AnchorFailed, TimestampService, verifying_services
from trialforecast.batch import Batch, BatchTrial
from trialforecast.forecasting import FORECASTER_NAME, Forecast
from trialforecast.records import require_plain_date
from trialforecast.screening import ScreeningRecord, require_eligible

SEAL_FILE = "seal.json"
ANCHOR_FILES = {"rfc3161": "seal.json.tsr", "opentimestamps": "seal.json.ots"}  # what the standard tools expect
OPENINGS_FILE = "openings.jsonl"
PUBLISHING_BRANCH = "main"
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


class NotRegistered(Exception):
    """A batch was to be sealed before the protocol was registered."""


class SealNotAnchored(Exception):
    """A seal lacks a valid anchor from each of the two kinds of time-stamping service."""


class TamperedSeal(Exception):
    """A seal file on disk is not exactly a seal."""


class NotInSeal(Exception):
    """A revealed forecast is not the one committed to in the seal."""


@dataclass(frozen=True)
class Registration:
    """Where and when the study protocol was registered."""

    registry: str
    url: str
    registered_on: dt.date
    protocol_sha256: str

    def __post_init__(self) -> None:
        require_plain_date(self.registered_on, "registration date")
        if not self.registry.strip() or not self.url.strip():
            raise ValueError("a registration needs its registry and its address")
        if not _SHA256_HEX.fullmatch(self.protocol_sha256):
            raise ValueError("a registration needs the SHA-256 of the protocol file as registered")


def read_registration(path: pathlib.Path) -> Registration | None:
    """The registration recorded by the setup wizard, or None if the protocol is not yet registered."""
    if not path.exists():
        return None
    return records.from_line(Registration, path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Plan:
    """The registered comparison: the forecaster that carries the claim, its reference, and the effect-size baselines.

    Every seal carries it, so which forecaster carries the claim is fixed before any result is known.
    """

    forecaster: str
    reference: str
    effect_size_baselines: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "effect_size_baselines", tuple(self.effect_size_baselines))
        if not all(isinstance(name, str) and FORECASTER_NAME.fullmatch(name) for name in self.forecasters):
            raise ValueError(f"a plan names forecasters, not {self.forecasters}")
        if not self.effect_size_baselines or self.forecaster in (self.reference, *self.effect_size_baselines):
            raise ValueError("a plan compares one forecaster with a reference and at least one baseline, all other than itself")

    @property
    def forecasters(self) -> tuple[str, ...]:
        return (self.forecaster, self.reference, *self.effect_size_baselines)


def read_plan(path: pathlib.Path) -> Plan:
    """The plan as recorded in the study folder, for the first sealing to carry."""
    return records.from_line(Plan, path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Opening:
    """What is disclosed at reveal for one forecast: its canonical line and the salt of its commitment."""

    forecaster: str
    nct: str
    salt: str
    line: str

    @property
    def commitment(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.salt) + self.line.encode()).hexdigest()


@dataclass(frozen=True)
class Seal:
    """What is published when a batch is sealed: its trials and one commitment per forecast, and no forecast."""

    batch_date: dt.date
    registration_url: str
    protocol_sha256: str
    trials: tuple[BatchTrial, ...]
    commitments: dict[str, dict[str, str]]  # forecaster, then trial
    plan: Plan
    previous_seal: str | None  # the fingerprint of the seal before this one, so that none can be left out later

    def __post_init__(self) -> None:
        require_plain_date(self.batch_date, "batch date")
        if not isinstance(self.registration_url, str) or not _SHA256_HEX.fullmatch(str(self.protocol_sha256)):
            raise ValueError("a seal must name the registered protocol")
        if not isinstance(self.plan, Plan):
            raise ValueError("a seal must carry the registered plan")
        absent = [name for name in self.plan.forecasters if name not in self.commitments]
        if absent:
            raise ValueError(f"the plan names forecasters that are not in the batch: {', '.join(absent)}")
        if self.previous_seal is not None and not _SHA256_HEX.fullmatch(str(self.previous_seal)):
            raise ValueError("the seal before this one is named by its SHA-256 in hexadecimal")
        listed = sorted(t.nct for t in self.trials)
        if len(set(listed)) != len(listed):
            raise ValueError("a seal lists each trial once")
        for forecaster, by_trial in self.commitments.items():
            if not FORECASTER_NAME.fullmatch(str(forecaster)) or sorted(by_trial) != listed:
                raise ValueError(f"{forecaster!r} must hold one commitment for each trial in the seal and no other")
            if not all(isinstance(c, str) and _SHA256_HEX.fullmatch(c) for c in by_trial.values()):
                raise ValueError(f"{forecaster}: a commitment is a SHA-256 in hexadecimal and nothing else")

    def file_bytes(self) -> bytes:
        """The exact bytes of the seal file. Their SHA-256 is what the anchors are for."""
        document = {
            "batch_date": self.batch_date.isoformat(),
            "registration_url": self.registration_url,
            "protocol_sha256": self.protocol_sha256,
            "trials": [json.loads(records.to_line(t)) for t in sorted(self.trials, key=lambda t: t.nct)],
            "commitments": self.commitments,
            "plan": json.loads(records.to_line(self.plan)),
            "previous_seal": self.previous_seal,
        }
        return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.file_bytes()).hexdigest()


@dataclass(frozen=True)
class SealedBatch:
    seal: Seal
    openings: tuple[Opening, ...]  # private until each trial's reveal
    anchors: dict[str, bytes]  # by time-stamping method


def verify_seal(seal: Seal, anchors: dict[str, bytes], services: Iterable[TimestampService]) -> dict[str, AnchorCheck]:
    """Confirm the seal has a valid anchor from each of the two kinds of time-stamping service."""
    by_method = {s.method: s for s in services}
    checks = {}
    for method in METHODS:
        if method not in by_method or method not in anchors:
            raise SealNotAnchored(f"seal {seal.fingerprint} has no {method} anchor that can be checked")
        try:
            checks[method] = by_method[method].verify(seal.fingerprint, anchors[method])
        except AnchorFailed as failure:
            raise SealNotAnchored(f"seal {seal.fingerprint}: {failure}") from failure
    signed_on = checks["rfc3161"].signed_on
    if signed_on != seal.batch_date:
        raise SealNotAnchored(f"the RFC 3161 anchor was signed on {signed_on}, not on the batch date {seal.batch_date}")
    return checks


def seal_batch(
    batch: Batch,
    screening: Iterable[ScreeningRecord],
    registration: Registration | None,
    plan: Plan,
    previous: Seal | None,
    services: Iterable[TimestampService],
    today: dt.date,
) -> SealedBatch:
    """Seal a batch on its own date, under the registered plan, following the seal before it.

    Refuses without a registered protocol, an eligible screening for every trial,
    or one anchor from each kind of time-stamping service signed that day. Refuses
    a plan other than the previous seal's, and a batch not dated after it.
    """
    if registration is None:
        raise NotRegistered("no protocol registration is recorded")
    if registration.registered_on > batch.batch_date:
        raise NotRegistered(f"the protocol was registered on {registration.registered_on}, after this batch")
    if today != batch.batch_date:
        raise ValueError(f"a batch dated {batch.batch_date} can only be sealed on that day, not on {today}")
    if previous is not None and previous.plan != plan:
        raise ValueError("the plan cannot change once a batch is sealed")
    if previous is not None and previous.batch_date >= batch.batch_date:
        raise ValueError(f"a batch is sealed after the one before it, which was dated {previous.batch_date}")
    # The reference and the baselines are what every comparison falls back on, so they must have forecast every trial.
    for name in (plan.reference, *plan.effect_size_baselines):
        if any(forecast.no_forecast for forecast in batch.forecasts.get(name, ())):
            raise ValueError(f"{name} gave no forecast for a trial, so it cannot be the reference or a baseline")
    require_eligible(batch.batch_date, [t.nct for t in batch.trials], screening)
    services = list(services)
    if sorted(s.method for s in services) != sorted(METHODS):
        raise SealNotAnchored(f"sealing needs exactly one service of each kind: {', '.join(METHODS)}")

    openings = tuple(
        Opening(forecaster=name, nct=forecast.nct, salt=secrets.token_hex(32), line=records.to_line(forecast))
        for name in sorted(batch.forecasts) for forecast in batch.forecasts[name]
    )
    commitments: dict[str, dict[str, str]] = {}
    for opening in openings:
        commitments.setdefault(opening.forecaster, {})[opening.nct] = opening.commitment
    seal = Seal(batch.batch_date, registration.url, registration.protocol_sha256, batch.trials, commitments, plan,
                previous.fingerprint if previous else None)
    anchors = {s.method: s.anchor(seal.fingerprint) for s in services}
    verify_seal(seal, anchors, services)
    return SealedBatch(seal, openings, anchors)


def verify_opening(opening: Opening, seal: Seal) -> Forecast:
    """The forecast an opening discloses, if it is exactly the one committed to for that forecaster and trial."""
    slot = f"{opening.forecaster} / {opening.nct}"
    if not _SHA256_HEX.fullmatch(opening.salt):
        raise NotInSeal(f"{slot}: the salt is not 32 bytes of hexadecimal")
    if seal.commitments.get(opening.forecaster, {}).get(opening.nct) != opening.commitment:
        raise NotInSeal(f"{slot}: does not match the commitment in the seal")
    try:
        forecast = records.from_line(Forecast, opening.line)
    except (ValueError, TypeError, KeyError) as unreadable:
        raise NotInSeal(f"{slot}: the line disclosed is not a forecast") from unreadable
    if records.to_line(forecast) != opening.line:
        raise NotInSeal(f"{slot}: the line disclosed is not in canonical form, so it could be read two ways")
    if (forecast.forecaster, forecast.nct, forecast.batch_date) != (opening.forecaster, opening.nct, seal.batch_date):
        raise NotInSeal(f"{slot}: the forecast disclosed is for something else")
    return forecast


def write_sealed_batch(
    sealed: SealedBatch, public_root: pathlib.Path, private_root: pathlib.Path
) -> tuple[pathlib.Path, pathlib.Path]:
    """Write the seal with its anchors, and separately the openings. Returns both directories."""
    day = sealed.seal.batch_date.isoformat()
    public_dir, private_dir = public_root / day, private_root / day
    public_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)
    (public_dir / SEAL_FILE).write_bytes(sealed.seal.file_bytes())
    for method, anchor in sealed.anchors.items():
        (public_dir / ANCHOR_FILES[method]).write_bytes(anchor)
    for opening in sealed.openings:
        records.append(private_dir / OPENINGS_FILE, opening)
    return public_dir, private_dir


def read_seal(public_dir: pathlib.Path) -> tuple[Seal, dict[str, bytes]]:
    """Read a seal and its anchors, refusing a file that is anything other than exactly a seal."""
    written = (public_dir / SEAL_FILE).read_bytes()
    try:
        document = json.loads(written)
        seal = Seal(
            batch_date=dt.date.fromisoformat(document["batch_date"]),
            registration_url=document["registration_url"],
            protocol_sha256=document["protocol_sha256"],
            trials=tuple(BatchTrial(**t) for t in document["trials"]),
            commitments=document["commitments"],
            plan=Plan(**document["plan"]),
            previous_seal=document["previous_seal"],
        )
    except (ValueError, TypeError, KeyError) as unreadable:
        raise TamperedSeal(f"{public_dir}: the seal file cannot be read as a seal") from unreadable
    if seal.file_bytes() != written:
        raise TamperedSeal(f"{public_dir}: the seal file holds something other than a seal in its canonical form")
    anchors = {
        method: (public_dir / name).read_bytes() for method, name in ANCHOR_FILES.items() if (public_dir / name).exists()
    }
    return seal, anchors


def _opened(seal: Seal, anchors: dict[str, bytes], openings_file: pathlib.Path, services: Iterable[TimestampService]) -> Batch:
    checks = verify_seal(seal, anchors, services)
    if not checks["opentimestamps"].complete:
        raise SealNotAnchored(f"seal {seal.fingerprint}: its OpenTimestamps anchor has not reached the block chain; "
                              f"upgrade it (`ots upgrade`) before the batch is analysed")
    forecasts: dict[str, dict[str, Forecast]] = {name: {} for name in seal.commitments}
    for opening in records.read(openings_file, Opening):
        forecast = verify_opening(opening, seal)
        if forecast.nct in forecasts[opening.forecaster]:
            raise NotInSeal(f"{opening.forecaster} / {opening.nct}: opened more than once")
        forecasts[opening.forecaster][forecast.nct] = forecast
    unopened = [f"{name} / {nct}" for name, by_trial in sorted(seal.commitments.items())
                for nct in sorted(by_trial) if nct not in forecasts[name]]
    if unopened:
        raise NotInSeal(f"no opening for: {', '.join(unopened)}")
    return Batch(seal.batch_date, seal.trials,
                 {name: tuple(by_trial[nct] for nct in sorted(by_trial)) for name, by_trial in forecasts.items()})


def open_sealed_batch(
    public_dir: pathlib.Path, openings_file: pathlib.Path, services: Iterable[TimestampService]
) -> Batch:
    """The batch behind a published seal, for analysis: every forecast shown to be the one committed to.

    Refuses a seal without both anchors complete, and openings that are not exactly
    one matching opening for each commitment in the seal.
    """
    seal, anchors = read_seal(public_dir)
    return _opened(seal, anchors, openings_file, services)


@dataclass(frozen=True)
class SealedStudy:
    """Every sealed batch read back through its seal, the plan the seals carry, and their fingerprints in order."""

    batches: tuple[Batch, ...]
    plan: Plan | None  # None where nothing has been sealed
    seals: tuple[str, ...]


def read_sealed_study(
    public_root: pathlib.Path, private_root: pathlib.Path, services: Iterable[TimestampService]
) -> SealedStudy:
    """Read every sealed batch, refusing a set of seals that is not one unbroken chain under one plan.

    Each seal names the one before it, so a seal taken away from the start or the
    middle is noticed: without that, a later forecast could pass for a trial's first.
    """
    services = list(services)
    days = sorted(d.name for d in public_root.iterdir() if (d / SEAL_FILE).exists()) if public_root.exists() else []
    batches, previous = [], None
    for day in days:
        seal, anchors = read_seal(public_root / day)
        if seal.batch_date.isoformat() != day:
            raise TamperedSeal(f"{public_root / day}: holds the seal of {seal.batch_date}")
        if seal.previous_seal != (previous.fingerprint if previous else None):
            raise TamperedSeal(f"{public_root / day}: does not follow the seal before it; a seal is absent or out of order")
        if previous is not None and seal.plan != previous.plan:
            raise TamperedSeal(f"{public_root / day}: carries a plan other than the first seal's")
        batches.append(_opened(seal, anchors, private_root / day / OPENINGS_FILE, services))
        previous = seal
    fingerprints = tuple(hashlib.sha256((public_root / day / SEAL_FILE).read_bytes()).hexdigest() for day in days)
    return SealedStudy(tuple(batches), previous.plan if previous else None, fingerprints)


def publish_seal(repository: pathlib.Path, public_dir: pathlib.Path, services: Iterable[TimestampService]) -> None:
    """Commit one seal directory and push it, and nothing else.

    Refuses if the directory holds anything but a seal and its anchors, if the
    anchors do not hold, or if anything else would go out with the push: other
    staged changes, any unpushed commit, or a branch other than main.
    """
    allowed = {SEAL_FILE, *ANCHOR_FILES.values()}
    unexpected = sorted(p.name for p in public_dir.iterdir() if p.name not in allowed)
    if unexpected:
        raise ValueError(f"{public_dir} holds files that are not part of a seal: {', '.join(unexpected)}")
    if public_dir.is_symlink() or any(p.is_symlink() or not p.is_file() for p in public_dir.iterdir()):
        raise ValueError(f"{public_dir} must hold plain files, not a link to something elsewhere")
    seal, anchors = read_seal(public_dir)
    verify_seal(seal, anchors, services)
    seal_path = str(public_dir.relative_to(repository))

    def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(repository), *arguments], check=check, capture_output=True, text=True)

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch != PUBLISHING_BRANCH:
        raise ValueError(f"seals are published from {PUBLISHING_BRANCH}, and {branch} is checked out")
    if git("check-ignore", "-q", "--", seal_path, check=False).returncode == 0:
        raise ValueError(f"git is set to ignore {seal_path}, so the seal would not be published")
    # Ask the remote what it holds; the local record of it may be stale.
    if git("fetch", "origin", PUBLISHING_BRANCH, check=False).returncode != 0:
        raise ValueError(f"origin has no {PUBLISHING_BRANCH} branch to publish to; push {PUBLISHING_BRANCH} once first")
    upstream = f"origin/{PUBLISHING_BRANCH}"

    def outside_the_seal(paths: str) -> list[str]:
        return sorted(p for p in paths.splitlines() if p and not p.startswith(seal_path + "/"))

    staged = outside_the_seal(git("diff", "--cached", "--name-only").stdout)
    if staged:
        raise ValueError(f"other changes are staged and would be committed with the seal: {', '.join(staged)}")
    # Every unpushed commit goes out with the push, whatever a later commit undid. Only an
    # earlier attempt at publishing this very seal may be waiting.
    unpushed = git("rev-list", f"{upstream}..HEAD").stdout.split()
    touched = [git("show", "--name-only", "--format=", commit).stdout for commit in unpushed]
    if len(unpushed) > 1 or any(outside_the_seal(paths) for paths in touched):
        raise ValueError(f"{len(unpushed)} unpushed commit(s) would be published with the seal; push or drop them first")

    if git("status", "--porcelain", "--", seal_path).stdout.strip():
        git("add", "--", seal_path)
        git("commit", "-m", f"Seal batch {seal.batch_date.isoformat()}: {seal.fingerprint}", "--", seal_path)
    if git("rev-list", f"{upstream}..HEAD").stdout.strip():
        git("push", "--no-follow-tags", "origin", f"HEAD:{PUBLISHING_BRANCH}")


def verify_command(arguments: list[str] | None = None, services: Iterable[TimestampService] | None = None) -> int:
    """Check revealed forecasts against a published seal: `trialseal-verify <seal directory> <openings file>`."""
    arguments = sys.argv[1:] if arguments is None else arguments
    if len(arguments) != 2:
        print("usage: trialseal-verify <seal directory> <openings file>")
        return 2
    public_dir, openings_file = pathlib.Path(arguments[0]), pathlib.Path(arguments[1])
    services = verifying_services() if services is None else list(services)
    try:
        seal, anchors = read_seal(public_dir)
        checks = verify_seal(seal, anchors, services)
    except (TamperedSeal, SealNotAnchored) as problem:
        print(f"NOT VERIFIED: {problem}")
        return 1
    print(f"seal for batch {seal.batch_date}, fingerprint {seal.fingerprint}")
    print(f"  RFC 3161 anchor signed on {checks['rfc3161'].signed_on}")
    state = "in the block chain" if checks["opentimestamps"].complete else "awaiting the block chain"
    print(f"  OpenTimestamps anchor {state}; confirm with: ots verify {public_dir / ANCHOR_FILES['opentimestamps']}")
    try:
        openings = records.read(openings_file, Opening)
        if not openings:
            print(f"NOT VERIFIED: {openings_file} holds no openings")
            return 1
        for opening in openings:
            forecast = verify_opening(opening, seal)
            if forecast.no_forecast:
                print(f"  VERIFIED {forecast.forecaster} {forecast.nct}: no forecast produced ({forecast.no_forecast})")
                continue
            print(f"  VERIFIED {forecast.forecaster} {forecast.nct}: probability {forecast.probability_positive}, "
                  f"hazard ratio {forecast.hazard_ratio} ({forecast.hazard_ratio_low} to {forecast.hazard_ratio_high})")
    except (NotInSeal, ValueError, TypeError, KeyError) as problem:
        print(f"NOT VERIFIED: {problem}")
        return 1
    return 0
