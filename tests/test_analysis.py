"""The registered analysis plan: batches and adjudications in, every registered table out."""
import dataclasses
import datetime as dt
import math

import pytest

from study_records import (
    ANALYSIS_DATE, BATCH_1, BATCH_2, EIGHTEEN_MONTHS, PLAN, TWENTY_FOUR_MONTHS, FixedForecaster, Unanswering,
    adjudicated, base_rate, both_adjudicated, candidate, keys_anywhere, screened,
)
from trialforecast import analysis, records, scoring
from trialforecast.adjudication import AdjudicationLog, ForecastAccess, Reconciliation, Withdrawal
from trialforecast.analysis import (
    ALL_SPONSORS, DESCRIPTIVE_LOOK_ON, AlreadyRun, AnalysisRecord, NotDue, NotReady, by_forecaster_version,
    by_lead_time, descriptive_look, effect_size_comparison, final_analysis, forecaster_scores, model_table, paired,
    primary_comparison, sensitivity_analyses, study_state,
)
from trialforecast.batch import build_batch
from trialforecast.forecasting import Forecast

READOUT = dt.date(2027, 3, 14)
OS = "Overall survival"   # the scored endpoint of the made-up trials, as an adjudicator records it
FEW_RESAMPLES = 200  # enough to exercise the bootstrap; the registered number is the default


def batch_of(trials, forecasters, on=BATCH_1):
    screening = [screened(c["nct"], "eligible", on=on - dt.timedelta(days=3)) for c in trials]
    return build_batch(on, trials, screening, forecasters)


def as_of(batches, adjudications, adjudicated_by=ANALYSIS_DATE, readouts_to=None):
    return study_state(batches, AdjudicationLog(adjudications), adjudicated_by, readouts_to)


# --- the primary comparison --------------------------------------------------------


def test_the_primary_comparison_groups_trials_of_one_drug():
    trials = [candidate("NCT1", drug="Examplumab"), candidate("NCT2", drug="examplumab 200 mg"),
              candidate("NCT3", drug="Otherinib"), candidate("NCT4")]
    said = {"NCT1": 0.9, "NCT2": 0.2, "NCT3": 0.8, "NCT4": 0.3}
    batch = batch_of(trials, [base_rate(), FixedForecaster("stand_in", said)])
    adjudications = [*both_adjudicated("NCT1", "positive"), *both_adjudicated("NCT2", "negative"),
                     *both_adjudicated("NCT3", "positive"), *both_adjudicated("NCT4", "negative")]

    result = primary_comparison(as_of([batch], adjudications), "stand_in", "base_rate", n_boot=FEW_RESAMPLES)

    assert (result["n_trials"], result["n_drug_groups"]) == (4, 3)   # a trial with no drug recorded stands alone
    assert result["brier"]["stand_in"] == pytest.approx((0.01 + 0.04 + 0.04 + 0.09) / 4)
    assert result["brier"]["base_rate"] == pytest.approx((0.2025 + 0.3025) / 2)
    # Three drug groups are too few to resample: the difference is given without an interval or a p-value.
    assert result["difference"] == {"mean_diff": pytest.approx(0.045 - 0.2525), "ci_low": None, "ci_high": None,
                                    "p_two_sided": None, "n_trials": 4, "n_clusters": 3}


def test_with_enough_drug_groups_the_difference_has_an_interval_from_resampling_whole_groups():
    batches, log = a_study_of(60, drugs=30, hit_rate=0.8)
    difference = primary_comparison(study_state(batches, log, ANALYSIS_DATE), "stand_in", "base_rate",
                                    n_boot=FEW_RESAMPLES)["difference"]
    assert difference["n_clusters"] == 30 and difference["ci_low"] < difference["mean_diff"] < difference["ci_high"]
    assert 0 < difference["p_two_sided"] <= 1


def test_a_forecaster_renamed_between_batches_cannot_pass_a_later_forecast_off_as_its_first():
    early, late = candidate("NCT1"), candidate("NCT2")
    batches = [
        batch_of([early], [base_rate(), FixedForecaster("old_name", 0.2)]),
        batch_of([early, late], [base_rate(), FixedForecaster("new_name", 0.95)], on=BATCH_2),
    ]
    adjudications = both_adjudicated("NCT1", "positive") + both_adjudicated("NCT2", "positive")

    comparison = paired(as_of(batches, adjudications), "new_name", "base_rate")

    # NCT1 was first sealed before "new_name" existed, so its 0.95 there is not a first forecast.
    assert comparison.scored_at_reference == {"NCT1": "not a forecaster in the batch of 2026-11-02"}
    assert [(p.trial.nct, p.scored.probability_positive) for p in comparison.pairs] == [("NCT1", 0.55), ("NCT2", 0.95)]


def test_a_comparison_needs_a_reference_that_forecast_every_trial():
    batch = batch_of([candidate("NCT1")], [base_rate(), Unanswering("silent", 0.0)])
    with pytest.raises(ValueError, match="silent has no forecast for NCT1"):
        paired(as_of([batch], both_adjudicated("NCT1", "positive")), "base_rate", "silent")


def test_an_analysis_fixed_for_a_date_uses_nothing_sealed_or_disclosed_after_it():
    batches = [batch_of([candidate("NCT1"), candidate("NCT2")], [base_rate()]),
               batch_of([candidate("NCT1"), candidate("NCT2"), candidate("NCT3")], [base_rate()], on=BATCH_2)]
    paper = dict(source_type="paper_or_regulator", source="https://example.test/paper")
    adjudications = (both_adjudicated("NCT1", "positive", readout=dt.date(2026, 11, 20))
                     # A paper after the date reverses NCT1; it is adjudicated, but outside this analysis.
                     + both_adjudicated("NCT1", "negative", readout=dt.date(2027, 2, 1), **paper)
                     + both_adjudicated("NCT2", "positive", readout=dt.date(2027, 1, 5)))
    held = as_of(batches, adjudications, readouts_to=dt.date(2026, 11, 30))
    assert [b.batch_date for b in held.batches] == [BATCH_1]
    assert {nct: r.outcome for nct, r in held.results.items()} == {"NCT1": "positive"}
    assert as_of(batches, adjudications).results["NCT1"].outcome == "negative"


# --- every forecaster's scores -------------------------------------------------------


def test_every_forecaster_is_scored_for_calibration_and_discrimination_and_by_a_second_rule():
    trials = [candidate(f"NCT{i}") for i in range(1, 5)]
    said = {"NCT1": 0.9, "NCT2": 0.8, "NCT3": 0.3, "NCT4": 0.2}
    batch = batch_of(trials, [base_rate(), FixedForecaster("stand_in", said), Unanswering("silent", 0.0)])
    adjudications = [*both_adjudicated("NCT1", "positive"), *both_adjudicated("NCT2", "positive"),
                     *both_adjudicated("NCT3", "negative"), *both_adjudicated("NCT4", "negative")]

    table = forecaster_scores(as_of([batch], adjudications), "base_rate")

    assert sorted(table) == ["base_rate", "silent", "stand_in"]
    sharp = table["stand_in"]
    assert sharp["n_trials"] == 4 and sharp["scored_at_reference"] == 0
    assert sharp["brier"] == pytest.approx((0.01 + 0.04 + 0.09 + 0.04) / 4)
    assert sharp["log_score"] == pytest.approx(-(math.log(0.9) + math.log(0.8) + math.log(0.7) + math.log(0.8)) / 4)
    assert sharp["auc"] == 1.0
    # Each forecast sits alone in its bin, 0.1 or 0.2 from what happened: reliability is the mean squared gap.
    assert sharp["reliability"] == pytest.approx((0.01 + 0.04 + 0.09 + 0.04) / 4)
    assert [(row["n"], row["mean_forecast"], row["share_positive"]) for row in sharp["calibration"]] == [
        (1, pytest.approx(0.2), 0.0), (1, pytest.approx(0.3), 0.0), (1, pytest.approx(0.8), 1.0), (1, pytest.approx(0.9), 1.0)]
    # A forecaster with no forecasts earns exactly the reference's scores.
    assert {k: v for k, v in table["silent"].items() if k != "scored_at_reference"} == {
        k: v for k, v in table["base_rate"].items() if k != "scored_at_reference"}
    assert table["silent"]["scored_at_reference"] == 4


