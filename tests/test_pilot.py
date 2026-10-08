"""The retrospective pilot: what each model already knows, which trials it cannot know, and what the pilot measures."""
import dataclasses
import datetime as dt
import gzip
import hashlib
import json
import math

import pytest

from registry_records import study
from study_records import adjudicated, both_adjudicated, candidate
from trialforecast import records
from trialforecast.adjudication import AdjudicationLog, results
from trialforecast.forecasting import Forecast
from trialforecast.models import ModelSpec, ModelUnavailable, Reply
from trialforecast.pilot import (
    CUTOFF_PROBE, MEMORISATION_PROBE, NOT_THE_EVIDENCE, PROBE_VERSION, ModelPilot, PastTrial, ProbeRecord,
    ProbesIncomplete, adjudicator_agreement, as_before_readout, ask_probe, current_answers, dates_to_check, main,
    months_after, pilot_plan, pilot_reference, probe_answer, probe_prompt, recall_by_month, recalled, report,
    said_known_without_readout, sample_size_statement, score_differences, traced_trials, with_adjudicated,
)

SPEC = ModelSpec(provider="anthropic", model="example-1", training_cutoff="2026-06", released_on=dt.date(2026, 9, 21),
                 input_usd_per_million=4.0, output_usd_per_million=20.0)
TODAY = dt.date(2026, 10, 8)


def past(nct, readout=None, positive=None, hazard_ratio=None):
    return PastTrial(nct=nct, readout_date=readout, positive=positive, hazard_ratio=hazard_ratio)


def read_out_in(*months, year=2026):
    """Past trials NCT1, NCT2, ... that read out, positive, on the 10th of the given months."""
    return [past(f"NCT{i}", dt.date(year, month, 10), True) for i, month in enumerate(months, 1)]


def answer(nct, known, positive=None, probe=CUTOFF_PROBE, first_reported=None):
    return ProbeRecord(nct=nct, model="example-1", probe=probe, asked_on=TODAY, known=known, positive=positive,
                       first_reported=first_reported, reply="", failure=None, input_tokens=0, output_tokens=0,
                       cost_usd=0.0)


def answers_to_both(trials, recalls=()):
    """Answers to both probes for every trial: the results in `recalls` known and rightly dated, the rest unknown."""
    return [answer(t.nct, True, t.positive, probe, t.readout_date.strftime("%Y-%m"))
            if t.nct in recalls else answer(t.nct, False, probe=probe)
            for t in trials for probe in (CUTOFF_PROBE, MEMORISATION_PROBE)]


# --- past trials ------------------------------------------------------------------------


def test_traced_trials_are_readouts_and_trials_with_none_and_nothing_in_doubt(tmp_path):
    trace = tmp_path / "trace.csv"
    trace.write_text(
        "nct,disclosed,first_disclosure_date,primary_result,hr_value,hr_first_public_date\n"
        "NCT1,yes,2026-07-14,met,0.72,2026-07-14\n"
        "NCT2,yes,2026-02-01,stopped_futility,,\n"
        "NCT3,no,,,,\n"
        "NCT4,no,,terminated_no_analysis,,\n"   # ended without a primary analysis: neither a readout nor a trial with none
        "NCT5,unclear,2026-05-01,unclear,,\n"
        "NCT6,yes,2026-05-01,mixed,,\n"
        "NCT7,yes,2025-01-10,met,0.80,2025-07-10\n"   # hazard ratio public exactly six months after the readout
        "NCT8,yes,2025-01-10,met,0.80,2025-07-11\n"   # a day too late to count (ADR-0011)
    )
    assert traced_trials([trace]) == [
        past("NCT1", dt.date(2026, 7, 14), True, 0.72), past("NCT2", dt.date(2026, 2, 1), False), past("NCT3"),
        past("NCT7", dt.date(2025, 1, 10), True, 0.80), past("NCT8", dt.date(2025, 1, 10), True)]


def test_an_adjudicated_result_takes_the_place_of_the_traced_one():
    candidates = {nct: candidate(nct) for nct in ("NCT1", "NCT2", "NCT3", "NCT4")}
    candidates["NCT2"]["sponsor_type"] = float("nan")    # as a record read from a table has it when the registry gave none
    traced = [past("NCT1", dt.date(2026, 8, 1), True, 0.7), past("NCT2", dt.date(2026, 8, 1), True, 0.7),
              past("NCT3", dt.date(2026, 8, 1), True), past("NCT4")]
    log = AdjudicationLog([
        # Both adjudicators date NCT1 earlier, read it as negative, and record a hazard ratio for another endpoint.
        *both_adjudicated("NCT1", "negative", readout=dt.date(2026, 3, 2), hazard_ratio=0.9, hazard_ratio_endpoint="PFS"),
        *both_adjudicated("NCT2", "positive", readout=dt.date(2026, 8, 3), hazard_ratio=0.66, hazard_ratio_endpoint="Overall survival"),
        *both_adjudicated("NCT3", "void", readout=dt.date(2026, 8, 1)),
    ])
    assert with_adjudicated(traced, results(log, TODAY), candidates, TODAY) == [
        PastTrial("NCT1", dt.date(2026, 3, 2), False, None, adjudicated=True),
        PastTrial("NCT2", dt.date(2026, 8, 3), True, 0.66, adjudicated=True),
        past("NCT4"),                                  # NCT3 was void: it never read out, so it is no longer here
    ]


# --- the two probes -----------------------------------------------------------------------


