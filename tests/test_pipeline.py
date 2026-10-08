"""The record pipeline: candidates and forecasts in, a fingerprinted batch out; batches and adjudications in, scores out."""
import datetime as dt
import gzip
import json
import socket

import pytest

from registry_records import study
from trialforecast import records, universe
from trialforecast.adjudication import Adjudication, AdjudicationLog, record_adjudication
from trialforecast.analysis import primary_comparison, study_state
from trialforecast.batch import (
    BatchTrial, InvalidForecast, TamperedBatch, batch_cost, build_batch, read_batch, write_batch,
)
from trialforecast.forecasting import BaseRateForecaster, Forecast
from trialforecast.screening import IneligibleTrial, ScreeningRecord, eligible_trials

from study_records import (
    ANALYSIS_DATE, BASE_RATES, BATCH_1, BATCH_2, HAZARD_RATIOS, SCREENED_ON, FixedForecaster, Unanswering, adjudicated,
    base_rate, both_adjudicated, candidate, screened,
)


# --- forecasts and forecasters ---------------------------------------------------


def test_base_rate_forecaster_issues_the_base_rate_of_the_reference_class():
    forecast = base_rate().forecast(candidate("NCT1", "Progression-free survival"), BATCH_1)
    assert forecast == Forecast(
        nct="NCT1", forecaster="base_rate", version="2026-11", batch_date=BATCH_1,
        probability_positive=0.66, hazard_ratio=0.70, hazard_ratio_low=0.50, hazard_ratio_high=0.98,
    )


def test_base_rate_forecaster_refuses_a_trial_with_no_base_rate():
    forecaster = BaseRateForecaster({}, HAZARD_RATIOS, version="2026-11")
    with pytest.raises(LookupError, match="no base rate for reference class industry/overall_survival"):
        forecaster.forecast(candidate("NCT2"), BATCH_1)
    forecaster = BaseRateForecaster(BASE_RATES, {}, version="2026-11")
    with pytest.raises(LookupError, match="no hazard ratio for reference class industry/overall_survival"):
        forecaster.forecast(candidate("NCT2"), BATCH_1)


def test_a_forecast_must_be_a_probability_and_an_ordered_interval():
    ok = dict(nct="NCT1", forecaster="x", version="1", batch_date=BATCH_1,
              probability_positive=0.5, hazard_ratio=0.8, hazard_ratio_low=0.6, hazard_ratio_high=1.0)
    Forecast(**ok)
    for bad in ({"probability_positive": 1.2}, {"hazard_ratio_low": 0.9}, {"hazard_ratio_high": 0.7},
                {"hazard_ratio_low": 0.0}, {"forecaster": "../escaped"}, {"forecaster": ""},
                {"batch_date": dt.datetime(2026, 11, 2, 9, 0)}, {"batch_date": "2026-11-02"}):
        with pytest.raises(ValueError):
            Forecast(**{**ok, **bad})


def test_equal_forecasts_are_identical_however_their_numbers_were_typed():
    as_ints = Forecast(nct="NCT1", forecaster="x", version="1", batch_date=BATCH_1,
                       probability_positive=1, hazard_ratio=1, hazard_ratio_low=1, hazard_ratio_high=1)
    as_floats = Forecast(nct="NCT1", forecaster="x", version="1", batch_date=BATCH_1,
                         probability_positive=1.0, hazard_ratio=1.0, hazard_ratio_low=1.0, hazard_ratio_high=1.0)
    assert records.to_line(as_ints) == records.to_line(as_floats)


# --- screening -------------------------------------------------------------------


def test_only_a_trial_screened_as_having_no_public_result_is_eligible():
    candidates = [candidate("NCT1"), candidate("NCT2"), candidate("NCT3")]
    log = [screened("NCT1", "eligible"), screened("NCT2", "already_read_out")]  # NCT3 never screened
    assert [c["nct"] for c in eligible_trials(candidates, log, BATCH_1)] == ["NCT1"]


def test_a_trial_that_has_read_out_can_never_be_cleared_again():
    log = [screened("NCT1", "already_read_out", on=dt.date(2026, 10, 1)), screened("NCT1", "eligible")]
    assert eligible_trials([candidate("NCT1")], log, BATCH_1) == []
    assert eligible_trials([candidate("NCT1")], log[::-1], BATCH_1) == []


def test_screening_must_be_recent_and_not_dated_after_the_batch():
    def eligible_with(screened_on):
        return bool(eligible_trials([candidate("NCT1")], [screened("NCT1", "eligible", on=screened_on)], BATCH_1))

    assert eligible_with(BATCH_1)
    assert eligible_with(BATCH_1 - dt.timedelta(days=14))
    assert not eligible_with(BATCH_1 - dt.timedelta(days=15))   # stale: a result may have appeared since
    assert not eligible_with(BATCH_1 + dt.timedelta(days=1))    # screened after the batch date