def test_declining_its_misses_cannot_make_a_forecaster_look_more_discriminating():
    class DeclinesItsMisses(FixedForecaster):
        def forecast(self, candidate, batch_date):
            if candidate["nct"] in ("NCT2", "NCT3"):
                return Unanswering(self.name, 0.0).forecast(candidate, batch_date)
            return super().forecast(candidate, batch_date)

    trials = [candidate(f"NCT{i}") for i in range(1, 5)]
    said = {"NCT1": 0.9, "NCT2": 0.2, "NCT3": 0.8, "NCT4": 0.1}    # wrong about NCT2 and NCT3
    batch = batch_of(trials, [base_rate(), FixedForecaster("honest", said), DeclinesItsMisses("selective", said)])
    adjudications = [*both_adjudicated("NCT1", "positive"), *both_adjudicated("NCT2", "positive"),
                     *both_adjudicated("NCT3", "negative"), *both_adjudicated("NCT4", "negative")]
    table = forecaster_scores(as_of([batch], adjudications), "base_rate")
    assert table["honest"]["auc"] == 0.75
    # Declined trials stay in, at the base rate, where they tie with each other. Left out, the two trials
    # that remain would be ranked perfectly and the declining forecaster would show an AUC of 1.
    assert table["selective"]["auc"] == 0.875 and table["selective"]["scored_at_reference"] == 2
    assert table["selective"]["n_trials"] == 4


def test_all_sponsor_scores_cover_trials_outside_the_primary_analysis_set():
    batch = batch_of([candidate("NCT1"), candidate("NCT2", cls="NIH")], [base_rate(), FixedForecaster("stand_in", 0.9)])
    held = as_of([batch], both_adjudicated("NCT1", "positive") + both_adjudicated("NCT2", "positive"))
    assert forecaster_scores(held, "base_rate")["stand_in"]["n_trials"] == 1
    assert forecaster_scores(held, "base_rate", sponsor_type=ALL_SPONSORS)["stand_in"]["n_trials"] == 2


# --- effect size -------------------------------------------------------------------


def hazard_ratio_reading(nct, hazard_ratio, endpoint=OS, outcome="positive", **reading):
    return both_adjudicated(nct, outcome, hazard_ratio=hazard_ratio, hazard_ratio_endpoint=endpoint, **reading)


def test_hazard_ratio_forecasts_are_scored_on_the_log_scale_against_a_baseline():
    close = FixedForecaster("stand_in", 0.7, hazard_ratio=(0.70, 0.60, 0.82))
    batch = batch_of([candidate("NCT1")], [base_rate(), close])

    result = effect_size_comparison(as_of([batch], hazard_ratio_reading("NCT1", 0.72)), "stand_in", "base_rate",
                                    n_boot=FEW_RESAMPLES)

    z = 1.2815515655446004  # the 90th centile of a standard normal: half an 80% interval
    observed = math.log(0.72)
    expected = {
        "stand_in": scoring.crps_normal(math.log(0.70), (math.log(0.82) - math.log(0.60)) / (2 * z), observed),
        "base_rate": scoring.crps_normal(math.log(0.84), (math.log(1.07) - math.log(0.66)) / (2 * z), observed),
    }
    assert result["n_trials"] == 1
    for name in ("stand_in", "base_rate"):
        assert result["crps"][name] == pytest.approx(float(expected[name]))
        assert result["coverage"][name] == 1.0
    assert result["crps"]["stand_in"] < result["crps"]["base_rate"]
    assert result["interval_score"]["stand_in"] == pytest.approx(math.log(0.82) - math.log(0.60))
    assert result["difference"]["mean_diff"] == pytest.approx(float(expected["stand_in"] - expected["base_rate"]))


def test_a_hazard_ratio_is_scored_only_when_recorded_under_the_scored_endpoints_own_name():
    trials = [candidate(f"NCT{i}") for i in range(1, 6)]
    batch = batch_of(trials, [base_rate(), FixedForecaster("stand_in", 0.7)])
    adjudications = [
        *hazard_ratio_reading("NCT1", 0.72, endpoint="overall  survival"),            # the same words
        *hazard_ratio_reading("NCT2", 0.60, endpoint="Progression-free survival", readout=dt.date(2026, 12, 1)),
        *hazard_ratio_reading("NCT3", 0.80, endpoint="Overall survival in the PD-L1 high subgroup", readout=dt.date(2026, 12, 1)),
        *both_adjudicated("NCT4", "negative", readout=dt.date(2026, 12, 1)),          # none reported within six months
        *both_adjudicated("NCT5", "positive", readout=dt.date(2028, 4, 1)),           # still within its six months
    ]
    result = effect_size_comparison(as_of([batch], adjudications), "stand_in", "base_rate", n_boot=FEW_RESAMPLES)
    assert result["n_trials"] == 1
    assert result["hazard_ratio_for_another_endpoint"] == ["NCT2", "NCT3"]
    assert result["hazard_ratio_missing"] == ["NCT4"] and result["hazard_ratio_awaited"] == ["NCT5"]


def test_a_hazard_ratio_for_another_endpoint_that_came_first_is_passed_over():
    batch = batch_of([candidate("NCT1")], [base_rate(), FixedForecaster("stand_in", 0.7)])
    conference = dict(source_type="conference", source="https://example.test/congress")
    adjudications = (hazard_ratio_reading("NCT1", 0.55, endpoint="Progression-free survival")
                     + hazard_ratio_reading("NCT1", 0.78, readout=READOUT + dt.timedelta(days=50), **conference)
                     # A later paper's figure is not the first reported for the scored endpoint.
                     + hazard_ratio_reading("NCT1", 0.81, readout=READOUT + dt.timedelta(days=120),
                                            source_type="paper_or_regulator", source="https://example.test/paper"))
    held = as_of([batch], adjudications)
    trial = held.batches[0].trials[0]
    assert analysis.scored_hazard_ratio(held.results["NCT1"], trial, held.readouts_to) == (0.78, "reported")
    assert effect_size_comparison(held, "stand_in", "base_rate", n_boot=FEW_RESAMPLES)["n_trials"] == 1


def test_a_forecaster_with_no_forecast_is_scored_at_the_baselines_hazard_ratio():
    batch = batch_of([candidate("NCT1")], [base_rate(), Unanswering("stand_in", 0.0)])
    result = effect_size_comparison(as_of([batch], hazard_ratio_reading("NCT1", 0.72)), "stand_in", "base_rate",
                                    n_boot=FEW_RESAMPLES)
    assert result["scored_at_baseline"] == {"NCT1": "every run refused"}
    assert result["crps"]["stand_in"] == result["crps"]["base_rate"]
    assert result["difference"]["mean_diff"] == 0.0


