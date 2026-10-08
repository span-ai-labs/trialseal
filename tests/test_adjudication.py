"""Adjudication rules: how two people's readings of a trial's sources become one result."""
import datetime as dt
import random

import pytest

from trialforecast import records
from trialforecast.adjudication import (
    Adjudication, AdjudicationLog, ForecastAccess, NotBlind, Reconciliation, Withdrawal, awaiting_result,
    derive_outcome, read_log, record_adjudication, record_forecast_access, record_reconciliation, results, set_aside,
    unsettled_sources,
)

TOPLINE_DAY = dt.date(2027, 3, 14)
PAPER_DAY = dt.date(2027, 11, 2)
LATER = dt.date(2028, 5, 1)
TOPLINE = "https://example.test/topline"


def adjudicated(nct="NCT1", adjudicator="first", outcome="positive", *, source_type="press_release_or_filing",
                source=TOPLINE, disclosed_on=TOPLINE_DAY, recorded_on=None, hazard_ratio=None,
                hazard_ratio_endpoint=None, language="en", original_text="The trial met its primary endpoint.",
                translation=None, endpoint_rule="single", endpoint_results=None, early_stop=None):
    if endpoint_results is None:
        endpoint_results = () if early_stop else (("met",) if outcome == "positive" else ("not_met",))
    if hazard_ratio is not None and hazard_ratio_endpoint is None:
        hazard_ratio_endpoint = "Overall survival"
    return Adjudication(
        nct=nct, adjudicator=adjudicator, recorded_on=recorded_on or disclosed_on, source_type=source_type,
        source=source, disclosed_on=disclosed_on, language=language, original_text=original_text,
        translation=translation, endpoint_rule=endpoint_rule, endpoint_results=endpoint_results,
        early_stop=early_stop, outcome=outcome, hazard_ratio=hazard_ratio, hazard_ratio_endpoint=hazard_ratio_endpoint,
    )


def both(**kwargs):
    return [adjudicated(adjudicator="first", **kwargs), adjudicated(adjudicator="second", **kwargs)]


def paper(**kwargs):
    return dict(source_type="paper_or_regulator", source="doi:10.0000/example", disclosed_on=PAPER_DAY, **kwargs)


def reconciled(recorded_on=TOPLINE_DAY + dt.timedelta(days=2), adjudicators=("first", "second"), **kwargs):
    fields = dict(nct="NCT1", source_type="press_release_or_filing", source=TOPLINE, outcome="positive",
                  hazard_ratio=0.60, hazard_ratio_endpoint="Overall survival", disclosed_on=TOPLINE_DAY,
                  reason="0.95 was the upper confidence limit, not the estimate")
    return Reconciliation(**{**fields, **kwargs}, adjudicators=adjudicators, recorded_on=recorded_on)


def log_of(adjudications, **kwargs):
    return AdjudicationLog(adjudications=adjudications, **kwargs)


def result_of(adjudications, on=LATER, **kwargs):
    return results(log_of(adjudications, **kwargs), on)["NCT1"]


HAZARD_RATIO_DISPUTE = [adjudicated(adjudicator="first", hazard_ratio=0.60),
                        adjudicated(adjudicator="second", hazard_ratio=0.95)]


# --- what positive, negative and void mean -----------------------------------------


def test_outcome_follows_from_the_endpoint_rule_and_what_each_primary_endpoint_showed():
    assert derive_outcome("single", ("met",)) == "positive"
    assert derive_outcome("single", ("not_met",)) == "negative"
    # Endpoints that each suffice: one is enough, and the others need not have reported yet.
    assert derive_outcome("any_of", ("met", "not_reported")) == "positive"
    assert derive_outcome("any_of", ("not_met", "not_met")) == "negative"
    assert derive_outcome("any_of", ("not_met", "not_reported")) is None
    # Co-primary endpoints: all are needed, and one miss is enough to fail.
    assert derive_outcome("co_primary", ("met", "met")) == "positive"
    assert derive_outcome("co_primary", ("met", "not_met")) == "negative"
    assert derive_outcome("co_primary", ("met", "not_reported")) is None


def test_early_stops_decide_the_outcome():
    assert derive_outcome("single", (), early_stop="efficacy") == "positive"
    assert derive_outcome("single", (), early_stop="futility") == "negative"
    assert derive_outcome("co_primary", (), early_stop="no_analysis") == "void"


