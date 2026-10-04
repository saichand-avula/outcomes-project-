"""Deterministic risk-flag rules and the Not-Applicable gate (architecture 5.2 steps 2 and 5).

Rules scan transcript turns directly (no model output). Nurse screening questions never fire; negated phrases are
suppressed ("no trouble breathing"), except suicidal phrases that carry their own wording. Developed on training data.
"""
from __future__ import annotations

import re

from .lexicons import FORMULARY, HEDGE, I, NEGATION, rx

CATEGORIES = ["uncontrolled_symptom", "medication_concern", "suicidal_statement", "breathing_concern", "escalation_request", "other_urgent"]
NUM = r"(?:7|8|9|10|seven|eight|nine|ten)"
NEG_BEFORE = re.compile(r"\b(?:no|not|never|without|denies|denied|nothing|hasn'?t|haven'?t|isn'?t|aren'?t|wasn'?t|doesn'?t|don'?t|didn'?t|can'?t say|none|nor|neither|zero)\b", I)
CONDITIONAL = re.compile(r"\b(?:if|when|whenever|should|in case|any time|anytime|once|unless|say|call us for|call us if)\b", I)
MED_CONTEXT = re.compile(r"medic|\bmeds?\b|\bpills?\b|tablet|capsule|\bdoses?\b|insulin|patch|injection|syringe|inhaler|refill|prescri|liquid|drops|" + "|".join(re.escape(d) for d in FORMULARY if len(d) > 3), I)
PAIN_ASK = re.compile(r"(?=.*(?:pain|hurt|ache|sore))(?=.*(?:scale|number|zero to ten|0 to 10|how bad|how much|rate|rating|how strong|how severe|how would you))", I | re.S)
HISTORICAL = re.compile(r"last time|years? ago|months? ago|weeks? ago|used to|history of|in the past|back in|when (?:i|he|she) was|once before|before this|previously|last year", I)
UNIT_AFTER = r"(?!\s*(?:years|days|day|weeks|hours|hour|minutes|pounds|units|mg|ml|times|o'?clock|am|pm|a\.m|p\.m|milligram|milliliter|tablet|pill))"
INSIDE_NEGATION = re.compile(r"\b(?:don'?t|do not|doesn'?t|wouldn'?t|would not|won'?t)\b", I)