# --- secondary and sensitivity analyses -----------------------------------------------


def test_each_sensitivity_analysis_changes_only_what_it_names():
    trials = [
        candidate("NCT1"),                              # industry, positive, English
        candidate("NCT2", cls="NIH"),                   # not industry-led, negative
        candidate("NCT3"),                              # void
        candidate("NCT4"),                              # positive, disclosed in Japanese
        candidate("NCT5", pcd="2027-06"),               # no readout found, registry date long past
        candidate("NCT6", pcd="2029-01"),               # no readout found, not yet due
        candidate("NCT7", pcd="2027-06"),               # one adjudication only: awaiting, never imputed
    ]
    early = batch_of(trials, [base_rate(), FixedForecaster("stand_in", 0.9)])
    late = batch_of(trials, [base_rate(), FixedForecaster("stand_in", 0.6)], on=BATCH_2)
    adjudications = [
        *both_adjudicated("NCT1", "positive"), *both_adjudicated("NCT2", "negative"), *both_adjudicated("NCT3", "void"),
        *both_adjudicated("NCT4", "positive", language="ja", original_text="主要評価項目を達成", translation="Met its primary endpoint."),
        adjudicated("NCT7", "first", "positive"),
    ]
    held = as_of([early, late], adjudications)

    primary = primary_comparison(held, "stand_in", "base_rate", n_boot=FEW_RESAMPLES)
    analyses = sensitivity_analyses(held, held, "stand_in", "base_rate", n_boot=FEW_RESAMPLES)

    # First forecasts were 0.9: a positive trial scores 0.01, a negative or void one 0.81. Last forecasts were 0.6.
    assert (primary["n_trials"], primary["brier"]["stand_in"]) == (2, pytest.approx(0.01))
    expected = {
        "all sponsors": (3, (0.01 + 0.81 + 0.01) / 3),
        "last forecast before readout": (2, 0.16),
        "without non-English disclosures": (1, 0.01),
        "void counted as negative": (3, (0.01 + 0.81 + 0.01) / 3),
        "unresolved imputed as negative": (3, (0.01 + 0.01 + 0.81) / 3),
        "unresolved imputed as positive": (3, 0.01),
        "with sources read after the forecasts were opened": (2, 0.01),     # none were, here
    }
    assert sorted(analyses) == sorted(expected)
    for name, (n_trials, brier) in expected.items():
        assert (name, analyses[name]["n_trials"]) == (name, n_trials)
        assert analyses[name]["brier"]["stand_in"] == pytest.approx(brier), name
        assert analyses[name]["difference"]["n_trials"] == n_trials


def test_the_last_forecast_before_readout_ignores_batches_sealed_after_it():
    trial = candidate("NCT1")
    after_readout = dt.date(2027, 4, 1)
    batches = [batch_of([trial], [base_rate(), FixedForecaster("stand_in", p)], on=on)
               for p, on in ((0.2, BATCH_1), (0.6, BATCH_2), (0.99, after_readout))]
    held = as_of(batches, both_adjudicated("NCT1", "positive"))

    first = paired(held, "stand_in", "base_rate").pairs[0]
    last = paired(held, "stand_in", "base_rate", last_forecast=True).pairs[0]

    assert (first.scored.probability_positive, last.scored.probability_positive) == (0.2, 0.6)
    assert (first.lead_days, last.lead_days) == ((READOUT - BATCH_1).days, (READOUT - BATCH_2).days)


def test_an_unresolved_trial_is_imputed_only_once_its_whole_registry_month_has_passed():
    batch = batch_of([candidate("NCT1", pcd="2027-06"), candidate("NCT2", pcd="2027-06-10")],
                     [base_rate(), FixedForecaster("stand_in", 0.9)])

    def imputed(on):
        return [p.trial.nct for p in paired(as_of([batch], [], on), "stand_in", "base_rate", impute_unresolved="negative").pairs]

    assert imputed(dt.date(2027, 6, 9)) == []
    assert imputed(dt.date(2027, 6, 29)) == ["NCT2"]
    assert imputed(dt.date(2027, 6, 30)) == ["NCT1", "NCT2"]
    with pytest.raises(ValueError, match="negative or as positive"):
        paired(as_of([batch], []), "stand_in", "base_rate", impute_unresolved=False)


def test_a_void_trial_made_known_before_its_first_sealing_is_never_scored():
    batch = batch_of([candidate("NCT1")], [base_rate(), FixedForecaster("stand_in", 0.9)])
    before, after = dt.date(2026, 10, 20), dt.date(2027, 3, 1)
    adjudications = (both_adjudicated("NCT1", "void", readout=before, source="https://example.test/first-notice")
                     + both_adjudicated("NCT1", "void", readout=after))
    comparison = paired(as_of([batch], adjudications), "stand_in", "base_rate", void_as_negative=True)
    assert comparison.pairs == () and comparison.forecast_not_before_readout == ("NCT1",)


def test_accuracy_is_reported_by_lead_time_and_by_forecaster_version():
    soon, later = candidate("NCT1"), candidate("NCT2")
    batches = [batch_of([soon], [base_rate(), FixedForecaster("stand_in", 0.9, version="1")]),
               batch_of([soon, later], [base_rate(), FixedForecaster("stand_in", 0.4, version="2")], on=BATCH_2)]
    adjudications = (both_adjudicated("NCT1", "positive", readout=dt.date(2027, 1, 10))    # 69 days after its first forecast
                     + both_adjudicated("NCT2", "negative", readout=dt.date(2028, 2, 1)))  # over a year after
    held = as_of(batches, adjudications)

    bands = {row["lead_time"]: row for row in by_lead_time(held, "stand_in", "base_rate")}
    assert [bands[b]["n_trials"] for b in ("under 3 months", "3 to 6 months", "6 to 12 months", "over 12 months")] == [1, 0, 0, 1]
    assert bands["under 3 months"]["brier"]["stand_in"] == pytest.approx(0.01)
    assert bands["3 to 6 months"]["brier"]["stand_in"] is None

    versions = {row["version"]: row for row in by_forecaster_version(held, "stand_in", "base_rate")}
    assert sorted(versions) == ["1", "2"]
    assert versions["2"]["n_trials"] == 1 and versions["2"]["brier"]["stand_in"] == pytest.approx(0.16)


@pytest.mark.parametrize("days, band", [(90, "under 3 months"), (91, "3 to 6 months"), (182, "3 to 6 months"),
                                        (183, "6 to 12 months"), (365, "6 to 12 months"), (366, "over 12 months")])
def test_a_lead_time_band_starts_on_its_first_day(days, band):
    batch = batch_of([candidate("NCT1")], [base_rate(), FixedForecaster("stand_in", 0.9)])
    held = as_of([batch], both_adjudicated("NCT1", "positive", readout=BATCH_1 + dt.timedelta(days=days)))
    assert [row["lead_time"] for row in by_lead_time(held, "stand_in", "base_rate") if row["n_trials"]] == [band]


# --- one row per model ---------------------------------------------------------------


class AModel(FixedForecaster):
    """A stand-in for a frontier model as shipped: its forecasts record the model and when it was used."""

    served = "example-1-20260901"

    def forecast(self, candidate, batch_date):
        plain = super().forecast(candidate, batch_date)
        return dataclasses.replace(plain, model="example-1", model_served=self.served, model_training_cutoff="2026-06",
                                   model_released_on=dt.date(2026, 9, 21), used_on=batch_date)


