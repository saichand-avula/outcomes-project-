"""Tall-man lettering for look-alike drug names.

Subset of the FDA / ISMP "look-alike drug names with recommended tall man letters" lists,
limited to drugs plausible in hospice / home-health calls. References render `LORazepam`
but plain `morphine`, which is consistent with these lists. Applied by the renderer to
summary text (never to verbatim quotes).
"""
from __future__ import annotations

import re

TALL_MAN = [
    "ALPRAZolam", "LORazepam", "clonazePAM", "cloNIDine", "busPIRone", "buPROPion",
    "HYDROmorphone", "HYDROcodone", "oxyCODONE", "OxyCONTIN", "fentaNYL", "SUFentanil",
    "traMADol", "traZODone", "hydrOXYzine", "hydrALAZINE", "predniSONE", "prednisoLONE",
    "glipiZIDE", "glyBURIDE", "metFORMIN", "metroNIDAZOLE", "QUEtiapine", "OLANZapine",
    "risperiDONE", "rOPINIRole", "PARoxetine", "FLUoxetine", "DULoxetine", "levETIRAcetam",
    "lamoTRIgine", "carBAMazepine", "OXcarbazepine", "NIFEdipine", "niCARdipine",
    "sitaGLIPtin", "chlorproMAZINE", "methylPREDNISolone", "NexIUM",
    "ZyPREXA", "SEROquel", "KlonoPIN", "LaMICtal", "TEGretol",
]
_PATTERNS = [(re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE), t) for t in TALL_MAN]


def apply_tall_man(text: str) -> str:
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text
