"""Authoring helper: add `|| A#` tags to transcript lines that name a drug from the fact record but are untagged.

Usage: python3 code/data/autotag.py <file.yaml> ...
Only touches lines without an existing `||`; appends tags of every assessment/response item whose
medication_name_spoken / medication_name_true appears in the line.
"""
import re
import sys
import yaml

for p in sys.argv[1:]:
    s = open(p).read()
    c = yaml.safe_load(s)
    names = []
    for it in (c.get("assessment") or []) + (c.get("response") or []):
        for k in ("medication_name_spoken", "medication_name_true"):
            n = it.get(k)
            if n:
                names.append((n.lower(), it["item_id"]))
    out = []
    in_t = False
    n_tag = 0
    for l in s.split("\n"):
        if l.startswith("transcript:"):
            in_t = True
        elif in_t and not l.startswith("  "):
            in_t = False
        if in_t and l.startswith(("  Nurse ->", "  Caller ->")) and "||" not in l:
            low = l.lower()
            ids = sorted({i for n, i in names if re.search(r"\b" + re.escape(n), low)})
            if ids:
                l += " || " + ", ".join(ids)
                n_tag += 1
        out.append(l)
    open(p, "w").write("\n".join(out))
    print(p, "tagged", n_tag)
