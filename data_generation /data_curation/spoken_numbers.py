"""Spoken-number converter (digits -> words) and inverse normalizer (words -> digits).

Forward side is used by asr_noise.py to make synthetic transcripts sound like ASR output
(89% of numerics in the real calls are spoken words). Inverse side is used by validators
(V5 numbers, identity checks) and by gold-vs-output comparison. Round-trip tested.
"""
from __future__ import annotations
import datetime as dt, random, re
from typing import Optional

ONES = "zero one two three four five six seven eight nine".split()
TEENS = "ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENSW = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
ORD_SMALL = ("first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth fourteenth fifteenth "
             "sixteenth seventeenth eighteenth nineteenth twentieth").split()
CUR_YY = 26   # two-digit years <= this are also read as 20YY

W2N = {w: i for i, w in enumerate(ONES)}
W2N.update({w: 10 + i for i, w in enumerate(TEENS)})
W2N.update({w: 10 * i for i, w in enumerate(TENSW) if w})
W2N["oh"] = 0
ORD2N = {w: i + 1 for i, w in enumerate(ORD_SMALL)}
ORD2N["thirtieth"] = 30
UNIT_CANON = {"ml": "mL", "mil": "mL", "mils": "mL", "milliliter": "mL", "milliliters": "mL", "millilitre": "mL", "millilitres": "mL",
              "mg": "mg", "milligram": "mg", "milligrams": "mg", "mcg": "mcg", "microgram": "mcg", "micrograms": "mcg",
              "g": "g", "gram": "g", "grams": "g", "tablet": "tablet", "tablets": "tablet", "pill": "tablet", "pills": "tablet",
              "puff": "puffs", "puffs": "puffs", "drop": "drops", "drops": "drops", "patch": "patch", "patches": "patch",
              "iu": "IU", "units": "IU", "capsule": "capsule", "capsules": "capsule"}
UNIT_SPOKEN = {"mcg/hr": ["mcg per hour", "micrograms per hour", "mcg/hr"], "mL": ["milliliters", "mils", "mil", "mL"], "mg": ["milligrams", "mg", "milligrams"], "mcg": ["micrograms", "mcg"],
               "g": ["grams"], "tablet": ["tablet", "pill"], "puffs": ["puffs"], "drops": ["drops"], "patch": ["patch"], "IU": ["units"],
               "capsule": ["capsule"]}


# ----------------------------------------------------------------------------- forward: numbers -> words
def int_to_words(n: int, hyphen: bool = True) -> str:
    if n < 10: return ONES[n]
    if n < 20: return TEENS[n - 10]
    if n < 100:
        t, o = divmod(n, 10)
        return TENSW[t] if o == 0 else TENSW[t] + ("-" if hyphen else " ") + ONES[o]
    if n < 1000:
        h, r = divmod(n, 100)
        return ONES[h] + " hundred" + (" " + int_to_words(r, hyphen) if r else "")
    if n < 10000:
        t, r = divmod(n, 1000)
        return ONES[t] + " thousand" + (" " + int_to_words(r, hyphen) if r else "")
    raise ValueError(n)


def digits_to_words(s: str, rng: random.Random | None = None, p_oh: float = 0.0) -> str:
    return " ".join(("oh" if (c == "0" and rng and rng.random() < p_oh) else ONES[int(c)]) for c in s if c.isdigit())


def phone_to_words(p: str, rng: random.Random | None = None, grouped: bool = False) -> str:
    p = re.sub(r"\D", "", p)
    if grouped and len(p) == 10:
        return ", ".join(digits_to_words(g, rng) for g in (p[:3], p[3:6], p[6:]))
    return digits_to_words(p, rng)


def year_to_words(y: int, hyphen: bool = True) -> str:
    if 2000 <= y <= 2099:
        r = y - 2000
        return "two thousand" + ("" if r == 0 else " " + int_to_words(r, hyphen))
    if 1900 <= y <= 1999:
        r = y - 1900
        return "nineteen " + ("hundred" if r == 0 else ("oh " + ONES[r] if r < 10 else int_to_words(r, hyphen)))
    raise ValueError(y)


def ordinal_to_words(n: int, hyphen: bool = True) -> str:
    if n <= 20: return ORD_SMALL[n - 1]
    if n == 30: return "thirtieth"
    t, o = divmod(n, 10)
    return TENSW[t] + ("-" if hyphen else " ") + ORD_SMALL[o - 1]


