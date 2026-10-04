"""Automatic quote repair (an optional post-processing step, reported separately from the raw model output).

A model often stitches two sentences with "..." or runs a quote past a clean span. Where a quote is not an exact span of the cited turns but a
close one exists (one sentence, or two in a row), the quote is replaced by that exact text. A quote with no close match is left alone, so
fabricated quotes stay ERRORs. The summary text, facts and everything else are never touched.
"""
from __future__ import annotations

import copy
import re
from difflib import SequenceMatcher

from .textnorm import collapse_spelled, normalize
from .transcript import turn_text

MIN_SIMILARITY = 0.6
SENTENCE = re.compile(r"(?<=[.?!])\s+")


def _spans(text: str):
    sents = [s.strip() for s in SENTENCE.split(text) if s.strip()]
    for i in range(len(sents)):
        yield sents[i]
        if i + 1 < len(sents):
            yield sents[i] + " " + sents[i + 1]


def repair_quote(quote: str, cited_text: str):
    """-> exact replacement text, or None when the quote is already exact or nothing is close enough"""
    nq = normalize(collapse_spelled(quote))
    if not nq or f" {nq} " in f" {normalize(collapse_spelled(cited_text))} ":
        return None
    best, best_r = None, 0.0
    for sp in _spans(cited_text):
        r = SequenceMatcher(None, nq, normalize(collapse_spelled(sp))).ratio()
        if r > best_r:
            best, best_r = sp, r
    return best if best and best_r >= MIN_SIMILARITY else None


def repair(obj, turns: list[dict]):
    """-> (repaired copy of obj, number of quotes replaced)"""
    if not isinstance(obj, dict):
        return obj, 0
    out, n = copy.deepcopy(obj), 0
    n_turns = len(turns)
    holders = [out.get("chief_complaint")] + [b for s in ("assessment", "response", "education", "risk_flags") for b in (out.get(s) or [])]
    for b in holders:
        if not isinstance(b, dict) or not isinstance(b.get("quote"), str):
            continue
        ids = [i for i in (b.get("turns") or []) if isinstance(i, int) and 1 <= i <= n_turns]
        if not ids:
            continue
        new = repair_quote(b["quote"], turn_text(turns, ids))
        if new:
            b["quote"] = new
            n += 1
    return out, n
