import random, re
from transcript_utils import Turn, norm, speaker_blocks, join_turns
import asr_noise as AN
import spoken_numbers as SN

def toy():
    return [Turn(1, "Nurse", "Thank you for calling Meadow Hospice. May I please have the patient's date of birth and a good callback number?"),
            Turn(2, "Caller", "It is June 4, 1951 and my name is Nina, I'm calling about my mother Mara Ellis because she is in a lot of pain this morning and we are almost out of everything.", {"S1"}),
            Turn(3, "Nurse", "All right, Nina. And what is a good callback number? Okay thank you so much for that, and how can I help you today?"),
            Turn(4, "Caller", "It is (202) 555-0101. I gave her the lorazepam 0.5 mg at 6:30 this morning and it did not help much at all really, so I called.", {"M1"}),
            Turn(5, "Nurse", "Okay Nina, I will have the on-call nurse call you back within thirty minutes and you can give morphine 0.25 mL under the tongue if she needs it.", {"M2"})]

def run(seed, level="high", **kw):
    plan = dict(asr_level=level, number_words=True, identity_drift=True, late_answers=True, drug_confusion_targets=["M1"], **kw)
    return AN.apply_noise(toy(), random.Random(seed), plan, {"M1": "lorazepam"}, {"caller_name": "Nina"})

def test_deterministic():
    a, ea = run(5); b, eb = run(5)
    assert join_turns(a) == join_turns(b) and ea == eb
    assert join_turns(run(6)[0]) != join_turns(a)

def test_numbers_survive_all_noise_levels_property():
    """200 seeds x 3 levels: phone, DOB and doses stay recoverable after fillers/repeats/fragments/shifts."""
    for level in ("low", "medium", "high"):
        for seed in range(200):
            turns, _ = run(seed, level)
            full = " ".join(t.text for t in turns)
            assert SN.normalize_phone(full) == "2025550101", (seed, level, full)
            assert "1951-06-04" in [c["iso"] for c in SN.date_candidates(full)], (seed, level)
            assert ("0.25", "mL") in SN.dose_candidates(full), (seed, level)

def test_fragmentation_preserves_speaker_block_text():
    clean = toy()
    plan = dict(asr_level="low", number_words=False, identity_drift=False, late_answers=False)
    prof = AN.PROFILES["low"]; saved = dict(prof)
    prof.update(filler_p=0, repeat_p=0, backchannel_p=0, split_p=0.9)
    try:
        noisy, ev = AN.apply_noise(clean, random.Random(1), plan)
    finally:
        prof.update(saved)
    assert any(e["kind"] == "fragment" for e in ev)
    before = [(s, " ".join(toks)) for s, _, toks, _ in speaker_blocks(clean)]
    after = [(s, " ".join(toks)) for s, _, toks, _ in speaker_blocks(noisy)]
    assert before == after

def test_drug_confusion_targets_only_tagged_turns_and_logs_event():
    turns, ev = run(3)
    e = next(x for x in ev if x["kind"] == "drug_confusion")
    assert e["fact_id"] == "M1" and e["heard"].lower() != "lorazepam" and e["original"].lower() == "lorazepam"
    full = " ".join(t.text for t in turns).lower()
    assert "lorazepam" not in full and e["heard"].lower() in full
    assert "morphine" in full                       # untargeted drug untouched
    assert any("M1" in t.fact_ids and e["heard"].lower() in t.text.lower() for t in turns)

def test_name_drift_only_in_nurse_turns_after_caller_statement():
    drifted = 0
    for seed in range(60):
        turns, ev = run(seed)
        e = [x for x in ev if x["kind"] == "name_drift"]
        if e:
            drifted += 1
            v = e[0]["variant"]
            for t in turns:
                if v in t.text: assert t.speaker == "Nurse"
            assert any(t.speaker == "Caller" and re.search(r"\bNina\b", t.text) for t in turns)   # caller's own statement intact
    assert drifted > 10

def test_diarization_shift_keeps_nurse_sentences():
    base = toy()
    sents = lambda ts: sorted(s for t in ts if t.speaker == "Nurse" for s in re.split(r"(?<=[.?!])\s+", t.text) if s)
    plan = dict(asr_level="low", number_words=False, identity_drift=False, late_answers=True)
    prof = AN.PROFILES["low"]; saved = dict(prof)
    prof.update(filler_p=0, repeat_p=0, backchannel_p=0, split_p=0, diar_p=1.0)
    try:
        noisy, ev = AN.apply_noise(base, random.Random(1), plan)
    finally:
        prof.update(saved)
    assert any(e["kind"] == "diarization_shift" for e in ev)
    assert sents(noisy) == sents(base)

def test_noise_rates_match_calibration_within_tolerance():
    clean = [Turn(i, "Caller" if i % 2 else "Nurse", "so the patient has been taking the medicine and she is a little better and he said that we can try it for the next couple of days if that is okay with you") for i in range(1, 400)]
    plan = dict(asr_level="medium", number_words=False, identity_drift=False, late_answers=False)
    prof = AN.PROFILES["medium"]; saved = dict(prof); prof.update(split_p=0, backchannel_p=0)
    try:
        noisy, ev = AN.apply_noise(clean, random.Random(0), plan)
    finally:
        prof.update(saved)
    n_tok = sum(len(t.text.split()) for t in clean)
    fill = sum(e["kind"] == "filler" for e in ev) * 1000 / n_tok
    rep = sum(e["kind"] == "repeat" for e in ev) * 1000 / n_tok
    assert 11.3 * 0.6 < fill < 11.3 * 1.5, fill
    assert 11.9 * 0.5 < rep < 11.9 * 2.0, rep      # repeat only hits function words; this text is function-word heavy

def test_inaudible_off_by_default():
    for seed in range(30):
        _, ev = run(seed, "high")
        assert not any(e["kind"] == "inaudible_value" for e in ev)


def test_filler_never_splits_hyphenated_number_from_unit():
    """Regression: 'eighty-one uh, milligrams' (filler between a hyphenated numeral and its unit)."""
    import random
    from transcript_utils import Turn
    for seed in range(300):
        turns = [Turn(1, "Caller", "He takes the aspirin, eighty-one milligrams by mouth, daily and seventy-two hours later.")]
        AN.fillers_repeats(turns, random.Random(seed), 0.6, 0.0)
        assert "eighty-one milligrams" in turns[0].text and "seventy-two hours" in turns[0].text, turns[0].text
