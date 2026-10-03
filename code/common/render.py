"""Deterministic renderer: summary JSON -> exact reference text format.

Reference format (from synthetic_clinical_summary_examples.yaml):

    Chief Complaint
    [2000-01-01 14:41 UTC]
    Patient <name>, DOB MM/DD/YYYY. Patient's <rel>, <caller>, calling on <his|her> behalf, (ddd)-ddd-dddd. <reason>
      Caller: "<quote>"
      Explanation: <explanation>

    Assessment
    • <text>
      <Speaker>: "<quote>"
      Explanation: <explanation>
    ...
"""
from __future__ import annotations

from datetime import datetime

from .tallman import apply_tall_man

SECTIONS = [("assessment", "Assessment"), ("response", "Response"), ("education", "Education")]
EMPTY_SECTION = "• None documented during call."


def fmt_timestamp(iso: str | None) -> str:
    if not iso:
        return "[timestamp not provided]"
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return f"[{dt:%Y-%m-%d %H:%M} UTC]"


def fmt_dob(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{m}/{d}/{y}"


def fmt_phone(digits: str) -> str:
    if len(digits) == 10 and digits.isdigit():
        return f"({digits[:3]})-{digits[3:6]}-{digits[6:]}"
    return digits


def _heard(field: dict, fmt=lambda x: x) -> str:
    heard = [fmt(h) for h in field.get("heard_as") or []]
    return f" (unclear; heard as {' / '.join(heard)})" if heard else " (unclear)"


def identity_sentence(identity: dict) -> str:
    pn, dob = identity["patient_name"], identity["patient_dob"]
    cn, rel, ph = identity["caller_name"], identity["relationship"], identity["callback_phone"]
    pron = identity.get("patient_pronoun") or "their"

    # patient
    if pn.get("value"):
        name = pn["value"] + (_heard(pn) if pn.get("certainty") == "unclear" else "")
        s = f"Patient {name}"
    else:
        s = "Patient name not provided"
    if dob.get("value"):
        s += f", DOB {fmt_dob(dob['value'])}" + (_heard(dob, fmt_dob) if dob.get("certainty") == "unclear" else "")
    else:
        s += ", DOB not provided"

    # phone
    if ph.get("value"):
        phone = fmt_phone(ph["value"]) + (_heard(ph, fmt_phone) if ph.get("certainty") == "unclear" else "")
    else:
        phone = "callback number not provided"

    # caller
    if rel.get("value") == "self":
        return f"{s}, calling on own behalf, {phone}."
    if cn.get("value"):
        caller = cn["value"] + (_heard(cn) if cn.get("certainty") == "unclear" else "")
    else:
        caller = "name not provided"
    if rel.get("value"):
        rel_txt = rel["value"] + (" (unclear)" if rel.get("certainty") == "unclear" else "")
        return f"{s}. Patient's {rel_txt}, {caller}, calling on {pron} behalf, {phone}."
    return f"{s}. Caller {caller}, relationship not provided, calling on {pron} behalf, {phone}."


def _evidence(item: dict) -> list[str]:
    return [f'  {item["speaker"]}: "{item["quote"]}"', f"  Explanation: {apply_tall_man(item['explanation'])}"]


def render(summary: dict, call_timestamp_utc: str | None) -> str:
    na = summary.get("not_applicable") or {}
    if na.get("is_na"):
        return f"Not Applicable\n{fmt_timestamp(call_timestamp_utc)}\nReason: {na.get('reason') or 'Insufficient clinical content.'}\n"

    cc = summary["chief_complaint"]
    lines = [
        "Chief Complaint",
        fmt_timestamp(call_timestamp_utc),
        f"{identity_sentence(summary['identity'])} {apply_tall_man(cc['reason'])}",
        *_evidence(cc),
    ]
    for key, title in SECTIONS:
        lines += ["", title]
        items = summary.get(key) or []
        if not items:
            lines.append(EMPTY_SECTION)
        for it in items:
            lines.append(f"• {apply_tall_man(it['text'])}")
            lines += _evidence(it)
    return "\n".join(lines) + "\n"
