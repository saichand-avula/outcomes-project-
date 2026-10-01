"""Gold builder: (FactRecord, noisy tagged turns, noise events) -> gold JSON + rendered reference-style text. NO LLM.

* Noise events are folded into the facts: a drug-confusion event makes the medication name unrecoverable
  (name=None, name_as_heard=<what the transcript says>, certainty='unclear'; policy P1); a name-drift event adds the
  variant to IdField.alternates while the self-stated value stays the value (policy P2).
* Evidence = the turns that carry each fact (tags set by the voicer). Quotes are verbatim sentences of those turns,
  so the plan's V3 (quote-in-source, same speaker) holds BY CONSTRUCTION; validate_gold.py re-checks it independently.
* Output schema is the plan's Section 2 schema. `gold_full` keeps fact ids (for scoring); `to_target` strips them (SFT target).
"""
from __future__ import annotations
import re

import lexicons as L
import risk_rules as RR
import spoken as SP
from schema import FactRecord, Medication
from transcript_utils import Turn

FORM = {d["generic"]: d for d in L.FORMULARY}
SENT = re.compile(r"(?<=[.?!])\s+")
NA_REASON = {"wrong_number": "Caller reached the wrong number; no clinical content.",
             "hang_up": "Call disconnected or silent; no clinical content.",
             "billing_admin_only": "Administrative/billing call; no clinical content.",
             "test_call": "Test call; no clinical content."}
CTX_TEXT = {"caller asks for a nurse to come out now": "Caller requested a nurse visit now.",
            "caller asks to be sent to the hospital": "Caller requested that the patient be sent to the hospital.",
            "caller asks to speak to the doctor today": "Caller requested to speak to the doctor today."}
NEG_TEXT = {"nausea": "nausea", "difficulty breathing": "trouble breathing", "confusion": "confusion", "fever": "fever", "falls": "falls"}
ACT_PLANNED = {"refill_request": "submit a refill request for {x}", "team_message": "send a message to the care team",
               "nurse_visit": "arrange a nurse visit", "callback": "arrange a callback", "physician_notification": "notify the physician",
               "documentation": "document the call", "appointment_scheduling": "have the team schedule an appointment",
               "medication_order": "ask the physician to order {x}", "referral": "advise in-person evaluation"}
ACT_DONE = {"refill_request": "a refill request for {x} was submitted", "team_message": "a message was sent to the care team",
            "nurse_visit": "a nurse visit request was placed", "callback": "the on-call nurse was called",
            "physician_notification": "the physician was called", "documentation": "the call was documented",
            "appointment_scheduling": "an appointment request was submitted"}
EXPL = {"symptom": "Documents a caller-reported symptom.", "negative": "Documents a pertinent negative reported by the caller.",
        "med_caller": "Documents the caller-reported medication details.", "med_nurse": "Documents medication guidance stated by the nurse.",
        "med_unclear": "Documents a medication detail the caller or transcript left unclear.", "supply": "Documents the reported supply status and request.",
        "context": "Documents additional caller-reported context.", "planned": "Documents an action the nurse stated is planned, not yet completed.",
        "completed": "Documents an action the nurse stated was completed.", "advised": "Documents the nurse's recommendation.",
        "education": "Documents guidance communicated to the caller.", "cc": "Documents caller, patient, relationship and the reason for the call."}


def cap(s: str) -> str: return s[:1].upper() + s[1:]


def display_name(m: Medication) -> str:
    return FORM[m.name]["tall_man"] if m.name in FORM else (m.name or "")


def med_desc(m: Medication) -> str:
    parts = [display_name(m) if m.name else f"a medication heard as '{m.name_as_heard}'"]
    d = SP.dose_str(m.dose, m.unit)
    if d: parts.append(d)
    if m.route: parts.append(SP.ROUTE_SPOKEN[m.route][0])
    if m.frequency: parts.append(SP.FREQ_SPOKEN[m.frequency][0])
    return " ".join(parts)


# ----------------------------------------------------------------------------- events -> facts
def apply_events(rec: FactRecord, events: list[dict]) -> FactRecord:
    rec = rec.model_copy(deep=True)
    meds = {m.id: m for m in rec.medications}
    for e in events:
        if e["kind"] == "drug_confusion" and e["fact_id"] in meds:
            m = meds[e["fact_id"]]
            m.name_as_heard, m.name, m.certainty = e["heard"], None, "unclear"
            m.note = f"policy P1: transcript says '{e['heard']}' for a drug whose name is not recoverable"
        elif e["kind"] == "name_drift":
            fld = getattr(rec.identity, e["field"])
            if e["variant"] not in fld.alternates:
                fld.alternates.append(e["variant"])
    return rec


