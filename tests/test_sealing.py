"""Sealing: proving a batch existed on a date without disclosing any forecast, and checking a reveal against it."""
import dataclasses
import datetime as dt
import hashlib
import json
import shutil
import subprocess

import pytest

from registry_records import study
from trialforecast import records, universe
from trialforecast.anchors import AnchorCheck
from trialforecast.batch import Batch, InvalidForecast, build_batch
from trialforecast.forecasting import BaseRateForecaster, Forecast
from trialforecast.screening import IneligibleTrial, ScreeningRecord
from trialforecast.sealing import (
    NotInSeal, NotRegistered, Opening, Registration, SealNotAnchored, TamperedSeal, publish_seal, read_registration,
    Plan, open_sealed_batch, read_plan, read_seal, read_sealed_study, seal_batch, verify_command, verify_opening, verify_seal, write_sealed_batch,
)

from study_records import BASE_RATES, BATCH_1, BATCH_2, HAZARD_RATIOS, PLAN, REGISTERED, FakeService, services

class StandIn:
    name, version, probability = "stand_in", "1", 0.8

    def forecast(self, candidate, batch_date):
        return Forecast(nct=candidate["nct"], forecaster=self.name, version=self.version, batch_date=batch_date,
                        probability_positive=self.probability, hazard_ratio=0.8, hazard_ratio_low=0.6, hazard_ratio_high=1.05)


SERVICES = services()
SCREENING = [ScreeningRecord(nct=nct, decision="eligible", screened_on=dt.date(2026, 10, 30), evidence="searched", confidence="high")
             for nct in ("NCT1", "NCT2")]


def a_batch(on=BATCH_1, probability=0.8):
    trials = [universe.flatten(study(nct, "Overall survival")) for nct in ("NCT1", "NCT2")]
    screening = [dataclasses.replace(s, screened_on=on - dt.timedelta(days=3)) for s in SCREENING]
    stand_in = StandIn()
    stand_in.probability = probability
    return build_batch(on, trials, screening, [BaseRateForecaster(BASE_RATES, HAZARD_RATIOS, version="2026-11"), stand_in])


def sealed(**kwargs):
    arguments = dict(batch=a_batch(), screening=SCREENING, design_reviews=(), registration=REGISTERED, plan=PLAN, previous=None,
                     services=SERVICES, today=BATCH_1)
    return seal_batch(**{**arguments, **kwargs})


def sealed_after(previous, on=BATCH_2, **kwargs):
    """A later batch sealed on its own day, following an earlier seal."""
    batch = a_batch(on, probability=0.3)
    screening = [dataclasses.replace(s, screened_on=on - dt.timedelta(days=3)) for s in SCREENING]
    return sealed(**{**dict(batch=batch, screening=screening, previous=previous, services=services(on), today=on), **kwargs})


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
    read_out_since = SCREENING + [ScreeningRecord(
        nct="NCT1", decision="already_read_out", screened_on=BATCH_1, evidence="topline announced this morning",
        confidence="high", readout_date=BATCH_1, evidence_links=("https://example.test/topline",))]
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
            ScreeningRecord(nct=misspelt, decision="eligible", screened_on=BATCH_1, evidence="searched", confidence="high")
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


# --- reading a sealed batch back for analysis ------------------------------------------


def test_a_sealed_batch_is_read_back_from_its_seal_and_its_openings(tmp_path):
    public_dir, private_dir = write_sealed_batch(sealed(), tmp_path / "seals", tmp_path / "private")
    assert open_sealed_batch(public_dir, private_dir / "openings.jsonl", SERVICES) == a_batch()