def test_a_screening_record_needs_a_known_decision_evidence_and_a_plain_date():
    with pytest.raises(ValueError):
        screened("NCT1", "probably fine")
    with pytest.raises(ValueError):
        ScreeningRecord(nct="NCT1", decision="eligible", screened_on=SCREENED_ON, evidence="  ", confidence="high")
    with pytest.raises(ValueError):
        screened("NCT1", "eligible", on=dt.datetime(2026, 10, 30, 12, 0))


# --- batches ---------------------------------------------------------------------


def test_a_batch_cannot_include_a_trial_that_has_already_read_out():
    trials = [candidate("NCT1"), candidate("NCT2")]
    log = [screened("NCT1", "eligible"), screened("NCT2", "already_read_out")]
    with pytest.raises(IneligibleTrial, match="NCT2"):
        build_batch(BATCH_1, trials, log, [base_rate()])


def test_a_batch_cannot_include_a_trial_that_was_never_screened():
    with pytest.raises(IneligibleTrial, match="NCT9"):
        build_batch(BATCH_1, [candidate("NCT9")], [], [base_rate()])


def test_a_batch_holds_every_forecasters_forecast_for_every_trial():
    trials = [candidate("NCT2", "Progression-free survival"), candidate("NCT1")]
    log = [screened("NCT1", "eligible"), screened("NCT2", "eligible")]
    batch = build_batch(BATCH_1, trials, log, [base_rate(), FixedForecaster("stand_in", 0.9)])
    assert set(batch.forecasts) == {"base_rate", "stand_in"}
    assert [f.nct for f in batch.forecasts["base_rate"]] == ["NCT1", "NCT2"]
    assert [f.probability_positive for f in batch.forecasts["base_rate"]] == [0.55, 0.66]
    assert [f.probability_positive for f in batch.forecasts["stand_in"]] == [0.9, 0.9]


def test_a_batch_names_each_trials_scored_endpoint_and_reference_class():
    batch = build_batch(BATCH_1, [candidate("NCT1", "Progression-free survival (PFS)")],
                        [screened("NCT1", "eligible")], [base_rate()])
    (trial,) = batch.trials
    assert (trial.nct, trial.scored_endpoint, trial.sponsor_type, trial.endpoint_type) == (
        "NCT1", "Progression-free survival (PFS)", "industry", "progression")


def test_a_batch_names_each_trials_investigational_drug_and_registry_completion_date():
    trials = [candidate("NCT1", drug="Examplumab 200 mg (EX-101)", pcd="2027-03"), candidate("NCT2")]
    batch = build_batch(BATCH_1, trials, [screened("NCT1", "eligible"), screened("NCT2", "eligible")], [base_rate()])
    first, second = batch.trials
    assert (first.investigational_drug, first.registry_completion_date) == ("examplumab", "2027-03")
    assert second.investigational_drug is None


def test_a_batch_trial_holds_one_spelling_of_a_drug_and_a_registry_date():
    ok = dict(nct="NCT1", scored_endpoint="Overall survival", sponsor_type="industry", endpoint_type="overall_survival")
    BatchTrial(**ok, investigational_drug="examplumab", registry_completion_date="2027-03-31")
    with pytest.raises(ValueError, match="one spelling"):
        BatchTrial(**ok, investigational_drug="Examplumab ")
    with pytest.raises(ValueError, match="registry completion date"):
        BatchTrial(**ok, registry_completion_date="March 2027")


def test_a_batch_rejects_a_forecast_that_is_not_what_was_asked_for():
    class AnswersForAnotherTrial(FixedForecaster):
        def forecast(self, candidate, batch_date):
            return super().forecast({**candidate, "nct": "NCT2"}, batch_date)

    class BackdatesItsForecast(FixedForecaster):
        def forecast(self, candidate, batch_date):
            return super().forecast(candidate, dt.date(2020, 1, 1))

    class SignsAsSomeoneElse(FixedForecaster):
        def forecast(self, candidate, batch_date):
            return FixedForecaster("base_rate", 0.5).forecast(candidate, batch_date)

    log = [screened("NCT1", "eligible")]
    for forecaster in (AnswersForAnotherTrial("stand_in", 0.9), BackdatesItsForecast("stand_in", 0.9),
                       SignsAsSomeoneElse("stand_in", 0.9)):
        with pytest.raises(InvalidForecast):
            build_batch(BATCH_1, [candidate("NCT1")], log, [forecaster])


def test_two_forecasters_cannot_share_a_name():
    with pytest.raises(ValueError, match="stand_in"):
        build_batch(BATCH_1, [candidate("NCT1")], [screened("NCT1", "eligible")],
                    [FixedForecaster("stand_in", 0.2), FixedForecaster("stand_in", 0.9)])


