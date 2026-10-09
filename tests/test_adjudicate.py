"""The adjudication command: a form each adjudicator fills in, recorded as readings, with disagreements settled between them."""
import csv
import datetime as dt
import gzip
import json

import pytest

from registry_records import study
from trialforecast import records
from trialforecast.adjudicate import main
from trialforecast.adjudication import (
    ForecastAccess, awaiting_result, no_result_found, read_log, read_nothing_found, results, source_states,
)

TODAY = dt.date(2026, 10, 12)
TOMORROW = TODAY + dt.timedelta(days=1)
TOPLINE = "https://example.test/topline"
QUOTE = "The trial met its primary endpoint of overall survival."
ADA, BEN = ["Ada Reader"], ["Ben Second"]
BOTH = [*ADA, *BEN]


@pytest.fixture
def study_dir(tmp_path):
    """A study with two adjudicators and three trials on the reference worklist."""
    (tmp_path / "study").mkdir()
    (tmp_path / "study" / "adjudicators.json").write_text(json.dumps(BOTH))
    worklist = tmp_path / "adjudication" / "reference" / "worklist.csv"
    worklist.parent.mkdir(parents=True)
    worklist.write_text("nct,acronym,title,scored_endpoint\n"
                        "NCT0001,ALPHA,A Study of X,Overall survival\n"
                        "NCT0002,,A Study of Y,Progression-free survival (PFS)\n"
                        "NCT0003,,A Study of Z,Overall survival\n")
    return tmp_path


def run(study_dir, *arguments, by=ADA, today=TODAY, trials="reference"):
    named = [part for name in by for part in ("--by", name)]
    return main([*arguments, "--set", trials, "--study", str(study_dir), *named], today=today)


def working(study_dir, name, trials="reference"):
    return study_dir / "adjudication" / "working" / trials / name


def form_of(study_dir, name="ada-reader"):
    return working(study_dir, f"form_{name}.csv")


