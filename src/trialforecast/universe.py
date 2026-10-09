"""Turn a frozen registry snapshot into the study's candidates.

The snapshot is a broad superset (see scripts/snapshot_universe.py). This module
flattens each record, keeps trials with a time-to-event primary endpoint that are
not withdrawn, and gives each candidate what later steps need: its scored
endpoint, its reference class (sponsor type by endpoint type), the alias record
its readout may be announced under, and a tag where the design needs review
before it can be eligible. Primary purpose and MeSH tags proved too noisy to
filter on, so they are kept as columns for hand review, not used as filters.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import pathlib
import re

import pandas as pd

from trialforecast.dates import add_months

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Decides which trials are candidates. Tuned on two hand-labelled samples in the
# pre-build research; precision is in-sample.
TTE = re.compile(
    r"surviv|\bPFS\b|\bOS\b|\bDFS\b|\bEFS\b|\bRFS\b|\bMFS\b|\bDMFS\b|\bi?DFS\b|\bTTP\b|\bTTF\b"
    r"|progression[- ]free|free[- ]progression|disease[- ]free|event[- ]free|recurrence[- ]free"
    r"|relapse[- ]free|metastasis[- ]free|failure[- ]free"
    r"|time to (?:tumou?r |disease |local |first |distant )?"
    r"(?:progression|recurrence|relapse|death|treatment failure|event|metast)"
    r"|all-cause mortality|death from any cause",
    re.I,
)
NONINF = re.compile(r"non[- ]?inferior", re.I)

# Endpoint types of a time-to-event measure. Registry text is free-form, so the
# patterns accept "X-free", "X free" and "X - free", and common misspellings.
OVERALL_SURVIVAL = re.compile(
    r"overall[\s-]*survival|(?-i:\bOS\b)|death from any cause|all[- ]cause mortality|time to death", re.I
)
PROGRESSION = re.compile(
    r"\bPFS\b|\bi?DFS\b|\bEFS\b|\bRFS\b|\bD?MFS\b|\bTTP\b"
    r"|(?:progress\w*|disease|event|recurren\w*|relapse|metasta\w*|failure|leuka?emia|tumou?r|cancer)\s*-?\s*free"
    r"|free[- ]progression|with ?out (?:progression|recurrence|relapse)"
    r"|\b(?:progression|recurrence|relapse)\b",
    re.I,
)
QUALIFIED_SURVIVAL = re.compile(r"free|specific", re.I)
ENDPOINT_TYPES = ("overall_survival", "progression", "other_time_to_event")
SPONSOR_TYPES = ("industry", "non_industry")
TITLE_TRIAL_NAME = re.compile(r"\(([A-Za-z][\w .\-/]{2,40})\)\s*$")


def parse_date(s: str | None) -> dt.date | None:
    """Registry dates are YYYY-MM-DD or YYYY-MM; a month-only date maps to its first day."""
    if not isinstance(s, str) or not s:  # a record read from a table carries NaN where the registry gave no date
        return None
    parts = [int(x) for x in s.split("-")]
    return dt.date(parts[0], parts[1], parts[2] if len(parts) > 2 else 1)


def endpoint_type(measure: str) -> str | None:
    """Endpoint type of a primary outcome measure, or None if it is not time-to-event.

    A measure naming two types (a composite, or "PFS and OS") takes the one named
    first. Survival with no qualifier is overall survival; survival qualified in a
    way we do not recognise is other time-to-event.
    """
    if not TTE.search(measure):
        return None
    named = []
    for name, pattern in (("overall_survival", OVERALL_SURVIVAL), ("progression", PROGRESSION)):
        match = pattern.search(measure)
        if match:
            named.append((match.start(), name))
    if named:
        return min(named)[1]
    if "surviv" in measure.lower() and not QUALIFIED_SURVIVAL.search(measure):
        return "overall_survival"
    return "other_time_to_event"


def scored_endpoint(primary_outcomes: list[dict]) -> tuple[str | None, str | None]:
    """The first time-to-event primary endpoint listed, with its endpoint type."""
    for outcome in primary_outcomes:
        measure = str(outcome.get("measure", ""))
        its_type = endpoint_type(measure)
        if its_type:
            return measure, its_type
    return None, None


# Companies the registry classes as something other than industry (ADR-0016). Each develops or sells a drug or a
# device for profit. The list is published with the protocol; a sponsor type is sealed with each batch, so a name
# added later changes only batches sealed afterwards.
COMPANIES_THE_REGISTRY_CLASSES_OTHERWISE = (
    "Ahon Pharmaceutical Co., Ltd.",
    "Biotech Pharmaceutical Co., Ltd.",
    "ImmuneOnco Biopharmaceuticals (Shanghai) Inc.",
    "S.LAB (SOLOWAYS)",
    "Shanghai Junshi Bioscience Co., Ltd.",
    "Shouyao Holdings (Beijing) Co. LTD",
    "Steba Biotech S.A.",
    "THERABIONIC INC.",
    "WALA Heilmittel GmbH",
    "Xi'an Xintong Pharmaceutical Research Co.,Ltd.",
)


def _name_key(name: str | None) -> str:
    """A sponsor's name without case, spacing or punctuation, which the registry does not keep consistent."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