def test_the_cutoff_probe_shows_the_record_without_what_the_registry_shows_once_a_trial_is_over():
    trial = candidate("NCT00000001", "Overall survival", drug="Examplumab", pcd="2026-05-10", pcd_type="ACTUAL",
                      status="COMPLETED")
    assert trial["enrollment"] == 500 and trial["enrollment_type"] == "ESTIMATED"
    shown = probe_prompt(trial, CUTOFF_PROBE)
    assert "A Study of X Versus Y" in shown and "Examplumab" in shown and "NCT00000001" in shown
    for hidden in ("COMPLETED", "2026-05-10", "ACTUAL", "500", "ESTIMATED"):
        assert hidden not in shown
    assert as_before_readout(trial)["scored_endpoint"] == trial["scored_endpoint"]


def test_the_memorisation_probe_shows_identifiers_alone():
    trial = {**candidate("NCT00000001", drug="Examplumab"), "acronym": "EXAMPLE-3", "org_study_id": "EX-301"}
    shown = probe_prompt(trial, MEMORISATION_PROBE)
    assert "NCT00000001" in shown and "EXAMPLE-3" in shown and "EX-301" in shown
    assert "Examplumab" not in shown and "A Study of X Versus Y" not in shown and "Overall survival" not in shown
    with pytest.raises(ValueError, match="not one of the probes"):
        probe_prompt(trial, "something else")


def test_the_wording_of_the_probes_cannot_change_without_a_new_version():
    trial = {**candidate("NCT00000001", drug="Examplumab"), "acronym": "EXAMPLE-3", "org_study_id": "EX-301"}
    wording = hashlib.sha256((probe_prompt(trial, CUTOFF_PROBE) + probe_prompt(trial, MEMORISATION_PROBE)).encode()).hexdigest()
    assert (PROBE_VERSION, wording[:16]) == ("2", "e6cd3ba761b0d085"), (
        "the probes are worded differently: raise PROBE_VERSION, then update this fingerprint")


def test_a_probe_answer_is_the_last_json_object_and_nothing_looser():
    said = '{"result_known": true, "result": "positive", "first_reported": "2026-03"}'
    assert probe_answer(f"I recall this. {said}") == (True, True, "2026-03")
    assert probe_answer(f'Draft {said} final {{"result_known": false, "result": null, "first_reported": null}}') == (False, None, None)
    for unusable in (None, "It was positive.", '{"result_known": "yes", "result": "positive"}',
                     '{"result_known": true, "result": "probably positive"}', '{"result_known": true, "result": null}'):
        assert probe_answer(unusable) is None


@pytest.mark.parametrize("stated, month", [("2026-03", "2026-03"), ("2026-09-10", "2026-09"), ("2026-9", "2026-09"),
                                           (None, None), ("spring 2026", None), ("2026-13", None), (202603, None)])
def test_a_date_is_taken_to_the_month_however_exactly_the_model_gives_it(stated, month):
    reply = json.dumps({"result_known": True, "result": "negative", "first_reported": stated})
    assert probe_answer(reply) == (True, False, month)


def test_a_probe_keeps_the_reply_with_its_cost_and_asks_again_only_after_an_outage():
    replies = iter([Reply(None, 0, 0, failure="provider unavailable"),
                    Reply('{"result_known": true, "result": "positive", "first_reported": "2026-02"}', 1000, 500,
                          model_served="example-1-0901")])
    waited = []
    record = ask_probe(SPEC, lambda spec, prompt: next(replies), candidate("NCT1"), CUTOFF_PROBE, TODAY,
                       snapshot="2026-10-07T090006", wait=waited.append)
    assert (record.nct, record.known, record.positive, record.first_reported, record.failure) == ("NCT1", True, True, "2026-02", None)
    assert record.cost_usd == pytest.approx((1000 * 4.0 + 500 * 20.0) / 1e6) and len(waited) == 1
    assert (record.snapshot, record.model_served, record.probe_version) == ("2026-10-07T090006", "example-1-0901", PROBE_VERSION)


def test_a_refusal_is_recorded_as_no_usable_answer_whatever_its_text_says():
    refused = Reply('{"result_known": true, "result": "positive", "first_reported": "2026-02"}', 900, 20, failure="refused")
    record = ask_probe(SPEC, lambda spec, prompt: refused, candidate("NCT1"), CUTOFF_PROBE, TODAY)
    assert (record.known, record.positive, record.first_reported, record.failure) == (None, None, None, "refused")


def test_only_the_first_answer_to_the_current_wording_of_a_probe_is_counted():
    first, again = answer("NCT1", False), answer("NCT1", True, True, first_reported="2026-08")
    earlier_wording = dataclasses.replace(answer("NCT2", True, True, first_reported="2026-08"), probe_version="1")
    assert current_answers([first, again, earlier_wording]) == {("NCT1", CUTOFF_PROBE): first}


# --- recall around the cutoff, and the buffer ------------------------------------------------


def test_months_are_counted_from_the_month_of_the_stated_cutoff():
    assert months_after("2026-06", dt.date(2026, 6, 30)) == 0
    assert months_after("2026-06", dt.date(2026, 8, 1)) == 2
    assert months_after("2026-04-30", dt.date(2026, 5, 1)) == 1   # a cutoff given to the day counts as its month
    assert months_after("2026-06", dt.date(2025, 12, 15)) == -6
    assert months_after("2025-11", dt.date(2026, 2, 1)) == 3


@pytest.mark.parametrize("stated, is_recall", [("2026-08", True), ("2026-05", True), ("2026-11", True),   # within three months
                                               ("2026-04", False), ("2026-12", False), ("2025-08", False), (None, False)])
