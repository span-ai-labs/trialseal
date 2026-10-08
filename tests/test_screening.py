"""Screening: which candidates are eligible trials, which wait for the study lead, and what the first screen found."""
import csv
import dataclasses
import datetime as dt
import gzip
import json

import pytest

from registry_records import study
from study_records import BATCH_1, SCREENED_ON, base_rate, candidate, screened
from trialforecast import records
from trialforecast.batch import build_batch
from trialforecast.screen import main
from trialforecast.screening import (
    DesignReview, IneligibleTrial, ScreeningRecord, confirmed, eligible_trials, found_no_result, screening_status,
    screening_summary,
)

LEAD = "Abhijoy Sarkar"
NON_INFERIORITY = dict(measure="Overall survival (non-inferiority margin 1.25)")


def review(nct, decision, reason="primary analysis is a superiority test; non-inferiority is a secondary aim"):
    return DesignReview(nct=nct, decision=decision, reason=reason, reviewed_by=LEAD, reviewed_on=SCREENED_ON)


# --- a screening record ----------------------------------------------------------------------


def test_a_screening_record_carries_its_confidence_and_what_it_rests_on():
    with pytest.raises(ValueError, match="confidence"):
        screened("NCT1", "eligible", confidence="fairly sure")
    with pytest.raises(ValueError, match="readout date and a link"):
        screened("NCT1", "already_read_out", readout_date=None)
    with pytest.raises(ValueError, match="readout date and a link"):
        screened("NCT1", "already_read_out", evidence_links=())
    with pytest.raises(ValueError, match="before it was found"):
        screened("NCT1", "already_read_out", readout_date=SCREENED_ON + dt.timedelta(days=1))
    with pytest.raises(ValueError, match="only a trial that has read out"):
        screened("NCT1", "eligible", readout_date=SCREENED_ON)
    with pytest.raises(ValueError, match="one spelling"):
        screened("NCT1", "eligible", investigational_drug="Examplumab 200 mg")
    kept = screened("NCT1", "eligible", evidence_links=["https://example.test/news"], investigational_drug="examplumab")
    assert records.from_line(ScreeningRecord, records.to_line(kept)) == kept


# --- who is eligible -------------------------------------------------------------------------


def status(log, nct="NCT1", on=BATCH_1):
    return screening_status(log, on).get(nct, "not_screened")


def test_a_decision_of_low_or_medium_confidence_waits_for_the_study_lead():
    unsure = screened("NCT1", "eligible", confidence="medium")
    assert status([unsure]) == "awaiting_confirmation"
    assert eligible_trials([candidate("NCT1")], [unsure], BATCH_1) == []
    with pytest.raises(IneligibleTrial, match="NCT1"):
        build_batch(BATCH_1, [candidate("NCT1")], [unsure], [base_rate()])
    confirmation = confirmed(unsure, by=LEAD, on=dt.date(2026, 10, 31))
    assert (confirmation.confirmed_by, confirmation.confirmed_on, confirmation.confidence) == (LEAD, dt.date(2026, 10, 31), "medium")
    assert status([unsure, confirmation]) == "eligible"
    assert status([screened("NCT1", "eligible", confidence="low")]) == "awaiting_confirmation"
    for half_confirmed in (dict(confirmed_by=LEAD), dict(confirmed_on=SCREENED_ON), dict(confirmed_by="  ", confirmed_on=SCREENED_ON),
                           dict(confirmed_by=LEAD, confirmed_on=SCREENED_ON - dt.timedelta(days=1))):
        with pytest.raises(ValueError, match="confirm"):
            screened("NCT1", "eligible", confidence="medium", **half_confirmed)


def test_confirming_a_decision_does_not_make_an_old_search_a_recent_one():
    search = screened("NCT1", "eligible", on=BATCH_1 - dt.timedelta(days=28), confidence="medium")
    confirmation = confirmed(search, by=LEAD, on=BATCH_1 - dt.timedelta(days=14))
    assert confirmation.screened_on == search.screened_on
    assert status([search, confirmation]) == "not_screened"     # the search is four weeks old, whenever it was confirmed


def ruling(nct, on, **fields):
    """The study lead's own decision that a trial is eligible, as recorded when overruling a report."""
    return screened(nct, "eligible", on=on, confidence="medium", confirmed_by=LEAD, confirmed_on=on, **fields)


