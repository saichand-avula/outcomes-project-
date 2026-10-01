"""Deterministic pre-processing (plan step 1): machine-extracted CANDIDATES the model must verify against the transcript.

Spoken numbers are normalised to digits by code (never by the model), because LLMs are unreliable at spelling out digit
sequences. Ambiguity is surfaced, not resolved: a century-ambiguous date or an 'oh' that could be a digit or an interjection
gives several candidates. Fillers are stripped before parsing; consecutive same-speaker turns are merged (ASR splits numbers).
"""
from __future__ import annotations
import re

import lexicons as L
import risk_rules as RR
import spoken_numbers as SN
from transcript_utils import Turn
from validate_gold import DRUG_RX

_ALIAS = {a.lower(): d["generic"] for d in L.FORMULARY for a in [d["generic"], *d["aliases"]]}
_NUMTOK = re.compile(r"\b(\d+|zero|one|two|three|four|five|six|seven|eight|nine|oh)\b", re.I)


def _blocks(turns: list[Turn]) -> list[tuple[str, list[Turn]]]:
    out: list[tuple[str, list[Turn]]] = []
    for t in turns:
        if out and out[-1][0] == t.speaker:
            out[-1][1].append(t)
        else:
            out.append((t.speaker, [t]))
    return out


def candidates(turns: list[Turn]) -> dict:
    phones, dobs, drugs = [], [], []
    for sp, blk in _blocks(turns):
        text = RR.strip_fillers(" ".join(t.text for t in blk))
        tids = [t.id for t in blk if _NUMTOK.search(RR.strip_fillers(t.text))] or [blk[0].id]
        for v in SN.phone_candidates(text):
            if len(v) == 10:
                phones.append(dict(value=v, speaker=sp, turn_ids=tids))
        for c in SN.date_candidates(text):
            y = int(c["iso"][:4])
            if 1900 <= y <= 2026:
                dobs.append(dict(value=c["iso"], speaker=sp, turn_ids=tids, century_ambiguous=bool(c["century_ambiguous"])))
    for t in turns:
        for m in DRUG_RX.finditer(RR.strip_fillers(t.text)):
            drugs.append(dict(surface=m.group(0), generic=_ALIAS.get(m.group(0).lower()), turn_id=t.id))
    seen = set()
    uniq = lambda xs, k: [x for x in xs if not (k(x) in seen or seen.add(k(x)))]
    return dict(phones=uniq(phones, lambda x: (x["value"], x["speaker"])), dobs=uniq(dobs, lambda x: (x["value"], x["speaker"])),
                drugs=drugs)


def render_candidates(c: dict) -> str:
    lines = []
    for p in c["phones"]:
        lines.append(f"PHONE {p['value']} ({p['speaker']}, T{','.join(map(str, p['turn_ids']))})")
    for d in c["dobs"]:
        lines.append(f"DATE {d['value']} ({d['speaker']}, T{','.join(map(str, d['turn_ids']))})" + (" [century inferred]" if d["century_ambiguous"] else ""))
    for g in c["drugs"]:
        lines.append(f"DRUG '{g['surface']}' -> {g['generic']} (T{g['turn_id']})")
    return "\n".join(lines) or "(none)"
