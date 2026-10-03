"""Near-duplicate check across splits: character 5-gram Jaccard similarity of whole transcripts.

Reports the closest validation-vs-train pairs and fails (exit 1) if any pair is >= 0.5.
Run: python3 code/data/dupcheck.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import load_split  # noqa: E402
from common.textnorm import normalize  # noqa: E402

THRESHOLD = 0.5


def grams(text: str, n: int = 5) -> set[str]:
    t = normalize(text)
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def main() -> int:
    train = [(c["call_id"], grams(c["transcript"])) for c in load_split("train")]
    val = [(c["call_id"], grams(c["transcript"])) for c in load_split("val")]
    pairs = []
    for vid, vg in val:
        for tid, tg in train:
            pairs.append((len(vg & tg) / len(vg | tg), vid, tid))
    pairs.sort(reverse=True)
    print("closest validation-vs-train transcript pairs (5-gram Jaccard):")
    for j, v, t in pairs[:5]:
        print(f"  {j:.3f}  {v} ~ {t}")
    worst = pairs[0][0]
    print(f"max similarity {worst:.3f}; threshold {THRESHOLD}")
    return 1 if worst >= THRESHOLD else 0


if __name__ == "__main__":
    sys.exit(main())