def test_each_model_is_shown_with_its_cutoff_its_dates_of_use_and_the_readouts_it_is_scored_on():
    class JoinsLate(AModel):
        def forecast(self, candidate, batch_date):
            if batch_date == BATCH_1:
                return Unanswering(self.name, 0.0).forecast(candidate, batch_date)
            return super().forecast(candidate, batch_date)

    class Updated(AModel):
        served = "example-1-20261101"

    trials = [candidate("NCT1"), candidate("NCT2"), candidate("NCT3", cls="NIH")]
    batches = [batch_of(trials[:2], [base_rate(), AModel("a_model", 0.6), JoinsLate("late_model", 0.6)]),
               batch_of(trials, [base_rate(), Updated("a_model", 0.6), JoinsLate("late_model", 0.6)], on=BATCH_2)]
    adjudications = (both_adjudicated("NCT1", "positive", readout=dt.date(2027, 1, 10))
                     + both_adjudicated("NCT3", "negative", readout=dt.date(2027, 9, 2)))
    a_model, late_model = model_table(as_of(batches, adjudications))
    assert a_model == {
        "forecaster": "a_model", "model": "example-1",
        "model_served": "example-1-20260901; example-1-20261101",    # a change mid-study is shown, not hidden
        "training_cutoff": "2026-06", "released_on": dt.date(2026, 9, 21),
        "first_used_on": BATCH_1, "last_used_on": BATCH_2,
        "trials_scored": 2, "earliest_readout_scored": dt.date(2027, 1, 10), "latest_readout_scored": dt.date(2027, 9, 2),
    }
    # Its first record for NCT1 was of no forecast, but its later forecast is scored as the last before readout.
    assert (late_model["trials_scored"], late_model["earliest_readout_scored"]) == (2, dt.date(2027, 1, 10))


# --- the descriptive look ------------------------------------------------------------


def a_small_study():
    trials = [candidate(f"NCT{i}") for i in range(1, 5)]
    batch = batch_of(trials, [base_rate(), FixedForecaster("stand_in", {"NCT1": 0.9, "NCT2": 0.2, "NCT3": 0.7, "NCT4": 0.6})])
    adjudications = (both_adjudicated("NCT1", "positive", readout=dt.date(2027, 2, 1))
                     + both_adjudicated("NCT2", "negative", readout=dt.date(2027, 3, 1))
                     + both_adjudicated("NCT3", "positive", readout=dt.date(2027, 5, 20))    # after the look
                     + [adjudicated("NCT4", "first", "positive", readout=dt.date(2027, 4, 1))])  # read once so far
    return [batch], AdjudicationLog(adjudications)


def test_the_descriptive_look_reports_scores_and_tests_nothing(tmp_path):
    batches, log = a_small_study()
    with pytest.raises(NotDue):
        descriptive_look(batches, log, PLAN, DESCRIPTIVE_LOOK_ON - dt.timedelta(days=1), tmp_path / "analyses.jsonl")

    look = descriptive_look(batches, log, PLAN, dt.date(2027, 6, 1), tmp_path / "analyses.jsonl")

    assert look["n_trials"] == 2  # NCT3 read out after the look's fixed date, though before the day it was run
    assert look["forecasters"]["stand_in"]["brier"] == pytest.approx((0.01 + 0.04) / 2)
    assert look["awaiting_adjudication"] == {"NCT4": "awaiting second adjudication"}
    assert not keys_anywhere(look) & {"difference", "mean_diff", "ci_low", "ci_high", "p_two_sided", "claim_supported"}


def test_the_descriptive_look_is_made_once(tmp_path):
    batches, log = a_small_study()
    record_file = tmp_path / "analyses.jsonl"
    look = descriptive_look(batches, log, PLAN, dt.date(2027, 4, 20), record_file)
    assert look["n_trials"] == 2
    # NCT4 read out before the look and its second adjudication arrives afterwards: on a first run this would
    # make a third trial, but the look already made is regenerated as it was.
    late_second_reading = adjudicated("NCT4", "second", "positive", readout=dt.date(2027, 4, 1), recorded_on=dt.date(2027, 4, 20))
    grown = AdjudicationLog([*log.adjudications, late_second_reading])
    assert descriptive_look(batches, grown, PLAN, dt.date(2027, 9, 1), record_file) == look
    assert descriptive_look(batches, grown, PLAN, dt.date(2027, 9, 1), tmp_path / "another.jsonl")["n_trials"] == 3
    assert [r.kind for r in records.read(record_file, AnalysisRecord)] == ["descriptive_look"]
    # But not on a log whose earlier entries have changed underneath it.
    rewritten = AdjudicationLog([a if a.nct != "NCT2" else adjudicated("NCT2", a.adjudicator, "positive", readout=dt.date(2027, 3, 1))
                                 for a in log.adjudications])
    with pytest.raises(AlreadyRun):
        descriptive_look(batches, rewritten, PLAN, dt.date(2027, 9, 1), record_file)
    with pytest.raises(AlreadyRun, match="fewer entries"):
        descriptive_look(batches, AdjudicationLog(log.adjudications[:-1]), PLAN, dt.date(2027, 9, 1), record_file)


# --- the final analysis ---------------------------------------------------------------


def a_study_of(n_trials, readout=dt.date(2027, 8, 1), hit_rate=1.0, drugs=None):
    """A study in which every trial read out. The stand-in forecaster is right about `hit_rate` of the trials."""
    ncts = [f"NCT{i:04d}" for i in range(1, n_trials + 1)]
    positive = {nct: i % 3 != 0 for i, nct in enumerate(ncts)}
    right = {nct: (i * 7919) % 100 < hit_rate * 100 for i, nct in enumerate(ncts)}
    said = {nct: 0.8 if positive[nct] == right[nct] else 0.3 for nct in ncts}
    batch = batch_of([candidate(nct, drug=f"drug{i % (drugs or n_trials // 2)}") for i, nct in enumerate(ncts)],
                     [base_rate(), FixedForecaster("stand_in", said)])
    adjudications = [a for nct in ncts
                     for a in both_adjudicated(nct, "positive" if positive[nct] else "negative", readout=readout,
                                               hazard_ratio=0.7 if positive[nct] else 0.95, hazard_ratio_endpoint=OS)]
    return [batch], AdjudicationLog(adjudications)


def run_final(study, today, record_file, screening=(), plan=PLAN, n_boot=FEW_RESAMPLES):
    batches, log = study
    return final_analysis(batches, log, screening, plan, today, record_file, n_boot=n_boot)


def test_the_final_analysis_cannot_run_before_its_date(tmp_path):
    with pytest.raises(NotDue, match="2028-05-02"):
        run_final(a_study_of(4), EIGHTEEN_MONTHS - dt.timedelta(days=1), tmp_path / "analyses.jsonl")


def test_with_enough_trials_the_claim_is_tested_at_eighteen_months(tmp_path):
    final = run_final(a_study_of(120), EIGHTEEN_MONTHS, tmp_path / "analyses.jsonl")

    assert (final["decision"], final["extended"], final["readouts_to"]) == ("tested", False, EIGHTEEN_MONTHS)
    assert final["primary"]["n_trials"] == 120 and final["primary"]["n_drug_groups"] == 60
    assert final["primary"]["difference"]["ci_high"] < 0 and final["claim_supported"] is True
    assert set(final) >= {"forecasters", "forecasters_all_sponsors", "effect_size", "sensitivity", "lead_time",
                          "versions", "models"}
    assert final["effect_size"]["base_rate"]["n_trials"] == 120


