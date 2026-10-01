"""Mutation generator: inject ONE known error into a gold record, return (mutated_gold, error_type) or None.

Two uses (plan Sections 6 and External-LLM):
  1. prove the deterministic validators can fail  -> tests/test_mutation.py, AUDIT.md table (detection rate per error type)
  2. calibrate the LLM-judge panel                -> run the judges on mutated summaries; report detection per error type

Completeness errors (a dropped bullet) are not validator errors: validators check consistency/precision, completeness is
scored by gold-fact alignment in the scorer, so `drop_bullet` is provided for the scorer/judge but excluded from validator tests.
"""
from __future__ import annotations
import copy
import random

import lexicons as L
import spoken as SP

FORMS = [d["generic"] for d in L.FORMULARY]
FLIP_ROUTE = {"PO": "PR", "SL": "PO", "transdermal": "PO", "inhaled": "PO", "PR": "PO"}
FLIP_FREQ = {"daily": "QID", "BID": "q72h", "TID": "q72h", "QID": "daily", "q4h": "q72h", "q4h PRN": "q72h", "q6h PRN": "q72h",
             "q2h PRN": "q72h", "q8h PRN": "q72h", "q72h": "TID"}


def _bullets(g, kind): return [b for b in g["bullets"] if b["kind"] == kind]


def swap_drug(g, rng):
    c = [b for b in _bullets(g, "medication") if b["facts"][0]["name"]]
    if not c: return None
    b = rng.choice(c); old = b["facts"][0]["name"]
    new = rng.choice([x for x in FORMS if x != old])
    b["facts"][0]["name"] = new; b["text"] = b["text"].replace(old, new, 1)
    return "swap_drug"


def change_dose(g, rng):
    c = [b for b in _bullets(g, "medication") if b["facts"][0]["dose"]]
    if not c: return None
    b = rng.choice(c); f = b["facts"][0]
    f["dose"] = f"{float(f['dose']) * 2:g}" if f["dose"] != "1" else "3"
    return "change_dose"


def change_frequency(g, rng):
    c = [b for b in _bullets(g, "medication") if b["facts"][0]["frequency"] in FLIP_FREQ]
    if not c: return None
    b = rng.choice(c); b["facts"][0]["frequency"] = FLIP_FREQ[b["facts"][0]["frequency"]]
    return "change_frequency"


def change_route(g, rng):
    c = [b for b in _bullets(g, "medication") if b["facts"][0]["route"]]
    if not c: return None
    b = rng.choice(c); b["facts"][0]["route"] = FLIP_ROUTE[b["facts"][0]["route"]]
    return "change_route"


def change_severity(g, rng):
    c = [b for b in _bullets(g, "symptom") if (b["facts"][0]["severity"] or "").endswith("/10")]
    if not c: return None
    b = rng.choice(c); n = int(b["facts"][0]["severity"].split("/")[0])
    b["facts"][0]["severity"] = f"{(n + 4 - 1) % 10 + 1}/10"
    return "change_severity"


def change_qty(g, rng):
    c = [b for b in _bullets(g, "supply") if b["facts"][0]["quantity_remaining"]]
    if not c: return None
    b = rng.choice(c); b["facts"][0]["quantity_remaining"] = "29 doses"
    return "change_quantity"


def wrong_speaker(g, rng):
    c = [b for b in g["bullets"] if b["speaker"]]
    if not c: return None
    b = rng.choice(c); b["speaker"] = "Nurse" if b["speaker"] == "Caller" else "Caller"
    return "wrong_speaker"


def attribution_text(g, rng):
    c = [b for b in g["bullets"] if b["text"].split()[0] in ("Caller", "Nurse")]
    if not c: return None
    b = rng.choice(c); w = b["text"].split()[0]
    b["text"] = ("Nurse" if w == "Caller" else "Caller") + b["text"][len(w):]
    return "attribution_swapped"