_COMPANIES = frozenset(_name_key(name) for name in COMPANIES_THE_REGISTRY_CLASSES_OTHERWISE)


def sponsor_type(sponsor_class: str | None, lead_sponsor: str | None = None) -> str | None:
    """Industry-led or not: the registry's class for the lead sponsor, except for the companies it classes otherwise."""
    if _name_key(lead_sponsor) in _COMPANIES:
        return "industry"
    if not sponsor_class or sponsor_class == "UNKNOWN":
        return None
    return "industry" if sponsor_class == "INDUSTRY" else "non_industry"


# Intervention types that can be the drug under test; procedures, devices and imaging cannot.
DRUG_TYPES = ("DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT")
_PARENTHETICAL = re.compile(r"\([^)]*\)")
_DOSE_ONWARDS = re.compile(r"\s\d[\d.,]*\s*(?:mg|mcg|µg|g|ml|iu|units?)\b.*$")


def drug_name(written: str) -> str:
    """One spelling per drug: lower case, without a parenthetical or a dose."""
    return " ".join(_DOSE_ONWARDS.sub("", _PARENTHETICAL.sub(" ", written).casefold()).split())


def investigational_drug(study: dict) -> str | None:
    """The drug a trial tests: the first drug the registry lists as given in experimental arms only.

    A default for screening to correct. A backbone given only in the experimental
    arm can be listed ahead of the drug under test, and a code name is not matched
    to the name the drug was given later.
    """
    arms = study.get("protocolSection", {}).get("armsInterventionsModule", {})
    experimental = {g.get("label") for g in arms.get("armGroups", []) if g.get("type") == "EXPERIMENTAL"}
    for intervention in arms.get("interventions", []):
        given_in = set(intervention.get("armGroupLabels", []))
        name = intervention.get("name") or ""
        if (intervention.get("type") in DRUG_TYPES and given_in and given_in <= experimental
                and "placebo" not in name.lower() and drug_name(name)):
            return drug_name(name)
    return None


