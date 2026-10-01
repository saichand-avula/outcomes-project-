"""Seeded fact-record sampler (NO LLM). 1,300 records: 800 train / 100 dev / 400 eval.

Leakage controls (enforced at sampling time, verified by check_leakage):
  * patient surnames, patient first names and caller first names come from split-disjoint pools
  * every DOB is globally unique; every phone is globally unique
  * (drug, dose, unit) combos are split-disjoint for drugs with >=3 dose options; drugs with <3 options
    are exempt (otherwise whole drugs would vanish from eval) and listed in the leakage report
"""
from __future__ import annotations
import datetime as dt, hashlib, json, random, sys
from pathlib import Path
from schema import *
import lexicons as L

HERE = Path(__file__).parent
SPLITS = ["train", "dev", "eval"]
TAXO = {  # category: (train, dev, eval)  -- plan Section 4
    "routine": (120, 15, 60), "ambiguous": (120, 15, 60), "asr_error": (120, 15, 60), "medication": (140, 17, 70),
    "supply": (100, 13, 50), "high_risk": (140, 17, 70), "not_applicable": (60, 8, 30)}
HR_COUNTS = {"train": [28] * 5, "dev": [4, 4, 3, 3, 3], "eval": [14] * 5}
ASR_LEVEL = {"routine": "low", "ambiguous": "medium", "asr_error": "high", "medication": "medium",
             "supply": "medium", "high_risk": "medium", "not_applicable": "low"}

FEMALE = """Alice Beatrice Camille Dana Elise Fiona Gloria Hannah Irene Janet Karen Lorraine Monica Nadia Olga Patricia Rosa Sandra
Teresa Ursula Vivian Wendy Yvonne Zoe Abigail Bonnie Carla Denise Eleanor Frances Gwen Helen Iris Joan Kendra Lillian Margaret
Natalie Opal Priscilla Rhonda Stella Tamara Una Valerie Winifred Agnes Brenda Cora Delia Esther Faye Georgia Hazel Ingrid Jolene
Kathleen Lucille Marianne Noelle Odette Paula Rebecca Shirley Thelma Vera Willa Alma Blanche Celeste Dorothy Edith Flora Greta
Harriet Isabel Josephine Katrina Leona Mabel Nell Octavia Phyllis Ruth Sylvia Trudy Vanessa Wilma Adele Bridget""".split()
MALE = """Aaron Bruce Calvin Dennis Edgar Franklin Gordon Harold Ivan Jerome Kenneth Leonard Marcus Norman Oscar Percy Quentin Raymond
Stanley Theodore Victor Walter Alan Bernard Cecil Douglas Eugene Felix Gerald Howard Irving Jacob Kyle Lloyd Martin Nolan Orville
Peter Randall Samuel Todd Vernon Warren Abel Barry Clifford Dale Elliot Floyd Glenn Hugh Isaac Jasper Keith Lance Morris Neil
Owen2 Philip Roland Sidney Terrence Ulysses Vince Wallace Alfred Boyd Clyde Duane Emmett Forrest Grant Henry Ira Julian Karl
Leroy Mitchell Nathan Otis Preston Rufus Sherman Tobias Wayne Arthur Basil""".split()
MALE = [n for n in MALE if n != "Owen2"]   # "Owen" is reserved (real example 4)
SURNAMES = """Abbott Alvarez Archer Baldwin Barnes Beaumont Bishop Blackwell Brennan Brooks Burke Calloway Carver Chambers Chandler Clayton
Coleman Collins Crawford Dalton Dawson Delgado Dixon Donovan Duncan Edwards Emerson Fairfax Fischer Fleming Fowler Gallagher
Garrett Gibson Gilbert Graves Gray Griffin Hadley Hammond Hansen Hartley Hawkins Hayes Holloway Hudson Hunter Ingram Jacobs
Jennings Keller Kendall Kirby Lambert Larson Lawson Lowell Madden Maxwell McBride Mendoza Miller Mitchell Monroe Morrison Nash
Nolan Norris Oakley Olsen Osborne Palmer Parsons Patel Pearson Pierce Porter Powell Prescott Quinlan Ramsey Reeves Reynolds Rhodes
Rivera Roberts Rowe Russell Sampson Sawyer Schmidt Sharp Shepherd Simmons Spencer Stanton Sullivan Tanner Thornton Tucker Turner
Underwood Vaughn Wagner Walsh Watkins Webb Whitaker Wiley Winters Wood Wright Yates Young Zimmerman Abernathy Ashford Bellamy
Calhoun Dunham Everett Fitzgerald Gunderson Hollis Irvine Jorgensen Kessler Langford Merritt Nickerson Pennington Rutledge""".split()
RESERVED = {"Mara", "Ellis", "Nina", "Miles", "Harper", "Leah", "Evan", "Bennett", "Nora", "Quinn", "Mina", "Lane", "Owen",
            "Ethan", "Mercer", "Naomi", "Marlowe", "Clara", "Ada", "Elena", "Karen", "Nadine", "Noreen", "Norine", "Olivia", "Lena"}
