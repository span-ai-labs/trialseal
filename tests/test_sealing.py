"""Sealing: proving a batch existed on a date without disclosing any forecast, and checking a reveal against it."""
import dataclasses
import datetime as dt
import hashlib
import json
import subprocess

import pytest

from registry_records import study
from trialforecast import records, universe
from trialforecast.anchors import AnchorCheck, AnchorFailed
from trialforecast.batch import Batch, InvalidForecast, build_batch
from trialforecast.forecasting import BaseRateForecaster, Forecast
from trialforecast.screening import IneligibleTrial, ScreeningRecord
from trialforecast.sealing import (
    NotInSeal, NotRegistered, Opening, Registration, SealNotAnchored, TamperedSeal, publish_seal, read_registration,
    read_seal, seal_batch, verify_command, verify_opening, verify_seal, write_sealed_batch,
)

BATCH_1 = dt.date(2026, 11, 2)
REGISTERED = Registration(registry="OSF", url="https://osf.example/abcde", registered_on=dt.date(2026, 10, 31),
                          protocol_sha256="ab" * 32)
BASE_RATES = {"industry/overall_survival": 0.55}
HAZARD_RATIOS = {"industry/overall_survival": (0.84, 0.66, 1.07)}


class FakeService:
    """A stand-in time-stamping service: its anchor is the fingerprint under a method-specific prefix."""

    def __init__(self, method, signed_on=BATCH_1):
        self.method, self._signed_on = method, signed_on

    def anchor(self, fingerprint):
        return f"{self.method}:{fingerprint}".encode()

    def verify(self, fingerprint, anchor):
        if anchor != f"{self.method}:{fingerprint}".encode():
            raise AnchorFailed(f"{self.method}: not an anchor for {fingerprint}")
        return AnchorCheck(signed_on=self._signed_on if self.method == "rfc3161" else None, complete=True)


class StandIn:
    name, version = "stand_in", "1"

    def forecast(self, candidate, batch_date):
        return Forecast(nct=candidate["nct"], forecaster=self.name, version=self.version, batch_date=batch_date,
                        probability_positive=0.8, hazard_ratio=0.8, hazard_ratio_low=0.6, hazard_ratio_high=1.05)


SERVICES = [FakeService("rfc3161"), FakeService("opentimestamps")]
SCREENING = [ScreeningRecord(nct=nct, decision="eligible", screened_on=dt.date(2026, 10, 30), evidence="searched")
             for nct in ("NCT1", "NCT2")]


def a_batch():
    trials = [universe.flatten(study(nct, "Overall survival")) for nct in ("NCT1", "NCT2")]
    return build_batch(BATCH_1, trials, SCREENING,
                       [BaseRateForecaster(BASE_RATES, HAZARD_RATIOS, version="2026-11"), StandIn()])


def sealed(**kwargs):
    arguments = dict(batch=a_batch(), screening=SCREENING, registration=REGISTERED, services=SERVICES, today=BATCH_1)
    return seal_batch(**{**arguments, **kwargs})


def openings_for(sealed_batch, nct):
    return [o for o in sealed_batch.openings if o.nct == nct]


# --- what is public and what is not ---------------------------------------------------


def test_a_seal_commits_to_every_forecast_and_names_every_trial():
    seal = sealed().seal
    assert seal.batch_date == BATCH_1
    assert [t.nct for t in seal.trials] == ["NCT1", "NCT2"]
    assert seal.registration_url == "https://osf.example/abcde"
    assert {name: sorted(by_trial) for name, by_trial in seal.commitments.items()} == {
        "base_rate": ["NCT1", "NCT2"], "stand_in": ["NCT1", "NCT2"]}
    assert all(len(c) == 64 for by_trial in seal.commitments.values() for c in by_trial.values())


def test_nothing_written_for_the_public_discloses_a_forecast(tmp_path):
    sealed_batch = sealed()
    public_dir, private_dir = write_sealed_batch(sealed_batch, tmp_path / "seals", tmp_path / "private")
    assert sorted(p.name for p in public_dir.iterdir()) == ["seal.json", "seal.json.ots", "seal.json.tsr"]
    published = b"".join(p.read_bytes() for p in public_dir.iterdir()).decode()
    assert "probability_positive" not in published and "hazard_ratio" not in published
    for opening in sealed_batch.openings:
        assert opening.salt not in published and opening.line not in published
    # The forecasts and their salts are kept, privately.
    assert records.read(private_dir / "openings.jsonl", Opening) == list(sealed_batch.openings)