def test_recall_is_the_right_result_dated_to_within_three_months_either_way(stated, is_recall):
    trial = past("NCT1", dt.date(2026, 8, 5), True)
    assert recalled(answer("NCT1", True, True, first_reported=stated), trial) is is_recall
    assert recalled(answer("NCT1", True, False, first_reported="2026-08"), trial) is False    # the wrong result


def test_recall_is_counted_by_month_of_readout_apart_from_right_results_without_the_date():
    trials = [past("NCT1", dt.date(2026, 3, 2), True), past("NCT2", dt.date(2026, 3, 20), False),
              past("NCT3", dt.date(2026, 8, 5), True), past("NCT4"), past("NCT5", dt.date(2026, 8, 9), True)]
    answers = [
        answer("NCT1", True, True, first_reported="2026-02"),     # right, and dated within three months: recalled
        answer("NCT2", True, True, first_reported="2026-03"),     # it said it knew, but the result is wrong
        answer("NCT3", False),
        answer("NCT4", True, True, first_reported="2026-01"),     # no readout to recall
        answer("NCT5", True, True, first_reported="2025-06"),     # the right result, placed a year too early
    ]
    assert recall_by_month(answers, trials, "2026-06") == [
        {"months_after_cutoff": -3, "trials": 2, "said_known": 2, "right_result": 1, "recalled": 1},
        {"months_after_cutoff": 2, "trials": 2, "said_known": 1, "right_result": 1, "recalled": 0},
    ]
    assert said_known_without_readout(answers, trials) == {"trials": 1, "said_known": 1}
    # Either NCT5 was inferred, or its readout on record is late: it is listed for a second look.
    assert dates_to_check(answers, trials) == ["NCT5"]


def test_the_buffer_covers_every_month_in_which_recall_was_seen_and_never_less_than_one():
    trials = read_out_in(5, 8, 9, 10, 10, 10, 10, 10, 10)
    assert pilot_plan(SPEC, answers_to_both(trials, recalls={"NCT1"}), trials).buffer_months == 1
    # One result recalled two months after the stated cutoff, on one probe only, pushes the buffer out to cover it.
    on_one_probe = [a for a in answers_to_both(trials) if (a.nct, a.probe) != ("NCT2", MEMORISATION_PROBE)]
    on_one_probe.append(answer("NCT2", True, True, MEMORISATION_PROBE, "2026-08"))
    plan = pilot_plan(SPEC, on_one_probe, trials)
    assert (plan.latest_recall, plan.buffer_months) == (2, 2)
    # The right result without its date does not move the buffer.
    undated = [a for a in answers_to_both(trials) if (a.nct, a.probe) != ("NCT3", CUTOFF_PROBE)]
    undated.append(answer("NCT3", True, True, CUTOFF_PROBE, None))
    assert pilot_plan(SPEC, undated, trials).buffer_months == 1


def test_a_models_pilot_trials_read_out_after_its_cutoff_plus_buffer():
    trials = read_out_in(5, 6, 7, 8, 8, 9, 9, 9, 10)
    plan = pilot_plan(SPEC, answers_to_both(trials), trials)
    assert plan.buffer_months == 1 and plan.dropped is None
    assert [t.nct for t in plan.trials] == ["NCT4", "NCT5", "NCT6", "NCT7", "NCT8", "NCT9"]   # August onwards


def test_a_model_showing_recall_beyond_its_buffer_gets_a_longer_one_or_is_dropped():
    trials = read_out_in(5, 6, 7, 8, 8, 9, 9, 9, 10)
    plan = pilot_plan(SPEC, answers_to_both(trials, recalls={"NCT6"}), trials)     # NCT6 read out in September
    assert plan.buffer_months == 3 and [t.nct for t in plan.trials] == ["NCT9"]
    assert "fewer than 5" in plan.dropped


def test_five_pilot_trials_are_enough_and_four_are_not():
    assert pilot_plan(SPEC, answers_to_both(read_out_in(8, 8, 9, 9, 10)), read_out_in(8, 8, 9, 9, 10)).dropped is None
    assert pilot_plan(SPEC, answers_to_both(read_out_in(8, 8, 9, 9)), read_out_in(8, 8, 9, 9)).dropped is not None


def test_no_buffer_is_chosen_until_both_probes_have_been_answered_for_every_trial():
    trials = read_out_in(5, 8, 8, 9, 9, 10)
    with pytest.raises(ProbesIncomplete, match="12 of 12"):
        pilot_plan(SPEC, [], trials)
    one_probe_only = [a for a in answers_to_both(trials) if a.probe == CUTOFF_PROBE]
    with pytest.raises(ProbesIncomplete, match="6 of 12"):
        pilot_plan(SPEC, one_probe_only, trials)
    with pytest.raises(ProbesIncomplete, match="1 of 12"):
        pilot_plan(SPEC, answers_to_both(trials)[:-1], trials)


def test_a_model_that_mostly_gives_no_usable_answer_to_the_probes_is_dropped():
    trials = read_out_in(5, 8, 8, 9, 9, 10)
    refusing = [dataclasses.replace(a, known=None, failure="refused") for a in answers_to_both(trials)]
    plan = pilot_plan(SPEC, refusing, trials)
    assert plan.trials == () and "usable answer to only 0%" in plan.dropped
    one_refusal_in_twelve = [dataclasses.replace(a, known=None) if i == 0 else a for i, a in enumerate(answers_to_both(trials))]
    assert pilot_plan(SPEC, one_refusal_in_twelve, trials).dropped is None     # 92% usable


# --- agreement between the adjudicators --------------------------------------------------