def test_an_adjudication_cannot_record_an_outcome_its_own_basis_does_not_support():
    for unsupported in (
        dict(endpoint_rule="co_primary", endpoint_results=("met", "not_met")),
        dict(endpoint_rule="co_primary", endpoint_results=("met", "not_reported")),
        dict(endpoint_rule="co_primary", endpoint_results=("met",)),              # a co-primary design has several
        dict(endpoint_rule="single", endpoint_results=("met", "not_met")),        # a single design has one
        dict(endpoint_rule="co_primary", endpoint_results=("met", "not_met"), early_stop="efficacy"),
    ):
        with pytest.raises(ValueError):
            adjudicated(outcome="positive", **unsupported)
    assert adjudicated(endpoint_rule="any_of", endpoint_results=("met", "not_reported")).outcome == "positive"


# --- what an adjudication must hold --------------------------------------------------


def test_a_non_english_disclosure_needs_its_original_text_and_a_translation():
    with pytest.raises(ValueError, match="translation"):
        adjudicated(language="zh", original_text="该研究达到了主要终点。")
    with pytest.raises(ValueError, match="language"):
        adjudicated(language=" ", translation="The study met its primary endpoint.")
    with pytest.raises(ValueError, match="original text"):
        adjudicated(original_text=" ")
    in_chinese = adjudicated(language="ZH", original_text="该研究达到了主要终点。",
                             translation="The study met its primary endpoint.")
    assert in_chinese.language == "zh"
    assert records.from_line(Adjudication, records.to_line(in_chinese)) == in_chinese


def test_the_result_carries_the_language_of_the_readout():
    chinese = dict(language="zh", original_text="该研究达到了主要终点。", translation="The study met its primary endpoint.")
    assert result_of(both(**chinese) + both(**paper())).disclosure_language == "zh"


def test_an_adjudication_needs_a_ranked_source_disclosed_before_it_was_recorded():
    with pytest.raises(ValueError, match="source type"):
        adjudicated(source_type="tweet")
    with pytest.raises(ValueError, match="before"):
        adjudicated(disclosed_on=TOPLINE_DAY, recorded_on=TOPLINE_DAY - dt.timedelta(days=1))
    with pytest.raises(ValueError):
        adjudicated(adjudicator="  ")


def test_a_hazard_ratio_must_say_which_endpoint_it_is_for():
    with pytest.raises(ValueError, match="endpoint"):
        adjudicated(hazard_ratio=0.7, hazard_ratio_endpoint=" ")
    with pytest.raises(ValueError):
        adjudicated(hazard_ratio=-1)
    assert result_of(both(hazard_ratio=0.7, hazard_ratio_endpoint="PFS by BICR")).hazard_ratio_endpoint == "PFS by BICR"


# --- agreement ---------------------------------------------------------------------


def test_a_trial_has_a_result_only_when_two_adjudicators_agree():
    log = log_of([
        *both(nct="NCT1"),
        adjudicated(nct="NCT2", adjudicator="first"),
        adjudicated(nct="NCT3", adjudicator="first"), adjudicated(nct="NCT3", adjudicator="second", outcome="negative"),
        adjudicated(nct="NCT4", adjudicator="first"), adjudicated(nct="NCT4", adjudicator="First "),
    ])
    assert set(results(log, LATER)) == {"NCT1"}
    assert awaiting_result(log, LATER) == {
        "NCT2": "awaiting second adjudication", "NCT3": "disagreement", "NCT4": "awaiting second adjudication"}


def test_adjudicators_must_agree_on_everything_they_read_from_the_source():
    for difference in (dict(hazard_ratio=0.95), dict(disclosed_on=dt.date(2027, 3, 10)),
                       dict(endpoint_rule="any_of", endpoint_results=("met", "not_reported"))):
        log = log_of([adjudicated(adjudicator="first", hazard_ratio=0.60, recorded_on=TOPLINE_DAY),
                      adjudicated(adjudicator="second", **{"hazard_ratio": 0.60, "recorded_on": TOPLINE_DAY, **difference})])
        assert results(log, LATER) == {}, difference
        assert awaiting_result(log, LATER) == {"NCT1": "disagreement"}, difference