def test_the_claim_is_supported_only_when_the_whole_interval_favours_the_forecaster(tmp_path):
    # Right about 62% of trials: better than the base rate on average, but not clearly.
    final = run_final(a_study_of(120, hit_rate=0.62), EIGHTEEN_MONTHS, tmp_path / "analyses.jsonl")
    difference = final["primary"]["difference"]
    assert difference["mean_diff"] < 0 < difference["ci_high"]
    assert final["decision"] == "tested" and final["claim_supported"] is False


def test_one_trial_short_of_the_number_needed_extends_the_study_and_shows_no_scores(tmp_path):
    study = a_study_of(119)
    record_file = tmp_path / "analyses.jsonl"

    at_eighteen = run_final(study, EIGHTEEN_MONTHS, record_file)

    assert at_eighteen == {"kind": "final_analysis", "decision": "extended", "n_trials": 119,
                           "run_on": EIGHTEEN_MONTHS, "readouts_to": TWENTY_FOUR_MONTHS}
    with pytest.raises(NotDue, match="2028-11-02"):
        run_final(study, dt.date(2028, 8, 1), record_file)

    at_twenty_four = run_final(study, TWENTY_FOUR_MONTHS, record_file)
    assert (at_twenty_four["decision"], at_twenty_four["extended"]) == ("tested", True)
    assert [r.kind for r in records.read(record_file, AnalysisRecord)] == ["extension", "final_analysis"]


@pytest.mark.parametrize("n_trials, decision", [(60, "tested"), (59, "estimate_only")])
def test_after_the_extension_sixty_trials_are_needed_to_make_the_claim(tmp_path, n_trials, decision):
    study = a_study_of(n_trials, drugs=40)
    record_file = tmp_path / "analyses.jsonl"
    assert run_final(study, EIGHTEEN_MONTHS, record_file)["decision"] == "extended"

    final = run_final(study, TWENTY_FOUR_MONTHS, record_file)

    assert final["decision"] == decision
    difference = final["primary"]["difference"]
    assert difference["ci_low"] < difference["mean_diff"] < difference["ci_high"]    # an estimate with its uncertainty
    if decision == "estimate_only":
        assert final["claim_supported"] is None and "p_two_sided" not in keys_anywhere(final)


def test_no_claim_rests_on_fewer_than_thirty_drug_groups(tmp_path):
    # 120 trials of one drug: resampling one group gives an interval of no width, which proves nothing.
    final = run_final(a_study_of(120, drugs=1), EIGHTEEN_MONTHS, tmp_path / "analyses.jsonl")
    assert final["primary"]["n_drug_groups"] == 1
    assert (final["decision"], final["claim_supported"]) == ("estimate_only", None)
    assert final["primary"]["difference"]["ci_high"] is None
    # The same floor holds for every comparison in the analysis, not only the primary one.
    assert all(a["difference"]["ci_high"] is None for a in final["sensitivity"].values())
    assert final["effect_size"]["base_rate"]["difference"]["ci_high"] is None
    assert run_final(a_study_of(120, drugs=30), EIGHTEEN_MONTHS, tmp_path / "other.jsonl")["decision"] == "tested"


def test_the_day_the_final_analysis_is_run_decides_nothing(tmp_path):
    batches, log = a_study_of(120)
    # A paper after the fixed date reverses one trial, and is adjudicated before a late run.
    paper = both_adjudicated("NCT0002", "negative", readout=EIGHTEEN_MONTHS + dt.timedelta(days=20),
                             source_type="paper_or_regulator", source="https://example.test/paper")
    on_time = run_final((batches, log), EIGHTEEN_MONTHS, tmp_path / "on_time.jsonl")
    late = run_final((batches, AdjudicationLog([*log.adjudications, *paper])), EIGHTEEN_MONTHS + dt.timedelta(days=60),
                     tmp_path / "late.jsonl")
    assert late["primary"] == on_time["primary"]


def test_readouts_after_the_fixed_date_do_not_count_towards_the_final_analysis(tmp_path):
    late_run = EIGHTEEN_MONTHS + dt.timedelta(days=30)
    assert run_final(a_study_of(120, readout=EIGHTEEN_MONTHS + dt.timedelta(days=1)), late_run, tmp_path / "a.jsonl") == {
        "kind": "final_analysis", "decision": "extended", "n_trials": 0, "run_on": late_run,
        "readouts_to": TWENTY_FOUR_MONTHS}


def test_the_final_analysis_waits_until_every_sealed_trial_is_accounted_for(tmp_path):
    batches, log = a_study_of(120)
    record_file = tmp_path / "analyses.jsonl"

    # One trial read once only.
    with pytest.raises(NotReady, match="NCT0120"):
        run_final((batches, AdjudicationLog(log.adjudications[:-1])), EIGHTEEN_MONTHS, record_file)

    # Five trials with nothing recorded at all: run early, they would simply not be counted and the study would extend.
    not_looked_at = AdjudicationLog([a for a in log.adjudications if a.nct > "NCT0005"])
    with pytest.raises(NotReady, match="NCT0001, NCT0002, NCT0003, NCT0004, NCT0005"):
        run_final((batches, not_looked_at), EIGHTEEN_MONTHS, record_file)
    too_early = [screened(f"NCT000{i}", "eligible", on=EIGHTEEN_MONTHS - dt.timedelta(days=1)) for i in range(1, 6)]
    with pytest.raises(NotReady):
        run_final((batches, not_looked_at), EIGHTEEN_MONTHS, record_file, screening=too_early)
    assert not record_file.exists()
    # Screened on or after the date and found without a public result, they are accounted for.
    looked_at = [screened(f"NCT000{i}", "eligible", on=EIGHTEEN_MONTHS) for i in range(1, 6)]
    assert run_final((batches, not_looked_at), EIGHTEEN_MONTHS, record_file, screening=looked_at)["n_trials"] == 115


def test_a_trial_cannot_be_removed_from_the_final_analysis_by_recording_that_its_forecasts_were_opened(tmp_path):
    batches, log = a_study_of(120)
    opened = [ForecastAccess(nct="NCT0001", person="first", opened_on=dt.date(2027, 7, 1))]
    marked = AdjudicationLog(log.adjudications, forecast_access=opened)
    with pytest.raises(NotReady, match="NCT0001 .adjudicated after opening the forecasts."):
        run_final((batches, marked), EIGHTEEN_MONTHS, tmp_path / "analyses.jsonl")


def test_the_final_analysis_runs_once(tmp_path):
    batches, log = a_study_of(120)
    record_file = tmp_path / "analyses.jsonl"
    final = run_final((batches, log), EIGHTEEN_MONTHS, record_file)
    later = dt.date(2028, 7, 1)

    # Regenerating its tables is allowed and changes nothing: not a later day, more resamples, or a longer log.
    grown = AdjudicationLog([*log.adjudications, *both_adjudicated("NCT0001", "negative", readout=later, source="https://example.test/again")])
    assert run_final((batches, grown), later, record_file, n_boot=5 * FEW_RESAMPLES) == final
    # Running it on anything else is not: other adjudications, another plan, or other forecasts.
    flipped = AdjudicationLog([a if a.nct != "NCT0001" else adjudicated("NCT0001", a.adjudicator, "negative", readout=dt.date(2027, 8, 1))
                               for a in log.adjudications])
    with pytest.raises(AlreadyRun):
        run_final((batches, flipped), later, record_file)
    with pytest.raises(AlreadyRun):
        run_final((batches, log), later, record_file, plan=dataclasses.replace(PLAN, effect_size_baselines=("base_rate", "other")))
    with pytest.raises(AlreadyRun):
        run_final((a_study_of(121)[0], log), later, record_file)


