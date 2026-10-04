"""Transcript parsing and the user message (a verbatim copy of pipeline/pl/transcript.py: training must see exactly what the pipeline sends).

A raw transcript is one turn per line: "Nurse -> text" or "Caller -> text". Turns are numbered from 1 in order.
"""
from __future__ import annotations

import re

_TURN = re.compile(r"^(Nurse|Caller)\s*->\s*(.*)$")


def parse(raw: str) -> list[dict]:
    """-> [{"id": 1, "speaker": "Nurse", "text": "..."}]. Lines that do not match are appended to the previous turn."""
    turns: list[dict] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        m = _TURN.match(line.strip())
        if m:
            turns.append({"id": len(turns) + 1, "speaker": m.group(1), "text": m.group(2).strip()})
        elif turns:
            turns[-1]["text"] += " " + line.strip()
        else:
            turns.append({"id": 1, "speaker": "Caller", "text": line.strip()})
    return turns


def numbered(turns: list[dict]) -> str:
    return "\n".join(f"[T{t['id']}] {t['speaker']} -> {t['text']}" for t in turns)


def user_message(turns: list[dict]) -> str:
    return "CALL TRANSCRIPT\n" + numbered(turns)


def turn_text(turns: list[dict], ids) -> str:
    by = {t["id"]: t["text"] for t in turns}
    return " ".join(by[i] for i in ids if i in by)


def window(ids, n_turns: int, radius: int) -> list[int]:
    """Cited turn ids plus `radius` neighbours on each side, clipped to the transcript."""
    out = set()
    for i in ids:
        if isinstance(i, int):
            out.update(range(max(1, i - radius), min(n_turns, i + radius) + 1))
    return sorted(out)
