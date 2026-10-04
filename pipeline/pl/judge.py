"""Semantic judge stage (needs the GPU server): the frozen v5 judge validated in llm_judge/.

Per summary: faithfulness (1 call), calibration (1 call), completeness (1-2 calls per checklist item).
Completeness needs a checklist of what the summary must cover:
  mode "reference"  : one line per fact-record item (our validation calls). This is the validated mode.
  mode "transcript" : the judge model lists the important facts of the call itself (for unseen calls with no fact record).
                      NOT validated: it measures coverage of what the model thinks matters, and is only comparable between systems
                      when both systems use the same cached checklist.
The judge sees only transcript + rendered summary. It never sees gold, labels or validator findings.
"""
from __future__ import annotations

import copy
import json
import re
import time
from datetime import datetime
from pathlib import Path

from .judge_lib import CHECK, VERDICT, ask
from .render import render
from .transcript import numbered, parse

HERE = Path(__file__).resolve().parent.parent
PROMPTS = HERE / "prompts" / "judge"
CALIB = {"type": "object", "required": ["analysis", "problem_type", "reason"], "additionalProperties": False, "properties": {
    "analysis": {"type": "string"}, "problem_type": {"type": "string", "enum": ["none", "certainty", "status", "speaker"]}, "reason": {"type": "string"}}}
FACT_TYPES = ["symptom", "negative", "medication", "vital", "supply", "nurse_action", "instruction"]
EXTRACT = {"type": "object", "required": ["facts"], "additionalProperties": False, "properties": {"facts": {"type": "array", "items": {
    "type": "object", "required": ["type", "fact"], "additionalProperties": False, "properties": {"type": {"type": "string", "enum": FACT_TYPES}, "fact": {"type": "string"}}}}}}


def load_prompts() -> dict:
    names = {"faithfulness": "v5_prompt_faithfulness.md", "calibration": "v5_prompt_calibration.md", "match": "v5_prompt_completeness_match.md",
             "recheck": "v5_prompt_completeness_recheck.md", "extract": "completeness_extract_transcript_mode.md"}
    return {k: (PROMPTS / v).read_text() for k, v in names.items()}


_DATE_FORMATS = ("%B %d %Y", "%b %d %Y", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%Y/%m/%d", "%d %B %Y")


def _iso_date(text: str) -> str | None:
    """Best-effort conversion of a date written another way ("March 3rd, 1940", "03/03/1940") to YYYY-MM-DD, or None."""
    spoken = _spoken_date(str(text or ""))
    if spoken:
        return spoken
    t = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", str(text or "").strip(), flags=re.I).replace(",", " ")
    t = " ".join(t.split())
    for f in _DATE_FORMATS:
        try:
            return datetime.strptime(t, f).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11,
        "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
        "twentieth": 20, "thirtieth": 30}
_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def _words_to_num(words: list[str]) -> int | None:
    """"nineteen thirty three" -> 33, "twenty one" -> 21, "eighth" -> 8, "twenty second" -> 22 (a number below 100, or None)."""
    total = 0
    for w in words:
        if w in _TENS:
            total += _TENS[w]
        elif w in _UNITS:
            total += _UNITS[w]
        elif w in _ORD:
            total += _ORD[w]
        else:
            return None
    return total if words else None


def _spoken_date(text: str) -> str | None:
    """"December eighth, nineteen thirty three" -> 1933-12-08; "November fifth, twenty twenty" -> 2020-11-05."""
    w = re.sub(r"[,\-]", " ", text.lower()).split()
    if len(w) < 4 or w[0] not in _MONTHS:
        return None
    month = _MONTHS.index(w[0]) + 1
    for i in range(2, 4):  # day is one or two words ("twenty second")
        day, year = _words_to_num(w[1:i]), w[i:]
        if day and 1 <= day <= 31 and len(year) >= 2:
            head = _words_to_num(year[:1]) if year[0] in ("nineteen", "twenty") else None
            if year[0] == "twenty" and len(year) >= 2 and year[1] not in _TENS and year[1] not in _UNITS:
                continue
            tail = _words_to_num(year[1:]) if head is not None else None
            if head in (19, 20) and tail is not None and tail < 100:
                if year[0] == "twenty" and year[1] in _TENS and len(year) == 2 and year[1] == "twenty":
                    tail = 20  # "twenty twenty"
                return f"{head * 100 + tail:04d}-{month:02d}-{day:02d}"
    return None