def rows_of(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def fill(path, typed):
    """Type into a file: `typed` gives, for a trial or for one source of a trial, the cells typed into its row.

    A list gives one row for each of its members.
    """
    rows = rows_of(path)
    filled = []
    for row in rows:
        cells = typed.get((row["nct"], row["source"]), typed.get(row["nct"]))
        filled += [{**row, **(each or {})} for each in (cells if isinstance(cells, list) else [cells])]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(filled)


def met(**cells):
    return {"source_type": "press_release_or_filing", "source": TOPLINE, "disclosed_on": "2026-03-01", "original_text": QUOTE,
            "endpoint_results": "met", **cells}


def reads(study_dir, typed, by=ADA, today=TODAY, revise=False):
    """An adjudicator asks for a fresh form, types into it and records it."""
    name = by[0].lower().replace(" ", "-")
    form_of(study_dir, name).unlink(missing_ok=True)
    assert run(study_dir, "form", by=by, today=today) == 0
    fill(form_of(study_dir, name), typed)
    return run(study_dir, "record", *(["--revise"] if revise else []), by=by, today=today)


def log_of(study_dir):
    return read_log(study_dir / "adjudication" / "reference")


def a_disagreement(study_dir, ada=None, ben=None):
    reads(study_dir, {"NCT0001": ada or met(hazard_ratio="0.72")})
    reads(study_dir, {"NCT0001": ben or met(hazard_ratio="0.78", disclosed_on="2026-03-02")}, by=BEN)
    assert run(study_dir, "disagreements") == 0
    return working(study_dir, "disagreements.csv")


SETTLED = {"settled_outcome": "positive", "settled_disclosed_on": "2026-03-01", "settled_hazard_ratio": "0.72",
           "settled_hazard_ratio_endpoint": "Overall survival", "reason": "The release is dated 1 March and gives 0.72."}


# --- the form ------------------------------------------------------------------------------------


def test_the_form_gives_each_trial_a_row_with_what_the_adjudicator_need_not_type(study_dir, capsys):
    assert run(study_dir, "form") == 0
    rows = rows_of(form_of(study_dir))
    assert [row["nct"] for row in rows] == ["NCT0001", "NCT0002", "NCT0003"]
    assert rows[1]["title"] == "A Study of Y" and rows[1]["scored_endpoint"] == "Progression-free survival (PFS)"
    # The scored endpoint is offered word for word as what a hazard ratio is for; one primary endpoint is the usual case.
    assert rows[1]["hazard_ratio_endpoint"] == "Progression-free survival (PFS)"
    assert (rows[1]["language"], rows[1]["endpoint_rule"], rows[1]["source"], rows[1]["disclosed_on"]) == ("en", "single", "", "")
    said = capsys.readouterr().out
    assert "3 rows for Ada Reader" in said and "adjudication/working/reference/form_ada-reader.csv" in said


def test_the_form_shows_the_primary_outcomes_the_registry_lists(study_dir):
    snapshot = study_dir / "snapshots" / "2026-10-08T090005"
    snapshot.mkdir(parents=True)
    with gzip.open(snapshot / "studies.jsonl.gz", "wt", encoding="utf-8") as f:
        f.write(json.dumps(study("NCT0001", "Overall survival", n_extra=1)) + "\n")
    (snapshot / "manifest.json").write_text("{}")
    run(study_dir, "form")
    assert [row["primary_outcomes"] for row in rows_of(form_of(study_dir))] == ["Overall survival | ORR", "", ""]


def test_the_pilots_trials_have_their_own_worklist_and_log(study_dir):
    assert run(study_dir, "form", trials="pilot") == 1                       # the pilot has not listed its trials yet
    pilot = study_dir / "results" / "pilot" / "adjudication_worklist.csv"
    pilot.parent.mkdir(parents=True)
    pilot.write_text("nct,acronym,title,scored_endpoint,pilot_trial_for,adjudicated\nNCT0007,,A Study of W,Overall survival,m,no\n")
    assert run(study_dir, "form", trials="pilot") == 0
    form = working(study_dir, "form_ada-reader.csv", trials="pilot")
    fill(form, {"NCT0007": met()})
    assert run(study_dir, "record", trials="pilot") == 0
    assert [a.nct for a in read_log(study_dir / "adjudication" / "pilot").adjudications] == ["NCT0007"]
    assert log_of(study_dir).adjudications == ()


def test_only_a_named_adjudicator_can_use_the_command(study_dir, capsys):
    assert run(study_dir, "form", by=["Ada Reeder"]) == 1
    assert "NOT DONE: 'Ada Reeder' is not one of the adjudicators named in" in capsys.readouterr().out
    assert run(study_dir, "form", by=[" ada   READER "]) == 0                 # the same person, however typed
    listed = study_dir / "study" / "adjudicators.json"
    # One person listed twice, three people, something that is not a list of names, two names with one file name.
    for unusable in (["Ada Reader", "Ada  Reader"], ["A", "B", "C"], "Ada Reader", [1, 2], [""], [], ["Ada Reader", "Ada-Reader"],
                     ["???"], ["Ame\u0301lie R", "Am\u00e9lie R"]):
        listed.write_text(json.dumps(unusable))
        assert run(study_dir, "status") == 1
        assert 'must hold the adjudicators\' names, as ["First Name", "Second Name"]' in capsys.readouterr().out
    listed.write_text("not json")
    assert run(study_dir, "status") == 1 and "must hold the adjudicators' names" in capsys.readouterr().out
    listed.unlink()
    assert run(study_dir, "status") == 1 and "the study's adjudicators are not named" in capsys.readouterr().out


# --- recording readings ----------------------------------------------------------------------------


def test_filled_rows_are_recorded_as_readings_made_today(study_dir, capsys):
    assert reads(study_dir, {
        "NCT0001": met(hazard_ratio="0.72"),
        "NCT0002": met(endpoint_results="not_met", hazard_ratio="0.95", hazard_ratio_endpoint="Overall survival"),
    }) == 0
    assert "2 readings recorded for Ada Reader" in capsys.readouterr().out
    first, second = log_of(study_dir).adjudications
    assert (first.nct, first.adjudicator, first.recorded_on, first.outcome) == ("NCT0001", "ada reader", TODAY, "positive")
    assert (first.source_type, first.source, first.disclosed_on, first.language) == (
        "press_release_or_filing", TOPLINE, dt.date(2026, 3, 1), "en")
    assert (first.endpoint_rule, first.endpoint_results, first.early_stop, first.original_text) == ("single", ("met",), None, QUOTE)
    # Left as offered, the hazard ratio is for the scored endpoint; typed over, it is for whatever the adjudicator named.
    assert (first.hazard_ratio, first.hazard_ratio_endpoint) == (0.72, "Overall survival")
    assert (second.outcome, second.hazard_ratio_endpoint) == ("negative", "Overall survival")
    # The form is written again with what is left: the trial not yet read.
    assert [row["nct"] for row in rows_of(form_of(study_dir))] == ["NCT0003"]


def test_recording_the_same_form_twice_adds_nothing(study_dir):
    run(study_dir, "form")
    typed = {"NCT0001": met()}
    fill(form_of(study_dir), typed)
    assert run(study_dir, "record") == 0
    fill(form_of(study_dir), {"NCT0002": met(nct="NCT0001")})                  # the same reading typed again
    assert run(study_dir, "record") == 0 and len(log_of(study_dir).adjudications) == 1


def test_a_row_with_no_hazard_ratio_names_no_endpoint_for_one(study_dir):
    reads(study_dir, {"NCT0001": met()})
    reading, = log_of(study_dir).adjudications
    assert (reading.hazard_ratio, reading.hazard_ratio_endpoint) == (None, None)


def test_one_trial_can_have_several_sources_and_several_endpoints(study_dir):
    paper = met(source_type="paper_or_regulator", source="https://example.test/paper", disclosed_on="2026-06-01",
                endpoint_rule="co_primary", endpoint_results="met; not_met")
    stopped = {"source_type": "registry", "source": "https://example.test/registry", "disclosed_on": "2026-02-01",
               "original_text": "Terminated: slow accrual.", "early_stop": "no_analysis", "endpoint_results": ""}
    assert reads(study_dir, {"NCT0001": [met(), paper], "NCT0003": stopped}) == 0
    by_source = {a.source: a for a in log_of(study_dir).adjudications}
    assert by_source["https://example.test/paper"].endpoint_results == ("met", "not_met")
    assert by_source["https://example.test/paper"].outcome == "negative"          # co-primary: one missed is enough
    assert by_source["https://example.test/registry"].outcome == "void"


@pytest.mark.parametrize("typed, why", [
    (dict(disclosed_on="March 2026"), "'March 2026' is not a date (write it as 2026-03-01; in a spreadsheet, format"),
    (dict(disclosed_on="2026-11-01"), "a source must be disclosed before it is adjudicated"),
    (dict(endpoint_results="not_reported"), "these endpoint results do not say whether the trial was positive or negative"),
    (dict(endpoint_results="met; met"), "`single` takes one endpoint result; use any_of or co_primary"),
    (dict(endpoint_rule="any_of"), "any_of needs a result for each primary endpoint, at least two"),
    (dict(endpoint_results="Met"), "each endpoint result must be one of met, not_met, not_reported, not 'Met'"),
    (dict(early_stop="efficacy"), "leave endpoint_results blank for an early stop"),
    (dict(source_type=""), "source type must be one of paper_or_regulator, conference, press_release_or_filing, registry"),
    (dict(source=""), "the source's address is needed"),
    (dict(language="zh"), "a disclosure in 'zh' needs a translation beside the original"),
    (dict(hazard_ratio="0,72"), "hazard ratio '0,72' is not a number"),
    (dict(hazard_ratio="72"), "hazard ratio 72 is not between 0.05 and 20.0: check the decimal point"),
    (dict(hazard_ratio="nan"), "hazard ratio nan is not between"),
    (dict(nct="NCT0099"), "not on the worklist"),
    (dict(nothing_found="PubMed"), "a row records a reading or that nothing was found, not both"),
])
def test_a_row_that_cannot_be_a_reading_stops_the_whole_file_and_says_why(study_dir, capsys, typed, why):
    assert reads(study_dir, {"NCT0001": met(), "NCT0002": met(**typed)}) == 1
    said = capsys.readouterr().out
    assert "NOT RECORDED" in said and f"row 3 ({typed.get('nct', 'NCT0002')}): {why}" in said
    assert log_of(study_dir).adjudications == ()                                # not even the row that was in order


def test_a_file_that_is_not_the_form_or_not_saved_as_utf_8_is_refused(study_dir, capsys):
    assert run(study_dir, "record") == 1 and "there is no form at" in capsys.readouterr().out
    run(study_dir, "form")
    form_of(study_dir).write_text("nct,outcome\nNCT0001,positive\n")
    assert run(study_dir, "record") == 1
    assert "is not an adjudication form: it has no column 'title'" in capsys.readouterr().out
    form_of(study_dir).write_bytes("nct,title\nNCT0001,Étude\n".encode("cp1252"))
    assert run(study_dir, "record") == 1 and 'save it as "CSV UTF-8"' in capsys.readouterr().out


def test_the_same_source_cannot_enter_the_log_under_two_spellings(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()})
    capsys.readouterr()
    # The other adjudicator finds the same release and copies its address a little differently, or calls it a conference.
    for other in (dict(source="https://Example.test/topline/"), dict(source_type="conference"),
                  dict(source="http://www.example.test/topline#results")):
        assert reads(study_dir, {"NCT0002": met(nct="NCT0001", **other)}, by=BEN) == 1
        assert ("this looks like the source already cited as press_release_or_filing, 'https://example.test/topline'; "
                "use that source type and address exactly") in capsys.readouterr().out
    # Addresses that differ in the path's case, or after a "#/" that some sites use as the page's address, are two sources.
    apart = [met(source="https://example.test/news#/release/1"), met(source="https://example.test/news#/release/2"),
             met(source="https://example.test/Topline")]
    assert reads(study_dir, {"NCT0002": apart}, by=BEN) == 0
    # Two rows of one file are held to the same rule, and one source cannot be read twice in a file.
    capsys.readouterr()
    assert reads(study_dir, {"NCT0003": [met(source="https://example.test/two"), met(source="example.test/two")]}, by=BEN) == 1
    assert "this looks like the source already cited" in capsys.readouterr().out
    assert reads(study_dir, {"NCT0003": [met(source="https://example.test/two")] * 2}, by=BEN) == 1
    assert "the same source is read twice in this file" in capsys.readouterr().out


