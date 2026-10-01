"""Lexicons for data generation, ASR noise, and (later) validators.

!! FORMULARY IS NOT CLINICALLY VALIDATED !!  Compiled from general knowledge for synthetic data
only. Strengths, doses and frequencies are plausible, not clinical guidance.
Tall-man spellings are limited to those confirmed on the FDA/ISMP tall-man lists
(ALPRAZolam, buPROPion, busPIRone, clonazePAM, HYDROmorphone, LORazepam); the reference
summaries only show LORazepam, so no other tall-man forms are applied.
"""
from __future__ import annotations
import csv, json
from pathlib import Path

CONFIRMED_TALL_MAN = {"alprazolam": "ALPRAZolam", "bupropion": "buPROPion", "buspirone": "busPIRone",
                      "clonazepam": "clonazePAM", "hydromorphone": "HYDROmorphone", "lorazepam": "LORazepam"}

# D(generic, class, setting, doses[(value, unit)], routes, freqs, aliases, sound-alike ASR forms)
# setting: H = hospice comfort, C = chronic/home-health, P = pediatric/acute
def D(g, cls, st, doses, routes, freqs, aliases=(), sound=(), oov=()):
    return dict(generic=g, cls=cls, setting=st, doses=doses, routes=routes, freqs=freqs,
                aliases=list(aliases), sound_alikes=list(sound), oov_mishears=list(oov),
                tall_man=CONFIRMED_TALL_MAN.get(g, g))