def test_the_fingerprint_is_the_sha256_of_the_seal_file_so_standard_tools_can_check_it(tmp_path):
    sealed_batch = sealed()
    public_dir, _ = write_sealed_batch(sealed_batch, tmp_path / "seals", tmp_path / "private")
    assert hashlib.sha256((public_dir / "seal.json").read_bytes()).hexdigest() == sealed_batch.seal.fingerprint


def test_a_commitment_cannot_be_guessed_from_the_forecast_alone():
    first, second = sealed(), sealed()
    opening = first.openings[0]
    assert opening.line == second.openings[0].line                                            # the same forecast
    commitment = first.seal.commitments[opening.forecaster][opening.nct]
    assert commitment != second.seal.commitments[opening.forecaster][opening.nct]             # a fresh secret every time
    assert commitment != hashlib.sha256(opening.line.encode()).hexdigest()                    # so hashing a guess proves nothing


# --- reveal and verification ---------------------------------------------------------


def test_a_revealed_forecast_is_confirmed_against_the_seal_without_the_other_trials():
    sealed_batch = sealed()
    opened = openings_for(sealed_batch, "NCT1")
    forecasts = {o.forecaster: verify_opening(o, sealed_batch.seal) for o in opened}
    assert forecasts["stand_in"] == StandIn().forecast({"nct": "NCT1"}, BATCH_1)
    assert forecasts["base_rate"].probability_positive == 0.55


def test_an_altered_reveal_is_rejected():
    sealed_batch = sealed()
    opening = next(o for o in openings_for(sealed_batch, "NCT1") if o.forecaster == "stand_in")
    for forged in (
        dataclasses.replace(opening, line=opening.line.replace("0.8", "0.99", 1)),  # a better-looking forecast
        dataclasses.replace(opening, salt="00" * 32),                               # the wrong secret
        dataclasses.replace(opening, salt=""),
        dataclasses.replace(opening, nct="NCT2"),                                   # another trial's slot
        dataclasses.replace(opening, forecaster="base_rate"),                       # another forecaster's slot
        dataclasses.replace(opening, line="not json"),
    ):
        with pytest.raises(NotInSeal):
            verify_opening(forged, sealed_batch.seal)
    with pytest.raises(NotInSeal):
        verify_opening(opening, sealed().seal)  # the right forecast against the wrong seal


def test_a_reveal_must_be_the_exact_line_that_was_committed_to():
    original = sealed().seal
    honest = records.to_line(StandIn().forecast({"nct": "NCT1"}, BATCH_1))
    # The same line with one key repeated: a reader sees 0.8 first, a parser keeps the last, 0.05.
    line = honest.replace('"probability_positive":0.8', '"probability_positive":0.8,"probability_positive":0.05')
    assert line != honest
    opening = Opening(forecaster="stand_in", nct="NCT1", salt="11" * 32, line=line)
    seal = dataclasses.replace(original, commitments={
        **original.commitments, "stand_in": {**original.commitments["stand_in"], "NCT1": opening.commitment}})
    with pytest.raises(NotInSeal, match="canonical"):
        verify_opening(opening, seal)
    # The honest line under the same commitment scheme does verify, so it is the repetition that is refused.
    honest_opening = Opening(forecaster="stand_in", nct="NCT1", salt="11" * 32, line=honest)
    honest_seal = dataclasses.replace(original, commitments={
        **original.commitments, "stand_in": {**original.commitments["stand_in"], "NCT1": honest_opening.commitment}})
    assert verify_opening(honest_opening, honest_seal).probability_positive == 0.8


def test_anyone_can_check_a_reveal_from_the_command_line(tmp_path, capsys):
    sealed_batch = sealed()
    public_dir, _ = write_sealed_batch(sealed_batch, tmp_path / "seals", tmp_path / "private")
    revealed = tmp_path / "NCT1.jsonl"
    for opening in openings_for(sealed_batch, "NCT1"):
        records.append(revealed, opening)

    assert verify_command([str(public_dir), str(revealed)], services=SERVICES) == 0
    shown = capsys.readouterr().out
    assert sealed_batch.seal.fingerprint in shown and "stand_in" in shown and "0.8" in shown

    # Inside the revealed file each forecast line is itself a quoted string, hence the escaped quote.
    altered = revealed.read_text().replace('probability_positive\\":0.8', 'probability_positive\\":0.99')
    assert altered != revealed.read_text()
    revealed.write_text(altered)
    assert verify_command([str(public_dir), str(revealed)], services=SERVICES) == 1
    assert "does not match" in capsys.readouterr().out