def alias_record(study: dict) -> dict:
    """The names a trial's readout may be announced under, which often differ from the registry's."""
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {})
    interventions = ps.get("armsInterventionsModule", {}).get("interventions", [])

    def distinct(values):
        return list(dict.fromkeys(v for v in values if v))

    # Announcements usually use a trial name that the registry holds only at the end of the title.
    # These are unverified: the same position also holds disease abbreviations ("NSCLC").
    title_names = []
    for title in (ident.get("briefTitle"), ident.get("officialTitle")):
        match = TITLE_TRIAL_NAME.search(title or "")
        if match:
            title_names.append(match.group(1).strip())

    listed = [n for i in interventions for n in [i.get("name"), *i.get("otherNames", [])] if n]
    return {
        "nct": ident.get("nctId"),
        "acronym": ident.get("acronym"),
        "title_names": distinct(n for n in title_names if n != ident.get("acronym")),
        "sponsor_study_id": ident.get("orgStudyIdInfo", {}).get("id"),
        # Short secondary IDs ("2023") are registry noise and would match anything.
        "other_ids": distinct(i for s in ident.get("secondaryIdInfos", []) if len(i := s.get("id") or "") >= 5),
        "intervention_names": distinct(
            part.strip() for n in listed for part in n.split(";") if "placebo" not in part.lower()
        ),
        "lead_sponsor": sponsor.get("leadSponsor", {}).get("name"),
        "collaborators": distinct(c.get("name") for c in sponsor.get("collaborators", [])),
    }


