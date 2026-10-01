import collections, hashlib, json, random
import build_dataset as BD
import build_gold as BG
import lexicons as L
import mutate_gold as MG
import risk_rules as RR
import spoken as SP
import validate_gold as VG
import voicer as V
from repair import repair_all
from schema import FactRecord
from transcript_utils import Turn, join_turns

ALL = lambda out: [r for sp in ("train", "dev", "eval") for r in out[sp]]


# ----------------------------------------------------------------------------- repair
def test_repair_removes_every_audited_defect(built):
    out, st = built
    assert st["negatives_dropped"] == 30 and st["duplicate_meds_dropped"] == 23 and st["p6_flags_added"] == 30
    for r in ALL(out):
        rec = r["rec"]
        assert len({m.name for m in rec.medications}) == len(rec.medications)
        if any(a.type == "escalation_911_ed" for a in rec.actions):
            assert any(f.category == "escalation_request" for f in rec.risk_flags)
        FactRecord.model_validate(rec.model_dump())


def test_repair_is_idempotent_and_pure():
    raw = [FactRecord.model_validate(json.loads(l)) for l in open("data/fact_records/train.jsonl")][:200]
    a, _ = repair_all(raw); b, _ = repair_all(a)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


# ----------------------------------------------------------------------------- whole pipeline
def test_every_record_passes_every_validator(built):
    out, _ = built
    bad = [(r["rec"].record_id, i["id"]) for r in ALL(out) for i in r["issues"]]
    assert bad == []


def test_pipeline_is_deterministic():
    recs = [FactRecord.model_validate(json.loads(l)) for l in open("data/fact_records/dev.jsonl")][:25]
    h = lambda: hashlib.sha256(json.dumps([(join_turns(x["turns"]), x["gold"]) for x in (BD.build_one(r) for r in recs)], sort_keys=True).encode()).hexdigest()
    assert h() == h()


def test_counts_and_categories(built):
    out, _ = built
    assert [len(out[s]) for s in ("train", "dev", "eval")] == [800, 100, 400]
    na = [r for r in ALL(out) if r["gold"]["not_applicable"]]
    assert len(na) == 98 and all(r["target"]["bullets"] == [] for r in na)


def test_garbled_drug_is_unclear_and_name_never_leaks(built):
    out, _ = built
    n = 0
    for r in ALL(out):
        for e in (e for e in r["events"] if e["kind"] == "drug_confusion"):
            n += 1
            b = next(b for b in r["gold"]["bullets"] if b["fact_id"] == e["fact_id"])
            f = b["facts"][0]
            assert f["name"] is None and f["certainty"] == "unclear" and f["name_as_heard"] and "unclear" in b["text"]
            blob = RR.clean_text(" ".join(t.text for t in r["turns"]))
            assert e["generic"].lower() not in blob
    assert n >= 100


def test_name_drift_becomes_alternate_not_value(built):
    out, _ = built
    n = 0
    for r in ALL(out):
        for e in (e for e in r["events"] if e["kind"] == "name_drift"):
            n += 1
            idf = r["gold"]["identity"][e["field"]]
            assert e["variant"] in idf["alternates"] and idf["value"].split()[0] == e["original"]
    assert n >= 100


def test_no_sound_alike_is_another_real_formulary_drug():
    real = {AN_sp for AN_sp in []}
    import asr_noise as AN
    for d in L.FORMULARY:
        for seed in range(30):
            ev = AN.drug_confusion([Turn(1, "Caller", f"He takes {d['generic']} daily.", {"M1"})], "M1", d["generic"], random.Random(seed))
            assert ev and AN._spaceless(ev["heard"]) not in AN._REAL_NAMES, (d["generic"], ev["heard"])


def test_na_records_score_only_the_na_label(built):
    out, _ = built
    for r in ALL(out):
        if r["rec"].not_applicable:
            assert r["rec"].critical_slots() == [("not_applicable", "NA", {"value": True})]


# ----------------------------------------------------------------------------- voicer templates
def test_every_formulary_value_is_speakable():
    for d in L.FORMULARY:
        assert set(d["freqs"]) <= set(SP.FREQ_SPOKEN) and set(d["routes"]) <= set(SP.ROUTE_SPOKEN)


def test_action_templates_carry_correct_cues():
    clean = RR.clean_text
    for typ, tpls in V.PLANNED.items():
        for t in tpls:
            x = clean(t)
            assert any(clean(c) in x for c in L.FUTURE_CUES) and not any(clean(c) in x for c in L.COMPLETION_CUES), t
    for typ, tpls in V.COMPLETED.items():
        for t in tpls:
            x = clean(t)
            assert any(clean(c) in x for c in L.COMPLETION_CUES) and not any(clean(c) in x for c in L.FUTURE_CUES), t