def test_agreement_is_measured_on_each_adjudicators_first_reading():
    later = dt.date(2027, 4, 1)
    log = AdjudicationLog([
        # Entered out of order: the later correction first, to show that the first reading is found by its date.
        adjudicated("NCT3", "second", "positive", hazard_ratio=0.8, hazard_ratio_endpoint="OS", recorded_on=later),
        adjudicated("NCT1", "first", "positive", hazard_ratio=0.7, hazard_ratio_endpoint="OS"),
        adjudicated("NCT1", "second", "positive", hazard_ratio=0.704, hazard_ratio_endpoint="os"),   # the same to two places
        adjudicated("NCT2", "first", "negative"),
        adjudicated("NCT2", "second", "negative", disclosed_on=dt.date(2027, 3, 13)),               # a day apart
        adjudicated("NCT3", "first", "positive", hazard_ratio=0.8, hazard_ratio_endpoint="OS"),
        adjudicated("NCT3", "second", "negative"),
        adjudicated("NCT4", "first", "positive"),      # read by one adjudicator only: not compared
        adjudicated("NCT5", "first", "positive", hazard_ratio=0.8, hazard_ratio_endpoint="OS"),
        adjudicated("NCT5", "second", "positive", hazard_ratio=0.8, hazard_ratio_endpoint="PFS"),    # another endpoint
    ])
    agreement = adjudicator_agreement(log)
    assert (agreement["sources"], agreement["not_read_by_two"], agreement["outcome_agreed"]) == (4, 1, 3)
    # Observed agreement 3/4; by chance (3/4 * 2/4) + (1/4 * 2/4) = 1/2; kappa = (3/4 - 1/2) / (1 - 1/2).
    assert agreement["kappa"] == pytest.approx(0.5)
    assert agreement["disclosure_date_agreed"] == 3
    assert (agreement["hazard_ratio_compared"], agreement["hazard_ratio_agreed"]) == (3, 1)


def test_kappa_is_undefined_when_both_adjudicators_called_every_source_the_same_way():
    one_source = AdjudicationLog(both_adjudicated("NCT1", "positive"))
    assert adjudicator_agreement(one_source)["kappa"] is None and adjudicator_agreement(one_source)["outcome_agreed"] == 1
    assert adjudicator_agreement(AdjudicationLog([adjudicated("NCT1", "first", "positive")]))["sources"] == 0


# --- the reference and the scores -----------------------------------------------------------


def a_forecast(nct, name, probability, hazard_ratio=(0.8, 0.6, 1.05)):
    median, low, high = hazard_ratio
    return Forecast(nct=nct, forecaster=name, version="pilot", batch_date=TODAY, probability_positive=probability,
                    hazard_ratio=median, hazard_ratio_low=low, hazard_ratio_high=high)


def test_the_pilot_reference_uses_only_readouts_no_later_than_the_cutoff_month():
    survival = [past(f"NCT{i}", dt.date(2026, 1 + i % 6, 10), i < 9, 0.5 + i / 20) for i in range(12)]     # 9 of 12 positive
    progression = [past(f"NCT{20 + i}", dt.date(2026, 3, 10), False, 0.9) for i in range(3)]              # too few alone
    after_cutoff = [past(f"NCT{40 + i}", dt.date(2026, 7, 10), False, 2.0) for i in range(10)]            # must not count
    candidates = {t.nct: candidate(t.nct) for t in survival + after_cutoff}
    candidates.update({t.nct: candidate(t.nct, "Progression-free survival") for t in progression})

    reference = pilot_reference(survival + progression + after_cutoff, candidates, "2026-06")

    own_class = reference.forecast(candidates["NCT0"], TODAY)
    ratios = sorted(0.5 + i / 20 for i in range(12))
    assert own_class.probability_positive == pytest.approx(9 / 12)
    assert own_class.hazard_ratio == pytest.approx(math.sqrt(ratios[5] * ratios[6]))    # the median, on the log scale
    assert own_class.hazard_ratio_low < own_class.hazard_ratio < own_class.hazard_ratio_high < 2.0
    # Three earlier readouts are too few for a class of its own: it takes the figures of all fifteen together.
    assert reference.forecast(candidates["NCT20"], TODAY).probability_positive == pytest.approx(9 / 15)
    with pytest.raises(ValueError, match="too few for a base rate"):
        pilot_reference(survival[:9], candidates, "2026-06")


def test_score_differences_are_the_models_score_minus_the_references_trial_by_trial():
    trials = [past("NCT1", dt.date(2026, 9, 1), True, 0.7), past("NCT2", dt.date(2026, 9, 2), False)]
    own = {"NCT1": a_forecast("NCT1", "m", 0.9, (0.7, 0.6, 0.82)), "NCT2": a_forecast("NCT2", "m", 0.4)}
    reference = {t.nct: a_forecast(t.nct, "base_rate", 0.6, (0.84, 0.66, 1.07)) for t in trials}
    differences = score_differences(own, reference, trials)
    assert differences["brier"] == pytest.approx([0.01 - 0.16, 0.16 - 0.36])
    assert len(differences["crps"]) == 1 and differences["crps"][0] < 0    # only NCT1 has a hazard ratio to score


def test_a_trial_the_model_gave_no_forecast_for_is_scored_at_the_reference():
    trials = [past("NCT1", dt.date(2026, 9, 1), True, 0.7)]
    silent = {"NCT1": Forecast(nct="NCT1", forecaster="m", version="pilot", batch_date=TODAY, probability_positive=None,
                               hazard_ratio=None, hazard_ratio_low=None, hazard_ratio_high=None, no_forecast="refused")}
    reference = {"NCT1": a_forecast("NCT1", "base_rate", 0.6)}
    assert score_differences(silent, reference, trials) == {"brier": [0.0], "crps": [0.0]}