def tag_map(turns: list[Turn]) -> dict[str, list[int]]:
    m: dict[str, list[int]] = {}
    for t in turns:
        for f in t.fact_ids:
            m.setdefault(f, []).append(t.id)
    return m


ACK_ONLY = {"okay", "all right", "alright", "thank you", "okay thank you", "okay great", "perfect", "great", "okay okay", "sure",
            "okay great thank you", "yes", "right", "uh huh", "mhm"}


def _plain(s: str) -> str:
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def _score(sentence: str, keys: set[str]) -> tuple:
    w = re.findall(r"[a-z]{4,}", sentence.lower())
    return (len(keys & set(w)), len(sentence.split()))          # key overlap first, then the more substantive (longer) sentence


def best_sentence(text: str, key_text: str, max_words: int = 40) -> str:
    """A verbatim sentence of `text`. Pure acknowledgments ("Okay, thank you.") are never chosen when anything else exists:
    fragmentation often splits the real instruction away from the nurse's leading ack (audit: 15% of bullets quoted an ack)."""
    keys = set(re.findall(r"[a-z]{4,}", key_text.lower()))
    sents = [s for s in SENT.split(text) if len(s.split()) >= 2] or [text]
    sents = [s for s in sents if _plain(s) not in ACK_ONLY] or sents
    best = max(enumerate(sents), key=lambda p: (*_score(p[1], keys), -p[0]))[1]
    w = best.split()
    return " ".join(w[:max_words]) if len(w) > max_words else best


def grounded(turns: list[Turn], tags: dict[str, list[int]], fid: str, speaker: str, key_text: str, max_turns: int = 6):
    ids = tags.get(fid, [])
    if fid[0] in "SNMUX":       # a symptom/med/supply/context fact is evidenced by its own turns, not by education/action turns that restate it
        own = [i for i in ids if not any(t[0] in "EA" for t in turns[i - 1].fact_ids)]
        ids = own or ids
    pri = [i for i in ids if turns[i - 1].speaker == speaker] or ids
    pri = pri[:max_turns]
    if not pri:
        return [], None, None
    scored = []
    keys = set(re.findall(r"[a-z]{4,}", key_text.lower()))
    for i in pri:
        q = best_sentence(turns[i - 1].text, key_text)
        scored.append((*_score(q, keys), -i, i, q))
    qi, quote = max(scored)[-2:]
    pri = [qi] + [i for i in pri if i != qi]
    return pri, turns[qi - 1].speaker, quote


# ----------------------------------------------------------------------------- bullet text
def sym_text(s) -> str:
    base = s.name + (f" in {', '.join(s.location)}" if s.location else "")
    if s.certainty == "unclear":
        return f"Caller reported possible {base}; caller expressed uncertainty (unclear)."
    return f"Caller reported {base}" + (f" ({s.severity})" if s.severity else "") + (f", {s.onset_duration}" if s.onset_duration else "") + "."


def med_text(m: Medication) -> tuple[str, str]:
    d = med_desc(m)
    if m.name is None:
        return f"Caller reported {d} (unclear: name not recoverable from the transcript; possible mishearing).", "med_unclear"
    if m.certainty == "unclear":
        return f"Caller reported {d} (unclear: caller was not sure of the details).", "med_unclear"
    if m.status == "administered":
        last = f", last dose {m.last_dose}" if m.last_dose else ""
        return f"Caller reported giving {display_name(m)} {SP.dose_str(m.dose, m.unit)} {SP.ROUTE_SPOKEN[m.route][0]}{last}; ordered {SP.FREQ_SPOKEN[m.frequency][0]}.", "med_caller"
    if m.status == "ordered":
        return f"Nurse stated {d} is ordered.", "med_nurse"
    if m.status == "advised":
        return f"Nurse advised {d}.", "med_nurse"
    return f"Caller reported the patient takes {d}.", "med_caller"