def test_the_result_does_not_depend_on_the_order_of_the_log():
    entries = (both(source="release A", outcome="positive", hazard_ratio=0.70)
               + both(source="release B", outcome="negative", hazard_ratio=0.90)
               + [adjudicated(adjudicator="first", outcome="negative", **paper()),
                  adjudicated(adjudicator="first", outcome="negative", hazard_ratio=0.93,
                              recorded_on=PAPER_DAY + dt.timedelta(days=1), **paper()),
                  adjudicated(adjudicator="second", outcome="negative", hazard_ratio=0.93,
                              recorded_on=PAPER_DAY + dt.timedelta(days=2), **paper())])
    expected = result_of(entries)
    assert (expected.outcome, expected.hazard_ratio) == ("negative", 0.70)
    shuffler = random.Random(0)
    for _ in range(50):
        shuffled = entries[:]
        shuffler.shuffle(shuffled)
        assert result_of(shuffled) == expected


# --- reconciliation and revision -------------------------------------------------------


def test_a_disagreement_blocks_the_result_until_it_is_reconciled_with_a_reason():
    with pytest.raises(ValueError, match="reason"):
        reconciled(reason=" ")
    result = result_of(HAZARD_RATIO_DISPUTE, reconciliations=[reconciled()])
    assert (result.outcome, result.hazard_ratio) == ("positive", 0.60)
    # Before the reconciliation was recorded, the trial still had no result.
    assert results(log_of(HAZARD_RATIO_DISPUTE, reconciliations=[reconciled()]), TOPLINE_DAY + dt.timedelta(days=1)) == {}


def test_a_reconciliation_must_settle_a_recorded_disagreement_between_its_own_adjudicators():
    one_reading = [adjudicated(adjudicator="first", hazard_ratio=0.60)]
    in_agreement = both(hazard_ratio=0.60)
    for adjudications, reconciliation in (
        (one_reading, reconciled()),                                        # nobody disagreed: one reading only
        (in_agreement, reconciled(hazard_ratio=0.5)),                       # nobody disagreed: they agree
        (HAZARD_RATIO_DISPUTE, reconciled(adjudicators=("third", "fourth"))),  # not the people who read it
        (HAZARD_RATIO_DISPUTE, reconciled(source="some other source")),     # a source nobody adjudicated
        (HAZARD_RATIO_DISPUTE, reconciled(recorded_on=TOPLINE_DAY - dt.timedelta(days=1), disclosed_on=TOPLINE_DAY - dt.timedelta(days=5))),
    ):
        with pytest.raises(ValueError, match="does not settle"):
            results(log_of(adjudications, reconciliations=[reconciliation]), LATER)
    for invalid in (dict(outcome="void"), dict(hazard_ratio=-1), dict(source_type="tweet"), dict(adjudicators=("first",))):
        with pytest.raises(ValueError):
            reconciled(**invalid)


def test_a_reconciliation_is_checked_before_it_enters_the_log(tmp_path):
    log_file = tmp_path / "reconciliation.jsonl"
    with pytest.raises(ValueError, match="does not settle"):
        record_reconciliation(log_file, reconciled(), log_of(both(hazard_ratio=0.60)), today=reconciled().recorded_on)
    assert not log_file.exists()
    record_reconciliation(log_file, reconciled(), log_of(HAZARD_RATIO_DISPUTE), today=reconciled().recorded_on)
    assert records.read(log_file, Reconciliation) == [reconciled()]


def test_changing_an_entry_to_match_does_not_dissolve_a_disagreement():
    log = HAZARD_RATIO_DISPUTE + [adjudicated(adjudicator="second", hazard_ratio=0.60,
                                              recorded_on=TOPLINE_DAY + dt.timedelta(days=1))]
    assert awaiting_result(log_of(log), LATER) == {"NCT1": "disagreement"}
    assert result_of(log, reconciliations=[reconciled()]).hazard_ratio == 0.60