def test_an_address_typed_but_not_yet_read_is_kept_when_the_form_is_written_again(study_dir):
    run(study_dir, "form")
    fill(form_of(study_dir), {"NCT0001": met(), "NCT0002": {"source_type": "conference", "source": "https://example.test/abstract"}})
    assert run(study_dir, "record") == 0
    kept = {row["nct"]: (row["source_type"], row["source"]) for row in rows_of(form_of(study_dir))}
    assert kept == {"NCT0002": ("conference", "https://example.test/abstract"), "NCT0003": ("", "")}
    assert run(study_dir, "form") == 0 and rows_of(form_of(study_dir))[0]["source"] == "https://example.test/abstract"
    # What else was typed on such a row is kept too, and a row for a trial not on the worklist is not silently dropped.
    fill(form_of(study_dir), {"NCT0002": {"language": "ja", "endpoint_rule": "any_of", "hazard_ratio_endpoint": "OS"}})
    assert run(study_dir, "form") == 0
    kept = rows_of(form_of(study_dir))[0]
    assert (kept["language"], kept["endpoint_rule"], kept["hazard_ratio_endpoint"]) == ("ja", "any_of", "OS")
    fill(form_of(study_dir), {"NCT0003": {"nct": "NCT0033", "source_type": "conference", "source": "https://example.test/z"}})
    assert run(study_dir, "form") == 1


def test_a_form_with_rows_not_yet_recorded_is_not_written_over(study_dir, capsys):
    run(study_dir, "form")
    fill(form_of(study_dir), {"NCT0001": met(), "NCT0002": met(disclosed_on="March"), "NCT0003": {"nothing_found": "PubMed"}})
    capsys.readouterr()
    assert run(study_dir, "form") == 1
    assert "holds 3 rows not yet recorded; run record, or delete the file" in capsys.readouterr().out
    assert rows_of(form_of(study_dir))[0]["original_text"] == QUOTE


def test_someone_who_has_opened_a_trials_forecasts_cannot_record_a_reading_of_it(study_dir, capsys):
    records.append(study_dir / "adjudication" / "reference" / "forecast_access.jsonl",
                   ForecastAccess(nct="NCT0001", person="Ada Reader", opened_on=TODAY))
    assert reads(study_dir, {"NCT0001": met(), "NCT0002": met()}) == 1
    assert "row 2 (NCT0001): ada reader opened the forecasts for NCT0001 before adjudicating it" in capsys.readouterr().out
    assert log_of(study_dir).adjudications == ()
    assert reads(study_dir, {"NCT0001": {"nothing_found": "PubMed"}}) == 1
    assert "ada reader opened the forecasts for NCT0001 before searching for its result" in capsys.readouterr().out


def test_a_log_dated_after_today_stops_every_step(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()}, today=TOMORROW)
    capsys.readouterr()
    for step in ("form", "record", "status", "disagreements"):
        assert run(study_dir, step) == 1
        assert "the log holds an entry dated 2026-10-13, after today (2026-10-12): check this computer's date" in capsys.readouterr().out


# --- the second adjudicator ------------------------------------------------------------------------


def test_the_second_adjudicator_is_given_the_first_ones_sources_and_nothing_of_what_was_read(study_dir, capsys):
    reads(study_dir, {"NCT0001": met(hazard_ratio="0.72", endpoint_rule="any_of", endpoint_results="met;not_met", language="zh",
                                     translation="It met.")})
    assert run(study_dir, "form", by=BEN) == 0
    form = form_of(study_dir, "ben-second")
    first = rows_of(form)[0]
    assert (first["nct"], first["source_type"], first["source"]) == ("NCT0001", "press_release_or_filing", TOPLINE)
    assert {cell: first[cell] for cell in ("disclosed_on", "original_text", "translation", "endpoint_results", "hazard_ratio")} == {
        "disclosed_on": "", "original_text": "", "translation": "", "endpoint_results": "", "hazard_ratio": ""}
    assert (first["language"], first["endpoint_rule"]) == ("en", "single")           # as offered to everyone
    text = form.read_text() + capsys.readouterr().out
    assert all(read not in text for read in (QUOTE, "0.72", "2026-03-01", "It met.", "any_of", "zh", "not_met"))


def test_a_trial_is_settled_when_both_have_read_its_source_the_same_way(study_dir, capsys):
    reads(study_dir, {"NCT0001": met(hazard_ratio="0.72")})
    reads(study_dir, {"NCT0001": met(hazard_ratio="0.72", original_text="Met its primary endpoint.")}, by=BEN)
    assert results(log_of(study_dir), TODAY)["NCT0001"].outcome == "positive"         # the quote is each one's own
    reads(study_dir, {"NCT0002": met(source="https://example.test/y")})
    capsys.readouterr()
    assert run(study_dir, "status") == 0
    assert capsys.readouterr().out.splitlines() == [
        "NCT0001  settled", "NCT0002  awaiting the second adjudicator", "NCT0003  not yet read",
        "3 trials: 1 settled, 0 with no result found, 1 awaiting the second adjudicator, 0 read differently, 1 not yet read"]


def test_a_trial_that_has_left_the_worklist_can_still_be_seen_and_come_back_to(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()})
    worklist = study_dir / "adjudication" / "reference" / "worklist.csv"
    worklist.write_text(worklist.read_text().replace("NCT0001,ALPHA,A Study of X,Overall survival\n", ""))
    capsys.readouterr()
    assert run(study_dir, "status") == 0
    assert "NCT0001  awaiting the second adjudicator  (no longer on the worklist)" in capsys.readouterr().out
    assert run(study_dir, "form", "--reread", "NCT0001") == 0
    assert [(row["nct"], row["source"]) for row in rows_of(form_of(study_dir))][-1] == ("NCT0001", TOPLINE)
    # The other adjudicator is still given its source to read.
    run(study_dir, "form", by=BEN)
    assert ("NCT0001", TOPLINE) in [(row["nct"], row["source"]) for row in rows_of(form_of(study_dir, "ben-second"))]


def test_a_worklist_that_is_not_a_list_of_trials_is_refused(study_dir, capsys):
    (study_dir / "adjudication" / "reference" / "worklist.csv").write_text("trial,title\nNCT0001,A Study of X\n")
    assert run(study_dir, "status") == 1 and "is not a list of trials: it has no column 'nct'" in capsys.readouterr().out


def test_nothing_is_added_to_the_reference_log_once_the_base_rates_are_frozen(study_dir, capsys):
    disagreements = a_disagreement(study_dir)
    fill(disagreements, {"NCT0001": SETTLED})
    (study_dir / "study" / "base_rates.json").write_text("{}")
    capsys.readouterr()
    run(study_dir, "form", by=BEN)
    fill(form_of(study_dir, "ben-second"), {"NCT0002": met(source="https://example.test/y")})
    for refused in (lambda: run(study_dir, "record", by=BEN), lambda: run(study_dir, "reconcile", by=BOTH),
                    lambda: run(study_dir, "withdraw", "--trial", "NCT0001", "--source", TOPLINE, "--reason", "late")):
        assert refused() == 1
        assert "the reference log is closed" in capsys.readouterr().out
    assert len(log_of(study_dir).adjudications) == 2 and log_of(study_dir).reconciliations == ()
    assert run(study_dir, "status") == 0


# --- a search that found nothing ---------------------------------------------------------------------