AREA_CODES = [202, 212, 213, 303, 312, 404, 415, 512, 602, 617, 646, 702, 713, 718, 786, 818, 917, 206, 305, 503]
NURSE_NAMES = ["Ada", "Elena", "Karen", "Marcus", "Priya", "Tom", "Rosa", "Dev"]   # nurse names are persona only


class Pools:
    def __init__(self, rng: random.Random):
        self.names = {s: {} for s in SPLITS}
        for key, lst in (("F", FEMALE), ("M", MALE), ("S", SURNAMES)):
            lst = [n for n in lst if n not in RESERVED]; rng.shuffle(lst)
            a, b = round(.6 * len(lst)), round(.1 * len(lst))
            self.names["train"][key], self.names["dev"][key], self.names["eval"][key] = lst[:a], lst[a:a + b], lst[a + b:]
        phones = [(ac, n) for ac in AREA_CODES for n in range(100, 200) if not (ac == 202 and 101 <= n <= 105)]
        rng.shuffle(phones); self.phones = phones
        self.dobs: set[str] = {"1951-06-04", "1949-02-09", "1939-04-14", "1933-02-13", "2018-10-08"}   # reserve real-5 DOBs
        # (drug, dose, unit) combos: stratified split for drugs with >=3 options
        self.combos = {s: {} for s in SPLITS}
        self.exempt: list[str] = []
        for d in L.FORMULARY:
            opts = list(d["doses"])
            if len(opts) < 3:
                self.exempt.append(d["generic"])
                for s in SPLITS: self.combos[s][d["generic"]] = opts
                continue
            rng.shuffle(opts)
            k_e = max(1, round(.3 * len(opts))); k_d = 1
            self.combos["eval"][d["generic"]] = opts[:k_e]
            self.combos["dev"][d["generic"]] = opts[k_e:k_e + k_d]
            self.combos["train"][d["generic"]] = opts[k_e + k_d:]

    def dob(self, rng, age_lo, age_hi):
        for _ in range(1000):
            y = 2026 - rng.randint(age_lo, age_hi)
            d = dt.date(y, rng.randint(1, 12), rng.randint(1, 28)).isoformat()
            if d not in self.dobs:
                self.dobs.add(d); return d
        raise RuntimeError("DOB space exhausted")


def idf(v, status="stated"): return IdField(value=v, status=status)


def make_identity(rng, P: Pools, split, pediatric=False, rel_hint=None):
    ps = rng.choice("FM"); surname = rng.choice(P.names[split]["S"]); pfirst = rng.choice(P.names[split][ps])
    if pediatric:
        rel = rng.choice(["mother", "father"]); cs = "F" if rel == "mother" else "M"; dob = P.dob(rng, 3, 15)
    else:
        rel = rel_hint or rng.choices(L.RELATIONSHIPS, [4, 3, 4, 0, 0, 1, 2, 1, 1, 1])[0]
        cs = {"daughter": "F", "granddaughter": "F"}.get(rel) or {"son": "M"}.get(rel) or rng.choice("FM")
        dob = P.dob(rng, 62, 99) if rng.random() < .9 else P.dob(rng, 30, 61)
    if rel == "patient (self)":
        cs = ps; cfirst = pfirst
    else:
        cfirst = rng.choice([n for n in P.names[split][cs] if n != pfirst] or P.names[split][cs])
    full = rel in ("spouse", "mother", "father", "daughter", "son") and rng.random() < .3
    ac, n = P.phones.pop()
    ident = Identity(patient_name=idf(f"{pfirst} {surname}"), patient_dob=idf(dob),
                     caller_name=idf(f"{cfirst} {surname}" if full else cfirst), relationship=idf(rel),
                     callback_phone=idf(f"{ac}555{n:04d}"))
    return ident, dict(patient_sex=ps, caller_sex=cs, patient_first=pfirst, caller_first=cfirst, pediatric=pediatric)


