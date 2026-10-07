import datetime as dt
import json

import pandas as pd

from trialforecast import universe as u


def study(nct, measure, status="RECRUITING", cls="INDUSTRY", pcd="2027-03", pcd_type="ESTIMATED", n_extra=0):
    prim = [{"measure": measure, "timeFrame": "up to 5 years"}] + [{"measure": "ORR"}] * n_extra
    return {
        "hasResults": False,
        "protocolSection": {
            "identificationModule": {"nctId": nct, "briefTitle": "A Study of X Versus Y"},
            "statusModule": {"overallStatus": status, "primaryCompletionDateStruct": {"date": pcd, "type": pcd_type}},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Acme", "class": cls}},
            "designModule": {"phases": ["PHASE3"], "enrollmentInfo": {"count": 500, "type": "ESTIMATED"}},
            "outcomesModule": {"primaryOutcomes": prim},
        },
    }


def test_tte_pattern_hits_and_misses():
    hits = ["Overall Survival (OS)", "Progression-free survival by BICR", "PFS", "Time to disease progression",
            "Invasive disease-free survival", "Event free survival", "Death from any cause"]
    misses = ["Objective response rate", "Incidence of grade 3 neuropathy", "Change in pain score", "Pathological complete response"]
    assert all(u.TTE.search(h) for h in hits)
    assert not any(u.TTE.search(m) for m in misses)


def test_parse_date_handles_month_only():
    assert u.parse_date("2027-03") == dt.date(2027, 3, 1)
    assert u.parse_date("2027-03-15") == dt.date(2027, 3, 15)
    assert u.parse_date(None) is None


def test_add_months_clamps_day():
    assert u.add_months(dt.date(2026, 10, 31), -8) == dt.date(2026, 2, 28)
    assert u.add_months(dt.date(2026, 10, 6), 15) == dt.date(2028, 1, 6)


def test_refine_filters_and_tags():
    as_of = dt.date(2026, 10, 6)
    df = pd.DataFrame([u.flatten(s) for s in [
        study("NCT1", "Overall survival"),
        study("NCT2", "Objective response rate"),                       # not time-to-event
        study("NCT3", "Progression-free survival", status="WITHDRAWN"),  # withdrawn
        study("NCT4", "PFS", cls="OTHER", pcd="2026-01", n_extra=1),     # stale estimate, multi-primary
        study("NCT5", "PFS", pcd="2025-12-01", pcd_type="ACTUAL"),
    ]])
    r = u.refine(df, as_of).set_index("nct")
    assert set(r.index) == {"NCT1", "NCT4", "NCT5"}
    assert r.loc["NCT1", "next_15m"] and not r.loc["NCT1", "past_12m"]
    assert r.loc["NCT4", "stale_estimate"] and r.loc["NCT4", "multi_primary"] and not r.loc["NCT4", "industry"]
    assert r.loc["NCT5", "past_12m"] and not r.loc["NCT5", "stale_estimate"]


def endpoint_type_of(measure):
    return u.flatten(study("NCT9", measure))["endpoint_type"]


def test_endpoint_type_of_a_primary_outcome_measure():
    assert endpoint_type_of("Overall Survival (OS)") == "overall_survival"
    assert endpoint_type_of("Death from any cause") == "overall_survival"
    assert endpoint_type_of("Progression-free survival by BICR") == "progression"
    assert endpoint_type_of("Invasive disease-free survival") == "progression"
    assert endpoint_type_of("Event Free Survival (EFS)") == "progression"
    assert endpoint_type_of("Time to treatment failure") == "other_time_to_event"
    assert endpoint_type_of("Cancer-specific survival") == "other_time_to_event"
    assert endpoint_type_of("Objective response rate") is None


def test_unqualified_survival_is_overall_survival():
    for measure in ("Survival", "2-year survival rate", "Five-year survival rate", "Overall-Survival",
                    "Survival after hematopoietic cell transplantation"):
        assert endpoint_type_of(measure) == "overall_survival", measure
    # A survival endpoint qualified in a way we do not recognise is neither.
    assert endpoint_type_of("Puncture/drainage-Free Survival") == "other_time_to_event"
    assert endpoint_type_of("Disease-specific survival") == "other_time_to_event"


def test_freedom_from_disease_endpoints_are_progression_however_written():
    for measure in ("Invasive breast cancer-free survival", "Recurrence - free survival rates",
                    "tumor-free survival rate", "Leukemia-Free Survival", "Poly-metastatic free survival"):
        assert endpoint_type_of(measure) == "progression", measure


def test_composite_endpoint_ending_in_death_is_not_overall_survival():
    composite = "Number of patients with local or distant recurrence or death from any cause, whichever occurred first"
    assert endpoint_type_of(composite) == "progression"


def test_the_word_os_is_not_the_abbreviation_for_overall_survival():
    assert endpoint_type_of("Dose per os and time to treatment failure") == "other_time_to_event"


def with_primaries(*measures):
    s = study("NCT9", measures[0])
    s["protocolSection"]["outcomesModule"]["primaryOutcomes"] = [{"measure": m} for m in measures]
    return u.flatten(s)


def test_scored_endpoint_is_first_listed_time_to_event_primary():
    both = with_primaries("Progression-free survival (PFS)", "Overall survival (OS)")
    assert both["scored_endpoint"] == "Progression-free survival (PFS)"
    assert both["endpoint_type"] == "progression"

    reversed_order = with_primaries("Overall survival (OS)", "Progression-free survival (PFS)")
    assert reversed_order["scored_endpoint"] == "Overall survival (OS)"
    assert reversed_order["endpoint_type"] == "overall_survival"

    # A first-listed endpoint with no hazard ratio cannot be the scored endpoint.
    response_first = with_primaries("Pathological complete response", "Event-free survival")
    assert response_first["scored_endpoint"] == "Event-free survival"
    assert response_first["endpoint_type"] == "progression"

    assert with_primaries("Objective response rate")["scored_endpoint"] is None


