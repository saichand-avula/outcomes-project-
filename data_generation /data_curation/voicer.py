"""Deterministic template voicer: FactRecord -> list[Turn] (clean text, per-turn fact tags). NO LLM, NO API, NO GPU.

Contract (what the rest of the pipeline relies on)
  * Every turn that expresses a fact value carries that fact's id in `Turn.fact_ids` (S#, N#, M#, U#, A#, E#, X#, R#,
    and 'ID.<field>' for identity). Any turn that mentions a drug is tagged with that drug's M# id, so ASR drug confusion
    (asr_noise.drug_confusion) garbles EVERY mention consistently.
  * Facts are voiced exactly: all of a medication's gold values (name, dose+unit, route, frequency) appear in its turns.
  * Stated facts contain no hedge words; unclear facts are hedged ("I think ... I'm not sure").
  * The nurse never commits to an action or gives instruction that is not a gold Action/Education (questions only).
  * Digits are written in digit form (phones, DOBs, doses, clock) so asr_noise.number_words can speak them;
    severities/quantities/frequencies are written as words directly (spoken.py).
  * Filler / interruptions / small talk contain no drug, number or clinical value.
"""
from __future__ import annotations
import hashlib
import random
import re

import lexicons as L
import spoken as SP
import spoken_numbers as SN
from schema import FactRecord, Medication, Symptom
from transcript_utils import Turn

FORM = {d["generic"]: d for d in L.FORMULARY}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
PRON = {"F": dict(sub="she", obj="her", pos="her"), "M": dict(sub="he", obj="him", pos="his")}

# symptom name -> caller phrase templates. Checked by tests: no risk-lexicon collision outside high-risk records.
SYM = {
    "pain": ["{Be} having pain{loc}", "{Be} hurting{loc}", "{Be} in pain{loc}"],
    "shortness of breath": ["{Be} having trouble breathing", "{Be} short of breath", "{Be} having a hard time breathing"],
    "agitation": ["{Be} very agitated", "{Be} getting agitated and pulling at the covers", "{Be} agitated and upset"],
    "restlessness": ["{Be} restless", "{Be} fidgety and restless"],
    "confusion": ["{Be} confused", "{Be} disoriented"],
    "anxiety": ["{Be} anxious", "{Be} worried and panicky"],
    "nausea": ["{Be} nauseated", "{Be} queasy", "{Be} sick to {pos} stomach"],
    "vomiting": ["{Be} throwing up", "{Be} vomiting"],
    "constipation": ["{Be} constipated"],
    "diarrhea": ["{Be} having loose stools", "{Be} having diarrhea"],
    "fever": ["{Be} running a fever", "{Be} burning up with a fever"],
    "chills": ["{Be} shivering", "{Be} having chills"],
    "cough": ["{Be} coughing a lot", "{Be} having a cough"],
    "nasal congestion": ["{Be} stuffed up with a stuffy nose", "{Be} congested"],
    "sore throat": ["{Be} complaining of a sore throat", "{has} a sore throat"],
    "lethargy": ["{Be} very tired", "{Be} lethargic", "{Be} sleeping most of the day"],
    "decreased appetite": ["{Be} not eating much", "{Be} not hungry"],
    "dizziness": ["{Be} dizzy", "{Be} lightheaded"],
    "insomnia": ["{Be} not sleeping", "{Be} up all night"],
    "swelling": ["{has} swollen legs", "{has} swelling in {pos} feet"],
    "urinary retention": ["{Be} not urinating", "{Hv} not been able to pee"],
    "skin breakdown": ["{has} a sore on {pos} back", "{has} a red spot that's opening up"],
    "headache": ["{Be} having a headache", "{has} a headache"],
    "weakness": ["{Be} very weak", "{Be} too weak to stand up"],
    "difficulty swallowing": ["{Be} having a hard time getting pills down", "{Be} having trouble getting {pos} medicine down"],
    "fall": ["{Hv} had a fall", "{sub} fell"],
}
SUICIDAL = {
    "patient": ["{Sub} keeps telling me {sub} wants to die.", "{Sub} said {sub} wants to die, and it scared me."],
    "caller": ["Honestly, I don't want to live like this anymore.", "I feel like I want to end my life, and I needed to tell someone."],
}
NEG_PHRASE = {"nausea": "nausea", "difficulty breathing": "trouble breathing", "confusion": "confusion", "fever": "fever", "falls": "falls"}
FALL_WHEN = {"since this morning": "this morning", "since last night": "last night", "since Monday": "on Monday",
             "for the last couple of days": "a couple of days ago", "for about three days": "three days ago",
             "for a week": "a week ago", "on and off for a few weeks": "a few times over the last few weeks",
             "just started an hour ago": "an hour ago", "despite last dose": "just now"}
