"""Why are medication scores low? Classify every gold medication of the 100 validation calls for each saved run.

For each gold medication (same matching as pl/reference_metrics.py H3/H4):
  ok            name found and dose+unit right
  dose_missing  name found, the model wrote no dose although the gold has one
  dose_wrong    name found, the model wrote a different number
  unit_wrong    same number, different unit
  not_found     no model medication matches the name (then: did the model write another drug instead, or nothing?)
Also counts model medications that match no gold medication ("extra").

Usage: python3 dev/med_error_analysis.py [run ...]     (default: base_v4_s2 finetuned_epoch1_s2 finetuned_epoch2_s2 finetuned_epoch3_s2)
Writes outputs/med_errors.md and outputs/med_errors.json.
"""
import json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pl.reference_metrics import _facts, _name_match, _same_dose, _num, _unit, SECTIONS  # noqa: E402
from pl.textnorm import normalize  # noqa: E402

RUNS = sys.argv[1:] or ["base_v4_s2", "finetuned_epoch1_s2", "finetuned_epoch2_s2", "finetuned_epoch3_s2"]
cases = {c["id"]: c for c in map(json.loads, open(ROOT / "data" / "val_cases.jsonl"))}


def meds(t, sections):
    return [f for s in sections for _, f in _facts(t, s) if f.get("type") == "medication"]


WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
COUNT_UNITS = {"tablet", "puff", "drop", "unit"}


def summary_text(t):
    """The prose of a summary as a list of passages: the reason for the call and every bullet's text (what the nurse reads after rendering); digits kept."""
    parts = [str((t.get("chief_complaint") or {}).get("reason") or "")]
    parts += [str(b.get("text") or "") for sec in SECTIONS for b in (t.get(sec) or []) if isinstance(b, dict)]
    return [re.sub(r"\b(" + "|".join(WORDS) + r")\b", lambda m: WORDS[m.group(1)], p.lower()) for p in parts]


def passages_naming(gf, text):
    """The passages that name the drug (first long word of its gold name)."""
    words = [w for w in normalize(str(gf.get("name") or "")).split() if len(w) >= 4]
    return [p for p in text if words and words[0] in normalize(p)]


def name_in_text(gf, text):
    return bool(passages_naming(gf, text))


def dose_in_text(gf, text):
    """True/False when the gold dose is a number (is it written in a passage that names the drug?); None when it is not (e.g. 'half a tablet')."""
    d = str(gf.get("dose") or "").strip().lower()
    d = WORDS.get(d, d)
    if not re.fullmatch(r"\d+(\.\d+)?", d):
        return None
    return any(re.search(rf"(?<![\d.]){re.escape(d)}(?![\d]|\.\d)", p) for p in passages_naming(gf, text))


def fmt(f):
    return f"{f.get('name')} {f.get('dose') or ''} {f.get('unit') or ''}".strip()


def classify(gf, pf):
    if _same_dose(gf, pf):
        return "ok"
    if pf.get("dose") in (None, ""):
        return "dose_missing"
    a, b = _num(gf.get("dose")), _num(pf.get("dose"))
    if a is not None and b is not None and a == b:
        return "unit_wrong"
    return "dose_wrong"


result, detail = {}, {}
for run in RUNS:
    gens = {r["id"]: r for r in map(json.loads, open(ROOT / "outputs" / run / "generations.jsonl"))}
    cnt, rows, extra = Counter(), [], []
    n_gold = 0
    for cid, c in cases.items():
        gold = c["gold_target"]
        if (gold.get("not_applicable") or {}).get("is_na"):
            continue
        pred = gens.get(cid, {}).get("parsed") or {}
        text = summary_text(pred)
        g_meds = meds(gold, ("assessment",))
        p_meds = meds(pred, SECTIONS)
        used = set()
        for gf in g_meds:
            n_gold += 1
            nit = name_in_text(gf, text)
            cnt["name_in_text"] += int(nit)
            dit = dose_in_text(gf, text)
            cnt["name_and_dose_in_text"] += int(nit and dit is not False)
            hit = next((i for i, pf in enumerate(p_meds) if i not in used and _name_match(gf.get("name"), pf.get("name"))), None)
            if hit is None:
                cnt["not_found"] += 1
                unused = [fmt(pf) for i, pf in enumerate(p_meds) if i not in used]
                rows.append({"id": cid, "kind": "not_found", "gold": fmt(gf), "model": "; ".join(unused) or "(no medication written)", "category": c["meta"].get("category"),
                             "reading": "named in the summary text, no typed medication fact" if nit else "dropped from the summary"})
                continue
            used.add(hit)
            k = classify(gf, p_meds[hit])
            cnt[k] += 1
            if k != "ok":
                reading = {"dose_missing": "dose is in the summary text, not in the typed fact" if dit else "dose dropped from the summary",
                           "dose_wrong": "gold counts tablets or fractions, model wrote the strength (convention)" if (dit is None or _unit(gf.get("unit")) in COUNT_UNITS or _unit(gf.get("unit")) == "") and _unit(p_meds[hit].get("unit")) in ("mg", "mcg", "g", "ml") else "different number"}.get(k, "")
                rows.append({"id": cid, "kind": k, "gold": fmt(gf), "model": fmt(p_meds[hit]), "category": c["meta"].get("category"), "reading": reading})
        for i, pf in enumerate(p_meds):
            if i not in used:
                extra.append({"id": cid, "model": fmt(pf)})
    result[run] = {"gold_meds": n_gold, **cnt, "extra_model_meds": len(extra)}
    detail[run] = {"errors": rows, "extra": extra}

(ROOT / "outputs" / "med_errors.json").write_text(json.dumps({"summary": result, "detail": detail}, indent=1))

L = ["# Medication errors by type (100 validation calls)", "",
     "Every gold medication is compared with what each run wrote, using the same matching as H3/H4 in the matrix. Generated by `dev/med_error_analysis.py`.", "",
     "| run | gold meds | strict ok (H4) | not found | dose missing | dose wrong | unit wrong | extra meds not in gold | name in summary text | name and dose in summary text |", "|---|---|---|---|---|---|---|---|---|---|"]
for run, r in result.items():
    L.append(f"| {run} | {r['gold_meds']} | {r.get('ok', 0)} | {r.get('not_found', 0)} | {r.get('dose_missing', 0)} | {r.get('dose_wrong', 0)} | {r.get('unit_wrong', 0)} | {r['extra_model_meds']} | {r.get('name_in_text', 0)} | {r.get('name_and_dose_in_text', 0)} |")
for run in RUNS:
    L += ["", f"## {run}: every medication error", "", "| call | category | error | gold | model wrote | reading |", "|---|---|---|---|---|---|"]
    for e in detail[run]["errors"]:
        L.append(f"| {e['id']} | {e['category']} | {e['kind']} | {e['gold']} | {e['model']} | {e.get('reading', '')} |")
(ROOT / "outputs" / "med_errors.md").write_text("\n".join(L) + "\n")
print("\n".join(L[:9]))