def test_an_unconfirmed_report_of_a_readout_bars_a_trial_until_the_study_lead_rules():
    cleared = screened("NCT1", "eligible", on=dt.date(2026, 10, 25))
    doubtful = screened("NCT1", "already_read_out", on=dt.date(2026, 10, 28), confidence="low")
    assert status([cleared, doubtful]) == "awaiting_confirmation"
    # A searcher's later finding of nothing does not answer the report, however confident, and whatever the order.
    found_nothing = screened("NCT1", "eligible", on=dt.date(2026, 10, 29))
    assert status([cleared, doubtful, found_nothing]) == "awaiting_confirmation"
    same_day = screened("NCT1", "eligible", on=dt.date(2026, 10, 28))
    assert status([doubtful, same_day]) == status([same_day, doubtful]) == "awaiting_confirmation"
    # Nor does the report drop out of sight with age.
    assert status([doubtful], on=dt.date(2027, 3, 1)) == "awaiting_confirmation"
    # The study lead looks and finds it was a sibling trial: that ruling takes the doubtful report's place.
    assert status([cleared, doubtful, ruling("NCT1", dt.date(2026, 10, 30))]) == "eligible"
    # A ruling recorded before the report, or resting on an older search, does not answer it.
    assert status([ruling("NCT1", dt.date(2026, 10, 27)), doubtful]) == "awaiting_confirmation"
    # Had the readout been confirmed, nothing recorded later could clear the trial again.
    confirmed_readout = confirmed(doubtful, by=LEAD, on=dt.date(2026, 10, 29))
    assert status([cleared, doubtful, confirmed_readout, ruling("NCT1", dt.date(2026, 10, 30))]) == "already_read_out"


def test_what_accounts_for_a_trial_at_the_final_analysis_is_a_standing_search_with_nothing_to_bar_it():
    start, end = dt.date(2028, 5, 2), dt.date(2028, 5, 12)
    assert found_no_result([screened("NCT1", "eligible", on=start)], start, end) == {"NCT1"}
    assert found_no_result([screened("NCT1", "eligible", on=start, confidence="medium")], start, end) == set()
    assert found_no_result([screened("NCT1", "eligible", on=start - dt.timedelta(days=1))], start, end) == set()
    assert found_no_result([screened("NCT1", "eligible", on=end + dt.timedelta(days=1))], start, end) == set()
    # A search made before the date and confirmed after it is still a search made before the date.
    early = screened("NCT1", "eligible", on=start - dt.timedelta(days=13), confidence="medium")
    assert found_no_result([early, confirmed(early, by=LEAD, on=start + dt.timedelta(days=1))], start, end) == set()
    read_out_since = screened("NCT1", "already_read_out", on=start + dt.timedelta(days=5))
    assert found_no_result([screened("NCT1", "eligible", on=start), read_out_since], start, end) == set()
    # A doubtful report the study lead overruled long ago does not block a fresh search from counting.
    old_doubt = screened("NCT1", "already_read_out", on=dt.date(2026, 10, 28), confidence="low")
    history = [old_doubt, ruling("NCT1", dt.date(2026, 10, 30)), screened("NCT1", "eligible", on=start)]
    assert found_no_result(history, start, end) == {"NCT1"}


def test_a_trial_that_ended_without_a_primary_analysis_is_never_eligible():
    ended = screened("NCT1", "void", on=dt.date(2026, 10, 1))
    assert status([ended, screened("NCT1", "eligible")]) == "void"


def test_a_screening_dated_after_the_batch_or_long_before_it_clears_nothing():
    assert status([screened("NCT1", "eligible", on=BATCH_1 + dt.timedelta(days=1))]) == "not_screened"
    assert status([screened("NCT1", "eligible", on=BATCH_1 - dt.timedelta(days=15))]) == "not_screened"
    assert status([screened("NCT1", "eligible", on=BATCH_1 - dt.timedelta(days=14))]) == "eligible"


# --- designs that may rule a candidate out -----------------------------------------------------


def test_a_candidate_tagged_for_exclusion_review_is_not_eligible_until_a_person_has_ruled():
    tagged, plain = candidate("NCT1", **NON_INFERIORITY), candidate("NCT2")
    assert tagged["exclusion_review"] and not plain["exclusion_review"]
    log = [screened("NCT1", "eligible"), screened("NCT2", "eligible")]
    assert [c["nct"] for c in eligible_trials([tagged, plain], log, BATCH_1)] == ["NCT2"]
    assert [c["nct"] for c in eligible_trials([tagged, plain], log, BATCH_1, [review("NCT1", "include")])] == ["NCT1", "NCT2"]
    # A ruling to exclude holds for any candidate, tagged or not, and the latest ruling is the one that stands.
    assert eligible_trials([tagged, plain], log, BATCH_1, [review("NCT1", "exclude"), review("NCT2", "exclude")]) == []
    reversed_later = [review("NCT1", "exclude"),
                      dataclasses.replace(review("NCT1", "include"), reviewed_on=SCREENED_ON + dt.timedelta(days=1))]
    assert [c["nct"] for c in eligible_trials([tagged], log, BATCH_1, reversed_later)] == ["NCT1"]
    with pytest.raises(ValueError, match="include or exclude"):
        review("NCT1", "maybe")


