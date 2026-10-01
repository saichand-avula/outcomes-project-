import lexicons as L
from schema import RiskCategory
from typing import get_args

def test_formulary_basics():
    gs = [d["generic"] for d in L.FORMULARY]
    assert len(gs) == len(set(gs)) >= 50
    for d in L.FORMULARY:
        assert d["doses"] and d["routes"] and d["freqs"] and d["setting"] in "HCP"
        assert all(s.lower() != d["generic"] for s in d["sound_alikes"])

def test_tall_man_only_confirmed():
    for d in L.FORMULARY:
        if d["tall_man"] != d["generic"]:
            assert d["generic"] in L.CONFIRMED_TALL_MAN and d["tall_man"] == L.CONFIRMED_TALL_MAN[d["generic"]]
    assert next(d for d in L.FORMULARY if d["generic"] == "lorazepam")["tall_man"] == "LORazepam"
    assert next(d for d in L.FORMULARY if d["generic"] == "morphine")["tall_man"] == "morphine"

def test_real_call_drugs_present_with_observed_garbles():
    byg = {d["generic"]: d for d in L.FORMULARY}
    for g in ["morphine", "lorazepam", "haloperidol", "tamsulosin", "amitriptyline", "bisacodyl", "famotidine", "bupropion",
              "metformin", "lisinopril", "finasteride", "sertraline", "albuterol", "ibuprofen"]:
        assert g in byg, g
    assert "carfentanil" in byg["morphine"]["oov_mishears"]
    assert {"phalarisipham"} <= set(byg["lorazepam"]["sound_alikes"])
    assert {"ampatripoline"} <= set(byg["amitriptyline"]["sound_alikes"])
    assert {"tamifluoln", "tamazolid"} <= set(byg["tamsulosin"]["sound_alikes"])
    assert "metroforum" in byg["metformin"]["sound_alikes"]

def test_risk_categories_match_schema():
    assert set(L.RISK_PHRASES) == set(get_args(RiskCategory))
    assert set(L.HIGH_RISK_SUBTYPES) == set(L.RISK_PHRASES)

def test_action_education_types_match_schema():
    from schema import ActionType, EducationType
    assert set(L.ACTION_TYPES) == set(get_args(ActionType))
    assert set(L.EDUCATION_TYPES) == set(get_args(EducationType))

def test_future_and_completion_cues_disjoint():
    assert not set(L.FUTURE_CUES) & set(L.COMPLETION_CUES)

def test_export_files(tmp_path):
    L.export(tmp_path)
    assert (tmp_path / "formulary.csv").read_text().count("\n") == len(L.FORMULARY) + 1
    assert "NO" in (tmp_path / "formulary.csv").read_text().splitlines()[1].split(",")[-1]   # clinically_validated = NO