def pick_med(rng, P, split, settings="HC", status="current", certainty="stated", i=1, generic=None, among=None, **kw):
    pool = [d for d in L.FORMULARY if d["setting"] in settings and (among is None or d["generic"] in among)]
    d = next(x for x in L.FORMULARY if x["generic"] == generic) if generic else rng.choice(pool)
    v, u = rng.choice(P.combos[split][d["generic"]])
    freq = rng.choice(d["freqs"])
    return Medication(id=f"M{i}", name=d["generic"], dose=f"{v:g}", unit=u, route=rng.choice(d["routes"]), frequency=freq,
                      prn=("PRN" in freq) or None, status=status, certainty=certainty, **kw)


def pick_symptoms(rng, n, allow_risk=False, pain_cap=6, forbid=()):
    names = [k for k, v in L.SYMPTOMS.items() if (allow_risk or "risk" not in v) and k not in ("terminal secretions",) and k not in forbid]
    out = []
    for i, name in enumerate(rng.sample(names, n), 1):
        sty = L.SYMPTOMS[name]["sev"]
        sev = (f"{rng.randint(2, pain_cap)}/10" if sty == "numeric" else
               rng.choice(L.SEVERITY_GRADES[:2] if not allow_risk else L.SEVERITY_GRADES) if sty == "graded" else None)
        loc = rng.sample(L.SYMPTOMS[name]["loc"], rng.randint(1, 2)) if "loc" in L.SYMPTOMS[name] else []
        out.append(Symptom(id=f"S{i}", name=name, severity=sev, location=loc, onset_duration=rng.choice(L.DURATIONS)))
    return out


def pick_actions(rng, kinds, start=1):
    out = []
    for i, k in enumerate(kinds, start):
        planned, completed = L.ACTION_TYPES[k]
        st = "advised" if completed is None else rng.choices(["planned", "completed"], [4, 1])[0]
        out.append(Action(id=f"A{i}", type=k, description=k.replace("_", " "), status=st))
    return out


def pick_education(rng, kinds, start=1):
    return [Education(id=f"E{i}", type=k, description=k.replace("_", " ")) for i, k in enumerate(kinds, start)]


def hedge(rng, rec: FactRecord, n=2):
    """Mark n facts as caller-uncertain (gold certainty=unclear); voicing prompt must express the doubt."""
    cands = [f for f in (*rec.medications, *rec.symptoms) if f.certainty == "stated" and getattr(f, "critical", True)]
    chosen = rng.sample(cands, min(n, len(cands)))
    for f in chosen: f.certainty = "unclear"
    rec.persona["uncertain_facts"] = [f.id for f in chosen]
    rec.persona["self_contradiction"] = rng.random() < .5
    return rec


