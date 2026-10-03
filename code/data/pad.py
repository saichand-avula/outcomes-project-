"""Insert untagged filler lines after the transcript line containing an anchor substring.
Usage (python):  from pad import pad; pad(path, [(anchor, "line\nline\n"), ...])"""
import sys


def pad(path, items):
    lines = open(path).read().split("\n")
    for anchor, block in items:
        if not block.strip():
            continue
        idx = next((i for i, l in enumerate(lines) if anchor in l and l.startswith("  ")), None)
        if idx is None:
            print(f"anchor not found (skipped): {anchor[:60]}")
            continue
        new = [l for l in block.rstrip("\n").split("\n")]
        lines[idx + 1:idx + 1] = new
    open(path, "w").write("\n".join(lines))
