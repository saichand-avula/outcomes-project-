"""Deterministic validators for a summarizer output, using ONLY the transcript and the output (no fact record, no gold).

Rules (architecture 5.2, extended):
  V1 JSON parses and matches the schema        V2 sections / Not-Applicable consistency     V3 cited turns exist
  V4 quote is verbatim in the cited turns      V5 quote speaker = speaker of the cited turn  V6 numbers are in the cited turns
  V7 drug names are in the call                V8 clinical terms are in the call             V9 identity values are in the call
  V10 planned / completed matches the nurse's words    V11 hedges kept (warning)             V12 negations kept
  V13 risk flags vs rule hits                  V14 Not-Applicable gate                       V15 coverage proxies (warnings)
  V16 hygiene (empty text, duplicates)
Severity: ERROR = the output is unsafe to use as it stands; WARN = needs a nurse's look; INFO is never scored.
Every check also records (ok, total) counters so rates can be reported.
"""
from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher

from . import lexicons as L
from . import risk_rules as RR
from .schema import SUMMARY_SCHEMA, check as schema_check
from .textnorm import collapse_spelled, normalize, number_candidates, numbers_in, supported
from .transcript import turn_text, window

SECTIONS = ("assessment", "response", "education")
NUM_FIELDS = ("dose", "strength", "severity", "value", "supply", "last_dose", "frequency", "timeframe", "duration", "onset")
RISK_ERROR_CATEGORIES = {"suicidal_statement", "escalation_request"}  # rule precision >= 0.9 on training data; other categories only warn
NA_CLINICAL_HIGH = 4
RADIUS = 2


class Ctx:
    def __init__(self, obj, turns):
        self.obj, self.turns = obj, turns
        self.n = len(turns)
        self.findings: list[dict] = []
        self.counters: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        self.full_text = " ".join(t["text"] for t in turns)
        self.full_norm = normalize(collapse_spelled(self.full_text))
        self.full_words = set(self.full_norm.split())
        self.full_cands = number_candidates(self.full_text)
        # capitalized words that are not sentence-initial: names as they were typed in the transcript
        self.proper_words = {m.group(1).lower() for m in re.finditer(r"(?<![.?!]\s)(?<!^)\b([A-Z][a-z]{3,})\b", re.sub(r"(?m)^(Nurse|Caller) -> ", "", " ".join(t["text"] for t in turns)))}
        self._cand_cache: dict[tuple, set] = {}

    def add(self, rule, sev, path, msg):
        self.findings.append({"rule": rule, "severity": sev, "path": path, "message": msg})

    def count(self, name, ok: bool):
        c = self.counters[name]
        c[1] += 1
        c[0] += bool(ok)

    def cands(self, ids) -> set:
        key = tuple(ids)
        if key not in self._cand_cache:
            self._cand_cache[key] = number_candidates(turn_text(self.turns, ids))
        return self._cand_cache[key]

    def items(self):
        o = self.obj
        if isinstance(o.get("chief_complaint"), dict):
            yield "chief_complaint", o["chief_complaint"], "reason"
        for sec in SECTIONS:
            for i, b in enumerate(o.get(sec) or []):
                if isinstance(b, dict):
                    yield f"{sec}[{i}]", b, "text"


def _ids(b) -> list[int]:
    return [i for i in (b.get("turns") or []) if isinstance(i, int) and not isinstance(i, bool)]


def _tokens(s: str) -> list[str]:
    return normalize(s).split()


def best_window_ratio(q: list[str], hay: list[str]) -> float:
    if not q or not hay:
        return 0.0
    best = 0.0
    for size in {max(1, len(q) - 1), len(q), len(q) + 1}:
        for i in range(0, max(1, len(hay) - size + 1)):
            best = max(best, SequenceMatcher(None, q, hay[i:i + size]).ratio())
            if best >= 0.999:
                return best
    return best