FORMULARY = [
    # ---- hospice comfort core
    D("morphine", "opioid", "H", [(0.25, "mL"), (0.5, "mL"), (0.75, "mL"), (1, "mL"), (5, "mg"), (10, "mg"), (15, "mg")],
      ["PO", "SL"], ["q2h PRN", "q4h PRN", "q4h"], ["morphine sulfate", "MSIR"], ["more fine", "moor fin", "morphing"], ["carfentanil"]),
    D("lorazepam", "benzodiazepine", "H", [(0.5, "mg"), (1, "mg"), (2, "mg"), (1, "tablet"), (0.5, "tablet")],
      ["PO", "SL"], ["q4h PRN", "q6h PRN", "TID"], ["Ativan"], ["lore as a pam", "phalarisipham", "lorazapam", "lora zapam"], []),
    D("haloperidol", "antipsychotic", "H", [(0.5, "mg"), (1, "mg"), (2, "mg"), (5, "mg")],
      ["PO", "SL"], ["q4h PRN", "q6h PRN", "BID"], ["Haldol"], ["hell doll", "hal oh peridol"], []),
    D("hydromorphone", "opioid", "H", [(1, "mg"), (2, "mg"), (4, "mg")], ["PO"], ["q4h PRN", "q6h PRN"],
      ["Dilaudid"], ["hydro more phone", "hydrocodone"], []),
    D("oxycodone", "opioid", "H", [(2.5, "mg"), (5, "mg"), (10, "mg")], ["PO"], ["q4h PRN", "q6h PRN"],
      ["Roxicodone"], ["oxy codone", "oxycontin"], []),
    D("fentanyl", "opioid", "H", [(12, "mcg/hr"), (25, "mcg/hr"), (50, "mcg/hr")], ["transdermal"], ["q72h"],
      ["fentanyl patch"], ["fentanil", "fenta nyl"], []),
    D("methadone", "opioid", "H", [(2.5, "mg"), (5, "mg"), (10, "mg")], ["PO"], ["BID", "TID"], [], ["methodone"], []),
    D("hyoscyamine", "anticholinergic", "H", [(0.125, "mg")], ["SL"], ["q4h PRN"], ["Levsin"], ["hi oh sigh a mean"], []),
    D("atropine drops", "anticholinergic", "H", [(2, "drops"), (4, "drops")], ["SL"], ["q4h PRN"], ["atropine"], ["a tropine"], []),
    D("glycopyrrolate", "anticholinergic", "H", [(0.2, "mg"), (1, "mg")], ["PO"], ["TID"], ["Robinul"], ["glyco pyro late"], []),
    D("scopolamine", "anticholinergic", "H", [(1, "patch")], ["transdermal"], ["q72h"], ["scopolamine patch"], ["scope olamine"], []),
    D("ondansetron", "antiemetic", "H", [(4, "mg"), (8, "mg")], ["PO", "SL"], ["q8h PRN"], ["Zofran"], ["on dance a tron"], []),
    D("prochlorperazine", "antiemetic", "H", [(5, "mg"), (10, "mg")], ["PO"], ["q6h PRN"], ["Compazine"], ["pro chlor per a zine"], []),
    D("metoclopramide", "antiemetic", "H", [(5, "mg"), (10, "mg")], ["PO"], ["QID"], ["Reglan"], ["metoclopromide"], []),
    D("dexamethasone", "steroid", "H", [(2, "mg"), (4, "mg"), (8, "mg")], ["PO"], ["daily", "BID"], ["Decadron"], ["dexa methazone"], []),
    D("senna", "laxative", "H", [(8.6, "mg"), (17.2, "mg")], ["PO"], ["BID", "daily at bedtime"], ["Senokot"], ["sen a"], []),
    D("bisacodyl", "laxative", "H", [(10, "mg")], ["PR", "PO"], ["daily PRN"], ["Dulcolax"], ["bis a codyl"], []),
    D("polyethylene glycol", "laxative", "H", [(17, "g")], ["PO"], ["daily"], ["MiraLAX", "Miralax"], ["poly ethylene glycol"], []),
    D("docusate", "laxative", "H", [(100, "mg")], ["PO"], ["BID"], ["Colace"], ["doc you sate"], []),
    D("lactulose", "laxative", "H", [(15, "mL"), (30, "mL")], ["PO"], ["BID"], [], ["lack tyoo lows"], []),
    D("acetaminophen", "analgesic", "H", [(325, "mg"), (500, "mg"), (650, "mg"), (1000, "mg")], ["PO", "PR"],
      ["q6h PRN", "q4h PRN"], ["Tylenol"], ["a seat a minnow fin"], []),
    D("levetiracetam", "anticonvulsant", "H", [(250, "mg"), (500, "mg"), (750, "mg")], ["PO"], ["BID"], ["Keppra"], ["leva tire a setam"], []),
    D("olanzapine", "antipsychotic", "H", [(2.5, "mg"), (5, "mg")], ["PO", "SL"], ["daily at bedtime", "BID PRN"], ["Zyprexa"], ["olan zapine"], []),
    D("lidocaine patch", "analgesic", "H", [(1, "patch"), (2, "patch")], ["transdermal"], ["12 hours on, 12 hours off"], ["Lidoderm"], ["lido cane patch"], []),
    D("gabapentin", "anticonvulsant", "H", [(100, "mg"), (300, "mg"), (600, "mg")], ["PO"], ["TID"], ["Neurontin"], ["gabba pentin"], []),
    D("baclofen", "muscle relaxant", "H", [(5, "mg"), (10, "mg")], ["PO"], ["TID"], [], ["back low fen"], []),
    D("clonazepam", "benzodiazepine", "H", [(0.25, "mg"), (0.5, "mg"), (1, "mg")], ["PO"], ["BID"], ["Klonopin"], ["clonazapam"], []),
    D("alprazolam", "benzodiazepine", "H", [(0.25, "mg"), (0.5, "mg")], ["PO"], ["TID PRN"], ["Xanax"], ["alpra zolam"], []),
    D("trazodone", "antidepressant", "H", [(50, "mg"), (100, "mg")], ["PO"], ["at bedtime"], ["Desyrel"], ["trazo done"], []),
    D("mirtazapine", "antidepressant", "H", [(7.5, "mg"), (15, "mg")], ["PO"], ["at bedtime"], ["Remeron"], ["mirta zapine"], []),
    D("melatonin", "supplement", "H", [(3, "mg"), (5, "mg")], ["PO"], ["at bedtime"], [], ["mela tonin"], []),
    # ---- chronic / home-health (seen in real example 2)
    D("amitriptyline", "antidepressant", "C", [(10, "mg"), (25, "mg"), (50, "mg")], ["PO"], ["at bedtime"],
      ["Elavil"], ["ampatripoline", "amy trip a line", "nortriptyline"], []),
    D("tamsulosin", "alpha blocker", "C", [(0.4, "mg"), (0.8, "mg")], ["PO"], ["daily after a meal"],
      ["Flomax"], ["tamifluoln", "tamazolid", "tam sue low sin"], []),
    D("finasteride", "5-ARI", "C", [(5, "mg")], ["PO"], ["daily"], ["Proscar"], ["fin asteride"], []),
    D("sertraline", "antidepressant", "C", [(25, "mg"), (50, "mg"), (100, "mg")], ["PO"], ["daily"], ["Zoloft"], ["sir tra line"], []),
    D("bupropion", "antidepressant", "C", [(150, "mg"), (300, "mg")], ["PO"], ["daily"], ["Wellbutrin"], ["bus pirone"], []),
    D("buspirone", "anxiolytic", "C", [(5, "mg"), (10, "mg")], ["PO"], ["BID", "TID"], ["BuSpar"], ["bupropion"], []),
    D("metformin", "antidiabetic", "C", [(500, "mg"), (850, "mg"), (1000, "mg")], ["PO"], ["BID with meals"],
      ["Glucophage"], ["metroforum", "met for men"], []),
    D("lisinopril", "ACE inhibitor", "C", [(5, "mg"), (10, "mg"), (20, "mg"), (40, "mg")], ["PO"], ["daily"], ["Zestril"], ["lisin a pril"], []),
    D("atorvastatin", "statin", "C", [(10, "mg"), (20, "mg"), (40, "mg")], ["PO"], ["daily"], ["Lipitor"], ["libator", "a tor va statin"], []),
    D("famotidine", "H2 blocker", "C", [(20, "mg"), (40, "mg")], ["PO"], ["daily", "BID"], ["Pepcid"], ["fam oh tie dean"], []),
    D("amlodipine", "calcium channel blocker", "C", [(2.5, "mg"), (5, "mg"), (10, "mg")], ["PO"], ["daily"], ["Norvasc"], ["am lo di peen"], []),
    D("metoprolol", "beta blocker", "C", [(25, "mg"), (50, "mg")], ["PO"], ["BID"], ["Lopressor"], ["meta prolol"], []),
    D("furosemide", "diuretic", "C", [(20, "mg"), (40, "mg")], ["PO"], ["daily"], ["Lasix"], ["fur ose a mide"], []),
    D("levothyroxine", "thyroid", "C", [(25, "mcg"), (50, "mcg"), (75, "mcg"), (100, "mcg")], ["PO"], ["daily in the morning"], ["Synthroid"], ["levo thigh rock sin"], []),
    D("warfarin", "anticoagulant", "C", [(2, "mg"), (5, "mg")], ["PO"], ["daily in the evening"], ["Coumadin"], ["war farin"], []),
    D("apixaban", "anticoagulant", "C", [(2.5, "mg"), (5, "mg")], ["PO"], ["BID"], ["Eliquis"], ["a pix a ban"], []),
    D("aspirin", "antiplatelet", "C", [(81, "mg")], ["PO"], ["daily"], [], ["as prin"], []),
    D("prednisone", "steroid", "C", [(5, "mg"), (10, "mg"), (20, "mg")], ["PO"], ["daily"], [], ["pred ni zone"], []),
    D("albuterol", "bronchodilator", "C", [(2, "puffs")], ["inhaled"], ["q4h PRN", "TID"], ["ProAir", "Ventolin"], ["al byoo ter all"], []),
    D("tiotropium", "bronchodilator", "C", [(1, "capsule")], ["inhaled"], ["daily"], ["Spiriva"], ["tie oh tropium"], []),
    D("vitamin D", "supplement", "C", [(1000, "IU"), (2000, "IU")], ["PO"], ["daily"], [], [], []),
    # ---- pediatric / acute (seen in real example 5)
    D("ibuprofen", "NSAID", "P", [(100, "mg"), (200, "mg"), (400, "mg"), (5, "mL"), (7.5, "mL")], ["PO"], ["q6h PRN"],
      ["Motrin", "Advil"], ["i bu pro fin"], []),
    D("amoxicillin", "antibiotic", "P", [(250, "mg"), (500, "mg")], ["PO"], ["TID"], [], ["amox a cillin"], []),
    D("cetirizine", "antihistamine", "P", [(5, "mg"), (10, "mg")], ["PO"], ["daily"], ["Zyrtec"], ["ceti rizine"], []),
    D("loratadine", "antihistamine", "P", [(10, "mg")], ["PO"], ["daily"], ["Claritin"], ["lora tadine"], []),
]

