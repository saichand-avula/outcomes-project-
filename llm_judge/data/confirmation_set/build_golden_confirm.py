"""Build the CONFIRMATION set: validation calls not used in the first judge set (llm_judge/), 20 clean and 20 edited.

Edits are applied to the gold summary JSON, then rendered with the project renderer, so the edited
summary has the exact reference format. Each edit is tagged with the rubric(s) it should break:
  completeness  - a clinically relevant item is missing
  faithfulness  - a statement is wrong or not supported by the transcript
  calibration   - status, hedging or speaker attribution is misstated
Clean summaries are the validated gold summaries and should PASS all three rubrics.

Run (on the Mac, from the project root): python3 llm_judge/data/confirmation_set/build_golden_confirm.py
Writes: judge_inputs.jsonl (what the judge sees), golden_labels.jsonl (answers), golden_review.xlsx.
"""
from __future__ import annotations

import copy
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code"))
from common.loader import load_split  # noqa: E402
from common.render import render  # noqa: E402

OUT = Path(__file__).resolve().parent
SEED, N_TOTAL, N_EDITED = 23, 40, 20
SECTIONS = ("assessment", "response", "education")
RUBRIC_OF = {"drop_assessment": "completeness", "drop_education": "completeness", "drop_response": "completeness",
             "wrong_number": "faithfulness", "fabricated_finding": "faithfulness", "flipped_negative": "faithfulness",
             "wrong_drug": "faithfulness", "planned_to_completed": "calibration", "speaker_swap": "calibration",
             "hedge_removed": "calibration"}
# 25 edited calls: 7 completeness, 8 faithfulness, 6 calibration, 2 comp+faith, 2 faith+calib
PLAN = (["drop_assessment"] * 2 + ["drop_education"] * 2 + ["drop_response"]
        + ["wrong_number"] * 3 + ["fabricated_finding"] * 2 + ["flipped_negative"] + ["wrong_drug"] * 2
        + ["planned_to_completed"] * 2 + ["speaker_swap"] * 2 + ["hedge_removed"]
        + [("drop_education", "wrong_drug"), ("wrong_number", "speaker_swap")])
FALLBACK = {"hedge_removed": "planned_to_completed", "flipped_negative": "wrong_number"}
FABRICATIONS = [("fever", "A fever of 101.5 was reported.", "He also had a fever of one oh one point five last night."),
                ("fall", "A fall the previous evening was reported.", "She also fell in the bathroom last evening."),
                ("chest", "New chest pain was reported.", "He's also had some chest pain since this morning."),
                ("rash", "A new rash on the arms was reported.", "She has a new rash all over her arms."),
                ("seizure", "A seizure earlier in the day was reported.", "He had a seizure this afternoon.")]
OTHER_DRUGS = ["lisinopril", "warfarin", "prednisone", "furosemide", "sertraline", "amoxicillin"]
HEDGE_CLAUSE = re.compile(r"[,;]\s[^,;.]*\b(unclear|unsure|not sure|uncertain|unknown)\b[^.]*(?=\.)", re.I)
NUM = re.compile(r"(?<![\d.])\d+(?![\d.]|:\d)")


def good_numbers(txt):
    return [m for m in NUM.finditer(txt) if int(m.group()) > 1 and not re.fullmatch(r"(19|20)\d\d", m.group())]


def new_number(txt, m):
    v, after = int(m.group()), txt[m.end():m.end() + 12].lower()
    if after.startswith("/10"):
        return v - 3 if v >= 5 else v + 3
    if after.startswith(" percent") or after.startswith("%"):
        return v - 10
    return v * 2 if v < 50 else v + 50


def bullets(t, section):
    return t.get(section) or []


def has_med_fact(b):
    return any(f.get("type") == "medication" and f.get("name") for f in b.get("facts", []))