def test_an_adjudicator_may_correct_their_own_entry_before_anyone_disagrees(tmp_path):
    log_file = tmp_path / "adjudication.jsonl"
    entries = [
        adjudicated(adjudicator="first", outcome="negative"),
        adjudicated(adjudicator="first", recorded_on=TOPLINE_DAY + dt.timedelta(days=1)),   # first corrects themselves
        adjudicated(adjudicator="second", recorded_on=TOPLINE_DAY + dt.timedelta(days=2)),
    ]
    for entry in entries:
        record_adjudication(log_file, entry, forecast_access=[], today=entry.recorded_on)
    kept = records.read(log_file, Adjudication)
    assert kept == entries  # the log keeps the superseded entry
    assert result_of(kept).outcome == "positive"


def test_a_mistaken_entry_can_be_withdrawn_with_a_reason():
    mistaken = adjudicated(adjudicator="first", outcome="negative", source="wrong link", recorded_on=TOPLINE_DAY)
    log = both() + [mistaken]
    assert awaiting_result(log_of(log), LATER) == {"NCT1": "awaiting second adjudication"}
    withdrawal = Withdrawal(nct="NCT1", adjudicator="first", source_type="press_release_or_filing", source="wrong link",
                            reason="cited a sister trial's release", recorded_on=TOPLINE_DAY + dt.timedelta(days=1))
    assert result_of(log, withdrawals=[withdrawal]).outcome == "positive"
    with pytest.raises(ValueError, match="reason"):
        Withdrawal(nct="NCT1", adjudicator="first", source_type="press_release_or_filing", source="wrong link",
                   reason="", recorded_on=TOPLINE_DAY)
    nothing_to_withdraw = Withdrawal(nct="NCT1", adjudicator="second", source_type="press_release_or_filing",
                                     source="wrong link", reason="typo", recorded_on=TOPLINE_DAY + dt.timedelta(days=1))
    with pytest.raises(ValueError, match="nothing to withdraw"):
        results(log_of(log, withdrawals=[nothing_to_withdraw]), LATER)


# --- sources ---------------------------------------------------------------------------


def test_the_most_authoritative_source_decides_and_the_earliest_disclosure_sets_the_readout_date():
    log = both(outcome="positive") + both(outcome="negative", **paper())

    before_the_paper = result_of(log, on=dt.date(2027, 6, 1))
    assert (before_the_paper.outcome, before_the_paper.readout_date) == ("positive", TOPLINE_DAY)
    assert not before_the_paper.revised

    after_the_paper = result_of(log)
    assert (after_the_paper.outcome, after_the_paper.readout_date) == ("negative", TOPLINE_DAY)
    assert after_the_paper.decided_by.source_type == "paper_or_regulator"
    # The earlier result stays in the history.
    assert [(r.source_type, r.outcome) for r in after_the_paper.history] == [
        ("press_release_or_filing", "positive"), ("paper_or_regulator", "negative")]
    assert after_the_paper.revised


def test_a_later_less_authoritative_source_does_not_revise_the_result():
    log = both(outcome="positive", **paper()) + both(outcome="negative", source_type="registry", source="registry posting",
                                                     disclosed_on=PAPER_DAY + dt.timedelta(days=60))
    result = result_of(log)
    assert result.outcome == "positive" and not result.revised


def test_sources_rank_paper_or_regulator_then_conference_then_press_release_then_registry():
    def decided_by(*source_types):
        log = []
        for i, source_type in enumerate(source_types):
            log += both(source_type=source_type, source=f"source {i}", disclosed_on=TOPLINE_DAY + dt.timedelta(days=i))
        return result_of(log).decided_by.source_type

    assert decided_by("registry", "press_release_or_filing") == "press_release_or_filing"
    assert decided_by("conference", "press_release_or_filing") == "conference"
    assert decided_by("paper_or_regulator", "conference", "registry") == "paper_or_regulator"


def test_between_two_sources_of_one_rank_the_later_disclosure_decides():
    log = (both(source="interim release", endpoint_rule="any_of", endpoint_results=("met", "not_reported"))
           + both(source="final release", disclosed_on=TOPLINE_DAY + dt.timedelta(days=200),
                  endpoint_rule="any_of", endpoint_results=("met", "not_met")))
    result = result_of(log)
    assert result.decided_by.source == "final release"
    assert result.readout_date == TOPLINE_DAY


