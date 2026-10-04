"""Reference-based scoring against the gold summary (only for calls that have one: our validation set).

Everything is a (matched, total) pair so results can be summed over calls. Matching is anchored on the turns each bullet
cites (+/- 1 turn), so it does not depend on the model using the same wording as the gold.
Critical-Fact Accuracy (architecture 6.1): matched critical slots / (gold critical slots + unsupported model critical slots).
"""
from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher

from .textnorm import normalize

SECTIONS = ("assessment", "response", "education")
IDENT = ("patient_name", "patient_dob", "caller_name", "relationship", "callback_phone")
STOP = {"the", "and", "was", "were", "had", "has", "have", "for", "with", "that", "this", "her", "his", "their", "she", "him", "not", "any", "very", "been",
        "reported", "present", "caller", "patient", "about", "from", "than", "into"}


SYNONYMS = {  # words that name the same finding; each maps to one canonical word before comparing
    "intake": "intake", "eating": "intake", "eat": "intake", "ate": "intake", "appetite": "intake", "sips": "intake", "sipping": "intake",
    "drinking": "intake", "fluids": "intake", "food": "intake",
    "sleepiness": "sleepy", "sleepy": "sleepy", "sleeping": "sleepy", "sleep": "sleepy", "drowsy": "sleepy", "drowsiness": "sleepy",
}
UNITS = {"mg": "mg", "milligram": "mg", "milligrams": "mg", "ml": "ml", "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "mcg": "mcg",
         "microgram": "mcg", "micrograms": "mcg", "g": "g", "gram": "g", "grams": "g", "tablet": "tablet", "tablets": "tablet", "tab": "tablet",
         "pill": "tablet", "pills": "tablet", "puff": "puff", "puffs": "puff", "unit": "unit", "units": "unit", "drop": "drop", "drops": "drop"}


def _words(s) -> set:
    return {SYNONYMS.get(w, w) for w in normalize(str(s or "")).split() if len(w) >= 3 and w not in STOP}


def _unit(u) -> str:
    n = normalize(str(u or ""))
    return UNITS.get(n, n)


def _near(a_turns, b_turns, radius=1) -> bool:
    return any(abs(x - y) <= radius for x in a_turns for y in b_turns if isinstance(x, int) and isinstance(y, int))


def _num(v):
    try:
        return float(re.sub(r"[^\d.]", "", str(v)))
    except ValueError:
        return None


def _facts(t, sec):
    for b in (t.get(sec) or []) if isinstance(t, dict) else []:
        if isinstance(b, dict):
            for f in b.get("facts") or []:
                if isinstance(f, dict):
                    yield b, f


def _name_match(a, b) -> bool:
    na, nb = normalize(str(a or "")), normalize(str(b or ""))
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na or SequenceMatcher(None, na, nb).ratio() >= 0.85


def _same_dose(g, p) -> bool:
    gd, pd = g.get("dose"), p.get("dose")
    if gd in (None, ""):
        return True  # the gold names no dose: extra detail the call really contains is not an error (invented numbers are caught by rule V6)
    a, b = _num(gd), _num(pd)
    if a is None or b is None:
        return normalize(str(gd)) == normalize(str(pd))
    if a != b:
        return False
    gu, pu = _unit(g.get("unit")), _unit(p.get("unit"))
    return gu == pu or not gu or not pu