def test_the_sample_size_statement_follows_from_the_spread_of_the_differences():
    differences = [-0.10, 0.02, -0.06, 0.04, -0.08, -0.02]
    statement = sample_size_statement(differences)
    mean = sum(differences) / 6
    sd = math.sqrt(sum((d - mean) ** 2 for d in differences) / 5)
    both_tails_and_power = 1.959964 + 0.841621   # two-sided 5%, 80% power
    assert statement["trials"] == 6 and statement["mean"] == pytest.approx(mean) and statement["sd"] == pytest.approx(sd)
    assert statement["detectable_difference"][120] == pytest.approx(both_tails_and_power * sd / math.sqrt(120), rel=1e-4)
    assert statement["detectable_difference"][60] == pytest.approx(both_tails_and_power * sd / math.sqrt(60), rel=1e-4)
    assert statement["trials_needed"][0.02] == math.ceil((both_tails_and_power * sd / 0.02) ** 2)
    assert sorted(statement["trials_needed"]) == [0.01, 0.02, 0.03, 0.05]
    # Six trials pin the spread down poorly: the 95% interval for a standard deviation on five degrees of freedom.
    low, high = statement["sd_interval"]
    assert (low, high) == (pytest.approx(sd * math.sqrt(5 / 12.8325), rel=1e-4), pytest.approx(sd * math.sqrt(5 / 0.831212), rel=1e-4))
    assert statement["detectable_at_upper_sd"][120] == pytest.approx(both_tails_and_power * high / math.sqrt(120), rel=1e-4)


@pytest.mark.parametrize("differences", [[0.1], [0.1, 0.1, 0.1], []])
def test_no_spread_is_stated_from_one_trial_or_from_trials_that_do_not_differ(differences):
    statement = sample_size_statement(differences)
    assert statement["sd"] is None and statement["trials_needed"] == {} and statement["detectable_difference"] == {}


# --- the report ------------------------------------------------------------------------------


def a_model_pilot(trials, forecast_of=lambda t: 0.7 if t.positive else 0.4, **recalls):
    answers = answers_to_both(trials, **recalls)
    plan = pilot_plan(SPEC, answers, trials)
    forecasts = {t.nct: a_forecast(t.nct, "example_1", forecast_of(t)) for t in plan.trials}
    reference = {t.nct: a_forecast(t.nct, "base_rate", 0.6) for t in plan.trials}
    return ModelPilot(SPEC, tuple(answers), plan, forecasts, reference)


def test_the_report_says_plainly_what_the_pilot_is_and_that_unadjudicated_outcomes_are_provisional():
    trials = [past(f"NCT{i}", dt.date(2026, month, 10), i % 2 == 0, 0.8) for i, month in enumerate((3, 5, 8, 8, 9, 9, 9, 10), 1)]
    pilot = a_model_pilot(trials, recalls={"NCT1", "NCT2"})

    text = report([pilot], trials, agreement=None, written_on=TODAY)

    assert text.count(NOT_THE_EVIDENCE) == 2 and "tests the method" in NOT_THE_EVIDENCE and "not the evidence" in NOT_THE_EVIDENCE
    assert "**Outcomes are provisional.** 0 of the 8 readouts are adjudicated" in text
    assert "Agreement between the adjudicators is not yet measured" in text
    assert "example-1" in text and "6 pilot trials" in text
    assert "recalled no result that was disclosed after the month of its stated cutoff" in text and "buffer of 1 month" in text
    assert "0 replies gave no usable answer" in text
    # The scores and what they imply for the size of the study.
    assert "- Brier score, model minus base rate: -0.135 over 6 trials." in text    # 3 x (0.09 - 0.16), 3 x (0.16 - 0.36)
    assert "- CRPS of the log hazard ratio, model minus effect-size baseline: +0.000 over 6 trials." in text
    assert "## Sample size" in text and "standard deviation 0.071" in text and "120 trials detect a mean difference of 0.018" in text
    assert "Trials needed to detect an assumed mean difference: 0.01 needs" in text
    # No trial is named beside its forecast: the adjudicators have still to read these trials.
    assert not any(t.nct in text for t in pilot.plan.trials)


def test_the_report_gives_agreement_once_the_adjudicators_have_read_and_says_when_all_is_adjudicated():
    trials = [dataclasses.replace(t, adjudicated=True) for t in read_out_in(3, 8, 8, 9, 9, 10)]
    log = AdjudicationLog([a for t in trials for a in both_adjudicated(t.nct, "positive", readout=t.readout_date)]
                          + [adjudicated("NCT9", "first", "positive")])
    text = report([a_model_pilot(trials)], trials, adjudicator_agreement(log), written_on=TODAY)
    assert "Every readout here was adjudicated by both adjudicators." in text and "provisional" not in text
    assert "agreed on the outcome for 6 of 6 sources (Cohen's kappa not defined" in text
    assert "1 source had not been read by exactly two people" in text


def test_the_report_gives_no_scores_for_a_model_that_is_dropped_or_not_yet_forecast():
    trials = read_out_in(5, 8, 8, 9, 9, 9, 10)
    waiting = dataclasses.replace(a_model_pilot(trials), forecasts=None, reference=None)
    text = report([waiting], trials, agreement=None, written_on=TODAY)
    assert "Forecasts have not yet been made for all 6 pilot trials" in text and "### Scores" not in text
    assert "No model has forecasts for enough pilot trials" in text

    dropped = a_model_pilot(trials, recalls={"NCT4"})    # recalled a September result
    text = report([dropped], trials, agreement=None, written_on=TODAY)
    assert "recalled a result disclosed 3 months after the month of its stated cutoff" in text and "buffer of 3 months" in text
    assert "Dropped from the pilot: fewer than 5 past trials read out more than 3 months after" in text
    assert "### Scores" not in text