def render_summary(obj: dict, timestamp: str | None) -> str | None:
    """Render for the judge. A date of birth in the wrong format is a rule finding (V9), not a reason to skip the judge, so it is
    converted for display when possible; a summary that still cannot be rendered is reported as unjudged."""
    try:
        return render(obj, timestamp)
    except Exception:
        pass
    try:
        fixed = copy.deepcopy(obj)
        dob = fixed["identity"]["patient_dob"]
        dob["value"] = _iso_date(dob.get("value"))  # None when it cannot be read: shown as a missing date of birth, V9 reports the bad value
        return render(fixed, timestamp)
    except Exception:
        pass
    return None


def extract_checklist(args, prompts: dict, transcript: str) -> list[dict]:
    out = ask(args, prompts["extract"], f"TRANSCRIPT\n{numbered(parse(transcript))}", EXTRACT, 2000)
    facts = ((out or {}).get("facts") or [])[:10]
    return [{"n": i, "fact": f"[{f['type']}] {f['fact']}"} for i, f in enumerate(facts, 1)]


def judge_one(args, prompts: dict, case: dict, summary_obj, checklist: list[dict] | None, mode: str) -> dict:
    t0 = time.time()
    summary = render_summary(summary_obj, case.get("call_timestamp_utc")) if isinstance(summary_obj, dict) else None
    if summary is None:
        return {"id": case["id"], "judged": False, "reason": "no renderable summary", "verdicts": None, "extra": {}, "completeness_mode": mode, "seconds": 0}
    both = f"TRANSCRIPT\n{case['transcript']}\n\nSUMMARY\n{summary}"
    v, extra = {}, {}
    out = ask(args, prompts["faithfulness"], both, VERDICT, 1500)
    v["faithfulness"] = {"verdict": out["verdict"], "reason": out.get("reason", "")} if out and out.get("verdict") in ("PASS", "FAIL") else None
    out = ask(args, prompts["calibration"], both, CALIB, 1500)
    v["calibration"] = {"verdict": "PASS" if out["problem_type"] == "none" else "FAIL", "reason": f"[{out['problem_type']}] {out.get('reason', '')}"} if out and out.get("problem_type") else None
    items, failed = [], False
    na = bool((summary_obj.get("not_applicable") or {}).get("is_na"))
    if na or not checklist:
        v["completeness"] = {"verdict": "PASS", "reason": "no checklist: completeness not applicable"}
        extra["items"] = []
    else:
        for it in checklist:
            user = f"REFERENCE ITEM\n{it['fact']}\n\nSUMMARY\n{summary}"
            first = ask(args, prompts["match"], user, CHECK, 300)
            if first is None:
                failed = True
                continue
            rec = {"n": it["n"], "fact": it["fact"], "first": first["present"], "evidence": first["evidence"], "rechecked": None}
            if not first["present"]:
                second = ask(args, prompts["recheck"], user, CHECK, 300)
                if second is None:
                    failed = True
                    continue
                rec["rechecked"], rec["evidence"] = second["present"], second["evidence"] or rec["evidence"]
            rec["present"] = first["present"] or bool(rec["rechecked"])
            items.append(rec)
        missing = [i["fact"] for i in items if not i["present"]]
        extra["items"] = items
        v["completeness"] = None if failed or not items else {"verdict": "FAIL" if missing else "PASS", "reason": ("Missing: " + " | ".join(missing)) if missing else "Every checklist item is covered."}
    return {"id": case["id"], "judged": True, "verdicts": v if all(x is not None for x in v.values()) else None, "partial": v, "extra": extra,
            "completeness_mode": mode, "seconds": round(time.time() - t0, 2)}
