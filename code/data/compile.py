"""Compile authored YAML calls into canonical JSONL files + SFT rows + xlsx view.

Refuses to compile if the gold validator reports any ERROR.

Outputs:
  data/facts/{split}.jsonl        fact records (ground truth)
  data/transcripts/{split}.jsonl  raw transcript text + tagged turns + noise log
  data/gold/{split}.jsonl         target JSON + alignment + rendered reference text
  data/sft/{train,val}.jsonl      {id, transcript, call_timestamp_utc, target}  (no prompt inside)
  (workbook view: code/data/build_workbook.py)
  data/SHA256SUMS

Run: python3 code/data/compile.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import AUTHORING, ROOT, load_split  # noqa: E402
from common.render import render  # noqa: E402
from data.validate_gold import global_checks, validate_call  # noqa: E402

DATA = ROOT / "data"
SPLITS = ["train", "val"]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    by_split = {s: load_split(s) for s in SPLITS if (AUTHORING / s).exists()}
    errors = 0
    for calls in by_split.values():
        for c in calls:
            errors += sum(1 for lvl, *_ in validate_call(c).items if lvl == "ERROR")
    leaks = [l for l in global_checks([c for s, cs in by_split.items() if s != "real5" for c in cs]) if l.startswith("ERROR")]
    if errors or leaks:
        print(f"refusing to compile: {errors} validator errors, {len(leaks)} leakage errors (run validate_gold.py)")
        return 1

    written = []
    for split, calls in by_split.items():
        sub = "real5" if split == "real5" else None
        facts, trans, gold, sft = [], [], [], []
        for c in calls:
            ts = c["setup"].get("call_timestamp_utc")
            facts.append({k: c[k] for k in ("call_id", "split", "blueprint", "setup", "chief_complaint",
                                             "assessment", "response", "education", "risk_flags")})
            trans.append({"call_id": c["call_id"], "split": split, "call_timestamp_utc": ts,
                          "length_bucket": c["setup"].get("length_bucket"), "transcript": c["transcript"],
                          "turns": c["turns"], "noise_events": c["noise_events"]})
            gold.append({"call_id": c["call_id"], "split": split, "target": c["target"],
                         "alignment": c["alignment"], "rendered": render(c["target"], ts)})
            sft.append({"id": c["call_id"], "transcript": c["transcript"], "call_timestamp_utc": ts,
                        "target": c["target"]})
        base = DATA / sub if sub else DATA
        name = "calls" if sub else split
        for folder, rows in (("facts", facts), ("transcripts", trans), ("gold", gold)):
            p = (base / f"{folder}.jsonl") if sub else (base / folder / f"{name}.jsonl")
            _write_jsonl(p, rows)
            written.append(p)
        if split in ("train", "val"):
            p = DATA / "sft" / f"{split}.jsonl"
            _write_jsonl(p, sft)
            written.append(p)
        print(f"{split:6} {len(calls):4} calls compiled")

    with (DATA / "SHA256SUMS").open("w") as f:
        for p in sorted(written):
            f.write(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}\n")
    print(f"wrote {len(written)} files + data/SHA256SUMS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