def test_every_kind_of_log_entry_is_part_of_what_the_final_analysis_was_run_on(tmp_path):
    batches, log = a_study_of(120)
    mistaken = adjudicated("NCT0001", "first", "negative", readout=dt.date(2027, 8, 1), source="https://example.test/wrong-trial")
    withdrawn = Withdrawal(nct="NCT0001", adjudicator="first", source_type="press_release_or_filing",
                           source="https://example.test/wrong-trial", reason="about another trial", recorded_on=dt.date(2027, 8, 2))
    opened = ForecastAccess(nct="NCT0001", person="first", opened_on=dt.date(2028, 4, 1))
    whole = AdjudicationLog([*log.adjudications, mistaken], withdrawals=[withdrawn], forecast_access=[opened])
    record_file = tmp_path / "analyses.jsonl"
    run_final((batches, whole), EIGHTEEN_MONTHS, record_file)
    for kind, changed in (("withdrawals", dataclasses.replace(withdrawn, reason="another reason")),
                          ("forecast_access", dataclasses.replace(opened, opened_on=dt.date(2028, 4, 2)))):
        with pytest.raises(AlreadyRun):
            run_final((batches, dataclasses.replace(whole, **{kind: [changed]})), EIGHTEEN_MONTHS, record_file)


def test_two_reconciliations_recorded_in_another_order_are_not_the_log_the_analysis_was_run_on(tmp_path):
    batches, log = a_study_of(120)
    readout = dt.date(2027, 8, 1)
    disputed = [a if (a.nct, a.adjudicator) != ("NCT0002", "second") else adjudicated("NCT0002", "second", "negative", readout=readout)
                for a in log.adjudications]

    def settle(outcome):
        return Reconciliation(nct="NCT0002", source_type="press_release_or_filing", source="https://example.test/topline",
                              outcome=outcome, hazard_ratio=None, hazard_ratio_endpoint=None, disclosed_on=readout,
                              reason=f"read again: {outcome}", adjudicators=("first", "second"), recorded_on=readout)

    record_file = tmp_path / "analyses.jsonl"
    run_final((batches, AdjudicationLog(disputed, [settle("positive"), settle("negative")])), EIGHTEEN_MONTHS, record_file)
    with pytest.raises(AlreadyRun):
        run_final((batches, AdjudicationLog(disputed, [settle("negative"), settle("positive")])), EIGHTEEN_MONTHS, record_file)


def test_a_recorded_extension_must_follow_from_what_it_was_decided_on(tmp_path):
    study = a_study_of(80)
    record_file = tmp_path / "analyses.jsonl"
    run_final(study, EIGHTEEN_MONTHS, record_file)
    (honest,) = records.read(record_file, AnalysisRecord)
    for forged in (dataclasses.replace(honest, n_trials=500), dataclasses.replace(honest, inputs_sha256="00" * 32),
                   dataclasses.replace(honest, run_on=dt.date(2027, 1, 1)),
                   dataclasses.replace(honest, readouts_to=dt.date(2030, 1, 1))):
        forged_file = tmp_path / f"forged-{forged.n_trials}-{forged.run_on}-{forged.readouts_to}-{forged.inputs_sha256[:2]}.jsonl"
        records.append(forged_file, forged)
        with pytest.raises(AlreadyRun, match="does not follow"):
            run_final(study, TWENTY_FOUR_MONTHS, forged_file)
    # An extension written by hand for a study that had enough trials is refused as well: here because the
    # log holds adjudications, dated before the extension, that the record says were not there.
    enough = a_study_of(120)
    records.append(tmp_path / "invented.jsonl", dataclasses.replace(honest, batches=(enough[0][0].fingerprint,)))
    with pytest.raises(AlreadyRun, match="dated before"):
        run_final(enough, TWENTY_FOUR_MONTHS, tmp_path / "invented.jsonl")


def test_a_final_analysis_that_cannot_be_completed_is_not_recorded_as_run(tmp_path):
    record_file = tmp_path / "analyses.jsonl"
    with pytest.raises(ValueError, match="never_sealed"):
        run_final(a_study_of(120), EIGHTEEN_MONTHS, record_file, plan=dataclasses.replace(PLAN, effect_size_baselines=("never_sealed",)))
    assert not record_file.exists()
    assert run_final(a_study_of(120), EIGHTEEN_MONTHS, record_file)["decision"] == "tested"


# --- found by the second review ------------------------------------------------------------


def test_a_screening_accounts_for_a_trial_only_if_no_later_record_shows_it_read_out(tmp_path):
    batches, log = a_study_of(120)
    not_looked_at = AdjudicationLog([a for a in log.adjudications if a.nct > "NCT0005"])
    found_none = [screened(f"NCT000{i}", "eligible", on=EIGHTEEN_MONTHS) for i in range(1, 6)]
    run_on = EIGHTEEN_MONTHS + dt.timedelta(days=10)
    # Found to have read out a week later, and not yet adjudicated: the trial is not accounted for.
    since = [screened("NCT0003", "already_read_out", on=EIGHTEEN_MONTHS + dt.timedelta(days=8))]
    with pytest.raises(NotReady, match="NCT0003"):
        run_final((batches, not_looked_at), run_on, tmp_path / "a.jsonl", screening=found_none + since)
    # Nor does a screening dated after the day of the run account for anything.
    post_dated = found_none[:4] + [screened("NCT0005", "eligible", on=run_on + dt.timedelta(days=1))]
    with pytest.raises(NotReady, match="NCT0005"):
        run_final((batches, not_looked_at), run_on, tmp_path / "a.jsonl", screening=post_dated)


def test_a_batch_sealed_when_an_analysis_was_run_cannot_go_absent_afterwards(tmp_path):
    batches, log = a_small_study()
    later_batch = batch_of([candidate("NCT8"), candidate("NCT9")], [base_rate(), FixedForecaster("stand_in", 0.5)],
                           on=dt.date(2027, 6, 1))
    record_file = tmp_path / "analyses.jsonl"
    look = descriptive_look([*batches, later_batch], log, PLAN, dt.date(2027, 6, 10), record_file)
    assert look["n_trials"] == 2    # the later batch is after the look's date and plays no part in it
    with pytest.raises(AlreadyRun, match="no longer among the sealed batches"):
        descriptive_look(batches, log, PLAN, dt.date(2027, 7, 1), record_file)
    with pytest.raises(AlreadyRun, match="no longer among the sealed batches"):
        run_final((batches, log), EIGHTEEN_MONTHS, record_file)


