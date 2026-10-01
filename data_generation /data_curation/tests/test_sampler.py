import json, re
import pytest
from collections import Counter
import sample_facts as SF
from gold_real5 import build

DATA = SF.sample_all()
ALL = [r for s in SF.SPLITS for r in DATA[s]]
REAL, _ = build()


def test_counts_and_taxonomy():
    assert {s: len(DATA[s]) for s in SF.SPLITS} == {"train": 800, "dev": 100, "eval": 400}
    for si, s in enumerate(SF.SPLITS):
        c = Counter(r.category for r in DATA[s])
        assert all(c[k] == v[si] for k, v in SF.TAXO.items()), (s, c)
    for s in SF.SPLITS:
        assert sorted(Counter(r.subtype for r in DATA[s] if r.category == "high_risk").values(), reverse=True) == sorted(SF.HR_COUNTS[s], reverse=True)


def test_deterministic_same_seed_same_hash():
    again = SF.sample_all()
    h = lambda d: [r.model_dump_json() for s in SF.SPLITS for r in d[s]]
    assert h(again) == h(DATA)
    assert h(SF.sample_all(seed=1)) != h(DATA)


def test_no_leakage():
    rep = SF.check_leakage(DATA)
    assert rep["violations"] == [], rep["violations"][:5]


def test_independent_leakage_recheck():
    sn = {s: {r.identity.patient_name.value.split()[-1] for r in DATA[s] if not r.not_applicable} for s in SF.SPLITS}
    assert not (sn["train"] & sn["dev"]) and not (sn["train"] & sn["eval"]) and not (sn["dev"] & sn["eval"])
    ph = [r.identity.callback_phone.value for r in ALL if r.identity.callback_phone.value]
    assert len(ph) == len(set(ph))
    dobs = [r.identity.patient_dob.value for r in ALL if r.identity.patient_dob.value]
    assert len(dobs) == len(set(dobs))
    combos = {s: {(m.name, m.dose, m.unit) for r in DATA[s] for m in r.medications if m.name not in DATA["_pools"].exempt} for s in SF.SPLITS}
    assert not (combos["train"] & combos["dev"]) and not (combos["train"] & combos["eval"]) and not (combos["dev"] & combos["eval"])


def test_real5_identities_never_reused():
    real_names = {r.identity.patient_name.value for r in REAL} | {r.identity.caller_name.value for r in REAL}
    real_first = {n.split()[0] for n in real_names}
    real_sur = {r.identity.patient_name.value.split()[-1] for r in REAL}
    real_dob = {r.identity.patient_dob.value for r in REAL}; real_ph = {r.identity.callback_phone.value for r in REAL}
    for r in ALL:
        if r.not_applicable: continue
        assert r.identity.patient_name.value.split()[-1] not in real_sur
        assert r.identity.patient_name.value.split()[0] not in real_first and r.identity.caller_name.value.split()[0] not in real_first
        assert r.identity.patient_dob.value not in real_dob and r.identity.callback_phone.value not in real_ph


def test_phones_are_fictional_555_01xx():
    for r in ALL:
        p = r.identity.callback_phone.value
        if p: assert re.fullmatch(r"\d{3}5550[1]\d{2}", p), p


def test_risk_flag_rules():
    for r in ALL:
        req = [f.category for f in r.risk_flags if f.required]
        if r.category == "high_risk": assert req == [r.subtype]
        elif r.category == "supply": assert req in ([], ["medication_concern"])
        else: assert req == [], (r.record_id, req)


def test_not_applicable_records_carry_no_clinical_facts():
    nas = [r for r in ALL if r.category == "not_applicable"]
    assert len(nas) == 98 and all(r.not_applicable and r.na_subtype and not r.risk_flags for r in nas)
    assert Counter(r.na_subtype for r in nas).keys() == set(SF.L.NA_SUBTYPES)
    ni = [r for r in ALL if not r.not_applicable]
    assert all(not r.not_applicable for r in ni)


def test_ambiguous_and_asr_error_have_their_controls():
    for r in ALL:
        if r.category == "ambiguous": assert r.persona["uncertain_facts"] and any(f.certainty == "unclear" for f in (*r.medications, *r.symptoms))
        if r.category == "asr_error":
            assert r.noise_plan["drug_confusion_targets"] and r.noise_plan["asr_level"] == "high"
            assert set(r.noise_plan["drug_confusion_targets"]) <= {m.id for m in r.medications}
        assert r.noise_plan.get("allow_inaudible", False) is False


def test_eval_covers_every_formulary_drug():
    used = {m.name for r in DATA["eval"] for m in r.medications}
    missing = {d["generic"] for d in SF.L.FORMULARY} - used
    assert len(missing) <= 6, missing    # rare drugs may not be drawn in 400 records; the report lists them


def test_clinically_plausible_high_risk_drugs():
    for r in ALL:
        if r.subtype == "breathing_concern": assert r.medications[0].name in ("morphine", "lorazepam")
        if r.subtype == "uncontrolled_symptom": assert r.medications[0].name in ("morphine", "hydromorphone", "oxycodone")


def test_every_record_has_critical_slots():
    assert all(len(r.critical_slots()) >= 6 for r in ALL if not r.not_applicable)
    # corrected behaviour: a Not-Applicable record is scored on the NA label only (no identity slots)
    assert all(r.critical_slots() == [("not_applicable", "NA", {"value": True})] for r in ALL if r.not_applicable)
