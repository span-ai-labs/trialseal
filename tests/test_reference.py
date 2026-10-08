"""The reference set: traced past trials, the base rates and hazard-ratio distributions drawn from them."""
import csv
import datetime as dt
import gzip
import json

import pytest

from registry_records import study
from study_records import adjudicated, both_adjudicated, candidate
from trialforecast import records, scoring
from trialforecast.adjudication import AdjudicationLog, awaiting_result, results
from trialforecast.reference import (
    NotFrozen, adjudication_sample, base_rate_forecaster, base_rate_table, frozen_base_rates, hazard_ratio_table, main,
    reference_trials, trace_accuracy,
)
from trialforecast.screening import DesignReview

TODAY = dt.date(2026, 10, 9)
HEADER = "nct,disclosed,first_disclosure_date,primary_result,which_endpoint,hr_value,hr_first_public_date,confidence\n"


def trace(directory, rows, name="trace_A.csv"):
    path = directory / name
    path.write_text(HEADER + "\n".join(rows) + "\n")
    return path


def test_a_wilson_interval_stays_inside_zero_and_one_and_narrows_with_more_trials():
    low, high = scoring.wilson_interval(27, 39)
    # By hand: share 0.6923, z 1.96; centre (0.6923 + 0.0492) / 1.0985 = 0.6751; half-width 0.1393.
    assert (low, high) == (pytest.approx(0.5358, abs=1e-3), pytest.approx(0.8144, abs=1e-3))
    assert scoring.wilson_interval(0, 5)[0] == 0.0 and scoring.wilson_interval(5, 5)[1] == 1.0
    assert scoring.wilson_interval(270, 390)[1] - scoring.wilson_interval(270, 390)[0] < high - low
    assert scoring.wilson_interval(0, 0) == (None, None)


# --- each trial's place ----------------------------------------------------------------------


def test_each_traced_trial_has_one_place_in_the_reference_set(tmp_path):
    candidates = {f"NCT{i}": candidate(f"NCT{i}") for i in range(1, 16)}
    for tagged in ("NCT9", "NCT10"):
        candidates[tagged] = candidate(tagged, "Overall survival (non-inferiority)")
    path = trace(tmp_path, [
        "NCT1,yes,2025-03-01,met,OS,0.70,2025-03-01,high",
        "NCT2,yes,2025-03-01,stopped_futility,OS,,,medium",
        "NCT3,no,,terminated_no_analysis,,,,high",
        "NCT4,no,,,,,,high",
        "NCT5,yes,2025-03-01,mixed,OS,,,high",                 # in doubt until the adjudicators read it
        "NCT6,yes,2025-03-01,met,OS,0.5,2025-03-01,low",       # low confidence: does not count until re-checked
        "NCT7,yes,2025-03-01,met,OS,0.5,2025-09-02,high",      # hazard ratio a day past six months: the result counts, it does not
        "NCT8,yes,2025-03-01,not_met,OS,,,high",               # not a candidate in the snapshot: left out
        "NCT9,yes,2025-03-01,met,OS,,,high",                   # tagged for exclusion review, nobody has ruled
        "NCT10,yes,2025-03-01,met,OS,,,high",                  # design ruled out
        "NCT11,unclear,2025-03-01,met,OS,0.6,2025-03-01,high", # the reader was not sure it was disclosed: in doubt
        "NCT12,yes,2025-03-01,met,OS,0.6,2025-03-01,Low",      # confidence however it is spelt
        "NCT13,yes,2025-03-01,met,OS,0.6,2025-03-01,",         # and no confidence given is not high confidence
        "NCT14,yes,2025-03-01,met,PFS,0.45,2025-03-01,high",   # a hazard ratio traced for another endpoint than the scored one
        "NCT15,yes,2025-03-01,met,OS,0.6,2023-07-01,high",     # a hazard ratio dated long before the readout
    ])
    del candidates["NCT8"]
    excluded = DesignReview("NCT10", "exclude", "non-inferiority primary", "Abhijoy Sarkar", TODAY)
    trials = {t.nct: t for t in reference_trials([path], candidates, design_reviews=[excluded])}
    assert {nct: t.place for nct, t in trials.items()} == {
        "NCT1": "positive", "NCT2": "negative", "NCT3": "void", "NCT4": "unresolved", "NCT5": "in_doubt",
        "NCT6": "awaiting_recheck", "NCT7": "positive", "NCT9": "awaiting_design_review", "NCT10": "excluded_design",
        "NCT11": "in_doubt", "NCT12": "awaiting_recheck", "NCT13": "awaiting_recheck", "NCT14": "positive", "NCT15": "positive"}
    assert {nct: trials[nct].hazard_ratio for nct in ("NCT1", "NCT7", "NCT14", "NCT15")} == {
        "NCT1": 0.70, "NCT7": None, "NCT14": None, "NCT15": None}
    assert trials["NCT1"].reference_class == "industry/overall_survival"