# (name, pattern, speakers, suppress_if_negated, context) ; context in {None, "med"}
RULES: dict[str, list[tuple[str, re.Pattern, tuple[str, ...], bool, str | None]]] = {
    "suicidal_statement": [
        ("self_negative_wording", re.compile(r"(?:don'?t|do not|doesn'?t) want to (?:live|be here|wake up|go on|be alive|do this anymore)|(?:wish|hope|want|wanting|rather|if only)[^.?!]{0,25}(?:wouldn'?t|would not|not|never) wake up|go to sleep and (?:not|never) wake up|better off (?:dead|gone|without)|want(?:s|ed)? to die|(?:no|not any) (?:reason|point) (?:to|in) (?:live|living|go on)|\bend(?:ing)? (?:it all|my life|his life|her life|everything)|thinking (?:about|of) (?:ending|suicide|killing)|suicid|kill(?:ing)? (?:myself|himself|herself)(?![^.?!]{0,25}\b(?:if|when|every time|one more time)\b)|take (?:all|them all|all of them)(?: of)? (?:the |my |his |her )?(?:pills|them|medicines?|meds)|take them all|take all (?:of )?(?:them|these|those)|i'?d be better off|done with (?:life|everything|it all)|wish (?:i|he|she) (?:was|were) dead|not be here anymore|can'?t go on", I), ("Caller",), False, None),
        ("self_harm_wording", re.compile(r"hurt (?:myself|himself|herself)|harm (?:myself|himself|herself)|\bend it\b|\bending it\b", I), ("Caller",), True, None),
    ],
    "breathing_concern": [
        ("cannot_breathe", re.compile(r"can'?t (?:breathe|catch (?:his|her|my|their) breath)|cannot breathe|\bgasping\b|struggling to breathe|working (?:so |really )?hard to breathe|not breathing|stopped breathing|turning blue|(?:blue|bluish|gray|grey) (?:lips|around)|lips (?:are |look |turned )?(?:blue|gray|grey)|throat (?:is |'s )?(?:tight|closing)|\bchoking\b|chest (?:pain|tight)|tightness in (?:his|her|my|the) chest|wheezing", I), ("Caller",), True, None),
        ("hard_to_breathe", re.compile(r"hard (?:time )?(?:to )?breath|trouble breathing|difficulty breathing|(?:short(?:ness)?|out) of breath|breathless|labored breathing|breathing (?:fast|hard|so fast|is fast|really fast|heavy|heavily)|fast breathing", I), ("Caller",), True, None),
    ],
    "escalation_request": [
        ("caller_urgent_help", re.compile(r"(?:send|get) (?:someone|a nurse|the nurse|somebody|an ambulance)(?: out| over| here)?[^.?!]{0,20}?(?:now|right now|right away|immediately|as soon as)|(?:need|want) (?:someone|a nurse|the nurse|somebody)(?: to come| out)?[^.?!]{0,15}?(?:now|right now|right away|immediately)|(?:need|want) (?:you|someone|a nurse|somebody|the nurse) to come(?: out| over)?[^.?!]{0,10}?(?:now|right now|right away|immediately|today|tonight)|(?:need|want) (?:an )?ambulance|\bcall (?:911|nine one one)\b|\bcan (?:someone|somebody|a nurse|the nurse|anyone) (?:please )?(?:come|get here)|(?:want|need) (?:him|her|them) in the (?:emergency (?:department|room)|er)", I), ("Caller",), True, None),
        ("nurse_911_ed", re.compile(r"(?:call|dial) (?:911|nine one one)(?: right)? (?:now|away|immediately)|hang up and call (?:911|nine one one)|(?:i'?m|i am|we'?re|we are) (?:calling|sending|dispatching) (?:911|nine one one|an ambulance|ems|paramedics)|(?:go|take (?:him|her|them)|get (?:him|her|them)|head) to the (?:er|emergency (?:room|department)|hospital)[^.?!]{0,12}?(?:now|right away|immediately)|(?:911|nine one one)[^.?!]{0,10}?(?:right )?(?:now|away)|call (?:an )?ambulance", I), ("Nurse",), True, None),
        ("nurse_urgent_visit", re.compile(r"(?:i'?m|i am) sending (?:a nurse|someone|the nurse|our nurse)[^.?!]{0,25}?(?:now|right now|right away|immediately|within the hour|within an hour)|nurse will be there (?:within|in) (?:the hour|an hour|thirty|30|twenty|20|forty|45)|(?:send|sending) (?:a nurse|someone) (?:out )?(?:now|right now|right away|immediately)", I), ("Nurse",), False, None),
    ],
    "medication_concern": [
        ("ran_out", re.compile(r"(?:ran|run|running|runs) out(?: of)?|\bout of (?:his|her|my|the|their|our)\b|no (?:more|doses) left|last (?:dose|pill|tablet)", I), ("Caller",), True, "med"),
        ("wrong_or_extra", re.compile(r"too much|wrong (?:pill|medicine|medication|insulin|dose|one|bottle|strength|syringe|drug)|double(?:d)? (?:dose|up|the)|extra (?:dose|pill|tablet|one|time)|overdos|took (?:two|an extra|another|one more|a second|the wrong|too)|took (?:a |an |one |the )?\w+ and (?:then )?(?:i )?took (?:another|a second|one more)|gave (?:him|her|them)[^.?!]{0,25}(?:twice|an extra|another|two|the wrong|too)|(?:twice|two times)[^.?!]{0,20}(?:already|in a row|by mistake)|by mistake|mix(?:ed)? up|messed up|took the wrong|gave the wrong|two (?:pills|tablets|doses) (?:instead|by)|took (?:it|them) (?:twice|again)|took (?:it|them) two times", I), ("Caller",), True, "med"),
        ("stopped_missed", re.compile(r"stopp(?:ed|ing) (?:taking|giving|the|his|her|my|it|them)|(?:forgot|missed|skipped|didn'?t get) (?:a |the |his |her |to give |any )?(?:dose|doses|pill|pills|medic\w*|his|her|them|it)|hasn'?t had (?:his|her) (?:\w+ )?(?:medic\w*|pill|dose|morphine|insulin)|can'?t (?:swallow|keep down)", I), ("Caller",), True, "med"),
    ],
    "uncontrolled_symptom": [
        ("pain_score_high", re.compile(rf"\b{NUM} out of (?:10|ten)\b|\b(?:7|8|9|10)\s*/\s*10\b|(?:pain|hurts?|hurting)[^.?!]{{0,25}}\b{NUM}\b{UNIT_AFTER}|\b{NUM}\b{UNIT_AFTER}[^.?!]{{0,15}}(?:pain|hurts)", I), ("Caller",), False, None),
        ("not_relieved", re.compile(r"(?:it|that|this|morphine|medicine|medication|pills?|dose|they|nothing)\s+(?:is |are |was |were )?(?:not|n'?t) (?:helping|working|touching|helped|enough)|\b(?:isn'?t|aren'?t|wasn'?t|hasn'?t|haven'?t|didn'?t|doesn'?t) (?:helping|working|touching|helped|help)|no relief|still (?:in pain|hurting|hurts|screaming|moaning)|thrashing|writhing|screaming|unbearable|worst pain|excruciating|crying out|nothing (?:helps|works)", I), ("Caller",), True, None),
    ],
    "other_urgent": [
        ("seizure", re.compile(r"seizure|seizing|convuls", I), ("Caller",), True, None),
        ("fall_injury", re.compile(r"(?:fell|fall|fallen|slipped|tripped|found (?:him|her) on the floor|on the floor)[^.?!]{0,60}(?:head|bleed|blood|broke|cut|bruis|swollen|can'?t (?:move|stand|walk|get up)|hip|hurt)|(?:hit|banged|bumped) (?:his|her|my|the) head|hit (?:it|the) \w+ on the", I), ("Caller",), True, None),
        ("bleeding", re.compile(r"bleeding|blood (?:from|in|coming|on)|nosebleed|(?:throwing up|vomit\w*|threw up) (?:bright )?(?:red )?blood|coffee grounds|black (?:and )?tarry|black stool|bright red blood|bloody", I), ("Caller",), True, None),
        ("death_arrest", re.compile(r"passed away|has died|just died|stopped breathing|no pulse|isn'?t breathing(?! (?:hard|fast|heavy|heavily|well|right))|not breathing(?! (?:hard|fast|heavy|heavily|well|right))|he'?s gone|she'?s gone|funeral home", I), ("Caller",), True, None),
        ("neuro_emergency", re.compile(r"face (?:is )?(?:drooping|falling)|slurred|(?:having|think .{0,12}) a stroke|can'?t move (?:his|her) (?:arm|leg)|unresponsive|(?:he|she|they|patient)\s+won'?t wake|not waking|can'?t wake|hard to wake|unconscious|passed out|collapsed", I), ("Caller",), True, None),
    ],
}


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]