def test_a_sealed_batch_is_not_read_back_unless_every_commitment_is_opened_as_sealed(tmp_path):
    public_dir, private_dir = write_sealed_batch(sealed(), tmp_path / "seals", tmp_path / "private")
    openings = private_dir / "openings.jsonl"
    written = openings.read_text()

    openings.write_text("".join(written.splitlines(keepends=True)[:-1]))
    with pytest.raises(NotInSeal, match="stand_in / NCT2"):
        open_sealed_batch(public_dir, openings, SERVICES)

    assert "0.8" in written
    openings.write_text(written.replace("0.8", "0.9"))
    with pytest.raises(NotInSeal):
        open_sealed_batch(public_dir, openings, SERVICES)

    openings.write_text(written + written.splitlines(keepends=True)[0])
    with pytest.raises(NotInSeal, match="opened more than once"):
        open_sealed_batch(public_dir, openings, SERVICES)

    openings.write_text(written)
    (public_dir / "seal.json.tsr").write_bytes(b"not an anchor")
    with pytest.raises(SealNotAnchored):
        open_sealed_batch(public_dir, openings, SERVICES)


# --- the plan and the chain of seals ------------------------------------------------------


def test_a_seal_names_the_registered_plan_and_the_seal_before_it():
    first = sealed().seal
    assert (first.plan, first.previous_seal) == (PLAN, None)
    second = sealed_after(first).seal
    assert (second.plan, second.previous_seal) == (PLAN, first.fingerprint)
    document = json.loads(second.file_bytes())
    assert document["plan"] == {"forecaster": "stand_in", "reference": "base_rate", "effect_size_baselines": ["base_rate"]}
    assert document["previous_seal"] == first.fingerprint


def test_a_plan_names_two_different_forecasters_and_at_least_one_baseline(tmp_path):
    for wrong in (dict(reference="stand_in"), dict(effect_size_baselines=()), dict(forecaster="Not A Name"),
                  dict(effect_size_baselines=("stand_in",))):
        with pytest.raises(ValueError):
            dataclasses.replace(PLAN, **wrong)
    recorded = tmp_path / "analysis_plan.json"
    recorded.write_text(json.dumps({"forecaster": "stand_in", "reference": "base_rate", "effect_size_baselines": ["base_rate"]}))
    assert read_plan(recorded) == PLAN


def test_a_batch_is_not_sealed_under_a_plan_that_names_a_forecaster_it_lacks():
    with pytest.raises(ValueError, match="span"):
        sealed(plan=dataclasses.replace(PLAN, forecaster="span"))
    with pytest.raises(ValueError, match="shrunk"):
        sealed(plan=dataclasses.replace(PLAN, effect_size_baselines=("base_rate", "shrunk")))


def test_the_plan_cannot_change_once_a_batch_is_sealed_and_seals_follow_in_date_order():
    first = sealed().seal
    with pytest.raises(ValueError, match="plan"):
        sealed_after(first, plan=Plan("base_rate", "stand_in", ("stand_in",)))
    with pytest.raises(ValueError, match="after"):
        sealed(previous=first)    # a second seal on the first one's date


def test_a_sealed_study_is_read_back_whole_or_not_at_all(tmp_path):
    first = sealed()
    second = sealed_after(first.seal)
    third = sealed_after(second.seal, on=dt.date(2027, 1, 4))
    for sealed_batch in (first, second, third):
        write_sealed_batch(sealed_batch, tmp_path / "seals", tmp_path / "private")
    class AnyDay(FakeService):
        """Checks an anchor as signed on the day the seal names, as a real service reports the day it signed."""

        def verify(self, fingerprint, anchor):
            super().verify(fingerprint, anchor)
            signed_on = next(s.seal.batch_date for s in (first, second, third) if s.seal.fingerprint == fingerprint)
            return AnchorCheck(signed_on=signed_on if self.method == "rfc3161" else None, complete=True)

    checking = [AnyDay("rfc3161"), AnyDay("opentimestamps")]
    study = read_sealed_study(tmp_path / "seals", tmp_path / "private", checking)
    assert [b.batch_date for b in study.batches] == [BATCH_1, BATCH_2, dt.date(2027, 1, 4)]
    assert study.plan == PLAN and study.seals == tuple(s.seal.fingerprint for s in (first, second, third))

    # With the first or a middle seal taken away, a later forecast could pass for a trial's first.
    for taken_away in (BATCH_1, BATCH_2):
        copy = tmp_path / f"without-{taken_away}"
        shutil.copytree(tmp_path / "seals", copy)
        shutil.rmtree(copy / taken_away.isoformat())
        with pytest.raises(TamperedSeal, match="does not follow"):
            read_sealed_study(copy, tmp_path / "private", checking)

    assert read_sealed_study(tmp_path / "nothing-here", tmp_path / "private", checking).batches == ()