ASIDES_CALLER = ["Hold on one second, I'm sorry.", "Sorry, the dog is barking. Hold on.", "Okay, I'm back. Sorry about that.",
                 "Can you hold on, someone is at the door?", "Sorry, my phone is breaking up a little.",
                 "Sorry, I had to move to another room.", "Hold on, let me sit down for a second.",
                 "The cat just jumped on the table, sorry about that.", "Sorry, I'm a little scattered today."]
ASIDES_HEAVY = ["Please, please wait a moment. You gotta hold on a second.", "Sorry, we have a lot going on here right now.",
                "I'm so sorry, the neighbors are stopping by. Hold on.", "Okay, okay, I'm here, I'm here. Sorry."]
CHATTER = ["It's just been a lot, honestly.", "We're all just really tired right now.", "I appreciate you being so patient with me.",
           "I'm sorry, I'm not good at this part.", "It's hard to see this, you know?", "Thank you for picking up so quickly."]
NURSE_EMPATHY = ["I'm sorry to hear that.", "That sounds really hard.", "I understand, take your time.", "No problem at all, take your time."]
ACKS = ["Okay.", "All right.", "Thank you.", "Perfect.", "Okay, thank you.", "Alright.", "Okay, great."]

COMFORT = ["Keep {obj} propped up with a couple of pillows.", "A cool cloth on the forehead can help.",
           "Try to keep the room quiet and calm.", "Gentle repositioning every so often can help {obj} stay comfortable."]
SUPPORT = ["Keep offering sips of water or ice chips.", "Keep up the mouth care.", "Keep encouraging small meals if {sub} wants them."]
RETURN = ["Call us back right away if anything changes.", "Please call us back if {sub} has any new symptoms.",
          "Call us right away if {pos} symptoms get worse or if you have any concerns."]
FOLLOWUP = ["Someone from the team will follow up with you.", "The team will review this and get back to you."]
CALLBACK_INV = ["Please call us if you have any questions.", "Call us anytime if you need anything else.", "And if you have any other questions, don't hesitate to call."]
EMERG = ["If {sub} seems to be in immediate danger, call emergency services right away.",
         "If anything feels unsafe, please call emergency services right away."]
EMERG_SUICIDE = ["If you feel anyone might act on those thoughts, call emergency services right away, or call the crisis line.",
                 "Please stay with {obj} and call emergency services right away if anything feels unsafe."]

PLANNED = {
    "refill_request": ["I will put in a refill request for {x}.", "I'll try to submit a refill request for {x}.", "Let me put in a refill request for {x}."],
    "team_message": ["I'll send a message to the team regarding {x}.", "I'm going to let the team know of {x}.", "Let me send a message to the team regarding {x}."],
    "nurse_visit": ["I'll arrange a nurse visit as soon as we can.", "I will set up a nurse visit as soon as possible."],
    "callback": ["I'll have the on-call nurse call you back.", "I will call you back to check in on {obj}.", "I'm going to have the on-call nurse give you a call."],
    "physician_notification": ["I'll let the doctor know what's going on.", "I will notify the doctor of what you've told me.", "I'm going to let the physician know."],
    "documentation": ["I'll document everything in my notes.", "I will put all of this in my notes.", "Let me document this in the chart."],
    "appointment_scheduling": ["I'll have the team call you to schedule an appointment.", "I will have the team reach out to schedule an appointment."],
    "medication_order": ["I'll ask the doctor to order {x}."],
    "referral": ["I will arrange for {obj} to be evaluated in person."],
}
COMPLETED = {
    "refill_request": ["I've put in the refill request for {x}.", "I submitted the refill request for {x}."],
    "team_message": ["I sent a message to the team regarding {x}.", "I've sent a message to the team regarding {x}."],
    "nurse_visit": ["I placed the request for a nurse visit.", "I've put in the request for a nurse to visit."],
    "callback": ["I've called the on-call nurse for you.", "I called the on-call nurse and gave them the details."],
    "physician_notification": ["I've called the doctor to report this.", "I called the physician and gave them the details."],
    "documentation": ["I entered all of this in my notes.", "I entered everything in the chart."],
    "appointment_scheduling": ["I went ahead and scheduled the appointment.", "I submitted the appointment request."],
}
ADVISED = {
    "escalation_911_ed": ["I would recommend that you call nine one one and go to the emergency department.",
                          "I'd advise calling nine one one or going to the emergency department right away."],
    "referral": ["I'd advise getting {obj} evaluated in person."],
}
TEAM_X = ["what you've told me", "everything you've described", "the details you gave me"]

