"""Turn splitting, normalization and anchor resolution.

Normalization = lower-case, strip punctuation, collapse immediate word repeats
(the rule under which all 58 reference quotes in the 5 examples are recoverable).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

TURN_RE = re.compile(r"^(Nurse|Caller) -> ?(.*)$")


@dataclass
class Turn:
    id: int                      # 1-based, T1..Tn
    speaker: str
    text: str
    fact_ids: set = field(default_factory=set)   # filled by voicing step (synthetic)


def split_turns(transcript: str) -> list[Turn]:
    turns: list[Turn] = []
    for ln in transcript.strip().split("\n"):
        m = TURN_RE.match(ln.strip())
        if m:
            turns.append(Turn(len(turns) + 1, m.group(1), m.group(2).strip()))
        elif turns and ln.strip():           # continuation line
            turns[-1].text += " " + ln.strip()
    return turns


def join_turns(turns: list[Turn]) -> str:
    return "\n".join(f"{t.speaker} -> {t.text}" for t in turns)


def tokens(s: str) -> list[str]:
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()


def norm(s: str) -> str:
    out: list[str] = []
    for w in tokens(s):
        if not out or out[-1] != w:
            out.append(w)
    return " ".join(out)


def speaker_blocks(turns: list[Turn]):
    """Merge consecutive same-speaker turns -> [(speaker, [turn_ids], tokens, token_turn_ids)]."""
    blocks = []
    for t in turns:
        if blocks and blocks[-1][0] == t.speaker:
            b = blocks[-1]
        else:
            b = [t.speaker, [], [], []]
            blocks.append(b)
        b[1].append(t.id)
        for w in tokens(t.text):
            if b[2] and b[2][-1] == w:       # collapse immediate repeat
                continue
            b[2].append(w)
            b[3].append(t.id)
    return [tuple(b) for b in blocks]


def find_anchor(turns: list[Turn], speaker: str, anchor: str) -> list[list[int]]:
    """All hits of `anchor` inside same-speaker blocks -> list of turn-id lists."""
    a = norm(anchor).split()
    hits = []
    for sp, _ids, toks, tids in speaker_blocks(turns):
        if sp != speaker:
            continue
        for i in range(len(toks) - len(a) + 1):
            if toks[i:i + len(a)] == a:
                hits.append(sorted(set(tids[i:i + len(a)])))
    return hits


def resolve_anchor(turns: list[Turn], speaker: str, anchor: str,
                   occurrence: int | None = None) -> list[int]:
    hits = find_anchor(turns, speaker, anchor)
    if not hits:
        raise ValueError(f"anchor not found for {speaker}: {anchor!r}")
    if occurrence is None:
        if len(hits) > 1:
            raise ValueError(f"anchor ambiguous ({len(hits)} hits) for {speaker}: {anchor!r}; "
                             f"hits at turns {hits} - pass occurrence=")
        return hits[0]
    return hits[occurrence]