def test_the_drug_a_person_corrected_at_screening_is_the_one_the_batch_fixes():
    trial = candidate("NCT1", drug="Docetaxel plus examplumab")
    log = [screened("NCT1", "eligible", investigational_drug="examplumab")]
    assert trial["investigational_drug"] == "docetaxel plus examplumab"
    assert build_batch(BATCH_1, [trial], log, [base_rate()]).trials[0].investigational_drug == "examplumab"
    unconfirmed = [screened("NCT1", "eligible"), screened("NCT1", "eligible", confidence="low", investigational_drug="otherinib")]
    assert status(unconfirmed) == "awaiting_confirmation"


def test_a_batch_cannot_include_a_tagged_candidate_nobody_has_ruled_on():
    tagged = candidate("NCT1", **NON_INFERIORITY)
    log = [screened("NCT1", "eligible")]
    with pytest.raises(IneligibleTrial, match="NCT1.*exclusion review"):
        build_batch(BATCH_1, [tagged], log, [base_rate()])
    with pytest.raises(IneligibleTrial, match="NCT1.*excluded"):
        build_batch(BATCH_1, [tagged], log, [base_rate()], design_reviews=[review("NCT1", "exclude", "non-inferiority primary")])
    batch = build_batch(BATCH_1, [tagged], log, [base_rate()], design_reviews=[review("NCT1", "include")])
    assert (batch.trials[0].nct, batch.trials[0].exclusion_review) == ("NCT1", "non-inferiority mentioned")


# --- the summary of a screen ---------------------------------------------------------------------


def test_the_summary_puts_every_candidate_in_one_place_and_lists_what_needs_the_study_lead():
    candidates = [candidate(f"NCT{i}") for i in range(1, 8)] + [candidate(f"NCT{i}", **NON_INFERIORITY) for i in (8, 9, 10, 11)]
    log = [
        # NCT10 is tagged and not yet screened: its design is queued all the same. NCT11 is tagged but has read out.
        screened("NCT11", "already_read_out"),
        screened("NCT1", "eligible"),
        screened("NCT2", "already_read_out"),
        screened("NCT3", "void"),
        screened("NCT4", "eligible", confidence="medium"),
        screened("NCT5", "already_read_out", confidence="low"),
        screened("NCT6", "eligible", on=BATCH_1 - dt.timedelta(days=30)),    # too long ago to count
        # NCT7 was never screened
        screened("NCT8", "eligible"), screened("NCT9", "eligible"),
    ]
    summary = screening_summary(candidates, log, [review("NCT9", "exclude", "non-inferiority primary")], BATCH_1)
    assert summary["counts"] == {"eligible": 1, "already_read_out": 2, "void": 1, "excluded_design": 1,
                                 "awaiting_confirmation": 2, "awaiting_design_review": 1, "not_screened": 3}
    assert [c["nct"] for c in summary["eligible"]] == ["NCT1"]
    assert [r.nct for r in summary["read_out"]] == ["NCT11", "NCT2"] and summary["read_out"][1].readout_date == SCREENED_ON - dt.timedelta(days=40)
    assert [(r.nct, r.reason) for r in summary["excluded"]] == [("NCT9", "non-inferiority primary")]
    assert [r.nct for r in summary["queue"]] == ["NCT4", "NCT5"]
    assert [c["nct"] for c in summary["design_queue"]] == ["NCT10", "NCT8"]
    assert sorted(c["nct"] for c in summary["not_screened"]) == ["NCT10", "NCT6", "NCT7"]


# --- the screening command, through files -----------------------------------------------------------

TODAY = dt.date(2026, 10, 9)