def flatten(study: dict) -> dict:
    ps = study.get("protocolSection", {})
    ident, status = ps.get("identificationModule", {}), ps.get("statusModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {})
    design = ps.get("designModule", {})
    arms = ps.get("armsInterventionsModule", {})
    description = ps.get("descriptionModule", {})
    prim = ps.get("outcomesModule", {}).get("primaryOutcomes", [])
    docs = study.get("documentSection", {}).get("largeDocumentModule", {}).get("largeDocs", [])
    pcd = status.get("primaryCompletionDateStruct", {})
    prim_text = " | ".join(str(o.get("measure", "")) for o in prim)
    design_text = " ".join(
        filter(None, [ident.get("briefTitle"), ident.get("officialTitle"), description.get("briefSummary"),
                      description.get("detailedDescription"), prim_text])
    )
    scored, scored_type = scored_endpoint(prim)
    sponsor_class = sponsor.get("leadSponsor", {}).get("class")
    its_sponsor_type = sponsor_type(sponsor_class, sponsor.get("leadSponsor", {}).get("name"))
    return {
        "nct": ident.get("nctId"),
        "acronym": ident.get("acronym"),
        "org_study_id": ident.get("orgStudyIdInfo", {}).get("id"),
        "brief_title": ident.get("briefTitle"),
        "status": status.get("overallStatus"),
        "lead_sponsor": sponsor.get("leadSponsor", {}).get("name"),
        "sponsor_class": sponsor_class,
        "sponsor_type": its_sponsor_type,
        "collaborators": "; ".join(c.get("name", "") for c in sponsor.get("collaborators", [])),
        "phases": "/".join(design.get("phases", [])),
        "primary_purpose": design.get("designInfo", {}).get("primaryPurpose"),
        "masking": design.get("designInfo", {}).get("maskingInfo", {}).get("masking"),
        "enrollment": design.get("enrollmentInfo", {}).get("count"),
        "enrollment_type": design.get("enrollmentInfo", {}).get("type"),
        "start_date": status.get("startDateStruct", {}).get("date"),
        "primary_completion_date": pcd.get("date"),
        "primary_completion_type": pcd.get("type"),
        "last_update_posted": status.get("lastUpdatePostDateStruct", {}).get("date"),
        "results_first_posted": status.get("resultsFirstPostDateStruct", {}).get("date"),
        "has_results": bool(study.get("hasResults")),
        "conditions": "; ".join(ps.get("conditionsModule", {}).get("conditions", [])),
        "interventions": "; ".join(
            f'{i.get("type", "")}: {i.get("name", "")}' for i in arms.get("interventions", [])
        ),
        "n_arms": len(arms.get("armGroups", [])),
        "arms": "; ".join(f'{g.get("type", "")}: {g.get("label", "")}' for g in arms.get("armGroups", [])),
        "primary_outcomes": prim_text,
        "primary_time_frames": " | ".join(str(o.get("timeFrame", "")) for o in prim),
        "n_primary_outcomes": len(prim),
        "tte_primary": scored is not None,
        "scored_endpoint": scored,
        "endpoint_type": scored_type,
        "reference_class": f"{its_sponsor_type}/{scored_type}" if its_sponsor_type and scored_type else None,
        # A mention is enough to queue the trial for review; it is not a finding about the design.
        "exclusion_review": "non-inferiority mentioned" if NONINF.search(design_text) else None,
        "investigational_drug": investigational_drug(study),
        "aliases": json.dumps(alias_record(study), ensure_ascii=False),
        "has_protocol_doc": any(d.get("hasProtocol") for d in docs),
        "has_sap_doc": any(d.get("hasSap") for d in docs),
    }


def load_snapshot(snapshot_dir: pathlib.Path) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((snapshot_dir / "manifest.json").read_text())
    with gzip.open(snapshot_dir / "studies.jsonl.gz", "rt", encoding="utf-8") as f:
        rows = [flatten(json.loads(line)) for line in f]
    return pd.DataFrame(rows), manifest


def refine(df: pd.DataFrame, as_of: dt.date) -> pd.DataFrame:
    """Keep time-to-event, non-withdrawn trials and tag them relative to the snapshot date."""
    out = df[df["tte_primary"] & (df["status"] != "WITHDRAWN")].copy()
    pcd = out["primary_completion_date"].map(parse_date)
    out["industry"] = out["sponsor_type"] == "industry"
    out["multi_primary"] = out["n_primary_outcomes"] > 1
    out["pcd_in_past"] = pcd.map(lambda d: d is not None and d <= as_of)
    out["stale_estimate"] = out["pcd_in_past"] & (out["primary_completion_type"] == "ESTIMATED")
    out["past_12m"] = pcd.map(lambda d: d is not None and add_months(as_of, -12) <= d <= as_of)
    out["past_24m"] = pcd.map(lambda d: d is not None and add_months(as_of, -24) <= d <= as_of)
    out["next_15m"] = pcd.map(lambda d: d is not None and as_of < d <= add_months(as_of, 15))
    return out.sort_values(["primary_completion_date", "nct"]).reset_index(drop=True)


def summarise(u: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, mask in [("past 12 months", u["past_12m"]), ("past 24 months", u["past_24m"]), ("next 15 months", u["next_15m"])]:
        w = u[mask]
        ind = w[w["industry"]]
        rows.append(
            {
                "window": label,
                "all_sponsors": len(w),
                "industry": len(ind),
                "industry_n200plus": int((ind["enrollment"].fillna(0) >= 200).sum()),
                "industry_multi_primary": int(ind["multi_primary"].sum()),
                "industry_has_results": int(ind["has_results"].sum()),
                "industry_stale_estimate": int(ind["stale_estimate"].sum()),
                "industry_exclusion_review": int(ind["exclusion_review"].notna().sum()),
            }
        )
    return pd.DataFrame(rows)


def latest_snapshot() -> pathlib.Path:
    snaps = sorted(p for p in (ROOT / "snapshots").iterdir() if (p / "manifest.json").exists())
    if not snaps:
        raise SystemExit("no snapshot found; run scripts/snapshot_universe.py first")
    return snaps[-1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", type=pathlib.Path, default=None, help="snapshot directory (default: latest)")
    args = ap.parse_args()
    snap = args.snapshot or latest_snapshot()
    df, manifest = load_snapshot(snap)
    as_of = dt.date.fromisoformat(manifest["data_timestamp_start"][:10])
    u = refine(df, as_of)
    out_dir = ROOT / "data" / "universe"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"universe_{as_of.isoformat()}.csv"
    u.to_csv(out, index=False)
    print(f"snapshot {snap.name}: {len(df)} superset records -> {len(u)} refined (as of {as_of})")
    print(summarise(u).to_string(index=False))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