# ------------------------------------------------------------------ V2 / V3
def v2_sections(c: Ctx):
    o = c.obj
    na = o.get("not_applicable") or {}
    is_na = bool(na.get("is_na"))
    if is_na:
        ok = bool(na.get("reason")) and not any(o.get(s) for s in SECTIONS) and not o.get("risk_flags") and not o.get("chief_complaint")
        c.count("na_consistent", ok)
        if not na.get("reason"):
            c.add("V2", "ERROR", "not_applicable.reason", "Not Applicable without a reason")
        if any(o.get(s) for s in SECTIONS) or o.get("risk_flags"):
            c.add("V2", "ERROR", "not_applicable", "Not Applicable output still has sections or risk flags")
        return
    if not isinstance(o.get("chief_complaint"), dict):
        c.add("V2", "ERROR", "chief_complaint", "missing chief_complaint on a clinical call")
    if not any(o.get(s) for s in SECTIONS):
        c.add("V2", "WARN", "$", "no assessment, response or education bullets on a clinical call")


def v3_turns(c: Ctx):
    for path, b, _ in c.items():
        ids = b.get("turns")
        ok = isinstance(ids, list) and len(ids) > 0 and all(isinstance(i, int) and 1 <= i <= c.n for i in ids)
        c.count("turns_valid", ok)
        if not ok:
            c.add("V3", "ERROR", f"{path}.turns", f"cited turns {ids!r} are empty or outside 1..{c.n}")
    for i, f in enumerate(c.obj.get("risk_flags") or []):
        ids = f.get("turns") if isinstance(f, dict) else None
        ok = isinstance(ids, list) and ids and all(isinstance(x, int) and 1 <= x <= c.n for x in ids)
        c.count("turns_valid", ok)
        if not ok:
            c.add("V3", "ERROR", f"risk_flags[{i}].turns", f"cited turns {ids!r} are empty or outside 1..{c.n}")


# ------------------------------------------------------------------ V4 / V5
def _check_quote(c: Ctx, path: str, quote, ids) -> str:
    """-> 'exact' | 'repairable' | 'bad'"""
    if not isinstance(quote, str) or not quote.strip():
        c.add("V4", "ERROR", f"{path}.quote", "empty quote")
        return "bad"
    valid = [i for i in ids if 1 <= i <= c.n]
    cited = normalize(collapse_spelled(turn_text(c.turns, valid)))
    nq = normalize(collapse_spelled(quote))
    if nq and f" {nq} " in f" {cited} ":
        return "exact"
    ratio = best_window_ratio(nq.split(), cited.split())
    if ratio >= 0.9:
        c.add("V4", "WARN", f"{path}.quote", f"quote differs slightly from the cited turns (similarity {ratio:.2f}); replace it with the exact span")
        return "repairable"
    where = [t["id"] for t in c.turns if nq and f" {nq} " in f" {normalize(collapse_spelled(t['text']))} "]
    if where:
        c.add("V4", "ERROR", f"{path}.quote", f"quote is not in the cited turns {valid} but is in turn(s) {where}")
    else:
        c.add("V4", "ERROR", f"{path}.quote", f"quote not found in the cited turns (best similarity {ratio:.2f}): {quote[:70]!r}")
    return "bad"


def v4_v5_quotes(c: Ctx):
    for path, b, _ in c.items():
        ids = _ids(b)
        res = _check_quote(c, path, b.get("quote"), ids)
        c.count("quote_exact", res == "exact")
        c.count("quote_valid", res in ("exact", "repairable"))
        if res == "bad":
            continue
        nq = normalize(collapse_spelled(b.get("quote") or ""))
        holders = [t for t in c.turns if t["id"] in ids and nq and f" {nq} " in f" {normalize(collapse_spelled(t['text']))} "] or [t for t in c.turns if t["id"] in ids]
        ok = any(t["speaker"] == b.get("speaker") for t in holders)
        c.count("speaker_ok", ok)
        if not ok:
            c.add("V5", "WARN", f"{path}.speaker", f"bullet says {b.get('speaker')} but the quoted turn(s) {[t['id'] for t in holders]} are labeled {holders[0]['speaker']} (attribution error, or a diarization error the model corrected)")
    for i, f in enumerate(c.obj.get("risk_flags") or []):
        if isinstance(f, dict):
            res = _check_quote(c, f"risk_flags[{i}]", f.get("quote"), _ids(f))
            c.count("quote_valid", res in ("exact", "repairable"))
            c.count("quote_exact", res == "exact")