def test_a_source_only_one_adjudicator_has_read_holds_the_result_back():
    log = both(outcome="positive") + [adjudicated(adjudicator="first", outcome="negative", **paper())]
    assert results(log_of(log), LATER) == {}
    assert awaiting_result(log_of(log), LATER) == {"NCT1": "awaiting second adjudication"}
    # Until the paper was recorded, the press release stood.
    assert result_of(log, on=dt.date(2027, 6, 1)).outcome == "positive"


# --- hazard ratio --------------------------------------------------------------------------


def test_the_hazard_ratio_is_the_first_one_reported_within_six_months_of_readout():
    in_time = both() + both(hazard_ratio=0.72, source_type="conference", source="ESMO abstract",
                            disclosed_on=dt.date(2027, 9, 14))
    result = result_of(in_time)
    assert (result.hazard_ratio, result.hazard_ratio_status) == (0.72, "reported")

    too_late = both() + both(hazard_ratio=0.72, source_type="conference", source="ASCO abstract",
                             disclosed_on=dt.date(2027, 9, 15))
    result = result_of(too_late)
    assert (result.hazard_ratio, result.hazard_ratio_status) == (None, "missing")


def test_a_hazard_ratio_is_awaited_until_six_months_have_passed():
    assert result_of(both(), on=dt.date(2027, 9, 14)).hazard_ratio_status == "awaited"
    assert result_of(both(), on=dt.date(2027, 9, 15)).hazard_ratio_status == "missing"


def test_a_later_paper_does_not_replace_the_first_reported_hazard_ratio():
    assert result_of(both(hazard_ratio=0.70) + both(hazard_ratio=0.74, **paper())).hazard_ratio == 0.70


def test_of_two_sources_disclosed_on_one_day_the_more_authoritative_gives_the_hazard_ratio():
    same_day = dict(source_type="paper_or_regulator", source="doi:10.0000/example", disclosed_on=TOPLINE_DAY)
    assert result_of(both(hazard_ratio=0.70) + both(hazard_ratio=0.74, **same_day)).hazard_ratio == 0.74


def test_a_void_trial_has_no_readout_date_and_no_hazard_ratio():
    log = both(outcome="void", early_stop="no_analysis", original_text="The sponsor ended the study for strategic reasons.")
    result = result_of(log)
    assert (result.outcome, result.readout_date, result.hazard_ratio_status) == ("void", None, "not_applicable")
    with pytest.raises(ValueError):
        adjudicated(outcome="void", early_stop="no_analysis", hazard_ratio=0.8)


# --- blindness -----------------------------------------------------------------------------


def test_someone_who_has_opened_a_trials_forecasts_cannot_adjudicate_it(tmp_path):
    log_file = tmp_path / "adjudication.jsonl"
    opened = [ForecastAccess(nct="NCT1", person="First", opened_on=TOPLINE_DAY)]
    with pytest.raises(NotBlind, match="first"):
        record_adjudication(log_file, adjudicated(adjudicator="first"), forecast_access=opened, today=TOPLINE_DAY)
    assert not log_file.exists()
    # Someone else, or another trial, is unaffected.
    record_adjudication(log_file, adjudicated(adjudicator="second"), forecast_access=opened, today=TOPLINE_DAY)
    record_adjudication(log_file, adjudicated(nct="NCT2", adjudicator="first"), forecast_access=opened, today=TOPLINE_DAY)
    assert len(records.read(log_file, Adjudication)) == 2


def test_opening_forecasts_after_adjudicating_is_allowed():
    opened_later = [ForecastAccess(nct="NCT1", person="first", opened_on=TOPLINE_DAY + dt.timedelta(days=30))]
    assert result_of(both(), forecast_access=opened_later).outcome == "positive"


def test_an_entry_made_after_its_author_saw_the_forecasts_voids_only_that_trials_result():
    opened = [ForecastAccess(nct="NCT1", person="first", opened_on=TOPLINE_DAY - dt.timedelta(days=1))]
    log = log_of(both(nct="NCT1") + both(nct="NCT2"), forecast_access=opened)
    assert set(results(log, LATER)) == {"NCT2"}
    assert awaiting_result(log, LATER) == {"NCT1": "adjudicated after opening the forecasts"}


