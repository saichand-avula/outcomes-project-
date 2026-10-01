"""Independent validators. They re-check transcripts and gold with different code paths than the builder used, so a
builder bug cannot hide itself. Each returns a list of issue dicts {id, record_id, detail}; an empty list = clean.

Gold checks mirror the plan's runtime validators (V3 quote-in-source, V4 speaker, V5 numbers, V8 planned-vs-completed,
V9 hedges, V6 drug mishearing, V7 identity) because the gold must pass the same validators the model output will face.
"""
from __future__ import annotations
import re

import lexicons as L
import risk_rules as RR
import spoken as SP
import spoken_numbers as SN
from schema import FactRecord
from transcript_utils import Turn, norm, speaker_blocks

FORM = {d["generic"]: d for d in L.FORMULARY}
DRUG_NAMES = sorted({n.lower() for d in L.FORMULARY for n in [d["generic"], *d["aliases"]]}, key=len, reverse=True)
DRUG_RX = re.compile(r"\b(" + "|".join(re.escape(n) for n in DRUG_NAMES) + r")\b", re.I)
HEDGE_RX = re.compile(r"\b(" + "|".join(re.escape(h) for h in L.HEDGES if h not in ("[inaudible]", "about")) + r")\b", re.I)
# "about" before a duration ("for about three days") is an approximate duration, not a hedge on a critical value
ABOUT_VALUE_RX = re.compile(r"\babout\s+(?!(?:\w+\s+){0,2}(?:day|days|week|weeks|hour|hours|month|months)\b)", re.I)


def has_hedge(text: str) -> str | None:
    m = HEDGE_RX.search(text) or ABOUT_VALUE_RX.search(text)
    return m.group(0).strip() if m else None


# independent keyword lists (deliberately NOT imported from voicer) used to confirm a symptom/negative is actually voiced
SYM_KEYS = {"pain": {"pain", "hurting"}, "shortness of breath": {"breathing", "breath"}, "agitation": {"agitated", "agitation"},
            "restlessness": {"restless", "fidgety"}, "confusion": {"confused", "disoriented"}, "anxiety": {"anxious", "panicky"},
            "nausea": {"nauseated", "queasy", "stomach"}, "vomiting": {"throwing", "vomiting"}, "constipation": {"constipated"},
            "diarrhea": {"loose", "diarrhea"}, "fever": {"fever"}, "chills": {"shivering", "chills"}, "cough": {"cough", "coughing"},
            "nasal congestion": {"stuffy", "congested"}, "sore throat": {"throat"}, "lethargy": {"tired", "lethargic", "sleeping"},
            "decreased appetite": {"eating", "hungry"}, "dizziness": {"dizzy", "lightheaded"}, "insomnia": {"sleeping", "night"},
            "swelling": {"swollen", "swelling"}, "urinary retention": {"urinating", "pee"}, "skin breakdown": {"sore", "spot"},
            "headache": {"headache"}, "weakness": {"weak"}, "difficulty swallowing": {"pills", "medicine"}, "fall": {"fall", "fell"},
            "statement of wanting to die (by patient)": {"die", "life", "live"}, "statement of wanting to die (by caller)": {"die", "life", "live"}}
NEG_KEYS = {"nausea": {"nausea"}, "difficulty breathing": {"breathing"}, "confusion": {"confusion"}, "fever": {"fever"}, "falls": {"falls"}}


# symptoms whose natural surface form is itself negative ("not eating", "not sleeping", "not urinating")
NEG_EXEMPT = {"decreased appetite", "insomnia", "urinary retention"}


def polarity(turns, b, keys) -> tuple[int, int]:
    """(occurrences of the key words in the fact's own turns, how many are inside a negation window)."""
    toks: list[str] = []
    for t in turns:
        if b["fact_id"] in t.fact_ids:
            toks += RR.clean_tokens(t.text)
    tot = neg = 0
    for i, w in enumerate(toks):
        if w in keys:
            tot += 1
            neg += any(RR._is_neg(x) for x in toks[max(0, i - L.NEGATION_WINDOW):i])
    return tot, neg