def test_the_fingerprint_covers_everything_in_the_batch_and_ignores_input_order():
    trials = [candidate("NCT1"), candidate("NCT2")]
    log = [screened("NCT1", "eligible"), screened("NCT2", "eligible")]

    def fingerprint(trial_order=trials, stand_in_probability=0.9, batch_date=BATCH_1):
        return build_batch(batch_date, trial_order, log,
                           [base_rate(), FixedForecaster("stand_in", stand_in_probability)]).fingerprint

    original = fingerprint()
    assert len(original) == 64
    assert fingerprint(trial_order=trials[::-1]) == original
    assert fingerprint(stand_in_probability=0.91) != original
    assert fingerprint(batch_date=BATCH_1 + dt.timedelta(days=1)) != original
    # The scored endpoint is named at this point, so changing it changes the fingerprint.
    renamed = [candidate("NCT1", "Overall survival (OS)"), candidate("NCT2")]
    assert fingerprint(trial_order=renamed) != original


def test_a_batch_altered_on_disk_is_refused(tmp_path):
    batch = build_batch(BATCH_1, [candidate("NCT1")], [screened("NCT1", "eligible")],
                        [base_rate(), FixedForecaster("stand_in", 0.2)])
    directory = write_batch(batch, tmp_path)
    assert read_batch(directory) == batch
    altered = directory / "stand_in.jsonl"
    altered.write_text(altered.read_text().replace("0.2", "0.99"))
    with pytest.raises(TamperedBatch):
        read_batch(directory)


# --- primary comparison ----------------------------------------------------------


def test_the_primary_comparison_scores_only_each_trials_first_forecast():
    first_trial, later_trial = candidate("NCT1"), candidate("NCT2")
    log = [screened("NCT1", "eligible"), screened("NCT2", "eligible"),
           screened("NCT1", "eligible", on=BATCH_2), screened("NCT2", "eligible", on=BATCH_2)]
    batches = [
        # Given out of date order on purpose: the first forecast is the earliest issued, not the first listed.
        build_batch(BATCH_2, [first_trial, later_trial], log, [base_rate(), FixedForecaster("stand_in", 0.95, "2")]),
        build_batch(BATCH_1, [first_trial], log, [base_rate(), FixedForecaster("stand_in", 0.2, "1")]),
    ]
    adjudications = both_adjudicated("NCT1", "positive") + both_adjudicated("NCT2", "negative")

    held = study_state(batches, AdjudicationLog(adjudications), ANALYSIS_DATE)
    result = primary_comparison(held, "stand_in", "base_rate")

    assert result["n_trials"] == 2
    # NCT1 positive: first forecast 0.2 -> 0.64 (the later 0.95 is ignored). NCT2 negative: 0.95 -> 0.9025.
    assert result["brier"]["stand_in"] == pytest.approx((0.64 + 0.9025) / 2)
    # Base rate 0.55 for both: 0.2025 and 0.3025.
    assert result["brier"]["base_rate"] == pytest.approx((0.2025 + 0.3025) / 2)


def test_two_batches_on_one_date_make_the_first_forecast_ambiguous():
    log = [screened("NCT1", "eligible")]
    batches = [build_batch(BATCH_1, [candidate("NCT1")], log, [base_rate(), FixedForecaster("stand_in", p)])
               for p in (0.2, 0.95)]
    with pytest.raises(ValueError, match="2026-11-02"):
        study_state(batches, AdjudicationLog(both_adjudicated("NCT1", "positive")), ANALYSIS_DATE)


def test_only_agreed_positive_or_negative_industry_led_trials_are_scored():
    trials = [candidate("NCT1"), candidate("NCT2"), candidate("NCT3"), candidate("NCT4", cls="NIH")]
    log = [screened(c["nct"], "eligible") for c in trials]
    batch = build_batch(BATCH_1, trials, log, [base_rate(), FixedForecaster("stand_in", 0.9)])
    adjudications = [
        *both_adjudicated("NCT1", "positive"),
        *both_adjudicated("NCT2", "void"),               # no readout
        adjudicated("NCT3", "first", "positive"),        # one adjudicator only
        *both_adjudicated("NCT4", "positive"),           # not industry-led: outside the primary analysis set
    ]
    held = study_state([batch], AdjudicationLog(adjudications), ANALYSIS_DATE)
    result = primary_comparison(held, "stand_in", "base_rate")
    assert result["n_trials"] == 1
    assert result["brier"]["stand_in"] == pytest.approx(0.01)
    assert result["awaiting_adjudication"] == {"NCT3": "awaiting second adjudication"}