# Non-clinical chatter for the "long call" profile. Real calls contain long stretches of waiting, small talk and
# background noise (real_02: cat small talk; real_04: laughter) with no clinical content. INVARIANT (tested): no drug name,
# no digit, no risk-lexicon phrase, nothing the nurse commits to.
CHATTER_CALLER = [
    "Hold on, let me find the bottle. Okay, I'm looking for it now.", "Sorry, can you hear me okay?",
    "I'm just walking into the other room so I don't wake everybody.", "Let me put you on speaker, one second.",
    "Sorry, my daughter is asking me something. Go ahead, I'm listening.", "Bear with me, I'm trying to find my glasses.",
    "I'm sorry, I'm just a little flustered today.", "Thank you for your patience with me.",
    "The kettle is going, sorry. Let me turn that off.", "Okay, I'm back. What were you saying?",
    "Our cat keeps jumping on the bed, sorry, give me a second.", "It's been such a long few days, you know?",
    "I didn't sleep well, so I'm a little foggy myself.", "Sorry, there's a lot of noise here, can you hear me?",
    "Let me sit down, my back is killing me.", "Oh, sorry, that was the television. Let me turn it down.",
    "I'm so glad somebody picked up. I hate calling at this hour.", "Hold on, the neighbor is knocking.",
    "Sorry, I lost my train of thought.", "Let me get a pen so I can write that down.", "Okay, I'm ready. Go ahead.",
    "You're very kind to be so patient.", "Sorry, I'm still here, I'm just moving around.", "My phone is acting up again, sorry.",
    "Can you hold on? Someone just came in.", "I'm trying to be organized but it's hard right now.",
    "Okay, okay. Thank you for your patience.", "I have a whole bag of papers here, give me a moment.",
    "Sorry, the dog needs to go out, one second.", "Everyone here is doing their best, it's just a lot.",
    "Okay.", "Uh huh.", "Yes.", "Right.", "Mhm.", "Okay, okay.", "Yeah.", "Hmm.", "Sure.", "Okay, thank you.", "Alright.", "Yes, I'm here.",
]
CHATTER_NURSE = ["Take your time, I'm right here.", "I'm still here, no rush.", "Sure, no problem.", "That's perfectly fine.",
                 "Not a problem at all.", "I can hear you fine.", "Go ahead whenever you're ready.", "I understand.", "I'm here."]
BACKCHANNEL = ["Okay.", "Uh huh.", "Mhm.", "Yes.", "Right.", "Okay, okay.", "Yeah."]

NA_SCRIPTS = {
    "wrong_number": [[("Caller", "Hi, is this the pharmacy?"), ("Nurse", "No, I'm sorry, this is {agency}. I think you may have the wrong number."),
                      ("Caller", "Oh, I'm so sorry about that. Have a good day."), ("Nurse", "You too. Goodbye.")],
                     [("Caller", "Hello, am I speaking to the dentist's office?"), ("Nurse", "No, this is {agency}. You might have dialed the wrong number."),
                      ("Caller", "Oh no. My apologies."), ("Nurse", "That's quite all right. Goodbye.")]],
    "hang_up": [[("Caller", "Hello?"), ("Nurse", "Hello? Can you hear me? This is {nurse} with {agency}."), ("Caller", "Hello?"),
                 ("Nurse", "I'm having trouble hearing you. If you can hear me, please call back. Goodbye.")],
                [("Caller", "Um."), ("Nurse", "Hello? This is {agency}. Is anyone there?"),
                 ("Nurse", "I can't hear anything on the line. Please call back if you need us. Goodbye.")]],
    "billing_admin_only": [[("Caller", "Hi, I'm calling about a bill for {pn}. I got a statement in the mail and I have a question about it."),
                            ("Nurse", "I'm sorry, I'm the triage nurse and I can't help with billing. I can transfer you to the billing department."),
                            ("Caller", "That would be great, thank you."), ("Nurse", "Please hold while I transfer you.")],
                           [("Caller", "Hello, I need to talk to someone in billing about the account for {pn}."),
                            ("Nurse", "This is the clinical line, so I can't help with that, but I can send you over to billing."),
                            ("Caller", "Okay, thank you."), ("Nurse", "One moment please.")]],
    "test_call": [[("Caller", "Hi, this is just a test call. Testing, testing, can you hear me okay?"),
                   ("Nurse", "Yes, I can hear you fine. Is there anything clinical I can help with?"),
                   ("Caller", "No, I'm just testing the line. Thank you."), ("Nurse", "Okay, no problem. Goodbye.")],
                  [("Caller", "This is a test, please ignore this call."), ("Nurse", "Okay, I can hear you. Is there anything you need?"),
                   ("Caller", "No, nothing, just checking the system."), ("Nurse", "All right. Goodbye.")]],
}