def test_scores_without_the_trials_a_model_said_it_knew_are_shown_only_when_they_give_no_single_forecast_away():
    trials = read_out_in(3, 3, 3, 3, 8, 8, 8, 9, 9, 9, 10, 10)

    def pilot_saying_it_knew(*ncts):
        pilot = a_model_pilot(trials, forecast_of=lambda t: 0.9 if t.nct in ("NCT5", "NCT6", "NCT7") else 0.6)
        said = [dataclasses.replace(a, known=True, positive=True, first_reported="2025-01") if a.nct in ncts else a
                for a in pilot.answers]    # the right result, placed far too early: not recall
        return dataclasses.replace(pilot, answers=tuple(said))

    three = report([pilot_saying_it_knew("NCT5", "NCT6", "NCT7")], trials, agreement=None, written_on=TODAY)
    assert "said it knew the result of 3 of them" in three and "The second line of each pair leaves those out." in three
    assert "- Brier score, model minus base rate: -0.056 over 8 trials." in three     # 3 x (0.01 - 0.16), 5 x 0
    assert "-   without the trials it said it knew: +0.000 over 5 trials." in three
    assert "right result with a date more than 3 months before the readout on record for: NCT5, NCT6, NCT7" in three

    one = report([pilot_saying_it_knew("NCT5")], trials, agreement=None, written_on=TODAY)
    assert "said it knew the result of 1 of them" in one and "would give away single forecasts" in one
    assert "without the trials it said it knew:" not in one


# --- the pilot from traces to report, through files ------------------------------------------

READOUT_MONTHS = {f"NCT{i:04d}": month for i, month in enumerate((1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 8, 8, 9, 9, 9, 10, 10), 1)}
NO_READOUT = ("NCT0021", "NCT0022")
PILOT_TRIALS = [nct for nct, month in READOUT_MONTHS.items() if month >= 8]     # seven: August onwards


def was_met(nct):
    return list(READOUT_MONTHS).index(nct) % 3 != 0


def write_study(root, roster):
    snapshot = root / "snapshots" / "2026-10-07T090006"
    snapshot.mkdir(parents=True)
    with gzip.open(snapshot / "studies.jsonl.gz", "wt", encoding="utf-8") as f:
        for nct in [*READOUT_MONTHS, *NO_READOUT, "NCT0030"]:
            measure = "Objective response rate" if nct == "NCT0030" else "Overall survival"   # NCT0030 has no scored endpoint
            f.write(json.dumps(study(nct, measure, status="COMPLETED", pcd_type="ACTUAL")) + "\n")
    (snapshot / "manifest.json").write_text(json.dumps({"data_timestamp_start": "2026-10-07T09:00:06"}))
    trace = root / "data" / "readout_trace" / "trace_A.csv"
    trace.parent.mkdir(parents=True)
    rows = [f"{nct},yes,2026-{month:02d}-10,{'met' if was_met(nct) else 'not_met'},{0.7 if was_met(nct) else 0.98},2026-{month:02d}-10"
            for nct, month in READOUT_MONTHS.items()]
    trace.write_text("nct,disclosed,first_disclosure_date,primary_result,hr_value,hr_first_public_date\n" + "\n".join(rows)
                     + "".join(f"\n{nct},no,,,," for nct in NO_READOUT) + "\nNCT0030,yes,2026-09-10,met,0.7,2026-09-10\n")
    (root / "study").mkdir()
    (root / "study" / "models.json").write_text(json.dumps(roster))
    return root


EXAMPLE_1 = {"provider": "anthropic", "model": "example-1", "training_cutoff": "2026-06", "released_on": "2026-09-21",
             "input_usd_per_million": 4.0, "output_usd_per_million": 20.0}


@pytest.fixture
def pilot_dir(tmp_path):
    """A study directory with a registry snapshot, a readout trace, and one model whose stated cutoff is June 2026."""
    return write_study(tmp_path, [EXAMPLE_1])


class Scripted:
    """A stand-in model: it recalls readouts up to June 2026, knows nothing later, and forecasts when asked to."""

    recalls_to = 6

    def __init__(self):
        self.prompts, self.probes, self.forecasting = [], [], []

    def __call__(self, spec, prompt):
        self.prompts.append(prompt)
        if "not a request to forecast" not in prompt:
            self.forecasting.append(prompt)
            return self.forecast(prompt)
        self.probes.append(prompt)
        nct = next(n for n in [*READOUT_MONTHS, *NO_READOUT] if n in prompt)
        if READOUT_MONTHS.get(nct, 99) <= self.recalls_to:
            return Reply(f'{{"result_known": true, "result": "{"positive" if was_met(nct) else "negative"}", '
                         f'"first_reported": "2026-{READOUT_MONTHS[nct]:02d}"}}', 500, 50)
        return Reply('{"result_known": false, "result": null, "first_reported": null}', 500, 50)

    def forecast(self, prompt):
        return Reply('{"probability_positive": 0.7, "hazard_ratio": 0.75, "hazard_ratio_low": 0.6, '
                     '"hazard_ratio_high": 0.95}', 1000, 400, model_served="example-1-0901")


def run(step, pilot_dir, model, *options, today=TODAY):
    return main([step, "--study", str(pilot_dir), *options], ask=model, today=today, wait=lambda seconds: None)


def pilot_forecasts(pilot_dir, name="example_1"):
    path = pilot_dir / "private" / "pilot" / f"{name}.jsonl"
    return records.read(path, Forecast) if path.exists() else []