def build_gold(rec0: FactRecord, turns: list[Turn], events: list[dict]) -> dict:
    rec = apply_events(rec0, events)
    tags = tag_map(turns)
    out = dict(record_id=rec.record_id, split=rec.split, category=rec.category, subtype=rec.subtype,
               not_applicable=rec.not_applicable, na_reason=NA_REASON.get(rec.na_subtype) if rec.not_applicable else None,
               identity={}, chief_complaint=None, bullets=[], risk_flags=[], noise_events_applied=[e["kind"] for e in events
                                                                                                  if e["kind"] in ("drug_confusion", "name_drift")])
    # identity
    for f in ("patient_name", "patient_dob", "callback_phone", "caller_name", "relationship"):
        fld = getattr(rec.identity, f)
        ids, _, _ = grounded(turns, tags, f"ID.{f}", "Caller", fld.value or "")
        out["identity"][f] = dict(value=fld.value, status=fld.status, alternates=list(fld.alternates), turn_ids=ids)
    if rec.not_applicable:
        return out

    def add(fid, section, text, speaker_hint, key, expl, facts, kind):
        ids, spk, quote = grounded(turns, tags, fid, speaker_hint, key + " " + text)
        out["bullets"].append(dict(fact_id=fid, kind=kind, section=section, text=text, speaker=spk, turn_ids=ids, quote=quote,
                                   explanation=expl, facts=facts))

    for s in rec.symptoms:
        add(s.id, "Assessment", sym_text(s), "Caller", s.name, EXPL["symptom"],
            [dict(type="symptom", name=s.name, severity=s.severity, certainty=s.certainty)], "symptom")
    for n in rec.pertinent_negatives:
        add(n.id, "Assessment", f"Caller denied {NEG_TEXT[n.name]}.", "Caller", NEG_TEXT[n.name], EXPL["negative"],
            [dict(type="negative", name=n.name)], "negative")
    for m in rec.medications:
        txt, ex = med_text(m)
        section = "Response" if m.status in ("ordered", "advised") and m.certainty == "stated" and m.name else "Assessment"
        spk = "Nurse" if section == "Response" else "Caller"
        key = " ".join(x for x in (m.name, m.name_as_heard, *(FORM[m.name]["aliases"] if m.name in FORM else [])) if x)
        add(m.id, section, txt, spk, key, EXPL[ex],
            [dict(type="medication", name=m.name, name_as_heard=m.name_as_heard, dose=m.dose, unit=m.unit, route=m.route,
                  frequency=m.frequency, status=m.status, certainty=m.certainty)], "medication")
    for u in rec.supplies:
        if u.request == "equipment":
            txt = f"Caller requested delivery of {u.item}."
        else:
            txt = f"Caller reported {u.quantity_remaining} of {u.item} remaining and requested {'delivery' if u.request == 'delivery' else 'a refill'}."
        add(u.id, "Assessment", txt, "Caller", u.item, EXPL["supply"],
            [dict(type="supply", item=u.item, quantity_remaining=u.quantity_remaining, request=u.request, certainty=u.certainty)], "supply")
    for x in rec.context:
        txt = CTX_TEXT.get(x.text) or "Caller reported a " + x.text + "."
        add(x.id, "Assessment", txt, "Caller", x.text, EXPL["context"], [dict(type="context", kind=x.kind, text=x.text)], "context")
    ref_meds = [m for m in rec.medications if any(u.item == (m.name or "") for u in rec.supplies)] or rec.medications[:1]
    xs = ", ".join(display_name(m) for m in ref_meds if m.name) or "the medication"
    for a in rec.actions:
        if a.status == "advised":
            txt = "Nurse recommended calling 911 and going to the emergency department." if a.type == "escalation_911_ed" else "Nurse advised in-person evaluation."
            ex = "advised"
        elif a.status == "planned":
            txt, ex = f"Nurse stated planned to {ACT_PLANNED[a.type].format(x=xs)}.", "planned"
        else:
            txt, ex = f"Nurse stated {ACT_DONE[a.type].format(x=xs)}.", "completed"
        add(a.id, "Response", txt, "Nurse", a.type.replace("_", " "), EXPL[ex],
            [dict(type="action", action_type=a.type, status=a.status)], "action")
    for e in rec.education:
        ids, spk, quote = grounded(turns, tags, e.id, "Nurse", e.type.replace("_", " "))
        sent = re.sub(r"^(Okay, thank you|Okay, great|All right|Alright|Okay|Thank you|Perfect)[.,]?\s+", "", quote or "")
        out["bullets"].append(dict(fact_id=e.id, kind="education", section="Education", text=f"Nurse advised the caller: {sent}", speaker=spk,
                                   turn_ids=ids, quote=quote, explanation=EXPL["education"],
                                   facts=[dict(type="education", education_type=e.type)]))
    # chief complaint
    I = rec.identity
    dob = I.patient_dob.value; dob_us = f"{dob[5:7]}/{dob[8:10]}/{dob[:4]}" if dob else "not stated"
    ph = I.callback_phone.value; ph_f = f"({ph[:3]})-{ph[3:6]}-{ph[6:]}" if ph else "not stated"
    alt = lambda fld: (f" (also heard as {', '.join(fld.alternates)})" if fld.alternates else "")
    if I.relationship.value == "patient (self)":
        who = f"Patient {I.patient_name.value}{alt(I.patient_name)}, DOB {dob_us}, calling for self, {ph_f}."
    else:
        rel = "calling from the patient's facility (nurse)" if I.relationship.value == "facility nurse" else f"the patient's {I.relationship.value}, calling on the patient's behalf"
        who = (f"Patient {I.patient_name.value}{alt(I.patient_name)}, DOB {dob_us}. Caller {I.caller_name.value}{alt(I.caller_name)}, "
               f"{rel}, {ph_f}.")
    syms = [s for s in rec.symptoms if s.certainty == "stated"] or rec.symptoms
    if rec.category == "high_risk":
        sub = rec.subtype
        if sub == "uncontrolled_symptom":
            reason = "Reported uncontrolled pain not relieved by the last dose."
        elif sub == "medication_concern":
            reason = f"Reported a medication problem ({rec.context[0].text.split(': ')[-1]})."
        elif sub == "suicidal_statement":
            reason = f"Reported a statement of wanting to die ({rec.symptoms[0].name.split('by ')[-1].rstrip(')')})."
        elif sub == "breathing_concern":
            reason = "Reported trouble breathing."
        else:
            reason = CTX_TEXT.get(rec.context[0].text, "Reported an urgent request.") if rec.context else "Reported an urgent request."
    elif rec.category in ("medication", "asr_error"):
        m = rec.medications[0]
        reason = f"Called with a question regarding {display_name(m) if m.name else 'a medication (name unclear)'}."
    elif rec.category == "supply":
        reason = "Requested " + " and ".join(("delivery" if u.request == "delivery" else "a refill" if u.request == "refill" else "delivery") +
                                              f" of {u.item}" for u in rec.supplies) + "."
    else:
        reason = "Reported " + " and ".join(s.name for s in syms[:2]) + "."
    first_non_id = next((t for t in turns if t.speaker == "Caller" and any(not f.startswith("ID.") for f in t.fact_ids)), None)
    cq = best_sentence(first_non_id.text, reason) if first_non_id else None
    out["chief_complaint"] = dict(text=f"{who} {reason}", speaker="Caller", turn_ids=[first_non_id.id] if first_non_id else [],
                                  quote=cq, explanation=EXPL["cc"])
    # risk flags: grounded in the tagged trigger turn, else in the first rule hit for the category
    scan = RR.scan_turns(turns)
    for r in rec.risk_flags:
        ids = tags.get(r.id) or (scan.get(r.category) or [])[:1]
        quote = None
        if ids:
            t = turns[ids[0] - 1]
            phrases = {ph for c, ph in RR.scan_text(t.text) if c == r.category}
            quote = next((s for s in SENT.split(t.text) if any(p in " ".join(RR.tokens(s)) for p in phrases)), best_sentence(t.text, r.rationale))
        out["risk_flags"].append(dict(fact_id=r.id, category=r.category, required=r.required, turn_ids=ids, quote=quote))
    return out