# ------------------------------------------------------------------ V6 numbers
def _item_number_sources(b, text_key):
    yield "text", b.get(text_key) or ""
    for fi, f in enumerate(b.get("facts") or []):
        if not isinstance(f, dict):
            continue
        for k in NUM_FIELDS:
            v = f.get(k)
            if v is not None and not isinstance(v, bool):
                yield f"facts[{fi}].{k}", str(v)


def v6_numbers(c: Ctx):
    for path, b, text_key in c.items():
        ids = _ids(b)
        win = window(ids, c.n, RADIUS)
        cands = c.cands(win) if win else set()
        for where, src in _item_number_sources(b, text_key):
            for n in numbers_in(src):
                in_win = supported(n, cands)
                in_call = in_win or supported(n, c.full_cands)
                c.count("numbers_in_window", in_win)
                c.count("numbers_in_call", in_call)
                if not in_call:
                    c.add("V6", "ERROR", f"{path}.{where}", f"number {n} is not in the call (invented or changed)")
                elif not in_win:
                    c.add("V6", "INFO", f"{path}.{where}", f"number {n} is in the call but not in the cited turns {ids}")


# ------------------------------------------------------------------ V7 drugs
_DRUG_RX = re.compile(r"\b(?:" + "|".join(re.escape(d) for d in sorted(L.FORMULARY, key=len, reverse=True) if len(d) > 3) + r")\b", re.I)


def _in_text(name: str, words: set, norm: str) -> bool:
    nn = normalize(name)
    return bool(nn) and (f" {nn} " in f" {norm} " or all(w in words for w in nn.split()))


def _drug_names(b):
    for fi, f in enumerate(b.get("facts") or []):
        if not isinstance(f, dict):
            continue
        if f.get("type") == "medication" and f.get("name"):
            yield f"facts[{fi}].name", str(f["name"])
        for k in ("med_name", "medication"):
            if f.get(k) and f.get("type") == "action":
                yield f"facts[{fi}].{k}", str(f[k])
        for h in f.get("heard_as") or []:
            if f.get("type") == "medication":
                yield f"facts[{fi}].heard_as", str(h)


def v7_drugs(c: Ctx):
    for path, b, text_key in c.items():
        ids = _ids(b)
        win_norm = normalize(collapse_spelled(turn_text(c.turns, window(ids, c.n, RADIUS))))
        win_words = set(win_norm.split())
        names = list(_drug_names(b))
        for m in _DRUG_RX.finditer(b.get(text_key) or ""):
            names.append(("text", m.group(0)))
        for where, name in names:
            in_call = _in_text(name, c.full_words, c.full_norm)
            in_win = in_call and _in_text(name, win_words, win_norm)
            c.count("drugs_in_call", in_call)
            c.count("drugs_in_window", in_win)
            if not in_call:
                close = max((SequenceMatcher(None, normalize(name), w).ratio() for w in c.full_words if len(w) > 3), default=0)
                if close >= 0.8:
                    c.add("V7", "WARN", f"{path}.{where}", f"drug name {name!r} differs from the spelling in the call (policy: keep the name as spoken)")
                else:
                    c.add("V7", "ERROR", f"{path}.{where}", f"drug name {name!r} is not in the call")
            elif not in_win:
                c.add("V7", "INFO", f"{path}.{where}", f"drug name {name!r} is in the call but not in the cited turns {ids}")


