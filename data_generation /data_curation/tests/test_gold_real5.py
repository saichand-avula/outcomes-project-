import yaml
import pytest
from pathlib import Path
from gold_real5 import build, HERE
from transcript_utils import split_turns, norm
import spoken_numbers as SN

RECS, TR = build()
BY = {r.record_id: r for r in RECS}


def test_five_records_all_anchors_resolved():
    assert len(RECS) == 5
    for r in RECS:
        turns = split_turns(TR[r.record_id])
        evs = [e for f in r.all_facts() for e in f.evidence]
        for fld in r.identity.model_dump():
            evs += getattr(r.identity, fld).evidence
        assert evs and all(e.turn_ids for e in evs), r.record_id
        assert all(1 <= i <= len(turns) for e in evs for i in e.turn_ids)


def test_anchor_text_really_in_cited_turns():
    for r in RECS:
        turns = split_turns(TR[r.record_id])
        for f in r.all_facts():
            for e in f.evidence:
                if e.span_after: continue
                text = norm(" ".join(turns[i - 1].text for i in e.turn_ids))
                assert norm(e.anchor) in text, (r.record_id, f.id, e.anchor)


def test_identity_complete_and_consistent_with_number_normalizer():
    for r in RECS:
        turns = split_turns(TR[r.record_id])
        for fld in ("patient_name", "patient_dob", "caller_name", "relationship", "callback_phone"):
            assert getattr(r.identity, fld).status == "stated", (r.record_id, fld)
        for fld, fn in (("callback_phone", lambda t: SN.phone_candidates(t)),
                        ("patient_dob", lambda t: [c["iso"] for c in SN.date_candidates(t)])):
            f = getattr(r.identity, fld)
            per_turn = [x for e in f.evidence for i in e.turn_ids for x in fn(turns[i - 1].text)]
            joined = fn(" ".join(turns[i - 1].text for e in f.evidence for i in e.turn_ids))
            ok = f.value in per_turn + joined or any(f.value.endswith(x) for x in per_turn if len(x) == 7)
            if not ok and r.record_id == "real_04" and fld == "patient_dob":   # month/day in one turn, year in another
                ok = any(c.endswith("-02-13") for c in per_turn) and "nineteen thirty three" in norm(
                    " ".join(turns[i - 1].text for e in f.evidence for i in e.turn_ids))
            assert ok, (r.record_id, fld, f.value, per_turn)


def test_dob_phone_formats():
    for r in RECS:
        assert len(r.identity.callback_phone.value) == 10 and r.identity.callback_phone.value.startswith("202555010")
        assert r.identity.patient_dob.value.count("-") == 2


def test_policy_p1_carfentanil_is_unclear():
    m = next(m for m in BY["real_03"].medications if m.name_as_heard == "carfentanil")
    assert m.certainty == "unclear" and m.name is None


def test_policy_p2_caller_name_conflict():
    c = BY["real_03"].identity.caller_name
    assert c.value == "Nora Quinn" and {"Nadine", "Noreen", "Norine"} <= set(c.alternates)


def test_policy_p3_ibuprofen_unclear_and_unique_mention():
    ex5 = yaml.safe_load(open(HERE / "data/raw/real5_examples.yaml"))["examples"][4]["input_transcript"]
    assert ex5.lower().count("ibuprofen") == 1                       # the finding the policy rests on
    m = next(m for m in BY["real_05"].medications if m.name_as_heard == "ibuprofen")
    assert m.certainty == "unclear"


def test_policy_p4_bp_unclear():
    bp = next(v for v in BY["real_04"].vitals if v.name == "bp")
    assert bp.value == "181/154" and bp.certainty == "unclear"


def test_required_flags():
    req = lambda rid: sorted(f.category for f in BY[rid].risk_flags if f.required)
    assert req("real_01") == ["medication_concern", "uncontrolled_symptom"]
    assert req("real_02") == ["medication_concern"]
    assert req("real_03") == ["breathing_concern"]
    assert req("real_04") == ["escalation_request", "uncontrolled_symptom"]
    assert req("real_05") == []                                     # negation control: many denials, no flag


def test_planned_vs_completed_cases():
    assert all(a.status == "planned" for a in BY["real_01"].actions)          # 'I will try to put in' is NOT completed
    assert next(a for a in BY["real_03"].actions).status == "planned"
    assert next(a for a in BY["real_04"].actions).status == "advised"


def test_critical_slots_present():
    for r in RECS:
        kinds = {k for k, *_ in r.critical_slots()}
        assert {"identity", "not_applicable"} <= kinds
        assert len(r.critical_slots()) >= 10


def test_reference_quotes_recoverable_claim():
    """The plan's claim: all 58 reference quotes recoverable after normalization (50 exact)."""
    import re
    d = yaml.safe_load(open(HERE / "data/raw/real5_examples.yaml"))["examples"]
    from transcript_utils import speaker_blocks
    tot = exact = ok = 0
    for e in d:
        turns = split_turns(e["input_transcript"]); full = " ".join(t.text for t in turns)
        blocks = speaker_blocks(turns)
        for sp, q in re.findall(r'^\s+(Caller|Nurse): "(.*)"\s*$', e["output_clinical_summary"], re.M):
            tot += 1; exact += q in full
            ok += any(norm(q) in " ".join(b[2]) for b in blocks if b[0] == sp)
    assert (tot, exact, ok) == (58, 50, 58)
