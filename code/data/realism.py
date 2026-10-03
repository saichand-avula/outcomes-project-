"""Realism check: compare authored transcripts with the 5 real examples on surface statistics.

Target: each metric within +/-30% of the real-5 value (plan.md §2.3 step 6).
Run: python3 code/data/realism.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import ROOT, load_split, parse_transcript  # noqa: E402

FILLERS = {"um", "uh", "mhm", "hmm", "uh-huh", "huh", "ah", "oh"}
NUM_WORDS = {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
             "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
             "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand"}


def stats(transcripts: list[list[dict]]) -> dict[str, float]:
    toks = turns = caller_turns = short_caller = frag = same = fill = rep = numw = chars = 0
    for turns_ in transcripts:
        prev = None
        for t in turns_:
            words = re.findall(r"[A-Za-z']+|\d+", t["text"].lower())
            toks += len(words)
            turns += 1
            chars += len(t["text"])
            fill += sum(w in FILLERS for w in words)
            rep += sum(1 for a, b in zip(words, words[1:]) if a == b)
            numw += sum(w in NUM_WORDS for w in words)
            if prev == t["speaker"]:
                same += 1
            prev = t["speaker"]
            if t["speaker"] == "Caller":
                caller_turns += 1
                short_caller += len(words) <= 3
                frag += bool(re.search(r"\b(and|to|the|a|of|for|that|but|or|with|my|her|his)\.?\s*$", t["text"].lower()))
    k = max(toks, 1) / 1000
    return {
        "calls": len(transcripts),
        "mean_chars": chars / max(len(transcripts), 1),
        "mean_turns": turns / max(len(transcripts), 1),
        "caller_short_turn_rate": short_caller / max(caller_turns, 1),
        "caller_dangling_fragment_rate": frag / max(caller_turns, 1),
        "same_speaker_consecutive_rate": same / max(turns, 1),
        "fillers_per_1k": fill / k,
        "immediate_repeats_per_1k": rep / k,
        "number_words_per_1k": numw / k,
    }


def main() -> int:
    refs = yaml.safe_load((ROOT / "synthetic_clinical_summary_examples.yaml").read_text())["examples"]
    real = stats([parse_transcript(e["input_transcript"]) for e in refs])
    rows = {"real-5": real}
    for split in ("train", "val"):
        calls = [c for c in load_split(split) if c["setup"].get("scenario_category") != "not_applicable"]
        if calls:
            rows[split] = stats([c["turns"] for c in calls])
    keys = list(real)
    print(f"{'metric':32}" + "".join(f"{k:>12}" for k in rows))
    for m in keys:
        line = f"{m:32}"
        for name, s in rows.items():
            v = s[m]
            mark = ""
            if name != "real-5" and m not in ("calls", "mean_chars", "mean_turns") and real[m]:
                mark = "" if abs(v - real[m]) / real[m] <= 0.30 else "*"
            line += f"{v:11.3f}{mark or ' '}" if isinstance(v, float) else f"{v:11d} "
        print(line)
    print("\n* = outside +/-30% of real-5 (length differs by design: synthetic set is 72% short calls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