def test_the_pilot_runs_from_traces_to_a_report(pilot_dir, capsys):
    model = Scripted()
    assert run("probe", pilot_dir, model) == 0
    assert len(model.probes) == 2 * 22 and not model.forecasting    # both probes, every past trial with a scored endpoint
    assert not any("NCT0030" in prompt for prompt in model.prompts)
    assert run("probe", pilot_dir, model) == 0
    assert len(model.probes) == 2 * 22                              # nothing is asked twice

    assert run("forecast", pilot_dir, model) == 0
    # Cutoff June, buffer one month: the seven trials that read out from August, each asked about five times.
    assert len(model.forecasting) == 7 * 5
    assert not any("COMPLETED" in prompt or "ACTUAL" in prompt for prompt in model.forecasting)
    # An outcome's time frame can name a data cut-off, which would tell a forecaster the analysis has happened.
    assert not any("up to 5 years" in prompt for prompt in model.forecasting)
    assert all("has not yet reported" in prompt for prompt in model.forecasting)
    forecasts = pilot_forecasts(pilot_dir)
    assert sorted(f.nct for f in forecasts) == PILOT_TRIALS
    assert all(f.probability_positive == pytest.approx(0.7) and f.no_forecast is None for f in forecasts)
    shown = capsys.readouterr().out
    assert "forecasts held for 7 of 7 pilot trials" in shown
    assert "0.7" not in shown and not any(nct in shown for nct in PILOT_TRIALS)    # nothing about any one forecast

    assert run("forecast", pilot_dir, model) == 0
    assert len(model.forecasting) == 7 * 5                          # forecasts already made are not bought again

    assert run("report", pilot_dir, model) == 0
    assert len(model.prompts) == 44 + 35                            # the report asks no model anything
    out = pilot_dir / "results" / "pilot"
    text = (out / "report.md").read_text()
    assert NOT_THE_EVIDENCE in text and "provisional" in text and "7 pilot trials" in text
    # Forecast 0.7 against a base rate of 8 in 12: five of the seven pilot trials were positive and two negative.
    expected = (5 * ((0.7 - 1) ** 2 - (8 / 12 - 1) ** 2) + 2 * (0.7 ** 2 - (8 / 12) ** 2)) / 7
    assert f"- Brier score, model minus base rate: {expected:+.3f} over 7 trials." in text
    recall = (out / "recall.csv").read_text().splitlines()
    assert recall[0] == "model,probe,months_after_cutoff,trials,said_known,right_result,recalled"
    assert "example-1,record,-5,2,2,2,2" in recall and "example-1,identifiers,2,2,0,0,0" in recall
    worklist = (out / "adjudication_worklist.csv").read_text().splitlines()
    assert worklist[0] == "nct,acronym,title,scored_endpoint,pilot_trial_for,adjudicated"
    assert [line.split(",")[0] for line in worklist[1:]] == PILOT_TRIALS and worklist[1].endswith("example-1,no")


def test_adjudicated_results_reshape_the_pilot_not_only_its_outcomes(pilot_dir):
    model = Scripted()
    for step in ("probe", "forecast"):
        assert run(step, pilot_dir, model) == 0
    log = pilot_dir / "adjudication" / "pilot" / "adjudications.jsonl"
    readings = (
        # The adjudicators find NCT0014 was first disclosed in March, well before the cutoff: not a pilot trial after all.
        both_adjudicated("NCT0014", "positive", readout=dt.date(2026, 3, 2), recorded_on=TODAY)
        # NCT0015 they read as negative, where the trace had it positive; NCT0016 ended without a primary analysis.
        + both_adjudicated("NCT0015", "negative", readout=dt.date(2026, 8, 10), recorded_on=TODAY)
        + both_adjudicated("NCT0016", "void", readout=dt.date(2026, 9, 10), recorded_on=TODAY)
    )
    for reading in readings:
        records.append(log, reading)

    assert run("report", pilot_dir, model) == 0

    text = (pilot_dir / "results" / "pilot" / "report.md").read_text()
    assert "Past trials: 19 with a readout" in text and "2 of the 19 readouts are adjudicated" in text
    assert "leaving 5 pilot trials" in text and "over 5 trials" in text
    assert "agreed on the outcome for 3 of 3 sources" in text
    worklist = (pilot_dir / "results" / "pilot" / "adjudication_worklist.csv").read_text()
    assert "NCT0014" not in worklist and "NCT0016" not in worklist
    assert "NCT0015,,A Study of X Versus Y,Overall survival,example-1,yes" in worklist


def test_one_model_of_the_roster_can_be_worked_with_alone(tmp_path, capsys):
    pilot_dir = write_study(tmp_path, [EXAMPLE_1, {**EXAMPLE_1, "model": "example-2"}])
    model = Scripted()
    assert run("probe", pilot_dir, model, "--model", "another-model") == 1
    assert "another-model is not in the roster" in capsys.readouterr().out and not model.prompts
    assert run("probe", pilot_dir, model, "--model", "example-2") == 0
    assert len(model.probes) == 44
    assert sorted(p.name for p in (pilot_dir / "private" / "pilot" / "probes").iterdir()) == ["example_2.jsonl"]


def test_one_probe_can_be_asked_alone_and_forecasts_wait_for_the_other(pilot_dir, capsys):
    model = Scripted()
    assert run("probe", pilot_dir, model, "--probe", "identifiers") == 0
    assert len(model.probes) == 22 and not any("Trial record" in prompt for prompt in model.probes)
    # Half the probes are not enough to choose a buffer: nothing is forecast and nothing is spent.
    assert run("forecast", pilot_dir, model) == 1
    assert "has not been probed on 22 of 44 questions" in capsys.readouterr().out and not model.forecasting
    assert run("report", pilot_dir, model) == 0
    assert "left out of the report" in capsys.readouterr().out


