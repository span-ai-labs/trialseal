import datetime as dt

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
