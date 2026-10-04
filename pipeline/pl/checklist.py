"""Reference checklist: one short sentence per fact-record item (symptom, medication, nurse action, instruction ...).

Used by the judge's completeness check when a fact record exists (the validation set). Same rendering as the one validated in llm_judge/.
"""
from __future__ import annotations

STATUS_FIX = {"ran": "ran out", "given_during_call": "given during the call"}


def words(s):
    return str(s).replace("_", " ")


def join(parts):
    return ", ".join(str(p) for p in parts if p not in (None, "", [], False))


def sentence(kind, it):
    if kind == "cc":
        return f"Reason for call: {it['reason_for_call']}" + (f" ({it['relevant_context']})" if it.get("relevant_context") else "")
    if kind == "assessment":
        t = it["item_type"]
        if t == "symptom":
            return "Symptom " + ("present" if it.get("symptom_present") else "absent") + ": " + join([it.get("symptom_name"), it.get("severity"), it.get("body_location"), it.get("onset_or_duration"), it.get("trend")])
        if t == "pertinent_negative":
            return "Pertinent negative: " + join([it.get("symptom_name"), it.get("history_or_context_text")])
        if t == "medication":
            name = it.get("medication_name_spoken") or it.get("medication_name_true")
            st = it.get("medication_status")
            return "Medication: " + join([name, it.get("strength"), join([it.get("dose"), it.get("unit")]).replace(", ", " "), it.get("route"), it.get("frequency"),
                                          "as needed" if it.get("prn") else None, f"status: {STATUS_FIX.get(st, st)}" if st else None,
                                          f"last dose: {it['last_dose']}" if it.get("last_dose") else None, it.get("history_or_context_text"),
                                          f"{it['supply_remaining']} {it.get('supply_unit') or ''} remaining" if it.get("supply_remaining") else None])
        if t == "vital":
            return f"Measurement: {it.get('vital_name')} {it.get('vital_value')}"
        if t == "supply":
            rem = it.get("supply_remaining")
            left = None if not rem else (f"none remaining ({it.get('supply_unit')})" if str(rem).lower() in ("none", "0") else f"{rem} {it.get('supply_unit') or ''} remaining".strip())
            return "Supply: " + join([it.get("supply_item"), left])
        return "Background: " + join([it.get("history_or_context_text"), it.get("caller_concern_text")])
    if kind == "response":
        return f"Nurse action ({it.get('action_status')}): " + join([words(it["action_type"]), it.get("recipient_or_target"), it.get("medication_name_spoken"), it.get("timeframe"),
                                                                     it.get("reason_or_trigger") and f"because {it['reason_or_trigger']}"])
    return f"Instruction given ({words(it['education_type'])}): " + join([it.get("instruction_content"), it.get("trigger_condition") and f"when: {it['trigger_condition']}"])


def checklist(record: dict) -> list[dict]:
    """fact record {chief_complaint, assessment, response, education} -> [{"n": 1, "fact": "..."}]"""
    items = [("cc", record["chief_complaint"])] + [(k, it) for k in ("assessment", "response", "education") for it in record.get(k) or []]
    return [{"n": n, "fact": sentence(k, it)} for n, (k, it) in enumerate(items, 1)]