def test_a_trial_traced_in_two_files_is_refused(tmp_path):
    first = trace(tmp_path, ["NCT1,yes,2025-03-01,met,OS,,,high"])
    second = trace(tmp_path, ["NCT1,yes,2025-03-01,not_met,OS,,,high"], name="trace_B.csv")
    with pytest.raises(ValueError, match="NCT1 is traced in both trace_A and trace_B"):
        reference_trials([first, second], {"NCT1": candidate("NCT1")})


def test_a_recheck_replaces_the_traced_row_and_the_adjudicators_stand_above_both(tmp_path):
    candidates = {nct: candidate(nct) for nct in ("NCT1", "NCT2", "NCT3", "NCT4", "NCT5")}
    path = trace(tmp_path, ["NCT1,yes,2025-03-01,met,OS,,,low", "NCT2,yes,2025-03-01,met,OS,,,high",
                            "NCT3,unclear,2025-03-01,unclear,,,,low", "NCT4,yes,2025-03-01,met,OS,,,low",
                            "NCT5,yes,2025-03-01,met,OS,,,high"])
    rechecks = trace(tmp_path, ["NCT1,yes,2025-01-15,not_met,OS,,,high", "NCT3,no,,,,,,medium",
                                "NCT4,yes,2025-03-01,met,OS,,,low"], name="rechecks.csv")
    log = AdjudicationLog([*both_adjudicated("NCT2", "negative", readout=dt.date(2025, 2, 20)),
                           adjudicated("NCT5", "first", "negative", readout=dt.date(2025, 3, 1))])   # read by one so far
    trials = {t.nct: t for t in reference_trials([path], candidates, rechecks=[rechecks], adjudicated=results(log, TODAY),
                                                 awaiting_adjudication=awaiting_result(log, TODAY))}
    assert (trials["NCT1"].place, trials["NCT1"].readout_date, trials["NCT1"].rechecked) == ("negative", dt.date(2025, 1, 15), True)
    assert (trials["NCT2"].place, trials["NCT2"].readout_date, trials["NCT2"].adjudicated) == ("negative", dt.date(2025, 2, 20), True)
    assert trials["NCT3"].place == "unresolved"
    assert trials["NCT4"].place == "in_doubt"        # a re-check that is itself unsure settles nothing
    assert trials["NCT5"].place == "in_doubt"        # the adjudicators have begun and not finished: the trace no longer counts


# --- the tables --------------------------------------------------------------------------------


def a_class(first, n, measure, positive, with_ratio, sponsor="INDUSTRY", ratio=0.70):
    """`n` trials of one reference class, numbered from `first`: so many positive, so many with a hazard ratio."""
    endpoint = "PFS" if measure.startswith("Progression") else "OS"
    rows, candidates = [], {}
    for i in range(n):
        nct = f"NCT{first + i:04d}"
        candidates[nct] = candidate(nct, measure, cls=sponsor)
        hazard_ratio = f"{ratio + i / 100:.2f},2025-03-01" if i < with_ratio else ","
        rows.append(f"{nct},yes,2025-03-01,{'met' if i < positive else 'not_met'},{endpoint},{hazard_ratio},high")
    return rows, candidates


def reference_set(tmp_path, *classes, extra_rows=()):
    rows, candidates = list(extra_rows), {}
    for class_rows, class_candidates in classes:
        rows += class_rows
        candidates.update(class_candidates)
    return reference_trials([trace(tmp_path, rows)], candidates), candidates


SURVIVAL = dict(first=1, n=36, measure="Overall survival", positive=26, with_ratio=20, ratio=0.50)
PROGRESSION = dict(first=101, n=6, measure="Progression-free survival", positive=5, with_ratio=6, ratio=0.60)
ACADEMIC = dict(first=201, n=24, measure="Overall survival", positive=8, with_ratio=12, sponsor="OTHER", ratio=0.85)


