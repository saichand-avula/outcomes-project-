"""Judge v5. Calibration reports a problem TYPE (verdict follows from it); completeness checks the main point of each
fact-record item. Faithfulness unchanged from v3/v4.

    python3 run_judge.py [--set first|confirmation] [--url http://localhost:8000/v1] [--model gemma] [--workers 6]

--set first          data/first_set (50 items)         -> results_first_set/judge_outputs.jsonl
--set confirmation   data/confirmation_set (40 items)  -> results_confirmation/judge_outputs.jsonl
Standard library only (judge_lib.py is in this folder).
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from judge_lib import CHECK, VERDICT, ask

HERE = Path(__file__).resolve().parent
NEEDED = ["faithfulness", "calibration", "completeness_match", "completeness_recheck"]
CALIB = {"type": "object", "required": ["analysis", "problem_type", "reason"], "additionalProperties": False, "properties": {
    "analysis": {"type": "string"}, "problem_type": {"type": "string", "enum": ["none", "certainty", "status", "speaker"]},
    "reason": {"type": "string"}}}


def judge_one(args, prompts, item, ref):
    t0 = time.time()
    both = f"TRANSCRIPT\n{item['transcript']}\n\nSUMMARY\n{item['summary']}"
    verdicts, extra = {}, {}
    out = ask(args, prompts["faithfulness"], both, VERDICT, 1500)
    ok = out and out.get("verdict") in ("PASS", "FAIL")
    verdicts["faithfulness"] = {"verdict": out["verdict"], "reason": out.get("reason", "")} if ok else None
    extra["faithfulness_analysis"] = out.get("analysis") if out else None
    out = ask(args, prompts["calibration"], both, CALIB, 1500)
    verdicts["calibration"] = ({"verdict": "PASS" if out["problem_type"] == "none" else "FAIL",
                                "reason": f"[{out['problem_type']}] {out.get('reason', '')}"} if out and out.get("problem_type") else None)
    extra["calibration_analysis"] = out.get("analysis") if out else None
    checks, failed = [], False
    for it in ref["items"]:
        user = f"REFERENCE ITEM\n{it['fact']}\n\nSUMMARY\n{item['summary']}"
        first = ask(args, prompts["completeness_match"], user, CHECK, 300)
        if first is None:
            failed = True
            continue
        rec = {"n": it["n"], "fact": it["fact"], "first": first["present"], "evidence": first["evidence"], "rechecked": None}
        if not first["present"]:
            second = ask(args, prompts["completeness_recheck"], user, CHECK, 300)
            if second is None:
                failed = True
                continue
            rec["rechecked"], rec["evidence"] = second["present"], second["evidence"] or rec["evidence"]
        rec["present"] = first["present"] or bool(rec["rechecked"])
        checks.append(rec)
    missing = [c["fact"] for c in checks if not c["present"]]
    extra["items_checked"], extra["missing"], extra["missing_numbers"] = checks, missing, [c["n"] for c in checks if not c["present"]]
    verdicts["completeness"] = None if failed or not checks else {
        "verdict": "FAIL" if len(missing) >= args.min_missing else "PASS",
        "reason": ("Missing: " + " | ".join(missing)) if missing else "Every reference item is covered."}
    return {"id": item["id"], "verdicts": verdicts if all(verdicts.values()) else None, "partial": verdicts, "extra": extra,
            "seconds": round(time.time() - t0, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000/v1")
    ap.add_argument("--model", default="gemma")
    ap.add_argument("--set", choices=["first", "confirmation"], default="first")
    ap.add_argument("--inputs")
    ap.add_argument("--reference")
    ap.add_argument("--out")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--min-missing", type=int, default=1)
    args = ap.parse_args()
    data = HERE.parent / "data" / ("first_set" if args.set == "first" else "confirmation_set")
    args.inputs = args.inputs or str(data / "judge_inputs.jsonl")
    args.reference = args.reference or str(data / "completeness_reference.jsonl")
    args.out = args.out or str(HERE / f"results_{'first_set' if args.set == 'first' else 'confirmation'}" / "judge_outputs.jsonl")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    missing = [n for n in NEEDED if not (HERE / "prompts" / f"v5_prompt_{n}.md").exists()]
    if missing:
        raise SystemExit("missing prompt files in prompts/: " + ", ".join(f"v5_prompt_{n}.md" for n in missing))
    prompts = {n: (HERE / "prompts" / f"v5_prompt_{n}.md").read_text() for n in NEEDED}
    items = [json.loads(l) for l in Path(args.inputs).read_text().splitlines() if l.strip()]
    refs = {r["id"]: r for r in map(json.loads, Path(args.reference).read_text().splitlines()) if r}
    with ThreadPoolExecutor(args.workers) as ex:
        rows = list(ex.map(lambda it: judge_one(args, prompts, it, refs[it["id"]]), items))
    Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"judged {len(rows)} items -> {args.out} ({sum(r['verdicts'] is None for r in rows)} with a missing verdict)")


if __name__ == "__main__":
    main()