def test_reference_class_combines_sponsor_type_and_endpoint_type():
    industry = u.flatten(study("NCT1", "Overall survival", cls="INDUSTRY"))
    assert industry["sponsor_type"] == "industry"
    assert industry["reference_class"] == "industry/overall_survival"

    for cls in ("NIH", "NETWORK", "OTHER", "OTHER_GOV"):
        row = u.flatten(study("NCT2", "Progression-free survival", cls=cls))
        assert row["sponsor_type"] == "non_industry"
        assert row["reference_class"] == "non_industry/progression"

    # No scored endpoint, no reference class.
    assert u.flatten(study("NCT3", "Objective response rate"))["reference_class"] is None

    # An unknown sponsor class is unknown, not non-industry.
    unknown = u.flatten(study("NCT4", "Overall survival", cls=None))
    assert unknown["sponsor_type"] is None and unknown["reference_class"] is None


def test_alias_record_collects_the_names_a_readout_may_be_announced_under():
    s = study("NCT00000001", "Progression-free survival")
    ps = s["protocolSection"]
    ps["identificationModule"].update({
        "acronym": "EXAMPLE-01",
        "briefTitle": "A Study of Examplimab Plus Chemotherapy in Gastric Cancer (MOCKSTONE-301)",
        "orgStudyIdInfo": {"id": "EXM-301"},
        "secondaryIdInfos": [{"id": "2021-000000-00"}, {"id": "2023"}, {"id": "jRCT0000000000"}],
    })
    ps["sponsorCollaboratorsModule"] = {
        "leadSponsor": {"name": "Acme Pharma", "class": "INDUSTRY"},
        "collaborators": [{"name": "Beta Bio"}, {"name": "Gamma Group"}],
    }
    ps["armsInterventionsModule"] = {"interventions": [
        {"type": "DRUG", "name": "Examplimab", "otherNames": ["EXM-25; ACM598"]},
        {"type": "DRUG", "name": "Otherlizumab", "otherNames": ["OTH-317"]},
        {"type": "DRUG", "name": "Examplimab"},
        {"type": "DRUG", "name": "Placebo matching examplimab"},
    ]}
    assert u.alias_record(s) == {
        "nct": "NCT00000001",
        "acronym": "EXAMPLE-01",
        "title_names": ["MOCKSTONE-301"],
        "sponsor_study_id": "EXM-301",
        "other_ids": ["2021-000000-00", "jRCT0000000000"],
        "intervention_names": ["Examplimab", "EXM-25", "ACM598", "Otherlizumab", "OTH-317"],
        "lead_sponsor": "Acme Pharma",
        "collaborators": ["Beta Bio", "Gamma Group"],
    }


def test_alias_record_survives_a_sparse_registry_entry():
    assert u.alias_record(study("NCT1", "Overall survival")) == {
        "nct": "NCT1", "acronym": None, "title_names": [], "sponsor_study_id": None, "other_ids": [],
        "intervention_names": [], "lead_sponsor": "Acme", "collaborators": [],
    }


def test_flattened_candidate_carries_its_alias_record():
    s = study("NCT1", "Overall survival")
    assert json.loads(u.flatten(s)["aliases"]) == u.alias_record(s)


def test_mention_of_non_inferiority_is_tagged_for_review_and_kept():
    plain = study("NCT1", "Overall survival")
    in_title = study("NCT2", "Overall survival")
    in_title["protocolSection"]["identificationModule"]["officialTitle"] = "A Non-Inferiority Study of X Versus Y"
    in_description = study("NCT3", "Progression-free survival")
    in_description["protocolSection"]["descriptionModule"] = {
        "detailedDescription": "The study will test whether X is noninferior to Y for PFS."
    }
    rows = [u.flatten(s) for s in (plain, in_title, in_description)]
    assert [r["exclusion_review"] for r in rows] == [None, "non-inferiority mentioned", "non-inferiority mentioned"]

    kept = u.refine(pd.DataFrame(rows), dt.date(2026, 10, 6)).set_index("nct")
    assert set(kept.index) == {"NCT1", "NCT2", "NCT3"}
    assert kept.loc["NCT3", "exclusion_review"] == "non-inferiority mentioned"


def test_misspelled_progression_endpoints_are_still_progression():
    for measure in ("Progress free survival", "Progressive free survive assessed by Independent Review Committee",
                    "Locally recurrent free survival", "survival with out recurrence"):
        assert endpoint_type_of(measure) == "progression", measure


def test_summary_counts_candidates_by_window_and_sponsor_type():
    as_of = dt.date(2026, 10, 6)
    df = pd.DataFrame([u.flatten(s) for s in [
        study("NCT1", "Overall survival", pcd="2027-03"),
        study("NCT2", "Overall survival", pcd="2027-06", cls="OTHER"),
        study("NCT3", "PFS", pcd="2026-01", pcd_type="ACTUAL"),
        study("NCT4", "PFS", pcd="2025-01", pcd_type="ACTUAL", cls="NIH"),
    ]])
    s = u.summarise(u.refine(df, as_of)).set_index("window")
    assert (s.loc["next 15 months", "all_sponsors"], s.loc["next 15 months", "industry"]) == (2, 1)
    assert (s.loc["past 12 months", "all_sponsors"], s.loc["past 12 months", "industry"]) == (1, 1)
    assert (s.loc["past 24 months", "all_sponsors"], s.loc["past 24 months", "industry"]) == (2, 1)