def test_the_base_rate_table_counts_only_clear_results_and_shows_the_rest_beside_them(tmp_path):
    others = ["NCT0901,no,,terminated_no_analysis,,,,high", "NCT0902,no,,terminated_no_analysis,,,,high",
              "NCT0903,no,,,,,,high", "NCT0904,no,,,,,,high", "NCT0905,yes,2025-03-01,mixed,OS,,,high"]
    trials, candidates = reference_set(tmp_path, a_class(**SURVIVAL), a_class(**PROGRESSION), a_class(**ACADEMIC), extra_rows=others)
    candidates.update({f"NCT090{i}": candidate(f"NCT090{i}") for i in range(1, 6)})
    trials = reference_trials([tmp_path / "trace_A.csv"], candidates)
    table = {row["reference_class"]: row for row in base_rate_table(trials)}
    survival = table["industry/overall_survival"]
    assert (survival["trials"], survival["positive"], survival["void"], survival["unresolved"], survival["not_yet_counted"]) == (36, 26, 2, 2, 1)
    assert survival["rate"] == pytest.approx(26 / 36) and survival["interval"] == pytest.approx(scoring.wilson_interval(26, 36))
    assert table["industry/progression"]["rate"] == pytest.approx(5 / 6)
    assert (table["industry"]["trials"], table["industry"]["rate"]) == (42, pytest.approx(31 / 42))
    assert (table["non_industry"]["trials"], table["non_industry"]["rate"]) == (24, pytest.approx(8 / 24))
    assert (table["all sponsors"]["trials"], table["all sponsors"]["rate"]) == (66, pytest.approx(39 / 66))
    assert table["non_industry/progression"]["trials"] == 0 and table["non_industry/progression"]["rate"] is None


def test_hazard_ratios_are_summarised_on_the_log_scale_for_each_reference_class(tmp_path):
    trials, _ = reference_set(tmp_path, a_class(**SURVIVAL), a_class(**PROGRESSION))
    table = {row["reference_class"]: row for row in hazard_ratio_table(trials)}
    survival = table["industry/overall_survival"]
    ratios = sorted(0.50 + i / 100 for i in range(20))
    assert survival["trials"] == 20 and survival["median"] == pytest.approx((ratios[9] * ratios[10]) ** 0.5, rel=1e-3)
    assert survival["low"] < survival["median"] < survival["high"]
    assert table["industry/progression"]["trials"] == 6


def test_a_reference_class_with_too_few_trials_takes_its_sponsor_types_figures(tmp_path):
    trials, candidates = reference_set(tmp_path, a_class(**SURVIVAL), a_class(**PROGRESSION), a_class(**ACADEMIC))
    frozen = frozen_base_rates(trials, TODAY)
    assert frozen["frozen_on"] == "2026-10-09"
    assert frozen["base_rates"]["industry/overall_survival"] == pytest.approx(26 / 36)
    # Six progression trials are too few to stand alone: the class takes the rate of all industry-led trials,
    # not the rate of all sponsors together.
    assert frozen["base_rates"]["industry/progression"] == pytest.approx(31 / 42)
    assert frozen["base_rates"]["non_industry/progression"] == pytest.approx(8 / 24)
    assert frozen["pooled"] == ["industry/other_time_to_event", "industry/progression", "non_industry/other_time_to_event",
                                "non_industry/progression"]
    # Hazard ratios are pooled by their own bar of ten: industry progression has six.
    assert "industry/progression" in frozen["hazard_ratios_pooled"] and "industry/overall_survival" not in frozen["hazard_ratios_pooled"]
    assert frozen["hazard_ratios"]["industry/progression"] == frozen["hazard_ratios"]["industry/other_time_to_event"]
    median, low, high = frozen["hazard_ratios"]["non_industry/overall_survival"]
    assert 0.85 < low < median < high
    assert frozen["counts"]["industry/progression"] == {"clear_results": 6, "hazard_ratios": 6}


@pytest.mark.parametrize("n, stands_alone", [(20, True), (19, False)])
def test_twenty_clear_results_let_a_class_keep_its_own_base_rate(tmp_path, n, stands_alone):
    small = dict(first=101, n=n, measure="Progression-free survival", positive=n, with_ratio=0)
    trials, _ = reference_set(tmp_path, a_class(**SURVIVAL), a_class(**small), a_class(**ACADEMIC))
    frozen = frozen_base_rates(trials, TODAY)
    assert (frozen["base_rates"]["industry/progression"] == 1.0) is stands_alone
    assert ("industry/progression" in frozen["pooled"]) is not stands_alone


