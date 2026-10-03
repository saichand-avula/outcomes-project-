"""Mutation test: inject known errors into a clean gold call and check the validator catches each one.

Run: python3 code/tests/test_validator.py
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import ROOT, load_call  # noqa: E402
from data.validate_gold import validate_call  # noqa: E402


def codes(call):
    return {code for lvl, code, _ in validate_call(call).items if lvl == "ERROR"}


def mutate(base, fn):
    c = copy.deepcopy(base)
    fn(c)
    return c


def main() -> int:
    base = load_call(ROOT / "data/authoring/train/tr-023.yaml")
    assert codes(base) == set(), f"clean call has errors: {codes(base)}"
    t = "target"
    med = lambda c: next(f for b in c[t]["assessment"] for f in b["facts"] if f["type"] == "medication")
    cases = {
        "quote not in transcript (G2)": (lambda c: c[t]["assessment"][0].update(quote="A lot of agitation."), "G2"),
        "wrong speaker (G2)": (lambda c: c[t]["assessment"][0].update(speaker="Nurse"), "G2"),
        "unsupported number (G3)": (lambda c: c[t]["assessment"][0].update(text=c[t]["assessment"][0]["text"].replace("25 mg", "75 mg")), "G3"),
        "drug not in transcript (G4)": (lambda c: med(c).update(name="haloperidol"), "G4"),
        "wrong DOB (G5)": (lambda c: c[t]["identity"]["patient_dob"].update(value="1939-04-15"), "G5"),
        "wrong phone (G5)": (lambda c: c[t]["identity"]["callback_phone"].update(value="2025550113"), "G5"),
        "wrong patient name (G5)": (lambda c: c[t]["identity"]["patient_name"].update(value="Zelda Quimby"), "G5"),
        "dose changed (G5)": (lambda c: med(c).update(dose="75"), "G5"),
        "action status flipped (G6)": (lambda c: next(f for b in c[t]["response"] for f in b["facts"] if f["type"] == "action" and f.get("status") == "planned").update(status="completed"), "G6"),
        "dropped bullet (G7)": (lambda c: (c[t]["assessment"].pop(1), c["alignment"].pop("assessment[5]")), "G7"),
        "invented coverage (G8)": (lambda c: c["alignment"]["assessment[0]"].append("A99"), "G8"),
        "missing risk flag (G9)": (lambda c: c[t].update(risk_flags=[]), "G9"),
        "extra risk flag (G9)": (lambda c: c[t]["risk_flags"].append({"category": "suicidal_statement", "turns": [8], "quote": "My dad took his metoprolol twice this morning."}), "G9"),
        "untagged record item (G10)": (lambda c: [tr["fact_ids"].remove("A1") for tr in c["turns"] if "A1" in tr["fact_ids"]], "G10"),
        "NA mismatch (G1)": (lambda c: c[t]["not_applicable"].update(is_na=True), "G1"),
    }
    failed = 0
    for name, (fn, want) in cases.items():
        got = codes(mutate(base, fn))
        ok = want in got
        failed += not ok
        print(f"{'caught' if ok else 'MISSED':6}  {name:34} -> {sorted(got)}")
    print(f"\n{len(cases) - failed}/{len(cases)} mutations caught")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