# ------------------------------------------------------------------ V8 clinical terms
def v8_terms(c: Ctx):
    for path, b, text_key in c.items():
        parts = [b.get(text_key) or ""]
        for f in b.get("facts") or []:
            if isinstance(f, dict) and f.get("type") in ("symptom", "pertinent_negative", "vital", "context"):
                parts += [str(f.get(k)) for k in ("name", "item") if f.get(k)]
        text = " ".join(parts)
        for term, (s_pat, t_pat) in L.CLINICAL.items():
            if s_pat.search(text):
                ok = bool(t_pat.search(c.full_text))
                c.count("clinical_terms_supported", ok)
                if not ok:
                    c.add("V8", "WARN" if term in L.GENERIC_TERMS else "ERROR", f"{path}.text", f"'{term}' appears in the summary but nothing in the call mentions it")
                elif term in L.SPECIFIC_TERMS and not s_pat.search(c.full_text):
                    c.add("V8", "WARN", f"{path}.text", f"'{term}' is in the summary but the call only has a loose synonym, not the word itself")


# ------------------------------------------------------------------ V9 identity
def _date_ok(c: Ctx, iso: str) -> tuple[str, str]:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    if not m:
        return "bad", "date is not YYYY-MM-DD"
    y, mo, d = m.group(1), str(int(m.group(2))), str(int(m.group(3)))
    parts = {"year": y, "month": mo, "day": d}
    missing = [k for k, v in parts.items() if not supported(v, c.full_cands)]
    if missing:
        return "bad", f"{', '.join(missing)} of {iso} never spoken in the call"
    for i in range(0, c.n):
        wc = c.cands([t["id"] for t in c.turns[i:i + 4]])
        if all(supported(v, wc) for v in parts.values()):
            return "ok", ""
    return "scattered", f"year, month and day of {iso} are all in the call but not close together"


def _phone_ok(c: Ctx, digits: str) -> tuple[str, str]:
    digits = re.sub(r"\D", "", digits or "")
    if len(digits) != 10:
        return "bad", f"phone {digits!r} is not 10 digits"
    if digits not in c.full_cands:
        for i in range(0, max(1, c.n - 3)):
            if digits in c.cands([t["id"] for t in c.turns[i:i + 5]]):
                return "ok", ""
        return "bad", f"phone number {digits} was never spoken as one number"
    return "ok", ""


def v9_identity(c: Ctx):
    idn = c.obj.get("identity") or {}
    if (c.obj.get("not_applicable") or {}).get("is_na"):
        return
    for key in ("patient_name", "caller_name"):
        f = idn.get(key) or {}
        v = f.get("value")
        if not v:
            if f.get("certainty") == "stated":
                c.add("V9", "ERROR", f"identity.{key}", "certainty is 'stated' but the value is empty")
            continue
        toks = [t for t in normalize(v).split() if len(t) > 1]
        miss = [t for t in toks if t not in c.full_words]
        c.count("identity_supported", not miss)
        if miss:
            close = [t for t in miss if max((SequenceMatcher(None, t, w).ratio() for w in c.full_words), default=0) >= 0.8]
            c.add("V9", "WARN" if len(close) == len(miss) else "ERROR", f"identity.{key}", f"name part(s) {miss} not in the call" + (" (close spelling exists)" if close else ""))
        elif f.get("certainty") == "stated":
            for t in toks:
                near = {w for w in c.proper_words if w != t and len(w) >= 4 and len(t) >= 4 and SequenceMatcher(None, t, w).ratio() >= 0.8}
                if near:
                    c.add("V9", "WARN", f"identity.{key}", f"'stated' but the call also has similar spellings {sorted(near)[:3]} (possible name drift; policy: unclear unless resolved)")
                    break
    f = idn.get("patient_dob") or {}
    if f.get("value"):
        st, msg = _date_ok(c, f["value"])
        c.count("identity_supported", st != "bad")
        if st == "bad":
            c.add("V9", "ERROR", "identity.patient_dob", msg)
        elif st == "scattered":
            c.add("V9", "WARN", "identity.patient_dob", msg)
    f = idn.get("callback_phone") or {}
    if f.get("value"):
        st, msg = _phone_ok(c, f["value"])
        c.count("identity_supported", st == "ok")
        if st != "ok":
            c.add("V9", "ERROR", "identity.callback_phone", msg)
    f = idn.get("relationship") or {}
    rel = (f.get("value") or "").lower()
    if rel and rel != "self":
        parts = [rel] + [p for p in re.split(r"[\s-]+", rel) if len(p) >= 3 and p not in ("paid", "home", "group", "facility", "law", "in")]
        words = {rel, rel.replace("-", " ")}
        for p in parts:
            words |= {w.lower() for w in L.RELATIONSHIP_WORDS.get(p, [p])} | {w.lower() for w in L.PATIENT_WORDS.get(p, [])}
        text = c.full_text.lower()
        ok = any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)
        c.count("identity_supported", ok)
        if not ok:
            c.add("V9", "WARN", "identity.relationship", f"relationship '{rel}' is never mentioned in the call")
    for key in ("patient_name", "patient_dob", "caller_name", "relationship", "callback_phone"):
        f = idn.get(key) or {}
        if f.get("value") and f.get("certainty") == "not_stated":
            c.add("V9", "ERROR", f"identity.{key}", "value present but certainty is 'not_stated'")