def join_list(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else (", ".join(xs[:-1]) + " and " + xs[-1])


class Voicer:
    def __init__(self, rec: FactRecord, rng: random.Random, stress: tuple[int, int] | None = None):
        self.rec, self.r = rec, rng
        self.long_k = stress or (18, 42)
        p = rec.persona
        self.ps, self.cs = p.get("patient_sex", "F"), p.get("caller_sex", "F")
        self.rel = rec.identity.relationship.value
        self.self_call = self.rel == "patient (self)"
        pr = PRON[self.ps]
        if self.self_call:
            self.w = dict(sub="I", Sub="I", obj="me", pos="my", Be="I'm", has="I have", Hv="I've", takes="take", gave="I took")
        else:
            self.w = dict(sub=pr["sub"], Sub=pr["sub"].capitalize(), obj=pr["obj"], pos=pr["pos"], Be=pr["sub"] + "'s",
                          has=pr["sub"] + " has", Hv=pr["sub"] + "'s", takes="takes", gave="I gave")
        self.nurse, self.agency = p.get("nurse", "Ada"), rec.agency
        self.verb, self.dist = p.get("verbosity", "normal"), p.get("distraction", "none")
        self.unclear = set(p.get("uncertain_facts", []))
        self.long = (not rec.not_applicable) and (stress is not None or int(hashlib.md5(rec.record_id.encode()).hexdigest(), 16) % 100 < 40)
        self.t: list[Turn] = []
        self.surf: dict[str, str] = {}
        self.med = {m.id: m for m in rec.medications}

    # ------------------------------------------------------------------ primitives
    def say(self, sp: str, text: str, *tags: str) -> None:
        text = re.sub(r"^([a-z])", lambda m: m.group(1).upper(), text.strip())        # sentence-initial capital
        self.t.append(Turn(len(self.t) + 1, sp, text, set(tags)))

    def n(self, text: str, *tags: str) -> None: self.say("Nurse", text, *tags)
    def c(self, text: str, *tags: str) -> None: self.say("Caller", text, *tags)
    def ack(self) -> str: return self.r.choice(ACKS)

    def bc(self) -> None:
        """Caller murmurs an acknowledgement after a nurse statement (real calls: 33% of caller turns are <= 3 words)."""
        if self.r.random() < .6:
            self.c(self.ch(BACKCHANNEL))
    def ch(self, xs): return self.r.choice(xs)
    def fmt(self, s: str, **kw) -> str: return s.format(**{**self.w, **kw})

    def nm(self, m: Medication) -> str:
        """Consistent drug surface for the whole call: generic or (25%) a brand/alias."""
        if m.id not in self.surf:
            if m.name is None:
                self.surf[m.id] = m.name_as_heard or "that medicine"
            else:
                al = FORM[m.name]["aliases"] if m.name in FORM else []
                self.surf[m.id] = self.r.choice(al) if al and self.r.random() < .25 else m.name
        return self.surf[m.id]

    def dose(self, m: Medication) -> str: return SP.dose_str(m.dose, m.unit) or ""
    def route(self, m: Medication) -> str: return self.r.choice(SP.ROUTE_SPOKEN[m.route]) if m.route else ""
    def freq(self, m: Medication) -> str: return self.r.choice(SP.FREQ_SPOKEN[m.frequency]) if m.frequency else ""

    def med_core(self, m: Medication) -> str:
        parts = [f"the {self.nm(m)}"]
        d = " ".join(x for x in (self.dose(m), self.route(m)) if x)
        if d: parts.append(d)
        if m.frequency: parts.append(self.freq(m))
        return ", ".join(parts)

    # ------------------------------------------------------------------ call skeleton
    def greeting(self):
        self.n(self.ch(["Thank you for calling {agency}. This is {nurse}, the triage nurse. How can I help you?",
                        "{agency}, this is {nurse}. How may I help you today?",
                        "Thank you for calling {agency}. This is {nurse}. What can I do for you?"]).format(agency=self.agency, nurse=self.nurse))

    def dob_text(self, iso: str) -> str:
        y, m, d = (int(x) for x in iso.split("-"))
        return f"{MONTHS[m - 1]} {d}, {y}" if self.r.random() < .6 else f"{m}/{d}/{y}"

    def phone_text(self, ph: str) -> str:
        return f"{ph[:3]}-{ph[3:6]}-{ph[6:]}" if self.r.random() < .5 else ph

    def rel_phrase(self) -> str:
        rel = self.rel
        if self.self_call:
            return "I'm calling for myself"
        pos = PRON[self.ps]["pos"]
        if rel == "facility nurse":
            return f"I'm the nurse at the facility where {PRON[self.ps]['sub']} lives"
        word = {"spouse": "husband" if self.cs == "M" else "wife", "mother": "mom", "father": "dad"}.get(rel, rel)
        return f"I'm {pos} {word}"

    def identity(self):
        I = self.rec.identity
        pn, cn, ph, dob = I.patient_name.value, I.caller_name.value, I.callback_phone.value, I.patient_dob.value
        flow = self.r.choice(["A", "B", "C"])
        if self.self_call:
            self.c(f"This is {pn}. I'm calling for myself.", "ID.patient_name", "ID.caller_name", "ID.relationship")
            self.n(f"{self.ack()} Thank you. And can I have your date of birth?")
            self.c(f"It's {self.dob_text(dob)}.", "ID.patient_dob")
        elif flow == "C":
            self.c(f"Hi, this is {cn}. {self.rel_phrase()}, and I'm calling for {pn}.", "ID.caller_name", "ID.relationship", "ID.patient_name")
            self.n(f"{self.ack()} Thank you. And what is {self.w['pos']} date of birth?")
            self.c(f"{self.dob_text(dob)}.", "ID.patient_dob")
        elif flow == "B":
            self.n("Can I have the patient's date of birth, please?")
            self.c(f"{self.dob_text(dob)}.", "ID.patient_dob")
            self.n(f"{self.ack()} Thank you. And the first and last name?")
            self.c(f"{pn}.", "ID.patient_name")
            self.n(f"{self.ack()} And who am I speaking to?")
            self.c(f"This is {cn}. {self.rel_phrase()}.", "ID.caller_name", "ID.relationship")
        else:
            self.n("Can I get the patient's first and last name, please?")
            self.c(f"It's {pn}.", "ID.patient_name")
            self.n(f"{self.ack()} Thank you. And the date of birth?")
            self.c(f"{self.dob_text(dob)}.", "ID.patient_dob")
            self.n(f"{self.ack()} And who am I speaking with?")
            self.c(f"This is {cn}. {self.rel_phrase()}.", "ID.caller_name", "ID.relationship")
        self.n(f"{self.ack()} And what's a good callback number in case we get disconnected?")
        self.c(f"{self.phone_text(ph)}.", "ID.callback_phone")
        if self.verb != "terse":
            first = I.caller_name.value.split()[0]
            self.n(f"Thank you, {first}. I have {I.patient_name.value.split()[0]}, born {self.dob_text(dob)}, and your number. Is that right?",
                   "ID.patient_name", "ID.patient_dob", "ID.caller_name", "ID.callback_phone")
            self.c(self.ch(["Yes, that's right.", "Yes, correct.", "That's right."]))

    # ------------------------------------------------------------------ symptoms
    def sym_phrase(self, s: Symptom) -> str:
        loc = ""
        if s.location:
            loc = " all over" if s.location == ["everywhere"] else f" in {self.w['pos']} " + join_list(s.location)
        base = self.fmt(self.ch(SYM[s.name]), loc=loc)
        o = s.onset_duration
        if s.name == "fall":
            return base + (" " + FALL_WHEN[o] if o else "")
        if o is None:
            return base
        if o.startswith(("since ", "for ", "on and off")):
            return f"{base} {o}"
        if o == "just started an hour ago":
            return f"{base}, and it just started an hour ago"
        if o == "despite last dose":
            return f"{base}, even despite the last dose"
        return base

    def symptom_turns(self, s: Symptom, first_sentence: str | None = None, extra_tags: tuple = ()):
        tags = (s.id, *extra_tags)
        phrase = self.sym_phrase(s)                       # starts with a pronoun form: "he's ...", "I have ...", "she fell ..."
        cap = phrase[0].upper() + phrase[1:]
        if s.id in self.unclear or s.certainty == "unclear":
            sev = SP.sev_spoken(s.severity)
            tail = f" Maybe {'a ' + sev if 'out of ten' in sev else sev}." if sev else ""
            self.c(f"{self.ch(['I think', 'Maybe', 'I believe'])} {phrase}.{tail} I'm not really sure.", *tags)
        elif first_sentence:
            self.c(first_sentence.format(sym=phrase, Sym=cap), *tags)
        else:
            self.c(cap + ".", *tags)
        if s.severity and not (s.id in self.unclear or s.certainty == "unclear"):   # hedged symptoms voice severity inside the hedged turn
            sev = SP.sev_spoken(s.severity)
            if "out of ten" in sev:
                self.n(f"{self.ack()} On a scale of one to ten, how bad is the {s.name}?")
                self.c(f"It's a {sev}.", *tags)
            else:
                self.n(f"{self.ack()} Would you say it's mild, moderate or severe?")
                self.c(f"I'd say it's {sev}.", *tags)

    # ------------------------------------------------------------------ medications
    def med_turns(self, m: Medication, lead_q: bool = True, first: bool = True):
        tags = (m.id,)
        core = self.med_core(m)
        st = m.status
        if m.certainty == "unclear" or m.id in self.unclear:
            if lead_q:
                self.n(f"{self.ack()} " + ("And what medicine is {sub} taking for that?".format(**self.w) if first else "And what is the other medicine?"))
            self.c(f"I think it's {core}, but I'm not sure about the dose. I'd have to check the bottle.", *tags)
        elif st in ("current", "administered"):
            if lead_q:
                self.n(f"{self.ack()} " + ("And what medicine is {sub} taking for that?".format(**self.w) if first else "And what is the other medicine?"))
            if st == "administered":
                last = f" {SP.LAST_DOSE_SPOKEN[m.last_dose]}" if m.last_dose else ""
                d = " ".join(x for x in (self.dose(m), self.route(m)) if x)
                self.c(f"{self.w['gave']} the {self.nm(m)}, {d}{last}. It's ordered {self.freq(m)}.", *tags)
            else:
                self.c(self.ch(["{Be} on {core}.", "{Sub} {takes} {core}."]).format(core=core, **self.w), *tags)
        elif st == "ordered":
            self.n(f"{self.ack()} Let me look at the chart. It shows {core} ordered by the doctor.", *tags)
            self.c(self.ch(["Okay.", "Yes, that's right.", "Right."]))
        elif st == "advised":
            self.n(f"{self.ack()} You can go ahead and give {core}.", *tags)
            self.c(self.ch(["Okay, I will.", "Okay, thank you.", "Okay."]))
        if self.verb != "terse" and st in ("current", "administered") and m.certainty == "stated" and self.r.random() < .5:
            self.n(f"Just to make sure I have that right, that's {core}, correct?", *tags)
            self.c(self.ch(["Yes, that's right.", "Yes, correct."]))

    # ------------------------------------------------------------------ supplies / context
    def supply_turns(self, u, opened: bool = False):
        tags = (u.id,)
        med = next((m for m in self.rec.medications if m.name == u.item), None)
        extra = (med.id,) if med else ()
        item = self.nm(med) if med else u.item
        if u.request == "equipment":
            self.c((self.ch(["Yes, I need more {i}.", "That's right, more {i}."]) if opened else self.ch(["I also need more {i}.", "We need more {i} too."])).format(i=item), *tags)
            self.n(f"{self.ack()} Do you need that delivered?")
            self.c("Yes, delivered, please.", *tags)
            return
        q = SP.qty_spoken(u.quantity_remaining)
        k = int(u.quantity_remaining.split()[0])
        if k == 0:
            self.c(f"We ran out of the {item}. I have {q} left.", *tags, *extra)
        elif k <= 2:
            self.c(f"I'm almost out of the {item}. I only have {q} left.", *tags, *extra)
        else:
            self.c(f"I have {q} of the {item} left.", *tags, *extra)
        self.n(f"{self.ack()} Would you like that refilled or delivered?")
        self.c("Delivered, please." if u.request == "delivery" else "A refill, please.", *tags)

    def context_turn(self, x, rid: tuple):
        t, tags = x.text, (x.id, *rid)
        meds = self.rec.medications
        nm = self.nm(meds[0]) if meds else "the medicine"
        mt = (meds[0].id,) if meds else ()
        if t == "medication problem: missed doses": self.c(f"We missed doses of the {nm} yesterday and I feel terrible.", *tags, *mt)
        elif t == "medication problem: ran out": self.c(f"We ran out of the {nm} last night.", *tags, *mt)
        elif t == "medication problem: double dose": self.c(f"I gave a double dose of the {nm} by accident.", *tags, *mt)
        elif t == "medication problem: wrong dose": self.c(f"I gave the wrong dose of the {nm} and I'm worried.", *tags, *mt)
        elif t == "caller asks for a nurse to come out now": self.c("I need someone to come out now. Please send a nurse.", *tags)
        elif t == "caller asks to be sent to the hospital": self.c("I want {obj} sent to the hospital right now.".format(**self.w), *tags)
        elif t == "caller asks to speak to the doctor today": self.c("I need to talk to the doctor today.", *tags)
        else: self.c(f"{t}.", *tags)

    # ------------------------------------------------------------------ nurse side
    def action_turn(self, a):
        x = self.r.choice(TEAM_X)
        if a.type == "refill_request":
            ms = [m for m in self.rec.medications if any(u.item == m.name for u in self.rec.supplies)] or self.rec.medications[:1]
            x = join_list([f"the {self.nm(m)}" for m in ms]) if ms else "the medicine"
            tags = (a.id, *[m.id for m in ms])
        else:
            tags = (a.id,)
        bank = PLANNED if a.status == "planned" else COMPLETED if a.status == "completed" else ADVISED
        tpl = self.r.choice(bank.get(a.type) or PLANNED[a.type])
        self.n(f"{self.ack()} " + tpl.format(x=x, **{k: self.w[k] for k in ("obj", "sub", "pos")}), *tags)
        self.bc()

    def education_turn(self, e):
        cat, meds = e.type, self.rec.medications
        subj = self.rec.subtype
        m = next((m for m in meds if m.status in ("advised", "ordered")), meds[0] if meds else None)
        w = {k: self.w[k] for k in ("obj", "sub", "pos")}
        tags = (e.id,)
        if cat == "medication_instruction" and m is not None:
            txt, tags = f"You can go ahead and give {self.med_core(m)}.", (e.id, m.id)
        elif cat == "medication_timing" and m is not None:
            txt, tags = f"Try to keep the {self.nm(m)} on schedule, {self.freq(m)}.", (e.id, m.id)
        elif cat == "medication_safety" and m is not None:
            txt, tags = f"Please don't change the {self.nm(m)} or stop it without checking with us first.", (e.id, m.id)
        elif cat == "administration_method":
            txt = "Give it with a full glass of water and keep " + w["obj"] + " sitting upright for a while after."
        elif cat == "comfort_measure": txt = self.ch(COMFORT).format(**w)
        elif cat == "supportive_care": txt = self.ch(SUPPORT).format(**w)
        elif cat == "return_precaution": txt = self.ch(RETURN).format(**w)
        elif cat == "follow_up_expectation": txt = self.ch(FOLLOWUP)
        elif cat == "callback_invitation": txt = self.ch(CALLBACK_INV)
        elif cat == "emergency_guidance": txt = self.ch(EMERG_SUICIDE if subj == "suicidal_statement" else EMERG).format(**w)
        else: txt = self.ch(RETURN).format(**w)                  # medication_* with no med in record
        self.n(f"{self.ack()} {txt}", *tags)
        self.bc()

    # ------------------------------------------------------------------ distraction
    def asides(self):
        k = {"none": 0, "interruptions": 1, "heavy": 3}[self.dist]
        pool = ASIDES_CALLER + (ASIDES_HEAVY if self.dist == "heavy" else [])
        spots = sorted(self.r.sample(range(4, max(6, len(self.t))), min(k, max(1, len(self.t) - 5)))) if k else []
        for off, s in enumerate(spots):
            at = s + 2 * off
            self.t.insert(at, Turn(0, "Caller", self.ch(pool), set()))
            self.t.insert(at + 1, Turn(0, "Nurse", self.ch(["That's okay, take your time.", "No problem.", "That's all right."]), set()))
        if self.long:                                  # long-call profile: non-clinical chatter blocks
            k = self.r.randint(*self.long_k)
            lines = self.r.sample(CHATTER_CALLER, min(k, len(CHATTER_CALLER))) + [self.ch(CHATTER_CALLER) for _ in range(max(0, k - len(CHATTER_CALLER)))]
            for line in lines:
                at = self.r.randint(5, max(6, len(self.t) - 3))
                self.t.insert(at, Turn(0, "Caller", line, set()))
                self.t.insert(at + 1, Turn(0, "Nurse", self.ch(CHATTER_NURSE), set()))
        if self.verb == "chatty":
            for _ in range(self.r.randint(1, 2)):
                at = self.r.randint(6, max(7, len(self.t) - 4))
                self.t.insert(at, Turn(0, "Caller", self.ch(CHATTER), set()))
                self.t.insert(at + 1, Turn(0, "Nurse", self.ch(NURSE_EMPATHY), set()))

    # ------------------------------------------------------------------ whole call
    def reason_turn(self):
        r, cat, sub = self.rec, self.rec.category, self.rec.subtype
        syms, meds = r.symptoms, r.medications
        used_sym: set[str] = set(); used_med: set[str] = set()
        self.n(f"{self.ack()} And how can I help you today?")
        if cat == "high_risk":
            return self.high_risk_reason()
        if cat in ("medication", "asr_error"):
            m = meds[0]
            pre = "I'm sorry, the line isn't great. " if cat == "asr_error" else ""
            if cat == "asr_error":
                self.n("I'm having a little trouble hearing you, but go ahead.")
            self.c(f"{pre}I have a question on the {self.nm(m)}. I want to make sure {self.w['sub']} {'am' if self.self_call else 'is'} getting it the right way.", m.id)
            used_med.add(m.id)
        elif cat == "supply":
            u = r.supplies[0]
            med = next((m for m in meds if m.name == u.item), None)
            item = self.nm(med) if med else u.item
            self.c(f"I'm calling because I need more of the {item}." if u.request != "equipment" else f"I'm calling because I need more {item}.",
                   u.id, *((med.id,) if med else ()))
            used_med |= {med.id} if med else set()
            self._opened_supply = u.id
        else:                                                      # routine / ambiguous
            s = syms[0]
            self.symptom_turns(s, first_sentence="I'm calling to check in. {Sym}, and I wanted to see what to do.")
            used_sym.add(s.id)
        self._used_sym, self._used_med = used_sym, used_med

    def high_risk_reason(self):
        r, sub = self.rec, self.rec.subtype
        syms, meds = r.symptoms, r.medications
        rid = tuple(f.id for f in r.risk_flags if f.category == sub)
        self._used_sym, self._used_med = set(), set()
        if sub == "uncontrolled_symptom":
            s, m = syms[0], meds[0]
            sev = SP.sev_spoken(s.severity); locs = join_list(s.location)
            last = f" The last dose was {SP.LAST_DOSE_SPOKEN[m.last_dose]}." if m.last_dose else ""
            self.c(f"{self.w['Sub']} {'am' if self.self_call else 'is'} in a lot of pain in {self.w['pos']} {locs}, and it's {sev}. The {self.nm(m)} is not working and nothing helps.{last}",
                   s.id, m.id, *rid)
            self._used_sym.add(s.id)
            self.n(f"{self.ack()} I'm sorry {self.w['sub']} {'am' if self.self_call else 'is'} hurting. Let me ask a few questions.")
        elif sub == "medication_concern":
            x = r.context[0]
            self.context_turn(x, rid); self._used_med.add(meds[0].id)
            self._ctx_done = True
        elif sub == "suicidal_statement":
            who = "patient" if "patient" in syms[0].name else "caller"
            if self.self_call: who = "caller"
            txt = self.ch(SUICIDAL[who]).format(**{"Sub": self.w["Sub"], "sub": self.w["sub"]})
            self.c(txt, syms[0].id, *rid); self._used_sym.add(syms[0].id)
            self.n(f"{self.ack()} I'm so sorry you're going through this. Thank you for telling me. Let me ask a few questions.")
        elif sub == "breathing_concern":
            s = syms[0]
            self.symptom_turns(s, first_sentence="{Sym}, and I'm scared.", extra_tags=rid); self._used_sym.add(s.id)
        else:                                                       # escalation_request
            x = r.context[0]
            self.context_turn(x, rid); self._ctx_done = True

    def build(self) -> list[Turn]:
        rec = self.rec
        self.greeting()
        self.identity()
        self._ctx_done = False; self._opened_supply = None
        self.reason_turn()
        used_s, used_m = self._used_sym, self._used_med
        # remaining symptoms (first symptom was voiced in the reason for routine/ambiguous/breathing)
        for i, s in enumerate(rec.symptoms):
            if s.id in used_s:
                continue
            self.n(f"{self.ack()} And is {self.w['sub']} having any other symptoms?" if i else f"{self.ack()} What symptoms is {self.w['sub']} having?")
            self.symptom_turns(s)
        # pertinent negatives
        negs = rec.pertinent_negatives
        for ng in negs:
            ph = NEG_PHRASE[ng.name]
            self.n(f"{self.ack()} Any {ph}?")
            self.c(f"No, no {ph}.", ng.id)
        # context for non-high-risk (none sampled) / high risk follow-ups
        for x in rec.context:
            if not self._ctx_done:
                self.context_turn(x, tuple(f.id for f in rec.risk_flags if f.category == rec.subtype)); self._ctx_done = True
        # medications (every gold value is voiced here, even if the name came up in the opening)
        for i, m in enumerate(rec.medications):
            self.med_turns(m, lead_q=True, first=(i == 0))
        # supplies
        for u in rec.supplies:
            if u.request != "equipment":
                self.n(f"{self.ack()} How much do you have left?")
            elif u.id != self._opened_supply:
                self.n(f"{self.ack()} Do you need any supplies?")
            self.supply_turns(u, opened=(u.id == self._opened_supply))
        # actions / education
        for a in rec.actions: self.action_turn(a)
        for e in rec.education: self.education_turn(e)
        self.n("Is there anything else I can help you with?")
        self.c(self.ch(["No, that's all. Thank you.", "No, that's everything. Thank you so much.", "No, I think that's it."]))
        self.n(self.ch(["You're welcome. Take care.", "You're welcome. Goodbye.", "Take care now. Goodbye."]))
        self.asides()
        for i, t in enumerate(self.t, 1): t.id = i
        return self.t


def voice_na(rec: FactRecord, rng: random.Random) -> list[Turn]:
    v = Voicer(rec, rng)
    v.greeting()
    script = rng.choice(NA_SCRIPTS[rec.na_subtype])
    pn = rec.identity.patient_name.value or ""
    for sp, text in script:
        tags = {"ID.patient_name"} if "{pn}" in text else set()
        v.say(sp, text.format(agency=rec.agency, nurse=v.nurse, pn=pn), *tags)
    for i, t in enumerate(v.t, 1): t.id = i
    return v.t


def voice(rec: FactRecord, rng: random.Random, stress: tuple[int, int] | None = None) -> list[Turn]:
    """stress=(kmin,kmax): force the long-call profile with that many chatter exchanges (real-length latency/long-context slice)."""
    return voice_na(rec, rng) if rec.not_applicable else Voicer(rec, rng, stress).build()