def build_record(rng, P: Pools, split, idx, category, subtype=None) -> FactRecord:
    pediatric = category in ("routine", "medication") and rng.random() < .06
    if category == "not_applicable":
        ident, persona = make_identity(rng, P, split)
        keep = {"billing_admin_only": ("patient_name",), "hang_up": (), "wrong_number": (), "test_call": ()}[subtype]
        ident = Identity(**{k: (getattr(ident, k) if k in keep else IdField()) for k in Identity.model_fields})
        return FactRecord(record_id=f"{split}_{idx:04d}", source="synthetic", split=split, category=category, subtype=subtype,
                          persona={**persona, "nurse": rng.choice(NURSE_NAMES)}, agency=rng.choice(L.AGENCIES), identity=ident,
                          not_applicable=True, na_subtype=subtype, noise_plan=dict(asr_level="low", number_words=True))
    ident, persona = make_identity(rng, P, split, pediatric)
    settings = "P" if pediatric else "HC"
    rec = FactRecord(record_id=f"{split}_{idx:04d}", source="synthetic", split=split, category=category, subtype=subtype,
                     agency=rng.choice(L.AGENCIES), identity=ident)
    persona.update(nurse=rng.choice(NURSE_NAMES), verbosity=rng.choice(["terse", "normal", "chatty"]),
                   distraction=rng.choice(["none", "none", "interruptions", "heavy"]))
    rec.persona = persona
    if category in ("routine", "ambiguous"):
        rec.symptoms = pick_symptoms(rng, rng.randint(1, 3))
        rec.medications = [pick_med(rng, P, split, settings, i=i) for i in range(1, rng.randint(1, 2) + 1)]
        rec.pertinent_negatives = [PertinentNegative(id=f"N{i}", name=n) for i, n in
                                   enumerate(rng.sample(["fever", "nausea", "difficulty breathing", "falls", "confusion"], rng.randint(0, 2)), 1)]
        rec.actions = pick_actions(rng, rng.sample(["callback", "team_message", "documentation", "appointment_scheduling"], rng.randint(1, 2)))
        rec.education = pick_education(rng, rng.sample(["medication_instruction", "comfort_measure", "supportive_care", "return_precaution", "callback_invitation"], rng.randint(1, 3)))
        rec.reason_for_call = "status update / general question about " + rec.symptoms[0].name
    elif category == "medication":
        rec.medications = [pick_med(rng, P, split, settings, status=rng.choice(["advised", "ordered", "administered"]), i=i) for i in range(1, rng.randint(2, 3) + 1)]
        rec.symptoms = pick_symptoms(rng, rng.randint(1, 2))
        rec.actions = pick_actions(rng, rng.sample(["callback", "team_message", "physician_notification"], rng.randint(0, 2)))
        rec.education = pick_education(rng, ["medication_instruction", rng.choice(["medication_timing", "administration_method", "medication_safety"])] + ["return_precaution"] * (rng.random() < .5))
        rec.reason_for_call = "question about dosing / timing / side effects / administration of " + rec.medications[0].name
    elif category == "supply":
        meds = [pick_med(rng, P, split, settings, status="current", i=i) for i in range(1, rng.randint(1, 2) + 1)]
        rec.medications = meds
        rec.supplies = []
        low = rng.random() < .3
        for j, m in enumerate(meds, 1):
            q = rng.randint(1, 2) if (low and j == 1) else rng.randint(4, 30)
            rec.supplies.append(Supply(id=f"U{j}", item=m.name, quantity_remaining=f"{q} doses", request=rng.choice(["refill", "delivery"])))
        if rng.random() < .5:
            rec.supplies.append(Supply(id=f"U{len(meds)+1}", item=rng.choice(["oxygen tubing", "briefs", "bed pads", "suction catheters", "wound dressings", "nebulizer tubing"]),
                                       request="equipment"))
        rec.actions = pick_actions(rng, rng.sample(["refill_request", "team_message", "nurse_visit"], rng.randint(1, 2)))
        rec.education = pick_education(rng, rng.sample(["follow_up_expectation", "callback_invitation", "medication_safety"], rng.randint(1, 2)))
        rec.reason_for_call = "supply / refill request for " + ", ".join(s.item for s in rec.supplies)
        if low:
            rec.risk_flags = [RiskFlag(id="R1", category="medication_concern", rationale="<=2 doses remaining of a regularly used medication")]
    elif category == "high_risk":
        rec = build_high_risk(rng, P, split, rec, subtype, settings)
    if category == "ambiguous":
        hedge(rng, rec)
    rec.noise_plan = dict(asr_level=ASR_LEVEL[category], number_words=True, dose_time_words_p=.7, identity_drift=rng.random() < (.5 if category in ("asr_error", "ambiguous") else .15),
                          late_answers=rng.random() < .3, unclear_targets=[], drug_confusion_targets=[], allow_inaudible=False)
    if category == "asr_error":
        rec.medications = rec.medications or [pick_med(rng, P, split, settings, i=1)]
        rec.symptoms = rec.symptoms or pick_symptoms(rng, 2)
        rec.actions = rec.actions or pick_actions(rng, ["callback"])
        rec.education = rec.education or pick_education(rng, ["medication_instruction"])
        rec.reason_for_call = "medication question with poor audio"
        tg = [m.id for m in rng.sample(rec.medications, min(len(rec.medications), rng.randint(1, 2)))]
        # [inaudible] injection is OFF: the 5 real calls contain none (see calibration.json); ASR here emits wrong words instead.
        rec.noise_plan.update(drug_confusion_targets=tg, unclear_targets=tg)
    return rec