SYMPTOMS = {   # canonical -> synonyms, severity style, locations, duration phrases
    "pain": dict(syn=["pain", "hurting", "aching"], sev="numeric", loc=["head", "neck", "back", "abdomen", "legs", "hip", "chest", "everywhere"]),
    "shortness of breath": dict(syn=["trouble breathing", "short of breath", "can't catch his breath", "labored breathing"], sev="graded", risk="breathing_concern"),
    "agitation": dict(syn=["agitated", "restless and pulling at things", "can't settle"], sev="graded"),
    "restlessness": dict(syn=["restless", "can't get comfortable"], sev="graded"),
    "confusion": dict(syn=["confused", "doesn't know where he is", "disoriented"], sev="graded"),
    "anxiety": dict(syn=["anxious", "worried and panicky"], sev="graded"),
    "nausea": dict(syn=["nauseated", "queasy", "sick to her stomach"], sev="graded"),
    "vomiting": dict(syn=["throwing up", "vomiting"], sev="count"),
    "constipation": dict(syn=["constipated", "hasn't had a bowel movement"], sev="days"),
    "diarrhea": dict(syn=["loose stools", "diarrhea"], sev="count"),
    "fever": dict(syn=["fever", "feels hot"], sev="temp"),
    "chills": dict(syn=["shivering", "chills"], sev="graded"),
    "cough": dict(syn=["cough", "coughing a lot"], sev="graded"),
    "nasal congestion": dict(syn=["stuffy nose", "congested"], sev="graded"),
    "sore throat": dict(syn=["sore throat", "throat hurts"], sev="graded"),
    "lethargy": dict(syn=["very tired", "sleeping most of the day", "lethargic"], sev="graded"),
    "decreased appetite": dict(syn=["not eating", "not hungry"], sev="graded"),
    "dizziness": dict(syn=["dizzy", "lightheaded"], sev="graded"),
    "insomnia": dict(syn=["not sleeping", "up all night"], sev="graded"),
    "swelling": dict(syn=["swollen legs", "swelling in her feet"], sev="graded"),
    "urinary retention": dict(syn=["not urinating", "hasn't peed"], sev="hours"),
    "terminal secretions": dict(syn=["rattling", "gurgling", "congested chest sounds"], sev="graded"),
    "skin breakdown": dict(syn=["a sore on her back", "a red spot that's opening up"], sev="graded"),
    "headache": dict(syn=["headache"], sev="numeric"),
    "weakness": dict(syn=["very weak", "can't stand up"], sev="graded"),
    "difficulty swallowing": dict(syn=["can't swallow pills", "chokes on liquids"], sev="graded"),
    "fall": dict(syn=["fell", "slid out of the chair"], sev="count"),
}
SEVERITY_GRADES = ["mild", "moderate", "severe"]
DURATIONS = ["since this morning", "since last night", "for the last couple of days", "for about three days",
             "for a week", "since Monday", "on and off for a few weeks", "just started an hour ago"]