@pytest.mark.parametrize("with_ratio, stands_alone", [(10, True), (9, False)])
def test_ten_hazard_ratios_let_a_class_keep_its_own_typical_hazard_ratio(tmp_path, with_ratio, stands_alone):
    small = dict(first=101, n=25, measure="Progression-free survival", positive=20, with_ratio=with_ratio, ratio=0.30)
    trials, _ = reference_set(tmp_path, a_class(**SURVIVAL), a_class(**small), a_class(**ACADEMIC))
    frozen = frozen_base_rates(trials, TODAY)
    assert (frozen["hazard_ratios"]["industry/progression"][0] < 0.40) is stands_alone
    assert ("industry/progression" in frozen["hazard_ratios_pooled"]) is not stands_alone


def test_nothing_is_frozen_for_a_sponsor_type_with_too_little_to_set_a_bar(tmp_path):
    few = dict(first=201, n=19, measure="Overall survival", positive=6, with_ratio=12, sponsor="OTHER")
    trials, _ = reference_set(tmp_path, a_class(**SURVIVAL), a_class(**few))
    with pytest.raises(NotFrozen, match="non_industry trials have 19 clear results"):
        frozen_base_rates(trials, TODAY)


def test_the_sample_for_the_adjudicators_is_drawn_from_trials_traced_as_read_out_or_void(tmp_path):
    others = ["NCT0901,no,,terminated_no_analysis,,,,high", "NCT0903,no,,,,,,high", "NCT0905,yes,2025-03-01,mixed,OS,,,high"]
    trials, candidates = reference_set(tmp_path, a_class(**SURVIVAL), a_class(**PROGRESSION), extra_rows=others)
    candidates.update({nct: candidate(nct) for nct in ("NCT0901", "NCT0903", "NCT0905")})
    trials = reference_trials([tmp_path / "trace_A.csv"], candidates)
    sample = adjudication_sample(trials, 12)
    assert len(sample) == 12 and sample == adjudication_sample(trials, 12) == sorted(sample)
    everything = adjudication_sample(trials, 500)
    assert len(everything) == 43 and "NCT0901" in everything and "NCT0903" not in everything and "NCT0905" not in everything


def test_trace_accuracy_is_how_often_one_readers_trace_matched_the_adjudicators(tmp_path):
    trials, _ = reference_set(tmp_path, a_class(**SURVIVAL))
    log = AdjudicationLog(
        both_adjudicated("NCT0001", "positive", readout=dt.date(2025, 3, 1))           # as traced
        + both_adjudicated("NCT0002", "negative", readout=dt.date(2025, 3, 1))         # traced as positive
        + both_adjudicated("NCT0003", "positive", readout=dt.date(2024, 11, 1)))       # traced four months late
    assert trace_accuracy(trials, results(log, TODAY)) == {
        "trials": 3, "outcome_matched": 2, "date_within_a_week": 2, "date_later_than_adjudicated": 1}


# --- the command, through files -------------------------------------------------------------------


@pytest.fixture
def study_dir(tmp_path):
    """Thirty industry-led and twenty-four other overall-survival trials, each traced; one trace is of low confidence."""
    snapshot = tmp_path / "snapshots" / "2026-10-08T090005"
    snapshot.mkdir(parents=True)
    rows = []
    with gzip.open(snapshot / "studies.jsonl.gz", "wt", encoding="utf-8") as f:
        for i in range(1, 55):
            nct = f"NCT{i:04d}"
            f.write(json.dumps(study(nct, "Overall survival", pcd="2025-03", cls="INDUSTRY" if i <= 30 else "OTHER")) + "\n")
            rows.append(f"{nct},yes,2025-03-01,{'met' if i % 3 else 'not_met'},OS,0.7,2025-03-01,{'low' if i == 30 else 'high'}")
    (snapshot / "manifest.json").write_text(json.dumps({"data_timestamp_start": "2026-10-08T09:00:05"}))
    (tmp_path / "data" / "readout_trace").mkdir(parents=True)
    trace(tmp_path / "data" / "readout_trace", rows)
    return tmp_path


def run(study_dir, step, today=TODAY):
    return main([step, "--study", str(study_dir)], today=today)