def test_a_trial_both_searched_and_found_nothing_for_has_no_result_found(study_dir, capsys):
    searched = {"NCT0003": {"nothing_found": "registry record, PubMed by number and drug, the sponsor's news page"}}
    assert reads(study_dir, {"NCT0001": met(), **searched}) == 0
    assert "1 reading and 1 finding of nothing recorded for Ada Reader" in capsys.readouterr().out
    finding, = read_nothing_found(study_dir / "adjudication" / "reference")
    assert (finding.nct, finding.adjudicator, finding.recorded_on) == ("NCT0003", "ada reader", TODAY)
    assert finding.searched.startswith("registry record")
    # Ada has no more to do for that trial; Ben's form does not say what she found.
    assert "NCT0003" not in [row["nct"] for row in rows_of(form_of(study_dir))]
    run(study_dir, "form", by=BEN)
    assert [row["nct"] for row in rows_of(form_of(study_dir, "ben-second"))] == ["NCT0001", "NCT0002", "NCT0003"]
    assert "registry record" not in form_of(study_dir, "ben-second").read_text()
    assert run(study_dir, "status") == 0 and "NCT0003  awaiting the second adjudicator" in capsys.readouterr().out

    assert reads(study_dir, searched, by=BEN) == 0
    log = log_of(study_dir)
    assert no_result_found(read_nothing_found(study_dir / "adjudication" / "reference"), log, TODAY) == {
        "NCT0003": ("ada reader", "ben second")}
    assert run(study_dir, "status") == 0
    assert "NCT0003  no result found" in capsys.readouterr().out
    # Recording the search again adds nothing.
    assert reads(study_dir, {"NCT0002": {"nct": "NCT0003", "nothing_found": "again"}}, by=BEN) == 0
    assert len(read_nothing_found(study_dir / "adjudication" / "reference")) == 2


def test_a_source_the_other_then_finds_comes_back_to_the_one_who_found_nothing(study_dir, capsys):
    reads(study_dir, {"NCT0003": {"nothing_found": "registry, PubMed"}})
    reads(study_dir, {"NCT0003": met()}, by=BEN)
    run(study_dir, "form")
    row, = [row for row in rows_of(form_of(study_dir)) if row["nct"] == "NCT0003"]
    assert row["source"] == TOPLINE
    capsys.readouterr()
    # Whoever has read a source for the trial has found something, and cannot also have found nothing.
    assert reads(study_dir, {"NCT0002": {"nct": "NCT0003", "nothing_found": "looked again"}}, by=BEN) == 1
    assert "ben second has a reading of a source for NCT0003 in force" in capsys.readouterr().out


def test_one_who_found_nothing_and_later_finds_a_source_can_ask_for_a_row(study_dir):
    for who in (ADA, BEN):
        reads(study_dir, {"NCT0003": {"nothing_found": "registry, PubMed"}}, by=who)
    run(study_dir, "form")
    assert "NCT0003" not in [row["nct"] for row in rows_of(form_of(study_dir))]
    assert run(study_dir, "form", "--reread", "NCT0003") == 0
    assert ("NCT0003", "") in [(row["nct"], row["source"]) for row in rows_of(form_of(study_dir))]
    fill(form_of(study_dir), {"NCT0003": met()})
    assert run(study_dir, "record") == 0 and log_of(study_dir).adjudications[0].nct == "NCT0003"


def test_a_reading_and_a_search_that_found_nothing_for_one_trial_cannot_share_a_file(study_dir, capsys):
    searched = {"nothing_found": "PubMed", "source": "", "source_type": ""}
    for typed in ([met(), searched], [searched, met()]):
        assert reads(study_dir, {"NCT0001": typed}) == 1
        assert "row 3 (NCT0001): this file also records a" in capsys.readouterr().out
    # The same search typed on two rows is one finding.
    assert reads(study_dir, {"NCT0001": [searched, searched]}) == 0
    assert len(read_nothing_found(study_dir / "adjudication" / "reference")) == 1


def test_a_finding_of_nothing_dated_after_today_stops_the_command(study_dir, capsys):
    reads(study_dir, {"NCT0003": {"nothing_found": "PubMed"}}, today=TOMORROW)
    capsys.readouterr()
    assert run(study_dir, "status") == 1 and "the log holds an entry dated 2026-10-13" in capsys.readouterr().out


def test_an_adjudicator_can_dissent_from_a_source_the_other_cited(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()})
    # Ben reads the release Ada cited and finds it reports only a safety review. He says so on its row.
    assert reads(study_dir, {"NCT0001": {"nothing_found": "it reports an interim safety review, not the primary analysis"}},
                 by=BEN) == 0
    assert "0 readings and 1 dissent recorded for Ben Second" in capsys.readouterr().out
    dissent, = log_of(study_dir).dissents
    assert (dissent.nct, dissent.adjudicator, dissent.source, dissent.recorded_on) == ("NCT0001", "ben second", TOPLINE, TODAY)
    # The source no longer waits on his form, the two may now talk, and the trial still has no result.
    assert "NCT0001" not in [row["nct"] for row in rows_of(form_of(study_dir, "ben-second"))]
    assert run(study_dir, "status") == 0 and "NCT0001  read differently" in capsys.readouterr().out
    assert run(study_dir, "disagreements") == 0
    assert (f"NCT0001: Ada Reader read {TOPLINE}; Ben Second finds it does not state the result. "
            "Either the reading is withdrawn, or the source is read by both and reconciled.") in capsys.readouterr().out
    assert results(log_of(study_dir), TODAY) == {} and awaiting_result(log_of(study_dir), TODAY) == {"NCT0001": "disagreement"}
    # Ada stands by it and Ben reads it after all. He asks for its row again; having talked, they must reconcile it.
    assert run(study_dir, "form", "--reread", "NCT0001", by=BEN, today=TOMORROW) == 0
    again, = [row for row in rows_of(form_of(study_dir, "ben-second")) if row["nct"] == "NCT0001"]
    assert again["source"] == TOPLINE
    fill(form_of(study_dir, "ben-second"), {"NCT0001": met()})
    assert run(study_dir, "record", by=BEN, today=TOMORROW) == 0
    assert results(log_of(study_dir), TOMORROW) == {}
    assert run(study_dir, "disagreements", today=TOMORROW) == 0
    fill(working(study_dir, "disagreements.csv"), {"NCT0001": {**SETTLED, "settled_hazard_ratio": "", "settled_hazard_ratio_endpoint": ""}})
    assert run(study_dir, "reconcile", by=BOTH, today=TOMORROW) == 0
    assert results(log_of(study_dir), TOMORROW)["NCT0001"].outcome == "positive"


def test_a_dissent_and_a_reading_of_one_source_cannot_share_a_file(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()})
    dissenting = {"nothing_found": "a safety review only"}
    for typed in ([dissenting, met()], [met(), dissenting]):
        assert reads(study_dir, {"NCT0001": typed}, by=BEN) == 1
        assert "row 3 (NCT0001): this file also" in capsys.readouterr().out
    assert log_of(study_dir).dissents == () and len(log_of(study_dir).adjudications) == 1
    # Nor can the day's own reading be dissented from by its author, or a reading follow a dissent on the same day.
    assert reads(study_dir, {"NCT0001": dissenting}, by=BEN) == 0
    assert run(study_dir, "form", "--reread", "NCT0001", by=BEN) == 0
    fill(form_of(study_dir, "ben-second"), {"NCT0001": met()})
    assert run(study_dir, "record", by=BEN) == 1
    assert "this source was found today not to state the result; a reading of it can be recorded from tomorrow" in capsys.readouterr().out