def scan(turns: list[dict]) -> list[dict]:
    """-> [{category, rule, turns:[ids], quote}] for every rule hit (one per category+rule+sentence)."""
    hits, seen = [], set()
    for idx, t in enumerate(turns):
        prev = turns[idx - 1] if idx else None
        recent = turns[max(0, idx - 3):idx]
        recent_nurse = " ".join(x["text"] for x in recent if x["speaker"] == "Nurse")
        recent_text = " ".join(x["text"] for x in recent)
        for sent in split_sentences(t["text"]):
            is_q = sent.endswith("?")
            for cat, rules in RULES.items():
                if is_q and cat not in ("suicidal_statement", "escalation_request"):
                    continue
                for name, pat, speakers, suppress, ctx in rules:
                    if t["speaker"] not in speakers:
                        continue
                    if t["speaker"] == "Nurse" and re.match(r"(?:then|and then|so then)\b", sent, I):
                        continue  # a fragment that continues the previous (conditional) sentence
                    for m in pat.finditer(sent):
                        before = sent[:m.start()]
                        after = sent[m.end():]
                        if is_q and not re.search(r"\bcan (?:someone|somebody|a nurse|the nurse|anyone)", m.group(0), I):
                            continue
                        if is_q and re.search(r"before|after|between|tomorrow|next|monday|tuesday|wednesday|thursday|friday|saturday|sunday|morning|usual|regular|schedul|later", sent, I):
                            continue
                        # nurse return precautions: "call 911 right away if you get chest pain"
                        if t["speaker"] == "Nurse" and re.match(r"[^.?!]{0,25}\b(?:if|when|for|should)\b", after, I):
                            continue
                        if suppress and NEG_BEFORE.search(before[-40:]):
                            continue
                        if cat != "suicidal_statement" and CONDITIONAL.search(before):
                            continue
                        if ctx == "med" and not (MED_CONTEXT.search(t["text"]) or MED_CONTEXT.search(recent_text)):
                            continue
                        if cat in ("other_urgent", "uncontrolled_symptom", "breathing_concern") and HISTORICAL.search(sent):
                            continue
                        # the caller reading the nurse's list back ("chest pain, hard to wake ...") is not a new report
                        if t["speaker"] == "Caller" and recent_nurse and pat.search(recent_nurse) and cat != "suicidal_statement" \
                                and (CONDITIONAL.search(recent_nurse) or re.search(r"\bcall\b|\b911\b|nine one one", recent_nurse, I)):
                            continue
                        key = (cat, name, t["id"], sent)
                        if key not in seen:
                            seen.add(key)
                            hits.append({"category": cat, "rule": name, "turns": [t["id"]], "quote": sent})
                        break
            # short answer to "what is the pain on a scale of ..." (for example "It's a seven.")
            n_numbers = len(re.findall(r"\b(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|hundred|thousand|point|oh)\b", sent, I))
            if t["speaker"] == "Caller" and PAIN_ASK.search(recent_nurse or "") and len(sent.split()) <= 8 and n_numbers == 1 \
                    and re.search(rf"\b{NUM}\b{UNIT_AFTER}", sent, I) and not sent.endswith("?") and not HISTORICAL.search(sent):
                key = ("uncontrolled_symptom", "pain_answer", t["id"], sent)
                if key not in seen:
                    seen.add(key)
                    hits.append({"category": "uncontrolled_symptom", "rule": "pain_answer", "turns": [t["id"]], "quote": sent})
    return hits