def build_high_risk(rng, P, split, rec, sub, settings):
    if sub == "uncontrolled_symptom":
        rec.symptoms = [Symptom(id="S1", name="pain", severity=f"{rng.randint(8, 10)}/10", location=rng.sample(L.SYMPTOMS["pain"]["loc"], 2), onset_duration="despite last dose")]
        rec.medications = [pick_med(rng, P, split, "H", status="administered", i=1, among=["morphine", "hydromorphone", "oxycodone"], last_dose=rng.choice(["1 hour ago", "2 hours ago", "this morning"]))]
        rec.actions = pick_actions(rng, rng.sample(["callback", "nurse_visit", "physician_notification"], 2))
        rec.education = pick_education(rng, ["medication_instruction", "return_precaution"])
        rec.risk_flags = [RiskFlag(id="R1", category="uncontrolled_symptom", rationale="severe symptom not relieved by last dose")]
    elif sub == "medication_concern":
        mm = rng.choice(["wrong_dose", "double_dose", "missed_doses", "ran_out"])
        rec.medications = [pick_med(rng, P, split, "H", status="administered", i=1), pick_med(rng, P, split, "HC", status="current", i=2)]
        rec.symptoms = pick_symptoms(rng, 1)
        rec.supplies = [Supply(id="U1", item=rec.medications[0].name, quantity_remaining="0 doses", request="delivery")] if mm == "ran_out" else []
        rec.context = [ContextFact(id="X1", kind="other", text=f"medication problem: {mm.replace('_', ' ')}")]
        rec.actions = pick_actions(rng, rng.sample(["physician_notification", "callback", "nurse_visit"], 2))
        rec.education = pick_education(rng, ["medication_safety", "return_precaution"])
        rec.risk_flags = [RiskFlag(id="R1", category="medication_concern", rationale=f"caller reports {mm.replace('_', ' ')}")]
    elif sub == "suicidal_statement":
        who = rng.choice(["patient", "caller"])
        rec.symptoms = [Symptom(id="S1", name=f"statement of wanting to die (by {who})", certainty="stated", reporter="Caller"), *pick_symptoms(rng, 1)]
        rec.symptoms[1].id = "S2"
        rec.actions = pick_actions(rng, ["nurse_visit", "physician_notification"])
        rec.education = pick_education(rng, ["emergency_guidance", "return_precaution"])
        rec.risk_flags = [RiskFlag(id="R1", category="suicidal_statement", rationale="statement of wanting to die (never negation-suppressed)")]
    elif sub == "breathing_concern":
        rec.symptoms = [Symptom(id="S1", name="shortness of breath", severity=rng.choice(["moderate", "severe"]), onset_duration=rng.choice(L.DURATIONS)), *pick_symptoms(rng, 1)]
        rec.symptoms[1].id = "S2"
        rec.medications = [pick_med(rng, P, split, "H", status="advised", i=1, among=["morphine", "lorazepam"])]
        rec.actions = pick_actions(rng, rng.sample(["callback", "nurse_visit", "escalation_911_ed"], 2))
        rec.education = pick_education(rng, ["medication_instruction", "emergency_guidance"])
        rec.risk_flags = [RiskFlag(id="R1", category="breathing_concern", rationale="caller reports trouble breathing")]
    elif sub == "escalation_request":
        rec.symptoms = pick_symptoms(rng, 2, pain_cap=7)
        rec.context = [ContextFact(id="X1", kind="other", text=rng.choice(["caller asks for a nurse to come out now", "caller asks to be sent to the hospital", "caller asks to speak to the doctor today"]))]
        rec.actions = pick_actions(rng, rng.sample(["nurse_visit", "physician_notification", "escalation_911_ed"], 2))
        rec.education = pick_education(rng, ["return_precaution", "callback_invitation"])
        rec.risk_flags = [RiskFlag(id="R1", category="escalation_request", rationale="caller requests urgent in-person help")]
    rec.reason_for_call = f"high-risk call: {sub.replace('_', ' ')}"
    return rec


