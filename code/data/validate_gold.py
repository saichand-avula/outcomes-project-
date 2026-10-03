"""Gold validator (G1-G12): fact record <-> transcript <-> gold summary, both directions.

Run: python3 code/data/validate_gold.py [split ...]      (default: train val)
Exit code 1 if any ERROR. WARN lines are for human review.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import AUTHORING, IDENTITY_IDS, ROOT, SECTION_KEYS, load_split  # noqa: E402
from common.render import render  # noqa: E402
from common.textnorm import collapse_spelled, normalize, number_candidates, numbers_in, supported  # noqa: E402

CATEGORIES = {"routine", "ambiguous", "asr_error", "medication", "supply", "high_risk", "not_applicable"}
RISK = {"uncontrolled_symptom", "medication_concern", "suicidal_statement", "breathing_concern", "escalation_request", "other_urgent"}
FACT_TYPES = {"symptom", "pertinent_negative", "medication", "vital", "action", "education", "context", "supply"}
STATUS = {"planned", "completed", "advised"}
BUCKETS = {"short": (1500, 4500), "medium": (4500, 7500), "long": (7500, 13500)}
# v2 regime (setup.length_regime: v2): short +130%, medium +60%, long +30%; also a minimum line count
BUCKETS_V2 = {"short": (4500, 9000), "medium": (7500, 12500), "long": (10500, 18000)}
MIN_LINES_V2 = {"short": 65, "medium": 85, "long": 105}
PLAN_MARKERS = re.compile(r"\b(plan|planned|plans|will|would|to be|going to|to follow|pending|later|intends?)\b", re.I)
NUM_FIELDS = ["dose", "strength", "severity", "value", "supply", "quantity", "last_dose", "frequency", "timeframe"]
MED_FIELDS = ["strength", "dose", "unit", "route", "frequency", "prn"]

FORMULARY = [l.strip() for l in (ROOT / "data/lexicons/formulary.txt").read_text().splitlines()
             if l.strip() and not l.startswith("#")]


class Report:
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.items: list[tuple[str, str, str]] = []

    def err(self, code: str, msg: str):
        self.items.append(("ERROR", code, msg))

    def warn(self, code: str, msg: str):
        self.items.append(("WARN", code, msg))


def _norm_val(v) -> str:
    return normalize(str(v)) if v is not None else ""


def _turn_text(call: dict, ids) -> str:
    by_id = {t["id"]: t for t in call["turns"]}
    return " ".join(by_id[i]["text"] for i in ids if i in by_id)


def _tagged_turns(call: dict, fact_id: str) -> list[int]:
    return [t["id"] for t in call["turns"] if fact_id in t["fact_ids"]]


def _record_items(call: dict) -> dict[str, dict]:
    items = {}
    for key in SECTION_KEYS:
        for row in call[key]:
            items[row["item_id"]] = {**row, "_section": key}
    return items


def _bullets(target: dict):
    """Yield (label, bullet) for chief complaint and every section bullet."""
    if target.get("chief_complaint"):
        yield "chief_complaint", target["chief_complaint"]
    for key in SECTION_KEYS:
        for i, b in enumerate(target.get(key) or []):
            yield f"{key}[{i}]", b


# ------------------------------------------------------------------------------------------- checks
def g1_structure(call, r: Report):
    s, t = call["setup"], call["target"]
    if s.get("scenario_category") not in CATEGORIES:
        r.err("G1", f"setup.scenario_category invalid: {s.get('scenario_category')}")
    if s.get("length_bucket") not in BUCKETS:
        r.err("G1", f"setup.length_bucket invalid: {s.get('length_bucket')}")
    ids = [row["item_id"] for k in SECTION_KEYS for row in call[k]] + [f["flag_id"] for f in call["risk_flags"]]
    if len(ids) != len(set(ids)):
        r.err("G1", "duplicate item_id / flag_id in record")
    for f in call["risk_flags"]:
        if f.get("risk_category") not in RISK:
            r.err("G1", f"record flag {f.get('flag_id')} invalid category {f.get('risk_category')}")
    na = t.get("not_applicable") or {}
    if "is_na" not in na:
        r.err("G1", "target.not_applicable.is_na missing")
    idn = t.get("identity") or {}
    for k in IDENTITY_IDS:
        f = idn.get(k)
        if not isinstance(f, dict) or f.get("certainty") not in {"stated", "unclear", "not_stated"}:
            r.err("G1", f"identity.{k} missing or bad certainty")
    if na.get("is_na"):
        return
    n_turns = len(call["turns"])
    for label, b in _bullets(t):
        keys = {"reason", "speaker", "turns", "quote", "explanation"} if label == "chief_complaint" else \
               {"text", "speaker", "turns", "quote", "explanation", "facts"}
        missing = keys - set(b)
        if missing:
            r.err("G1", f"{label}: missing keys {sorted(missing)}")
            continue
        if b["speaker"] not in ("Caller", "Nurse"):
            r.err("G1", f"{label}: speaker must be Caller|Nurse")
        if not b["turns"] or any(not isinstance(x, int) or not 1 <= x <= n_turns for x in b["turns"]):
            r.err("G1", f"{label}: bad turns {b['turns']}")
        for f in b.get("facts") or []:
            if f.get("type") not in FACT_TYPES:
                r.err("G1", f"{label}: bad fact type {f.get('type')}")
            if f.get("certainty") not in ("stated", "unclear"):
                r.err("G1", f"{label}: fact certainty must be stated|unclear ({f})")
            if f.get("type") == "action" and f.get("status") not in STATUS:
                r.err("G1", f"{label}: action status invalid ({f.get('status')})")
    for fl in t.get("risk_flags") or []:
        if fl.get("category") not in RISK:
            r.err("G1", f"gold flag category invalid: {fl.get('category')}")


def g_na(call, r: Report):
    is_na_rec = call["setup"].get("scenario_category") == "not_applicable"
    t = call["target"]
    is_na = bool((t.get("not_applicable") or {}).get("is_na"))
    if is_na_rec != is_na:
        r.err("G1", f"NA mismatch: record category={call['setup'].get('scenario_category')} gold is_na={is_na}")
    if is_na and any(t.get(k) for k in SECTION_KEYS):
        r.err("G1", "NA call must have empty sections")
    if is_na and t.get("risk_flags"):
        r.err("G9", "NA call must not carry risk flags")


def g2_quotes(call, r: Report):
    t = call["target"]
    by_id = {x["id"]: x for x in call["turns"]}
    if (t.get("not_applicable") or {}).get("is_na"):
        return
    for label, b in _bullets(t):
        if not b.get("turns"):
            continue
        joined = normalize(_turn_text(call, b["turns"]))
        if normalize(b["quote"]) not in joined:
            r.err("G2", f"{label}: quote not found in cited turns {b['turns']}: {b['quote'][:70]!r}")
        for tid in b["turns"]:
            tr = by_id.get(tid)
            if not tr:
                continue
            actual = tr["speaker"]
            if tr["label_error"]:
                actual = "Caller" if actual == "Nurse" else "Nurse"
            if actual != b["speaker"]:
                r.err("G2", f"{label}: turn {tid} is {actual}, bullet speaker is {b['speaker']}")
    for fl in t.get("risk_flags") or []:
        if normalize(fl.get("quote", "")) not in normalize(_turn_text(call, fl.get("turns") or [])):
            r.err("G2", f"risk flag {fl.get('category')}: quote not in turns {fl.get('turns')}")


def _evidence_turns(call, label, b) -> list[int]:
    covers = call["alignment"].get(label, [])
    ev = set(b.get("turns") or [])
    for fid in covers:
        ev |= set(_tagged_turns(call, fid))
    return sorted(ev)


def g3_numbers(call, r: Report):
    t = call["target"]
    if (t.get("not_applicable") or {}).get("is_na"):
        return
    for label, b in _bullets(t):
        ev = _evidence_turns(call, label, b)
        cands = number_candidates(_turn_text(call, ev))
        text = b.get("text") if label != "chief_complaint" else b.get("reason")
        for n in numbers_in(text or ""):
            if not supported(n, cands):
                r.err("G3", f"{label}: number {n} in text not supported by evidence turns {ev}")
        for f in b.get("facts") or []:
            for k in NUM_FIELDS:
                v = f.get(k)
                if v is None or isinstance(v, bool):
                    continue
                v = str(v)
                if v in cands:
                    continue
                for n in numbers_in(v):
                    if not supported(n, cands):
                        r.err("G3", f"{label}: fact {f.get('type')}.{k}={v} not supported by turns {ev}")


def _matching_items(call, label, pred) -> list[dict]:
    items = _record_items(call)
    return [items[i] for i in call["alignment"].get(label, []) if i in items and pred(items[i])]


def g4_g6_facts(call, r: Report):
    """G4 drug names, G5b symptom/medication fields, G6 action status + planned wording."""
    t = call["target"]
    if (t.get("not_applicable") or {}).get("is_na"):
        return
    for label, b in _bullets(t):
        if label == "chief_complaint":
            continue
        ev_text = normalize(_turn_text(call, _evidence_turns(call, label, b)))
        for f in b.get("facts") or []:
            ft = f.get("type")
            med = f.get("name") if ft == "medication" else f.get("medication") if ft == "action" else None
            if med:
                if normalize(med) not in ev_text:
                    r.err("G4", f"{label}: drug '{med}' not found in evidence turns")
            if ft == "medication":
                m = _matching_items(call, label, lambda it: _norm_val(it.get("medication_name_spoken")) == _norm_val(med))
                if not m:
                    r.err("G4", f"{label}: medication '{med}' does not match any covered record item's medication_name_spoken")
                    continue
                it = m[0]
                if f.get("certainty") != it.get("certainty", "stated"):
                    r.err("G4", f"{label}: '{med}' certainty {f.get('certainty')} != record {it.get('certainty')}")
                for k in MED_FIELDS:
                    if it.get(k) is not None and f.get(k) is not None and _norm_val(it[k]) != _norm_val(f[k]):
                        r.err("G5", f"{label}: '{med}'.{k} {f[k]!r} != record {it[k]!r}")
                    if it.get(k) is not None and f.get(k) is None:
                        r.err("G5", f"{label}: '{med}'.{k} missing in gold fact (record has {it[k]!r})")
            elif ft in ("symptom", "pertinent_negative"):
                m = _matching_items(call, label, lambda it: _norm_val(it.get("symptom_name")) == _norm_val(f.get("name")))
                if not m:
                    r.err("G5", f"{label}: symptom '{f.get('name')}' does not match a covered record item")
                    continue
                it = m[0]
                present = ft == "symptom" and f.get("present", True)
                if bool(it.get("symptom_present", True)) != bool(present):
                    r.err("G5", f"{label}: '{f.get('name')}' presence differs from record")
                if it.get("severity") is not None and _norm_val(it["severity"]) != _norm_val(f.get("severity")):
                    r.err("G5", f"{label}: '{f.get('name')}' severity {f.get('severity')!r} != record {it['severity']!r}")
                if f.get("certainty") != it.get("certainty", "stated"):
                    r.err("G5", f"{label}: '{f.get('name')}' certainty differs from record")
            elif ft == "action":
                m = _matching_items(call, label, lambda it: it.get("action_type") == f.get("action_type") and
                                    (not f.get("medication") or _norm_val(it.get("medication_name_spoken")) == _norm_val(f.get("medication"))))
                if not m:
                    r.err("G6", f"{label}: action {f.get('action_type')}/{f.get('medication')} does not match a covered record item")
                    continue
                if not any(it.get("action_status") == f.get("status") for it in m):
                    r.err("G6", f"{label}: action {f.get('action_type')} status {f.get('status')} != record {[it.get('action_status') for it in m]}")
            elif ft == "education":
                if not _matching_items(call, label, lambda it: it.get("education_type") == f.get("education_type")):
                    r.err("G6", f"{label}: education_type {f.get('education_type')} not in covered record items")
        statuses = {f.get("status") for f in b.get("facts") or [] if f.get("type") == "action"}
        if "planned" in statuses and not PLAN_MARKERS.search(b["text"]):
            r.err("G6", f"{label}: planned action but text lacks planned wording: {b['text'][:70]!r}")
        if statuses == {"completed"} and re.search(r"\bplanned\b", b["text"], re.I):
            r.err("G6", f"{label}: completed action worded as planned")


def g5_identity(call, r: Report):
    t, cc = call["target"], call["chief_complaint"]
    idn = t.get("identity") or {}
    rec = {
        "patient_name": (cc.get("patient_name_spoken"), cc.get("patient_name_certainty")),
        "patient_dob": (cc.get("patient_dob_spoken"), cc.get("patient_dob_certainty")),
        "caller_name": (cc.get("caller_name_spoken"), cc.get("caller_name_certainty")),
        "relationship": (cc.get("relationship_to_patient"), cc.get("relationship_certainty")),
        "callback_phone": (cc.get("callback_phone_spoken"), cc.get("callback_phone_certainty")),
    }
    for k, (val, cert) in rec.items():
        g = idn.get(k) or {}
        cert = cert or ("not_stated" if val is None else "stated")
        if _norm_val(g.get("value")) != _norm_val(val):
            r.err("G5", f"identity.{k} {g.get('value')!r} != record {val!r}")
        if g.get("certainty") != cert:
            r.err("G5", f"identity.{k} certainty {g.get('certainty')} != record {cert}")
        if val is None or k == "relationship" and val == "self":
            continue
        turns = g.get("turns") or []
        text = _turn_text(call, turns)
        if not turns:
            r.err("G5", f"identity.{k}: no turns cited")
            continue
        if k in ("patient_name", "caller_name"):
            hay = normalize(collapse_spelled(text)) + " " + normalize(text)
            for tok in normalize(val).split():
                if tok not in hay.split():
                    r.err("G5", f"identity.{k}: token '{tok}' not in cited turns {turns}")
        elif k == "patient_dob":
            y, m, d = val.split("-")
            c = number_candidates(text)
            for part in (y, str(int(m)), str(int(d))):
                if part not in c:
                    r.err("G5", f"identity.patient_dob: part {part} not derivable from turns {turns}")
        elif k == "callback_phone":
            if val not in number_candidates(text):
                r.err("G5", f"identity.callback_phone {val} not derivable from turns {turns}")
    if (idn.get("patient_pronoun") or None) != (cc.get("patient_pronoun") or None):
        r.err("G5", f"identity.patient_pronoun {idn.get('patient_pronoun')} != record {cc.get('patient_pronoun')}")


def g7_g8_coverage(call, r: Report):
    t = call["target"]
    if (t.get("not_applicable") or {}).get("is_na"):
        return
    items = _record_items(call)
    covered = set()
    for label, ids in call["alignment"].items():
        if not ids:
            r.err("G8", f"{label}: covers nothing")
        for i in ids:
            if i != "cc" and i not in items:
                r.err("G8", f"{label}: covers unknown fact id {i}")
            covered.add(i)
    for i in items:
        if i not in covered:
            r.err("G7", f"record item {i} ({items[i]['_section']}) not covered by any gold bullet")
    # G7b: every covered item must also appear as a typed fact (not only in prose)
    want_types = {"symptom": {"symptom"}, "pertinent_negative": {"pertinent_negative"}, "medication": {"medication"},
                  "vital": {"vital"}, "supply": {"supply", "medication"}, "history_context": {"context"},
                  "caller_concern": {"context"}}
    facts_by_item: dict[str, set] = defaultdict(set)
    for label, b in _bullets(t):
        types = {f.get("type") for f in b.get("facts") or []}
        for i in call["alignment"].get(label, []):
            facts_by_item[i] |= types
    cc_cov = set(call["alignment"].get("chief_complaint", []))
    for i, it in items.items():
        if i not in covered or i in cc_cov:
            continue
        exp = {"response": {"action"}, "education": {"education"}}.get(it["_section"]) or want_types.get(it.get("item_type"), set())
        if exp and not (facts_by_item[i] & exp):
            r.err("G7", f"record item {i} covered but no typed fact of {sorted(exp)} in its bullets")
    if "cc" not in call["alignment"].get("chief_complaint", []):
        r.err("G7", "chief complaint does not cover 'cc'")
    for label, ids in call["alignment"].items():
        sec = label.split("[")[0]
        for i in ids:
            if i in items and sec in SECTION_KEYS and items[i]["_section"] != sec:
                r.warn("G8", f"{label}: covers {i} from section {items[i]['_section']}")


def g9_flags(call, r: Report):
    want = {f["risk_category"] for f in call["risk_flags"] if f.get("flag_required", True)}
    got = {f.get("category") for f in call["target"].get("risk_flags") or []}
    if want != got:
        r.err("G9", f"risk flags gold {sorted(got)} != record {sorted(want)}")


def g10_tags(call, r: Report):
    items = _record_items(call)
    for i, it in items.items():
        tagged = _tagged_turns(call, i)
        if not tagged:
            r.err("G10", f"record item {i} not tagged on any turn")
            continue
        med = it.get("medication_name_spoken")
        if med and normalize(med) not in normalize(_turn_text(call, tagged)):
            r.err("G10", f"record item {i}: '{med}' not in its tagged turns {tagged}")
    for f in call["risk_flags"]:
        if not _tagged_turns(call, f["flag_id"]):
            r.err("G10", f"record flag {f['flag_id']} not tagged on any turn")
    if call["setup"].get("scenario_category") != "not_applicable" and not _tagged_turns(call, "cc"):
        r.err("G10", "no turn tagged 'cc'")
    cc = call["chief_complaint"]
    for k, field in [("patient_name", "patient_name_spoken"), ("patient_dob", "patient_dob_spoken"),
                     ("caller_name", "caller_name_spoken"), ("callback_phone", "callback_phone_spoken")]:
        if cc.get(field) and not _tagged_turns(call, k):
            r.err("G10", f"identity {k} has a value but no tagged turn")
    by_id = {t["id"]: t for t in call["turns"]}
    known = set(items) | {f["flag_id"] for f in call["risk_flags"]} | set(IDENTITY_IDS) | {"cc"}
    for t in call["turns"]:
        for fid in t["fact_ids"]:
            if fid not in known:
                r.err("G10", f"turn {t['id']}: unknown tag '{fid}'")
    for ev in call["noise_events"]:
        tr = by_id.get(ev.get("turn"))
        if not tr:
            r.err("G10", f"noise event on missing turn {ev.get('turn')}")
            continue
        forms = [x.strip() for x in str(ev.get("heard_form", "")).split("/") if x.strip()]
        if forms and not any(normalize(x) in normalize(collapse_spelled(tr["text"])) or normalize(x) in normalize(tr["text"]) for x in forms):
            r.err("G10", f"noise event turn {tr['id']}: heard_form {ev.get('heard_form')!r} not in turn text")
    if len(call["noise_events"]) != int(call["setup"].get("noise_event_count", len(call["noise_events"]))):
        r.warn("G10", "setup.noise_event_count differs from logged noise events")


def g11_untagged_drugs(call, r: Report):
    distract = {normalize(x) for x in call["setup"].get("distractor_meds") or []}
    med_tagged = set()
    items = _record_items(call)
    for t in call["turns"]:
        if any(i in items for i in t["fact_ids"]):
            med_tagged.add(t["id"])
    for t in call["turns"]:
        if t["id"] in med_tagged:
            continue
        words = " " + normalize(t["text"]) + " "
        for drug in FORMULARY:
            d = normalize(drug)
            if f" {d} " in words and d not in distract:
                r.warn("G11", f"turn {t['id']}: drug '{drug}' in a turn not tagged with any record item")


def g12_render_length(call, r: Report):
    try:
        render(call["target"], call["setup"].get("call_timestamp_utc"))
    except Exception as e:  # noqa: BLE001
        r.err("G12", f"render failed: {e!r}")
    n = len(call["transcript"])
    v2 = call["setup"].get("length_regime") == "v2"
    lo, hi = (BUCKETS_V2 if v2 else BUCKETS).get(call["setup"].get("length_bucket"), (0, 10**9))
    if call["setup"].get("scenario_category") == "not_applicable":
        lo = 150
    elif v2:
        lines = len([l for l in call["transcript"].splitlines() if l.strip()])
        need = MIN_LINES_V2.get(call["setup"].get("length_bucket"), 0)
        if lines < need:
            r.warn("G12", f"only {lines} transcript lines; v2 {call['setup'].get('length_bucket')} needs >= {need}")
    if not lo <= n <= hi:
        r.warn("G12", f"transcript {n} chars outside {call['setup'].get('length_bucket')} bucket {lo}-{hi}")


CHECKS = [g1_structure, g_na, g2_quotes, g3_numbers, g4_g6_facts, g5_identity, g7_g8_coverage, g9_flags,
          g10_tags, g11_untagged_drugs, g12_render_length]


def validate_call(call: dict) -> Report:
    r = Report(call["call_id"])
    for chk in CHECKS:
        try:
            chk(call, r)
        except Exception as e:  # noqa: BLE001
            r.err("CRASH", f"{chk.__name__}: {e!r}")
    return r


def global_checks(calls: list[dict]) -> list[str]:
    errs = []
    seen = defaultdict(set)
    for c in calls:
        cc = c["chief_complaint"]
        for k in ("patient_name_true", "patient_dob_true", "callback_phone_true"):
            v = cc.get(k)
            if v:
                seen[(k, str(v))].add((c["split"], c["call_id"]))
    for (k, v), where in seen.items():
        splits = {s for s, _ in where}
        if len(where) > 1:
            lvl = "ERROR" if len(splits) > 1 else "WARN"
            errs.append(f"{lvl} LEAK {k}={v} reused in {sorted(i for _, i in where)}")
    ids = [c["call_id"] for c in calls]
    if len(ids) != len(set(ids)):
        errs.append("ERROR DUP duplicate call_id")
    return errs


def main(argv: list[str]) -> int:
    splits = argv or ["train", "val"]
    calls = []
    for s in splits:
        if (AUTHORING / s).exists():
            calls += load_split(s)
    n_err = n_warn = 0
    by_code = defaultdict(int)
    for c in calls:
        rep = validate_call(c)
        for lvl, code, msg in rep.items:
            print(f"{lvl:5} {code:5} {c['call_id']}: {msg}")
            by_code[(lvl, code)] += 1
            n_err += lvl == "ERROR"
            n_warn += lvl == "WARN"
    real = [c for c in calls if c["split"] != "real5"]
    for line in global_checks(real):
        print(line)
        n_err += line.startswith("ERROR")
    print(f"\nvalidated {len(calls)} calls: {n_err} errors, {n_warn} warnings")
    for (lvl, code), n in sorted(by_code.items()):
        print(f"  {lvl} {code}: {n}")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
