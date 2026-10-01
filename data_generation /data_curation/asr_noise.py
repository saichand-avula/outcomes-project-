"""Deterministic (seeded) ASR/conversation-noise injector. NO LLM.

Applied AFTER voicing, BEFORE gold is finalised. Every corruption that can change what a reader could
know is logged as an event; the gold builder turns drug-confusion events into certainty='unclear' and
name-drift events into IdField.alternates. Rates are anchored to data/calibration.json (5 real calls):
filler 11.3/1k tokens, repeats 11.9/1k, 29% of turns follow a same-speaker turn, 33% of caller turns <=3 words,
89% of numerics spoken as words, 0 [inaudible] tokens (so inaudible is OFF unless explicitly enabled).

Pipeline order: drug confusion -> name drift -> number words -> diarization shift -> fragments -> backchannels
-> fillers/repeats. Insertions never touch number tokens, so spoken digits stay recoverable.
"""
from __future__ import annotations
import copy, json, random, re
from pathlib import Path
from transcript_utils import Turn, tokens
import lexicons as L
import spoken_numbers as SN

HERE = Path(__file__).parent
FUNCTION = {"the", "a", "he", "she", "i", "and", "but", "so", "to", "of", "it", "that", "is", "was", "we", "you", "his", "her", "my", "in", "on", "for", "with", "have", "had", "just"}
DANGLING = {"and", "the", "to", "of", "a", "so", "but", "i", "he", "she", "that", "for", "with", "is", "or", "in", "my", "his", "her", "if", "because"}
ACK_START = ("all right", "okay", "thank you", "sure", "perfect", "great", "alright")
BACKCHANNELS = ["Okay.", "Uh huh.", "Mhm.", "Yes.", "Okay. Okay.", "Right.", "Yeah."]
SIMILAR = {"n": "m", "m": "n", "b": "p", "p": "b", "d": "t", "t": "d", "k": "c", "c": "k", "s": "z", "z": "s", "l": "r", "r": "l", "v": "b", "f": "v"}
NUMWORDS = set(SN.ONES) | set(SN.TEENS) | {w for w in SN.TENSW if w} | {"oh", "hundred", "thousand", "point"}


def load_profiles() -> dict:
    try:
        cal = json.loads((HERE / "data/calibration.json").read_text())
    except FileNotFoundError:   # fall back to the measured values
        cal = dict(filler_per_1k_tokens=11.3, immediate_repeat_per_1k_tokens=11.9, same_speaker_consecutive_turn_rate=0.293,
                   caller_turns_le3_words_rate=0.334)
    base = dict(filler_p=cal["filler_per_1k_tokens"] / 1000, repeat_p=cal["immediate_repeat_per_1k_tokens"] / 1000,
                split_p=cal["same_speaker_consecutive_turn_rate"] / 0.5,   # ~half of splits land on long turns
                backchannel_p=cal["caller_turns_le3_words_rate"] / 1.5)
    scale = {"low": .5, "medium": 1.0, "high": 2.0}
    prof = {k: {kk: min(vv * s, .9) for kk, vv in base.items()} for k, s in scale.items()}
    for k, d in {"low": .05, "medium": .12, "high": .25}.items(): prof[k]["diar_p"] = d      # hand count: >=2/5 calls
    for k, d in {"low": .25, "medium": .5, "high": .8}.items(): prof[k]["name_drift_p"] = d  # hand count: 4/5 calls
    return prof


PROFILES = load_profiles()


# ----------------------------------------------------------------------------- primitives
def _numish(w: str) -> bool:
    """True for number tokens, INCLUDING hyphenated numerals ("eighty-one", "seventy-two"). The original check missed those,
    so a filler could be inserted between "eighty-one" and its unit ("eighty-one uh, milligrams")."""
    x = w.lower().strip(".,?!")
    return x in NUMWORDS or any(c.isdigit() for c in w) or (("-" in x) and all(p in NUMWORDS for p in x.split("-") if p))


def name_variant(name: str, rng: random.Random) -> str:
    n = name
    cands = []
    if n[0].lower() in SIMILAR: cands.append((SIMILAR[n[0].lower()].upper() if n[0].isupper() else SIMILAR[n[0].lower()]) + n[1:])
    cands.append(n[:-1] + "ie" if n.endswith("y") else (n + "h" if n.endswith("a") else n + "e"))
    vm = {"a": "o", "o": "a", "e": "i", "i": "e", "u": "o"}
    for i, c in enumerate(n[1:], 1):
        if c in vm: cands.append(n[:i] + vm[c] + n[i + 1:]); break
    if len(n) > 4: cands.append(n[:2] + n[3:])
    cands = [c for c in dict.fromkeys(cands) if c.lower() != n.lower()]
    return rng.choice(cands) if cands else n + "e"