def test_a_dissent_does_not_lay_a_trial_open_while_another_source_of_it_is_unread(study_dir, capsys):
    paper = met(source_type="paper_or_regulator", source="https://example.test/paper", disclosed_on="2026-06-01")
    reads(study_dir, {"NCT0001": [met(), paper]})
    reads(study_dir, {("NCT0001", TOPLINE): {"nothing_found": "a safety review only"}}, by=BEN)   # the paper is still unread
    capsys.readouterr()
    assert run(study_dir, "status") == 0 and "NCT0001  awaiting the second adjudicator" in capsys.readouterr().out
    assert run(study_dir, "disagreements") == 0 and "finds it does not state" not in capsys.readouterr().out


def test_a_source_withdrawn_after_a_dissent_leaves_the_trial_to_be_searched(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()})
    reads(study_dir, {"NCT0001": {"nothing_found": "a safety review only"}}, by=BEN)
    assert run(study_dir, "withdraw", "--trial", "NCT0001", "--source", TOPLINE, "--reason", "Ben is right") == 0
    capsys.readouterr()
    assert run(study_dir, "status") == 0 and "NCT0001  not yet read" in capsys.readouterr().out
    # A dissent from one source is not a search of the trial: each still has a blank row for it.
    for who, name in ((ADA, "ada-reader"), (BEN, "ben-second")):
        run(study_dir, "form", by=who)
        assert ("NCT0001", "") in [(row["nct"], row["source"]) for row in rows_of(form_of(study_dir, name))]
    # Weeks later the same page holds the results and Ada cites it again. Ben's dissent was from what stood before.
    later = TODAY + dt.timedelta(days=21)
    assert reads(study_dir, {"NCT0001": met()}, today=later) == 0
    run(study_dir, "form", by=BEN, today=later)
    assert ("NCT0001", TOPLINE) in [(row["nct"], row["source"]) for row in rows_of(form_of(study_dir, "ben-second"))]


def test_a_citation_the_other_has_withdrawn_does_not_linger_on_ones_form(study_dir):
    reads(study_dir, {"NCT0001": met()})
    run(study_dir, "form", by=BEN)
    assert rows_of(form_of(study_dir, "ben-second"))[0]["source"] == TOPLINE
    run(study_dir, "withdraw", "--trial", "NCT0001", "--source", TOPLINE, "--reason", "about another trial")
    assert run(study_dir, "form", by=BEN) == 0
    assert [(row["nct"], row["source"]) for row in rows_of(form_of(study_dir, "ben-second"))][0] == ("NCT0001", "")
    # A row the adjudicator copied from a given one and typed another address into is theirs, and is kept.
    reads(study_dir, {"NCT0002": met(source="https://example.test/y")})
    run(study_dir, "form", by=BEN)
    fill(form_of(study_dir, "ben-second"), {"NCT0002": [None, {"source": "https://example.test/another"}]})
    assert run(study_dir, "form", by=BEN) == 0
    assert [row["source"] for row in rows_of(form_of(study_dir, "ben-second")) if row["nct"] == "NCT0002"] == [
        "https://example.test/y", "https://example.test/another"]


def test_a_row_for_a_trial_off_the_worklist_stops_the_form_being_recorded_at_all(study_dir, capsys):
    run(study_dir, "form")
    fill(form_of(study_dir), {"NCT0001": met(), "NCT0002": {"nct": "NCT0022", "source_type": "conference", "source": "https://example.test/z"}})
    capsys.readouterr()
    assert run(study_dir, "record") == 1
    said = capsys.readouterr().out
    assert "row 3 gives a source for NCT0022, which is not on the worklist" in said and "recorded for" not in said
    assert log_of(study_dir).adjudications == ()


def test_a_trial_with_only_findings_of_nothing_that_left_the_worklist_is_still_shown(study_dir, capsys):
    for who in (ADA, BEN):
        reads(study_dir, {"NCT0003": {"nothing_found": "registry, PubMed"}}, by=who)
    worklist = study_dir / "adjudication" / "reference" / "worklist.csv"
    worklist.write_text(worklist.read_text().replace("NCT0003,,A Study of Z,Overall survival\n", ""))
    capsys.readouterr()
    assert run(study_dir, "status") == 0
    assert "NCT0003  no result found  (no longer on the worklist)" in capsys.readouterr().out
    run(study_dir, "form")
    assert "NCT0003" not in [row["nct"] for row in rows_of(form_of(study_dir))]
    run(study_dir, "form", "--reread", "NCT0003")
    assert ("NCT0003", "") in [(row["nct"], row["source"]) for row in rows_of(form_of(study_dir))]


# --- changing one's mind -----------------------------------------------------------------------------


def test_a_reading_is_changed_only_on_purpose_and_the_first_one_stays_in_the_log(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()})
    assert run(study_dir, "form", "--reread", "NCT0001") == 0
    again = rows_of(form_of(study_dir))[0]
    assert (again["nct"], again["source_type"], again["source"], again["original_text"]) == (
        "NCT0001", "press_release_or_filing", TOPLINE, "")
    fill(form_of(study_dir), {"NCT0001": met(endpoint_results="not_met")})
    capsys.readouterr()
    assert run(study_dir, "record") == 1
    assert ("row 2 (NCT0001): you have already read this source differently on 2026-10-12; "
            "record with --revise to replace that reading") in capsys.readouterr().out
    assert run(study_dir, "record", "--revise") == 0
    first, revised = log_of(study_dir).adjudications
    assert (first.outcome, revised.outcome) == ("positive", "negative")
    in_force, = source_states(log_of(study_dir), TODAY).values()
    assert in_force.readings["ada reader"].outcome == "negative"
    assert run(study_dir, "form", "--reread", "NCT0042") == 1 and "not on the worklist: NCT0042" in capsys.readouterr().out


def test_a_quote_copied_wrongly_can_be_put_right(study_dir):
    reads(study_dir, {"NCT0001": met(original_text="WRONG QUOTE")})
    run(study_dir, "form", "--reread", "NCT0001")
    fill(form_of(study_dir), {"NCT0001": met()})
    assert run(study_dir, "record", "--revise") == 0
    assert [a.original_text for a in log_of(study_dir).adjudications] == ["WRONG QUOTE", QUOTE]


def test_a_source_cited_by_mistake_is_withdrawn_with_a_reason(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()})
    capsys.readouterr()
    cited = ("withdraw", "--trial", "NCT0001", "--source", TOPLINE)
    assert run(study_dir, *cited) == 1 and "a withdrawal needs its reason" in capsys.readouterr().out
    assert run(study_dir, *cited, "--reason", "this release is about another trial") == 0
    withdrawal, = log_of(study_dir).withdrawals
    assert (withdrawal.adjudicator, withdrawal.source_type, withdrawal.recorded_on) == ("ada reader", "press_release_or_filing", TODAY)
    assert run(study_dir, "withdraw", "--trial", "NCT0003", "--source", TOPLINE, "--reason", "none") == 1
    assert "NOT DONE: NCT0003: ada reader has no reading of" in capsys.readouterr().out


def test_a_withdrawn_source_can_be_read_again_only_from_the_next_day(study_dir, capsys):
    reads(study_dir, {"NCT0001": met(hazard_ratio="0.99")})
    run(study_dir, "withdraw", "--trial", "NCT0001", "--source", TOPLINE, "--reason", "misread the table")
    capsys.readouterr()
    # The log cannot tell the order of a withdrawal and a reading made on one day, whoever makes the reading.
    for who in (ADA, BEN):
        assert reads(study_dir, {"NCT0001": met(hazard_ratio="0.72")}, by=who) == 1
        assert "a reading of this source was withdrawn today; it can be read again from tomorrow" in capsys.readouterr().out
    assert reads(study_dir, {"NCT0001": met(hazard_ratio="0.72")}, by=BEN, today=TOMORROW) == 0
    assert reads(study_dir, {"NCT0001": met(hazard_ratio="0.72")}, today=TOMORROW) == 0
    assert results(log_of(study_dir), TOMORROW)["NCT0001"].hazard_ratio == 0.72       # they never differed: no disagreement