def date_to_words(iso: str, style: str = "month_name", rng: random.Random | None = None) -> str:
    """styles: month_name ('June fourth, nineteen fifty-one'), numeric ('six four nineteen fifty-one'),
    numeric_yy ('six four fifty-one': century dropped, as in real example 2)."""
    d = dt.date.fromisoformat(iso); hy = not (rng and rng.random() < .4)
    if style == "month_name":
        return f"{d.strftime('%B')} {ordinal_to_words(d.day, hy)}, {year_to_words(d.year, hy)}"
    if style == "numeric":
        return f"{int_to_words(d.month)} {int_to_words(d.day)} {year_to_words(d.year, hy)}"
    if style == "numeric_yy":
        yy = d.year % 100
        return f"{int_to_words(d.month)} {int_to_words(d.day)} {'oh ' + ONES[yy] if yy < 10 else int_to_words(yy, hy)}"
    raise ValueError(style)


def decimal_to_words(v: str, hyphen: bool = True) -> str:
    ip, _, fp = v.partition(".")
    w = int_to_words(int(ip), hyphen)
    return w if not fp else f"{w} point {digits_to_words(fp)}"


def clock_to_words(hhmm: str, rng: random.Random | None = None) -> str:
    h, m = (int(x) for x in hhmm.split(":"))
    h12 = h % 12 or 12
    if m == 0: return f"{int_to_words(h12)} o'clock"
    return f"{int_to_words(h12)} {'oh ' + ONES[m] if m < 10 else int_to_words(m)}"


# ----------------------------------------------------------------------------- inverse: words -> numbers
def toks(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower().replace("-", " "))


def _small(t: list[str], i: int) -> list[tuple[int, int]]:
    """Longest parse of a 0-99 number (cardinal or ordinal) starting at i -> [(value, next_i)] (0 or 1 items)."""
    if i >= len(t): return []
    w = t[i]
    if w.isdigit() and len(w) <= 2: return [(int(w), i + 1)]
    if w in ORD2N:
        return [(ORD2N[w], i + 1)]
    if w in W2N and w != "oh":
        v = W2N[w]
        if v >= 20 and i + 1 < len(t):                      # tens + ones / tens + ordinal ("twenty five", "twenty first")
            nxt = t[i + 1]
            if nxt in ONES and nxt != "zero": return [(v + W2N[nxt], i + 2)]
            if nxt in ORD2N and ORD2N[nxt] < 10: return [(v + ORD2N[nxt], i + 2)]
        return [(v, i + 1)]
    return []


def _small_all(t: list[str], i: int) -> list[tuple[int, int]]:
    """Like _small but also offers the bare-tens reading ('twenty' | 'two thousand') for day parsing."""
    r = _small(t, i)
    if r and i < len(t) and t[i] in W2N and W2N[t[i]] >= 20 and r[0][1] == i + 2:
        r = r + [(W2N[t[i]], i + 1)]
    return r


def _small_card(t: list[str], i: int):
    r = _small(t, i)
    return r[0] if r and not (t[i] in ORD2N) else None


def _cardinal(t: list[str], i: int):
    """Cardinal 0..9999 (or a bare digit token) at i -> (int, next_i) | None. 'a hundred' = 100."""
    def grp(j):
        if j < len(t) and t[j] in ("a", "an") and j + 1 < len(t) and t[j + 1] in ("hundred", "thousand"):
            v, k = 1, j + 1
        elif j < len(t) and t[j].isdigit():
            return int(t[j]), j + 1
        else:
            s = _small_card(t, j)
            if s is None: return None
            v, k = s
        if k < len(t) and t[k] == "hundred" and v < 10:
            v, k = v * 100, k + 1
            if k + 1 < len(t) and t[k] == "and" and _small_card(t, k + 1): k += 1
            s2 = _small_card(t, k)
            if s2: v, k = v + s2[0], s2[1]
        return v, k
    f = grp(i)
    if f is None: return None
    v, k = f
    if k < len(t) and t[k] == "thousand" and v < 10:
        v, k = v * 1000, k + 1
        r = grp(k)
        if r: v, k = v + r[0], r[1]
    return v, k