def test_the_reference_command_writes_the_tables_and_the_report(study_dir, capsys):
    assert run(study_dir, "report") == 0
    assert "54 past trials; industry-led base rate 69.0% (20 of 29)" in capsys.readouterr().out
    out = study_dir / "results" / "reference_set"
    with (out / "base_rates.csv").open() as f:
        table = {row["reference_class"]: row for row in csv.DictReader(f)}
    assert (table["industry/overall_survival"]["trials"], table["industry/overall_survival"]["positive"]) == ("29", "20")
    assert table["industry/overall_survival"]["not_yet_counted"] == "1" and table["non_industry"]["trials"] == "24"
    text = (out / "report.md").read_text()
    assert "provisional" in text and "43.4%" in text and "Yamamoto" in text and "1 trial awaits a re-check" in text
    assert "The adjudicators have not yet read their sample" in text
    assert (out / "hazard_ratios.csv").exists() and (out / "trials.csv").read_text().count("\n") == 55


def test_the_adjudicators_sample_is_drawn_once_and_shows_nothing_of_what_the_trace_found(study_dir, capsys):
    assert run(study_dir, "sample") == 0
    worklist = study_dir / "adjudication" / "reference" / "worklist.csv"
    listed = worklist.read_text().splitlines()
    assert listed[0] == "nct,acronym,title,scored_endpoint" and len(listed) == 41 and "met" not in "".join(listed[1:])
    drawn = json.loads((study_dir / "adjudication" / "reference" / "sample.json").read_text())
    assert drawn["trials"] == [line.split(",")[0] for line in listed[1:]] and drawn["drawn_on"] == "2026-10-09"
    # More trials are traced afterwards: the sample the adjudicators were given does not change.
    more = trace(study_dir / "data" / "readout_trace", [], name="trace_B.csv")
    more.write_text(HEADER + "".join(f"NCT{i:04d},yes,2025-03-01,met,OS,,,high\n" for i in range(1, 2)).replace("NCT0001", "NCT0100"))
    assert run(study_dir, "sample", today=TODAY + dt.timedelta(days=5)) == 0
    assert json.loads((study_dir / "adjudication" / "reference" / "sample.json").read_text()) == drawn


def test_base_rates_are_frozen_once_and_only_when_fit_to_be(study_dir, capsys):
    frozen = study_dir / "study" / "base_rates.json"

    def refused(why):
        assert run(study_dir, "freeze") == 1 and not frozen.exists()
        assert why in capsys.readouterr().out

    refused("1 trial are not yet counted")                                    # NCT0030 awaits a re-check
    trace(study_dir / "data" / "readout_trace", ["NCT0030,yes,2025-03-01,not_met,OS,,,high"], name="rechecks.csv")
    refused("the adjudicators' sample has not been drawn")
    run(study_dir, "sample")
    refused("have not settled 40 of the 40 trials in their sample")
    drawn = json.loads((study_dir / "adjudication" / "reference" / "sample.json").read_text())["trials"]
    for nct in drawn:
        for reading in both_adjudicated(nct, "positive" if int(nct[3:]) % 3 else "negative", readout=dt.date(2025, 3, 1),
                                        recorded_on=TODAY, hazard_ratio=0.7, hazard_ratio_endpoint="Overall survival"):
            records.append(study_dir / "adjudication" / "reference" / "adjudications.jsonl", reading)
    capsys.readouterr()

    assert run(study_dir, "freeze") == 0
    figures = json.loads(frozen.read_text())
    assert figures["base_rates"]["industry/overall_survival"] == pytest.approx(20 / 30)
    assert figures["adjudicated"] == 40 and sorted(figures["made_from"]) == ["rechecks.csv", "trace_A.csv"]
    assert all(len(digest) == 64 for digest in figures["made_from"].values())
    forecaster = base_rate_forecaster(frozen)
    forecast = forecaster.forecast(candidate("NCT9999"), TODAY)
    assert forecast.probability_positive == pytest.approx(20 / 30) and forecaster.version == "frozen 2026-10-09"
    assert run(study_dir, "freeze") == 1 and "already frozen" in capsys.readouterr().out


def test_a_trace_that_cannot_be_read_stops_the_command_without_a_traceback(study_dir, capsys):
    bad = study_dir / "data" / "readout_trace" / "trace_B.csv"
    bad.write_text(HEADER + "NCT0100,yes,2025-03-01,met,OS,0.70 (0.55-0.89),2025-03-01,high\n")
    assert run(study_dir, "report") == 1
    assert "NOT DONE: NCT0100: hazard ratio '0.70 (0.55-0.89)' is not a number" in capsys.readouterr().out
    bad.write_text(HEADER.replace("disclosed,", "") + "NCT0100,2025-03-01,met,OS,,,high\n")
    assert run(study_dir, "report") == 1 and "says whether its result was disclosed" in capsys.readouterr().out
    assert main(["report", "--study", str(study_dir / "nowhere")], today=TODAY) == 1