def test_a_forecast_issued_on_or_after_the_readout_is_reported_and_not_scored():
    trials = [candidate("NCT1"), candidate("NCT2")]
    log = [screened(c["nct"], "eligible") for c in trials]
    batch = build_batch(BATCH_1, trials, log, [base_rate(), FixedForecaster("stand_in", 0.9)])
    adjudications = (both_adjudicated("NCT1", "positive", readout=dt.date(2027, 3, 14))
                     + both_adjudicated("NCT2", "positive", readout=BATCH_1))  # screening missed this readout
    held = study_state([batch], AdjudicationLog(adjudications), ANALYSIS_DATE)
    result = primary_comparison(held, "stand_in", "base_rate")
    assert result["n_trials"] == 1
    assert result["forecast_not_before_readout"] == ["NCT2"]


def test_a_record_of_no_forecast_is_kept_in_the_batch_and_scored_at_the_reference(tmp_path):
    trials = [candidate("NCT1")]
    log = [screened("NCT1", "eligible")]
    batch = build_batch(BATCH_1, trials, log, [base_rate(), Unanswering("stand_in", 0.0)])
    assert read_batch(write_batch(batch, tmp_path)) == batch
    held = study_state([batch], AdjudicationLog(both_adjudicated("NCT1", "positive")), ANALYSIS_DATE)
    result = primary_comparison(held, "stand_in", "base_rate")
    # Declining to forecast earns exactly the reference's score, never a better one.
    assert result["n_trials"] == 1 and result["scored_at_reference"] == {"NCT1": "every run refused"}
    assert result["brier"]["stand_in"] == result["brier"]["base_rate"] == pytest.approx(0.2025)


def test_the_cost_of_a_batch_is_totalled_per_forecaster():
    trials = [candidate("NCT1"), candidate("NCT2")]
    log = [screened("NCT1", "eligible"), screened("NCT2", "eligible")]
    batch = build_batch(BATCH_1, trials, log, [base_rate(), Unanswering("stand_in", 0.0)])
    assert batch_cost(batch) == {
        "base_rate": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
        "stand_in": {"input_tokens": 9000, "output_tokens": 0, "cost_usd": pytest.approx(0.036)},
    }


# --- the whole path, through files, with no network --------------------------------


def test_one_trial_travels_from_snapshot_to_score(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("the record pipeline must not touch the network")

    monkeypatch.setattr(socket, "socket", no_network)

    # A frozen registry snapshot on disk, holding one made-up trial.
    snapshot = tmp_path / "snapshots" / "2026-10-30T090000"
    snapshot.mkdir(parents=True)
    with gzip.open(snapshot / "studies.jsonl.gz", "wt", encoding="utf-8") as f:
        f.write(json.dumps(study("NCT1", "Overall survival")) + "\n")
    (snapshot / "manifest.json").write_text(json.dumps({"data_timestamp_start": "2026-10-30T09:00:00"}))
    table, _ = universe.load_snapshot(snapshot)
    candidates = universe.refine(table, SCREENED_ON).to_dict("records")

    # Screening finds no public result.
    screening_log = tmp_path / "screening.jsonl"
    records.append(screening_log, screened("NCT1", "eligible"))
    screening = records.read(screening_log, ScreeningRecord)
    trials = eligible_trials(candidates, screening, BATCH_1)
    assert [c["nct"] for c in trials] == ["NCT1"]

    # A batch is built and written: one record set per forecaster, one fingerprint over all of them.
    batch = build_batch(BATCH_1, trials, screening, [base_rate(), FixedForecaster("stand_in", 0.8)])
    batch_dir = write_batch(batch, tmp_path / "batches")
    assert sorted(p.name for p in batch_dir.iterdir()) == [
        "_trials.jsonl", "base_rate.jsonl", "manifest.json", "stand_in.jsonl"]
    assert json.loads((batch_dir / "manifest.json").read_text())["fingerprint"] == batch.fingerprint
    read_back = read_batch(batch_dir)
    assert read_back == batch

    # Two adjudicators record the same outcome.
    adjudication_log = tmp_path / "adjudication.jsonl"
    for adjudication in both_adjudicated("NCT1", "positive"):
        record_adjudication(adjudication_log, adjudication, forecast_access=[], today=adjudication.recorded_on)
    adjudications = records.read(adjudication_log, Adjudication)
    assert adjudications == both_adjudicated("NCT1", "positive")

    # The primary comparison scores the first forecasts from the batch read back from disk.
    result = primary_comparison(study_state([read_back], AdjudicationLog(adjudications), ANALYSIS_DATE), "stand_in",
                                "base_rate")
    assert result["n_trials"] == 1
    assert result["brier"]["stand_in"] == pytest.approx(0.04)      # (0.8 - 1)^2
    assert result["brier"]["base_rate"] == pytest.approx(0.2025)   # (0.55 - 1)^2