def _cited(turns, b):
    """ONLY the turns the bullet cites. Deliberately ignores the voicer's fact tags: a model output has no tags, so a
    check that peeks at them would pass a bullet re-pointed at somebody else's quote (found by mutation testing)."""
    return " ".join(turns[i - 1].text for i in sorted(set(b["turn_ids"])))


def _i(id_, rid, detail): return dict(id=id_, record_id=rid, detail=detail)


# ----------------------------------------------------------------------------- transcript invariants
def check_transcript(rec: FactRecord, turns: list[Turn], gold_meds: dict[str, dict] | None = None) -> list[dict]:
    """rec = the record AFTER events (garbled meds have name None)."""
    iss: list[dict] = []
    rid = rec.record_id
    tags = set().union(*[t.fact_ids for t in turns]) if turns else set()
    if rec.not_applicable:
        # NA transcripts must carry no clinical token at all
        for t in turns:
            if DRUG_RX.search(t.text) or re.search(r"\d", t.text):
                iss.append(_i("T-NA", rid, f"clinical token in NA transcript turn {t.id}: {t.text[:60]!r}"))
        return iss
    want = [f.id for f in rec.all_facts() if not (f.id.startswith("R") and not f.evidence)] + [f"ID.{k}" for k in ("patient_name", "patient_dob", "caller_name", "relationship", "callback_phone")]
    for fid in want:
        if fid.startswith("R"):
            continue                                           # risk flags are grounded via trigger turns, checked in check_gold
        if fid not in tags:
            iss.append(_i("T1-fact-not-voiced", rid, fid))
    unclear_ids = {m.id for m in rec.medications if m.certainty == "unclear"} | {s.id for s in rec.symptoms if s.certainty == "unclear"}
    garbled = {m.id: m for m in rec.medications if m.name is None}
    for t in turns:
        # T2: untagged turns carry no drug name and no digit
        if not t.fact_ids:
            if DRUG_RX.search(t.text):
                iss.append(_i("T2-untagged-drug", rid, f"turn {t.id}: {t.text[:70]!r}"))
            if re.search(r"\d", t.text):
                iss.append(_i("T2-untagged-digit", rid, f"turn {t.id}: {t.text[:70]!r}"))
        # T3: turns expressing only stated facts contain no hedge word
        elif not (t.fact_ids & unclear_ids) and has_hedge(t.text):
            iss.append(_i("T3-hedge-in-stated", rid, f"turn {t.id}: {has_hedge(t.text)!r} in {t.text[:70]!r}"))
    full = RR.clean_text(" ".join(t.text for t in turns))        # filler/repeat-normalised, spans turn boundaries
    for m in rec.medications:
        if m.name is None:                                     # T4: garbled drug -> real name must not leak anywhere
            real = next((mm for mm in gold_meds.values() if mm["id"] == m.id), None) if gold_meds else None
            if real:
                names = [real["name"], *(FORM[real["name"]]["aliases"] if real["name"] in FORM else [])]
                for n in names:
                    if re.search(r"\b" + re.escape(RR.clean_text(n)) + r"\b", full):
                        iss.append(_i("T4-garble-leak", rid, f"{m.id}: true name {n!r} still present"))
            if m.name_as_heard and RR.clean_text(m.name_as_heard) not in full:
                iss.append(_i("T4-heard-missing", rid, f"{m.id}: heard form {m.name_as_heard!r} not in transcript"))
        else:
            names = [m.name, *(FORM[m.name]["aliases"] if m.name in FORM else [])]
            if not any(re.search(r"\b" + re.escape(RR.clean_text(n)) + r"\b", full) for n in names):
                iss.append(_i("T5-med-name-missing", rid, f"{m.id} {m.name}"))
    return iss


# ----------------------------------------------------------------------------- gold checks
def _blocks(turns):
    return speaker_blocks(turns)


