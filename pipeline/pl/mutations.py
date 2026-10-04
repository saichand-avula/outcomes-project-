"""Defect library: take a correct summary (gold) and damage it in one specific way.

Each mutation has: the rule that should catch it, the lowest severity we accept as "caught", and the judge rubric that
should catch it (faithfulness / completeness / calibration, or None for structural damage the judge never sees).
Mutations marked expect=None are damages the deterministic rules CANNOT see; they are in the library so that limit is measured.
"""
from __future__ import annotations

import copy
import json
import random
import re

from . import lexicons as L
from .textnorm import normalize, number_candidates
from .transcript import turn_text

SECTIONS = ("assessment", "response", "education")
OTHER_DRUGS = ["lisinopril", "warfarin", "prednisone", "furosemide", "sertraline", "amoxicillin", "tramadol", "insulin glargine"]
FABRICATIONS = [("A fever of 101.5 was reported.", "fever"), ("A fall the previous evening was reported.", "fall"), ("New chest pain was reported.", "chest pain"),
                ("A new rash on the arms was reported.", "rash"), ("A seizure earlier in the day was reported.", "seizure")]


def _bullets(t):
    for sec in SECTIONS:
        for i, b in enumerate(t.get(sec) or []):
            yield sec, i, b


def _text_key(path):
    return "reason" if path == "chief_complaint" else "text"


def _some(rng, items):
    items = list(items)
    return rng.choice(items) if items else None


def _words(s):
    return re.findall(r"\S+", s)


# ---------------------------------------------------------------- structural (raw / schema)
def m_truncate_json(t, turns, rng):
    return ("raw", json.dumps(t)[: max(40, int(len(json.dumps(t)) * rng.uniform(0.4, 0.9)))], "output cut off mid-JSON")


def m_drop_section(t, turns, rng):
    key = rng.choice(["education", "response", "assessment"])
    t.pop(key, None)
    return f"removed the '{key}' key"


def m_bad_speaker_enum(t, turns, rng):
    s = _some(rng, _bullets(t))
    if not s:
        return None
    s[2]["speaker"] = "Doctor"
    return "speaker set to 'Doctor'"


def m_turn_out_of_range(t, turns, rng):
    s = _some(rng, _bullets(t))
    if not s:
        return None
    s[2]["turns"] = [len(turns) + 5]
    return f"cited turn {len(turns) + 5} which does not exist"


# ---------------------------------------------------------------- quotes and speakers
def m_quote_other_turn(t, turns, rng):
    s = _some(rng, [x for x in _bullets(t) if len(turns) > 8])
    if not s:
        return None
    b = s[2]
    far = [x for x in turns if all(abs(x["id"] - i) > 4 for i in b["turns"]) and len(x["text"].split()) >= 5]
    if not far:
        return None
    pick = rng.choice(far)
    b["quote"], b["speaker"] = pick["text"], pick["speaker"]
    return f"quote replaced by an unrelated sentence from turn {pick['id']}"


