"""Hand-annotated gold fact records for the 5 real examples (sanity set).

Every fact is grounded by a verbatim `anchor`; build() resolves anchors to turn
ids and raises if any anchor is missing/ambiguous, so annotations are
machine-checked against the transcripts.

POLICY DECISIONS (where gold deliberately differs from, or is stricter than, the reference summaries):
 P1 Ex3 'carfentanil'  -> medication certainty=unclear, name=None (never emitted as stated).
 P2 Ex3 caller name    -> 'Nora Quinn' (self-stated); Nadine/Noreen/Norine kept as alternates.
 P3 Ex5 'ibuprofen'    -> certainty=unclear. Only mention is one nurse turn; caller never named it and
                          'keep that airway open' fits albuterol. Reference repeats it as stated.
 P4 Ex4 BP 181/154     -> certainty=unclear (caller doubts reading; diastolic implausible). Preserved, not interpreted.
 P5 Ex5 DOB 'ten eight two thousand eighteen' -> 2018-10-08 (US month/day assumed), note kept.
 P6 'escalation_request' covers nurse-initiated emergency escalation (Ex4) as well as caller requests.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import yaml
from schema import *
from transcript_utils import split_turns, resolve_anchor

HERE = Path(__file__).parent
E = lambda sp, a, occ=None, after=0: Evidence(speaker=sp, anchor=a, occurrence=occ, span_after=after)
C = lambda a, **k: E("Caller", a, **k)
N = lambda a, **k: E("Nurse", a, **k)


def ID(value, status, ev, alternates=(), note=None):
    return IdField(value=value, status=status, evidence=ev, alternates=list(alternates), note=note)


def record_1() -> FactRecord:
    return FactRecord(
        record_id="real_01", source="real", split="sanity", category="medication",
        secondary_tags=["supply", "uncontrolled_symptom"], agency="Meadow Hospice",
        identity=Identity(
            patient_name=ID("Mara Ellis", "stated", [C("Mara Ellis I'm calling for")]),
            patient_dob=ID("1951-06-04", "stated", [C("June fourth nineteen fifty one")]),
            caller_name=ID("Nina", "stated", [C("This is Nina")]),
            relationship=ID("daughter", "stated", [C("Her daughter")]),
            callback_phone=ID("2025550101", "stated", [C("Yes two zero two five five five zero one zero one")])),
        reason_for_call="Asks whether to give lorazepam and morphine together or which first, for recurrent pain",
        symptoms=[
            Symptom(id="S1", name="pain", severity="8-9/10", location=["head", "neck", "back"],
                    onset_duration="returned this morning; morphine relieved it ~22:30-06:30",
                    evidence=[C("She's saying it's like it was last night about an eight nine"),
                              C("She's saying it's in her head her neck and her back")]),
            Symptom(id="S2", name="restlessness", evidence=[C("So far not really anxious just restless")],
                    note="Caller thinks restlessness is driven by pain")],
        pertinent_negatives=[PertinentNegative(id="N1", name="anxiety", evidence=[C("not really anxious just restless")])],
        context=[
            ContextFact(id="X1", kind="diagnosis", text="lymphoma", evidence=[C("of course she has lymphoma")]),
            ContextFact(id="X2", kind="diagnosis", text="degenerative disc disease", evidence=[C("she does have degenerative disc")]),
            ContextFact(id="X3", kind="functional_status", text="in bed for a couple of days, bearing little weight",
                        evidence=[C("she's been in bed now for a couple days")])],
        medications=[
            Medication(id="M1", name="morphine", dose="0.25", unit="mL", route="PO", frequency="q4h", prn=True,
                       status="ordered", evidence=[N("She can have 0.25 milliliters by mouth every four hours as needed for pain")]),
            Medication(id="M2", name="morphine", status="administered", last_dose="22:30 previous night",
                       evidence=[C("at ten thirty we did I called and we did the morphine on top of that")]),
            Medication(id="M3", name="lorazepam", status="administered", last_dose="22:00 previous night",
                       evidence=[C("and then at ten was the lorazepam")]),
            Medication(id="M4", name="lorazepam", dose=None, unit="tablet", frequency="q4h", status="ordered",
                       evidence=[N("it looks like she has the lorazepam or Ativan It's ordered every four hours per tablet")],
                       note="Form 'tablet' and 'every four hours' stated. Strength never stated, and 'per tablet' does not state a quantity per dose, "
                            "so dose is NOT recorded (audit: the earlier dose='1' was an inference)."),
            Medication(id="M5", name="lorazepam", dose="1", unit="tablet", status="administered", last_dose="during call",
                       evidence=[C("Of the lorazepam I have it's in the other room so I can do that"),
                                 C("There is there's seven Now I have six I'm giving her one now so now I have six left")]),
            Medication(id="M6", name=None, name_as_heard="muscle relaxer", status="administered", last_dose="19:30 previous night",
                       certainty="unclear", critical=False,
                       evidence=[C("Muscle relaxer and then at ten was the lorazepam")], note="Name never stated."),
            Medication(id="M7", name="morphine", strength="100 mg/5 mL", status="label_read", certainty="unclear",
                       evidence=[C("It says morphine sulfate oral solution one hundred mg per five mL")],
                       note="Caller read the label hesitantly; earlier garble 'twenty hundred milligrams per five mL'; bottle volume 'I think' 15 mL.")],
        supplies=[
            Supply(id="U1", item="morphine", quantity_remaining="3 doses (caller estimate)", request="delivery", certainty="unclear",
                   evidence=[C("only have three more doses I think of the morphine and about six of the lorazepam")],
                   note="Caller later reads a 15 mL bottle and doubts the count."),
            Supply(id="U2", item="lorazepam", quantity_remaining="6 tablets (after giving one)", request="delivery",
                   evidence=[C("There is there's seven Now I have six I'm giving her one now so now I have six left")]),
            Supply(id="U3", item="morphine and lorazepam", request="delivery",
                   evidence=[C("so is it possible to have enough delivered today")],
                   note="Caller will not see the visiting nurse until Tuesday.")],
        actions=[
            Action(id="A1", type="refill_request", description="try to put in refill requests for morphine and lorazepam",
                   status="planned", evidence=[N("But I will try to put both of those in for you")]),
            Action(id="A2", type="team_message", description="let the team know remaining supply so delivery can be arranged",
                   status="planned", evidence=[N("I will try to order that for her and I'll let them know how many you have left")])],
        education=[
            Education(id="E1", type="medication_instruction", description="give lorazepam and morphine every 4 hours consistently",
                      evidence=[N("So you can go ahead and give those doses every four hours for her")]),
            Education(id="E2", type="medication_timing", description="do not wake her solely for pain medication; give when awake, keep to 4-hour mark",
                      evidence=[N("I wouldn't say wake her up if she's sleeping for the pain medications")]),
            Education(id="E3", type="comfort_measure", description="reposition 30-45 minutes after medication if able",
                      evidence=[N("If she's able to change positions like 30 to 45 minutes after the medication is administered")]),
            Education(id="E4", type="administration_method", description="if she cannot swallow, wet the tablet and place under tongue",
                      evidence=[N("you can wet the tablet and place it under her tongue")],
                      note="Tablet = lorazepam inferred from caller's garbled 'Phalarisipham' and the crush/applesauce question."),
            Education(id="E5", type="return_precaution", description="call back if no pain relief after consistent dosing",
                      evidence=[N("she's really not getting any pain relief from the medication she has ordered")]),
            Education(id="E6", type="callback_invitation", description="call with any questions or concerns",
                      evidence=[N("if you have any questions or concerns")])],
        risk_flags=[
            RiskFlag(id="R1", category="uncontrolled_symptom", rationale="pain recurred at 8-9/10",
                     evidence=[C("but the pain now is returned")]),
            RiskFlag(id="R2", category="medication_concern", rationale="very low reported supply of opioid/anxiolytic; next scheduled nurse contact is days away",
                     evidence=[C("only have three more doses I think of the morphine and about six of the lorazepam")])],
        annotation_notes=["Caller says 'I told Lena yesterday' - Lena is another clinician, not an identity field."])


def record_2() -> FactRecord:
    mentioned = [  # (id, canonical generic, as-heard, anchor)
        ("M6", "bisacodyl", "Dulcolax suppository", "He is on Dulcolax suppository"),
        ("M7", "famotidine", "Pepcid", "Then he's on Pepcid which is for stomach acid"),
        ("M8", "bupropion", "Wellbutrin", "Lidocaine and he is on Wellbutrin"),
        ("M9", "metformin", "Glucophage / 'Metroforum'", "He's ordered glucophage"),
        ("M10", "lisinopril", "Lisinopril", "Slo-Max Libator Lisinopril Albuterol"),
        ("M11", "finasteride", "Proscar", "And this one is Proscar"),
        ("M12", "sertraline", "Zoloft", "Another nebulizer Zoloft Glucophage Wellbutrin")]
    return FactRecord(
        record_id="real_02", source="real", split="sanity", category="medication",
        secondary_tags=["asr_error", "ambiguous", "nonadherence"], agency="Pine Home Health",
        identity=Identity(
            patient_name=ID("Miles Harper", "stated", [C("Miles Harper")], alternates=["Mile", "Myles"],
                            note="Nurse says 'Mile'; caller later says 'Myles' to the patient."),
            patient_dob=ID("1949-02-09", "stated", [C("Two nine forty nine")],
                           note="Spoken M D YY; century from nurse's 'nineteen forty-nine' one turn earlier."),
            caller_name=ID("Leah", "stated", [C("Leah", occ=0)]),
            relationship=ID("spouse", "stated", [C("So I have this thing with my husband today")],
                            note="Nurse also states 'documented as patient spouse'; caller 'Yep'."),
            callback_phone=ID("2025550102", "stated", [N("I have you with a contact number of two zero two five five five zero one zero two")],
                              note="Read back from record; caller confirmed.")),
        reason_for_call="Dizziness, confusion, constant need for reassurance, poor sleep; caller wants something to help him sleep",
        symptoms=[
            Symptom(id="S1", name="dizziness", onset_duration="last couple of days",
                    evidence=[C("he's dizzy all the time a lot quite often"), C("Well for the last couple of days")]),
            Symptom(id="S2", name="confusion", onset_duration="last couple of days", evidence=[C("he's confused")]),
            Symptom(id="S3", name="reassurance-seeking (repeatedly looks for caller, asks if she is okay, incl. at night)",
                    onset_duration="last couple of days",
                    evidence=[C("He constantly needs to know where I am or he'll come looking for me")]),
            Symptom(id="S4", name="sleep disruption (does not stay asleep)", onset_duration="last couple of nights",
                    evidence=[C("he just didn't stay asleep")])],
        context=[
            ContextFact(id="X1", kind="nonadherence", text="has stopped nearly all prescribed medications except morphine and haloperidol",
                        evidence=[C("He mainly stopped all of the meds"), C("Just taking those two main morphine and that")]),
            ContextFact(id="X2", kind="caller_concern", text="worried that stopping the prostate medication may impair urination",
                        evidence=[C("I'm worried about him not going you know to urinate")]),
            ContextFact(id="X3", kind="caller_concern", text="caller reluctant to give patient her own amitriptyline without guidance",
                        evidence=[C("I don't want to give him mine in case you know it's not good for him right now")])],
        medications=[
            Medication(id="M1", name="morphine", status="current", evidence=[C("Just taking those two main morphine and that")]),
            Medication(id="M2", name="haloperidol", frequency="q4h", prn=True, status="current",
                       evidence=[N("the haloperidol which is also called haldol and this can be given every four hours for agitation")],
                       note="Order described by nurse from chart; dose not stated."),
            Medication(id="M3", name="lorazepam", frequency="three times a day (previous)", status="stopped",
                       evidence=[N("And then he also has lorazepam"), C("Yep they got him on there for three times a day"),
                                 C("They took him off in that", occ=0), C("because he just out You couldn't wake him up for nothing")],
                       note="Stopped by prescriber for oversedation per caller. Evidence widened by the audit: name (T37), frequency (T38), stop (T41) were not cited."),
            Medication(id="M4", name="tamsulosin", name_as_heard="Flomax; caller spelled T-T-A-M-S-U-L-O-S-I-N; nurse 'tamifluoln'",
                       strength="0.4 capsule (unit not stated)", dose="0.8", frequency="once daily after a meal", status="ordered",
                       evidence=[N("it's the tamisol"), N("the Flomax 0 4 capsule and it's the dose is 0 8"), N("And once a day after a meal")],
                       note="Dose 0.8 vs 0.4 capsule preserved exactly as the nurse read it; units never stated. Resolved to Flomax from chart."),
            Medication(id="M5", name="amitriptyline", name_as_heard="Ampatripoline", status="requested",
                       evidence=[C("Yes it did In fact me yeah me and him take the same"), C("I'm grabbing it right now right Ampatripoline")],
                       note="Prior benefit reported by caller; nurse confirmed spelling 'Amitriptyline'.")]
            + [Medication(id=i, name=g, name_as_heard=h, status="mentioned", critical=False, evidence=[N(a)],
                          note="Read from chart by nurse; covered by the caller's blanket 'stopped all of the meds'.")
               for i, g, h, a in mentioned],
        actions=[
            Action(id="A1", type="team_message", description="message the team to find a sleep aid for the patient",
                   status="planned", evidence=[N("Go ahead and send a message to his team so that they can look into it and see what would be good for him for sleep")]),
            Action(id="A2", type="team_message", description="submit amitriptyline request early because it is Friday",
                   status="planned", evidence=[N("I'm going to put it in Early because it's Friday")]),
            Action(id="A3", type="documentation", description="document medications not being taken and Flomax trial",
                   status="planned", evidence=[N("I will also document it on the medications that he's not taking")])],
        education=[
            Education(id="E1", type="medication_safety", description="contact the physician before stopping any medication",
                      evidence=[N("you just need to contact the physician before you stop any medications")]),
            Education(id="E2", type="medication_instruction", description="give Flomax if he will take it (on current list, no end date)",
                      evidence=[N("if he'll take it to give that to him")]),
            Education(id="E3", type="return_precaution", description="notify the physician if he continues to refuse Flomax",
                      evidence=[N("If he doesn't then I would go ahead and let the physician know")]),
            Education(id="E4", type="follow_up_expectation", description="team will review notes and likely call back about amitriptyline",
                      evidence=[N("more than likely they'll give you a call back or they'll contact you and ask about that amitriptyline")]),
            Education(id="E5", type="callback_invitation", description="contact the agency if anything else is needed",
                      evidence=[N("Let us know if there's anything else")])],
        risk_flags=[
            RiskFlag(id="R1", category="medication_concern", rationale="patient has stopped nearly all prescribed medications",
                     evidence=[C("He mainly stopped all of the meds")]),
            RiskFlag(id="R2", category="uncontrolled_symptom", required=False,
                     rationale="new confusion and near-constant dizziness for 2 days (acceptable, not required)",
                     evidence=[C("he's dizzy all the time a lot quite often")])],
        annotation_notes=["Long off-topic small talk (cat) contains no clinical facts.",
                          "Unresolved nurse-read names 'Slo-Max', 'Libator' not recorded."])


def record_3() -> FactRecord:
    return FactRecord(
        record_id="real_03", source="real", split="sanity", category="high_risk", subtype="breathing",
        secondary_tags=["asr_error", "ambiguous"], agency="Meadow Hospice of Maple Grove",
        identity=Identity(
            patient_name=ID("Evan Bennett", "stated", [C("Bennett Evan Bennett B E N N E T T")], alternates=["Bennett Evan Bennett"],
                            note="Surname confirmed by letter-spelling; first name heard once, inside a duplicated-surname utterance."),
            patient_dob=ID("1939-04-14", "stated", [C("April fourteenth of nineteen thirty nine"), C("His date of birth is April fourteenth nineteen thirty nine")]),
            caller_name=ID("Nora Quinn", "stated", [C("I'm Nora Quinn")], alternates=["Nadine", "Noreen", "Norine"],
                           note="POLICY P2: self-stated 'Nora Quinn' wins; caller first said 'Nadine', nurse read back 'Noreen and Norine'. UI must surface the conflict."),
            relationship=ID("daughter", "stated", [C("I'm his daughter")]),
            callback_phone=ID("2025550103", "stated", [C("Two zero two five five five zero one zero three")])),
        reason_for_call="Trouble breathing and some agitation",
        symptoms=[
            Symptom(id="S1", name="trouble breathing", evidence=[C("he's having yeah he's having trouble breathing and then")]),
            Symptom(id="S2", name="agitation", severity="mild", evidence=[C("A little agitation also")])],
        context=[ContextFact(id="X1", kind="other", text="caller heard urging patient to wait/use walker to avoid falling (fall risk during call)",
                             evidence=[C("Dad wait Please you're gonna fall")])],
        medications=[
            Medication(id="M1", name="lorazepam", status="advised", evidence=[N("so yeah give him the lorazepam and then I'll give you a call back here in about thirty minutes")],
                       note="Dose not stated."),
            Medication(id="M2", name="morphine", status="advised", evidence=[N("with the trouble breathing we can give him a dose of his morphine")],
                       note="Offered for breathing; nurse chose to start with lorazepam only."),
            Medication(id="M3", name="lorazepam", status="administered", last_dose="prior episode",
                       evidence=[C("he had a trouble breathing one other time We gave him lorazepam That help the breathing and the agitation")],
                       note="Caller reports lorazepam helped both symptoms previously."),
            Medication(id="M4", name=None, name_as_heard="carfentanil", status="advised", certainty="unclear",
                       evidence=[N("we'll see how he's doing before advising the carfentanil")],
                       note="POLICY P1: almost certainly ASR for 'morphine' (named earlier by the nurse). Reference repeats it as stated; gold requires 'unclear' + possible-mishearing flag."),
            Medication(id="M5", name=None, name_as_heard="normal meds", status="administered", last_dose="18:00 previous evening",
                       certainty="unclear", critical=False, evidence=[C("Six o'clock last night He took his normal meds")],
                       note="Specific drugs not named.")],
        actions=[Action(id="A1", type="callback", description="nurse to call back in about 30 minutes to reassess before advising further medication",
                        status="planned", evidence=[N("I'll give you a call back here in about thirty minutes")])],
        education=[Education(id="E1", type="callback_invitation", description="call back sooner than 30 minutes if needed",
                             evidence=[N("if you need us sooner feel free to call us back before that")])],
        risk_flags=[RiskFlag(id="R1", category="breathing_concern", rationale="caller reports trouble breathing",
                             evidence=[C("he's having yeah he's having trouble breathing and then")])],
        annotation_notes=["Short call (31 turns); two identity conflicts (caller name, patient first name)."])


def record_4() -> FactRecord:
    return FactRecord(
        record_id="real_04", source="real", split="sanity", category="high_risk", subtype="escalation",
        secondary_tags=["ambiguous", "asr_error"], agency="Pine Home Care",
        identity=Identity(
            patient_name=ID("Mina Lane", "stated", [C("Mina Lane")]),
            patient_dob=ID("1933-02-13", "stated", [C("Two thirteen eighty three"), C("Nineteen thirty three")],
                           note="First utterance garbled ('eighty three'; nurse misread 'fifty three'); caller then gave 'nineteen thirty-three'."),
            caller_name=ID("Owen", "stated", [C("Owen")], alternates=["Olivia"], note="Nurse closes with 'You're welcome, Olivia' (name drift)."),
            relationship=ID("child", "stated", [C("My mom who's over 90 years old")], note="Caller says 'my mom'; sex of caller not stated."),
            callback_phone=ID("2025550104", "stated", [C("this number two zero two five five five zero one zero four")])),
        reason_for_call="Mother is shivering uncontrollably; caller unsure of cause, suspects urinary infection",
        symptoms=[
            Symptom(id="S1", name="shivering", severity="uncontrollable",
                    evidence=[C("She just called me to her room because she's shivering"), C("Uncontrollably she doesn't appear to have a fever")]),
            Symptom(id="S2", name="lethargy", onset_duration="today",
                    evidence=[C("she felt very lethargic and so she didn't bother to")]),
            Symptom(id="S3", name="decreased appetite", onset_duration="today", evidence=[C("She just wasn't that hungry")]),
            Symptom(id="S4", name="moaning", reporter="Nurse", evidence=[N("I can hear her moaning in the background")],
                    note="Nurse heard it; caller said it is not normal for her ('she's just so cold').")],
        pertinent_negatives=[
            PertinentNegative(id="N1", name="fever (apparent)", evidence=[C("she doesn't appear to have a fever")]),
            PertinentNegative(id="N2", name="strong urine odor or color change", evidence=[C("No no but last she does have a chronic Foley catheter")])],
        vitals=[Vital(id="V1", name="bp", value="181/154", certainty="unclear",
                      evidence=[C("I'm not sure this is an accurate reading but it says 181 over 154 and her heart rate is 60")],
                      note="POLICY P4: caller doubts accuracy; diastolic 154 implausible. Preserve as stated + unclear; do not interpret."),
                Vital(id="V2", name="hr", value="60", unit="bpm", certainty="unclear",
                      evidence=[C("I'm not sure this is an accurate reading but it says 181 over 154 and her heart rate is 60")])],
        context=[
            ContextFact(id="X1", kind="history", text="chronic Foley catheter, normally changed every 3 weeks",
                        evidence=[C("she does have a chronic Foley catheter and normally we change it every three weeks")]),
            ContextFact(id="X2", kind="history", text="catheter clogged last week; replaced by after-hours nurse; no symptoms until today",
                        evidence=[C("after ten days of the change it got clogged last week So we had to call for an after hours nurse to come and change her catheter and then she was fine")]),
            ContextFact(id="X3", kind="caller_concern", text="caller notes that when she does this she has had a urinary infection",
                        evidence=[C("Except when she does this she has an a urinary infection")])],
        actions=[Action(id="A1", type="escalation_911_ed", description="recommended calling 911 / going to the emergency department",
                        status="advised", evidence=[N("I would recommend to call nine one one and take her to the emergency department")])],
        education=[
            Education(id="E1", type="emergency_guidance", description="possible infection can worsen quickly at her age",
                      evidence=[N("an infection brewing and with her age you know that can that can go bad quickly")]),
            Education(id="E2", type="callback_invitation", description="call with any other questions",
                      evidence=[N("please give us a call if you have any other questions")])],
        risk_flags=[
            RiskFlag(id="R1", category="escalation_request", rationale="nurse recommends 911/ED (POLICY P6)",
                     evidence=[N("I would recommend to call nine one one and take her to the emergency department")]),
            RiskFlag(id="R2", category="uncontrolled_symptom", rationale="uncontrollable shivering with moaning",
                     evidence=[C("Uncontrollably she doesn't appear to have a fever")])],
        annotation_notes=["Long non-linguistic noise in the middle (laughter, 'I'm in a trance') carries no facts."])


def record_5() -> FactRecord:
    neg = [("N1", "difficulty breathing", N("Would you say that he is having difficulty breathing and it's severe"), 1),
           ("N2", "slow, shallow or weak breathing", N("Have you noticed any slow shallow or weak breathing"), 1),
           ("N3", "syncope with coughing", N("has he ever passed out due to this coughing"), 1),
           ("N4", "hemoptysis", N("has he coughed up any blood or blood thin mucus"), 1),
           ("N5", "retractions", N("Have you noticed any retractions"), 1),
           ("N6", "earache", N("And he hasn't complained about Any earaches Is this correct"), 1),
           ("N7", "facial/sinus pain or pressure", N("Any pain around like the cheek the jaw area pressure he hasn't complained about any of that"), 1)]
    return FactRecord(
        record_id="real_05", source="real", split="sanity", category="routine", subtype="pediatric_triage",
        secondary_tags=["asr_error", "negation_test"], agency="Cedar Care Cooperative",
        identity=Identity(
            patient_name=ID("Ethan Mercer", "stated", [C("Mercer M E R C E R"), N("the first name is Ethan E T H A N")]),
            patient_dob=ID("2018-10-08", "stated", [C("Yep is ten eight two thousand eighteen")],
                           note="POLICY P5: month/day order assumed US; first utterance garbled 'ten eight of eighteen two thousand eighteen'."),
            caller_name=ID("Naomi Mercer", "stated", [C("Hi this is Naomi Mercer")], alternates=["Naomi Marlowe"],
                           note="Nurse read back 'Naomi Marlowe'. 'Clara' is the call-center agent who transferred the call, not the caller."),
            relationship=ID("mother", "stated", [C("I got his mom on the phone"), N("Hi Mom Thank you")]),
            callback_phone=ID("2025550105", "stated", [N("and that is two zero two five five five zero one zero five")])),
        reason_for_call="Worsening cough since Monday 31 Aug with congestion/drainage, not helped by allergy pill or albuterol; caller asks about asthma",
        symptoms=[
            Symptom(id="S1", name="cough (deep, raspy, wet; worsening)", onset_duration="since Monday 31 August",
                    evidence=[C("so Ethan has had a cough since Monday the thirty first of August"), C("this inhaler is not touching his cough and his cough is getting worse")]),
            Symptom(id="S2", name="nasal congestion and drainage", evidence=[C("he's had a lot of drainage")]),
            Symptom(id="S3", name="sleep disruption from cough", evidence=[C("It's now keeping him up at night")]),
            Symptom(id="S4", name="sore throat (intermittent)", onset_duration="about a week", evidence=[C("he says his throat hurts")]),
            Symptom(id="S5", name="mild chest discomfort during night coughing", severity="mild", onset_duration="last night",
                    evidence=[C("he did say his chest hurt a little bit last night during the night")]),
            Symptom(id="S6", name="crackly breath sounds", severity="a little",
                    evidence=[C("I mean it does sound a little crackly")], note="Hedged by caller: cough is deep and raspy anyway."),
            Symptom(id="S7", name="body aches and weakness (Tuesday only)", onset_duration="Tuesday",
                    evidence=[C("Tuesday he said his body felt weak and achy")])],
        pertinent_negatives=[PertinentNegative(id=i, name=n, evidence=[ev.model_copy(update={"span_after": s})]) for i, n, ev, s in neg]
        + [PertinentNegative(id="N8", name="current chest pain", evidence=[C("No no I don't I don't I I mean I sent him to school")]),
           PertinentNegative(id="N9", name="current fever", evidence=[C("he hasn't really had a fever")])],
        vitals=[Vital(id="V1", name="temp", value="100.6", when="Tuesday the 8th", evidence=[C("It was like a hundred point six")],
                      note="Unit not stated (assumed F).")],
        context=[
            ContextFact(id="X1", kind="history", text="allergy testing positive for grass and cats", evidence=[C("he came back allergic to grass and cats")]),
            ContextFact(id="X2", kind="history", text="recurrent deep raspy wet coughs several times a year",
                        evidence=[C("these deep raspy wet coughs several times a year")]),
            ContextFact(id="X3", kind="caller_concern", text="caller wonders whether this is asthma and asks about testing",
                        evidence=[C("I just feel like maybe it could be asthma")]),
            ContextFact(id="X4", kind="functional_status", text="attending school; walking and eating normally", evidence=[C("he was walking and eating normally")])],
        medications=[
            Medication(id="M1", name="albuterol", route="inhaled", frequency="three times a day for about 1 week", status="current",
                       evidence=[C("Is albuterol inhaler he's been taking his inhaler three times a day for the last week and it's not helping")],
                       note="Caller later says he only uses it when allergies flare (inconsistent); preserved."),
            Medication(id="M2", name=None, name_as_heard="allergy pill", status="current", certainty="unclear", critical=False,
                       evidence=[C("he's been taking his allergy pill")], note="Name not stated."),
            Medication(id="M3", name=None, name_as_heard="ibuprofen", status="advised", certainty="unclear",
                       evidence=[N("taking the ibuprofen as directed")],
                       note="POLICY P3: single mention by nurse; caller never named ibuprofen; 'keep that airway open' fits albuterol. Reference repeats as stated; gold requires 'unclear'.")],
        actions=[
            Action(id="A1", type="referral", description="advised in-person evaluation within 3 days (rule out sinusitis, allergic reaction, strep, infection)",
                   status="advised", evidence=[N("it is advised for him to be sent within three days")]),
            Action(id="A2", type="appointment_scheduling", description="care team to follow up today or tomorrow to schedule appointment",
                   status="planned", evidence=[N("one of the care teams will follow up with you to try to schedule an appointment for him")]),
            Action(id="A3", type="documentation", description="nurse will document in notes", status="planned", evidence=[N("I will put in my notes")])],
        education=[
            Education(id="E1", type="return_precaution", description="call back to retriage if cough worsens, headache/pressure, blocked drainage, difficulty breathing or chest pain with cough",
                      evidence=[N("if he does come back from school and you notice that he's coughing is getting worse")]),
            Education(id="E2", type="medication_instruction", description="keep taking ibuprofen as directed (UNCLEAR drug, see M3)",
                      evidence=[N("taking the ibuprofen as directed")]),
            Education(id="E3", type="supportive_care", description="warm fluids help cough", evidence=[N("Warm water does help with coughing as well")]),
            Education(id="E4", type="return_precaution", description="call right away if no callback today and symptoms worsen; urgent care possible",
                      evidence=[N("if you don't receive a call back today and you notice any symptoms getting worse please don't hesitate Give us a call right away")])],
        risk_flags=[],
        annotation_notes=["NEGATION TEST: 'difficulty breathing', 'chest pain', 'fever' appear many times but are denied. Expected required flags: none.",
                          "Reference caption says mild chest discomfort 'after forceful coughing' with a weak quote; gold cites the actual turn."])


def build(yaml_path: Path = HERE / "data/raw/real5_examples.yaml") -> tuple[list[FactRecord], dict]:
    d = yaml.safe_load(open(yaml_path))["examples"]
    recs = [record_1(), record_2(), record_3(), record_4(), record_5()]
    transcripts = {}
    for rec, ex in zip(recs, d):
        turns = split_turns(ex["input_transcript"])
        transcripts[rec.record_id] = ex["input_transcript"]
        evs = []
        for f in (rec.identity.patient_name, rec.identity.patient_dob, rec.identity.caller_name,
                  rec.identity.relationship, rec.identity.callback_phone):
            evs += f.evidence
        for f in rec.all_facts():
            evs += f.evidence
        for ev in evs:
            ids = resolve_anchor(turns, ev.speaker, ev.anchor, ev.occurrence)
            if ev.span_after:
                ids = ids + [ids[-1] + k for k in range(1, ev.span_after + 1) if ids[-1] + k <= len(turns)]
            ev.turn_ids = ids
    return recs, transcripts


if __name__ == "__main__":
    recs, tr = build()
    out = HERE / "data/gold"
    (out / "real5_fact_records.json").write_text(json.dumps([r.model_dump() for r in recs], indent=1, ensure_ascii=False))
    for r in recs:
        print(r.record_id, "facts:", len(r.all_facts()), "critical slots:", len(r.critical_slots()),
              "required flags:", [f.category for f in r.risk_flags if f.required])