def test_reconciling_after_opening_the_forecasts_is_not_blind_either(tmp_path):
    opened = [ForecastAccess(nct="NCT1", person="second", opened_on=TOPLINE_DAY + dt.timedelta(days=1))]
    log = log_of(HAZARD_RATIO_DISPUTE, reconciliations=[reconciled()], forecast_access=opened)
    assert awaiting_result(log, LATER) == {"NCT1": "adjudicated after opening the forecasts"}
    with pytest.raises(NotBlind):
        record_reconciliation(tmp_path / "reconciliation.jsonl", reconciled(),
                              log_of(HAZARD_RATIO_DISPUTE, forecast_access=opened), today=reconciled().recorded_on)


def test_a_reading_that_was_not_blind_can_be_withdrawn_and_replaced_by_a_blind_one():
    opened = [ForecastAccess(nct="NCT1", person="first", opened_on=TOPLINE_DAY - dt.timedelta(days=1))]
    withdrawal = Withdrawal(nct="NCT1", adjudicator="first", source_type="press_release_or_filing", source=TOPLINE,
                            reason="had opened the forecasts", recorded_on=TOPLINE_DAY + dt.timedelta(days=1))
    third = adjudicated(adjudicator="third", recorded_on=TOPLINE_DAY + dt.timedelta(days=2))
    log = log_of(both() + [third], withdrawals=[withdrawal], forecast_access=opened)
    assert results(log, TOPLINE_DAY)  == {}
    assert results(log, LATER)["NCT1"].outcome == "positive"


# --- the log on disk ---------------------------------------------------------------------


def test_the_whole_log_is_read_back_from_its_directory(tmp_path):
    first, second = adjudicated(adjudicator="first"), adjudicated(adjudicator="second", outcome="negative")
    settled = Reconciliation(nct="NCT1", source_type="press_release_or_filing", source=TOPLINE, outcome="positive",
                             hazard_ratio=None, hazard_ratio_endpoint=None, disclosed_on=TOPLINE_DAY,
                             reason="the second reading took a secondary endpoint for the primary",
                             adjudicators=("first", "second"), recorded_on=TOPLINE_DAY)
    opened = ForecastAccess(nct="NCT1", person="first", opened_on=LATER)
    assert read_log(tmp_path) == AdjudicationLog()

    record_adjudication(tmp_path / "adjudications.jsonl", first, [], today=TOPLINE_DAY)
    record_adjudication(tmp_path / "adjudications.jsonl", second, [], today=TOPLINE_DAY)
    record_reconciliation(tmp_path / "reconciliations.jsonl", settled, AdjudicationLog([first, second]), today=TOPLINE_DAY)
    records.append(tmp_path / "forecast_access.jsonl", opened)

    log = read_log(tmp_path)
    assert log == AdjudicationLog([first, second], [settled], [], [opened])
    assert results(log, LATER)["NCT1"].outcome == "positive"


# --- an analysis that covers disclosures up to a fixed date -------------------------------


def test_a_source_disclosed_after_the_date_an_analysis_covers_plays_no_part_in_it():
    press_release = [adjudicated(adjudicator=who, hazard_ratio=0.7) for who in ("first", "second")]
    paper = [adjudicated(adjudicator=who, outcome="negative", source_type="paper_or_regulator",
                         source="https://example.test/paper", disclosed_on=PAPER_DAY) for who in ("first", "second")]
    log = log_of(press_release + paper)
    assert results(log, LATER)["NCT1"].outcome == "negative"   # the paper is the more authoritative source
    covered = results(log, LATER, disclosed_by=PAPER_DAY - dt.timedelta(days=1))["NCT1"]
    assert (covered.outcome, covered.hazard_ratio, [r.source for r in covered.history]) == ("positive", 0.7, [TOPLINE])
    assert results(log, LATER, disclosed_by=TOPLINE_DAY - dt.timedelta(days=1)) == {}


def test_an_unsettled_source_disclosed_after_that_date_does_not_hold_the_trial_back():
    press_release = [adjudicated(adjudicator=who) for who in ("first", "second")]
    paper_read_once = adjudicated(adjudicator="first", source_type="paper_or_regulator",
                                  source="https://example.test/paper", disclosed_on=PAPER_DAY)
    log = log_of([*press_release, paper_read_once])
    assert awaiting_result(log, LATER) == {"NCT1": "awaiting second adjudication"}
    before_the_paper = PAPER_DAY - dt.timedelta(days=1)
    assert awaiting_result(log, LATER, disclosed_by=before_the_paper) == {}
    assert results(log, LATER, disclosed_by=before_the_paper)["NCT1"].outcome == "positive"