def candidates(t, kind, touched, transcript):
    """Indices (section, i) where `kind` can be applied cleanly."""
    out = []
    low = transcript.lower()
    for sec in SECTIONS:
        items = bullets(t, sec)
        for i, b in enumerate(items):
            if (sec, i) in touched:
                continue
            txt = b["text"]
            if kind == "drop_assessment" and sec == "assessment" and len(items) >= 3 and any(f.get("type") in ("symptom", "medication", "pertinent_negative", "vital") for f in b.get("facts", [])):
                out.append((sec, i))
            elif kind == "drop_education" and sec == "education" and len(items) >= 2:
                out.append((sec, i))
            elif kind == "drop_response" and sec == "response" and len(items) >= 2:
                out.append((sec, i))
            elif kind == "wrong_number" and sec != "education" and good_numbers(txt):
                out.append((sec, i))
            elif kind == "wrong_drug" and sec in ("assessment", "response") and any(f.get("name") and f["name"].lower() in txt.lower() for f in b.get("facts", []) if f.get("type") == "medication"):
                out.append((sec, i))
            elif kind == "flipped_negative" and sec == "assessment" and any(f.get("type") == "pertinent_negative" and f.get("name") for f in b.get("facts", [])):
                out.append((sec, i))
            elif kind == "planned_to_completed" and sec == "response" and txt.startswith("Planned to "):
                out.append((sec, i))
            elif kind == "speaker_swap" and sec == "assessment" and b["speaker"] == "Caller":
                out.append((sec, i))
            elif kind == "hedge_removed" and sec == "assessment" and HEDGE_CLAUSE.search(txt) and any(f.get("certainty") == "unclear" for f in b.get("facts", [])):
                out.append((sec, i))
    if kind == "fabricated_finding" and any(k not in low for k, _, _ in FABRICATIONS):
        out.append(("assessment", -1))
    return out


def apply(t, kind, loc, rng, transcript):
    sec, i = loc
    if kind.startswith("drop_"):
        b = bullets(t, sec).pop(i)
        return f"Removed the {sec} item: \"{b['text']}\"", None
    if kind == "fabricated_finding":
        key, text, quote = rng.choice([f for f in FABRICATIONS if f[0] not in transcript.lower()])
        t["assessment"].append({"text": text, "speaker": "Caller", "turns": [], "quote": quote,
                                "explanation": "Documents an additional reported symptom.", "facts": []})
        return f"Added an assessment item that is not in the call: \"{text}\"", ("assessment", len(t["assessment"]) - 1)
    b = bullets(t, sec)[i]
    old = b["text"]
    if kind == "wrong_number":
        m = rng.choice(good_numbers(old))
        b["text"] = old[:m.start()] + str(new_number(old, m)) + old[m.end():]
    elif kind == "wrong_drug":
        name = next(f["name"] for f in b["facts"] if f.get("type") == "medication" and f.get("name") and f["name"].lower() in old.lower())
        repl = rng.choice([d for d in OTHER_DRUGS if d not in transcript.lower()])
        hit = re.search(re.escape(name), old, flags=re.I)
        repl = repl.capitalize() if hit.start() == 0 else repl
        b["text"] = old[:hit.start()] + repl + old[hit.end():]
    elif kind == "flipped_negative":
        name = next(f["name"] for f in b["facts"] if f.get("type") == "pertinent_negative" and f.get("name"))
        b["text"] = f"{name[0].upper()}{name[1:]} was reported."
    elif kind == "planned_to_completed":
        b["text"] = "Completed: " + old[len("Planned to "):]
    elif kind == "speaker_swap":
        b["speaker"] = "Nurse"
    elif kind == "hedge_removed":
        b["text"] = HEDGE_CLAUSE.sub("", old, count=1)
    return f"Changed {sec} item: \"{old}\" -> \"{b['text']}\"" if kind != "speaker_swap" else \
        f"Changed the speaker label on \"{old}\" from Caller to Nurse", (sec, i)