def rule_categories(turns: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for h in scan(turns):
        out.setdefault(h["category"], []).append(h)
    return out


# ------------------------------------------------------------ Not-Applicable gate
_SIGNALS = [re.compile(p, I) for p in [
    r"\bpain|hurt|ache|sore\b", r"\bmedic|\bpills?\b|\bdoses?\b|\bmg\b|\bml\b|tablet|capsule|prescri|refill", r"insulin|glucose|sugar|blood pressure|\bbp\b",
    r"oxygen|concentrator|tank|cannula|nebuliz|inhaler|tubing|catheter|dressing|wound|supplies|diaper|brief|ostomy|feeding tube|commode|walker|wheelchair|hospital bed",
    r"fever|vomit|nause|dizz|cough|breath|swell|constipat|diarrh|bleed|\bfall\b|\bfell\b|rash|seiz|confus|agitat|restless|sleepy|eating|drinking|appetite|bowel|urine|urin|weight|stool|swallow",
    r"nurse (?:will|can|is going)|visit|on-call|clinician|the doctor|physician|social worker|chaplain|hospice|symptom|patient",
    r"\bdate of birth\b|\bdob\b|born in|birthday",
]]
_FORMULARY_RX = re.compile(r"\b(?:" + "|".join(re.escape(d) for d in FORMULARY if len(d) > 3) + r")\b", I)


def clinical_score(turns: list[dict]) -> int:
    """Number of distinct clinical signal groups present in the call (0 = no clinical content), plus one for a drug name."""
    text = " ".join(t["text"] for t in turns)
    score = sum(bool(p.search(text)) for p in _SIGNALS)
    return score + int(bool(_FORMULARY_RX.search(text)))