@pytest.fixture
def study_dir(tmp_path):
    """A study directory whose snapshot holds trials with registry dates before, inside and after the search window."""
    snapshot = tmp_path / "snapshots" / "2026-10-08T090005"
    snapshot.mkdir(parents=True)
    trials = [
        study("NCT0001", "Overall survival", pcd="2026-12", drug="Examplumab"),
        study("NCT0002", "Overall survival", pcd="2027-06", cls="OTHER"),
        study("NCT0003", "Overall survival (non-inferiority)", pcd="2027-01"),
        study("NCT0004", "Overall survival", pcd="2025-03", pcd_type="ACTUAL", status="COMPLETED"),
        study("NCT0005", "Overall survival", pcd="2031-01"),                 # beyond the search window
        study("NCT0006", "Objective response rate", pcd="2026-12"),          # not a candidate
        study("NCT0007", "Overall survival", pcd="2025-06", pcd_type="ACTUAL", status="COMPLETED"),
    ]
    trials[0]["protocolSection"]["identificationModule"].update(acronym="EXAMPLE-3", orgStudyIdInfo={"id": "EX-301"})
    trials[6]["hasResults"] = True
    trials[6]["protocolSection"]["statusModule"]["resultsFirstPostDateStruct"] = {"date": "2026-08-20"}
    with gzip.open(snapshot / "studies.jsonl.gz", "wt", encoding="utf-8") as f:
        for trial in trials:
            f.write(json.dumps(trial) + "\n")
    (snapshot / "manifest.json").write_text(json.dumps({"data_timestamp_start": "2026-10-08T09:00:05"}))
    return tmp_path


def run(study_dir, *arguments, today=TODAY):
    return main([*arguments, "--study", str(study_dir)], today=today)