# --- guards ------------------------------------------------------------------------------


def test_sealing_refuses_without_a_registered_protocol():
    with pytest.raises(NotRegistered):
        sealed(registration=None)
    registered_afterwards = dataclasses.replace(REGISTERED, registered_on=BATCH_1 + dt.timedelta(days=1))
    with pytest.raises(NotRegistered):
        sealed(registration=registered_afterwards)
    for incomplete in (dict(url=" "), dict(protocol_sha256="abc"), dict(registry="")):
        with pytest.raises(ValueError):
            dataclasses.replace(REGISTERED, **incomplete)


def test_sealing_refuses_a_trial_without_an_eligible_screening_record():
    with pytest.raises(IneligibleTrial, match="NCT2"):
        sealed(screening=SCREENING[:1])
    read_out_since = SCREENING + [ScreeningRecord(nct="NCT1", decision="already_read_out",
                                                  screened_on=BATCH_1, evidence="topline announced this morning")]
    with pytest.raises(IneligibleTrial, match="NCT1"):
        sealed(screening=read_out_since)


def test_a_batch_is_sealed_on_its_own_date_and_no_other():
    with pytest.raises(ValueError, match="2026-11-02"):
        sealed(today=BATCH_1 + dt.timedelta(days=1))
    signed_another_day = [FakeService("rfc3161", signed_on=BATCH_1 - dt.timedelta(days=300)), FakeService("opentimestamps")]
    with pytest.raises(SealNotAnchored, match="signed"):
        sealed(services=signed_another_day)


def test_a_batch_must_hold_exactly_one_forecast_per_forecaster_for_each_of_its_trials():
    batch = a_batch()
    stray = StandIn().forecast({"nct": "NCT9"}, BATCH_1)
    for broken in (
        {**batch.forecasts, "stand_in": batch.forecasts["stand_in"] + (stray,)},  # a trial the batch does not list
        {**batch.forecasts, "stand_in": batch.forecasts["stand_in"][:1]},         # a listed trial with no forecast
    ):
        with pytest.raises(InvalidForecast):
            Batch(batch_date=batch.batch_date, trials=batch.trials, forecasts=broken)
    with pytest.raises(InvalidForecast):
        Batch(batch_date=batch.batch_date, trials=batch.trials + batch.trials[:1], forecasts=batch.forecasts)


def test_sealing_needs_one_anchor_from_each_of_the_two_kinds_of_service():
    for services in ([], [FakeService("rfc3161")], [FakeService("rfc3161"), FakeService("rfc3161")],
                     [FakeService("rfc3161"), FakeService("another_rfc3161_authority")]):
        with pytest.raises(SealNotAnchored):
            sealed(services=services)
    sealed_batch = sealed()
    assert set(sealed_batch.anchors) == {"rfc3161", "opentimestamps"}
    checks = verify_seal(sealed_batch.seal, sealed_batch.anchors, SERVICES)
    assert checks["rfc3161"].signed_on == BATCH_1


def test_a_seal_is_not_anchored_unless_it_was_signed_on_its_batch_date(tmp_path, capsys):
    sealed_batch = sealed()
    signed_later = [FakeService("rfc3161", signed_on=dt.date(2027, 6, 1)), FakeService("opentimestamps")]
    with pytest.raises(SealNotAnchored, match="signed"):
        verify_seal(sealed_batch.seal, sealed_batch.anchors, signed_later)
    public_dir, _ = write_sealed_batch(sealed_batch, tmp_path / "seals", tmp_path / "private")
    revealed = tmp_path / "NCT1.jsonl"
    for opening in openings_for(sealed_batch, "NCT1"):
        records.append(revealed, opening)
    assert verify_command([str(public_dir), str(revealed)], services=signed_later) == 1
    assert "VERIFIED " not in capsys.readouterr().out.replace("NOT VERIFIED", "")


def test_checking_a_reveal_with_nothing_in_it_is_not_a_success(tmp_path):
    public_dir, _ = write_sealed_batch(sealed(), tmp_path / "seals", tmp_path / "private")
    (tmp_path / "empty.jsonl").write_text("")
    assert verify_command([str(public_dir), str(tmp_path / "empty.jsonl")], services=SERVICES) == 1


def test_a_seal_is_not_anchored_by_anchors_for_something_else():
    sealed_batch, other = sealed(), sealed()
    with pytest.raises(SealNotAnchored):
        verify_seal(sealed_batch.seal, other.anchors, SERVICES)
    with pytest.raises(SealNotAnchored):
        verify_seal(sealed_batch.seal, {"rfc3161": sealed_batch.anchors["rfc3161"]}, SERVICES)