# ------------------------------------------------------------------ V10 status
def v10_status(c: Ctx):
    for path, b, _ in c.items():
        for fi, f in enumerate(b.get("facts") or []):
            if not isinstance(f, dict) or f.get("type") != "action" or b.get("speaker") != "Nurse":
                continue
            status = f.get("status")
            text = b.get("text") or ""
            quote = b.get("quote") or ""
            ev = " ".join([quote, turn_text(c.turns, _ids(b))])
            done, now = bool(L.COMPLETION.search(ev)), bool(L.NOW_PROGRESS.search(ev))
            q_done, q_now, fut = bool(L.COMPLETION.search(quote)), bool(L.NOW_PROGRESS.search(quote)), bool(L.FUTURE.search(quote))
            ok = True
            if status == "completed":
                if L.PLANNED_TEXT.search(text):
                    ok = False
                    c.add("V10", "ERROR", f"{path}.text", "status is 'completed' but the text is worded as planned")
                elif not (done or now):
                    ok = False
                    c.add("V10", "ERROR", f"{path}.facts[{fi}].status", "'completed' but the nurse's words have no completion cue (I've sent / I already / it's done / right now)")
            elif status == "planned":
                if L.DONE_TEXT.search(text):
                    ok = False
                    c.add("V10", "ERROR", f"{path}.text", "status is 'planned' but the text is worded as done")
                elif q_done and not q_now and not fut:
                    ok = False
                    c.add("V10", "ERROR", f"{path}.facts[{fi}].status", "'planned' but the nurse says it is already done")
            c.count("status_consistent", ok)


# ------------------------------------------------------------------ V11 hedges, V12 negation
def v11_hedges(c: Ctx):
    for path, b, text_key in c.items():
        if path == "chief_complaint" or b.get("speaker") != "Caller":
            continue
        facts = [f for f in b.get("facts") or [] if isinstance(f, dict)]
        if not facts:
            continue
        quote = b.get("quote") or ""
        hedged = bool(L.HEDGE.search(quote))
        kept = any(f.get("certainty") == "unclear" for f in facts) or bool(L.SOFTENER.search(b.get(text_key) or ""))
        c.count("hedge_kept", (not hedged) or kept)
        if hedged and not kept:
            c.add("V11", "WARN", path, f"the caller's quote has a hedge ({L.HEDGE.search(quote).group(0)!r}) but the bullet states it as certain")


