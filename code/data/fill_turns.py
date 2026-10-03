"""Fill gold `turns:` lists automatically (authoring convenience; the validator still checks everything).

In a gold section write `turns: auto`. This script replaces it with:
  * identity.<field>.turns  -> all transcript turns tagged with that identity key
  * chief_complaint / bullets / risk_flags -> the turn(s) whose text contains the quote
    (speaker-matched; first match wins; warns when ambiguous)

Usage: python3 code/data/fill_turns.py [--force] [path ...]     (default: all authoring files)
--force also recomputes turns that are already numbers.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import AUTHORING, IDENTITY_IDS, parse_transcript  # noqa: E402
from common.textnorm import normalize  # noqa: E402

TOKEN = re.compile(r"turns:\s*(\[[^\]]*\]|auto)")


def find_turns(turns: list[dict], quote: str, speaker: str | None):
    nq = normalize(quote)
    hits = []
    for t in turns:
        actual = t["speaker"]
        if t["label_error"]:
            actual = "Caller" if actual == "Nurse" else "Nurse"
        if nq and nq in normalize(t["text"]):
            hits.append((t["id"], actual))
    pref = [i for i, sp in hits if speaker is None or sp == speaker]
    return pref[:1], len(pref)


def process(path: Path, force: bool) -> list[str]:
    msgs = []
    text = path.read_text()
    data = yaml.safe_load(text)
    turns = parse_transcript(data["transcript"])
    gold = data["gold"]
    todo: list[list[int] | None] = []   # in document order

    def idn_turns(key):
        return [t["id"] for t in turns if key in t["fact_ids"]]

    for key, val in gold.items():
        if key == "identity":
            for f in IDENTITY_IDS:
                if isinstance(val.get(f), dict):
                    todo.append(idn_turns(f))
        elif key == "chief_complaint":
            ids, n = find_turns(turns, val["quote"], val.get("speaker"))
            if not ids:
                msgs.append(f"chief_complaint quote not found: {val['quote'][:60]!r}")
            elif n > 1:
                msgs.append(f"chief_complaint quote ambiguous ({n} turns), used first")
            todo.append(ids)
        elif key in ("assessment", "response", "education", "risk_flags"):
            for item in val or []:
                ids, n = find_turns(turns, item["quote"], item.get("speaker"))
                if not ids:
                    msgs.append(f"{key} quote not found: {item['quote'][:60]!r}")
                elif n > 1:
                    msgs.append(f"{key} quote ambiguous ({n} turns), used first: {item['quote'][:40]!r}")
                todo.append(ids)

    head, _, tail = text.partition("\ngold:\n")
    if not tail:
        return ["no gold section"]
    found = list(TOKEN.finditer(tail))
    if len(found) != len(todo):
        return [f"expected {len(todo)} turns fields in gold, found {len(found)}"]
    out, last = [], 0
    for m, ids in zip(found, todo):
        if m.group(1) != "auto" and not force:
            continue
        out.append(tail[last:m.start()])
        out.append(f"turns: {ids}")
        last = m.end()
    out.append(tail[last:])
    new = head + "\ngold:\n" + "".join(out)
    if new != text:
        path.write_text(new)
    return msgs


def main(argv: list[str]) -> int:
    force = "--force" in argv
    paths = [Path(a) for a in argv if not a.startswith("--")]
    if not paths:
        paths = sorted(AUTHORING.glob("*/*.yaml"))
    bad = 0
    for p in paths:
        for m in process(p, force):
            print(f"{p.stem}: {m}")
            bad += 1
    print(f"filled {len(paths)} files, {bad} messages")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