def test_a_hazard_ratio_is_awaited_or_missing_as_of_the_date_the_analysis_covers():
    log = log_of([adjudicated(adjudicator=who) for who in ("first", "second")])   # no hazard ratio reported
    assert results(log, LATER)["NCT1"].hazard_ratio_status == "missing"          # over six months on
    soon_after = TOPLINE_DAY + dt.timedelta(days=30)
    assert results(log, LATER, disclosed_by=soon_after)["NCT1"].hazard_ratio_status == "awaited"


def test_a_void_trial_is_dated_by_its_earliest_disclosure():
    stopped = dict(outcome="void", early_stop="no_analysis")
    log = log_of([adjudicated(adjudicator=who, **stopped) for who in ("first", "second")]
                 + [adjudicated(adjudicator=who, source="https://example.test/again", disclosed_on=PAPER_DAY, **stopped)
                    for who in ("first", "second")])
    assert results(log, LATER)["NCT1"].first_disclosed_on == TOPLINE_DAY


# --- the log as it stood ---------------------------------------------------------------------


def test_a_log_can_be_cut_back_to_what_it_held_when_an_analysis_was_run():
    first, second, later = adjudicated(adjudicator="first"), adjudicated(adjudicator="second"), adjudicated(nct="NCT2")
    opened = ForecastAccess(nct="NCT1", person="first", opened_on=LATER)
    as_run = AdjudicationLog([first, second], forecast_access=[opened])
    grown = AdjudicationLog([first, second, later], forecast_access=[opened, opened])
    assert as_run.sizes() == (2, 0, 0, 1)
    assert grown.first(as_run.sizes()) == as_run
    with pytest.raises(ValueError, match="fewer entries"):
        as_run.first(grown.sizes())


REVEAL = TOPLINE_DAY + dt.timedelta(days=30)


def opened_by_both(on=REVEAL):
    return [ForecastAccess(nct="NCT1", person=who, opened_on=on) for who in ("first", "second")]


def paper_reading(who, outcome="negative", **reading):
    return adjudicated(adjudicator=who, outcome=outcome, source_type="paper_or_regulator", source="https://example.test/paper",
                       disclosed_on=PAPER_DAY, **reading)


def test_a_later_source_read_after_the_reveal_is_set_aside_while_a_blind_reading_stands():
    press_release = [adjudicated(adjudicator=who, hazard_ratio=0.7) for who in ("first", "second")]
    # After the reveal the same two people read the paper, which reverses the result: they are no longer blind for it.
    log = log_of(press_release + [paper_reading(who) for who in ("first", "second")], forecast_access=opened_by_both())

    assert awaiting_result(log, LATER) == {}
    blind = results(log, LATER)["NCT1"]
    assert (blind.outcome, [r.source for r in blind.history]) == ("positive", [TOPLINE])
    assert set_aside(log, LATER) == {"NCT1": ["https://example.test/paper"]}
    # Counted only when asked for, as one sensitivity analysis does.
    assert results(log, LATER, count_set_aside=True)["NCT1"].outcome == "negative"
    # With no blind reading at all, the trial has no result and is held back, as before.
    only_the_paper = log_of([paper_reading(who) for who in ("first", "second")], forecast_access=opened_by_both())
    assert awaiting_result(only_the_paper, LATER) == {"NCT1": "adjudicated after opening the forecasts"}
    assert results(only_the_paper, LATER) == {} and set_aside(only_the_paper, LATER) == {}


def test_recording_that_forecasts_were_opened_cannot_set_aside_a_source_that_was_already_public():
    # Both sources were public before anyone opened the forecasts, and the paper decides against the forecaster.
    press_release = [adjudicated(adjudicator=who) for who in ("first", "second")]
    paper = [paper_reading(who, recorded_on=PAPER_DAY + dt.timedelta(days=20)) for who in ("first", "second")]
    assert results(log_of(press_release + paper), LATER)["NCT1"].outcome == "negative"
    # An entry saying one adjudicator opened the forecasts before reading the paper does not bring the press release
    # back: the paper was already public then, so reading it late is not blind, and the trial is held back.
    back_dated = [ForecastAccess(nct="NCT1", person="first", opened_on=PAPER_DAY + dt.timedelta(days=10))]
    log = log_of(press_release + paper, forecast_access=back_dated)
    assert awaiting_result(log, LATER) == {"NCT1": "adjudicated after opening the forecasts"}
    assert results(log, LATER) == {} and set_aside(log, LATER) == {}


