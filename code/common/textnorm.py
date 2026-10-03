"""Text normalization and spoken-number candidate extraction.

Used by the gold validator (and later by production validators) to check that
quotes, numbers and identity values in a summary are supported by transcript turns.
"""
from __future__ import annotations

import re

_QUOTE_MAP = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace and immediate word repeats."""
    t = text.translate(_QUOTE_MAP).lower()
    t = t.replace("'", "")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    words = t.split()
    out: list[str] = []
    for w in words:
        if out and out[-1] == w:
            continue
        out.append(w)
    return " ".join(out)


def collapse_spelled(text: str) -> str:
    """'M-E-R-C-E-R' or 'T, T, A, M, S' -> 'MERCER' / 'TTAMS' (adds spelled names as words)."""
    pattern = re.compile(r"\b(?:[A-Za-z](?:\s*[,\-\.]\s*|\s+)){2,}[A-Za-z]\b")
    return pattern.sub(lambda m: re.sub(r"[^A-Za-z]", "", m.group(0)), text)


# ---------------------------------------------------------------- spoken numbers
_SMALL = {
    "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_ORD = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
    "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
    "twentieth": 20, "thirtieth": 30,
}
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
_SCALE = {"hundred": 100, "thousand": 1000}
_NUMBER_WORDS = set(_SMALL) | set(_TENS) | set(_ORD) | set(_SCALE) | {"point", "a", "and"}


def _tokens(text: str) -> list[str]:
    t = text.translate(_QUOTE_MAP).lower().replace("-", " ")
    t = re.sub(r"[.?!;]+(?=\s|$)", " | ", t)  # sentence boundary: spoken numbers never run across it
    return re.findall(r"[a-z]+|\d+(?:\.\d+)?(?::\d{2})?|\|", t)


def _parse_run(words: list[str]) -> tuple[list[int], list[str]]:
    """Parse a run of number words into chunks.

    'two zero two' -> [2, 0, 2]; 'nineteen fifty one' -> [19, 51]; 'one hundred twenty five' -> [125];
    'two thousand eighteen' -> [2018]; 'ten eight' -> [10, 8]. Decimals ('zero point two five') go to extras.
    """
    chunks: list[int] = []
    extras: list[str] = []
    th = 0           # thousands part of the chunk being built
    cur = None       # below-thousand part
    mode = None      # None | unit | teen | tens | closed | hundred | thousand

    def flush():
        nonlocal th, cur, mode
        if th or cur is not None:
            chunks.append(th + (cur or 0))
        th, cur, mode = 0, None, None

    i = 0
    while i < len(words):
        w = words[i]
        if w == "point":
            whole = th + (cur or 0) if (th or cur is not None) else 0
            j = i + 1
            digs = []
            while j < len(words) and words[j] in _SMALL and _SMALL[words[j]] < 10:
                digs.append(str(_SMALL[words[j]]))
                j += 1
            if digs:
                extras.append(f"{whole}.{''.join(digs)}")
                extras.append(f".{''.join(digs)}")
            flush()
            i = j
            continue
        if w == "and":
            if mode not in ("hundred", "thousand"):
                flush()
            i += 1
            continue
        if w == "a":
            if i + 1 < len(words) and words[i + 1] in _SCALE:
                flush()
                cur, mode = 1, "unit"
            i += 1
            continue
        if w == "hundred":
            cur = (cur if cur is not None and cur < 100 else 1) * 100 if (cur is None or cur < 100) else cur
            mode = "hundred"
        elif w == "thousand":
            th = ((cur if cur is not None else 1)) * 1000
            cur, mode = None, "thousand"
        elif w in _TENS:
            if mode in ("hundred", "thousand"):
                cur = (cur or 0) + _TENS[w]
            else:
                flush()
                cur = _TENS[w]
            mode = "tens"
        else:
            v = _SMALL.get(w, _ORD.get(w))
            if v is None:
                i += 1
                continue
            if mode == "tens" and 0 < v < 10 and (cur or 0) % 10 == 0:
                cur += v
                mode = "closed"
            elif mode in ("hundred", "thousand"):
                cur = (cur or 0) + v
                mode = "closed"
            else:
                flush()
                cur = v
                mode = "teen" if v >= 10 else "unit"
        i += 1
    flush()
    return chunks, extras


def _time_variants(h: int, m: int) -> set[str]:
    out = set()
    if 1 <= h <= 12 and 0 <= m <= 59:
        for hh in {h % 12, h % 12 + 12, h}:
            out.add(f"{hh}{m:02d}")
            out.add(f"{hh:02d}{m:02d}")
            out.add(f"{hh}:{m:02d}")
            out.add(f"{hh:02d}:{m:02d}")
    return out


def number_candidates(text: str) -> set[str]:
    """All numeric strings a reader could derive from `text` (digits, spoken numbers, times, months)."""
    cands: set[str] = set()
    toks = _tokens(text)
    # digit tokens
    for t in toks:
        if re.fullmatch(r"\d+(?:\.\d+)?", t):
            cands.add(t)
            cands.add(t.lstrip("0") or "0")
            if "." in t:
                cands.add(t.split(".")[0])
        elif re.fullmatch(r"\d{1,2}:\d{2}", t):
            h, m = (int(x) for x in t.split(":"))
            cands |= {str(h), str(m), f"{m:02d}"} | _time_variants(h, m)
    # phone-like digit groups (202-555-0101, 555 0101)
    for m in re.finditer(r"\d[\d\-\s\.\(\)]{6,}\d", text):
        digits = re.sub(r"\D", "", m.group(0))
        cands.add(digits)
    # month names
    for t in toks:
        if t in _MONTHS:
            cands.add(str(_MONTHS[t]))
            cands.add(f"{_MONTHS[t]:02d}")
    # spoken number runs
    i = 0
    while i < len(toks):
        starts_decimal = toks[i] == "point" and i + 1 < len(toks) and toks[i + 1] in _SMALL and _SMALL[toks[i + 1]] < 10
        if toks[i] in _NUMBER_WORDS and (toks[i] not in ("a", "and", "point") or starts_decimal):
            j = i
            while j < len(toks) and toks[j] in _NUMBER_WORDS:
                j += 1
            run = toks[i:j]
            chunks, extras = _parse_run(run)
            for c in chunks:
                cands.add(str(c))
            cands |= set(extras)
            if len(chunks) >= 2:
                cands.add("".join(str(c) for c in chunks))
                # every contiguous sub-concatenation (phone groups, years, dates)
                for a in range(len(chunks)):
                    for b in range(a + 2, len(chunks) + 1):
                        cands.add("".join(str(c) for c in chunks[a:b]))
                for a in range(len(chunks) - 1):
                    cands |= _time_variants(chunks[a], chunks[a + 1])
            # "six o'clock" style
            if j < len(toks) and toks[j] == "o" and j + 1 < len(toks) and toks[j + 1] == "clock" and chunks:
                cands |= _time_variants(chunks[-1], 0)
            i = j
        else:
            i += 1
    # fractions: "half a milliliter" -> 0.5, "a quarter" -> 0.25
    if "half" in toks:
        cands |= {"0.5", ".5"}
        # "seven and a half" -> 7.5
        for k in range(1, len(toks) - 2):
            if toks[k:k + 3] == ["and", "a", "half"] and toks[k - 1] in _NUMBER_WORDS:
                chunks, _ = _parse_run([toks[k - 1]])
                for c in chunks:
                    cands.add(f"{c}.5")
    if "quarter" in toks:
        cands |= {"0.25", ".25"}
    # bare hours ("at six") as times
    for c in list(cands):
        if c.isdigit() and 1 <= int(c) <= 12:
            cands |= _time_variants(int(c), 0)
    return cands


def numbers_in(text: str) -> list[str]:
    """Digit numbers written in summary text, skipping '/10' scale denominators."""
    t = text.translate(_QUOTE_MAP)
    out = []
    for m in re.finditer(r"\d{1,2}:\d{2}|\d+(?:\.\d+)?", t):
        before = t[max(0, m.start() - 1):m.start()]
        if before == "/" and m.group(0) == "10":
            continue
        out.append(m.group(0))
    return out


def supported(num: str, cands: set[str]) -> bool:
    if num in cands or (num.lstrip("0") or "0") in cands:
        return True
    try:
        f = float(num)
    except ValueError:
        return False
    for c in cands:
        try:
            if float(c) == f:
                return True
        except ValueError:
            continue
    return False
