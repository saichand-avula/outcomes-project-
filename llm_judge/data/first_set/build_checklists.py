"""Build the completeness reference for each golden item from the call's fact record (Mac only; needs the project).

Completeness is judged against the fact record: every record item must appear in the summary.
Writes:
  completeness_reference.jsonl  what the judge sees: id + numbered checklist sentences (same list for edited and clean)
  golden_completeness.jsonl     answers: which checklist numbers were removed from the summary (empty for clean items)
Run: python3 llm_judge/build_checklists.py   (reads golden_labels.jsonl; does not change it)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code"))
from common.loader import load_split  # noqa: E402

OUT = Path(__file__).resolve().parent
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


def main():
    labels = [json.loads(l) for l in (OUT / "golden_labels.jsonl").read_text().splitlines() if l.strip()]
    calls = {c["call_id"]: c for c in load_split("val")}
    ref, gold = [], []
    for lab in labels:
        c = calls[lab["call_id"]]
        items = [("cc", "cc", c["chief_complaint"])] + [(k, it["item_id"], it) for k in ("assessment", "response", "education") for it in c[k]]
        numbered = [{"n": n, "item_id": iid, "sentence": sentence(k, it)} for n, (k, iid, it) in enumerate(items, 1)]
        removed_ids = set()
        for w in lab["what_changed"]:
            m = re.match(r'Removed the (assessment|response|education) item: "(.*)"$', w)
            if m:
                sec, text = m.groups()
                for i, b in enumerate(c["target"][sec]):
                    if b["text"] == text:
                        removed_ids |= set(c["alignment"][f"{sec}[{i}]"])
        missing = [x for x in numbered if x["item_id"] in removed_ids]
        ref.append({"id": lab["id"], "items": [{"n": x["n"], "fact": x["sentence"]} for x in numbered]})
        gold.append({"id": lab["id"], "call_id": lab["call_id"], "missing_numbers": [x["n"] for x in missing],
                     "missing_facts": [x["sentence"] for x in missing], "n_items": len(numbered),
                     "expected_completeness": "FAIL" if missing else "PASS"})
    for name, rows in (("completeness_reference.jsonl", ref), ("golden_completeness.jsonl", gold)):
        (OUT / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    bad = [g["id"] for g, l in zip(gold, labels) if g["expected_completeness"] != l["expected"]["completeness"]]
    print(f"{len(ref)} items; checklist length min/median/max =",
          sorted(len(r['items']) for r in ref)[0], sorted(len(r['items']) for r in ref)[len(ref) // 2], sorted(len(r['items']) for r in ref)[-1])
    print("edited items with a removed checklist item:", sum(bool(g["missing_numbers"]) for g in gold), "| label mismatches vs golden_labels:", bad)


if __name__ == "__main__":
    main()