def _year(t: list[str], i: int) -> list[tuple[int, int, bool]]:
    """Parses of a year at i -> [(year_or_yy, next_i, is_two_digit)]."""
    out = []
    if i >= len(t): return out
    if t[i] == "nineteen" and i + 1 < len(t):
        if t[i + 1] == "hundred": out.append((1900, i + 2, False))
        elif t[i + 1] == "oh" and i + 2 < len(t) and t[i + 2] in ONES: out.append((1900 + W2N[t[i + 2]], i + 3, False))
        else:
            for v, j in _small(t, i + 1)[:1]:
                if v >= 10: out.append((1900 + v, j, False))
    if t[i] == "two" and i + 1 < len(t) and t[i + 1] == "thousand":
        subs = _small(t, i + 2)[:1]
        out += [(2000 + v, j, False) for v, j in subs] or [(2000, i + 2, False)]
    if t[i] == "twenty" and i + 1 < len(t):
        for v, j in _small(t, i + 1):
            if v >= 10: out.append((2000 + v, j, False))
    if t[i].isdigit() and len(t[i]) == 4: out.append((int(t[i]), i + 1, False))
    if any(not two for _, _, two in out):                 # a full 4-digit reading beats a 2-digit one
        return sorted([o for o in out if not o[2]], key=lambda x: -x[1])
    if t[i] == "oh" and i + 1 < len(t) and t[i + 1] in ONES:              # "oh five" -> 05
        out.append((W2N[t[i + 1]], i + 2, True))
    for v, j in _small(t, i):
        if v >= 10: out.append((v, j, True))
    return sorted(out, key=lambda x: (x[2], -x[1]))


def date_candidates(text: str) -> list[dict]:
    """All plausible dates in `text`: [{iso, form, century_ambiguous, span}], best first."""
    t = toks(text); out = []

    def add(m, d, ys, form, a, b):
        for y, j, two in ys:
            for yy in ([1900 + y, 2000 + y] if two and y <= 99 else [y]):
                if two and yy > 2000 + CUR_YY: continue
                try: iso = dt.date(yy, m, d).isoformat()
                except ValueError: continue
                out.append(dict(iso=iso, form=form, century_ambiguous=two, span=(a, j)))

    for i in range(len(t)):
        if t[i] in MONTHS:
            m = MONTHS.index(t[i]) + 1; k = i + 1
            for d, j in _small_all(t, k):
                j2 = j + (1 if j < len(t) and t[j] == "of" else 0)
                add(m, d, _year(t, j2), "month_name", i, j2)
        else:
            for m, j in _small(t, i):
                if not 1 <= m <= 12 or t[i] in ORD2N: continue     # month in numeric form is a cardinal, never 'fourth'
                for d, j2 in _small_all(t, j):
                    if 1 <= d <= 31:
                        j3 = j2 + (1 if j2 < len(t) and t[j2] == "of" else 0)
                        add(m, d, _year(t, j3), "numeric", i, j3)
    for mo in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text):
        add(int(mo.group(1)), int(mo.group(2)), [(int(mo.group(3)), 0, False)], "digits_mdy", 0, 0)
    for mo in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        add(int(mo.group(2)), int(mo.group(3)), [(int(mo.group(1)), 0, False)], "digits_iso", 0, 0)
    seen, res = set(), []
    for c in sorted(out, key=lambda c: (c["century_ambiguous"], c["form"] == "numeric", -(c["span"][1] - c["span"][0]))):
        if (c["iso"]) not in seen: seen.add(c["iso"]); res.append(c)
    return res


def normalize_dob(text: str) -> Optional[str]:
    c = date_candidates(text)
    return c[0]["iso"] if c else None


def phone_candidates(text: str) -> list[str]:
    """Digit runs read from words/digits: 10-digit windows first, then 7-digit partials.

    "oh" is both the digit zero ("two oh two") and an interjection ("Oh, sorry"). A caller who reads a number and then says
    "Oh, ..." used to yield a run one digit too long, and keeping only the LAST ten digits silently shifted the whole number.
    Runs longer than 10 now yield every 10-digit window; windows that do not start or end on an ambiguous "oh" come first.
    """
    t = toks(text); runs: list[list[tuple[str, bool]]] = []; cur: list[tuple[str, bool]] = []
    for w in t + ["#"]:
        if w in ONES or w == "oh": cur.append((str(W2N[w]), w == "oh"))
        elif w.isdigit(): cur += [(c, False) for c in w]
        else:
            if cur: runs.append(cur)
            cur = []
    scored: list[tuple[int, int, str]] = []
    for r in runs:
        if len(r) >= 10:
            for i in range(len(r) - 9):
                win = r[i:i + 10]
                scored.append((int(win[0][1]) + int(win[-1][1]), 0, "".join(d for d, _ in win)))
        elif len(r) == 7:
            scored.append((0, 1, "".join(d for d, _ in r)))
    scored.sort(key=lambda x: (x[1], x[0]))
    out: list[str] = []
    for _, _, v in scored:
        if v not in out: out.append(v)
    return out

def normalize_phone(text: str) -> Optional[str]:
    c = [x for x in phone_candidates(text) if len(x) == 10]
    return c[0] if c else None


