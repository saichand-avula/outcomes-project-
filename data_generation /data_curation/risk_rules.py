"""Rule-based high-risk scan (plan V12). Pure lexicon + negation window; no model.

A phrase hit is suppressed when a negation word appears in the NEGATION_WINDOW tokens before it, EXCEPT for
suicidal_statement hits, which are never suppressed (plan Section 3).
"""
from __future__ import annotations
import re
import lexicons as L
from transcript_utils import Turn


def tokens(text: str) -> list[str]:
    """Like transcript_utils.tokens but KEEPS apostrophes: the lexicon contains "can't breathe", "hasn't", "n't";
    stripping apostrophes (transcript_utils.tokens) would make every one of them unmatchable."""
    return re.findall(r"[a-z0-9']+", text.lower().replace("\u2019", "'"))


FILLERS = {"um", "uh", "er", "erm"}


def clean_tokens(text: str) -> list[str]:
    """Tokens with ASR fillers dropped and immediate repeats collapsed ("in in the morning" -> "in the morning").
    Real transcripts contain both (calibration.json: 11.3 fillers and 11.9 repeats per 1k tokens), and they can split a
    lexicon phrase ("almost um out"), so every phrase/cue match must run on this normalisation."""
    out: list[str] = []
    for w in tokens(text):
        if w in FILLERS or (out and out[-1] == w):
            continue
        out.append(w)
    return out


_FILLER_RX = re.compile(r"\b(?:um|uh|er|erm)\b[,.]?\s*", re.I)


def strip_fillers(text: str) -> str:
    """Remove ASR fillers but keep punctuation/digits intact (safe in front of dose/date/phone parsers)."""
    return _FILLER_RX.sub("", text)


def clean_text(text: str) -> str:
    return " ".join(clean_tokens(text))


def _is_neg(w: str) -> bool:
    return w in L.NEGATION_WORDS or w.endswith("n't")


_PHRASES = {cat: [(p, tokens(p)) for p in phrases] for cat, phrases in L.RISK_PHRASES.items()}


def scan_text(text: str) -> list[tuple[str, str]]:
    t = clean_tokens(text)
    hits = []
    for cat, phrases in _PHRASES.items():
        for phrase, ph in phrases:
            n = len(ph)
            for i in range(len(t) - n + 1):
                if t[i:i + n] != ph:
                    continue
                if cat != "suicidal_statement":
                    window = t[max(0, i - L.NEGATION_WINDOW):i]
                    if any(_is_neg(w) for w in window):
                        continue
                hits.append((cat, phrase))
    return hits


# A nurse's SCREENING QUESTION ("Any trouble breathing?") is not an assertion, and nurse speech is only an escalation
# signal when she recommends 911/ED/a visit. So nurse turns are scanned for these categories only; everything else
# must come from the caller. (Found by measuring rule precision: 80/975 routine calls fired a false breathing flag.)
NURSE_CATEGORIES = {"escalation_request"}


def scan_turns(turns: list[Turn], speakers=("Caller", "Nurse")) -> dict[str, list[int]]:
    """category -> turn ids with an unsuppressed hit.

    Scans MERGED same-speaker blocks, not single turns: ASR segmentation routinely splits a phrase across two turns
    ("I want to end my." / "Life, and I needed to tell someone."), and a per-turn scan would miss it. The hit is
    attributed to the turn where the phrase starts (plus the turn where it ends)."""
    out: dict[str, list[int]] = {}
    blocks: list[list] = []                                   # [speaker, tokens, token_turn_ids]
    for tu in turns:
        if not blocks or blocks[-1][0] != tu.speaker:
            blocks.append([tu.speaker, [], []])
        for w in clean_tokens(tu.text):
            if blocks[-1][1] and blocks[-1][1][-1] == w:
                continue
            blocks[-1][1].append(w); blocks[-1][2].append(tu.id)
    for sp, toks, tids in blocks:
        if sp not in speakers:
            continue
        for cat, phrases in _PHRASES.items():
            if sp == "Nurse" and cat not in NURSE_CATEGORIES:
                continue
            for phrase, ph in phrases:
                n = len(ph)
                for i in range(len(toks) - n + 1):
                    if toks[i:i + n] != ph:
                        continue
                    if cat != "suicidal_statement" and any(_is_neg(w) for w in toks[max(0, i - L.NEGATION_WINDOW):i]):
                        continue
                    lst = out.setdefault(cat, [])
                    for tid in sorted({tids[i], tids[i + n - 1]}):
                        if tid not in lst:
                            lst.append(tid)
    return out
