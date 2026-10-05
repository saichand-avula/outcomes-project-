#!/usr/bin/env python3
"""Evaluation pipeline: generate -> validate (rules) -> judge (LLM) -> common matrix.

    python3 run_pipeline.py selftest                                   # local, no GPU: rules vs gold and vs damaged gold
    python3 run_pipeline.py generate  --system base --url http://localhost:8000/v1 --model gemma
    python3 run_pipeline.py validate  --system base
    python3 run_pipeline.py judge     --system base --url http://localhost:8000/v1 --model gemma
    python3 run_pipeline.py matrix    --systems base [finetuned]
    python3 run_pipeline.py all       --system base --url ... --model ...   # the four stages in a row
    python3 run_pipeline.py fake-system --system fake --damage number_changed_in_text:0.3   # outputs built from gold, for testing the plumbing
    python3 run_pipeline.py mutation-study [--judge-url ... --judge-model ...] [--per 10]

Files (outputs/<system>/): generations.jsonl, validation.jsonl, reference.jsonl, judge.jsonl; outputs/matrix_*.{md,xlsx,json}
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pl import generate as G  # noqa: E402
from pl import repair as REP  # noqa: E402
from pl import judge as J  # noqa: E402
from pl import medsafety as MS  # noqa: E402
from pl import matrix as MX  # noqa: E402
from pl import reference_metrics as RM  # noqa: E402
from pl.mutations import MUTATIONS, apply  # noqa: E402
from pl.study import deterministic_study, format_study, run_validate  # noqa: E402
from pl.transcript import parse  # noqa: E402
from pl.validators import validate  # noqa: E402

OUT = HERE / "outputs"


def read(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def write(p, rows):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def load_cases(a):
    cases = read(a.cases)
    if a.limit:
        cases = cases[: a.limit]
    return cases


def sysdir(name):
    return OUT / name


# ---------------------------------------------------------------- stages
def stage_generate(a):
    cases = load_cases(a)
    prompt = Path(a.prompt) if a.prompt else None
    print(f"generating {len(cases)} summaries with model '{a.model}' (workers={a.workers}) ...")
    rows = G.generate_all(cases, a.url, a.model, a.system, prompt, a.workers, a.max_tokens, not a.unconstrained, a.latency_n)
    write(sysdir(a.system) / "generations.jsonl", rows)
    ok = sum(1 for r in rows if isinstance(r.get("parsed"), dict))
    print(f"  {ok}/{len(rows)} parsed as JSON -> {sysdir(a.system) / 'generations.jsonl'}")


def stage_latency(a):
    """Time `--n` evenly spaced calls one at a time on an existing run and store latency_seq_s in its generations (the matrix then reports latency from them)."""
    cases = load_cases(a)
    path = sysdir(a.system) / "generations.jsonl"
    rows = read(path)
    if not a.prompt:
        raise SystemExit("--prompt is required: the timing must use the same system prompt as the run")
    system_prompt = Path(a.prompt).read_text()
    G.check_server(a.url, a.model)
    by_id = {r["id"]: r for r in rows}
    sample = [c for c in cases[:: max(1, len(cases) // a.n)][: a.n] if c["id"] in by_id]
    print(f"timing {len(sample)} calls one at a time with model '{a.model}' ...")
    G.generate_one(a.url, a.model, system_prompt, sample[0], a.max_tokens, not a.unconstrained)  # warm-up (not timed): the server compiles the JSON-schema grammar on first use
    for i, c in enumerate(sample, 1):
        r = G.generate_one(a.url, a.model, system_prompt, c, a.max_tokens, not a.unconstrained, stream=True)
        by_id[c["id"]]["latency_seq_s"] = r["latency_s"]
        by_id[c["id"]]["ttft_seq_s"] = r.get("ttft_s")
        print(f"  [{i}/{len(sample)}] {c['id']}: first token {r.get('ttft_s')}s, total {r['latency_s']}s, {r.get('completion_tokens')} tokens", flush=True)
    write(path, rows)
    lat = sorted(r["latency_seq_s"] for r in rows if r.get("latency_seq_s") is not None)
    ttf = sorted(r["ttft_seq_s"] for r in rows if r.get("ttft_seq_s") is not None)
    print(f"  total response time: p50 {lat[len(lat) // 2]:.1f}s, p95 {lat[min(len(lat) - 1, int(0.95 * len(lat)))]:.1f}s over {len(lat)} calls -> {path}")
    if ttf:
        print(f"  time to first token: p50 {ttf[len(ttf) // 2]:.2f}s, p95 {ttf[min(len(ttf) - 1, int(0.95 * len(ttf)))]:.2f}s")


def stage_validate(a):
    cases = load_cases(a)
    gens = {r["id"]: r for r in read(sysdir(a.system) / "generations.jsonl")}
    vrows, rrows, vrep, n_fixed = [], [], [], 0
    for c in cases:
        g = gens.get(c["id"], {})
        obj, err = g.get("parsed"), g.get("parse_error") or ("no generation" if not g else None)
        res = validate(obj, parse(c["transcript"]), err)
        vrows.append({"id": c["id"], **res})
        fixed, nf = REP.repair(obj, parse(c["transcript"]))
        n_fixed += nf
        vrep.append({"id": c["id"], "quotes_replaced": nf, **validate(fixed, parse(c["transcript"]), err)})
        if c.get("gold_target"):
            rrows.append({"id": c["id"], "counters": RM.score(obj, c["gold_target"])})
    write(sysdir(a.system) / "validation.jsonl", vrows)
    write(sysdir(a.system) / "validation_repaired.jsonl", vrep)
    stale = sysdir(a.system) / "reference.jsonl"
    if rrows:
        write(stale, rrows)
    elif stale.exists():
        stale.unlink()  # no gold for these cases: do not leave counters from an earlier run
    e = sum(1 for r in vrows if r["n_error"] == 0 and r["parse_ok"])
    print(f"  rules: {e}/{len(vrows)} calls with no ERROR -> {sysdir(a.system) / 'validation.jsonl'}" + (f"; reference counters for {len(rrows)} calls" if rrows else ""))
    print(f"  after automatic quote repair ({n_fixed} quotes replaced): {sum(1 for r in vrep if r['n_error'] == 0 and r['parse_ok'])}/{len(vrep)} calls with no ERROR")


def stage_net(a):
    """Automatic medication check (pl/medsafety.py) on an existing run -> a new run `<system>_net` with untyped drugs added and missing doses filled.
    The summary text is unchanged, so the judge verdicts are copied; rules and gold comparison are recomputed. Missing drugs (M3) are listed, not added."""
    import shutil
    cases = load_cases(a)
    gens = {r["id"]: r for r in read(sysdir(a.system) / "generations.jsonl")}
    rows, counts = [], {"M1": 0, "M2": 0, "M3": 0}
    for c in cases:
        r = dict(gens.get(c["id"], {"id": c["id"]}))
        if isinstance(r.get("parsed"), dict):
            r["parsed"], finds = MS.apply(r["parsed"], parse(c["transcript"]))
            r["safety_net"] = [f["rule"] + ":" + f["drug"] for f in finds]
            for f in finds:
                counts[f["rule"]] += 1
        rows.append(r)
    out = a.system + "_net"
    write(sysdir(out) / "generations.jsonl", rows)
    if (sysdir(a.system) / "judge.jsonl").exists():
        shutil.copy(sysdir(a.system) / "judge.jsonl", sysdir(out) / "judge.jsonl")
    print(f"  safety net: {counts['M1']} typed facts added (M1), {counts['M2']} doses filled (M2), {counts['M3']} drugs said but missing from the summary (M3) -> {sysdir(out)}")
    b = SimpleNamespace(**vars(a))
    b.system = out
    stage_validate(b)


def stage_judge(a):
    from concurrent.futures import ThreadPoolExecutor
    cases = load_cases(a)
    gens = {r["id"]: r for r in read(sysdir(a.system) / "generations.jsonl")}
    prompts = J.load_prompts()
    mode = a.mode or ("reference" if all(c.get("reference_checklist") is not None for c in cases) and any(c.get("reference_checklist") for c in cases) else "transcript")
    cache = OUT / "checklists_transcript_mode.jsonl"
    cached = {r["id"]: r["checklist"] for r in read(cache)} if cache.exists() else {}
    jargs = SimpleNamespace(url=a.url, model=a.model)
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        if mode == "transcript":
            todo = [c for c in cases if c["id"] not in cached]
            for c, cl in zip(todo, ex.map(lambda c: J.extract_checklist(jargs, prompts, c["transcript"]), todo)):
                cached[c["id"]] = cl
            if todo:
                write(cache, [{"id": k, "checklist": v} for k, v in cached.items()])
        checklist_of = (lambda c: c.get("reference_checklist")) if mode == "reference" else (lambda c: cached[c["id"]])
        rows = list(ex.map(lambda c: J.judge_one(jargs, prompts, c, (gens.get(c["id"]) or {}).get("parsed"), checklist_of(c), mode), cases))
    out = sysdir(a.system) / (a.out or "judge.jsonl")
    write(out, rows)
    print(f"  judge ({mode} checklist, {time.time() - t0:.0f}s): {sum(1 for r in rows if r.get('verdicts'))}/{len(rows)} with all three verdicts -> {out}")
    skipped = sum(1 for r in rows if not r.get("judged"))
    if skipped:
        print(f"  WARNING: {skipped} summaries could not be rendered and were not judged (invalid JSON or an unreadable date); they count as failures in the matrix")


def load_system(name, cases, judge_file="judge.jsonl"):
    d = sysdir(name)
    gens = read(d / "generations.jsonl") if (d / "generations.jsonl").exists() else []
    vals = read(d / "validation.jsonl") if (d / "validation.jsonl").exists() else []
    judges = read(d / judge_file) if (d / judge_file).exists() else None
    refs = read(d / "reference.jsonl") if (d / "reference.jsonl").exists() else None
    reps = read(d / "validation_repaired.jsonl") if (d / "validation_repaired.jsonl").exists() else None
    return MX.build(name, cases, gens, vals, judges, refs, reps)


def stage_matrix(a):
    cases = load_cases(a)
    results = [load_system(n, cases, a.judge_file) for n in a.systems]
    tag = "_vs_".join(a.systems)
    md = MX.compare(results, a.threshold)
    text = f"# Evaluation matrix: {' vs '.join(a.systems)}\n\nCases: {len(cases)}. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.\n\n{md}\n\n## Latency (seconds, calls timed one at a time)\n\n{MX.latency_md(results)}\n\n## Breakdown\n{MX.breakdown_md(results)}\n"
    OUT.mkdir(exist_ok=True)
    (OUT / f"matrix_{tag}.md").write_text(text)
    (OUT / f"matrix_{tag}.json").write_text(json.dumps(results, indent=1, default=str))
    MX.save_xlsx(results, OUT / f"matrix_{tag}.xlsx", a.threshold)
    print(text)
    print(f"\nwritten: {OUT / f'matrix_{tag}.md'} (+ .json, .xlsx)")


def stage_all(a):
    stage_generate(a)  # concurrency a.workers (1 by default) so the latency numbers are honest
    stage_validate(a)
    a.workers = a.judge_workers  # the judge stage may run in parallel: it is not being timed
    stage_judge(a)
    a.systems = [a.system]
    a.judge_file, a.threshold = "judge.jsonl", 95.0
    stage_matrix(a)


# ---------------------------------------------------------------- fake system (testing the plumbing, no GPU)
def stage_fake(a):
    """Model outputs built from gold. --damage name:fraction[,name:fraction] damages that fraction of calls with that mutation."""
    cases = load_cases(a)
    rng = random.Random(a.seed)
    plan = {}
    for part in filter(None, (a.damage or "").split(",")):
        n, f = part.split(":")
        plan[n] = float(f)
    rows = []
    for c in cases:
        obj, raw, err, damaged = c["gold_target"], None, None, None
        for name, frac in plan.items():
            if rng.random() < frac:
                res = apply(name, c["gold_target"], parse(c["transcript"]), c["id"])
                if res:
                    kind, payload, damaged = res
                    if kind == "raw":
                        raw, obj = payload, None
                        _, err = G.parse_json(payload)
                    else:
                        obj = payload
                    break
        rows.append({"id": c["id"], "system": a.system, "raw_text": raw if raw is not None else json.dumps(obj), "parsed": obj, "parse_error": err, "constrained": False,
                     "latency_s": round(rng.uniform(4, 14), 2), "finish_reason": "stop", "damage": damaged})
    write(sysdir(a.system) / "generations.jsonl", rows)
    print(f"fake system '{a.system}': {len(rows)} outputs, {sum(1 for r in rows if r['damage'])} damaged ({a.damage or 'none'})")


# ---------------------------------------------------------------- mutation study (rules, and judge when a server is given)
def stage_study(a):
    cases = [c for c in read(a.cases) if c.get("gold_target")]
    print(f"deterministic study on {len(cases)} gold summaries ({a.per} per defect) ...")
    res = deterministic_study(cases, per_mutation=a.per if not a.judge_url else max(a.per, 30))
    judge_res = {}
    if a.judge_url:
        prompts = J.load_prompts()
        jargs = SimpleNamespace(url=a.judge_url, model=a.judge_model)
        by_id = {c["id"]: c for c in cases}
        rng = random.Random(3)
        for name, (fn, expect, level, rubric) in MUTATIONS.items():
            if rubric is None:
                continue
            order = list(cases)
            rng.shuffle(order)
            done = caught = 0
            for c in order:
                r = apply(name, c["gold_target"], parse(c["transcript"]), c["id"])
                if r is None or r[0] != "obj":
                    continue
                jr = J.judge_one(jargs, prompts, c, r[1], c.get("reference_checklist"), "reference")
                if not jr.get("verdicts"):
                    continue
                done += 1
                caught += jr["verdicts"][rubric]["verdict"] == "FAIL"
                if done >= a.per:
                    break
            judge_res[name] = {"n": done, "caught": caught, "rubric": rubric}
            print(f"  judge {name}: {caught}/{done}")
        # false alarms of the judge on undamaged gold
        clean = [c for c in cases if not c["gold_target"]["not_applicable"]["is_na"]][: a.per * 2]
        fa = {"faithfulness": 0, "completeness": 0, "calibration": 0, "n": 0}
        for c in clean:
            jr = J.judge_one(jargs, prompts, c, c["gold_target"], c.get("reference_checklist"), "reference")
            if jr.get("verdicts"):
                fa["n"] += 1
                for k in ("faithfulness", "completeness", "calibration"):
                    fa[k] += jr["verdicts"][k]["verdict"] == "FAIL"
        judge_res["_clean_false_alarms"] = fa
    lines = ["| Defect | Rules: caught as ERROR | Rules: caught (WARN or ERROR) | Judge rubric | Judge: caught | Either |", "|---|---|---|---|---|---|"]
    for name, r in res.items():
        if name.startswith("_") or not r["n"]:
            continue
        jr = judge_res.get(name)
        jtxt = f"{jr['caught']}/{jr['n']} ({jr['caught'] / jr['n']:.0%})" if jr and jr["n"] else ("not judged" if not a.judge_url else "n/a")
        either = ""
        if jr and jr["n"]:
            either = f"≥{max(r['caught_any'] / r['n'], jr['caught'] / jr['n']):.0%}"
        lines.append(f"| {name} | {r['caught_error']}/{r['n']} ({r['caught_error'] / r['n']:.0%}) | {r['caught_any']}/{r['n']} ({r['caught_any'] / r['n']:.0%}) | {r['judge_rubric'] or '-'} | {jtxt} | {either} |")
    md = "\n".join(lines)
    OUT.mkdir(exist_ok=True)
    (OUT / "mutation_study.md").write_text(f"# Defect detection study\n\nBaseline: {res['_baseline']}\n\n{md}\n" + (f"\nJudge false alarms on undamaged gold: {judge_res.get('_clean_false_alarms')}\n" if judge_res else ""))
    (OUT / "mutation_study.json").write_text(json.dumps({"rules": res, "judge": judge_res}, indent=1))
    print(md)
    print(f"\nbaseline (undamaged gold): {res['_baseline']}")


# ---------------------------------------------------------------- selftest
def stage_selftest(a):
    cases = [c for c in read(a.cases) if c.get("gold_target")]
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + msg)
        ok &= bool(cond)

    errs = [c["id"] for c in cases if validate(c["gold_target"], parse(c["transcript"]))["n_error"]]
    check(not errs, f"undamaged gold: {len(cases) - len(errs)}/{len(cases)} calls pass with no ERROR {errs[:3] if errs else ''}")
    tot = {}
    for c in cases:
        for k, (x, y) in RM.score(c["gold_target"], c["gold_target"]).items():
            t = tot.setdefault(k, [0, 0])
            t[0] += x
            t[1] += y
    m, d = RM.cfa(tot)
    check(m == d, f"gold scored against itself: CFA {m}/{d}")
    from pl.schema import order_violations
    viol = {}
    for c in cases:
        for k, (x, y) in order_violations(c["gold_target"]).items():
            v = viol.setdefault(k, [0, 0])
            v[0] += x
            v[1] += y
    other = {k: v for k, v in viol.items() if k != "fact" and v[0]}
    check(not other and viol["fact"][0] <= 0.01 * viol["fact"][1],
          f"schema key order matches the gold order (constrained decoding must not fight the trained order): facts {viol['fact'][0]}/{viol['fact'][1]} differ, all other objects 0 {other or ''}")
    res = deterministic_study(cases, per_mutation=30)
    must = {"truncated_json": 1.0, "missing_section": 1.0, "turn_out_of_range": 1.0, "quote_from_other_turn": 1.0, "quote_paraphrased": 1.0, "drug_swapped_in_fact": 0.95,
            "drug_swapped_in_text": 0.95, "patient_name_changed": 0.95, "dob_year_changed": 0.95, "phone_digit_changed": 0.95, "status_flipped_to_done": 0.95,
            "negative_flipped": 0.9, "number_changed_in_text": 0.8, "dose_changed_in_fact": 0.75, "bullet_text_emptied": 1.0}
    for name, lo in must.items():
        r = res[name]
        rate = r["caught_error"] / r["n"] if r["n"] else 0
        check(r["n"] > 0 and rate >= lo, f"{name}: caught as ERROR {r['caught_error']}/{r['n']} (need >= {lo:.0%})")
    for name in ("invented_unlisted_finding", "names_swapped", "bullet_removed", "dose_swapped_within_call"):
        r = res[name]
        check(r["caught_error"] / max(1, r["n"]) < 0.3, f"{name}: rules correctly cannot see it ({r['caught_error']}/{r['n']}); the judge must")
    # automatic medication check: dose extraction, adding an untyped drug, flagging an absent one, leaving a good summary alone
    check(MS.extract_dose("Morphine sulfate oral solution 20 mg per mL, 0.25 mL under the tongue every two hours", "morphine") == ("0.25", "mL"), "net: a concentration is not taken for a dose")
    check(MS.extract_dose("Ibuprofen 100 mg per 5 mL was available and the box said 7.5 mL", "ibuprofen") == ("7.5", "mL"), "net: 100 mg per 5 mL is skipped, the dose 7.5 mL is found")
    check(MS.extract_dose("Albuterol was needed twice this week", "albuterol") is None, "net: no dose invented when the text has none")
    turns = [{"id": 1, "speaker": "Caller", "text": "I take warfarin five milligrams every night."}, {"id": 2, "speaker": "Caller", "text": "And lisinopril, ten milligrams."}]
    summ = {"assessment": [{"text": "Warfarin 5 mg was taken every night.", "facts": []}], "response": [], "education": []}
    new, fs = MS.apply(summ, turns)
    check([f["rule"] for f in fs].count("M1") == 1 and new["assessment"][0]["facts"][0].get("dose") == "5", "net: a drug in the text without a typed fact gets one, with its dose")
    check(any(f["rule"] == "M3" and f["drug"] == "lisinopril" for f in fs), "net: a drug the caller said and the summary never mentions is flagged")
    check(summ["assessment"][0]["facts"] == [], "net: the input summary is never modified")
    n_changed = sum(1 for c in cases if MS.apply(c["gold_target"], parse(c["transcript"]))[0] != c["gold_target"])
    check(n_changed <= 0.05 * len(cases), f"net: it leaves almost every gold summary unchanged ({n_changed}/{len(cases)} get a fact added)")
    print("\nselftest", "OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, system=True, server=False):
        sp.add_argument("--cases", default=str(HERE / "data" / "val_cases.jsonl"))
        sp.add_argument("--limit", type=int, default=0)
        if system:
            sp.add_argument("--system", required=True)
        if server:
            sp.add_argument("--url", default="http://localhost:8000/v1")
            sp.add_argument("--model", default="gemma")

    g = sub.add_parser("generate"); common(g, server=True)
    g.add_argument("--prompt"); g.add_argument("--workers", type=int, default=16, help="requests in flight (1 = every latency is a concurrency-1 latency)")
    g.add_argument("--latency-n", type=int, default=20, help="with workers>1: calls re-run one at a time to measure latency")
    g.add_argument("--max-tokens", type=int, default=6000); g.add_argument("--unconstrained", action="store_true")
    g.set_defaults(fn=stage_generate)
    lt = sub.add_parser("latency"); common(lt, server=True); lt.add_argument("--prompt"); lt.add_argument("--n", type=int, default=20)
    lt.add_argument("--max-tokens", type=int, default=6000); lt.add_argument("--unconstrained", action="store_true"); lt.set_defaults(fn=stage_latency)
    v = sub.add_parser("validate"); common(v); v.set_defaults(fn=stage_validate)
    j = sub.add_parser("judge"); common(j, server=True); j.add_argument("--mode", choices=["reference", "transcript"]); j.add_argument("--out"); j.add_argument("--workers", type=int, default=4); j.set_defaults(fn=stage_judge)
    nt = sub.add_parser("net"); common(nt); nt.set_defaults(fn=stage_net)
    m = sub.add_parser("matrix"); common(m, system=False); m.add_argument("--systems", nargs="+", required=True); m.add_argument("--threshold", type=float, default=95.0)
    m.add_argument("--judge-file", default="judge.jsonl"); m.set_defaults(fn=stage_matrix)
    al = sub.add_parser("all"); common(al, server=True); al.add_argument("--prompt"); al.add_argument("--workers", type=int, default=16); al.add_argument("--latency-n", type=int, default=20); al.add_argument("--max-tokens", type=int, default=6000)
    al.add_argument("--unconstrained", action="store_true"); al.add_argument("--mode", choices=["reference", "transcript"]); al.add_argument("--out"); al.add_argument("--judge-workers", type=int, default=4); al.set_defaults(fn=stage_all)
    f = sub.add_parser("fake-system"); common(f); f.add_argument("--damage", default=""); f.add_argument("--seed", type=int, default=1); f.set_defaults(fn=stage_fake)
    s = sub.add_parser("mutation-study"); common(s, system=False); s.add_argument("--per", type=int, default=30); s.add_argument("--judge-url"); s.add_argument("--judge-model", default="gemma"); s.set_defaults(fn=stage_study)
    t = sub.add_parser("selftest"); common(t, system=False); t.set_defaults(fn=stage_selftest)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
