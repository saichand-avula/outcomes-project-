"""Renderer checks: formatters, section structure, and agreement with the compiled gold file.

Run: python3 code/tests/test_render.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import ROOT, load_call  # noqa: E402
from common.render import fmt_dob, fmt_phone, fmt_timestamp, render  # noqa: E402


def main() -> int:
    call = load_call(ROOT / "data/authoring/train/tr-023.yaml")
    got = render(call["target"], call["setup"]["call_timestamp_utc"])
    assert fmt_dob("1951-06-04") == "06/04/1951"
    assert fmt_phone("2025550101") == "(202)-555-0101"
    assert fmt_timestamp("2000-01-01T14:41:00Z") == "[2000-01-01 14:41 UTC]"
    for section in ("Chief Complaint", "Assessment", "Response", "Education"):
        assert section in got, f"missing section {section}"
    assert fmt_timestamp(call["setup"]["call_timestamp_utc"]) in got
    gold = next(json.loads(l) for l in (ROOT / "data/gold/train.jsonl").read_text().splitlines() if f'"{call["call_id"]}"' in l[:40])
    assert got == gold["rendered"], "render differs from data/gold/train.jsonl (run compile.py?)"
    sft = next(json.loads(l) for l in (ROOT / "data/sft/train.jsonl").read_text().splitlines() if f'"{call["call_id"]}"' in l[:40])
    assert call["transcript"] == sft["transcript"], "transcript round-trip mismatch"
    print("test_render: OK (formatters, sections, rendered text and transcript match the compiled files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
