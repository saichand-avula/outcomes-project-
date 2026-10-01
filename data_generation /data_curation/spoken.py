"""Single source of truth for how structured values are SPOKEN in transcripts and read back by validators.

The voicer, gold builder and validators all import from here, so a value voiced one way can always be
recognised and inverted. Everything is a plain dict/list so tests can assert coverage (every formulary
frequency/route/unit must be speakable).
"""
from __future__ import annotations
import re
import spoken_numbers as SN

FREQ_SPOKEN: dict[str, list[str]] = {
    "daily": ["once a day", "daily"],
    "BID": ["twice a day"],
    "TID": ["three times a day"],
    "QID": ["four times a day"],
    "q2h PRN": ["every two hours as needed"],
    "q4h": ["every four hours"],
    "q4h PRN": ["every four hours as needed"],
    "q6h PRN": ["every six hours as needed"],
    "q8h PRN": ["every eight hours as needed"],
    "q72h": ["every seventy-two hours", "every three days"],
    "at bedtime": ["at bedtime"],
    "daily at bedtime": ["once a day at bedtime"],
    "daily in the morning": ["once a day in the morning"],
    "daily in the evening": ["once a day in the evening"],
    "daily after a meal": ["once a day after a meal"],
    "daily PRN": ["once a day as needed"],
    "TID PRN": ["three times a day as needed"],
    "BID PRN": ["twice a day as needed"],
    "BID with meals": ["twice a day with meals"],
    "12 hours on, 12 hours off": ["twelve hours on and twelve hours off"],
}

ROUTE_SPOKEN: dict[str, list[str]] = {
    "PO": ["by mouth"],
    "SL": ["under the tongue"],
    "transdermal": ["on the skin"],
    "inhaled": ["inhaled"],
    "PR": ["rectally"],
}

LAST_DOSE_SPOKEN = {"1 hour ago": "an hour ago", "2 hours ago": "two hours ago", "this morning": "this morning"}

# relationship value -> surface words a speaker may use (for recoverability checks)
REL_WORDS: dict[str, set[str]] = {
    "spouse": {"wife", "husband", "spouse"},
    "daughter": {"daughter"}, "son": {"son"},
    "mother": {"mom", "mother"}, "father": {"dad", "father"},
    "sister": {"sister"}, "granddaughter": {"granddaughter"}, "friend": {"friend"},
    "facility nurse": {"nurse"}, "patient (self)": {"myself", "self"},
}


def inv_table(table: dict[str, list[str]]) -> dict[str, str]:
    return {v: k for k, vs in table.items() for v in vs}


def sev_spoken(sev: str | None) -> str | None:
    """'6/10' -> 'six out of ten'; graded words pass through."""
    if sev is None:
        return None
    m = re.fullmatch(r"(\d+)/10", sev)
    return f"{SN.int_to_words(int(m.group(1)))} out of ten" if m else sev


def sev_numeric_from_spoken(text: str) -> str | None:
    """Invert 'six out of ten' (or 'six out of ten' with noise) -> '6/10'."""
    t = SN.toks(text)
    for i in range(len(t) - 3):
        if t[i + 1:i + 4] == ["out", "of", "ten"]:
            p = SN.parse_number(t, i)
            if p and p[0].isdigit():
                return f"{p[0]}/10"
    return None


def qty_spoken(q: str | None) -> str | None:
    """'3 doses' -> 'three doses'; '0 doses' -> 'zero doses'."""
    if q is None:
        return None
    m = re.fullmatch(r"(\d+) doses", q)
    return f"{SN.int_to_words(int(m.group(1)))} doses" if m else q


def dose_str(dose: str | None, unit: str | None) -> str | None:
    """Digit form (the number converter turns it into words later)."""
    if dose is None:
        return None
    return f"{dose} {unit}" if unit else dose
