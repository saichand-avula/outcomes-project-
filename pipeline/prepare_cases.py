"""Build the case files the pipeline reads. Run on the Mac from the project root: python3 pipeline/prepare_cases.py

A case is {id, transcript, call_timestamp_utc} (all that unseen data has) plus, for our own validation calls,
  gold_target          the validated gold summary JSON            -> reference-based metrics
  reference_checklist  one line per fact-record item              -> reference-based completeness in the judge
  meta                 category, length bucket, agency ...        -> breakdowns
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pl.checklist import checklist  # noqa: E402


def build(split: str):
    sft = [json.loads(l) for l in (ROOT / "data" / "sft" / f"{split}.jsonl").read_text().splitlines() if l.strip()]
    facts = {r["call_id"]: r for r in map(json.loads, (ROOT / "data" / "facts" / f"{split}.jsonl").read_text().splitlines()) if r}
    out = []
    for r in sft:
        f = facts[r["id"]]
        s = f["setup"]
        out.append({"id": r["id"], "transcript": r["transcript"], "call_timestamp_utc": r["call_timestamp_utc"], "gold_target": r["target"],
                    "reference_checklist": [] if r["target"]["not_applicable"]["is_na"] else checklist(f),
                    "meta": {"split": split, "category": s["scenario_category"], "length": s["length_bucket"], "agency": s["agency_name"], "noise": s.get("asr_noise_level")}})
    return out


if __name__ == "__main__":
    (Path(__file__).resolve().parent / "data").mkdir(exist_ok=True)
    for split in ("val", "train"):
        rows = build(split)
        p = Path(__file__).resolve().parent / "data" / f"{split}_cases.jsonl"
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        print(f"{split}: {len(rows)} cases -> {p.relative_to(ROOT)} ({p.stat().st_size // 1024} KB)")