def score(pred, gold: dict) -> dict:
    """-> {metric: [matched, total]} plus 'cfa_unsupported': [count, 0]. `pred` may be None (unusable output)."""
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    def add(name, ok, n=1):
        out[name][1] += n
        out[name][0] += n if ok is True else (ok if isinstance(ok, int) and not isinstance(ok, bool) else 0)

    pred = pred if isinstance(pred, dict) else {}
    g_na = bool((gold.get("not_applicable") or {}).get("is_na"))
    p_na = bool((pred.get("not_applicable") or {}).get("is_na")) if pred else None
    add("na_label", p_na is not None and p_na == g_na)
    unsupported = 0
    crit_total = 1
    crit_match = int(p_na is not None and p_na == g_na)
    if g_na:
        out["cfa_crit"] = [crit_match, crit_total]
        out["cfa_unsupported"] = [1 if (pred and not p_na) else 0, 0]
        return dict(out)
    gi, pi = gold.get("identity") or {}, pred.get("identity") or {}
    for k in IDENT:
        g, p = gi.get(k) or {}, pi.get(k) or {}
        gv, pv = g.get("value"), p.get("value")
        if k in ("patient_name", "caller_name"):  # all the gold's name words must be there; a spoken surname added by the model is fine
            val_ok = set(normalize(str(gv or "")).split()) <= set(normalize(str(pv or "")).split()) if normalize(str(gv or "")) else not normalize(str(pv or ""))
        else:
            val_ok = (normalize(str(gv or "")) == normalize(str(pv or ""))) if k not in ("patient_dob", "callback_phone") else (re.sub(r"\D", "", str(gv or "")) == re.sub(r"\D", "", str(pv or "")))
        cert_ok = (g.get("certainty") or "stated") == (p.get("certainty") or "stated") if pred else False
        add("identity_value", val_ok and bool(pred))
        add("identity_value_and_certainty", val_ok and cert_ok and bool(pred))
        crit_total += 1
        crit_match += int(val_ok and cert_ok and bool(pred))
        if pv and not val_ok:
            unsupported += 1
    # medications
    g_meds = [(b, f) for b, f in _facts(gold, "assessment") if f.get("type") == "medication"]
    p_meds = [(b, f) for sec in SECTIONS for b, f in _facts(pred, sec) if f.get("type") == "medication"]
    used = set()
    for gb, gf in g_meds:
        hit = next((i for i, (pb, pf) in enumerate(p_meds) if i not in used and _name_match(gf.get("name"), pf.get("name"))), None)
        add("medication_name", hit is not None)
        strict = hit is not None and _same_dose(gf, p_meds[hit][1])
        add("medication_name_dose_unit", strict)
        crit_total += 1
        crit_match += int(strict)
        if hit is not None:
            used.add(hit)
            gc, pc = gf.get("certainty", "stated"), p_meds[hit][1].get("certainty", "stated")
            add("medication_certainty", gc == pc)
    unsupported += len(p_meds) - len(used)
    out["medication_hallucinated"] = [len(p_meds) - len(used), len(p_meds)]
    # symptoms, pertinent negatives, vitals, supplies: anchored on turns
    for typ in ("symptom", "pertinent_negative", "vital", "supply"):
        gl = [(b, f) for b, f in _facts(gold, "assessment") if f.get("type") == typ]
        pl = [(b, f) for b, f in _facts(pred, "assessment") if f.get("type") == typ]
        used = set()
        for gb, gf in gl:
            gw = _words(gf.get("name") or gf.get("item")) or _words(gb.get("text"))
            hit = None
            for i, (pb, pf) in enumerate(pl):
                if i in used or not _near(gb.get("turns") or [], pb.get("turns") or []):
                    continue
                pw = _words(pf.get("name") or pf.get("item")) or _words(pb.get("text"))
                if typ == "vital":
                    ok = _num(gf.get("value")) is not None and _num(gf.get("value")) == _num(pf.get("value"))
                else:
                    ok = bool(gw & pw) or bool(gw & _words(pb.get("text")))
                if ok:
                    hit = i
                    break
            add(f"{typ}_recall", hit is not None)
            if typ in ("symptom", "pertinent_negative"):
                crit_total += 1
                crit_match += int(hit is not None)
            if hit is not None:
                used.add(hit)
        if typ in ("symptom", "pertinent_negative"):
            unsupported += len(pl) - len(used)
        out[f"{typ}_unmatched_model"] = [len(pl) - len(used), len(pl)]
    # actions
    g_act = [(b, f) for sec in SECTIONS for b, f in _facts(gold, sec) if f.get("type") == "action"]
    p_act = [(b, f) for sec in SECTIONS for b, f in _facts(pred, sec) if f.get("type") == "action"]
    used_t, used_s = set(), set()
    for gb, gf in g_act:
        ti = next((i for i, (pb, pf) in enumerate(p_act) if i not in used_t and pf.get("action_type") == gf.get("action_type")), None)
        add("action_type_recall", ti is not None)
        if ti is not None:
            used_t.add(ti)
        si = next((i for i, (pb, pf) in enumerate(p_act) if i not in used_s and pf.get("action_type") == gf.get("action_type") and pf.get("status") == gf.get("status")), None)
        add("action_type_and_status", si is not None)
        if si is not None:
            used_s.add(si)
        if ti is not None:
            add("action_status_given_type", si is not None)
        crit_total += 1
        crit_match += int(si is not None)
    unsupported += len(p_act) - len(used_s)
    out["action_unmatched_model"] = [len(p_act) - len(used_s), len(p_act)]
    # education types
    g_edu = [f.get("education_type") for _, f in _facts(gold, "education")]
    p_edu = [f.get("education_type") for _, f in _facts(pred, "education")]
    pool = list(p_edu)
    for e in g_edu:
        if e in pool:
            pool.remove(e)
            add("education_type_recall", True)
        else:
            add("education_type_recall", False)
    # bullets anchored on turns, per section
    for sec in SECTIONS:
        gb_, pb_ = [b for b in gold.get(sec) or []], [b for b in (pred.get(sec) or []) if isinstance(b, dict)] if pred else []
        for b in gb_:
            add(f"{sec}_bullet_recall", any(_near(b.get("turns") or [], p.get("turns") or []) for p in pb_))
        for p in pb_:
            add(f"{sec}_bullet_supported", any(_near(b.get("turns") or [], p.get("turns") or []) for b in gb_))
    # risk flags (call-level categories)
    gcats = {f.get("category") for f in gold.get("risk_flags") or []}
    pcats = {f.get("category") for f in pred.get("risk_flags") or [] if isinstance(f, dict)} if pred else set()
    for c in gcats:
        add("flag_recall", c in pcats)
        crit_total += 1
        crit_match += int(c in pcats)
    for c in pcats:
        add("flag_precision", c in gcats)
        if c not in gcats:
            unsupported += 1
    out["cfa_crit"] = [crit_match, crit_total]
    out["cfa_unsupported"] = [unsupported, 0]
    return dict(out)


def cfa(counters: dict) -> tuple[int, int]:
    """-> (matched, denominator) with denominator = gold critical slots + unsupported model slots"""
    m, t = counters.get("cfa_crit", [0, 0])
    u = counters.get("cfa_unsupported", [0, 0])[0]
    return m, t + u
