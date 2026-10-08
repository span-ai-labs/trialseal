"""Made-up registry records for tests."""


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