def test_a_set_aside_source_that_only_one_person_has_read_does_not_drop_the_trial_when_it_is_counted():
    press_release = [adjudicated(adjudicator=who) for who in ("first", "second")]
    log = log_of([*press_release, paper_reading("first")], forecast_access=opened_by_both())
    assert results(log, LATER)["NCT1"].outcome == "positive"
    assert results(log, LATER, count_set_aside=True)["NCT1"].outcome == "positive"     # an unsettled reading counts for nothing


def test_a_reading_after_the_reveal_is_taken_only_for_a_source_disclosed_after_it(tmp_path):
    log_file, opened = tmp_path / "adjudications.jsonl", opened_by_both()
    record_adjudication(log_file, paper_reading("first", recorded_on=PAPER_DAY), opened, today=PAPER_DAY)       # a later source: allowed
    with pytest.raises(NotBlind, match="first"):                                                # the topline was public before
        record_adjudication(log_file, adjudicated(adjudicator="first", recorded_on=PAPER_DAY), opened, today=PAPER_DAY)
    assert len(records.read(log_file, Adjudication)) == 1


def test_opening_forecasts_is_recorded_on_the_day_it_happens(tmp_path):
    access_file = tmp_path / "forecast_access.jsonl"
    with pytest.raises(ValueError, match="today"):
        record_forecast_access(access_file, ForecastAccess(nct="NCT1", person="first", opened_on=REVEAL), today=REVEAL + dt.timedelta(days=1))
    record_forecast_access(access_file, ForecastAccess(nct="NCT1", person="first", opened_on=REVEAL), today=REVEAL)
    assert len(records.read(access_file, ForecastAccess)) == 1


def test_a_reconciliation_cannot_date_a_source_after_the_day_it_was_recorded():
    with pytest.raises(ValueError, match="disclosed before"):
        reconciled(disclosed_on=dt.date(2031, 1, 1))


def test_a_reading_or_a_reconciliation_is_recorded_on_the_day_it_is_made(tmp_path):
    # Dated the day before a reveal but entered after it, a reading would pass for a blind one.
    late_entry = adjudicated(adjudicator="first", recorded_on=TOPLINE_DAY)
    with pytest.raises(ValueError, match="recorded on the day it is made"):
        record_adjudication(tmp_path / "a.jsonl", late_entry, [], today=TOPLINE_DAY + dt.timedelta(days=40))
    with pytest.raises(ValueError, match="recorded on the day it is made"):
        record_reconciliation(tmp_path / "r.jsonl", reconciled(), log_of(HAZARD_RATIO_DISPUTE), today=LATER)


def test_two_readers_of_a_later_source_can_settle_the_hazard_ratio_they_read_differently(tmp_path):
    press_release = [adjudicated(adjudicator=who) for who in ("first", "second")]
    typed = [paper_reading("first", outcome="positive", hazard_ratio=0.71), paper_reading("second", outcome="positive", hazard_ratio=0.17)]
    log = log_of(press_release + typed, forecast_access=opened_by_both())
    assert unsettled_sources(log, LATER) == {"NCT1": ["https://example.test/paper"]}
    settled = Reconciliation(nct="NCT1", source_type="paper_or_regulator", source="https://example.test/paper", outcome="positive",
                             hazard_ratio=0.71, hazard_ratio_endpoint="Overall survival", disclosed_on=PAPER_DAY,
                             reason="0.17 was a typing slip", adjudicators=("first", "second"), recorded_on=LATER)
    record_reconciliation(tmp_path / "r.jsonl", settled, log, today=LATER)      # allowed: the source came after the reveal
    after = log_of(press_release + typed, forecast_access=opened_by_both(), reconciliations=[settled])
    assert unsettled_sources(after, LATER) == {} and set_aside(after, LATER) == {"NCT1": ["https://example.test/paper"]}