# --- on disk and in the public repository ----------------------------------------------------


def test_a_seal_altered_on_disk_is_caught(tmp_path):
    sealed_batch = sealed()
    public_dir, _ = write_sealed_batch(sealed_batch, tmp_path / "seals", tmp_path / "private")
    seal, anchors = read_seal(public_dir)
    assert seal == sealed_batch.seal and anchors == sealed_batch.anchors
    verify_seal(seal, anchors, SERVICES)

    seal_file = public_dir / "seal.json"
    original = seal_file.read_text()
    document = json.loads(original)
    document["commitments"]["stand_in"]["NCT1"] = "0" * 64

    # Rewritten carefully in the same layout: it reads, but the anchors are for the original.
    seal_file.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    altered, _ = read_seal(public_dir)
    with pytest.raises(SealNotAnchored):
        verify_seal(altered, anchors, SERVICES)

    # Anything that is not exactly a seal is refused outright, such as an extra field holding a forecast.
    seal_file.write_text(json.dumps({**json.loads(original), "note": "probability 0.8"}, indent=2, sort_keys=True) + "\n")
    with pytest.raises(TamperedSeal):
        read_seal(public_dir)


def test_a_seal_file_must_have_the_shape_of_a_seal_as_well_as_its_layout(tmp_path):
    public_dir, _ = write_sealed_batch(sealed(), tmp_path / "seals", tmp_path / "private")
    seal_file = public_dir / "seal.json"
    original = json.loads(seal_file.read_text())

    def rewritten(change):
        document = json.loads(json.dumps(original))
        change(document)
        seal_file.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")

    for change in (
        lambda d: d["commitments"]["stand_in"].update(note="NCT1 probability 0.8"),   # a message in a spare slot
        lambda d: d["commitments"]["stand_in"].update(NCT1="probability 0.8"),        # not a commitment
        lambda d: d["commitments"]["stand_in"].pop("NCT2"),                           # a trial with no commitment
        lambda d: d["commitments"].update({"Someone Else": d["commitments"]["stand_in"]}),
        lambda d: d["trials"].append(dict(d["trials"][0])),                           # a trial listed twice
        lambda d: d["trials"][0].update(scored_endpoint={"probability": 0.8}),
    ):
        rewritten(change)
        with pytest.raises(TamperedSeal):
            read_seal(public_dir)


def test_trial_identifiers_have_one_spelling():
    for misspelt in ("NCT1 ", "nct1", " NCT1", "", "1"):
        with pytest.raises(ValueError):
            ScreeningRecord(nct=misspelt, decision="eligible", screened_on=BATCH_1, evidence="searched")
        with pytest.raises(ValueError):
            Forecast(nct=misspelt, forecaster="x", version="1", batch_date=BATCH_1, probability_positive=0.5,
                     hazard_ratio=0.8, hazard_ratio_low=0.6, hazard_ratio_high=1.0)


def test_the_registration_record_is_read_as_the_setup_wizard_writes_it(tmp_path):
    assert read_registration(tmp_path / "registration.json") is None  # not registered yet
    (tmp_path / "registration.json").write_text(
        '{\n  "registry": "OSF",\n  "url": "https://osf.example/abcde",\n  "registered_on": "2026-10-31",\n'
        '  "protocol_sha256": "' + "ab" * 32 + '"\n}\n')
    assert read_registration(tmp_path / "registration.json") == REGISTERED


def git(directory, *arguments):
    return subprocess.run(["git", "-C", str(directory), *arguments], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repository(tmp_path):
    origin, repository = tmp_path / "origin.git", tmp_path / "repository"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repository)], check=True)
    git(repository, "config", "user.email", "study@example.test")
    git(repository, "config", "user.name", "Study")
    git(repository, "remote", "add", "origin", str(origin))
    (repository / ".gitignore").write_text("private/\n")
    git(repository, "add", ".gitignore")
    git(repository, "commit", "-q", "-m", "start")
    git(repository, "push", "-q", "-u", "origin", "main")
    return repository


def pushed_files(repository):
    return sorted(git(repository, "ls-tree", "-r", "--name-only", "origin/main").split())


