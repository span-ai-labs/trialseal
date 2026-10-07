"""Build the refined trial universe from a frozen registry snapshot.

The snapshot is a broad superset (see scripts/snapshot_universe.py). This module
flattens each record and applies the filters that the pre-build research found to
work: a time-to-event pattern on the primary-outcome text, and exclusion of
withdrawn trials. Sponsor class, primary purpose and MeSH tags proved too noisy
to filter on, so they are kept as columns for hand review, not used as filters.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import pathlib
import re

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Tuned on two hand-labelled samples in the pre-build research; precision is in-sample.
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


def parse_date(s: str | None) -> dt.date | None:
    """Registry dates are YYYY-MM-DD or YYYY-MM; a month-only date maps to its first day."""
    if not s:
        return None
    parts = [int(x) for x in s.split("-")]
    return dt.date(parts[0], parts[1], parts[2] if len(parts) > 2 else 1)


def add_months(d: dt.date, months: int) -> dt.date:
    y, m = divmod(d.year * 12 + d.month - 1 + months, 12)
    last = [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m]
    return dt.date(y, m + 1, min(d.day, last))


def flatten(study: dict) -> dict:
    ps = study.get("protocolSection", {})
    ident, status = ps.get("identificationModule", {}), ps.get("statusModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {})
    design = ps.get("designModule", {})
    arms = ps.get("armsInterventionsModule", {})
    prim = ps.get("outcomesModule", {}).get("primaryOutcomes", [])
    docs = study.get("documentSection", {}).get("largeDocumentModule", {}).get("largeDocs", [])
    pcd = status.get("primaryCompletionDateStruct", {})
    title_text = " ".join(filter(None, [ident.get("briefTitle"), ident.get("officialTitle")]))
    prim_text = " | ".join(str(o.get("measure", "")) for o in prim)
    return {
        "nct": ident.get("nctId"),
        "acronym": ident.get("acronym"),
        "org_study_id": ident.get("orgStudyIdInfo", {}).get("id"),
        "brief_title": ident.get("briefTitle"),
        "status": status.get("overallStatus"),
        "lead_sponsor": sponsor.get("leadSponsor", {}).get("name"),
        "sponsor_class": sponsor.get("leadSponsor", {}).get("class"),
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
        "primary_outcomes": prim_text,
        "primary_time_frames": " | ".join(str(o.get("timeFrame", "")) for o in prim),
        "n_primary_outcomes": len(prim),
        "tte_primary": any(TTE.search(str(o.get("measure", ""))) for o in prim),
        "noninferiority_mention": bool(NONINF.search(title_text + " " + prim_text)),
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
    out["industry"] = out["sponsor_class"] == "INDUSTRY"
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
                "industry_noninferiority_mention": int(ind["noninferiority_mention"].sum()),
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