def test_the_pilot_stops_when_its_budget_is_spent_and_picks_up_where_it_stopped(pilot_dir, capsys):
    model = Scripted()
    # Each probe reply costs (500 * 4 + 50 * 20) / 1e6 = 0.003 dollars.
    assert run("probe", pilot_dir, model, "--budget-usd", "0.01") == 2
    shown = capsys.readouterr().out
    assert len(model.probes) == 4 and "budget" in shown and "spent $0.01" in shown
    assert run("forecast", pilot_dir, model) == 1 and not model.forecasting      # four answers are not a probe
    assert run("probe", pilot_dir, model) == 0
    assert len(model.probes) == 44


def test_a_model_without_prices_is_not_asked_anything(tmp_path, capsys):
    unpriced = {k: v for k, v in EXAMPLE_1.items() if not k.endswith("per_million")}
    model = Scripted()
    assert run("probe", write_study(tmp_path, [unpriced]), model) == 1
    assert "has no prices" in capsys.readouterr().out and not model.prompts


def test_a_trial_the_provider_could_not_answer_for_is_left_to_be_asked_again(pilot_dir, capsys):
    class DownAtFirst(Scripted):
        down = True

        def __call__(self, spec, prompt):
            if self.down and "NCT0003" in prompt:
                return Reply(None, 0, 0, failure="provider unavailable")
            return super().__call__(spec, prompt)

    model = DownAtFirst()
    assert run("probe", pilot_dir, model) == 3
    assert "2 trials could not be asked about" in capsys.readouterr().out
    probes = pilot_dir / "private" / "pilot" / "probes" / "example_1.jsonl"
    assert len(records.read(probes, ProbeRecord)) == 42 and "NCT0003" not in probes.read_text()
    assert run("forecast", pilot_dir, model) == 1 and not model.forecasting      # the probes are not complete
    model.down = False
    assert run("probe", pilot_dir, model) == 0
    assert len(records.read(probes, ProbeRecord)) == 44


def test_a_forecast_lost_to_an_outage_is_paid_for_but_not_kept_as_the_models_answer(pilot_dir, capsys):
    class DownForOneTrial(Scripted):
        down = True

        def forecast(self, prompt):
            first_trial_so_far = sum(PILOT_TRIALS[0] in p for p in self.forecasting)
            if self.down and PILOT_TRIALS[0] in prompt and first_trial_so_far > 2:
                return Reply(None, 0, 0, failure="provider unavailable")    # down after two replies about this trial
            return super().forecast(prompt)

    model = DownForOneTrial()
    assert run("probe", pilot_dir, model) == 0
    capsys.readouterr()
    assert run("forecast", pilot_dir, model) == 3
    shown = capsys.readouterr().out
    assert "forecasts held for 6 of 7 pilot trials" in shown and "1 trial could not be asked about" in shown
    # Six forecasts of five replies and two replies of the seventh, at (1000 * 4 + 400 * 20) / 1e6 dollars each.
    assert f"spent ${32 * 0.012:.2f}" in shown
    assert sorted(f.nct for f in pilot_forecasts(pilot_dir)) == PILOT_TRIALS[1:]
    assert run("report", pilot_dir, model) == 0
    assert "Forecasts have not yet been made for all 7 pilot trials" in (pilot_dir / "results" / "pilot" / "report.md").read_text()
    model.down = False
    assert run("forecast", pilot_dir, model) == 0
    assert sorted(f.nct for f in pilot_forecasts(pilot_dir)) == PILOT_TRIALS


def test_no_forecast_is_bought_for_a_model_that_is_dropped(pilot_dir, capsys):
    class RecallsSeptember(Scripted):
        recalls_to = 9

    model = RecallsSeptember()
    assert run("probe", pilot_dir, model) == 0
    assert run("forecast", pilot_dir, model) == 0
    assert "dropped from the pilot: fewer than 5 past trials read out more than 3 months after" in capsys.readouterr().out
    assert not model.forecasting and not pilot_forecasts(pilot_dir)
    assert run("report", pilot_dir, model) == 0
    assert (pilot_dir / "results" / "pilot" / "adjudication_worklist.csv").read_text().count("\n") == 1    # the header alone


def test_answers_to_an_earlier_wording_of_a_probe_are_kept_but_not_counted(pilot_dir):
    probes = pilot_dir / "private" / "pilot" / "probes" / "example_1.jsonl"
    earlier_wording = dataclasses.replace(answer("NCT0020", True, was_met("NCT0020"), first_reported="2026-10"), probe_version="1")
    records.append(probes, earlier_wording)
    model = Scripted()
    assert run("probe", pilot_dir, model) == 0
    kept = records.read(probes, ProbeRecord)
    assert len(model.probes) == 44 and len(kept) == 45 and kept[0] == earlier_wording
    assert run("forecast", pilot_dir, model) == 0
    # The earlier answer recalled an October result; counted, it would have stretched the buffer and dropped the model.
    assert len(pilot_forecasts(pilot_dir)) == 7


def test_a_model_the_provider_will_not_serve_stops_the_command_without_a_traceback(pilot_dir, capsys):
    def not_served(spec, prompt):
        raise ModelUnavailable("anthropic would not serve example-1 (status 401): check the key and the name")

    assert run("probe", pilot_dir, not_served) == 1
    assert "NOT DONE: anthropic would not serve example-1" in capsys.readouterr().out