# ----------------------------------------------------------------------------- SFT target + text rendering
def to_target(g: dict) -> dict:
    """The model-facing target (plan Section 2 schema): no fact ids, no split labels, no bookkeeping."""
    if g["not_applicable"]:
        return dict(not_applicable=True, na_reason=g["na_reason"], identity={}, chief_complaint=None, bullets=[], risk_flags=[])
    return dict(not_applicable=False, na_reason=None,
                identity={k: dict(value=v["value"], status=v["status"], alternates=v["alternates"], turn_ids=v["turn_ids"]) for k, v in g["identity"].items()},
                chief_complaint=g["chief_complaint"],
                bullets=[{k: b[k] for k in ("section", "text", "speaker", "turn_ids", "quote", "explanation", "facts")} for b in g["bullets"]],
                risk_flags=[dict(category=r["category"], turn_ids=r["turn_ids"], quote=r["quote"]) for r in g["risk_flags"]])


def render_summary(t: dict, call_ts: str = "2000-01-01T14:41:00Z") -> str:
    """Reference-style text (matches the layout of the provided examples)."""
    if t["not_applicable"]:
        return "Not Applicable"
    ts = call_ts[:10] + " " + call_ts[11:16] + " UTC"
    cc = t["chief_complaint"]
    lines = ["Chief Complaint", f"[{ts}]", cc["text"], f'  {cc["speaker"]}: "{cc["quote"]}"', f'  Explanation: {cc["explanation"]}']
    for sec in ("Assessment", "Response", "Education"):
        lines += ["", sec]
        bs = [b for b in t["bullets"] if b["section"] == sec]
        if not bs:
            lines.append("• None documented during call.")
        for b in bs:
            lines += [f"• {b['text']}", f'  {b["speaker"]}: "{b["quote"]}"', f'  Explanation: {b["explanation"]}']
    if t["risk_flags"]:
        lines += ["", "Flags for nurse review"]
        lines += [f'• {r["category"].replace("_", " ")}' + (f' — "{r["quote"]}"' if r["quote"] else "") for r in t["risk_flags"]]
    return "\n".join(lines)
