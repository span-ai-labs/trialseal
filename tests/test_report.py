"""One command regenerates every registered table and figure, from the seals, openings and logs on disk."""
import csv
import datetime as dt
import hashlib
import json

import pytest

from study_records import (
    BATCH_1, EIGHTEEN_MONTHS, REGISTERED, TWENTY_FOUR_MONTHS, FixedForecaster, base_rate, both_adjudicated, candidate,
    keys_anywhere, screened, services,
)
from trialforecast import records
from trialforecast.batch import build_batch
from trialforecast.report import main
from trialforecast.sealing import Plan, seal_batch, write_sealed_batch

SERVICES = services()
BEFORE_THE_LOOK, AFTER_THE_LOOK = dt.date(2027, 4, 1), dt.date(2027, 4, 16)
SPAN_AGAINST_BASE_RATE = Plan(forecaster="span", reference="base_rate", effect_size_baselines=("base_rate",))


@pytest.fixture
def study_dir(tmp_path):
    """A study on disk: one sealed batch of four trials, three of which have read out and one screened since."""
    trials = [candidate("NCT1", drug="Examplumab"), candidate("NCT2", drug="Examplumab"), candidate("NCT3"),
              candidate("NCT4")]
    screening = [screened(c["nct"], "eligible") for c in trials]
    said = {"NCT1": 0.9, "NCT2": 0.3, "NCT3": 0.7, "NCT4": 0.5}
    batch = build_batch(BATCH_1, trials, screening,
                        [base_rate(), FixedForecaster("span", said, hazard_ratio=(0.72, 0.6, 0.86))])
    sealed = seal_batch(batch, screening, (), REGISTERED, SPAN_AGAINST_BASE_RATE, None, SERVICES, today=BATCH_1)
    write_sealed_batch(sealed, tmp_path / "seals", tmp_path / "private")
    for adjudication in (
        both_adjudicated("NCT1", "positive", readout=dt.date(2027, 2, 1), hazard_ratio=0.7,
                         hazard_ratio_endpoint="Overall survival")
        + both_adjudicated("NCT2", "negative", readout=dt.date(2027, 3, 1))
        + both_adjudicated("NCT3", "positive", readout=dt.date(2027, 9, 1), hazard_ratio=0.8,
                           hazard_ratio_endpoint="Overall survival")
    ):
        records.append(tmp_path / "adjudication" / "adjudications.jsonl", adjudication)
    for looked_on in (EIGHTEEN_MONTHS, TWENTY_FOUR_MONTHS):
        records.append(tmp_path / "screening" / "screening.jsonl", screened("NCT4", "eligible", on=looked_on))
    return tmp_path


def seal_fingerprint(study_dir):
    return hashlib.sha256((study_dir / "seals" / BATCH_1.isoformat() / "seal.json").read_bytes()).hexdigest()


def regenerate(study_dir, today):
    return main(["--study", str(study_dir)], today=today, services=SERVICES)


