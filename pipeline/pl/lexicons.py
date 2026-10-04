"""Word lists and regexes used by the deterministic validators. Developed on the training split only."""
from __future__ import annotations

import re
from pathlib import Path

I = re.IGNORECASE
_HERE = Path(__file__).resolve().parent
FORMULARY = [l.strip().lower() for l in (_HERE.parent / "lexicons" / "formulary.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]


def rx(*alts: str) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(alts) + r")\b", I)


# ------------------------------------------------------------ hedges, negation, status cues
HEDGE = rx(r"i think", r"i guess", r"maybe", r"not (?:really )?sure", r"i don'?t know", r"don'?t (?:really )?remember", r"can'?t remember",
           r"probably", r"i believe", r"or so", r"i'?m trying to remember", r"let me think", r"might (?:be|have)",
           r"i'?m pretty sure", r"i suppose", r"something like", r"i (?:can'?t|cannot) tell", r"not certain", r"i'?m not positive", r"perhaps", r"seems? like")
SOFTENER = rx(r"about", r"around", r"approximately", r"approx", r"roughly", r"estimated", r"estimate", r"maybe", r"possibly", r"possible", r"probably",
              r"unsure", r"unclear", r"uncertain", r"not sure", r"not certain", r"reportedly", r"thought", r"appeared", r"seemed", r"seems",
              r"believed", r"guess(?:ed)?", r"could not say", r"couldn'?t say", r"did not know", r"didn'?t know", r"unable to (?:say|recall)",
              r"does not remember", r"did not remember", r"could not remember", r"or so", r"somewhat", r"may have", r"might", r"not clear", r"heard as", r"conflict")
NEGATION = rx(r"no", r"not", r"none", r"never", r"nothing", r"without", r"denies", r"denied", r"deny", r"negative", r"neither", r"nor", r"hasn'?t", r"haven'?t",
              r"hadn'?t", r"isn'?t", r"aren'?t", r"wasn'?t", r"weren'?t", r"doesn'?t", r"don'?t", r"didn'?t", r"can'?t", r"cannot", r"won'?t", r"wouldn'?t",
              r"couldn'?t", r"absent", r"free of", r"nothing")
NORMAL_STATE = rx(r"normal", r"fine", r"well", r"comfortable", r"comfortably", r"stable", r"clear", r"intact", r"okay", r"ok", r"good", r"settled", r"resting",
                  r"at baseline", r"unchanged", r"alert", r"steady", r"easy", r"easily", r"calm", r"breathing")
COMPLETION = rx(r"it'?s done", r"that'?s done", r"all done", r"already (?:\w+ )?(?:sent|put|paged|placed|called|messaged|ordered|scheduled|submitted|done|made|added|notified|contacted)",
                r"i already", r"we already", r"i'?ve got (?:the|that|it|a|your)\b", r"i'?ve (?:started|begun|opened|got it|got that)", r"i'?ve (?:\w+ )?(?:sent|put|placed|paged|messaged|called|ordered|submitted|scheduled|notified|added|made|left|emailed|faxed|logged|documented|entered|contacted|requested|moved|changed|updated|booked|arranged|confirmed|spoken)",
                r"i have (?:\w+ )?(?:sent|put|placed|paged|messaged|called|ordered|submitted|scheduled|notified|added|made|left|requested|moved|updated|booked)",
                r"we'?ve (?:\w+ )?(?:sent|put|placed|paged|called|ordered|scheduled)", r"just (?:sent|put|paged|called|messaged|ordered|placed|submitted)",
                r"has been (?:sent|paged|ordered|placed|scheduled|called|messaged|submitted|notified|moved|updated)", r"was just (?:sent|paged|placed)",
                r"i (?:sent|paged|messaged|ordered|placed|submitted|scheduled|notified|moved|changed|updated|booked) ",
                r"i (?:reached|spoke|talked|called|sent|paged|messaged|ordered|placed|submitted|scheduled|notified|moved|changed|updated|booked|recorded|documented|entered|noted|logged|confirmed|left|requested|arranged|contacted|emailed|faxed|checked|looked)\b",
                r"i'?ve \w+ed\b", r"i did (?:reach|call|send|page|message|order|talk|speak|get|contact|put|place|schedule|submit)\b", r"i just \w+(?:ed|t)\b", r"it'?s on the schedule", r"it is on the schedule", r"you'?re (?:all )?(?:set|scheduled|booked)", r"already (?:on|scheduled|booked)", r"(?:was|were|has been|have been) (?:\w+ )?(?:ordered|sent|placed|submitted|scheduled|paged|called|messaged|put in|entered|documented|recorded|confirmed|delivered|dispatched)\b")
NOW_PROGRESS = re.compile(r"\bi'?m (?:\w+ing)\b[^.?!]{0,60}\b(?:now|right now)\b|\bright now\b|as we speak|while (?:we'?re|you'?re) (?:talking|on|here)|\bnow\b[.?!]?\s*$", I)
FUTURE = rx(r"i'?ll", r"i will", r"i'?m going to", r"i am going to", r"going to", r"let me", r"we'?ll", r"we will", r"gonna", r"i'?d like to", r"i can", r"i could",
            r"i'?d (?:go ahead|have|get)", r"will (?:be|have|get|send|call|page|message)", r"i'?m (?:about|planning) to", r"i should", r"want to (?:send|call|page|message|schedule|order)", r"need to (?:send|call|page|message|schedule|order)",
            r"someone will", r"they will", r"they'?ll", r"he will", r"she will", r"within the (?:hour|day)", r"by (?:tomorrow|tonight|this)", r"tomorrow", r"later (?:today|tonight)")
PLANNED_TEXT = re.compile(r"^\s*(planned|plans|will|to be|scheduled to|to |arranged to|intend|going to)", I)
DONE_TEXT = re.compile(r"^\s*(completed|already|done|has been|was (?:sent|paged|placed|ordered)|sent|paged|ordered|placed)\b", I)

# ------------------------------------------------------------ clinical terms
# term -> (pattern for the SUMMARY text, pattern for the TRANSCRIPT; if the summary says it and the transcript has no trace of it, it is invented)
def _t(summary: str, transcript: str) -> tuple[re.Pattern, re.Pattern]:
    return re.compile(summary, I), re.compile(transcript, I)


CLINICAL = {
    "fever": _t(r"\bfever|febrile\b", r"fever|febrile|temperature|\btemp\b|hot to the touch|burning up|chills|thermometer|\b10[0-9](?:\.\d)?\b|one hundred|one oh"),
    "fall": _t(r"\bfalls?\b|\bfell\b(?! (?:below|under|to\b|from \d))|\bfallen\b", r"fall|fell|fallen|slipped|tripped|on the floor|went down|knocked|stumbled|hit (?:his|her|the)|collapsed|ground"),
    "chest pain": _t(r"chest pain|chest pressure|chest tightness", r"chest|heart|pressure|tight"),
    "seizure": _t(r"seizure|seizing|convuls", r"seiz|convuls|shak|jerk|stare|stared|staring|spell|fit\b|twitch|blank|unrespons|lip smack"),
    "rash": _t(r"\brash|hives\b", r"rash|hive|itch|red spots|bumps|breaking out|welts|blotch|spots"),
    "bleeding": _t(r"bleed|hemorrhag|nosebleed", r"bleed|blood|bloody|nosebleed|hemorrhag|spotting|red|dark|tarry|coffee|clot|oozing|soaked"),
    "vomiting": _t(r"vomit|emesis", r"vomit|throw|threw|thrown|throwing up|puk|sick to|heav|retch|spit|spat|gag|upchuck|brought it up|came back up|nause"),
    "diarrhea": _t(r"diarrh|loose stool", r"diarrh|loose|runny|watery|stool|bowel|poop|accident|liquid|going a lot|bathroom"),
    "headache": _t(r"headache|migraine", r"headache|head hurt|head is|head pain|migraine|pounding|my head|his head|her head|tired head|temple"),
    "dizziness": _t(r"dizz|lighthead|vertigo", r"dizz|light ?headed|woozy|spinning|vertigo|faint|room tilt|tilting|unsteady|wobbl|swim|off balance|balance"),
    "cough": _t(r"\bcough", r"cough|hack|clear (?:his|her|my) throat|wheez|phlegm|mucus|congest"),
    "swelling": _t(r"swell|swollen|edema", r"swell|swollen|edema|puff|bloat|fluid|retention|tight|big|bigger|tender|enlarge|ankle|legs"),
    "confusion": _t(r"confus|disorient|delir|hallucinat", r"confus|disorient|mixed up|doesn'?t know|not making sense|nonsens|delir|agitat|out of it|foggy|hallucinat|talking to|seeing|forget|wrong name|calling|not herself|not himself|lost|strange|odd"),
    "shortness of breath": _t(r"short(?:ness)? of breath|breathless|dyspnea|trouble breathing|difficulty breathing", r"breath|breathing|gasp|winded|wheez|air\b|chok|oxygen|sat(?:uration)?|panting|puffing"),
    "unresponsive": _t(r"unrespons|unconscious|difficult to wake|hard to wake|not waking", r"unrespons|unconscious|wake|waking|woke|asleep|sleep|limp|passed out|faint|rous|lethar|sleepy|drows|out cold"),
    "suicidal": _t(r"suicid|wish(?:ed)? to die|self-harm|take all (?:his|her|the|of)", r"die|dead|suicid|kill|end it|ending it|take (?:them )?all|wouldn'?t wake|not wake|better off|hurt(?:ing)? (?:my|your|him|her|them)self|himself|herself|pills|gone|harm|burden|give up|no point|done|hopeless|depress|988|crisis|down\b"),
    "nausea": _t(r"nause", r"nause|sick to|queasy|upset stomach|stomach|vomit|throw|threw|retch|gag|heav"),
    "constipation": _t(r"constipat", r"constipat|bowel|\bbm\b|stool|poop|haven'?t gone|hasn'?t gone|haven'?t had|hasn'?t had|backed up|impact|strain|laxative|miralax|senna|colace"),
    "pain": _t(r"\bpain\b|\bhurt|\bsore\b|\bache|aching|tender", r"pain|hurt|sore|ache|aching|tender|ouch|moan|grimac|uncomfortable|discomfort|burn|cramp|sting|throb|stiff"),
    "infection": _t(r"infection|\buti\b|pus\b", r"infect|uti\b|urinary|pus\b|discharge|antibiotic|swab|cloudy|smell|foul|red|warm|hot|hurts"),
    "choking": _t(r"chok|aspirat", r"chok|aspirat|swallow|coughing|gag|went down the wrong|food|drink|stuck|gasp|breath"),
    "weight gain": _t(r"weight gain|gained .{0,12}pounds", r"weigh|pound|lbs|scale|gain"),
    "blood pressure": _t(r"blood pressure|\bbp\b", r"blood pressure|\bbp\b|cuff|pressure|\d{2,3} over \d{2,3}|\d{2,3}/\d{2,3}|systolic|reading|monitor"),
    "oxygen": _t(r"\boxygen\b|\bo2\b", r"oxygen|\bo2\b|concentrator|tank|sat\b|saturation|cannula|nasal|breath|liters?|portable"),
    "wound": _t(r"\bwound|ulcer|pressure sore|bedsore", r"wound|ulcer|sore|bedsore|pressure|skin|dressing|bandage|red spot|spot|tailbone|bottom|open|broken|blister|bruise|cut\b|scab"),
}

# ------------------------------------------------------------ relationship words
RELATIONSHIP_WORDS = {
    "mother": ["mother", "mom", "mum", "mama", "mommy", "ma"], "father": ["father", "dad", "daddy", "papa", "pop"],
    "wife": ["wife", "my wife"], "husband": ["husband", "hubby"], "daughter": ["daughter"], "son": ["son"], "sister": ["sister"], "brother": ["brother"],
    "spouse": ["spouse", "wife", "husband", "partner"], "partner": ["partner", "boyfriend", "girlfriend", "fiance"], "grandmother": ["grandmother", "grandma", "nana", "granny"],
    "grandfather": ["grandfather", "grandpa", "granddad"], "grandson": ["grandson"], "granddaughter": ["granddaughter"], "niece": ["niece"], "nephew": ["nephew"],
    "aunt": ["aunt", "auntie"], "uncle": ["uncle"], "friend": ["friend"], "neighbor": ["neighbor", "neighbour"], "aide": ["aide", "caregiver", "caretaker", "home health aide", "hha", "cna"],
    "caregiver": ["caregiver", "aide", "caretaker", "cna"], "nurse": ["nurse", "rn", "lpn"], "daughter-in-law": ["daughter in law", "daughter-in-law"], "son-in-law": ["son in law", "son-in-law"],
    "self": ["myself", "me", "my own", "i'm the patient", "i am the patient", "calling for myself", "it's me", "this is"],
    "staff": ["staff", "nurse", "aide", "caregiver", "facility", "assisted living", "nursing home", "resident"], "guardian": ["guardian", "foster"], "parent": ["mom", "dad", "mother", "father", "parent"],
    "volunteer": ["volunteer"], "cousin": ["cousin"], "mother-in-law": ["mother in law"], "father-in-law": ["father in law"], "roommate": ["roommate"], "pastor": ["pastor", "chaplain"],
}

# generic words: a hit is only a warning (the summary may legitimately generalize, e.g. "pain pill" for a named drug)
GENERIC_TERMS = {"pain", "blood pressure", "oxygen", "wound", "infection", "weight gain", "swelling", "shortness of breath", "constipation", "nausea", "cough"}
# who the patient is, as the caller names them, for each relationship the caller can have (caller = X of the patient)
PATIENT_WORDS = {
    "daughter": ["mom", "mother", "dad", "father", "mama", "papa", "parent", "grandma", "grandmother", "grandpa", "grandfather", "mum"],
    "son": ["mom", "mother", "dad", "father", "mama", "papa", "parent", "grandma", "grandmother", "grandpa", "grandfather", "mum"],
    "wife": ["husband", "hubby"], "husband": ["wife"], "spouse": ["husband", "wife", "hubby"], "partner": ["partner", "boyfriend", "girlfriend", "husband", "wife"],
    "mother": ["son", "daughter", "child", "baby", "boy", "girl", "kid", "toddler", "infant"], "father": ["son", "daughter", "child", "baby", "boy", "girl", "kid", "toddler", "infant"],
    "parent": ["son", "daughter", "child", "baby", "boy", "girl", "kid", "toddler", "infant"], "sister": ["brother", "sister"], "brother": ["brother", "sister"],
    "granddaughter": ["grandma", "grandmother", "grandpa", "grandfather", "nana"], "grandson": ["grandma", "grandmother", "grandpa", "grandfather", "nana"],
    "niece": ["aunt", "uncle", "auntie"], "nephew": ["aunt", "uncle", "auntie"], "friend": ["friend"], "neighbor": ["neighbor", "neighbour"],
    "aide": ["client", "patient", "resident", "lady", "gentleman"], "caregiver": ["client", "patient", "resident", "lady", "gentleman"], "staff": ["resident", "patient", "client"],
}

# specific high-risk terms: if the summary names one and the call never says it in so many words, ask for a look
SPECIFIC_TERMS = {"fever", "fall", "chest pain", "seizure", "rash", "bleeding", "suicidal", "unresponsive", "choking"}