def parse_number(t: list[str], i: int = 0) -> Optional[tuple[str, int]]:
    """Cardinal or decimal at i: 'zero point two five'->'0.25', 'a hundred point six'->'100.6', 'forty five'->'45'."""
    if i < len(t) and re.fullmatch(r"\d+(?:\.\d+)?", t[i]) and ("." in t[i] or len(t[i]) > 2):   # digit-form decimal / long int
        return (t[i], i + 1)
    if i < len(t) and t[i] == "point":
        ip, j = 0, i
    else:
        r = _cardinal(t, i)
        if r is None: return None
        ip, j = r
    if j < len(t) and t[j] == "point":
        k, frac = j + 1, ""
        while k < len(t) and (t[k] in ONES or t[k] == "oh" or (t[k].isdigit() and len(t[k]) == 1)):
            frac += str(W2N[t[k]]) if t[k] in W2N else t[k]; k += 1
        if frac: return (f"{ip}.{frac}", k)
    return (str(ip), j)


def dose_candidates(text: str) -> list[tuple[str, str]]:
    """[(value, canonical_unit)] for 'zero point two five milliliters', '0.25 mL', 'five milligrams'."""
    t = toks(text); out = []
    for i in range(len(t)):
        if i and (t[i - 1] in W2N or t[i - 1] in ("point", "hundred", "thousand", "oh") or t[i - 1].isdigit()): continue
        r = parse_number(t, i)
        if r and r[1] < len(t) and t[r[1]] in UNIT_CANON:
            unit, k = UNIT_CANON[t[r[1]]], r[1] + 1
            if unit == "mcg" and (t[k:k + 1] == ["hr"] or t[k:k + 2] in (["per", "hour"], ["an", "hour"])): unit = "mcg/hr"
            out.append((r[0], unit))
    return list(dict.fromkeys(out))


def normalize_clock(text: str) -> list[str]:
    """'six thirty' -> ['06:30'] (12-hour; am/pm is NOT recoverable and left to context)."""
    t = toks(text); out = []
    for i in range(len(t)):
        for h, j in _small(t, i):
            if 1 <= h <= 12:
                if j < len(t) and t[j] == "oh" and j + 1 < len(t) and t[j + 1] in ONES: out.append(f"{h:02d}:0{W2N[t[j+1]]}")
                else:
                    for m, k in _small(t, j):
                        if 10 <= m <= 59: out.append(f"{h:02d}:{m:02d}")
    for mo in re.finditer(r"\b(\d{1,2}):(\d{2})\b", text): out.append(f"{int(mo.group(1)):02d}:{mo.group(2)}")
    return list(dict.fromkeys(out))


# ----------------------------------------------------------------------------- text-level converter (used by asr_noise)
_PH = re.compile(r"\(?\b(\d{3})\)?[-. ]?(\d{3})[-. ]?(\d{4})\b")
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MDY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_DOSE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(mL|ml|mg|mcg/hr|mcg|g|IU|puffs?|tablets?|drops?|patch(?:es)?|capsules?)\b")
_MNAME = re.compile(r"\b(" + "|".join(m.capitalize() for m in MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
_CLOCK = re.compile(r"\b(\d{1,2}):(\d{2})\b")


def convert_numbers_in_text(text: str, rng: random.Random, p_identity: float = 1.0, p_dose_time: float = 0.7) -> tuple[str, list[dict]]:
    """Rewrite digit-form numbers as spoken words. Returns (new_text, events)."""
    ev: list[dict] = []

    def sub(rx, fn, kind, p):
        nonlocal text
        def r(m):
            if rng.random() > p: return m.group(0)
            new = fn(m); ev.append(dict(kind="number_words", subkind=kind, original=m.group(0), spoken=new)); return new
        text = rx.sub(r, text)

    sub(_ISO, lambda m: date_to_words(m.group(0), rng.choice(["month_name", "numeric", "numeric_yy"]), rng), "date", p_identity)
    sub(_MDY, lambda m: date_to_words(f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}", rng.choice(["month_name", "numeric"]), rng), "date", p_identity)
    sub(_MNAME, lambda m: date_to_words(f"{m.group(3)}-{MONTHS.index(m.group(1).lower()) + 1:02d}-{int(m.group(2)):02d}",
                                        rng.choice(["month_name", "numeric"]), rng), "date", p_identity)
    sub(_PH, lambda m: phone_to_words("".join(m.groups()), rng, grouped=rng.random() < .15), "phone", p_identity)
    sub(_DOSE, lambda m: f"{decimal_to_words(m.group(1))} {rng.choice(UNIT_SPOKEN.get(UNIT_CANON.get(m.group(2).lower(), m.group(2)) if m.group(2).lower() != "mcg/hr" else "mcg/hr", [m.group(2)]))}", "dose", p_dose_time)
    sub(_CLOCK, lambda m: clock_to_words(m.group(0), rng), "clock", p_dose_time)
    return text, ev