def main() -> int:
    rng = random.Random(SEED)
    old_ids = {json.loads(l)["call_id"] for l in (OUT.parent / "first_set" / "golden_labels.jsonl").read_text().splitlines() if l.strip()}
    calls = [c for c in load_split("val") if not c["target"]["not_applicable"]["is_na"] and c["call_id"] not in old_ids]
    assert len(calls) >= N_TOTAL, len(calls)
    sample = rng.sample(calls, N_TOTAL)
    assert len(PLAN) == N_EDITED
    used, edits = set(), {}
    for plan in list(PLAN):
        kinds = (plan,) if isinstance(plan, str) else plan
        for c in sample:
            if c["call_id"] in used:
                continue
            t, touched, log, ok = copy.deepcopy(c["target"]), set(), [], True
            for kind in kinds:
                cand = candidates(t, kind, touched, c["transcript"])
                if not cand:
                    ok = False
                    break
                loc = rng.choice(cand)
                desc, new_loc = apply(t, kind, loc, rng, c["transcript"])
                log.append((kind, desc))
                if kind.startswith("drop_"):
                    touched = {(s, j - (1 if s == loc[0] and j > loc[1] else 0)) for s, j in touched}
                elif new_loc:
                    touched.add(new_loc)
            if ok:
                used.add(c["call_id"])
                edits[c["call_id"]] = (t, log)
                break
        else:
            if isinstance(plan, str) and plan in FALLBACK:
                PLAN.append(FALLBACK[plan])
                print(f"note: no call fits {plan}; using {FALLBACK[plan]} instead")
                continue
            raise SystemExit(f"no call fits edit plan {plan}")
    order = list(range(len(sample)))
    rng.shuffle(order)
    inputs, labels = [], []
    for n, k in enumerate(order, start=1):
        c = sample[k]
        jid = f"k-{n:03d}"
        ts = c["setup"]["call_timestamp_utc"]
        clean_text = render(c["target"], ts)
        if c["call_id"] in edits:
            t, log = edits[c["call_id"]]
            summary, broken = render(t, ts), sorted({RUBRIC_OF[kd] for kd, _ in log})
        else:
            summary, log, broken = clean_text, [], []
        expected = {r: ("FAIL" if r in broken else "PASS") for r in ("faithfulness", "completeness", "calibration")}
        inputs.append({"id": jid, "transcript": c["transcript"], "summary": summary})
        labels.append({"id": jid, "call_id": c["call_id"], "edited": bool(log), "rubrics_broken": broken, "expected": expected,
                       "edit_types": [kd for kd, _ in log], "what_changed": [d for _, d in log],
                       "original_summary": clean_text, "length_bucket": c["setup"]["length_bucket"],
                       "category": c["setup"]["scenario_category"]})
    for name, rows in (("judge_inputs.jsonl", inputs), ("golden_labels.jsonl", labels)):
        (OUT / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    write_xlsx(labels, inputs)
    ed = [r for r in labels if r["edited"]]
    from collections import Counter
    print(f"{len(labels)} items: {len(ed)} edited, {len(labels) - len(ed)} clean")
    print("rubric FAIL counts:", dict(Counter(r for x in ed for r in x["rubrics_broken"])))
    print("edit types:", dict(Counter(k for x in ed for k in x["edit_types"])))
    return 0


def write_xlsx(labels, inputs):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Golden labels"
    ws.append(["Judge id", "Source call", "Edited?", "Edit type(s)", "What changed", "Faithfulness", "Completeness", "Calibration", "Length", "Category"])
    for r in labels:
        ws.append([r["id"], r["call_id"], "EDITED" if r["edited"] else "clean", ", ".join(r["edit_types"]), "\n".join(r["what_changed"]),
                   r["expected"]["faithfulness"], r["expected"]["completeness"], r["expected"]["calibration"], r["length_bucket"], r["category"]])
        if r["edited"]:
            ws.cell(ws.max_row, 3).fill = PatternFill("solid", fgColor="FCE4D6")
        for col in (6, 7, 8):
            if ws.cell(ws.max_row, col).value == "FAIL":
                ws.cell(ws.max_row, col).fill = PatternFill("solid", fgColor="F8CBAD")
    for c in ws[1]:
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3864")
    for col, w in zip("ABCDEFGHIJ", (9, 11, 9, 28, 90, 13, 13, 12, 9, 15)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "B2"
    ws2 = wb.create_sheet("Summaries shown to judge")
    ws2.append(["Judge id", "Edited?", "Summary the judge sees", "Original summary (edited items only)"])
    by = {r["id"]: r for r in labels}
    for i in inputs:
        r = by[i["id"]]
        ws2.append([i["id"], "EDITED" if r["edited"] else "clean", i["summary"], r["original_summary"] if r["edited"] else ""])
    for c in ws2[1]:
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3864")
    for col, w in zip("ABCD", (9, 9, 90, 90)):
        ws2.column_dimensions[col].width = w
    for row in ws2.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(OUT / "golden_review.xlsx")


if __name__ == "__main__":
    sys.exit(main())