def _spaceless(x: str) -> str:
    return re.sub(r"[^a-z]", "", x.lower())


_REAL_NAMES = {_spaceless(n) for _d in L.FORMULARY for n in [_d["generic"], *_d["aliases"]]}


def garble_drug(word: str, rng: random.Random) -> str:
    """Fallback when the lexicon has no sound-alike: split into syllable-ish chunks / vowel swap."""
    w = word.lower(); k = rng.randint(3, max(3, len(w) - 3))
    return (w[:k] + " " + w[k:]) if rng.random() < .5 else re.sub(r"[aeiou]", lambda m: rng.choice("aeiou"), w, count=1)


def _match_case(src: str, dst: str) -> str:
    return dst.capitalize() if src[:1].isupper() else dst


def drug_confusion(turns: list[Turn], fact_id: str, generic: str, rng: random.Random) -> dict | None:
    d = next((x for x in L.FORMULARY if x["generic"] == generic), None)
    names = [generic] + (d["aliases"] if d else [])
    rx = re.compile(r"\b(" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")\b", re.I)
    pool = (d["sound_alikes"] + d["oov_mishears"]) if d else []
    # A "garble" that spells another real formulary drug (buspirone -> "bupropion") is undetectable by any validator, and one
    # that merely splits the same word ("oxy codone") is trivially recoverable, so gold 'unclear' would be unfair/wrong. Drop both.
    pool = [x for x in pool if _spaceless(x) not in _REAL_NAMES]
    heard = rng.choice(pool) if pool else garble_drug(generic, rng)
    if _spaceless(heard) in _REAL_NAMES:
        heard = generic[: max(3, len(generic) // 2)] + " " + "".join(reversed(generic[len(generic) // 2:]))   # deterministic non-word
    hit = False; orig = None
    for t in turns:
        if fact_id in t.fact_ids and rx.search(t.text):
            m = rx.search(t.text); orig = m.group(0)
            t.text = rx.sub(lambda m: _match_case(m.group(0), heard), t.text); hit = True
    return dict(kind="drug_confusion", fact_id=fact_id, original=orig, heard=heard, generic=generic) if hit else None


def name_drift(turns: list[Turn], field: str, first: str, rng: random.Random, p: float) -> dict | None:
    """Nurse read-backs of a name may drift; the person's own statements stay correct (policy P2)."""
    variant = name_variant(first, rng); rx = re.compile(r"\b" + re.escape(first) + r"\b"); seen_caller = False; changed = []
    for t in turns:
        if t.speaker == "Caller" and rx.search(t.text): seen_caller = True; continue
        if t.speaker == "Nurse" and seen_caller and rx.search(t.text) and rng.random() < p:
            t.text = rx.sub(variant, t.text, count=1); changed.append(t)
    return dict(kind="name_drift", field=field, original=first, variant=variant, n_turns=len(changed)) if changed else None


def number_words(turns: list[Turn], rng: random.Random, p_dose_time: float) -> list[dict]:
    ev = []
    for t in turns:
        t.text, e = SN.convert_numbers_in_text(t.text, rng, 1.0, p_dose_time)
        ev += [dict(x, turn_text=t.text[:60]) for x in e]
    return ev


def diarization_shift(turns: list[Turn], rng: random.Random, p: float) -> list[dict]:
    """Nurse's acknowledgement of an answer is attributed to the turn BEFORE the caller's answer (real ex 1, ex 3)."""
    ev = []; i = 0
    while i + 2 < len(turns):
        a, b, c = turns[i], turns[i + 1], turns[i + 2]
        if a.speaker == "Nurse" and "?" in a.text and b.speaker == "Caller" and c.speaker == "Nurse" and rng.random() < p:
            parts = re.split(r"(?<=[.?!])\s+", c.text, maxsplit=1)
            if len(parts) == 2 and parts[0].lower().startswith(ACK_START) and len(parts[0].split()) <= 12:
                a.text += " " + parts[0]; a.fact_ids |= c.fact_ids; c.text = parts[1]
                ev.append(dict(kind="diarization_shift", moved=parts[0])); i += 2
        i += 1
    return ev


def fragment(turns: list[Turn], rng: random.Random, p: float) -> tuple[list[Turn], list[dict]]:
    out, ev = [], []
    for t in turns:
        w = t.text.split()
        if len(w) >= 14 and rng.random() < p:
            ks = [k for k in range(5, len(w) - 4) if w[k - 1].lower().strip(".,") in DANGLING and not _numish(w[k - 1]) and not _numish(w[k])]
            ks = ks or [k for k in range(5, len(w) - 4) if w[k - 1].endswith(",") and not _numish(w[k])]
            if ks:
                k = rng.choice(ks)
                first = " ".join(w[:k]).rstrip(",") + "."; second = " ".join(w[k:]); second = second[0].upper() + second[1:]
                out += [Turn(0, t.speaker, first, set(t.fact_ids)), Turn(0, t.speaker, second, set(t.fact_ids))]
                ev.append(dict(kind="fragment", dangling=w[k - 1])); continue
        out.append(t)
    return out, ev


def backchannels(turns: list[Turn], rng: random.Random, p: float) -> tuple[list[Turn], list[dict]]:
    out, ev = [], []
    for t in turns:
        out.append(t)
        if len(t.text.split()) >= 25 and rng.random() < p:
            out.append(Turn(0, "Caller" if t.speaker == "Nurse" else "Nurse", rng.choice(BACKCHANNELS)))
            ev.append(dict(kind="backchannel"))
    return out, ev


def fillers_repeats(turns: list[Turn], rng: random.Random, pf: float, pr: float) -> list[dict]:
    ev = []
    for t in turns:
        w = t.text.split(); out = []
        for i, x in enumerate(w):
            nxt = w[i + 1] if i + 1 < len(w) else ""
            safe = not _numish(x) and not _numish(nxt) and not (out and _numish(out[-1]))
            if safe and rng.random() < pf: out.append(rng.choice(["um,", "uh,", "uh,", "um"])); ev.append(dict(kind="filler"))
            out.append(x)
            if safe and x.lower().strip(",.") in FUNCTION and rng.random() < pr * 3.3:   # repeats only hit function words (~30% of tokens)
                 out.append(x); ev.append(dict(kind="repeat"))
        t.text = " ".join(out)
    return ev


def inaudible_critical(turns, fact_id: str, surface: str) -> dict | None:
    """STRESS TEST ONLY (real calls contain no [inaudible]); replaces the value of a fact with [inaudible]."""
    for t in turns:
        if fact_id in t.fact_ids and surface in t.text:
            t.text = t.text.replace(surface, "[inaudible]"); return dict(kind="inaudible_value", fact_id=fact_id, original=surface)
    return None


# ----------------------------------------------------------------------------- orchestration
def apply_noise(turns: list[Turn], rng: random.Random, plan: dict, med_names: dict[str, str] | None = None,
                names: dict[str, str] | None = None) -> tuple[list[Turn], list[dict]]:
    """plan = FactRecord.noise_plan; med_names: {fact_id: generic}; names: {'caller_name': first, 'patient_name': first}."""
    prof = PROFILES[plan.get("asr_level", "medium")]
    turns = copy.deepcopy(turns); ev: list[dict] = []
    for fid in plan.get("drug_confusion_targets", []):
        if med_names and fid in med_names:
            e = drug_confusion(turns, fid, med_names[fid], rng)
            if e: ev.append(e)
    if plan.get("identity_drift") and names:
        for field, first in names.items():
            e = name_drift(turns, field, first, rng, prof["name_drift_p"])
            if e: ev.append(e)
    if plan.get("number_words", True): ev += number_words(turns, rng, plan.get("dose_time_words_p", .7))
    if plan.get("late_answers", False): ev += diarization_shift(turns, rng, prof["diar_p"] * 3)
    turns, e = fragment(turns, rng, prof["split_p"]); ev += e
    turns, e = backchannels(turns, rng, prof["backchannel_p"]); ev += e
    ev += fillers_repeats(turns, rng, prof["filler_p"], prof["repeat_p"])
    if plan.get("allow_inaudible"):
        for fid, surf in (plan.get("inaudible_surfaces") or {}).items():
            e = inaudible_critical(turns, fid, surf)
            if e: ev.append(e)
    for i, t in enumerate(turns, 1): t.id = i
    return turns, ev


def fact_turn_map(turns: list[Turn]) -> dict[str, list[int]]:
    m: dict[str, list[int]] = {}
    for t in turns:
        for f in t.fact_ids: m.setdefault(f, []).append(t.id)
    return m