def quote_in_source(turns: list[Turn], quote: str, speaker: str) -> bool:
    q = norm(quote)
    for sp, _ids, toks, _tids in _blocks(turns):
        if sp == speaker and q in " ".join(toks):
            return True
    return False


def _window_text(turns, ids, w=2):
    lo, hi = max(1, min(ids) - w), min(len(turns), max(ids) + w)
    return " ".join(turns[i - 1].text for i in range(lo, hi + 1))


def check_gold(g: dict, rec_after: FactRecord, turns: list[Turn]) -> list[dict]:
    iss: list[dict] = []
    rid = g["record_id"]
    if g["not_applicable"]:
        if g["bullets"] or g["chief_complaint"]:
            iss.append(_i("G6-na-has-content", rid, "NA record has bullets"))
        return iss
    units = [("cc", g["chief_complaint"])] + [(b["fact_id"], b) for b in g["bullets"]]
    for fid, b in units:                                        # V3 / V4
        if not b or not b.get("quote"):
            iss.append(_i("G1-no-quote", rid, fid)); continue
        if not b["turn_ids"]:
            iss.append(_i("G1-no-turns", rid, fid)); continue
        if not quote_in_source(turns, b["quote"], b["speaker"]):
            iss.append(_i("G1-quote-not-in-source", rid, f"{fid}: {b['quote'][:70]!r}"))
        if turns[b["turn_ids"][0] - 1].speaker != b["speaker"]:
            iss.append(_i("G2-speaker-mismatch", rid, fid))
        if fid != "cc":
            verb = b["text"].split()[0]
            if verb != b["speaker"]:
                iss.append(_i("G3-attribution", rid, f"{fid}: text starts {verb!r} but speaker {b['speaker']}"))
    for b in g["bullets"]:                                      # V5 numbers
        win = _cited(turns, b)
        ctoks = set(RR.clean_tokens(win))
        for f in b["facts"]:
            if f["type"] == "symptom" and not (SYM_KEYS.get(f["name"], {f["name"]}) & ctoks):
                iss.append(_i("G4-symptom-not-in-cited-turns", rid, f"{b['fact_id']} {f['name']}"))
            if f["type"] == "negative" and not (NEG_KEYS[f["name"]] & ctoks):
                iss.append(_i("G4-negative-not-in-cited-turns", rid, f"{b['fact_id']} {f['name']}"))
            if f["type"] == "negative":                              # G10 polarity: a denied item must be voiced in a negated context
                tot, neg = polarity(turns, b, NEG_KEYS[f["name"]])
                if tot and not neg:
                    iss.append(_i("G10-negative-not-negated", rid, f"{b['fact_id']} {f['name']}"))
            if f["type"] == "symptom" and f["name"] not in NEG_EXEMPT and "wanting to die" not in f["name"]:
                tot, neg = polarity(turns, b, SYM_KEYS.get(f["name"], {f["name"]}))
                if tot and neg == tot:
                    iss.append(_i("G10-symptom-only-negated", rid, f"{b['fact_id']} {f['name']}"))
            if f["type"] == "medication":
                names = [f["name"], *(FORM[f["name"]]["aliases"] if f["name"] in FORM else [])] if f["name"] else [f["name_as_heard"]]
                blob = RR.clean_text(win)
                if not any(RR.clean_text(n) in blob for n in names if n):
                    iss.append(_i("G4-med-name-not-in-cited-turns", rid, f"{b['fact_id']} {f['name'] or f['name_as_heard']}"))
            if f["type"] == "medication" and f.get("dose"):
                if (f["dose"], f["unit"]) not in SN.dose_candidates(RR.strip_fillers(win)):
                    iss.append(_i("G4-dose-not-in-cited-turns", rid, f"{b['fact_id']} {f['dose']} {f['unit']}"))
            if f["type"] == "medication" and f.get("frequency"):
                if not any(RR.clean_text(v) in RR.clean_text(win) for v in SP.FREQ_SPOKEN[f["frequency"]]):
                    iss.append(_i("G4-frequency-not-in-cited-turns", rid, f"{b['fact_id']} {f['frequency']}"))
            if f["type"] == "medication" and f.get("route"):
                if not any(RR.clean_text(v) in RR.clean_text(win) for v in SP.ROUTE_SPOKEN[f["route"]]):
                    iss.append(_i("G4-route-not-in-cited-turns", rid, f"{b['fact_id']} {f['route']}"))
            if f["type"] == "symptom" and f.get("severity") and "/" in f["severity"]:
                if SP.sev_numeric_from_spoken(win) != f["severity"]:
                    iss.append(_i("G4-severity-not-in-cited-turns", rid, f"{b['fact_id']} {f['severity']}"))
            if f["type"] == "supply" and f.get("quantity_remaining"):
                if RR.clean_text(SP.qty_spoken(f["quantity_remaining"])) not in RR.clean_text(win):
                    iss.append(_i("G4-qty-not-in-turns", rid, f"{b['fact_id']} {f['quantity_remaining']}"))
        if b["kind"] == "action" and b["turn_ids"]:             # V8 planned vs completed
            st = b["facts"][0]["status"]; txt = RR.clean_text(" ".join(turns[i - 1].text for i in b["turn_ids"]))
            fut = any(RR.clean_text(c) in txt for c in L.FUTURE_CUES); comp = any(RR.clean_text(c) in txt for c in L.COMPLETION_CUES)
            if st == "planned" and (not fut or comp): iss.append(_i("G7-planned-cues", rid, f"{b['fact_id']} fut={fut} comp={comp}"))
            if st == "completed" and (not comp or fut): iss.append(_i("G7-completed-cues", rid, f"{b['fact_id']} fut={fut} comp={comp}"))
            if st == "advised" and comp: iss.append(_i("G7-advised-has-completion", rid, b["fact_id"]))
        if b["kind"] == "medication":                           # V6 / policy P1 wording
            f = b["facts"][0]
            if (f["name"] is None or f["certainty"] == "unclear") and "unclear" not in b["text"]:
                iss.append(_i("G9-unclear-not-marked", rid, b["fact_id"]))
    # V7 identity recoverability
    I = g["identity"]
    allc = RR.strip_fillers(" ".join(t.text for t in turns))
    if I["callback_phone"]["value"] and I["callback_phone"]["value"] not in SN.phone_candidates(allc):
        iss.append(_i("G5-phone-not-recoverable", rid, I["callback_phone"]["value"]))
    dob = I["patient_dob"]["value"]
    if dob:
        ids = I["patient_dob"]["turn_ids"]
        cands = {c["iso"] for c in SN.date_candidates(RR.strip_fillers(" ".join(turns[i - 1].text for i in ids)))} if ids else set()
        if dob not in cands:
            iss.append(_i("G5-dob-not-recoverable", rid, dob))
    for f in ("patient_name", "caller_name"):
        v = I[f]["value"]
        if v and not all(re.search(r"\b" + re.escape(w) + r"\b", allc, re.I) for w in v.split()[:1]):
            iss.append(_i("G5-name-not-in-transcript", rid, f"{f}={v}"))
    rel = I["relationship"]["value"]
    if rel and not any(re.search(r"\b" + w + r"\b", allc, re.I) for w in SP.REL_WORDS.get(rel, {rel})):
        iss.append(_i("G5-relationship-not-in-transcript", rid, rel))
    # risk flags: grounded, and the rule scanner agrees (recall-first rule layer must find every required flag)
    scan = RR.scan_turns(turns)
    for r in g["risk_flags"]:
        if r["required"] and not r["quote"]:
            iss.append(_i("G8-flag-ungrounded", rid, r["category"]))
        if r["required"] and r["category"] not in scan:
            iss.append(_i("G8-rule-misses-required-flag", rid, r["category"]))
    return iss


def extra_rule_flags(g: dict, turns: list[Turn]) -> list[str]:
    """Categories the rule layer fires on that the gold does not list at all (precision noise)."""
    scan = RR.scan_turns(turns)
    have = {r["category"] for r in g["risk_flags"]}
    return sorted(c for c in scan if c not in have)