def misattribute_evidence(g, rng):
    """Point a bullet at another bullet's turns+quote (the quote is real, but it does not support this claim)."""
    c = [b for b in g["bullets"] if b["kind"] in ("symptom", "medication", "negative", "supply") and b["turn_ids"]]
    if len(c) < 2: return None
    a, b = rng.sample(c, 2)
    if a["facts"][0].get("name") == b["facts"][0].get("name"): return None
    a["turn_ids"], a["quote"], a["speaker"] = list(b["turn_ids"]), b["quote"], b["speaker"]
    return "misattributed_evidence"


def flip_action_status(g, rng):
    c = [b for b in _bullets(g, "action") if b["facts"][0]["status"] in ("planned", "completed")]
    if not c: return None
    b = rng.choice(c); f = b["facts"][0]
    f["status"] = "completed" if f["status"] == "planned" else "planned"
    return "planned_completed_flipped"


def wrong_phone(g, rng):
    v = g["identity"]["callback_phone"]["value"]
    if not v: return None
    g["identity"]["callback_phone"]["value"] = v[:-1] + str((int(v[-1]) + 3) % 10)
    return "wrong_phone"


def wrong_dob(g, rng):
    v = g["identity"]["patient_dob"]["value"]
    if not v: return None
    g["identity"]["patient_dob"]["value"] = v[:8] + f"{(int(v[8:]) % 28) + 1:02d}"
    return "wrong_dob"


def invented_symptom(g, rng):
    c = _bullets(g, "symptom")
    if not c: return None
    b = copy.deepcopy(rng.choice(c)); b["fact_id"] = "S99"
    b["facts"][0].update(name="seizure", severity=None); b["text"] = "Caller reported seizure."
    g["bullets"].append(b)
    return "invented_symptom"


def drop_unclear_marker(g, rng):
    c = [b for b in _bullets(g, "medication") if "unclear" in b["text"]]
    if not c: return None
    b = rng.choice(c); b["text"] = b["text"].replace("unclear", "confirmed")
    return "unclear_marker_removed"


def wrong_risk_category(g, rng):
    c = [r for r in g["risk_flags"] if r["required"]]
    if not c: return None
    r = rng.choice(c)
    r["category"] = "breathing_concern" if r["category"] != "breathing_concern" else "suicidal_statement"
    return "wrong_risk_category"


def negative_to_symptom(g, rng):
    c = _bullets(g, "negative")
    if not c: return None
    b = rng.choice(c); n = b["facts"][0]["name"]
    nm = {"difficulty breathing": "shortness of breath", "falls": "fall"}.get(n, n)
    b["kind"] = "symptom"; b["facts"] = [dict(type="symptom", name=nm, severity=None, certainty="stated")]
    b["text"] = f"Caller reported {nm}."
    return "negation_flipped"


def symptom_to_negative(g, rng):
    c = [b for b in _bullets(g, "symptom") if b["facts"][0]["name"] in ("fever", "nausea", "confusion")]
    if not c: return None
    b = rng.choice(c); n = b["facts"][0]["name"]
    b["kind"] = "negative"; b["facts"] = [dict(type="negative", name=n)]; b["text"] = f"Caller denied {n}."
    return "negation_flipped"


def drop_bullet(g, rng):                        # completeness error: for scorer / judge calibration only
    if len(g["bullets"]) < 2: return None
    g["bullets"].pop(rng.randrange(len(g["bullets"])))
    return "dropped_bullet"


VALIDATOR_MUTATIONS = [swap_drug, change_dose, change_frequency, change_route, change_severity, change_qty, wrong_speaker,
                       attribution_text, misattribute_evidence, flip_action_status, wrong_phone, wrong_dob, invented_symptom,
                       drop_unclear_marker, wrong_risk_category, negative_to_symptom, symptom_to_negative]
ALL_MUTATIONS = VALIDATOR_MUTATIONS + [drop_bullet]


def mutate(gold: dict, fn, seed) -> tuple[dict, str] | None:
    g = copy.deepcopy(gold)
    kind = fn(g, random.Random(seed))
    return (g, kind) if kind else None