def test_entries_dated_before_a_run_cannot_be_added_to_the_log_after_it(tmp_path):
    batches, log = a_study_of(150, hit_rate=0.7)
    record_file = tmp_path / "analyses.jsonl"
    # Run on a log that leaves 30 trials out, each "accounted for" by a screening.
    kept = AdjudicationLog([a for a in log.adjudications if a.nct > "NCT0030"])
    hidden = [a for a in log.adjudications if a.nct <= "NCT0030"]
    screening = [screened(f"NCT{i:04d}", "eligible", on=EIGHTEEN_MONTHS) for i in range(1, 31)]
    assert run_final((batches, kept), EIGHTEEN_MONTHS, record_file, screening=screening)["primary"]["n_trials"] == 120
    # Putting them back, dated as they always were, is not a regeneration of what was run.
    with pytest.raises(AlreadyRun, match="dated before"):
        run_final((batches, AdjudicationLog([*kept.adjudications, *hidden])), EIGHTEEN_MONTHS + dt.timedelta(days=5),
                  record_file, screening=screening)


def test_an_extension_record_that_claims_the_log_was_empty_is_refused(tmp_path):
    batches, log = a_study_of(120)
    nothing = AdjudicationLog()
    as_if_empty = study_state(batches, nothing, EIGHTEEN_MONTHS, EIGHTEEN_MONTHS)
    forged = AnalysisRecord("extension", EIGHTEEN_MONTHS, TWENTY_FOUR_MONTHS, 0, (batches[0].fingerprint,), (0, 0, 0, 0),
                            FEW_RESAMPLES, analysis._inputs_fingerprint(as_if_empty, nothing, PLAN), "00" * 32)
    records.append(tmp_path / "forged.jsonl", forged)
    with pytest.raises(AlreadyRun, match="dated before"):
        run_final((batches, log), TWENTY_FOUR_MONTHS, tmp_path / "forged.jsonl")
    with pytest.raises(ValueError):
        log.first((-1, 0, 0, 0))


def test_a_final_analysis_first_run_after_both_dates_extends_and_then_tests_in_one_go(tmp_path):
    record_file = tmp_path / "analyses.jsonl"
    final = run_final(a_study_of(80), TWENTY_FOUR_MONTHS + dt.timedelta(days=3), record_file)
    assert (final["decision"], final["extended"], final["readouts_to"]) == ("tested", True, TWENTY_FOUR_MONTHS)
    assert [r.kind for r in records.read(record_file, AnalysisRecord)] == ["extension", "final_analysis"]


def test_a_missing_hazard_ratio_is_counted_as_no_effect_in_a_sensitivity_analysis():
    trials = [candidate("NCT1"), candidate("NCT2"), candidate("NCT3")]
    batch = batch_of(trials, [base_rate(), FixedForecaster("stand_in", 0.7, hazard_ratio=(0.70, 0.60, 0.82))])
    adjudications = (hazard_ratio_reading("NCT1", 0.72)
                     + both_adjudicated("NCT2", "negative", readout=dt.date(2026, 12, 1))            # never reported
                     + hazard_ratio_reading("NCT3", 0.6, endpoint="Progression-free survival", readout=dt.date(2026, 12, 1)))
    held = as_of([batch], adjudications)
    reported = effect_size_comparison(held, "stand_in", "base_rate", n_boot=FEW_RESAMPLES)
    with_missing = effect_size_comparison(held, "stand_in", "base_rate", n_boot=FEW_RESAMPLES, missing_as_no_effect=True)
    assert (reported["n_trials"], with_missing["n_trials"]) == (1, 3)
    # A forecast of 0.70 is further from no effect than the baseline's 0.84, so it scores worse on those two trials.
    assert with_missing["crps"]["stand_in"] > with_missing["crps"]["base_rate"]
    assert with_missing["hazard_ratio_missing"] == ["NCT2"] and with_missing["hazard_ratio_for_another_endpoint"] == ["NCT3"]


# --- decided on 2026-10-09: readings after a reveal, and the effect-size follow-up ---------------


def test_a_source_read_after_the_reveal_changes_only_its_own_sensitivity_analysis(tmp_path):
    batches, log = a_study_of(120)
    reveal = dt.date(2027, 9, 1)
    opened = [ForecastAccess(nct="NCT0002", person=who, opened_on=reveal) for who in ("first", "second")]
    # After the reveal both adjudicators read a paper that reverses NCT0002. They are not blind for it.
    paper = both_adjudicated("NCT0002", "negative", readout=dt.date(2027, 12, 1), source_type="paper_or_regulator",
                             source="https://example.test/paper")
    plain = run_final((batches, log), EIGHTEEN_MONTHS, tmp_path / "plain.jsonl")
    final = run_final((batches, AdjudicationLog([*log.adjudications, *paper], forecast_access=opened)), EIGHTEEN_MONTHS,
                      tmp_path / "revealed.jsonl")
    assert final["primary"]["brier"] == plain["primary"]["brier"]          # the blind reading still decides
    assert final["set_aside"] == {"NCT0002": ["https://example.test/paper"]}
    counted_too = final["sensitivity"]["with sources read after the forecasts were opened"]
    assert counted_too["n_trials"] == 120 and counted_too["brier"] != plain["primary"]["brier"]
    assert plain["sensitivity"]["with sources read after the forecasts were opened"]["brier"] == plain["primary"]["brier"]


SIX_MONTHS_ON = dt.date(2028, 11, 2)    # six months after the final analysis date


def a_study_with_late_hazard_ratios():
    """120 trials read out in March 2028; half report a hazard ratio at once, half four months later, after the final date."""
    batches, log = a_study_of(120, readout=dt.date(2028, 3, 1))
    later = dt.date(2028, 7, 1)
    readings = []
    for reading in log.adjudications:
        if int(reading.nct[3:]) % 2:
            readings.append(reading)
            continue
        readings.append(dataclasses.replace(reading, hazard_ratio=None, hazard_ratio_endpoint=None))
        readings.append(dataclasses.replace(reading, source_type="conference", source="https://example.test/congress",
                                            disclosed_on=later, recorded_on=later))
    # A log is only ever added to, so the later readings come after everything recorded before them.
    return batches, AdjudicationLog(sorted(readings, key=lambda a: a.recorded_on))


def follow_up(study, today, record_file, searched_on=SIX_MONTHS_ON, plan=PLAN, n_boot=FEW_RESAMPLES):
    batches, log = study
    return analysis.effect_size_follow_up(batches, log, plan, today, record_file, hazard_ratios_searched_on=searched_on, n_boot=n_boot)