def table(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def screening_log(study_dir):
    path = study_dir / "screening" / "screening.jsonl"
    return records.read(path, ScreeningRecord) if path.exists() else []


def test_the_worklist_gives_the_searcher_every_name_a_readout_may_be_announced_under(study_dir):
    assert run(study_dir, "worklist") == 0
    rows = table(study_dir / "screening" / "worklist.csv")
    # Candidates with a registry completion date within two years either side, soonest first; NCT0007 has results posted.
    assert [r["nct"] for r in rows] == ["NCT0004", "NCT0007", "NCT0001", "NCT0003", "NCT0002"]
    first = next(r for r in rows if r["nct"] == "NCT0001")
    assert (first["acronym"], first["sponsor_study_id"], first["lead_sponsor"]) == ("EXAMPLE-3", "EX-301", "Acme")
    assert "Examplumab" in first["intervention_names"] and first["investigational_drug"] == "examplumab"
    assert next(r for r in rows if r["nct"] == "NCT0003")["exclusion_review"] == "non-inferiority mentioned"


def test_results_posted_on_the_registry_are_a_public_result(study_dir):
    assert run(study_dir, "registry") == 0
    (found,) = screening_log(study_dir)
    assert (found.nct, found.decision, found.readout_date, found.confidence) == ("NCT0007", "already_read_out", dt.date(2026, 8, 20), "high")
    assert found.evidence_links == ("https://clinicaltrials.gov/study/NCT0007",)
    assert run(study_dir, "registry") == 0 and len(screening_log(study_dir)) == 1    # recorded once
    assert run(study_dir, "worklist") == 0
    assert "NCT0007" not in [r["nct"] for r in table(study_dir / "screening" / "worklist.csv")]


def write_findings(study_dir, rows, name="findings.csv"):
    columns = ("nct", "decision", "confidence", "evidence", "evidence_links", "readout_date", "investigational_drug")
    path = study_dir / name
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows([[row.get(column, "") for column in columns] for row in rows])
    return path


def test_findings_are_taken_into_the_log_all_or_none(study_dir, capsys):
    good = [
        {"nct": "NCT0001", "decision": "eligible", "confidence": "high", "evidence": "searched EXAMPLE-3, EX-301, examplumab, Acme news",
         "evidence_links": "https://example.test/acme-news https://example.test/pubmed", "investigational_drug": "Examplumab (EX-101) 200 mg"},
        {"nct": "NCT0004", "decision": "already_read_out", "confidence": "medium", "evidence": "topline press release",
         "evidence_links": "https://example.test/topline", "readout_date": "2025-05-02"},
    ]
    bad = good + [{"nct": "NCT0002", "decision": "already_read_out", "confidence": "high", "evidence": "abstract"}]   # no date, no link
    assert run(study_dir, "import", str(write_findings(study_dir, bad)), "--screened-by", "agent") == 1
    assert "NCT0002" in capsys.readouterr().out and screening_log(study_dir) == []

    assert run(study_dir, "import", str(write_findings(study_dir, good)), "--screened-by", "agent") == 0
    first, second = screening_log(study_dir)
    assert (first.screened_on, first.screened_by, first.evidence_links, first.investigational_drug) == (
        TODAY, "agent", ("https://example.test/acme-news", "https://example.test/pubmed"), "examplumab")
    assert (second.decision, second.readout_date, second.confidence) == ("already_read_out", dt.date(2025, 5, 2), "medium")
    # A finding for a trial that is not a candidate in the snapshot is refused too.
    stray = [{"nct": "NCT0006", "decision": "eligible", "confidence": "high", "evidence": "searched"}]
    assert run(study_dir, "import", str(write_findings(study_dir, stray)), "--screened-by", "agent") == 1


def test_the_summary_lists_the_queue_and_the_study_lead_confirms_from_it(study_dir, capsys):
    findings = [
        {"nct": "NCT0001", "decision": "eligible", "confidence": "high", "evidence": "searched"},
        {"nct": "NCT0002", "decision": "eligible", "confidence": "medium", "evidence": "searched; sponsor site was down"},
        {"nct": "NCT0003", "decision": "eligible", "confidence": "high", "evidence": "searched"},
        {"nct": "NCT0004", "decision": "already_read_out", "confidence": "low", "evidence": "trade press, unclear which trial",
         "evidence_links": "https://example.test/press", "readout_date": "2025-05-02"},
    ]
    run(study_dir, "import", str(write_findings(study_dir, findings)), "--screened-by", "agent")
    run(study_dir, "registry")
    capsys.readouterr()

    assert run(study_dir, "summary") == 0
    shown = capsys.readouterr().out
    assert "eligible 1" in shown and "awaiting confirmation 2" in shown and "awaiting design review 1" in shown
    assert "already read out 1" in shown and "not screened 1" in shown     # NCT0005 lies outside the window searched
    out = study_dir / "results" / "screening"
    assert [r["nct"] for r in table(out / "eligible.csv")] == ["NCT0001"]
    assert [(r["nct"], r["readout_date"]) for r in table(out / "read_out.csv")] == [("NCT0007", "2026-08-20")]
    queue = table(out / "queue.csv")
    assert [(r["nct"], r["decision"], r["confirm"]) for r in queue] == [("NCT0002", "eligible", ""), ("NCT0004", "already_read_out", "")]
    assert [r["nct"] for r in table(out / "design_queue.csv")] == ["NCT0003"]
    assert "6 candidates" in (out / "summary.md").read_text()

    # The study lead marks the queue and the design queue, and the rulings are taken in.
    def mark(name, **cells_by_trial):
        rows = table(out / name)
        for row in rows:
            row.update(cells_by_trial.get(row["nct"], {}))
        with (out / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    mark("queue.csv", NCT0002={"confirm": "yes"}, NCT0004={"confirm": "no"})
    assert run(study_dir, "confirm", str(out / "queue.csv"), "--by", LEAD) == 1       # overruling a report needs a note
    assert "needs a note" in capsys.readouterr().out and len(screening_log(study_dir)) == 5
    mark("queue.csv", NCT0004={"note": "the press item is about the phase 2 sibling trial"})
    assert run(study_dir, "confirm", str(out / "queue.csv"), "--by", LEAD) == 0
    confirmation, overruling = screening_log(study_dir)[-2:]
    assert (confirmation.nct, confirmation.confirmed_by, confirmation.screened_on, confirmation.confirmed_on) == ("NCT0002", LEAD, TODAY, TODAY)
    assert (overruling.nct, overruling.decision, overruling.confirmed_by) == ("NCT0004", "eligible", LEAD)
    assert "phase 2 sibling trial" in overruling.evidence
    mark("design_queue.csv", NCT0003={"decision": "exclude", "reason": "the primary analysis tests non-inferiority"})
    assert run(study_dir, "design", str(out / "design_queue.csv"), "--by", LEAD) == 0
    capsys.readouterr()
    assert run(study_dir, "summary") == 0
    shown = capsys.readouterr().out
    assert "eligible 3" in shown and "awaiting confirmation 0" in shown and "excluded design 1" in shown
    assert [(r["nct"], r["reason"]) for r in table(out / "excluded.csv")] == [("NCT0003", "the primary analysis tests non-inferiority")]


def test_the_study_lead_confirms_only_what_was_in_the_queue_they_marked(study_dir, capsys):
    doubtful = {"nct": "NCT0001", "decision": "already_read_out", "confidence": "low", "evidence": "trade press hint",
                "evidence_links": "https://example.test/press", "readout_date": "2026-09-01"}
    run(study_dir, "import", str(write_findings(study_dir, [doubtful])), "--screened-by", "agent")
    run(study_dir, "summary")
    out = study_dir / "results" / "screening"
    queue = (out / "queue.csv").read_text().replace(",,\n", ",yes,\n")           # the lead marks the report "yes"
    (out / "queue.csv").write_text(queue)
    # Before the marks are handed back, the log moves on: a later search of medium confidence finds nothing.
    later = {"nct": "NCT0001", "decision": "eligible", "confidence": "medium", "evidence": "searched again"}
    run(study_dir, "import", str(write_findings(study_dir, [later], "later.csv")), "--screened-by", "agent", today=TODAY + dt.timedelta(days=1))
    capsys.readouterr()
    assert run(study_dir, "confirm", str(out / "queue.csv"), "--by", LEAD, today=TODAY + dt.timedelta(days=1)) == 0
    # What was confirmed is the report the lead saw, not the newer finding.
    assert (screening_log(study_dir)[-1].decision, screening_log(study_dir)[-1].confirmed_by) == ("already_read_out", LEAD)
    # A row that is no decision waiting in the log is refused, and nothing is recorded.
    (out / "queue.csv").write_text(queue.replace("already_read_out", "eligible"))
    assert run(study_dir, "confirm", str(out / "queue.csv"), "--by", LEAD, today=TODAY + dt.timedelta(days=1)) == 1
    assert "not a decision waiting" in capsys.readouterr().out and len(screening_log(study_dir)) == 3


def test_the_queue_holds_every_decision_that_waits_not_only_each_trials_latest(study_dir):
    findings = [{"nct": "NCT0001", "decision": "eligible", "confidence": "medium", "evidence": "searched"}]
    run(study_dir, "import", str(write_findings(study_dir, findings)), "--screened-by", "agent")
    older = [{"nct": "NCT0001", "decision": "already_read_out", "confidence": "low", "evidence": "a hint in a filing",
              "evidence_links": "https://example.test/filing", "readout_date": "2026-08-01"}]
    assert run(study_dir, "import", str(write_findings(study_dir, older, "older.csv")), "--screened-by", "agent",
               "--screened-on", "2026-10-01") == 0
    run(study_dir, "summary")
    queue = table(study_dir / "results" / "screening" / "queue.csv")
    assert [(r["nct"], r["decision"], r["screened_on"]) for r in queue] == [("NCT0001", "already_read_out", "2026-10-01")]


def test_findings_that_cannot_be_read_or_are_dated_ahead_are_refused_without_a_traceback(study_dir, capsys):
    good = {"nct": "NCT0001", "decision": "eligible", "confidence": "high", "evidence": "searched"}
    path = write_findings(study_dir, [good])
    assert run(study_dir, "import", str(path), "--screened-by", "agent", "--screened-on", "2026-10-10") == 1
    assert "never before" in capsys.readouterr().out
    # Nor is a search entered long after it is said to have been made: its date could be chosen to suit.
    assert run(study_dir, "import", str(path), "--screened-by", "agent", "--screened-on", "2026-09-24") == 1
    assert "within 14 days of being made" in capsys.readouterr().out
    assert run(study_dir, "import", str(path), "--screened-by", "agent", "--screened-on", "2026-09-25") == 0
    (study_dir / "screening" / "screening.jsonl").unlink()
    path.write_text(path.read_text() + "NCT0002,eligible,high,searched,,,,an extra cell\n")
    assert run(study_dir, "import", str(path), "--screened-by", "agent") == 1
    assert "more cells than the header" in capsys.readouterr().out and screening_log(study_dir) == []
    assert run(tmp_empty := study_dir / "nowhere", "summary") == 1 and "no registry snapshot" in capsys.readouterr().out
    del tmp_empty


def test_a_trial_screened_before_is_screened_again_even_after_it_leaves_the_snapshot(study_dir):
    records.append(study_dir / "screening" / "screening.jsonl", screened("NCT0099", "eligible", on=dt.date(2026, 9, 1)))
    again = [{"nct": "NCT0099", "decision": "eligible", "confidence": "high", "evidence": "searched again"}]
    assert run(study_dir, "import", str(write_findings(study_dir, again)), "--screened-by", "agent") == 0
    assert [r.screened_on for r in screening_log(study_dir)] == [dt.date(2026, 9, 1), TODAY]


def test_a_design_ruling_is_only_taken_for_a_candidate(study_dir, capsys):
    rulings = study_dir / "rulings.csv"
    rulings.write_text("nct,decision,reason\nNCT0006,exclude,not a comparison of efficacy\n")
    assert run(study_dir, "design", str(rulings), "--by", LEAD) == 1
    assert "not candidates" in capsys.readouterr().out and not (study_dir / "screening" / "design_reviews.jsonl").exists()


def test_a_readout_trace_gives_each_traced_trial_its_screening_record(study_dir):
    trace = study_dir / "data" / "readout_trace" / "trace_A.csv"
    trace.parent.mkdir(parents=True)
    trace.write_text(
        "nct,disclosed,first_disclosure_date,first_source_url,primary_result,search_notes,confidence\n"
        "NCT0001,no,,,,searched the acronym and sponsor news,high\n"
        "NCT0002,no,,,terminated_no_analysis,stopped for slow enrolment per the registry,medium\n"
        "NCT0004,yes,2025-05-02,https://example.test/topline,met,press release,high\n"
        "NCT0003,unclear,2026-05-01,https://example.test/hint,met,sponsor hints at a result,high\n"
    )
    assert run(study_dir, "import-trace", str(trace), "--screened-on", "2026-10-10") == 1     # a day that has not come
    assert run(study_dir, "import-trace", str(trace), "--screened-on", "2026-10-07") == 0
    by_trial = {r.nct: r for r in screening_log(study_dir)}
    assert (by_trial["NCT0001"].decision, by_trial["NCT0001"].screened_on, by_trial["NCT0001"].confidence) == ("eligible", dt.date(2026, 10, 7), "high")
    assert (by_trial["NCT0002"].decision, by_trial["NCT0002"].confidence) == ("void", "medium")
    assert (by_trial["NCT0004"].decision, by_trial["NCT0004"].readout_date) == ("already_read_out", dt.date(2025, 5, 2))
    # An unclear trace is a possible readout for the study lead to rule on, never a clearance.
    assert (by_trial["NCT0003"].decision, by_trial["NCT0003"].confidence) == ("already_read_out", "low")
    assert run(study_dir, "import-trace", str(trace), "--screened-on", "2026-10-07") == 0 and len(screening_log(study_dir)) == 4


def test_a_proposed_design_ruling_is_shown_beside_the_queue_and_is_never_a_ruling(study_dir, capsys):
    (study_dir / "screening").mkdir()
    (study_dir / "screening" / "design_review_proposals.csv").write_text(
        "nct,proposed_decision,proposed_reason,quote\n"
        'NCT0003,exclude,the primary analysis of overall survival is a non-inferiority test,"Overall survival (non-inferiority)"\n')
    assert run(study_dir, "summary") == 0
    (row,) = table(study_dir / "results" / "screening" / "design_queue.csv")
    assert (row["nct"], row["proposed_decision"], row["decision"], row["reason"]) == ("NCT0003", "exclude", "", "")
    # Handing the file back unmarked rules on nothing: only the study lead's own decision and reason count.
    assert run(study_dir, "design", str(study_dir / "results" / "screening" / "design_queue.csv"), "--by", LEAD) == 0
    assert "0 design rulings recorded" in capsys.readouterr().out
    assert not (study_dir / "screening" / "design_reviews.jsonl").exists()


def test_a_trace_that_cannot_be_read_is_refused_without_a_traceback(study_dir, capsys):
    trace = study_dir / "trace_X.csv"
    trace.write_text("nct,disclosed,first_disclosure_date,primary_result,confidence\nNCT0001,yes,2026-05,met,high\n")
    assert run(study_dir, "import-trace", str(trace), "--screened-on", "2026-10-07") == 1
    assert "not a date given to the day" in capsys.readouterr().out and screening_log(study_dir) == []


def test_registry_results_are_recorded_once_however_often_the_step_is_run(study_dir):
    assert run(study_dir, "registry") == 0
    assert run(study_dir, "registry", today=TODAY + dt.timedelta(days=3)) == 0
    assert len(screening_log(study_dir)) == 1


def test_the_list_of_readouts_gives_the_earliest_date_found_and_whether_a_trace_covers_it(study_dir):
    run(study_dir, "registry")                                   # NCT0007: results posted 2026-08-20
    earlier = [{"nct": "NCT0007", "decision": "already_read_out", "confidence": "high", "evidence": "topline press release",
                "evidence_links": "https://example.test/topline", "readout_date": "2025-11-03"}]
    run(study_dir, "import", str(write_findings(study_dir, earlier)), "--screened-by", "agent")
    run(study_dir, "summary")
    (row,) = table(study_dir / "results" / "screening" / "read_out.csv")
    assert (row["nct"], row["readout_date"], row["source"], row["traced"]) == ("NCT0007", "2025-11-03", "https://example.test/topline", "no")


def doubtful(nct, readout, link, evidence="a hint in a filing"):
    return {"nct": nct, "decision": "already_read_out", "confidence": "low", "evidence": evidence,
            "evidence_links": link, "readout_date": readout}


def mark_queue(study_dir, marks):
    """The study lead marks rows of the queue, chosen by trial and readout date."""
    path = study_dir / "results" / "screening" / "queue.csv"
    rows = table(path)
    for row in rows:
        row.update(marks.get((row["nct"], row["readout_date"]), {}))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_overruling_one_report_does_not_sweep_away_another_the_study_lead_has_not_seen(study_dir, capsys):
    run(study_dir, "import", str(write_findings(study_dir, [doubtful("NCT0001", "2026-08-01", "https://example.test/filing")])), "--screened-by", "agent")
    run(study_dir, "summary")
    queue = mark_queue(study_dir, {("NCT0001", "2026-08-01"): {"confirm": "no", "note": "the filing is about another trial"}})
    # Before the marks come back, a second report arrives: a congress abstract.
    next_day = TODAY + dt.timedelta(days=1)
    second = doubtful("NCT0001", "2026-10-09", "https://example.test/abstract", "a congress abstract")
    run(study_dir, "import", str(write_findings(study_dir, [second], "second.csv")), "--screened-by", "agent", today=next_day)
    capsys.readouterr()
    assert run(study_dir, "confirm", str(queue), "--by", LEAD, today=next_day) == 1
    assert "another report is waiting" in capsys.readouterr().out and len(screening_log(study_dir)) == 2


def test_a_mark_finds_its_own_report_among_several_alike(study_dir):
    alike = [doubtful("NCT0001", "2026-09-01", "https://example.test/one"), doubtful("NCT0001", "2026-10-05", "https://example.test/two")]
    run(study_dir, "import", str(write_findings(study_dir, alike)), "--screened-by", "agent")
    run(study_dir, "summary")
    queue = mark_queue(study_dir, {("NCT0001", "2026-09-01"): {"confirm": "yes"}})
    assert run(study_dir, "confirm", str(queue), "--by", LEAD) == 0
    assert (screening_log(study_dir)[-1].readout_date, screening_log(study_dir)[-1].confirmed_by) == (dt.date(2026, 9, 1), LEAD)


def test_a_finding_of_nothing_marked_no_goes_on_waiting(study_dir, capsys):
    unsure = {"nct": "NCT0001", "decision": "eligible", "confidence": "medium", "evidence": "searched"}
    run(study_dir, "import", str(write_findings(study_dir, [unsure])), "--screened-by", "agent")
    run(study_dir, "summary")
    queue = mark_queue(study_dir, {("NCT0001", ""): {"confirm": "no"}})
    capsys.readouterr()
    assert run(study_dir, "confirm", str(queue), "--by", LEAD) == 0
    assert '1 finding of nothing marked "no" left waiting' in capsys.readouterr().out and len(screening_log(study_dir)) == 1


def test_what_waits_for_a_trial_that_has_left_the_snapshot_is_still_queued(study_dir):
    records.append(study_dir / "screening" / "screening.jsonl",
                   screened("NCT0099", "already_read_out", on=dt.date(2026, 10, 1), confidence="low"))
    run(study_dir, "summary")
    assert [r["nct"] for r in table(study_dir / "results" / "screening" / "queue.csv")] == ["NCT0099"]


def test_the_latest_standing_correction_of_a_drug_is_the_one_used_whatever_order_it_was_entered_in():
    newer = screened("NCT1", "eligible", on=dt.date(2026, 11, 1), investigational_drug="examplumab")
    older = screened("NCT1", "eligible", on=dt.date(2026, 10, 25), investigational_drug="otherinib")
    for entered in ([older, newer], [newer, older]):
        assert build_batch(BATCH_1, [candidate("NCT1")], entered, [base_rate()]).trials[0].investigational_drug == "examplumab"


def test_a_log_line_that_is_not_a_record_stops_the_command_without_a_traceback(study_dir, capsys):
    (study_dir / "screening").mkdir()
    (study_dir / "screening" / "screening.jsonl").write_text('{"nct": "NCT0001", "unexpected": true}\n')
    assert run(study_dir, "summary") == 1 and "NOT DONE" in capsys.readouterr().out