def test_publishing_pushes_the_seal_and_only_the_seal(repository):
    sealed_batch = sealed()
    public_dir, _ = write_sealed_batch(sealed_batch, repository / "seals", repository / "private")
    publish_seal(repository, public_dir, SERVICES)

    assert pushed_files(repository) == [".gitignore", "seals/2026-11-02/seal.json", "seals/2026-11-02/seal.json.ots",
                                        "seals/2026-11-02/seal.json.tsr"]
    assert sealed_batch.seal.fingerprint in git(repository, "log", "-1", "--format=%s", "origin/main")
    publish_seal(repository, public_dir, SERVICES)  # running it again changes nothing
    assert len(git(repository, "log", "--format=%s", "origin/main").splitlines()) == 2


def test_publishing_refuses_whenever_something_other_than_the_seal_would_go_out(repository):
    sealed_batch = sealed()
    public_dir, _ = write_sealed_batch(sealed_batch, repository / "seals", repository / "private")
    forecast_in_clear = repository / "stand_in.jsonl"
    forecast_in_clear.write_text(sealed_batch.openings[0].line + "\n")

    # A forecast staged beside the seal.
    git(repository, "add", "stand_in.jsonl")
    with pytest.raises(ValueError, match="staged"):
        publish_seal(repository, public_dir, SERVICES)
    # A forecast committed earlier and not yet pushed.
    git(repository, "commit", "-q", "-m", "oops")
    with pytest.raises(ValueError, match="unpushed"):
        publish_seal(repository, public_dir, SERVICES)
    git(repository, "reset", "-q", "--hard", "origin/main")
    public_dir, _ = write_sealed_batch(sealed_batch, repository / "seals2", repository / "private2")

    # Another branch checked out.
    git(repository, "checkout", "-q", "-b", "wip")
    with pytest.raises(ValueError, match="main"):
        publish_seal(repository, public_dir, SERVICES)
    git(repository, "checkout", "-q", "main")

    # A file that is not part of a seal, or a seal whose anchors do not hold.
    (public_dir / "openings.jsonl").write_text("should never be here\n")
    with pytest.raises(ValueError, match="openings.jsonl"):
        publish_seal(repository, public_dir, SERVICES)
    (public_dir / "openings.jsonl").unlink()
    (public_dir / "seal.json.tsr").write_bytes(b"an anchor for something else")
    with pytest.raises(SealNotAnchored):
        publish_seal(repository, public_dir, SERVICES)
    assert pushed_files(repository) == [".gitignore"]


def test_publishing_refuses_history_that_ever_held_something_else(repository):
    sealed_batch = sealed()
    public_dir, _ = write_sealed_batch(sealed_batch, repository / "seals", repository / "private")
    (repository / "stand_in.jsonl").write_text(sealed_batch.openings[0].line + "\n")
    git(repository, "add", "stand_in.jsonl")
    git(repository, "commit", "-q", "-m", "oops")
    git(repository, "rm", "-q", "stand_in.jsonl")
    git(repository, "commit", "-q", "-m", "remove it again")  # the net change is nothing, but the history holds it
    with pytest.raises(ValueError, match="unpushed"):
        publish_seal(repository, public_dir, SERVICES)
    assert pushed_files(repository) == [".gitignore"]


def test_publishing_checks_what_the_remote_really_holds(repository, tmp_path):
    sealed_batch = sealed()
    public_dir, _ = write_sealed_batch(sealed_batch, repository / "seals", repository / "private")
    empty = tmp_path / "another.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(empty)], check=True)
    git(repository, "remote", "set-url", "origin", str(empty))  # the local record of origin/main is now stale
    with pytest.raises(ValueError, match="main"):
        publish_seal(repository, public_dir, SERVICES)
    assert git(empty, "for-each-ref").strip() == ""


def test_publishing_refuses_a_seal_that_is_a_link_or_that_git_ignores(repository, tmp_path):
    sealed_batch = sealed()
    public_dir, _ = write_sealed_batch(sealed_batch, repository / "seals", repository / "private")
    seal_file = public_dir / "seal.json"
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_bytes(seal_file.read_bytes())
    seal_file.unlink()
    seal_file.symlink_to(elsewhere)
    with pytest.raises(ValueError, match="link"):
        publish_seal(repository, public_dir, SERVICES)
    seal_file.unlink()
    seal_file.write_bytes(elsewhere.read_bytes())

    (repository / ".gitignore").write_text("private/\nseals/\n")
    git(repository, "commit", "-q", "-am", "ignore seals")
    git(repository, "push", "-q", "origin", "main")
    with pytest.raises(ValueError, match="ignore"):
        publish_seal(repository, public_dir, SERVICES)