# --- disagreements -------------------------------------------------------------------------------------


def test_a_disagreement_is_shown_to_both_and_settled_only_by_a_reconciliation_with_its_reason(study_dir, capsys):
    disagreements = a_disagreement(study_dir)
    assert awaiting_result(log_of(study_dir), TODAY) == {"NCT0001": "disagreement"}
    assert "1 source read differently, listed in" in capsys.readouterr().out
    row, = rows_of(disagreements)
    assert (row["first_adjudicator"], row["first_hazard_ratio"], row["second_adjudicator"], row["second_hazard_ratio"]) == (
        "ada reader", "0.72", "ben second", "0.78")
    assert (row["first_disclosed_on"], row["second_disclosed_on"], row["settled_outcome"]) == ("2026-03-01", "2026-03-02", "")
    assert run(study_dir, "status") == 0 and "NCT0001  read differently" in capsys.readouterr().out

    fill(disagreements, {"NCT0001": {**SETTLED, "reason": ""}})
    assert run(study_dir, "reconcile", by=BOTH) == 1
    assert "row 2 (NCT0001): a reconciliation needs its reason" in capsys.readouterr().out
    fill(disagreements, {"NCT0001": {**SETTLED, "settled_outcome": "Positive"}})       # however the outcome is capitalised
    # It is the two who read the source who settle it, both of them.
    assert run(study_dir, "reconcile", by=ADA) == 1
    assert "both adjudicators" in capsys.readouterr().out
    assert run(study_dir, "reconcile", by=BOTH) == 0
    reconciliation, = log_of(study_dir).reconciliations
    assert (reconciliation.adjudicators, reconciliation.recorded_on) == (("ada reader", "ben second"), TODAY)
    result = results(log_of(study_dir), TODAY)["NCT0001"]
    assert (result.outcome, result.hazard_ratio, result.readout_date) == ("positive", 0.72, dt.date(2026, 3, 1))
    # Running it again records nothing more, and the list is then written afresh.
    assert run(study_dir, "reconcile", by=BOTH) == 0 and len(log_of(study_dir).reconciliations) == 1
    assert run(study_dir, "disagreements") == 0 and "0 sources read differently" in capsys.readouterr().out


@pytest.mark.parametrize("settled, why", [
    ({"settled_outcome": "negative"}, "both adjudicators read the outcome the same way, so the reconciliation cannot change it"),
    ({"settled_hazard_ratio": "nan"}, "hazard ratio nan is not between"),
    ({"settled_outcome": "won"}, "the settled outcome must be one of positive, negative, void, not 'won'"),
    ({"settled_disclosed_on": ""}, "'' is not a date"),
])
def test_a_reconciliation_that_the_rules_refuse_is_not_recorded(study_dir, capsys, settled, why):
    fill(a_disagreement(study_dir), {"NCT0001": {**SETTLED, **settled}})
    capsys.readouterr()
    assert run(study_dir, "reconcile", by=BOTH) == 1
    assert f"row 2 (NCT0001): {why}" in capsys.readouterr().out and log_of(study_dir).reconciliations == ()


def test_a_list_a_spreadsheet_has_rewritten_the_dates_and_numbers_of_still_reconciles(study_dir):
    disagreements = a_disagreement(study_dir)
    fill(disagreements, {"NCT0001": {**SETTLED, "first_disclosed_on": "3/1/2026", "second_disclosed_on": "3/2/2026",
                                     "first_hazard_ratio": ".72", "second_hazard_ratio": "0.780"}})
    assert run(study_dir, "reconcile", by=BOTH) == 0 and len(log_of(study_dir).reconciliations) == 1


def test_an_endpoint_named_for_a_hazard_ratio_left_blank_is_refused(study_dir, capsys):
    fill(a_disagreement(study_dir), {"NCT0001": {**SETTLED, "settled_hazard_ratio": ""}})
    capsys.readouterr()
    assert run(study_dir, "reconcile", by=BOTH) == 1
    assert "an endpoint is named for a hazard ratio that is left blank" in capsys.readouterr().out


def test_a_list_can_be_reconciled_a_row_at_a_time_over_several_days(study_dir):
    reads(study_dir, {"NCT0001": met(hazard_ratio="0.72"), "NCT0002": met(source="https://example.test/y", hazard_ratio="0.5")})
    reads(study_dir, {"NCT0001": met(hazard_ratio="0.78"), "NCT0002": met(source="https://example.test/y", hazard_ratio="0.6")},
          by=BEN)
    run(study_dir, "disagreements")
    disagreements = working(study_dir, "disagreements.csv")
    fill(disagreements, {"NCT0001": SETTLED})
    assert run(study_dir, "reconcile", by=BOTH) == 0
    second = {**SETTLED, "settled_hazard_ratio": "0.5", "settled_hazard_ratio_endpoint": "Progression-free survival (PFS)"}
    fill(disagreements, {"NCT0002": second})
    assert run(study_dir, "reconcile", by=BOTH, today=TOMORROW) == 0
    assert [r.nct for r in log_of(study_dir).reconciliations] == ["NCT0001", "NCT0002"]


def test_putting_a_quote_right_leaves_a_reconciled_trial_settled(study_dir):
    fill(a_disagreement(study_dir), {"NCT0001": SETTLED})
    run(study_dir, "reconcile", by=BOTH)
    run(study_dir, "form", "--reread", "NCT0001", today=TOMORROW)
    fill(form_of(study_dir), {"NCT0001": met(hazard_ratio="0.72", original_text="The corrected quote.")})
    assert run(study_dir, "record", "--revise", today=TOMORROW) == 0
    assert results(log_of(study_dir), TOMORROW)["NCT0001"].hazard_ratio == 0.72


def test_a_disagreement_about_the_language_needs_the_language_settled(study_dir, capsys):
    disagreements = a_disagreement(study_dir, ada=met(language="zh", translation="It met."), ben=met())
    fill(disagreements, {"NCT0001": {**SETTLED, "settled_hazard_ratio": "", "settled_hazard_ratio_endpoint": ""}})
    capsys.readouterr()
    assert run(study_dir, "reconcile", by=BOTH) == 1 and "must say which language" in capsys.readouterr().out
    fill(disagreements, {"NCT0001": {"settled_language": "zh"}})
    assert run(study_dir, "reconcile", by=BOTH) == 0
    assert results(log_of(study_dir), TODAY)["NCT0001"].disclosure_language == "zh"


def test_a_list_of_disagreements_is_settled_once_and_against_the_readings_it_showed(study_dir, capsys):
    disagreements = a_disagreement(study_dir)
    # The same source on two rows, settled two ways.
    fill(disagreements, {"NCT0001": [SETTLED, {**SETTLED, "settled_hazard_ratio": "0.78"}]})
    capsys.readouterr()
    assert run(study_dir, "reconcile", by=BOTH) == 1
    assert "row 3 (NCT0001): the same source is settled twice in this file" in capsys.readouterr().out
    # A settlement typed and not yet recorded is kept when the list is written again.
    fill(disagreements, {"NCT0001": [SETTLED]})
    rows = rows_of(disagreements)
    with disagreements.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerow(rows[0])
    assert run(study_dir, "disagreements") == 0
    assert rows_of(disagreements)[0]["reason"] == SETTLED["reason"]
    # One of them then changes their reading. What the list shows is no longer what would be settled.
    run(study_dir, "form", "--reread", "NCT0001")
    fill(form_of(study_dir), {"NCT0001": met(hazard_ratio="0.75")})
    assert run(study_dir, "record", "--revise") == 0
    capsys.readouterr()
    assert run(study_dir, "reconcile", by=BOTH) == 1
    assert "the readings have changed since this list was written; run disagreements again" in capsys.readouterr().out
    assert log_of(study_dir).reconciliations == ()


