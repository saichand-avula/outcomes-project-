import random
import spoken_numbers as SN


def test_real_call_phrases():
    assert SN.normalize_phone("Yes, two zero two five five five zero one zero one.") == "2025550101"
    assert SN.normalize_phone("this number two zero two five five five zero one zero four") == "2025550104"
    assert SN.phone_candidates("Five five five zero one zero five") == ["5550105"]             # ex5 7-digit partial
    iso = lambda s: [c["iso"] for c in SN.date_candidates(s)]
    assert iso("June fourth, nineteen fifty-one") == ["1951-06-04"]
    assert iso("April fourteenth of nineteen thirty nine") == ["1939-04-14"]
    assert iso("Two nine forty-nine") == ["1949-02-09"]                                         # ex2: century dropped
    assert iso("ten eight two thousand eighteen") == ["2018-10-08"]
    assert "2018-10-08" in iso("ten eight of eighteen two thousand eighteen")                   # ex5 garbled first utterance
    assert iso("Two thirteen eighty three") == ["1983-02-13"]                                   # ex4: mis-heard; truth is 1933
    assert SN.dose_candidates("zero point two five milliliters") == [("0.25", "mL")]
    assert SN.dose_candidates("zero point two five mil") == [("0.25", "mL")]
    assert SN.parse_number(SN.toks("a hundred point six")) == ("100.6", 4)
    assert SN.parse_number(SN.toks("one hundred eighty one"))[0] == "181"
    assert SN.normalize_clock("six thirty") == ["06:30"]


def test_phone_roundtrip():
    rng = random.Random(1)
    for _ in range(300):
        p = "".join(rng.choice("0123456789") for _ in range(10))
        assert SN.normalize_phone(SN.phone_to_words(p, rng, grouped=rng.random() < .3)) == p


def test_phone_oh_variant():
    assert SN.normalize_phone("two oh two five five five oh one oh one") == "2025550101"


def test_date_roundtrip_all_styles():
    rng = random.Random(2)
    for _ in range(500):
        d = f"{rng.randint(1930, 2024)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        for style in ("month_name", "numeric", "numeric_yy"):
            got = [c["iso"] for c in SN.date_candidates(SN.date_to_words(d, style, rng))]
            assert d in got, (d, style, SN.date_to_words(d, style, rng), got)
        assert [c["iso"] for c in SN.date_candidates(SN.date_to_words(d, "month_name"))][0] == d   # best candidate is right


def test_numeric_yy_is_flagged_ambiguous():
    c = SN.date_candidates(SN.date_to_words("1949-02-09", "numeric_yy"))
    assert c[0]["century_ambiguous"] is True


def test_every_formulary_dose_roundtrips():
    import lexicons as L
    for d in L.FORMULARY:
        for v, u in d["doses"]:
            for spoken in SN.UNIT_SPOKEN.get(u, [u]):
                got = SN.dose_candidates(f"{SN.decimal_to_words(f'{v:g}')} {spoken}")
                assert (f"{v:g}", u) in got, (d["generic"], v, u, spoken, got)


def test_clock_roundtrip():
    for h in range(1, 13):
        for m in (0, 5, 15, 30, 45):
            if m == 0: continue
            assert f"{h:02d}:{m:02d}" in SN.normalize_clock(SN.clock_to_words(f"{h}:{m:02d}"))


def test_text_converter_and_inverse():
    rng = random.Random(3)
    txt = "DOB is June 4th, 1951, call (202) 555-0101, gave 0.25 mL at 6:30, born 2018-10-08 or 06/04/1951."
    out, ev = SN.convert_numbers_in_text(txt, rng, 1.0, 1.0)
    assert not any(c.isdigit() for c in out), out
    assert SN.normalize_phone(out) == "2025550101"
    isos = [c["iso"] for c in SN.date_candidates(out)]
    assert "1951-06-04" in isos and "2018-10-08" in isos
    assert ("0.25", "mL") in SN.dose_candidates(out) and "06:30" in SN.normalize_clock(out)
    assert {e["subkind"] for e in ev} == {"date", "phone", "dose", "clock"}


def test_year_words():
    assert SN.year_to_words(1951) == "nineteen fifty-one"
    assert SN.year_to_words(1905) == "nineteen oh five"
    assert SN.year_to_words(2018) == "two thousand eighteen"
    assert SN.year_to_words(2000) == "two thousand"


def test_phone_followed_by_oh_interjection():
    """Regression: 'oh' is a digit AND an interjection. A number followed by 'Oh, sorry' used to shift by one digit."""
    ph = "5035550179"
    for tail in (" Oh, sorry, that was the television.", " Oh okay.", ""):
        for head in ("", "Oh, one second. "):
            text = head + "five zero three, five five five, zero one seven nine." + tail
            assert ph in SN.phone_candidates(text), (head, tail, SN.phone_candidates(text))
    assert SN.normalize_phone("two oh two five five five zero one zero one") == "2025550101"
