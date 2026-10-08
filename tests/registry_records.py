"""Made-up registry records for tests."""


def study(nct, measure, status="RECRUITING", cls="INDUSTRY", pcd="2027-03", pcd_type="ESTIMATED", n_extra=0, drug=None):
    prim = [{"measure": measure, "timeFrame": "up to 5 years"}] + [{"measure": "ORR"}] * n_extra
    return {
        "hasResults": False,
        "protocolSection": {
            "identificationModule": {"nctId": nct, "briefTitle": "A Study of X Versus Y"},
            "statusModule": {"overallStatus": status, "primaryCompletionDateStruct": {"date": pcd, "type": pcd_type}},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Acme", "class": cls}},
            "designModule": {"phases": ["PHASE3"], "enrollmentInfo": {"count": 500, "type": "ESTIMATED"}},
            "outcomesModule": {"primaryOutcomes": prim},
            **({"armsInterventionsModule": arms_testing(drug)} if drug else {}),
        },
    }


def arms_testing(drug):
    """Two arms: the drug with a backbone against the backbone with placebo."""
    return {
        "armGroups": [{"label": "Experimental", "type": "EXPERIMENTAL"},
                      {"label": "Control", "type": "PLACEBO_COMPARATOR"}],
        "interventions": [
            {"type": "DRUG", "name": "Docetaxel", "armGroupLabels": ["Experimental", "Control"]},
            {"type": "DRUG", "name": drug, "armGroupLabels": ["Experimental"]},
            {"type": "DRUG", "name": "Placebo", "armGroupLabels": ["Control"]},
        ],
    }
