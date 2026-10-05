"""Automatic medication check: a deterministic check after the model, no GPU, no gold needed.

Why: the fine-tuned model records only the drugs a call is about (as the gold does) and sometimes (a) writes a drug in the summary text
without its own typed medication fact, (b) leaves a stated dose out of the typed fact, (c) leaves a drug out of the summary altogether.
Rules V1-V16 cannot see any of these (REPORT section 7). This module compares the transcript with the summary:

  expected drug   a formulary drug the CALLER said, and either said with a number in the same turn or said in two or more turns.
                  Chosen from the TRAINING gold only (dev/medsafety_eval.py reproduces the rates): such a drug is recorded in 82% of training
                  calls; a drug only the nurse says once is recorded in 0 to 10%.
  untyped         expected drug named in the summary text but without a typed medication fact -> the fact is ADDED to the bullet that names it.
  absent          expected drug named nowhere in the summary -> NOT added (nothing in the call's evidence bullets supports it): reported as a
                  finding, and the UI turns the call into NEEDS NURSE REVIEW.
  dose fill       a typed medication fact with no dose whose own bullet text states "<number> <unit>" right after the drug name -> dose and
                  unit are copied (never a concentration such as "20 mg per mL" or the number that is the fact's own strength).

apply(obj, turns) returns (new_obj, findings). It never changes the input object and never changes the summary text.
"""
from __future__ import annotations

import copy
import re
from difflib import SequenceMatcher

from .lexicons import FORMULARY
from .textnorm import normalize

DRUGS = sorted({d for d in FORMULARY if len(d) >= 5}, key=len, reverse=True)
DRUG_RX = {d: re.compile(r"\b" + re.escape(normalize(d)) + r"\b") for d in DRUGS}
NUM = re.compile(r"\b(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|half|quarter|point)\b", re.I)
UNIT = r"(?:mg|mcg|milligrams?|micrograms?|ml|milliliters?|millilitres?|g|grams?|units?|tablets?|pills?|puffs?|drops?|capsules?|patch(?:es)?)"
DOSE_RX = re.compile(rf"\b(\d+(?:\.\d+)?)\s*({UNIT})\b(?!\s*(?:/|per\b|in\b))", re.I)
SECTIONS = ("assessment", "response", "education")
UNIT_CANON = {"milligram": "mg", "milligrams": "mg", "mg": "mg", "microgram": "mcg", "micrograms": "mcg", "mcg": "mcg", "milliliter": "mL", "milliliters": "mL",
              "millilitre": "mL", "millilitres": "mL", "ml": "mL", "gram": "g", "grams": "g", "g": "g", "unit": "units", "units": "units",
              "tablet": "tablets", "tablets": "tablets", "pill": "tablets", "pills": "tablets", "puff": "puffs", "puffs": "puffs", "drop": "drops",
              "drops": "drops", "capsule": "capsules", "capsules": "capsules", "patch": "patch", "patches": "patch"}


def spoken_drugs(turns: list[dict]) -> dict[str, dict]:
    """-> {drug: {"turns": [ids], "caller": bool, "number": bool}} for formulary drugs said in the call."""
    out: dict[str, dict] = {}
    for t in turns:
        nt = normalize(t["text"])
        for d, rx in DRUG_RX.items():
            if rx.search(nt):
                o = out.setdefault(d, {"turns": [], "caller": False, "number": False})
                o["turns"].append(t["id"])
                o["caller"] |= t["speaker"] == "Caller"
                o["number"] |= bool(NUM.search(t["text"]))
    return out


def expected(o: dict) -> bool:
    return bool(o["caller"] and (o["number"] or len(o["turns"]) >= 2))


ALIASES = {  # brand -> generic, so "Tylenol" in the call matches "acetaminophen" in the summary (and the other way round)
    "tylenol": "acetaminophen", "advil": "ibuprofen", "motrin": "ibuprofen", "oxycontin": "oxycodone", "dilaudid": "hydromorphone",
    "ativan": "lorazepam", "xanax": "alprazolam", "klonopin": "clonazepam", "valium": "diazepam", "haldol": "haloperidol", "seroquel": "quetiapine",
    "zofran": "ondansetron", "colace": "docusate", "lasix": "furosemide", "lopressor": "metoprolol", "toprol": "metoprolol", "coumadin": "warfarin",
    "eliquis": "apixaban", "xarelto": "rivaroxaban", "plavix": "clopidogrel", "synthroid": "levothyroxine", "neurontin": "gabapentin",
    "keppra": "levetiracetam", "zoloft": "sertraline", "benadryl": "diphenhydramine", "pepcid": "famotidine", "prilosec": "omeprazole",
    "zyrtec": "cetirizine", "claritin": "loratadine", "miralax": "polyethylene glycol", "senokot": "senna",
}


def _canon(x: str) -> str:
    x = normalize(x or "")
    return " ".join(ALIASES.get(w, w) for w in x.split())


def _same(a: str, b: str) -> bool:
    a, b = _canon(a), _canon(b)
    return bool(a and b) and (a == b or a in b or b in a or SequenceMatcher(None, a, b).ratio() >= 0.85)


def _variants(drug: str) -> set[str]:
    """The drug and its brand/generic partners ("tylenol" <-> "acetaminophen"), so a summary that uses the other name is not flagged."""
    g = ALIASES.get(drug, drug)
    return {drug, g} | {b for b, gen in ALIASES.items() if gen == g}


def _named_in(drug: str, text: str) -> bool:
    return any(re.search(r"\b" + re.escape(normalize(v)) + r"\b", text) for v in _variants(drug))