def test_a_seal_is_not_analysed_until_its_opentimestamps_anchor_has_reached_the_block_chain(tmp_path):
    public_dir, private_dir = write_sealed_batch(sealed(), tmp_path / "seals", tmp_path / "private")
    with pytest.raises(SealNotAnchored, match="block chain"):
        open_sealed_batch(public_dir, private_dir / "openings.jsonl", services(complete=False))


def test_a_seal_directory_is_named_for_the_date_of_its_seal(tmp_path):
    public_dir, _ = write_sealed_batch(sealed(), tmp_path / "seals", tmp_path / "private")
    public_dir.rename(tmp_path / "seals" / "2026-11-03")
    with pytest.raises(TamperedSeal, match="2026-11-03"):
        read_sealed_study(tmp_path / "seals", tmp_path / "private", SERVICES)


def test_a_batch_is_not_sealed_with_a_reference_or_baseline_that_gave_no_forecast():
    class Silent(StandIn):
        name = "silent"

        def forecast(self, candidate, batch_date):
            return Forecast(nct=candidate["nct"], forecaster=self.name, version=self.version, batch_date=batch_date,
                            probability_positive=None, hazard_ratio=None, hazard_ratio_low=None, hazard_ratio_high=None,
                            no_forecast="refused")

    trials = [universe.flatten(study(nct, "Overall survival")) for nct in ("NCT1", "NCT2")]
    batch = build_batch(BATCH_1, trials, SCREENING,
                        [BaseRateForecaster(BASE_RATES, HAZARD_RATIOS, version="2026-11"), StandIn(), Silent()])
    sealed(batch=batch)    # a forecaster outside the plan may have no forecast
    for plan in (Plan("stand_in", "silent", ("base_rate",)), Plan("stand_in", "base_rate", ("silent",))):
        with pytest.raises(ValueError, match="silent gave no forecast"):
            sealed(batch=batch, plan=plan)


def test_a_seal_that_carries_another_plan_than_the_first_is_refused_when_read_back(tmp_path):
    first = sealed()
    second = sealed_after(first.seal)
    other_plan = dataclasses.replace(second.seal, plan=Plan("base_rate", "stand_in", ("stand_in",)))
    forged = dataclasses.replace(second, seal=other_plan,
                                 anchors={s.method: s.anchor(other_plan.fingerprint) for s in services(BATCH_2)})
    write_sealed_batch(first, tmp_path / "seals", tmp_path / "private")
    write_sealed_batch(forged, tmp_path / "seals", tmp_path / "private")
    with pytest.raises(TamperedSeal, match="plan other than the first"):
        read_sealed_study(tmp_path / "seals", tmp_path / "private", SERVICES)


def test_a_design_ruled_out_or_awaiting_a_ruling_cannot_be_sealed():
    from trialforecast.screening import DesignReview

    tagged = universe.flatten(study("NCT1", "Overall survival (non-inferiority)"))
    plain = universe.flatten(study("NCT2", "Overall survival"))
    forecasters = [BaseRateForecaster(BASE_RATES, HAZARD_RATIOS, version="2026-11"), StandIn()]

    def ruled(nct, decision):
        return DesignReview(nct, decision, "read the protocol", "Abhijoy Sarkar", dt.date(2026, 10, 30))

    batch = build_batch(BATCH_1, [tagged, plain], SCREENING, forecasters, design_reviews=[ruled("NCT1", "include")])
    sealed(batch=batch, design_reviews=[ruled("NCT1", "include")])
    with pytest.raises(IneligibleTrial, match="NCT1.*exclusion review"):
        sealed(batch=batch)                                               # the ruling is not there at the seal
    with pytest.raises(IneligibleTrial, match="NCT1.*excluded"):
        sealed(batch=batch, design_reviews=[ruled("NCT1", "include"), ruled("NCT1", "exclude")])
    with pytest.raises(IneligibleTrial, match="NCT2.*excluded"):
        sealed(batch=batch, design_reviews=[ruled("NCT1", "include"), ruled("NCT2", "exclude")])