HEDGES = ["i think", "maybe", "about", "around", "approximately", "not sure", "i'm not sure", "i believe", "probably",
          "kind of", "sort of", "i guess", "something like", "i don't know", "might be", "could be", "roughly",
          "i can't remember", "if i remember right", "[inaudible]"]
NEGATION_WORDS = ["no", "not", "never", "denies", "denied", "without", "hasn't", "haven't", "doesn't", "didn't",
                  "isn't", "none", "nothing", "n't"]   # 5-token window; suicidal phrases are never negation-suppressed
NEGATION_WINDOW = 5

RISK_PHRASES = {
    "breathing_concern": ["trouble breathing", "can't breathe", "cannot breathe", "short of breath", "shortness of breath",
                          "gasping", "struggling to breathe", "labored breathing", "hard time breathing", "difficulty breathing",
                          "can't catch his breath", "can't catch her breath", "wheezing", "choking", "gurgling", "rattling"],
    "uncontrolled_symptom": ["not working", "didn't help", "doesn't help", "nothing helps", "uncontrolled", "uncontrollably",
                             "getting worse", "unbearable", "screaming", "crying out", "ten out of ten", "nine out of ten",
                             "eight out of ten", "seven out of ten", "can't get comfortable", "breakthrough", "won't stop"],
    "medication_concern": ["ran out", "run out", "running low", "almost out", "missed a dose", "missed doses", "too many",
                           "double dose", "gave too much", "wrong dose", "wrong medication", "wrong medicine", "no refill",
                           "can't swallow", "stopped taking", "stopped all", "refusing", "won't take", "dropped the", "spilled the"],
    "suicidal_statement": ["want to die", "wants to die", "kill myself", "kill himself", "kill herself", "end my life",
                           "end it all", "don't want to live", "better off dead", "suicidal", "hurt myself", "take all the pills",
                           "not worth living"],
    "escalation_request": ["send someone", "send a nurse", "come out", "come see", "need a visit", "need someone to come",
                           "nine one one", "911", "emergency room", "emergency department", "hospital", "ambulance",
                           "urgent care", "speak to a doctor", "talk to the doctor", "need to be seen", "please come"],
}
COMPLETION_CUES = ["i sent", "i've sent", "i have sent", "i put in", "i've put in", "i have put in", "i placed", "was delivered",
                   "has been delivered", "i called", "i've called", "was sent", "has been sent", "i submitted", "i've submitted",
                   "i entered", "already done", "just did", "it's done", "went ahead and"]
