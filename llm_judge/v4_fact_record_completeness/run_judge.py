"""Judge v4: completeness is judged against the call's fact record (reference checklist), one item per call.

    python3 run_judge_v4.py [--url http://localhost:8000/v1] [--model gemma] [--workers 6]

Writes judge_outputs_v4.jsonl. Standard library only. Does not touch earlier versions.
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from judge_lib import CHECK, VERDICT, ask  # same folder

HERE = Path(__file__).resolve().parent
NEEDED = ["faithfulness", "calibration", "completeness_match", "completeness_recheck"]


def judge_one(args, prompts, item, ref):
    t0 = time.time()
    both = f"TRANSCRIPT\n{item['transcript']}\n\nSUMMARY\n{item['summary']}"
    verdicts, extra = {}, {}
    for rubric in ("faithfulness", "calibration"):
        out = ask(args, prompts[rubric], both, VERDICT, 1500)
        ok = out and out.get("verdict") in ("PASS", "FAIL")
        verdicts[rubric] = {"verdict": out["verdict"], "reason": out.get("reason", "")} if ok else None
        extra[rubric + "_analysis"] = out.get("analysis") if out else None
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
        "reason": ("Missing: " + " | ".join(missing)) if missing else "Every reference item is in the summary."}
    return {"id": item["id"], "verdicts": verdicts if all(verdicts.values()) else None, "partial": verdicts, "extra": extra,
            "seconds": round(time.time() - t0, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000/v1")
    ap.add_argument("--model", default="gemma")
    ap.add_argument("--inputs", default=str(HERE.parent / "data" / "first_set" / "judge_inputs.jsonl"))
    ap.add_argument("--reference", default=str(HERE.parent / "data" / "first_set" / "completeness_reference.jsonl"))
    ap.add_argument("--out", default=str(HERE / "results" / "judge_outputs.jsonl"))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--min-missing", type=int, default=1)
    args = ap.parse_args()
    missing = [n for n in NEEDED if not (HERE / f"v4_prompt_{n}.md").exists()]
    if missing:
        raise SystemExit("missing prompt files next to this script: " + ", ".join(f"v4_prompt_{n}.md" for n in missing))
    prompts = {n: (HERE / f"v4_prompt_{n}.md").read_text() for n in NEEDED}
    items = [json.loads(l) for l in Path(args.inputs).read_text().splitlines() if l.strip()]
    refs = {r["id"]: r for r in map(json.loads, Path(args.reference).read_text().splitlines()) if r}
    with ThreadPoolExecutor(args.workers) as ex:
        rows = list(ex.map(lambda it: judge_one(args, prompts, it, refs[it["id"]]), items))
    Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"judged {len(rows)} items -> {args.out} ({sum(r['verdicts'] is None for r in rows)} with a missing verdict)")


if __name__ == "__main__":
    main()
