"""Defect-detection study (deterministic part): damage correct summaries and check whether the validators notice.

For each mutation, apply it to up to N gold summaries, run the validators, and count a defect as
  caught at ERROR level  - a NEW ERROR finding appeared that was not in the unmodified summary
  caught at WARN level   - a new WARN or ERROR finding appeared
  caught by the expected rule - a new finding from one of the rules listed for this mutation
"""
from __future__ import annotations

import json
import random
from collections import defaultdict

from .mutations import INVISIBLE, MUTATIONS, apply
from .transcript import parse
from .validators import validate

SEV = {"INFO": 0, "WARN": 1, "ERROR": 2}


def _key(f):
    return (f["rule"], f["path"], f["severity"])


def run_validate(kind, payload, turns):
    if kind == "raw":
        try:
            obj, err = json.loads(payload), None
        except json.JSONDecodeError as e:
            obj, err = None, str(e)
        return validate(obj, turns, err)
    return validate(payload, turns)


def deterministic_study(cases: list[dict], per_mutation: int = 30, seed: int = 7, only: list[str] | None = None) -> dict:
    """cases: [{id, transcript, gold_target}]. Returns {mutation: {...counts...}, '_baseline': {...}}"""
    rng = random.Random(seed)
    cases = [c for c in cases if c.get("gold_target")]
    prepared = []
    base_err = base_warn = 0
    for c in cases:
        turns = parse(c["transcript"])
        base = validate(c["gold_target"], turns)
        base_err += base["n_error"] > 0
        base_warn += base["n_warn"] > 0
        prepared.append((c, turns, {_key(f) for f in base["findings"]}))
    out = {"_baseline": {"calls": len(prepared), "calls_with_error": base_err, "calls_with_warning": base_warn}}
    for name, (fn, expect, level, rubric) in MUTATIONS.items():
        if only and name not in only:
            continue
        rows = []
        order = list(prepared)
        rng.shuffle(order)
        for c, turns, base_keys in order:
            res = apply(name, c["gold_target"], turns, c["id"])
            if res is None:
                continue
            kind, payload, desc = res
            r = run_validate(kind, payload, turns)
            new = [f for f in r["findings"] if _key(f) not in base_keys and f["severity"] in ("WARN", "ERROR")]
            rows.append({"id": c["id"], "description": desc, "new_error": any(f["severity"] == "ERROR" for f in new), "new_any": bool(new),
                         "expected_rule": any(f["rule"] in expect for f in new), "rules": sorted({f["rule"] for f in new}), "messages": [f["message"][:100] for f in new[:2]]})
            if len(rows) >= per_mutation:
                break
        n = len(rows)
        out[name] = {"n": n, "caught_error": sum(r["new_error"] for r in rows), "caught_any": sum(r["new_any"] for r in rows),
                     "caught_by_expected_rule": sum(r["expected_rule"] for r in rows), "expected_rules": expect, "min_level": level, "judge_rubric": rubric,
                     "invisible_by_design": name in INVISIBLE, "examples": rows[:3], "missed": [r for r in rows if not r["new_any"]][:3]}
    return out


def format_study(res: dict) -> str:
    lines = ["| Defect | n | Caught as ERROR | Caught (WARN or ERROR) | By the expected rule | Expected rule |", "|---|---|---|---|---|---|"]
    for name, r in res.items():
        if name.startswith("_") or not r["n"]:
            continue
        rule = ", ".join(r["expected_rules"]) or "none (invisible to rules)"
        lines.append(f"| {name} | {r['n']} | {r['caught_error']}/{r['n']} ({r['caught_error'] / r['n']:.0%}) | {r['caught_any']}/{r['n']} ({r['caught_any'] / r['n']:.0%}) | "
                     f"{r['caught_by_expected_rule']}/{r['n']} | {rule} |")
    return "\n".join(lines)