def test_hazard_ratios_that_arrive_after_the_final_date_are_scored_once_six_months_later(tmp_path):
    batches, log = a_study_with_late_hazard_ratios()
    record_file = tmp_path / "analyses.jsonl"
    as_of_final = AdjudicationLog([a for a in log.adjudications if a.recorded_on <= EIGHTEEN_MONTHS])
    with pytest.raises(NotDue, match="final analysis has not been run"):
        follow_up((batches, log), SIX_MONTHS_ON, record_file)

    final = run_final((batches, as_of_final), EIGHTEEN_MONTHS, record_file)
    assert final["effect_size"]["base_rate"]["n_trials"] == 60 and len(final["effect_size"]["base_rate"]["hazard_ratio_awaited"]) == 60
    with pytest.raises(NotDue, match="2028-11-02"):
        follow_up((batches, log), SIX_MONTHS_ON - dt.timedelta(days=1), record_file)
    # It is made once, so it waits until someone says the search for hazard ratios is finished, on or after its date.
    for unfinished in (None, SIX_MONTHS_ON - dt.timedelta(days=1), SIX_MONTHS_ON + dt.timedelta(days=9)):
        with pytest.raises(NotReady, match="search for hazard ratios"):
            follow_up((batches, log), SIX_MONTHS_ON + dt.timedelta(days=5), record_file, searched_on=unfinished)

    made = follow_up((batches, log), SIX_MONTHS_ON, record_file)
    assert (made["kind"], made["readouts_to"], made["hazard_ratios_to"]) == ("effect_size_follow_up", EIGHTEEN_MONTHS, SIX_MONTHS_ON)
    # The same 120 trials the final analysis scored, now each with its hazard ratio.
    assert made["effect_size"]["base_rate"]["n_trials"] == 120 == final["primary"]["n_trials"]
    assert made["effect_size"]["base_rate"]["hazard_ratio_awaited"] == []
    # Nobody had opened a forecast when the later hazard ratios were read, so none was read after a reveal.
    assert made["effect_size"]["base_rate"]["hazard_ratio_read_after_reveal"] == []
    assert set(made) == {"kind", "run_on", "readouts_to", "hazard_ratios_to", "hazard_ratios_searched_on", "effect_size",
                         "effect_size_missing_as_no_effect"}
    assert made["hazard_ratios_searched_on"] == SIX_MONTHS_ON
    # Made once, like the others; and the final analysis is still regenerated exactly as it was.
    later = SIX_MONTHS_ON + dt.timedelta(days=30)
    assert follow_up((batches, log), later, record_file, searched_on=None, n_boot=7) == made
    assert [r.kind for r in records.read(record_file, AnalysisRecord)] == ["final_analysis", "effect_size_follow_up"]
    assert run_final((batches, log), later, record_file) == final
    with pytest.raises(AlreadyRun):
        follow_up((batches, log), later, record_file, plan=dataclasses.replace(PLAN, effect_size_baselines=("base_rate", "other")))


def test_the_follow_up_is_made_on_the_plan_the_final_analysis_was_made_on(tmp_path):
    batches, log = a_study_with_late_hazard_ratios()
    record_file = tmp_path / "analyses.jsonl"
    run_final((batches, AdjudicationLog([a for a in log.adjudications if a.recorded_on <= EIGHTEEN_MONTHS])), EIGHTEEN_MONTHS,
              record_file)
    with pytest.raises(AlreadyRun, match="final analysis was run on 2028-05-02"):
        follow_up((batches, log), SIX_MONTHS_ON, record_file,
                  plan=dataclasses.replace(PLAN, effect_size_baselines=("base_rate", "other")))
    assert [r.kind for r in records.read(record_file, AnalysisRecord)] == ["final_analysis"]


def test_the_follow_up_waits_for_a_hazard_ratio_that_only_one_adjudicator_has_read(tmp_path):
    batches, log = a_study_with_late_hazard_ratios()
    record_file = tmp_path / "analyses.jsonl"
    run_final((batches, AdjudicationLog([a for a in log.adjudications if a.recorded_on <= EIGHTEEN_MONTHS])), EIGHTEEN_MONTHS,
              record_file)
    revealed = [ForecastAccess(nct=t.nct, person=who, opened_on=EIGHTEEN_MONTHS + dt.timedelta(days=1))
                for t in batches[0].trials for who in ("first", "second")]
    # After the reveal the congress report of NCT0002 is read by one adjudicator only. It is set aside for the outcome
    # either way, but its hazard ratio would be scored on one person's copying of a number.
    read_once = [a for a in log.adjudications
                 if not (a.nct == "NCT0002" and a.source_type == "conference" and a.adjudicator == "second")]
    with pytest.raises(NotReady, match=r"NCT0002 \(https://example.test/congress\)"):
        follow_up((batches, AdjudicationLog(read_once, forecast_access=revealed)), SIX_MONTHS_ON, record_file)
    assert follow_up((batches, AdjudicationLog(log.adjudications, forecast_access=revealed)), SIX_MONTHS_ON, record_file)


def test_the_follow_up_scores_the_trials_of_the_final_analysis_and_no_others(tmp_path):
    batches, log = a_study_of(121, readout=dt.date(2028, 3, 1))
    record_file = tmp_path / "analyses.jsonl"
    # NCT0001 reads out a month after the final date: the final analysis does not score it, so nor does the follow-up.
    after_final = EIGHTEEN_MONTHS + dt.timedelta(days=30)
    readings = [dataclasses.replace(a, disclosed_on=after_final, recorded_on=after_final) if a.nct == "NCT0001" else a
                for a in log.adjudications]
    log = AdjudicationLog(sorted(readings, key=lambda a: a.recorded_on))
    as_of_final = AdjudicationLog([a for a in log.adjudications if a.recorded_on <= EIGHTEEN_MONTHS])
    looked = [screened("NCT0001", "eligible", on=EIGHTEEN_MONTHS)]
    assert run_final((batches, as_of_final), EIGHTEEN_MONTHS, record_file, screening=looked)["primary"]["n_trials"] == 120
    made = follow_up((batches, log), SIX_MONTHS_ON, record_file)
    assert made["effect_size"]["base_rate"]["n_trials"] == 120


def test_a_hazard_ratio_read_after_the_reveal_is_still_the_hazard_ratio_scored(tmp_path):
    batches, log = a_study_with_late_hazard_ratios()
    record_file = tmp_path / "analyses.jsonl"
    as_of_final = AdjudicationLog([a for a in log.adjudications if a.recorded_on <= EIGHTEEN_MONTHS])
    final = run_final((batches, as_of_final), EIGHTEEN_MONTHS, record_file)
    # The forecasts are revealed the day after the final analysis. Every later hazard ratio is read by people who have seen them.
    revealed = [ForecastAccess(nct=t.nct, person=who, opened_on=EIGHTEEN_MONTHS + dt.timedelta(days=1))
                for t in batches[0].trials for who in ("first", "second")]
    after_reveal = AdjudicationLog(log.adjudications, forecast_access=revealed)
    made = follow_up((batches, after_reveal), SIX_MONTHS_ON, record_file)
    scored = made["effect_size"]["base_rate"]
    assert scored["n_trials"] == 120 and len(scored["hazard_ratio_read_after_reveal"]) == 60
    assert final["effect_size"]["base_rate"]["hazard_ratio_read_after_reveal"] == []


def test_a_follow_up_to_a_study_that_made_no_claim_tests_nothing(tmp_path):
    batches, log = a_study_of(40, readout=dt.date(2028, 3, 1))
    record_file = tmp_path / "analyses.jsonl"
    run_final((batches, log), EIGHTEEN_MONTHS, record_file)
    assert run_final((batches, log), TWENTY_FOUR_MONTHS, record_file)["decision"] == "estimate_only"
    made = follow_up((batches, log), dt.date(2029, 5, 2), record_file, searched_on=dt.date(2029, 5, 2))
    assert "p_two_sided" not in keys_anywhere(made) and made["effect_size"]["base_rate"]["n_trials"] == 40


def test_a_hazard_ratio_is_awaited_only_until_its_six_months_are_up():
    batch = batch_of([candidate("NCT1")], [base_rate(), FixedForecaster("stand_in", 0.7)])
    readout = dt.date(2027, 3, 14)
    held = as_of([batch], both_adjudicated("NCT1", "positive", readout=readout))
    trial, result = held.batches[0].trials[0], held.results["NCT1"]
    six_months_on = dt.date(2027, 9, 14)
    assert analysis.scored_hazard_ratio(result, trial, six_months_on - dt.timedelta(days=1)) == (None, "awaited")
    assert analysis.scored_hazard_ratio(result, trial, six_months_on) == (None, "missing")