def test_a_list_whose_settlement_no_longer_fits_the_readings_is_written_afresh(study_dir, capsys):
    disagreements = a_disagreement(study_dir)
    fill(disagreements, {"NCT0001": SETTLED})
    run(study_dir, "form", "--reread", "NCT0001", by=BEN)
    fill(form_of(study_dir, "ben-second"), {"NCT0001": met(hazard_ratio="0.75", disclosed_on="2026-03-02")})
    assert run(study_dir, "record", "--revise", by=BEN) == 0
    capsys.readouterr()
    assert run(study_dir, "reconcile", by=BOTH) == 1 and "run disagreements again" in capsys.readouterr().out
    assert run(study_dir, "disagreements") == 0                                # which it now can be
    row, = rows_of(disagreements)
    assert (row["second_hazard_ratio"], row["settled_outcome"]) == ("0.75", "")


def test_a_typed_settlement_is_not_written_over_when_its_trial_gains_a_source(study_dir, capsys):
    disagreements = a_disagreement(study_dir)
    fill(disagreements, {"NCT0001": SETTLED})
    paper = met(nct="NCT0001", source_type="paper_or_regulator", source="https://example.test/paper")
    assert reads(study_dir, {"NCT0003": paper}, today=TOMORROW) == 0
    assert len(log_of(study_dir).adjudications) == 3
    capsys.readouterr()
    # The trial is now held back for the paper, but this source was laid open before and its settlement still fits.
    assert run(study_dir, "disagreements", today=TOMORROW) == 0
    row, = rows_of(disagreements)
    assert (row["source"], row["reason"]) == (TOPLINE, SETTLED["reason"])
    assert run(study_dir, "reconcile", by=BOTH, today=TOMORROW) == 0 and len(log_of(study_dir).reconciliations) == 1


def test_a_slip_in_a_reconciliation_is_put_right_on_purpose_and_both_stay_in_the_log(study_dir, capsys):
    disagreements = a_disagreement(study_dir)
    fill(disagreements, {"NCT0001": {**SETTLED, "settled_hazard_ratio": "0.27"}})          # 0.72 was meant
    run(study_dir, "reconcile", by=BOTH)
    assert results(log_of(study_dir), TODAY)["NCT0001"].hazard_ratio == 0.27
    # The list no longer shows the source. They ask for its trial again and settle it as it should have been.
    assert run(study_dir, "disagreements", today=TOMORROW) == 0 and rows_of(disagreements) == []
    assert run(study_dir, "disagreements", "--reread", "NCT0001", today=TOMORROW) == 0
    fill(disagreements, {"NCT0001": {**SETTLED, "reason": "0.27 was a slip for 0.72"}})
    capsys.readouterr()
    assert run(study_dir, "reconcile", by=BOTH, today=TOMORROW) == 1
    assert "this source was reconciled on 2026-10-12; reconcile with --revise to replace that" in capsys.readouterr().out
    assert run(study_dir, "reconcile", "--revise", by=BOTH, today=TOMORROW) == 0
    assert [r.hazard_ratio for r in log_of(study_dir).reconciliations] == [0.27, 0.72]
    assert results(log_of(study_dir), TOMORROW)["NCT0001"].hazard_ratio == 0.72


def test_a_correction_typed_for_a_reconciled_source_is_kept_when_the_list_is_written_again(study_dir, capsys):
    disagreements = a_disagreement(study_dir)
    fill(disagreements, {"NCT0001": {**SETTLED, "settled_hazard_ratio": "0.27"}})
    run(study_dir, "reconcile", by=BOTH)
    run(study_dir, "disagreements", "--reread", "NCT0001", today=TOMORROW)
    corrected = {**SETTLED, "reason": "0.27 was a slip for 0.72"}
    fill(disagreements, {"NCT0001": corrected})
    # Before they record it, someone runs the plain step. The correction is not what the log holds, so it is kept.
    capsys.readouterr()
    assert run(study_dir, "disagreements", today=TOMORROW) == 0
    row, = rows_of(disagreements)
    assert (row["settled_hazard_ratio"], row["reason"]) == ("0.72", corrected["reason"])
    assert run(study_dir, "reconcile", "--revise", by=BOTH, today=TOMORROW) == 0
    # Once recorded it is what the log holds, and the list is empty again.
    assert run(study_dir, "disagreements", today=TOMORROW) == 0 and rows_of(disagreements) == []


def test_a_list_with_one_settlement_that_still_fits_and_one_that_does_not_keeps_the_one_and_says_so(study_dir, capsys):
    reads(study_dir, {"NCT0001": met(hazard_ratio="0.72"), "NCT0002": met(source="https://example.test/y", hazard_ratio="0.5")})
    reads(study_dir, {"NCT0001": met(hazard_ratio="0.78"), "NCT0002": met(source="https://example.test/y", hazard_ratio="0.6")},
          by=BEN)
    run(study_dir, "disagreements")
    disagreements = working(study_dir, "disagreements.csv")
    second = {**SETTLED, "settled_hazard_ratio": "0.5", "settled_hazard_ratio_endpoint": "Progression-free survival (PFS)"}
    fill(disagreements, {"NCT0001": SETTLED, "NCT0002": second})
    # Before they record it, Ben changes his reading of the first source.
    run(study_dir, "form", "--reread", "NCT0001", by=BEN)
    fill(form_of(study_dir, "ben-second"), {("NCT0001", TOPLINE): met(hazard_ratio="0.75")})
    assert run(study_dir, "record", "--revise", by=BEN) == 0
    capsys.readouterr()
    assert run(study_dir, "reconcile", by=BOTH) == 1 and log_of(study_dir).reconciliations == ()
    assert run(study_dir, "disagreements") == 0
    assert f"1 settlement typed in the old list no longer fit the readings and were dropped: NCT0001 ({TOPLINE})" in capsys.readouterr().out
    first, kept = rows_of(disagreements)
    assert (first["settled_outcome"], kept["nct"], kept["settled_hazard_ratio"], kept["reason"]) == ("", "NCT0002", "0.5", SETTLED["reason"])
    assert run(study_dir, "reconcile", by=BOTH) == 0 and [r.nct for r in log_of(study_dir).reconciliations] == ["NCT0002"]


def test_a_paper_is_one_source_however_its_doi_is_written(study_dir, capsys):
    reads(study_dir, {"NCT0001": met(source_type="paper_or_regulator", source="https://doi.org/10.1056/NEJMoa1")})
    capsys.readouterr()
    for written in ("https://www.doi.org/10.1056/NEJMoa1", "https://doi.org/10.1056/nejmoa1/", "doi: 10.1056/NEJMoa1",
                    "10.1056/NEJMoa1", "https://dx.doi.org/10.1056/NEJMoa1#abstract"):
        assert reads(study_dir, {"NCT0002": met(nct="NCT0001", source_type="paper_or_regulator", source=written)}, by=BEN) == 1
        assert "this looks like the source already cited as paper_or_regulator" in capsys.readouterr().out


