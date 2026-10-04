"""Output schema of the summarizer (architecture 3.1) and a tiny validator for it.

SUMMARY_SCHEMA is also what the generator sends to vLLM for constrained decoding. `check()` implements the subset of
JSON Schema used here (type, enum, required, properties, additionalProperties, items), so structural validation and
decoding use one definition.
"""
from __future__ import annotations

CERT = {"type": "string", "enum": ["stated", "unclear", "not_stated"]}
INTS = {"type": "array", "items": {"type": "integer"}}
ANY = {"type": ["string", "number", "boolean", "null"]}
STR_OR_NULL = {"type": ["string", "null"]}


def _field(heard: bool = True) -> dict:
    # key order = the order of the gold summaries (value, certainty, heard_as, turns): vLLM's grammar forces schema order, and a model trained
    # on the gold order drops fields when the grammar asks for another one first
    props = {"value": STR_OR_NULL, "certainty": CERT}
    if heard:
        props["heard_as"] = {"type": "array", "items": {"type": "string"}}
    props["turns"] = INTS
    return {"type": "object", "required": ["value", "certainty", "turns"], "additionalProperties": False, "properties": props}


# Fact keys in the order that disagrees with the fewest gold facts (5.0% of 5,083; the gold itself uses both orders for a few pairs such as
# onset/severity). `certainty` is last in the gold, so it is last here: the grammar must not force it right after `type`.
FACT_KEYS = ["name", "action_type", "dose", "unit", "item", "strength", "education_type", "text", "route", "med_name", "medication", "present",
             "value", "location", "supply", "duration", "frequency", "onset", "prn", "severity", "status", "last_dose", "timeframe", "target",
             "med_status"]
FACT = {"type": "object", "required": ["type", "certainty"], "additionalProperties": False,
        "properties": {"type": {"type": "string", "enum": ["symptom", "pertinent_negative", "medication", "vital", "action", "education", "context", "supply"]},
                       **{k: ANY for k in FACT_KEYS},
                       "heard_as": {"type": "array", "items": {"type": "string"}},
                       "certainty": {"type": "string", "enum": ["stated", "unclear"]}}}
SPEAKER = {"type": "string", "enum": ["Caller", "Nurse"]}
BULLET = {"type": "object", "required": ["text", "speaker", "turns", "quote", "explanation", "facts"], "additionalProperties": False,
          "properties": {"text": {"type": "string"}, "speaker": SPEAKER, "turns": INTS, "quote": {"type": "string"},
                         "explanation": {"type": "string"}, "facts": {"type": "array", "items": FACT}}}
CHIEF = {"type": "object", "required": ["reason", "speaker", "turns", "quote", "explanation"], "additionalProperties": False,
         "properties": {"reason": {"type": "string"}, "speaker": SPEAKER, "turns": INTS, "quote": {"type": "string"}, "explanation": {"type": "string"}}}
FLAG = {"type": "object", "required": ["category", "turns", "quote"], "additionalProperties": False,
        "properties": {"category": {"type": "string", "enum": ["uncontrolled_symptom", "medication_concern", "suicidal_statement", "breathing_concern", "escalation_request", "other_urgent"]},
                       "turns": INTS, "quote": {"type": "string"}}}
SUMMARY_SCHEMA = {
    "type": "object",
    "required": ["not_applicable", "identity", "assessment", "response", "education", "risk_flags"],
    "additionalProperties": False,
    "properties": {
        "not_applicable": {"type": "object", "required": ["is_na", "reason"], "additionalProperties": False,
                           "properties": {"is_na": {"type": "boolean"}, "reason": STR_OR_NULL}},
        "identity": {"type": "object", "required": ["patient_name", "patient_dob", "caller_name", "relationship", "callback_phone"],
                     "additionalProperties": False,
                     "properties": {"patient_name": _field(), "patient_dob": _field(), "caller_name": _field(), "relationship": _field(False),
                                    "callback_phone": _field(), "patient_pronoun": STR_OR_NULL}},
        "chief_complaint": CHIEF,
        "assessment": {"type": "array", "items": BULLET},
        "response": {"type": "array", "items": BULLET},
        "education": {"type": "array", "items": BULLET},
        "risk_flags": {"type": "array", "items": FLAG},
    },
}


def _type_ok(v, t) -> bool:
    ts = t if isinstance(t, list) else [t]
    for x in ts:
        if x == "string" and isinstance(v, str): return True
        if x == "integer" and isinstance(v, int) and not isinstance(v, bool): return True
        if x == "number" and isinstance(v, (int, float)) and not isinstance(v, bool): return True
        if x == "boolean" and isinstance(v, bool): return True
        if x == "null" and v is None: return True
        if x == "array" and isinstance(v, list): return True
        if x == "object" and isinstance(v, dict): return True
    return False


def check(value, schema=SUMMARY_SCHEMA, path: str = "$") -> list[tuple[str, str]]:
    """-> [(path, message)] for every violation (empty list = valid)."""
    errs: list[tuple[str, str]] = []
    t = schema.get("type")
    if t is not None and not _type_ok(value, t):
        return [(path, f"expected {t}, got {type(value).__name__}")]
    if "enum" in schema and value not in schema["enum"]:
        errs.append((path, f"{value!r} not in {schema['enum']}"))
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errs.append((path, f"missing required key '{k}'"))
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                errs += check(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append((path, f"unexpected key '{k}'"))
    elif isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            errs += check(v, schema["items"], f"{path}[{i}]")
    return errs


def order_violations(obj) -> dict:
    """Count objects whose key order disagrees with the schema's property order -> {kind: (violating, total)}.
    Used on the gold summaries to prove the constrained-decoding schema does not fight the order a model is trained on."""
    P = SUMMARY_SCHEMA["properties"]
    orders = {"top": list(P), "not_applicable": list(P["not_applicable"]["properties"]), "identity": list(P["identity"]["properties"]),
              "identity_field": list(P["identity"]["properties"]["patient_name"]["properties"]), "chief": list(CHIEF["properties"]),
              "bullet": list(BULLET["properties"]), "fact": list(FACT["properties"]), "flag": list(FLAG["properties"])}
    out = {k: [0, 0] for k in orders}

    def look(kind, o):
        if isinstance(o, dict):
            out[kind][1] += 1
            out[kind][0] += int([k for k in orders[kind] if k in o] != list(o))

    look("top", obj)
    look("not_applicable", obj.get("not_applicable"))
    look("identity", obj.get("identity"))
    for v in (obj.get("identity") or {}).values():
        look("identity_field", v)
    look("chief", obj.get("chief_complaint"))
    for sec in ("assessment", "response", "education"):
        for b in obj.get(sec) or []:
            look("bullet", b)
            for f in b.get("facts") or []:
                look("fact", f)
    for f in obj.get("risk_flags") or []:
        look("flag", f)
    return {k: tuple(v) for k, v in out.items()}