_STOP = {"with", "from", "that", "this", "have", "does", "were", "been", "when", "than", "into", "over", "some", "more", "much", "very", "other", "while", "there", "their"}


def v12_negation(c: Ctx):
    """A pertinent negative whose text names the very symptom and still affirms it ("Fever was reported" for 'no fever')."""
    for path, b, text_key in c.items():
        text = b.get(text_key) or ""
        for fi, f in enumerate(b.get("facts") or []):
            if not isinstance(f, dict):
                continue
            if f.get("type") == "pertinent_negative" or (f.get("type") == "symptom" and f.get("present") is False):
                name = str(f.get("name") or "")
                words = [w for w in normalize(name).split() if len(w) >= 4 and w not in _STOP]
                named = [w for w in words if re.search(rf"\b{re.escape(w[:max(4, len(w) - 2)])}", text, re.I)]
                rest = re.sub("|".join(re.escape(w[:max(4, len(w) - 2)]) + r"\w*" for w in words) or "$^", " ", text, flags=re.I)
                safe = bool(L.NEGATION.search(rest) or L.NORMAL_STATE.search(rest))
                flipped = bool(words) and len(named) == len(words) and not safe  # the text repeats the whole negated finding with no negation
                c.count("negation_consistent", not flipped)
                if flipped:
                    c.add("V12", "ERROR", f"{path}.text", f"the fact is a negative finding ({name!r}) but the text names it without any negation (negation flipped?)")


# ------------------------------------------------------------------ V13 risk flags, V14 NA gate
def v13_risk(c: Ctx, rule_hits: dict):
    o = c.obj
    model = [f for f in o.get("risk_flags") or [] if isinstance(f, dict)]
    model_cats = {f.get("category") for f in model}
    if (o.get("not_applicable") or {}).get("is_na"):
        return
    for cat, hits in rule_hits.items():
        covered = cat in model_cats
        c.count("rule_flags_covered_strong" if cat in RISK_ERROR_CATEGORIES else "rule_flags_covered_loose", covered)
        if not covered:
            sev = "ERROR" if cat in RISK_ERROR_CATEGORIES else "WARN"
            h = hits[0]
            c.add("V13", sev, "risk_flags", f"rule detected {cat} (turn {h['turns'][0]}: {h['quote'][:70]!r}) but the output has no such flag")
    for i, f in enumerate(model):
        if f.get("category") == "suicidal_statement":
            fired = any(h for h in rule_hits.get("suicidal_statement", []))
            if not fired:
                c.add("V13", "WARN", f"risk_flags[{i}]", "suicidal_statement flag but no suicidal wording was found (figurative language?)")


def v14_na(c: Ctx, score: int, rule_hits: dict):
    is_na = bool((c.obj.get("not_applicable") or {}).get("is_na"))
    strong = any(cat in RISK_ERROR_CATEGORIES for cat in rule_hits)
    if is_na:
        bad = score >= NA_CLINICAL_HIGH or strong
        c.count("na_gate_ok", not bad)
        if bad:
            c.add("V14", "ERROR", "not_applicable", f"marked Not Applicable but the call has clinical content (score {score}" + (", urgent wording found" if strong else "") + ")")
    else:
        weak = score <= 1 and c.n < 20
        c.count("na_gate_ok", not weak)
        if weak:
            c.add("V14", "WARN", "not_applicable", f"summarized as a clinical call but the call has almost no clinical content (score {score}, {c.n} turns)")