def test_chatter_and_education_contain_no_clinical_tokens():
    pools = V.CHATTER_CALLER + V.CHATTER_NURSE + V.ASIDES_CALLER + V.ASIDES_HEAVY + V.CHATTER + V.NURSE_EMPATHY + V.COMFORT + V.SUPPORT + V.RETURN + V.FOLLOWUP + V.CALLBACK_INV + V.EMERG + V.EMERG_SUICIDE
    for line in pools:
        line = line.format(obj="him", sub="he", pos="his", Sub="He")
        assert not VG.DRUG_RX.search(line) and not any(ch.isdigit() for ch in line), line
        assert not RR.scan_text(line), (line, RR.scan_text(line))


def test_stated_symptom_phrases_do_not_trip_risk_lexicon_outside_high_risk():
    for name, tpls in V.SYM.items():
        if name == "shortness of breath":
            continue
        for t in tpls:
            s = t.format(Be="he's", has="he has", Hv="he's", sub="he", pos="his", loc="")
            assert not RR.scan_text(s), (name, s)


# ----------------------------------------------------------------------------- risk rules
def test_risk_rules_negation_apostrophes_and_blocks():
    assert RR.scan_text("She can't breathe at all") and not RR.scan_text("no trouble breathing at all")
    assert not RR.scan_text("He hasn't had any trouble breathing")
    assert RR.scan_text("he doesn't want to live but she wants to die")           # suicidal never suppressed
    turns = [Turn(1, "Caller", "I feel like I want to end my."), Turn(2, "Caller", "Life, and I needed to tell someone.")]
    assert "suicidal_statement" in RR.scan_turns(turns)                              # phrase split across turns
    assert RR.scan_turns([Turn(1, "Caller", "it's almost, um out")]) == {"medication_concern": [1]}   # filler inside phrase
    assert RR.scan_turns([Turn(1, "Nurse", "Any trouble breathing?")]) == {}          # screening question != assertion


def test_required_flags_found_and_no_extra_flags(built):
    out, _ = built
    for r in ALL(out):
        sc = RR.scan_turns(r["turns"])
        for f in r["gold"]["risk_flags"]:
            if f["required"]:
                assert f["category"] in sc
        assert VG.extra_rule_flags(r["gold"], r["turns"]) == []


# ----------------------------------------------------------------------------- target / render
def test_sft_target_has_no_fact_ids_and_renders(built):
    out, _ = built
    for r in ALL(out)[:300]:
        t = r["target"]
        assert "fact_id" not in json.dumps(t) and "required" not in json.dumps(t)
        txt = BG.render_summary(t)
        assert txt == "Not Applicable" if t["not_applicable"] else txt.startswith("Chief Complaint")


def test_long_profile_is_present_and_clean():
    recs = [FactRecord.model_validate(json.loads(l)) for l in open("data/fact_records/eval.jsonl")][:15]
    recs, _ = repair_all(recs)
    for r in recs:
        if r.not_applicable:
            continue
        x = BD.build_one(r, stress=(60, 110))
        assert x["issues"] == [] and len(join_turns(x["turns"])) > 4000


# ----------------------------------------------------------------------------- mutation testing of the validators
def test_validators_detect_injected_errors(built):
    out, _ = built
    app, det = collections.Counter(), collections.Counter()
    for r in ALL(out):
        if r["gold"]["not_applicable"]:
            continue
        after = BG.apply_events(r["rec"], r["events"])
        for fn in MG.VALIDATOR_MUTATIONS:
            m = MG.mutate(r["gold"], fn, f"{r['rec'].record_id}:{fn.__name__}")
            if m:
                app[m[1]] += 1; det[m[1]] += bool(VG.check_gold(m[0], after, r["turns"]))
    assert sum(det.values()) / sum(app.values()) >= 0.99
    for k in app:
        assert det[k] / app[k] >= (0.90 if k in ("misattributed_evidence", "wrong_risk_category") else 0.97), (k, det[k], app[k])


def test_no_bullet_quotes_a_bare_acknowledgment(built):
    """Regression: 15% of bullets (1,137 education + 143 action) used to quote "Okay, thank you." as their evidence."""
    out, _ = built
    for r in ALL(out):
        for b in r["gold"]["bullets"]:
            assert BG._plain(b["quote"]) not in BG.ACK_ONLY, (r["rec"].record_id, b["fact_id"], b["quote"])
            if b["kind"] in ("education", "action", "medication"):
                assert len(b["quote"].split()) >= 4, (r["rec"].record_id, b["fact_id"], b["quote"])