def table(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_before_the_look_nothing_is_scored(study_dir, capsys):
    assert regenerate(study_dir, BEFORE_THE_LOOK) == 0
    assert not (study_dir / "results").exists()
    assert not (study_dir / "study" / "analyses.jsonl").exists()
    shown = capsys.readouterr().out
    assert "1 batch, 4 trials sealed, 2 with a result" in shown
    assert "descriptive look is fixed for 2027-04-15" in shown and "final analysis is fixed for 2028-05-02" in shown


def test_the_look_is_written_as_tables_and_a_figure_and_compares_nothing(study_dir):
    assert regenerate(study_dir, AFTER_THE_LOOK) == 0
    look_dir = study_dir / "results" / "descriptive_look"
    assert sorted(p.name for p in look_dir.iterdir()) == [
        "calibration.csv", "calibration.png", "forecasters.csv", "models.csv", "summary.json"]
    summary = json.loads((look_dir / "summary.json").read_text())
    assert summary["n_trials"] == 2 and summary["forecasters"]["span"]["brier"] == pytest.approx((0.01 + 0.09) / 2)
    assert not keys_anywhere(summary) & {"difference", "mean_diff", "p_two_sided", "ci_low", "ci_high"}
    rows = table(look_dir / "forecasters.csv")
    assert [(r["trials"], r["forecaster"], r["n_trials"]) for r in rows] == [
        ("primary analysis set", "base_rate", "2"), ("primary analysis set", "span", "2"),
        ("all sponsors", "base_rate", "2"), ("all sponsors", "span", "2")]
    assert float(rows[1]["brier"]) == pytest.approx(0.05) and float(rows[0]["brier"]) == pytest.approx((0.2025 + 0.3025) / 2)
    assert not (study_dir / "results" / "final_analysis").exists()


def test_the_extension_is_recorded_and_shows_no_score(study_dir, capsys):
    assert regenerate(study_dir, EIGHTEEN_MONTHS) == 0
    decision = json.loads((study_dir / "results" / "final_analysis" / "summary.json").read_text())
    assert decision == {"kind": "final_analysis", "decision": "extended", "n_trials": 3, "run_on": "2028-05-02",
                        "readouts_to": "2028-11-02", "seals": [seal_fingerprint(study_dir)]}
    assert [p.name for p in (study_dir / "results" / "final_analysis").iterdir()] == ["summary.json"]
    assert "extended to 2028-11-02" in capsys.readouterr().out


def test_the_final_analysis_is_written_as_every_registered_table_and_figure(study_dir, capsys):
    regenerate(study_dir, EIGHTEEN_MONTHS)
    assert regenerate(study_dir, TWENTY_FOUR_MONTHS) == 0

    final_dir = study_dir / "results" / "final_analysis"
    assert sorted(p.name for p in final_dir.iterdir()) == [
        "calibration.csv", "calibration.png", "comparisons.csv", "differences.png", "effect_size.csv",
        "forecasters.csv", "lead_time.csv", "models.csv", "summary.json", "versions.csv"]
    summary = json.loads((final_dir / "summary.json").read_text())
    assert summary["decision"] == "estimate_only" and summary["primary"]["n_trials"] == 3
    assert summary["primary"]["n_drug_groups"] == 2 and summary["effect_size"]["base_rate"]["n_trials"] == 2
    # The forecaster that carries the claim is the one the seal named, and the seal is named in the summary.
    assert set(summary["primary"]["brier"]) == {"span", "base_rate"} and summary["seals"] == [seal_fingerprint(study_dir)]
    comparisons = table(final_dir / "comparisons.csv")
    assert [row["comparison"] for row in comparisons] == [
        "primary", "all sponsors", "last forecast before readout", "without non-English disclosures",
        "void counted as negative", "unresolved imputed as negative", "unresolved imputed as positive",
        "with sources read after the forecasts were opened"]
    primary = comparisons[0]
    assert float(primary["brier_forecaster"]) == pytest.approx((0.01 + 0.09 + 0.09) / 3)
    assert float(primary["brier_reference"]) == pytest.approx((0.2025 + 0.3025 + 0.2025) / 3)
    assert float(primary["mean_diff"]) == pytest.approx(float(primary["brier_forecaster"]) - float(primary["brier_reference"]))
    assert (primary["ci_low"], primary["p_two_sided"]) == ("", "")    # two drug groups: no interval, and no test
    reported, with_missing = table(final_dir / "effect_size.csv")
    assert (reported["analysis"], with_missing["analysis"]) == ("hazard ratios reported", "missing counted as no effect")
    assert float(reported["crps_forecaster"]) < float(reported["crps_baseline"]) and reported["hazard_ratio_missing"] == "1"
    assert (reported["n_trials"], with_missing["n_trials"]) == ("2", "3")
    assert "no claim is made" in capsys.readouterr().out
    # Regenerating changes nothing.
    before = {p.name: p.read_bytes() for p in final_dir.iterdir() if p.suffix != ".png"}
    assert regenerate(study_dir, TWENTY_FOUR_MONTHS + dt.timedelta(days=40)) == 0
    assert {p.name: p.read_bytes() for p in final_dir.iterdir() if p.suffix != ".png"} == before


def test_nothing_is_regenerated_from_forecasts_that_do_not_match_their_seal(study_dir, capsys):
    openings = study_dir / "private" / BATCH_1.isoformat() / "openings.jsonl"
    openings.write_text(openings.read_text().replace("0.9", "0.99"))
    assert regenerate(study_dir, TWENTY_FOUR_MONTHS) == 1
    assert "NOT REGENERATED" in capsys.readouterr().out
    assert not (study_dir / "results").exists()


def test_a_log_that_cannot_be_read_stops_the_command_without_a_traceback(study_dir, capsys):
    (study_dir / "adjudication" / "withdrawals.jsonl").write_text(json.dumps({
        "nct": "NCT1", "adjudicator": "first", "source_type": "registry", "source": "never read",
        "reason": "nothing to take back", "recorded_on": "2027-02-02"}) + "\n")
    assert regenerate(study_dir, AFTER_THE_LOOK) == 1
    shown = capsys.readouterr().out
    assert "NOT REGENERATED" in shown and "nothing to withdraw" in shown


def test_the_final_analysis_is_not_run_while_a_sealed_trial_is_unaccounted_for(study_dir, capsys):
    (study_dir / "screening" / "screening.jsonl").unlink()
    assert regenerate(study_dir, EIGHTEEN_MONTHS) == 1
    shown = capsys.readouterr().out
    assert "NOT REGENERATED" in shown and "NCT4" in shown
    assert not (study_dir / "results" / "final_analysis").exists()


def test_a_final_analysis_already_run_is_not_rerun_on_a_changed_log(study_dir, capsys):
    regenerate(study_dir, EIGHTEEN_MONTHS)
    regenerate(study_dir, TWENTY_FOUR_MONTHS)
    log = study_dir / "adjudication" / "adjudications.jsonl"
    log.write_text(log.read_text().replace('"not_met"', '"met"').replace('"negative"', '"positive"'))
    capsys.readouterr()
    assert regenerate(study_dir, TWENTY_FOUR_MONTHS + dt.timedelta(days=1)) == 1
    assert "NOT REGENERATED" in capsys.readouterr().out


def test_a_record_of_analyses_that_cannot_be_read_stops_the_command_without_a_traceback(study_dir, capsys):
    (study_dir / "study").mkdir()
    (study_dir / "study" / "analyses.jsonl").write_text("not a record\n")
    assert regenerate(study_dir, AFTER_THE_LOOK) == 1
    assert "NOT REGENERATED" in capsys.readouterr().out and not (study_dir / "results").exists()


def test_a_study_in_which_no_trial_can_be_scored_ends_without_a_claim_or_a_crash(study_dir, capsys):
    (study_dir / "adjudication" / "adjudications.jsonl").unlink()
    for nct in ("NCT1", "NCT2", "NCT3"):
        for looked_on in (EIGHTEEN_MONTHS, TWENTY_FOUR_MONTHS):
            records.append(study_dir / "screening" / "screening.jsonl", screened(nct, "eligible", on=looked_on))
    assert regenerate(study_dir, EIGHTEEN_MONTHS) == 0
    assert regenerate(study_dir, TWENTY_FOUR_MONTHS) == 0
    assert "no trial could be scored, so no claim is made" in capsys.readouterr().out


def test_the_effect_size_follow_up_is_written_six_months_after_the_final_analysis(study_dir, capsys):
    regenerate(study_dir, EIGHTEEN_MONTHS)
    regenerate(study_dir, TWENTY_FOUR_MONTHS)
    assert "effect-size follow-up is fixed for 2029-05-02" in capsys.readouterr().out
    assert not (study_dir / "results" / "effect_size_follow_up").exists()
    # It is made once, so it is not made until the search for hazard ratios is said to be finished.
    assert regenerate(study_dir, dt.date(2029, 5, 2)) == 1
    assert "search for hazard ratios" in capsys.readouterr().out and not (study_dir / "results" / "effect_size_follow_up").exists()
    assert main(["--study", str(study_dir), "--hazard-ratios-searched-on", "2029-05-02"], today=dt.date(2029, 5, 2), services=SERVICES) == 0
    assert regenerate(study_dir, dt.date(2029, 6, 1)) == 0            # regenerated afterwards without being told again
    follow_up_dir = study_dir / "results" / "effect_size_follow_up"
    assert sorted(p.name for p in follow_up_dir.iterdir()) == ["effect_size.csv", "summary.json"]
    summary = json.loads((follow_up_dir / "summary.json").read_text())
    assert (summary["readouts_to"], summary["hazard_ratios_to"]) == ("2028-11-02", "2029-05-02")
    assert [row["analysis"] for row in table(follow_up_dir / "effect_size.csv")] == ["hazard ratios reported", "missing counted as no effect"]