def sample_all(seed: int = 20261001) -> dict[str, list[FactRecord]]:
    rng = random.Random(seed); P = Pools(rng)
    out = {s: [] for s in SPLITS}
    for si, split in enumerate(SPLITS):
        plan: list[tuple[str, str | None]] = []
        for cat, counts in TAXO.items():
            n = counts[si]
            if cat == "high_risk":
                for sub, k in zip(L.HIGH_RISK_SUBTYPES, HR_COUNTS[split]): plan += [(cat, sub)] * k
            elif cat == "not_applicable":
                plan += [(cat, L.NA_SUBTYPES[i % 4]) for i in range(n)]
            else:
                plan += [(cat, None)] * n
        rng.shuffle(plan)
        for idx, (cat, sub) in enumerate(plan):
            out[split].append(build_record(rng, P, split, idx, cat, sub))
    out["_pools"] = P   # type: ignore
    return out


def check_leakage(data: dict) -> dict:
    P: Pools = data["_pools"]; rep = {"violations": [], "exempt_drugs_shared": sorted(P.exempt)}
    seen = {"surname": {}, "pfirst": {}, "cfirst": {}, "dob": {}, "phone": {}, "combo": {}}
    for s in SPLITS:
        for r in data[s]:
            if r.not_applicable: continue
            vals = {"surname": r.identity.patient_name.value.split()[-1], "pfirst": r.identity.patient_name.value.split()[0],
                    "cfirst": r.identity.caller_name.value.split()[0], "dob": r.identity.patient_dob.value, "phone": r.identity.callback_phone.value}
            for k, v in vals.items():
                if k in ("pfirst", "cfirst") and r.identity.relationship.value == "patient (self)": continue
                owner = seen[k].setdefault(v, s)
                if owner != s: rep["violations"].append((k, v, owner, s))
            for m in r.medications:
                if m.name and m.name not in P.exempt and m.dose:
                    key = (m.name, m.dose, m.unit); owner = seen["combo"].setdefault(key, s)
                    if owner != s: rep["violations"].append(("combo", key, owner, s))
    # cross-field: names used as patient first must not be caller first in another split
    pf = {s: {r.identity.patient_name.value.split()[0] for r in data[s] if not r.not_applicable} for s in SPLITS}
    cf = {s: {r.identity.caller_name.value.split()[0] for r in data[s] if not r.not_applicable} for s in SPLITS}
    for a in SPLITS:
        for b in SPLITS:
            if a != b and (pf[a] | cf[a]) & (pf[b] | cf[b]): rep["violations"].append(("first_name_cross", a, b))
    rep["n_unique_dobs"] = len(seen["dob"]); rep["n_unique_phones"] = len(seen["phone"])
    return rep


def main(seed=20261001):
    data = sample_all(seed); rep = check_leakage(data)
    od = HERE / "data/fact_records"
    for s in SPLITS:
        (od / f"{s}.jsonl").write_text("\n".join(r.model_dump_json() for r in data[s]) + "\n")
    digest = hashlib.sha256("".join((od / f"{s}.jsonl").read_text() for s in SPLITS).encode()).hexdigest()
    rep.update(seed=seed, sha256=digest, counts={s: len(data[s]) for s in SPLITS})
    (od / "leakage_report.json").write_text(json.dumps(rep, indent=1))
    print(rep["counts"], "violations:", len(rep["violations"]), "sha256:", digest[:16])
    return data, rep


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20261001)