FUTURE_CUES = ["i will", "i'll", "i'm going to", "going to", "gonna", "let me", "will try", "i'll try", "we'll", "they will",
               "they'll", "someone will", "plan to", "i would", "i can put", "i can send"]

ACTION_TYPES = {  # type -> (planned template, completed template) ; {x} = slot
    "refill_request": ("I'll put in a refill request for {x}.", "I've put in the refill request for {x}."),
    "team_message": ("I'm going to send a message to the team about {x}.", "I sent a message to the team about {x}."),
    "nurse_visit": ("I'll have a nurse come out {x}.", "A nurse is scheduled to come out {x}."),
    "callback": ("I'll have the on-call nurse call you back {x}.", "The on-call nurse has been paged and will call you {x}."),
    "escalation_911_ed": ("I'd recommend calling 911 and going to the emergency department {x}.", None),
    "appointment_scheduling": ("The team will call to schedule an appointment {x}.", "I've scheduled an appointment {x}."),
    "physician_notification": ("I'll let the doctor know about {x}.", "I notified the doctor about {x}."),
    "documentation": ("I'll document {x} in my notes.", "I documented {x}."),
    "medication_order": ("I'll ask the doctor to order {x}.", "The order for {x} has been entered."),
    "referral": ("I'd advise getting {x} evaluated in person.", None),
}
EDUCATION_TYPES = {
    "medication_instruction": "You can give {x}.", "medication_timing": "Try to keep to the schedule, {x}.",
    "medication_safety": "Please don't change {x} without checking with us.", "administration_method": "If {x}, you can place it under the tongue.",
    "comfort_measure": "It helps to {x}.", "return_precaution": "Call us back right away if {x}.",
    "follow_up_expectation": "Someone from the team will {x}.", "callback_invitation": "Please call us if you have any questions.",
    "emergency_guidance": "Call 911 if {x}.", "supportive_care": "Keep up {x}.",
}
NA_SUBTYPES = ["wrong_number", "hang_up", "billing_admin_only", "test_call"]
HIGH_RISK_SUBTYPES = ["uncontrolled_symptom", "medication_concern", "suicidal_statement", "breathing_concern", "escalation_request"]
RELATIONSHIPS = ["daughter", "son", "spouse", "mother", "father", "facility nurse", "patient (self)", "sister", "granddaughter", "friend"]
AGENCIES = ["Meadow Hospice", "Pine Home Health", "Cedar Care Cooperative", "Maple Grove Hospice", "Harbor Home Care",
            "Willow Creek Hospice", "Summit Home Health", "Lakeside Care Partners"]


def drug_combos() -> list[tuple[str, float, str]]:
    return [(d["generic"], v, u) for d in FORMULARY for v, u in d["doses"]]


def export(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "formulary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["generic", "tall_man", "class", "setting", "aliases", "routes", "frequencies", "dose_options",
                    "asr_sound_alikes", "asr_out_of_formulary_mishears", "clinically_validated"])
        for d in FORMULARY:
            w.writerow([d["generic"], d["tall_man"], d["cls"], d["setting"], "|".join(d["aliases"]), "|".join(d["routes"]),
                        "|".join(d["freqs"]), "|".join(f"{v} {u}" for v, u in d["doses"]), "|".join(d["sound_alikes"]),
                        "|".join(d["oov_mishears"]), "NO"])
    for name, obj in dict(symptoms=SYMPTOMS, risk_phrases=RISK_PHRASES, hedges=HEDGES,
                          negation=dict(words=NEGATION_WORDS, window=NEGATION_WINDOW),
                          cues=dict(completion=COMPLETION_CUES, future=FUTURE_CUES),
                          action_types=ACTION_TYPES, education_types=EDUCATION_TYPES).items():
        (out / f"{name}.json").write_text(json.dumps(obj, indent=1))


if __name__ == "__main__":
    export(Path(__file__).parent / "data/lexicons")
    print(len(FORMULARY), "drugs;", len(drug_combos()), "(drug, dose, unit) combos")
