"""Coverage report: are the planned diversity quotas met? (plan.md §2)

Works on blueprints (data/blueprints/*.jsonl) or on authored calls. Targets scale with the
number of calls present, so the 10% pilot is checked against 10% of the full-split targets.

Run: python3 code/data/coverage.py [--blueprints]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import ROOT, load_split  # noqa: E402

FULL = {"train": 500, "val": 100}
CATEGORY_TARGET = {  # full-split counts (train, val)
    "routine": (80, 16), "ambiguous": (60, 12), "asr_error": (60, 12), "medication": (90, 18),
    "supply": (60, 12), "high_risk": (100, 20), "not_applicable": (50, 10),
}
LENGTH_SHARE = {"short": 0.72, "medium": 0.12, "long": 0.16}
# minimum share of non-NA calls carrying the tag / value
TAG_MIN = {
    "name_spelled": .15, "name_drift": .10, "dob_self_corrected": .05, "phone_from_file": .20, "phone_not_given": .05,
    "identity_unresolved": .05, "chart_reading_distractor": .08, "prn_and_scheduled": .20, "liquid_concentration": .08,
    "tall_man_drug": .15, "trap_phrasing": .20, "hedging": .15, "contradiction": .08, "negated_risk_phrase": .15,
    "figurative_risk_language": .03, "late_answers": .30, "split_turns": .30, "crosstalk": .10,
    "offtopic_chatter": .10, "speaker_label_errors": .05, "multi_issue": .25,
}
REL_MIN = {"self": .10, "spouse": .15, "adult_child": .20, "parent": .05, "other_family": .05, "friend_neighbor": .03,
           "paid_caregiver": .05, "facility_staff": .05}
AGE_MIN = {"pediatric": .06, "18-64": .20, "65-89": .40, "90+": .05}
SPLIT_IDX = {"train": 0, "val": 1}


def _from_blueprints(split: str) -> list[dict]:
    p = ROOT / "data" / "blueprints" / f"{split}.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _from_calls(split: str) -> list[dict]:
    out = []
    for c in load_split(split):
        s = c["setup"]
        out.append({"category": s.get("scenario_category"), "subtype": s.get("subtype"),
                    "length": s.get("length_bucket"), "relationship_group": s.get("relationship_group"),
                    "age_group": s.get("patient_age_group"), "agency_type": s.get("agency_type"),
                    "tags": s.get("secondary_tags") or [], "domains": s.get("clinical_domains") or [],
                    "flags": [f["risk_category"] for f in c["risk_flags"]]})
    return out


def report(split: str, rows: list[dict]) -> int:
    n = len(rows)
    if not n:
        return 0
    frac = n / FULL[split]
    short = 0
    print(f"\n=== {split}: {n} calls ({frac:.0%} of full split) ===")
    cat = Counter(r["category"] for r in rows)
    print(f"{'category':16} {'have':>5} {'target':>7}")
    for k, t in CATEGORY_TARGET.items():
        want = round(t[SPLIT_IDX[split]] * frac)
        flag = "" if abs(cat[k] - want) <= 1 else "  <-- off target"
        short += bool(flag)
        print(f"{k:16} {cat[k]:5} {want:7}{flag}")
    ln = Counter(r["length"] for r in rows)
    print("length: " + ", ".join(f"{k} {ln[k]} (target {round(v * n)})" for k, v in LENGTH_SHARE.items()))
    non_na = [r for r in rows if r["category"] != "not_applicable"]
    m = len(non_na) or 1

    def check(title, counter, mins):
        nonlocal short
        print(f"{title}:")
        for k, lo in mins.items():
            share = counter[k] / m
            mark = "ok" if share >= lo else "BELOW"
            short += mark == "BELOW"
            print(f"   {k:26} {counter[k]:3} ({share:5.0%})  min {lo:.0%}  {mark}")

    check("relationship (non-NA)", Counter(r["relationship_group"] for r in non_na), REL_MIN)
    check("age group (non-NA)", Counter(r["age_group"] for r in non_na), AGE_MIN)
    check("secondary tags (non-NA)", Counter(t for r in non_na for t in r["tags"]), TAG_MIN)
    agencies = Counter(r["agency_type"] for r in non_na)
    print("agency types: " + ", ".join(f"{k} {v}" for k, v in agencies.most_common()))
    doms = Counter(d for r in non_na for d in r["domains"])
    print(f"clinical domains ({len(doms)} distinct): " + ", ".join(f"{k} {v}" for k, v in doms.most_common()))
    hr = Counter(r["subtype"] for r in rows if r["category"] == "high_risk")
    print("high-risk subtypes: " + ", ".join(f"{k} {v}" for k, v in sorted(hr.items())))
    na = Counter(r["subtype"] for r in rows if r["category"] == "not_applicable")
    print("NA subtypes: " + ", ".join(f"{k} {v}" for k, v in sorted(na.items())))
    fl = Counter(f for r in rows for f in r.get("flags", []))
    if fl:
        print("expected flags: " + ", ".join(f"{k} {v}" for k, v in sorted(fl.items())))
    return short


def main(argv: list[str]) -> int:
    use_bp = "--blueprints" in argv
    total_short = 0
    for split in ("train", "val"):
        rows = _from_blueprints(split) if use_bp else _from_calls(split)
        total_short += report(split, rows)
    print(f"\n{total_short} quota cells below target "
          "(small pilots cannot hit every minimum; judge the full set against these)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