def test_a_source_first_cited_after_the_two_have_differed_is_reconciled_even_when_read_alike(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()})
    reads(study_dir, {"NCT0001": {"nothing_found": "a safety review only"}}, by=BEN)
    run(study_dir, "withdraw", "--trial", "NCT0001", "--source", TOPLINE, "--reason", "Ben is right")
    abstract = met(source_type="conference", source="https://example.test/abstract")
    # The same day a new source for the trial is refused: the log could not tell whether it came before they talked.
    assert reads(study_dir, {"NCT0001": abstract}, by=BEN) == 1
    assert "a source of this trial was first read differently today; a new source for it can be recorded from tomorrow" in capsys.readouterr().out
    assert reads(study_dir, {"NCT0001": abstract}, by=BEN, today=TOMORROW) == 0
    assert reads(study_dir, {"NCT0001": abstract}, today=TOMORROW) == 0
    assert results(log_of(study_dir), TOMORROW) == {}                             # read alike, but not independently
    assert run(study_dir, "status", today=TOMORROW) == 0 and "NCT0001  read differently" in capsys.readouterr().out
    assert run(study_dir, "disagreements", today=TOMORROW) == 0
    fill(working(study_dir, "disagreements.csv"), {"NCT0001": {**SETTLED, "settled_hazard_ratio": "", "settled_hazard_ratio_endpoint": "",
                                                              "reason": "both read the abstract after talking about the release"}})
    assert run(study_dir, "reconcile", by=BOTH, today=TOMORROW) == 0
    assert results(log_of(study_dir), TOMORROW)["NCT0001"].outcome == "positive"


def test_a_dissent_dated_after_today_stops_the_command_and_one_for_a_trial_off_the_worklist_is_shown(study_dir, capsys):
    reads(study_dir, {"NCT0001": met()})
    reads(study_dir, {"NCT0001": {"nothing_found": "a safety review only"}}, by=BEN, today=TOMORROW)
    capsys.readouterr()
    assert run(study_dir, "status") == 1 and "the log holds an entry dated 2026-10-13" in capsys.readouterr().out
    worklist = study_dir / "adjudication" / "reference" / "worklist.csv"
    worklist.write_text(worklist.read_text().replace("NCT0001,ALPHA,A Study of X,Overall survival\n", ""))
    assert run(study_dir, "status", today=TOMORROW) == 0
    assert "NCT0001  read differently  (no longer on the worklist)" in capsys.readouterr().out


def test_a_trial_is_held_back_whichever_of_them_has_the_source_still_to_read(study_dir, capsys):
    paper = met(source_type="paper_or_regulator", source="https://example.test/paper", disclosed_on="2026-06-01")
    reads(study_dir, {"NCT0001": met(hazard_ratio="0.72")})
    reads(study_dir, {("NCT0001", TOPLINE): met(hazard_ratio="0.78"), "NCT0002": {**paper, "nct": "NCT0001"}}, by=BEN)
    capsys.readouterr()                                                          # here it is Ada who has not read the paper
    assert run(study_dir, "disagreements") == 0
    assert "0 sources read differently" in capsys.readouterr().out


def test_the_mark_on_a_list_covers_both_readings_and_everything_in_them(study_dir, capsys):
    disagreements = a_disagreement(study_dir)
    fill(disagreements, {"NCT0001": SETTLED})
    # The second-named adjudicator puts right nothing but the quote. The list no longer shows what is in force.
    run(study_dir, "form", "--reread", "NCT0001", by=BEN)
    fill(form_of(study_dir, "ben-second"), {"NCT0001": met(hazard_ratio="0.78", disclosed_on="2026-03-02", original_text="Other words.")})
    assert run(study_dir, "record", "--revise", by=BEN) == 0
    capsys.readouterr()
    assert run(study_dir, "reconcile", by=BOTH) == 1 and "the readings have changed" in capsys.readouterr().out


def test_a_trial_is_not_laid_open_while_one_of_them_has_a_source_still_to_read(study_dir, capsys):
    paper = met(source_type="paper_or_regulator", source="https://example.test/paper", disclosed_on="2026-06-01")
    reads(study_dir, {"NCT0001": [met(hazard_ratio="0.72"), paper]})
    reads(study_dir, {("NCT0001", TOPLINE): met(hazard_ratio="0.78")}, by=BEN)        # Ben has not read the paper yet
    capsys.readouterr()
    assert run(study_dir, "disagreements") == 0
    said = capsys.readouterr().out
    assert "0 sources read differently, listed in" in said
    assert "1 more wait until both have read every source of their trial" in said
    assert rows_of(working(study_dir, "disagreements.csv")) == []
    assert run(study_dir, "status") == 0 and "NCT0001  awaiting the second adjudicator" in capsys.readouterr().out
    # Once Ben has read the paper too, the disagreement about the release is laid out for both.
    reads(study_dir, {("NCT0001", "https://example.test/paper"): paper}, by=BEN)
    assert run(study_dir, "disagreements") == 0 and len(rows_of(working(study_dir, "disagreements.csv"))) == 1


def test_reading_a_source_alike_after_seeing_the_disagreement_does_not_settle_it(study_dir):
    a_disagreement(study_dir)
    run(study_dir, "form", "--reread", "NCT0001", by=BEN)
    fill(form_of(study_dir, "ben-second"), {"NCT0001": met(hazard_ratio="0.72")})
    assert run(study_dir, "record", "--revise", by=BEN) == 0
    assert awaiting_result(log_of(study_dir), TODAY) == {"NCT0001": "disagreement"}
    # Nor does it if both take their readings back and read it alike the next day.
    for who in (ADA, BEN):
        assert run(study_dir, "withdraw", "--trial", "NCT0001", "--source", TOPLINE, "--reason", "start again", by=who) == 0
    # The same day, under an address that differs by a slash: the log remembers the source although nobody's reading stands.
    assert reads(study_dir, {"NCT0001": met(hazard_ratio="0.72", source=TOPLINE + "/")}) == 1
    for who in (ADA, BEN):
        assert reads(study_dir, {"NCT0001": met(hazard_ratio="0.72")}, by=who, today=TOMORROW) == 0
    assert awaiting_result(log_of(study_dir), TOMORROW) == {"NCT0001": "disagreement"}


def test_a_reconciled_source_is_reopened_by_a_new_reading_and_not_on_the_same_day(study_dir, capsys):
    fill(a_disagreement(study_dir), {"NCT0001": SETTLED})
    assert run(study_dir, "reconcile", by=BOTH) == 0
    capsys.readouterr()
    withdrawing = ("withdraw", "--trial", "NCT0001", "--source", TOPLINE, "--reason", "second thoughts")
    assert run(study_dir, *withdrawing, by=BEN) == 1 and "was reconciled today" in capsys.readouterr().out
    run(study_dir, "form", "--reread", "NCT0001")
    fill(form_of(study_dir), {"NCT0001": met(endpoint_results="not_met")})
    assert run(study_dir, "record", "--revise") == 1
    assert "this source was reconciled today; a new reading of it can be recorded from tomorrow" in capsys.readouterr().out
    assert run(study_dir, "status") == 0                                          # and the log still reads
    assert run(study_dir, "record", "--revise", today=TOMORROW) == 0
    assert awaiting_result(log_of(study_dir), TOMORROW) == {"NCT0001": "disagreement"}