def _bullets(obj: dict):
    for sec in SECTIONS:
        for b in (obj.get(sec) or []) if isinstance(obj, dict) else []:
            if isinstance(b, dict):
                yield sec, b


def _typed_names(obj: dict) -> list[str]:
    return [str(f.get("name") or "") for _, b in _bullets(obj) for f in (b.get("facts") or []) if isinstance(f, dict) and f.get("type") == "medication"]


WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20,
           "twenty five": 25, "thirty": 30, "forty": 40, "fifty": 50, "seventy five": 75, "hundred": 100, "one hundred": 100}
WORDNUM_RX = re.compile(r"\b(" + "|".join(sorted(map(re.escape, WORDNUM), key=len, reverse=True)) + r")\b(?=\s+" + UNIT + r"\b)", re.I)


def _digits(t: str) -> str:
    """Spelled numbers directly before a unit become digits ("five milligrams" -> "5 milligrams"); anything else is left alone."""
    return WORDNUM_RX.sub(lambda m: str(WORDNUM[m.group(1).lower()]), t)


def _first_dose(window: str, before_drug: bool = False):
    for d in DOSE_RX.finditer(window):  # first "<number> <unit>" that is a dose, not a concentration ("20 mg per mL", "100 mg in 5 mL", "20 mg/mL")
        pre = window[max(0, d.start() - 5): d.start()]
        if re.search(r"(?:\bper|\bin|/)\s*$", pre):
            continue
        return d.group(1), UNIT_CANON.get(d.group(2).lower(), d.group(2))
    return None


def extract_dose(text: str, drug: str) -> tuple[str, str] | None:
    """The "<number> <unit>" that follows `drug` in `text` (before the next drug name or 70 characters); if none does, the one that comes
    just before it in the same clause ("five milligrams of morphine", at most 3 words between); None if there is none."""
    t = _digits(text.lower())
    m = re.search(r"\b" + re.escape(drug.lower()) + r"\b", t)
    if not m:
        return None
    window = t[m.end(): m.end() + 70]
    for other in DRUGS:  # stop at the next drug named
        if other.lower() != drug.lower():
            o = re.search(r"\b" + re.escape(other.lower()) + r"\b", window)
            if o:
                window = window[: o.start()]
                own = re.search(rf"\d+(?:\.\d+)?\s*(?:{UNIT})\s+of\s+(?:[a-z]+\s+){{0,2}}$", window)  # "<dose> of <next drug>": belongs to the next drug
                if own:
                    window = window[: own.start()]
    got = _first_dose(window)
    if got:
        return got
    back = re.search(rf"(\d+(?:\.\d+)?)\s*({UNIT})\s+of\s+(?:(?!per\b|in\b)[a-z]+\s+){{0,3}}$", t[max(0, m.start() - 45): m.start()])
    if back and not re.search(r"[,;.]", back.group(0)):  # same clause only; needs "of" ("5 mg of morphine"), so "20 mg per mL of x" is out
        return back.group(1), UNIT_CANON.get(back.group(2).lower(), back.group(2))
    return None


def apply(obj, turns: list[dict]):
    """-> (obj with untyped drugs added and missing doses filled, findings). Findings: {"rule", "severity", "drug", "message"}."""
    if not isinstance(obj, dict):
        return obj, []
    new = copy.deepcopy(obj)
    findings = []
    # 1. dose fill on the facts the model wrote
    for _, b in _bullets(new):
        for f in b.get("facts") or []:
            if isinstance(f, dict) and f.get("type") == "medication" and not f.get("dose") and f.get("name"):
                got = extract_dose(str(b.get("text") or ""), str(f["name"]))
                if got and got[0] not in re.findall(r"\d+(?:\.\d+)?", str(f.get("strength") or "")):
                    keys = list(f)
                    items = {k: f[k] for k in keys}
                    ordered = {}
                    for k in keys:
                        ordered[k] = items[k]
                        if k == "name":
                            ordered["dose"], ordered["unit"] = got
                    f.clear()
                    f.update(ordered)
                    findings.append({"rule": "M2", "severity": "INFO", "drug": f["name"], "message": f"dose {got[0]} {got[1]} copied from the bullet text into the typed fact for {f['name']}"})
    # 2. expected drugs missing from the typed facts
    typed = _typed_names(new)
    text = normalize(" ".join([str((new.get("chief_complaint") or {}).get("reason") or "")] + [str(b.get("text") or "") for _, b in _bullets(new)]))
    for drug, o in spoken_drugs(turns).items():
        if not expected(o) or any(_same(drug, n) for n in typed):
            continue
        if _named_in(drug, text):
            host = next((b for _, b in _bullets(new) if _named_in(drug, normalize(str(b.get("text") or "")))), None)
            fact = {"type": "medication", "name": drug}
            got = extract_dose(str(host.get("text") or ""), drug) if host else None
            if got:
                fact["dose"], fact["unit"] = got
            fact["certainty"] = "stated"
            if host is not None:
                host.setdefault("facts", []).append(fact)
                typed.append(drug)
                findings.append({"rule": "M1", "severity": "INFO", "drug": drug, "message": f"{drug} is in the summary text without a typed medication fact: fact added"})
        else:
            findings.append({"rule": "M3", "severity": "WARN", "drug": drug,
                             "message": f"{drug} was said by the caller (turns {', '.join(map(str, o['turns']))}) but is not in the summary: a nurse should check it"})
    return new, findings