def m_quote_paraphrase(t, turns, rng):
    s = _some(rng, [x for x in _bullets(t) if len(_words(x[2]["quote"])) >= 7])
    if not s:
        return None
    w = _words(s[2]["quote"])
    s[2]["quote"] = " ".join(w[: len(w) // 3] + ["basically", "that", "is", "what", "was", "said"] + w[-(len(w) // 3):])
    return "quote paraphrased (middle words replaced)"


def m_quote_one_word(t, turns, rng):
    s = _some(rng, [x for x in _bullets(t) if len(_words(x[2]["quote"])) >= 12])
    if not s:
        return None
    w = _words(s[2]["quote"])
    k = len(w) // 2
    w[k] = "really"
    s[2]["quote"] = " ".join(w)
    return "one word of a long quote changed (repairable)"


def m_speaker_flip(t, turns, rng):
    s = _some(rng, _bullets(t))
    if not s:
        return None
    b = s[2]
    b["speaker"] = "Nurse" if b["speaker"] == "Caller" else "Caller"
    return f"speaker label flipped on {s[0]}[{s[1]}]"


# ---------------------------------------------------------------- numbers, drugs, invented findings
def m_number_text(t, turns, rng):
    sites = []
    for sec, i, b in _bullets(t):
        for m in re.finditer(r"(?<![\d.:/])\d+(?![\d.:/])", b["text"]):
            if int(m.group()) > 1 and not re.fullmatch(r"(19|20)\d\d", m.group()):
                sites.append((b, m))
    s = _some(rng, sites)
    if not s:
        return None
    b, m = s
    v = int(m.group())
    new = v + 30 if v >= 50 else (v * 3 + 1)
    b["text"] = b["text"][:m.start()] + str(new) + b["text"][m.end():]
    return f"number {v} changed to {new} in the bullet text"


def m_number_fact(t, turns, rng):
    sites = [(f, k) for _, _, b in _bullets(t) for f in b["facts"] if isinstance(f, dict) for k in ("dose", "strength", "value") if re.fullmatch(r"\d+(\.\d+)?", str(f.get(k) or ""))]
    s = _some(rng, sites)
    if not s:
        return None
    f, k = s
    old = f[k]
    f[k] = str(int(float(old)) * 7 + 3)
    return f"fact {k} changed from {old} to {f[k]}"


def m_drug_swap_text(t, turns, rng):
    full = normalize(" ".join(x["text"] for x in turns))
    sites = []
    for sec, i, b in _bullets(t):
        for f in b["facts"]:
            if isinstance(f, dict) and f.get("type") == "medication" and f.get("name") and re.search(re.escape(f["name"]), b["text"], re.I):
                sites.append((b, f))
    s = _some(rng, sites)
    if not s:
        return None
    b, f = s
    repl = rng.choice([d for d in OTHER_DRUGS if d not in full])
    old = f["name"]
    b["text"] = re.sub(re.escape(old), repl, b["text"], count=1, flags=re.I)
    return f"drug {old} replaced by {repl} in the text"


def m_drug_swap_fact(t, turns, rng):
    full = normalize(" ".join(x["text"] for x in turns))
    sites = [f for _, _, b in _bullets(t) for f in b["facts"] if isinstance(f, dict) and f.get("type") == "medication" and f.get("name")]
    f = _some(rng, sites)
    if not f:
        return None
    old = f["name"]
    f["name"] = rng.choice([d for d in OTHER_DRUGS if d not in full])
    return f"medication fact name {old} replaced by {f['name']}"


def _new_bullet(turns, text, rng):
    pick = rng.choice([x for x in turns if x["speaker"] == "Caller" and len(x["text"].split()) >= 4] or turns)
    return {"text": text, "speaker": pick["speaker"], "turns": [pick["id"]], "quote": pick["text"], "explanation": "Documents an additional reported symptom.",
            "facts": [{"type": "symptom", "name": text.split(" was ")[0].lower(), "present": True, "certainty": "stated"}]}


def m_invented_with_number(t, turns, rng):
    if (t.get("not_applicable") or {}).get("is_na"):
        return None
    full = " ".join(x["text"] for x in turns).lower()
    if "fever" in full or "101" in full:
        return None
    t["assessment"].append(_new_bullet(turns, "A fever of 101.5 was reported.", rng))
    return "added an invented 'fever of 101.5'"


def m_invented_lexicon(t, turns, rng):
    if (t.get("not_applicable") or {}).get("is_na"):
        return None
    full = " ".join(x["text"] for x in turns).lower()
    opts = [(x, k) for x, k in FABRICATIONS if k not in full and "101" not in x]
    if not opts:
        return None
    text, k = rng.choice(opts)
    t["assessment"].append(_new_bullet(turns, text, rng))
    return f"added an invented finding: {text!r}"


def m_invented_unlisted(t, turns, rng):
    """A made-up finding that is NOT in the clinical-term list: the rules should miss it."""
    if (t.get("not_applicable") or {}).get("is_na"):
        return None
    full = " ".join(x["text"] for x in turns).lower()
    text = rng.choice([x for x in ["Numbness in the left hand was reported.", "Hearing loss in one ear was reported.", "Dry eyes were reported.", "Hair loss was reported."]
                       if x.split()[0].lower() not in full])
    t["assessment"].append(_new_bullet(turns, text, rng))
    return f"added an invented finding outside the term list: {text!r}"


# ---------------------------------------------------------------- identity
def _identity_field(t, key):
    f = (t.get("identity") or {}).get(key) or {}
    return f if f.get("value") else None


def m_patient_name(t, turns, rng):
    f = _identity_field(t, "patient_name")
    if not f:
        return None
    old = f["value"]
    f["value"] = rng.choice(["Zelda Quimby", "Orville Pennington", "Bettina Vandersloot"])
    return f"patient name {old} -> {f['value']}"


def m_caller_name(t, turns, rng):
    f = _identity_field(t, "caller_name")
    if not f:
        return None
    old = f["value"]
    f["value"] = rng.choice(["Gwendolyn Marsh", "Thaddeus Kline"])
    return f"caller name {old} -> {f['value']}"


def m_dob_year(t, turns, rng):
    f = _identity_field(t, "patient_dob")
    if not f or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["value"]):
        return None
    old = f["value"]
    y = int(old[:4])
    f["value"] = f"{y + rng.choice([-7, -3, 4, 9])}{old[4:]}"
    return f"DOB {old} -> {f['value']}"


def m_phone_digit(t, turns, rng):
    f = _identity_field(t, "callback_phone")
    if not f:
        return None
    old = f["value"]
    i = rng.randrange(3, 10)
    f["value"] = old[:i] + str((int(old[i]) + 3) % 10) + old[i + 1:]
    return f"phone {old} -> {f['value']}"


def m_names_swapped(t, turns, rng):
    """Patient and caller names exchanged: both are in the call, so rule-based identity checks cannot see it."""
    p, c = _identity_field(t, "patient_name"), _identity_field(t, "caller_name")
    if not p or not c or p["value"] == c["value"]:
        return None
    p["value"], c["value"] = c["value"], p["value"]
    return "patient and caller names swapped"


# ---------------------------------------------------------------- status, hedges, negation
def _actions(t):
    return [(sec, i, b, f) for sec, i, b in _bullets(t) if b["speaker"] == "Nurse" for f in b["facts"] if isinstance(f, dict) and f.get("type") == "action"]


def m_planned_to_completed_status(t, turns, rng):
    s = _some(rng, [x for x in _actions(t) if x[3].get("status") == "planned"])
    if not s:
        return None
    s[3]["status"] = "completed"
    return f"status flipped to completed on {s[0]}[{s[1]}] (text still says planned)"


def m_planned_to_completed_text(t, turns, rng):
    s = _some(rng, [x for x in _actions(t) if x[3].get("status") == "planned" and x[2]["text"].startswith("Planned to ")])
    if not s:
        return None
    s[2]["text"] = "Completed: " + s[2]["text"][len("Planned to "):]
    s[3]["status"] = "completed"
    return f"'Planned to ...' rewritten as 'Completed: ...' on {s[0]}[{s[1]}]"


def m_completed_to_planned(t, turns, rng):
    s = _some(rng, [x for x in _actions(t) if x[3].get("status") == "completed" and L.COMPLETION.search(x[2]["quote"])])
    if not s:
        return None
    s[3]["status"] = "planned"
    s[2]["text"] = "Planned to " + s[2]["text"][0].lower() + s[2]["text"][1:]
    return f"completed action rewritten as planned on {s[0]}[{s[1]}]"


def m_hedge_removed(t, turns, rng):
    sites = [(b, f) for sec, i, b in _bullets(t) if b["speaker"] == "Caller" and L.HEDGE.search(b["quote"]) for f in b["facts"] if isinstance(f, dict)]
    s = _some(rng, sites)
    if not s:
        return None
    b, _ = s
    for f in b["facts"]:
        if isinstance(f, dict):
            f["certainty"] = "stated"
    b["text"] = L.SOFTENER.sub("", b["text"]).replace("  ", " ")
    return "hedge removed from a bullet whose quote is hedged"


def m_negation_flip(t, turns, rng):
    sites = [(b, f) for sec, i, b in _bullets(t) for f in b["facts"] if isinstance(f, dict) and f.get("type") == "pertinent_negative" and f.get("name")]
    s = _some(rng, sites)
    if not s:
        return None
    b, f = s
    b["text"] = f"{f['name'][0].upper()}{f['name'][1:]} was reported."
    return f"negative finding '{f['name']}' rewritten as present"


# ---------------------------------------------------------------- risk flags and Not-Applicable
def m_drop_flag(t, turns, rng):
    s = _some(rng, range(len(t.get("risk_flags") or [])))
    if s is None:
        return None
    f = t["risk_flags"].pop(s)
    return f"risk flag {f['category']} removed"


def m_spurious_suicidal(t, turns, rng):
    if (t.get("not_applicable") or {}).get("is_na") or any(f["category"] == "suicidal_statement" for f in t.get("risk_flags") or []):
        return None
    pick = rng.choice([x for x in turns if x["speaker"] == "Caller" and len(x["text"].split()) >= 4] or turns)
    t["risk_flags"].append({"category": "suicidal_statement", "turns": [pick["id"]], "quote": pick["text"]})
    return "suicidal_statement flag added with an unrelated quote"


def m_na_false_positive(t, turns, rng):
    if (t.get("not_applicable") or {}).get("is_na"):
        return None
    t["not_applicable"] = {"is_na": True, "reason": "No clinical content."}
    for k in SECTIONS:
        t[k] = []
    t["risk_flags"] = []
    t.pop("chief_complaint", None)
    return "a clinical call returned as Not Applicable"


def m_na_false_negative(t, turns, rng):
    if not (t.get("not_applicable") or {}).get("is_na"):
        return None
    t["not_applicable"] = {"is_na": False, "reason": None}
    t["chief_complaint"] = {"reason": "Reported a symptom.", "speaker": "Caller", "turns": [2], "quote": turns[1]["text"], "explanation": "Documents the reason for the call."}
    t["assessment"].append(_new_bullet(turns, "Pain was reported.", rng))
    return "a non-clinical call summarized as if it were clinical"


# ---------------------------------------------------------------- completeness and hygiene
def m_drop_bullet(t, turns, rng):
    s = _some(rng, [x for x in _bullets(t) if len(t[x[0]]) >= 2])
    if not s:
        return None
    t[s[0]].pop(s[1])
    return f"removed {s[0]}[{s[1]}]"


def m_duplicate_bullet(t, turns, rng):
    s = _some(rng, _bullets(t))
    if not s:
        return None
    t[s[0]].append(copy.deepcopy(s[2]))
    return f"duplicated {s[0]}[{s[1]}]"


def m_empty_text(t, turns, rng):
    s = _some(rng, _bullets(t))
    if not s:
        return None
    s[2]["text"] = ""
    return "bullet text emptied"


def m_number_swapped_in_call(t, turns, rng):
    """A dose replaced by ANOTHER number that is spoken elsewhere in the same call: only locality can show it, so no rule fires."""
    sites = [(f, k) for _, _, b in _bullets(t) for f in b["facts"] if isinstance(f, dict) for k in ("dose",) if re.fullmatch(r"\d+", str(f.get(k) or ""))]
    s = _some(rng, sites)
    if not s:
        return None
    f, k = s
    nums = sorted(c for c in number_candidates(" ".join(x["text"] for x in turns)) if c.isdigit() and len(c) <= 3 and c != f[k] and not c.startswith("0"))
    if not nums:
        return None
    old = f[k]
    f[k] = rng.choice(nums)
    return f"dose {old} replaced by {f[k]}, which is spoken elsewhere in the call"


# name: (function, rules that should catch it, minimum severity that counts as caught, judge rubric)
MUTATIONS = {
    "truncated_json":            (m_truncate_json, ["V1"], "ERROR", None),
    "missing_section":           (m_drop_section, ["V1"], "ERROR", None),
    "bad_speaker_value":         (m_bad_speaker_enum, ["V1"], "ERROR", None),
    "turn_out_of_range":         (m_turn_out_of_range, ["V3"], "ERROR", None),
    "quote_from_other_turn":     (m_quote_other_turn, ["V4"], "ERROR", "faithfulness"),
    "quote_paraphrased":         (m_quote_paraphrase, ["V4"], "ERROR", "faithfulness"),
    "quote_one_word_changed":    (m_quote_one_word, ["V4"], "WARN", None),
    "speaker_flipped":           (m_speaker_flip, ["V5"], "WARN", "calibration"),
    "number_changed_in_text":    (m_number_text, ["V6"], "ERROR", "faithfulness"),
    "dose_changed_in_fact":      (m_number_fact, ["V6"], "ERROR", "faithfulness"),
    "drug_swapped_in_text":      (m_drug_swap_text, ["V7"], "ERROR", "faithfulness"),
    "drug_swapped_in_fact":      (m_drug_swap_fact, ["V7"], "ERROR", "faithfulness"),
    "invented_fever_101":        (m_invented_with_number, ["V6", "V8"], "ERROR", "faithfulness"),
    "invented_listed_finding":   (m_invented_lexicon, ["V8"], "ERROR", "faithfulness"),
    "invented_unlisted_finding": (m_invented_unlisted, [], "ERROR", "faithfulness"),
    "patient_name_changed":      (m_patient_name, ["V9"], "ERROR", "faithfulness"),
    "caller_name_changed":       (m_caller_name, ["V9"], "ERROR", "faithfulness"),
    "dob_year_changed":          (m_dob_year, ["V9"], "ERROR", "faithfulness"),
    "phone_digit_changed":       (m_phone_digit, ["V9"], "ERROR", "faithfulness"),
    "names_swapped":             (m_names_swapped, [], "ERROR", "faithfulness"),
    "status_flipped_to_done":    (m_planned_to_completed_status, ["V10"], "ERROR", "calibration"),
    "planned_rewritten_as_done": (m_planned_to_completed_text, ["V10"], "ERROR", "calibration"),
    "done_rewritten_as_planned": (m_completed_to_planned, ["V10"], "ERROR", "calibration"),
    "hedge_removed":             (m_hedge_removed, ["V11"], "WARN", "calibration"),
    "negative_flipped":          (m_negation_flip, ["V12"], "ERROR", "faithfulness"),
    "risk_flag_dropped":         (m_drop_flag, ["V13"], "WARN", None),
    "spurious_suicidal_flag":    (m_spurious_suicidal, ["V13"], "WARN", None),
    "clinical_call_marked_na":   (m_na_false_positive, ["V14"], "ERROR", "completeness"),
    "non_clinical_made_clinical": (m_na_false_negative, ["V14"], "WARN", "faithfulness"),
    "bullet_removed":            (m_drop_bullet, [], "ERROR", "completeness"),
    "bullet_duplicated":         (m_duplicate_bullet, ["V16"], "WARN", None),
    "bullet_text_emptied":       (m_empty_text, ["V16"], "ERROR", None),
    "dose_swapped_within_call":  (m_number_swapped_in_call, [], "ERROR", "faithfulness"),
}
# mutations the deterministic rules are NOT expected to catch (rules list is empty)
INVISIBLE = {k for k, v in MUTATIONS.items() if not v[1]}


def apply(name: str, target: dict, turns: list[dict], seed: str):
    """-> (kind, payload, description) or None when the mutation does not apply to this call. kind 'obj' (dict) or 'raw' (str)."""
    fn = MUTATIONS[name][0]
    rng = random.Random(f"{name}:{seed}")
    t = copy.deepcopy(target)
    out = fn(t, turns, rng)
    if out is None:
        return None
    if isinstance(out, tuple):
        return out
    return ("obj", t, out)
