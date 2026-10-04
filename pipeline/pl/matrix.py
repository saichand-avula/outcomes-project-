"""The common matrix: every metric normalized to a rate (0-100%, 100 = best) with its source, counts and evidence level.

Source tags:  D deterministic rules | J LLM judge | R reference (gold summary) | DJ rules AND judge | O operational
Evidence:     validated   - the detector was measured on damaged summaries (llm_judge/ and the mutation study) and behaves as stated
              indicator   - measured, but unreliable for part of its job (see notes)
              unvalidated - not measured
Invalid outputs count as failures in call-level rows. Slot-level rows (quotes, numbers, drugs ...) are computed over the outputs that parsed.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from .reference_metrics import cfa as cfa_pair


def wilson_lower(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - a) / d)


def _sum_counters(rows, key):
    ok = tot = 0
    for r in rows:
        c = (r.get("counters") or {}).get(key)
        if c:
            ok += c[0]
            tot += c[1]
    return ok, tot


def _pct(ok, tot):
    return None if not tot else 100.0 * ok / tot


def build(system: str, cases: list[dict], gens: list[dict], vals: list[dict], judges: list[dict] | None, refs: list[dict] | None, vals_rep: list[dict] | None = None) -> dict:
    """-> {"system", "n", "metrics": [row...], "breakdown": {...}}"""
    by = lambda rows: {r["id"]: r for r in rows or []}  # noqa: E731
    g, v, j, rf, vr = by(gens), by(vals), by(judges), by(refs), by(vals_rep)
    cases = [c for c in cases if c["id"] in g]  # only calls this system was actually run on
    N = len(cases)
    M = []

    def row(mid, group, name, source, ok, tot, evidence, note="", inverse=False):
        if tot == 0:
            M.append({"id": mid, "group": group, "name": name, "source": source, "num": None, "den": 0, "value": None, "ci_low": None, "evidence": evidence, "note": note})
            return
        if inverse:
            ok = tot - ok
        M.append({"id": mid, "group": group, "name": name, "source": source, "num": ok, "den": tot, "value": 100.0 * ok / tot,
                  "ci_low": 100.0 * wilson_lower(ok, tot), "evidence": evidence, "note": note})

    valid = [v[c["id"]] for c in cases if c["id"] in v and v[c["id"]].get("parse_ok")]
    nv = len(valid)
    # ---- A. output validity
    parsed = sum(1 for c in cases if c["id"] in g and isinstance(g[c["id"]].get("parsed"), dict))
    row("A1", "A. Output validity", "Output is valid JSON", "D", parsed, N, "validated", "an unparseable output counts as a failure everywhere below")
    sv = sum(1 for r in valid if (r["counters"].get("schema_valid") or [0, 0])[0] == 1)
    row("A2", "A. Output validity", "Output matches the schema", "D", sv, N, "validated")
    for mid, key, name, note in [("A3", "turns_valid", "Cited turns exist", ""), ("A4", "quote_valid", "Quotes are in the cited turns (verbatim or repairable)", f"over {nv} parsed outputs"),
                                 ("A5", "quote_exact", "Quotes are exactly verbatim", "stricter than A4; informational"), ("A6", "speaker_ok", "Quote speaker matches the transcript label", "a mismatch can also be a diarization error the model corrected")]:
        ok, tot = _sum_counters(valid, key)
        row(mid, "A. Output validity", name, "D", ok, tot, "validated", note)
    # ---- B. grounding
    for mid, key, name, note in [("B1", "numbers_in_call", "Numbers in the summary were spoken in the call", "catches invented or mistyped numbers; cannot see a number swapped with another spoken number"),
                                 ("B2", "numbers_in_window", "Numbers are in the cited turns (+/-2)", "locality, informational"),
                                 ("B3", "drugs_in_call", "Drug names appear in the call", "catches swapped and invented drugs"),
                                 ("B4", "clinical_terms_supported", "Clinical terms (fever, fall, seizure ...) appear in the call", "only covers terms in the lexicon"),
                                 ("B5", "identity_supported", "Identity values (name, DOB, phone, relationship) were spoken", "cannot see swapped patient/caller names")]:
        ok, tot = _sum_counters(valid, key)
        row(mid, "B. Grounding in the call", name, "D", ok, tot, "validated", note)
    # ---- C. wording vs meaning
    for mid, key, name, note in [("C1", "status_consistent", "Planned vs completed matches the nurse's words", ""), ("C2", "negation_consistent", "Negative findings are not stated as present", ""),
                                 ("C3", "hedge_kept", "Caller hedges are kept", "warning-level rule")]:
        ok, tot = _sum_counters(valid, key)
        row(mid, "C. Wording vs meaning", name, "D", ok, tot, "validated" if mid != "C3" else "indicator", note)
    # ---- D. safety gates
    ok, tot = _sum_counters(valid, "na_gate_ok")
    row("D1", "D. Safety gates", "Not-Applicable decision agrees with the clinical-content gate", "D", ok, tot, "validated")
    ok, tot = _sum_counters(valid, "rule_flags_covered_strong")
    row("D2", "D. Safety gates", "Suicidal / escalation flags the rules find are also in the output", "D", ok, tot, "validated", "rules are precise here (about 0.9 on training data)")
    ok, tot = _sum_counters(valid, "rule_flags_covered_loose")
    row("D2b", "D. Safety gates", "Other risk flags the rules suggest are also in the output", "D", ok, tot, "indicator", "rules are loose here (precision about 0.4-0.5): a low score is not necessarily wrong")
    ok, tot = _sum_counters(valid, "drug_mentions_covered")
    row("D3", "D. Safety gates", "Drugs mentioned in the call appear in the summary", "D", ok, tot, "indicator", "completeness proxy; chart-reading distractors count against it")
    # ---- E. call level, deterministic
    clean = sum(1 for c in cases if c["id"] in v and v[c["id"]].get("parse_ok") and v[c["id"]]["n_error"] == 0)
    review_free = sum(1 for c in cases if c["id"] in v and v[c["id"]].get("parse_ok") and v[c["id"]]["n_error"] == 0 and v[c["id"]]["n_warn"] == 0)
    row("E1", "E. Whole call (rules)", "Calls with no rule ERROR", "D", clean, N, "validated", "headline for the rules")
    row("E2", "E. Whole call (rules)", "Calls with no rule ERROR and no WARN (no nurse review needed)", "D", review_free, N, "indicator", "WARN rules are deliberately sensitive")
    if vals_rep is not None:
        clean_r = sum(1 for c in cases if c["id"] in vr and vr[c["id"]].get("parse_ok") and vr[c["id"]]["n_error"] == 0)
        row("E1r", "E. Whole call (rules)", "Calls with no rule ERROR after automatic quote repair", "D", clean_r, N, "indicator",
            "each quote that is a near-match is replaced by the exact span (pl/repair.py); quotes with no near-match stay errors")
    # ---- F. judge
    jd = [j[c["id"]] for c in cases if c["id"] in j and j[c["id"]].get("judged") and j[c["id"]].get("verdicts")]
    if judges is not None:
        jc = [c for c in cases if c["id"] in j]  # calls the judge was run on
        Nj = len(jc)
        cov = "" if Nj == N else f"; judge ran on {Nj} of {N} calls"

        def passes(rub):
            return sum(1 for c in jc if j[c["id"]].get("verdicts") and j[c["id"]]["verdicts"][rub]["verdict"] == "PASS")
        row("F1", "F. Meaning (LLM judge)", "Faithful: nothing wrong or invented", "J", passes("faithfulness"), Nj, "validated", "kappa 1.00 on 40 fresh items (10 faithfulness edits, all caught, 0/30 false alarms: small sample); an output that cannot be rendered counts as FAIL" + cov)
        items = [i for r in jd for i in (r["extra"].get("items") or [])]
        row("F2", "F. Meaning (LLM judge)", "Complete: checklist items covered (item level)", "J", sum(1 for i in items if i["present"]), len(items), "indicator",
            "reference mode: validated for missing nurse actions and instructions, unreliable for missing findings" if any(r.get("completeness_mode") == "reference" for r in jd) else "transcript mode: NOT validated")
        row("F3", "F. Meaning (LLM judge)", "Complete: calls where every checklist item is covered", "J", passes("completeness"), Nj, "indicator", cov.lstrip("; "))
        row("F4", "F. Meaning (LLM judge)", "Calibrated: hedges, planned vs done, speaker (indicator)", "J", passes("calibration"), Nj, "indicator", "reliable for planned vs completed only" + cov)
        # ---- G. combined
        safe = sum(1 for c in jc if c["id"] in v and v[c["id"]].get("parse_ok") and v[c["id"]]["n_error"] == 0 and j[c["id"]].get("verdicts")
                   and j[c["id"]]["verdicts"]["faithfulness"]["verdict"] == "PASS")
        row("G1", "G. Pipeline (rules + judge)", "Safe-pass: no rule ERROR and judged faithful", "DJ", safe, Nj, "validated", "headline for unseen data (no gold needed)" + cov)
        full = sum(1 for c in jc if c["id"] in v and v[c["id"]].get("parse_ok") and v[c["id"]]["n_error"] == 0 and j[c["id"]].get("verdicts")
                   and all(j[c["id"]]["verdicts"][r]["verdict"] == "PASS" for r in ("faithfulness", "completeness", "calibration")))
        row("G2", "G. Pipeline (rules + judge)", "Full-pass: safe-pass and complete and calibrated", "DJ", full, Nj, "indicator", "strict" + cov)
        if vals_rep is not None:
            safe_r = sum(1 for c in jc if c["id"] in vr and vr[c["id"]].get("parse_ok") and vr[c["id"]]["n_error"] == 0 and j[c["id"]].get("verdicts")
                         and j[c["id"]]["verdicts"]["faithfulness"]["verdict"] == "PASS")
            row("G1r", "G. Pipeline (rules + judge)", "Safe-pass after automatic quote repair", "DJ", safe_r, Nj, "indicator", "same as G1 with repaired quotes" + cov)
    # ---- H. reference (gold)
    if refs:
        agg = defaultdict(lambda: [0, 0])
        for c in cases:
            r = rf.get(c["id"])
            if r:
                for k, (a, b) in r["counters"].items():
                    agg[k][0] += a
                    agg[k][1] += b
        for mid, key, name, inv in [("H1", "identity_value", "Identity values correct (5 fields)", False), ("H2", "identity_value_and_certainty", "Identity values AND certainty correct", False),
                                    ("H3", "medication_name", "Medications found (name)", False), ("H4", "medication_name_dose_unit", "Medications correct (name + dose + unit)", False),
                                    ("H5", "medication_certainty", "Medication certainty (stated/unclear) correct", False), ("H6", "symptom_recall", "Symptoms found", False),
                                    ("H7", "pertinent_negative_recall", "Pertinent negatives found", False), ("H8", "vital_recall", "Vital signs found", False),
                                    ("H9", "action_type_recall", "Nurse actions found (type)", False), ("H10", "action_type_and_status", "Nurse actions correct (type + planned/completed)", False),
                                    ("H11", "education_type_recall", "Education items found (type)", False), ("H12", "flag_recall", "Gold risk flags found", False),
                                    ("H13", "flag_precision", "Output risk flags that are in gold", False), ("H14", "na_label", "Not-Applicable decision correct", False),
                                    ("H15", "assessment_bullet_recall", "Assessment bullets covered (anchored on cited turns)", False), ("H16", "response_bullet_recall", "Response bullets covered", False),
                                    ("H17", "education_bullet_recall", "Education bullets covered", False), ("H18", "medication_hallucinated", "Output medications that are in gold (no hallucinated drug)", True)]:
            a, b = agg.get(key, [0, 0])
            row(mid, "H. Against gold (validation set)", name, "R", a, b, "validated", "deterministic comparison with the validated gold summary", inverse=inv)
        m, d = cfa_pair(agg)
        row("H19", "H. Against gold (validation set)", "Critical-Fact Accuracy (headline in the architecture)", "R", m, d, "validated", "matched critical slots / (gold critical slots + unsupported model slots)")
        a, b = agg.get("cfa_crit", [0, 0])
        row("H19r", "H. Against gold (validation set)", "Gold critical facts found (no penalty for extra facts)", "R", a, b, "indicator",
            "diagnostic next to H19: the extra facts H19 counts against the model are often true details the gold did not record")
    # ---- O. operational
    seq = [r["latency_seq_s"] for r in gens if r.get("latency_seq_s") is not None]
    if seq:  # generated with several requests in flight: only the calls re-run one at a time give a real latency
        lat, lat_note = sorted(seq), f"concurrency 1, sample of {len(seq)} calls"
    elif all((r.get("concurrency") or 1) == 1 for r in gens):
        lat, lat_note = sorted(r["latency_s"] for r in gens if r.get("latency_s") is not None and (r.get("parsed") is not None or r.get("raw_text"))), "concurrency 1, all calls"
    else:
        lat, lat_note = [], ""  # parallel run without a latency sample: do not report a misleading number
    ops = {}
    if lat:
        pct = lambda p: lat[min(len(lat) - 1, int(math.ceil(p * len(lat))) - 1)]  # noqa: E731
        ops = {"p50": pct(0.5), "p95": pct(0.95), "mean": sum(lat) / len(lat), "max": lat[-1], "n": len(lat)}
        tt = sorted(r["ttft_seq_s"] for r in gens if r.get("ttft_seq_s") is not None)  # only measured one call at a time with streaming (`latency` stage)
        if tt:
            tpct = lambda p: tt[min(len(tt) - 1, int(math.ceil(p * len(tt))) - 1)]  # noqa: E731
            ops.update({"ttft_p50": tpct(0.5), "ttft_p95": tpct(0.95), "ttft_mean": sum(tt) / len(tt), "ttft_max": tt[-1], "ttft_n": len(tt)})
        row("O1", "O. Operational", "Latency p95 under 15 s (calls under 15 s)", "O", sum(1 for x in lat if x < 15), len(lat), "validated", f"p50 {ops['p50']:.1f}s, p95 {ops['p95']:.1f}s; {lat_note}")
    if gens:
        trunc = sum(1 for r in gens if r.get("finish_reason") == "length")
        row("O2", "O. Operational", "Outputs not cut off by the token limit", "O", len(gens) - trunc, len(gens), "validated")
    # ---- breakdown of the three call-level headlines
    breakdown = {}
    for dim in ("category", "length", "noise"):
        groups = defaultdict(list)
        for c in cases:
            groups[str((c.get("meta") or {}).get(dim))].append(c)
        if len(groups) < 2:
            continue
        rows_ = {}
        for gname, cs in sorted(groups.items()):
            n = len(cs)
            e1 = sum(1 for c in cs if c["id"] in v and v[c["id"]].get("parse_ok") and v[c["id"]]["n_error"] == 0)
            d = {"n": n, "E1": 100.0 * e1 / n}
            if judges is not None:
                cj = [c for c in cs if c["id"] in j]
                d["G1"] = None if not cj else 100.0 * sum(1 for c in cj if c["id"] in v and v[c["id"]].get("parse_ok") and v[c["id"]]["n_error"] == 0 and j[c["id"]].get("verdicts")
                                                          and j[c["id"]]["verdicts"]["faithfulness"]["verdict"] == "PASS") / len(cj)
            if refs:
                a = defaultdict(lambda: [0, 0])
                for c in cs:
                    r = rf.get(c["id"])
                    if r:
                        for k, (x, y) in r["counters"].items():
                            a[k][0] += x
                            a[k][1] += y
                m, dd = cfa_pair(a)
                d["H19"] = 100.0 * m / dd if dd else None
            rows_[gname] = d
        breakdown[dim] = rows_
    return {"system": system, "n": N, "valid_outputs": nv, "metrics": M, "ops": ops, "breakdown": breakdown}


def _fmt(r):
    if r is None or r["value"] is None:
        return "n/a"
    return f"{r['value']:.1f}% ({r['num']}/{r['den']})"


def compare(results: list[dict], threshold: float = 95.0) -> str:
    """Markdown matrix. One value column per system; Δ and the >=95% marks only when two systems are given."""
    names = [r["system"] for r in results]
    ids = []
    for r in results:
        for m in r["metrics"]:
            if m["id"] not in ids:
                ids.append(m["id"])
    idx = [{m["id"]: m for m in r["metrics"]} for r in results]
    first = {m["id"]: m for r in results for m in r["metrics"]}
    head = ["ID", "Metric", "Src", "Evidence"] + [f"{n} (rate, n/d)" for n in names] + (["Δ pts"] if len(results) == 2 else []) + [f"≥{threshold:.0f}% [{n}] (lower 95% bound)" for n in names]
    L = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    group = None
    for mid in ids:
        m0 = first[mid]
        if m0["group"] != group:
            group = m0["group"]
            L.append(f"| **{group}** |" + " |" * (len(head) - 1))
        cells = [mid, m0["name"], m0["source"], m0["evidence"]] + [_fmt(i.get(mid)) for i in idx]
        if len(results) == 2:
            a, b = idx[0].get(mid), idx[1].get(mid)
            cells.append(f"{b['value'] - a['value']:+.1f}" if a and b and a["value"] is not None and b["value"] is not None else "")
        for i in idx:
            m = i.get(mid)
            if m and m["value"] is not None:
                cells.append(("✅ " if m["value"] >= threshold else "— ") + f"({m['ci_low']:.0f}%)" + ("" if m["value"] < threshold else (" lower bound ≥95" if m["ci_low"] >= threshold else "")))
            else:
                cells.append("")
        L.append("| " + " | ".join(cells) + " |")
    L.append("")
    for r, i in zip(results, idx):
        got = [m for m in r["metrics"] if m["value"] is not None and m["value"] >= threshold]
        L.append(f"**{r['system']}: {len(got)} of {len([m for m in r['metrics'] if m['value'] is not None])} metrics reach ≥{threshold:.0f}%:** " + (", ".join(f"{m['id']} {m['name']} ({m['value']:.1f}%)" for m in got) or "none"))
    return "\n".join(L)


def latency_md(results: list[dict]) -> str:
    """The two timings the assignment asks for, side by side: time to first token and total response time (seconds, calls timed one at a time)."""
    rows = [("Time to first token, p50", "ttft_p50"), ("Time to first token, p95", "ttft_p95"), ("Total response time, p50", "p50"), ("Total response time, p95 (target < 15 s)", "p95"),
            ("Total response time, slowest", "max")]
    L = ["| seconds | " + " | ".join(r["system"] for r in results) + " |", "|---|" + "---|" * len(results)]
    for label, key in rows:
        L.append(f"| {label} | " + " | ".join("not measured" if r["ops"].get(key) is None else f"{r['ops'][key]:.2f}" for r in results) + " |")
    L.append("| calls timed | " + " | ".join(str(r["ops"].get("ttft_n") or r["ops"].get("n") or "") for r in results) + " |")
    return "\n".join(L)


def breakdown_md(results: list[dict]) -> str:
    L = []
    for r in results:
        for dim, groups in r["breakdown"].items():
            cols = sorted({k for g in groups.values() for k in g if k != "n"})
            L += [f"\n**{r['system']} by {dim}**\n", "| group | n | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 2)]
            for gname, d in groups.items():
                L.append(f"| {gname} | {d['n']} | " + " | ".join("" if d.get(c) is None else f"{d[c]:.1f}%" for c in cols) + " |")
    return "\n".join(L)


def save_xlsx(results: list[dict], path: Path, threshold: float = 95.0):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        return False
    wb = Workbook()
    ws = wb.active
    ws.title = "Matrix"
    names = [r["system"] for r in results]
    ws.append(["ID", "Group", "Metric", "Source", "Evidence"] + sum([[f"{n} %", f"{n} num", f"{n} den", f"{n} lower95", f"{n} ≥{threshold:.0f}%"] for n in names], []) + (["Δ pts"] if len(results) == 2 else []))
    idx = [{m["id"]: m for m in r["metrics"]} for r in results]
    ids = []
    for r in results:
        for m in r["metrics"]:
            if m["id"] not in ids:
                ids.append(m["id"])
    first = {m["id"]: m for r in results for m in r["metrics"]}
    green = PatternFill("solid", fgColor="C6EFCE")
    for mid in ids:
        m0 = first[mid]
        rowv = [mid, m0["group"], m0["name"], m0["source"], m0["evidence"]]
        for i in idx:
            m = i.get(mid)
            rowv += [None if not m or m["value"] is None else round(m["value"], 2), m and m["num"], m and m["den"], None if not m or m["ci_low"] is None else round(m["ci_low"], 1),
                     "yes" if m and m["value"] is not None and m["value"] >= threshold else ""]
        if len(results) == 2:
            a, b = idx[0].get(mid), idx[1].get(mid)
            rowv.append(round(b["value"] - a["value"], 2) if a and b and a["value"] is not None and b["value"] is not None else None)
        ws.append(rowv)
        for k in range(len(names)):
            if rowv[5 + 5 * k + 4] == "yes":
                ws.cell(ws.max_row, 6 + 5 * k).fill = green
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "F2"
    for col, w in zip("ABCDE", (6, 34, 62, 7, 12)):
        ws.column_dimensions[col].width = w
    ws2 = wb.create_sheet("Breakdown")
    ws2.append(["System", "Dimension", "Group", "n", "Metric", "Rate %"])
    for r in results:
        for dim, groups in r["breakdown"].items():
            for gname, d in groups.items():
                for k, vv in d.items():
                    if k != "n":
                        ws2.append([r["system"], dim, gname, d["n"], k, None if vv is None else round(vv, 1)])
    wb.save(path)
    return True