# ------------------------------------------------------------------ V15 coverage, V16 hygiene
def v15_coverage(c: Ctx):
    if (c.obj.get("not_applicable") or {}).get("is_na"):
        return
    summary_text = " ".join(str(v) for _, b, k in c.items() for v in [b.get(k)] + [f.get(x) for f in b.get("facts") or [] if isinstance(f, dict) for x in ("name", "med_name", "medication", "item")]).lower()
    mentioned = {m.group(0).lower() for m in _DRUG_RX.finditer(c.full_text)}
    for d in sorted(mentioned):
        covered = d in summary_text
        c.count("drug_mentions_covered", covered)
        if not covered:
            c.add("V15", "WARN", "$", f"{d} is mentioned in the call but not in the summary (it may be a chart-reading distractor)")
    promised = [t for t in c.turns if t["speaker"] == "Nurse" and L.FUTURE.search(t["text"]) and re.search(r"\b(send|page|message|call|schedule|order|notify|arrange|contact|submit)\b", t["text"], re.I)]
    if promised and not c.obj.get("response"):
        c.add("V15", "WARN", "response", f"the nurse promised actions (turn {promised[0]['id']}) but the response section is empty")


def v16_hygiene(c: Ctx):
    seen = set()
    for path, b, text_key in c.items():
        text = (b.get(text_key) or "").strip()
        if not text:
            c.add("V16", "ERROR", f"{path}.{text_key}", "empty text")
        key = (normalize(text), normalize(b.get("quote") or ""))
        if key in seen:
            c.add("V16", "WARN", path, "duplicate bullet")
        seen.add(key)
        if not str(b.get("explanation") or "").startswith("Documents"):
            c.add("V16", "INFO", f"{path}.explanation", "explanation does not start with 'Documents'")


# ------------------------------------------------------------------ entry point
def validate(obj, turns: list[dict], parse_error: str | None = None) -> dict:
    """Run every rule. `obj` is the parsed model output (or None if it did not parse)."""
    if obj is None or not isinstance(obj, dict):
        return {"findings": [{"rule": "V1", "severity": "ERROR", "path": "$", "message": f"output is not valid JSON: {parse_error or 'not an object'}"}],
                "counters": {"parse_ok": [0, 1], "schema_valid": [0, 1]}, "final_flags": [], "rule_flags": [], "n_error": 1, "n_warn": 0, "parse_ok": False}
    c = Ctx(obj, turns)
    c.count("parse_ok", True)
    errs = schema_check(obj)
    c.count("schema_valid", not errs)
    for p, m in errs[:20]:
        c.add("V1", "ERROR", p, m)
    rule_hits = RR.rule_categories(turns)
    score = RR.clinical_score(turns)
    structural_ok = not errs
    steps = [("V2", v2_sections), ("V3", v3_turns)]
    if structural_ok:  # content checks assume the structure is right
        steps += [("V4/V5", v4_v5_quotes), ("V6", v6_numbers), ("V7", v7_drugs), ("V8", v8_terms), ("V9", v9_identity), ("V10", v10_status),
                  ("V11", v11_hedges), ("V12", v12_negation), ("V13", lambda x: v13_risk(x, rule_hits)), ("V14", lambda x: v14_na(x, score, rule_hits)),
                  ("V15", v15_coverage), ("V16", v16_hygiene)]
    for name, fn in steps:
        try:
            fn(c)
        except Exception as e:  # a crashing rule must never hide the other rules
            c.add("V0", "ERROR", "$", f"validator {name} crashed: {e!r}")
    model_flags = [f for f in obj.get("risk_flags") or [] if isinstance(f, dict)] if structural_ok else []
    have = {f.get("category") for f in model_flags}
    final = list(model_flags) + [{"category": cat, "turns": h[0]["turns"], "quote": h[0]["quote"], "source": "rule"} for cat, h in rule_hits.items() if cat not in have and not (obj.get("not_applicable") or {}).get("is_na")]
    return {"findings": c.findings, "counters": {k: v for k, v in c.counters.items()}, "final_flags": final,
            "rule_flags": [{"category": cat, "turns": h[0]["turns"], "quote": h[0]["quote"]} for cat, h in rule_hits.items()],
            "na_score": score, "n_error": sum(f["severity"] == "ERROR" for f in c.findings), "n_warn": sum(f["severity"] == "WARN" for f in c.findings), "parse_ok": True}
