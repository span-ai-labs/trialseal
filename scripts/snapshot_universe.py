"""Snapshot the candidate trial universe from ClinicalTrials.gov API v2.

Pulls full study records for a deliberately broad superset (randomised phase 3
interventional trials matching a broad cancer condition list). The registry
completion date only bounds the search (docs/adr/0003): trials read out years
before or after it, so the window is wide on both sides. Narrowing (time-to-event
primary endpoint, screening for an existing public result) happens downstream so
that every later filter can be re-run on the same frozen registry state.

Output: snapshots/<dataTimestamp>/studies.jsonl.gz + manifest.json (with SHA-256).
"""
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://clinicaltrials.gov/api/v2"
UA = "spanai-trial-forecast/0.1"
ROOT = pathlib.Path(__file__).resolve().parent.parent / "snapshots"

COND = (
    "cancer OR neoplasm OR tumor OR carcinoma OR lymphoma OR leukemia OR myeloma OR sarcoma OR melanoma "
    "OR glioma OR glioblastoma OR myelodysplastic OR myelofibrosis OR malignancy OR adenocarcinoma "
    "OR mesothelioma OR neuroblastoma OR metastatic OR metastases OR malignant OR NSCLC OR SCLC OR CLL "
    "OR AML OR HCC OR DLBCL OR GIST OR macroglobulinemia OR myeloproliferative OR astrocytoma "
    "OR medulloblastoma OR cholangiocarcinoma OR thymoma"
)
WINDOW = ("2023-10-01", "2035-12-31")
ADV = (
    "AREA[StudyType]INTERVENTIONAL AND AREA[Phase]PHASE3 AND AREA[DesignAllocation]RANDOMIZED "
    f"AND AREA[PrimaryCompletionDate]RANGE[{WINDOW[0]},{WINDOW[1]}]"
)


def get(path, params=None):
    q = urllib.parse.urlencode(params or {}, quote_via=urllib.parse.quote)
    url = f"{BASE}{path}" + (f"?{q}" if q else "")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # retry transient failures, surface the rest
            if attempt == 4 or getattr(e, "code", None) in (400, 404):
                raise
            time.sleep(5 * (attempt + 1))


def main():
    version = get("/version")
    stamp = version["dataTimestamp"]
    out = ROOT / stamp.replace(":", "")
    if (out / "manifest.json").exists():
        if json.loads((out / "manifest.json").read_text()).get("filter_advanced") == ADV:
            print(f"snapshot for dataTimestamp {stamp} already exists: {out}")
            return 0
        out = ROOT / (stamp.replace(":", "") + "-wide")  # same registry state, wider query
        if (out / "manifest.json").exists():
            print(f"snapshot for dataTimestamp {stamp} already exists: {out}")
            return 0
    out.mkdir(parents=True, exist_ok=True)
    params = {"query.cond": COND, "filter.advanced": ADV, "pageSize": 100, "countTotal": "true"}
    token, n, total = None, 0, None
    sha = hashlib.sha256()
    started = dt.datetime.now(dt.timezone.utc)
    with gzip.open(out / "studies.jsonl.gz", "wt", encoding="utf-8") as f:
        while True:
            p = dict(params)
            if token:
                p["pageToken"] = token
            d = get("/studies", p)
            total = d.get("totalCount", total)
            for s in d.get("studies", []):
                line = json.dumps(s, sort_keys=True, separators=(",", ":"))
                sha.update(line.encode() + b"\n")
                f.write(line + "\n")
                n += 1
            token = d.get("nextPageToken")
            print(f"  {n}/{total}", file=sys.stderr)
            if not token:
                break
            time.sleep(1.0)
    after = get("/version")["dataTimestamp"]
    manifest = {
        "source": "ClinicalTrials.gov API v2",
        "api_version": version.get("apiVersion"),
        "data_timestamp_start": stamp,
        "data_timestamp_end": after,
        "retrieved_utc_start": started.isoformat(timespec="seconds"),
        "retrieved_utc_end": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "query_cond": COND,
        "filter_advanced": ADV,
        "records": n,
        "total_count_reported": total,
        "sha256_of_uncompressed_jsonl": sha.hexdigest(),
        "note": "Superset of the forecasting universe; no time-to-event or hand-review filter applied.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0 if n == total and after == stamp else 1


if __name__ == "__main__":
    sys.exit(main())
