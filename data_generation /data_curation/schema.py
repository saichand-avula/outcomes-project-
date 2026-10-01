"""Fact-record schema: the single source of truth for gold labels.

Every downstream artifact (voicing prompt, ASR noise log, gold summary JSON,
validators, CFA scoring) is derived from a FactRecord. Gold is therefore
correct by construction.
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

Speaker = Literal["Caller", "Nurse"]
Certainty = Literal["stated", "unclear"]
IdStatus = Literal["stated", "unclear", "not_stated"]
ActionStatus = Literal["planned", "completed", "advised"]
MedStatus = Literal["advised", "administered", "ordered", "stopped",
                    "requested", "current", "label_read", "mentioned"]
RiskCategory = Literal["uncontrolled_symptom", "medication_concern",
                       "suicidal_statement", "breathing_concern",
                       "escalation_request"]
Category = Literal["routine", "ambiguous", "asr_error", "medication",
                   "supply", "high_risk", "not_applicable"]
ActionType = Literal["refill_request", "team_message", "nurse_visit",
                     "callback", "escalation_911_ed", "appointment_scheduling",
                     "physician_notification", "documentation",
                     "medication_order", "referral"]
EducationType = Literal["medication_instruction", "medication_timing",
                        "medication_safety", "administration_method",
                        "comfort_measure", "return_precaution",
                        "follow_up_expectation", "callback_invitation",
                        "emergency_guidance", "supportive_care"]


class Evidence(BaseModel):
    """Where a fact is grounded. Real records: `anchor` (a verbatim fragment,
    resolved to turn_ids by transcript_utils). Synthetic: turn_ids come from
    the voicing step's per-turn fact tags (anchor stays None)."""
    speaker: Speaker
    anchor: Optional[str] = None
    occurrence: Optional[int] = None      # disambiguate repeated anchors (0-based)
    span_after: int = 0                   # also cite the next N turns (e.g. caller's answer to a nurse question)
    turn_ids: list[int] = Field(default_factory=list)


class Fact(BaseModel):
    id: str
    evidence: list[Evidence] = Field(default_factory=list)
    note: Optional[str] = None


class IdField(BaseModel):
    value: Optional[str] = None
    status: IdStatus = "not_stated"
    evidence: list[Evidence] = Field(default_factory=list)
    alternates: list[str] = Field(default_factory=list)   # conflicting variants heard
    note: Optional[str] = None


class Identity(BaseModel):
    patient_name: IdField = IdField()
    patient_dob: IdField = IdField()       # ISO yyyy-mm-dd
    caller_name: IdField = IdField()
    relationship: IdField = IdField()
    callback_phone: IdField = IdField()    # digits only


class Symptom(Fact):
    name: str
    severity: Optional[str] = None
    location: list[str] = Field(default_factory=list)
    onset_duration: Optional[str] = None
    certainty: Certainty = "stated"
    reporter: Speaker = "Caller"


class PertinentNegative(Fact):
    name: str


class Vital(Fact):
    name: Literal["bp", "hr", "temp", "spo2", "rr", "weight"]
    value: str
    unit: Optional[str] = None
    when: Optional[str] = None
    certainty: Certainty = "stated"


class Medication(Fact):
    name: Optional[str] = None            # canonical generic, lower-case; None if unrecoverable
    name_as_heard: Optional[str] = None   # surface string if ASR-garbled
    strength: Optional[str] = None
    dose: Optional[str] = None
    unit: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    prn: Optional[bool] = None
    last_dose: Optional[str] = None
    status: MedStatus = "mentioned"
    certainty: Certainty = "stated"
    critical: bool = True                 # False: incidental mention, excluded from CFA


class Supply(Fact):
    item: str
    quantity_remaining: Optional[str] = None
    request: Literal["refill", "delivery", "equipment", "none"] = "none"
    certainty: Certainty = "stated"


class Action(Fact):
    type: ActionType
    description: str
    status: ActionStatus
    actor: Speaker = "Nurse"


class Education(Fact):
    type: EducationType
    description: str


class ContextFact(Fact):
    kind: Literal["diagnosis", "functional_status", "history",
                  "caller_concern", "nonadherence", "other"]
    text: str


class RiskFlag(Fact):
    category: RiskCategory
    required: bool = True                 # False = acceptable but not required for recall
    rationale: str


class FactRecord(BaseModel):
    record_id: str
    source: Literal["real", "synthetic"]
    split: Optional[Literal["train", "dev", "eval", "sanity"]] = None
    category: Category
    subtype: Optional[str] = None
    secondary_tags: list[str] = Field(default_factory=list)
    persona: dict = Field(default_factory=dict)         # voicing controls
    noise_plan: dict = Field(default_factory=dict)      # ASR-noise controls
    agency: Optional[str] = None
    call_timestamp_utc: str = "2000-01-01T14:41:00Z"
    identity: Identity = Identity()
    reason_for_call: str = ""
    symptoms: list[Symptom] = Field(default_factory=list)
    pertinent_negatives: list[PertinentNegative] = Field(default_factory=list)
    vitals: list[Vital] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    supplies: list[Supply] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    context: list[ContextFact] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    not_applicable: bool = False
    na_subtype: Optional[str] = None
    annotation_notes: list[str] = Field(default_factory=list)

    def all_facts(self) -> list[Fact]:
        return [*self.symptoms, *self.pertinent_negatives, *self.vitals,
                *self.medications, *self.supplies, *self.actions,
                *self.education, *self.context, *self.risk_flags]

    @model_validator(mode="after")
    def _checks(self):
        ids = [f.id for f in self.all_facts()]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"duplicate fact ids: {sorted(dup)}")
        if self.not_applicable:
            if self.symptoms or self.medications or self.actions or self.risk_flags:
                raise ValueError("not_applicable record must carry no clinical facts")
            if not self.na_subtype:
                raise ValueError("not_applicable record needs na_subtype")
        for m in self.medications:
            if m.certainty == "stated" and m.name is None and m.critical:
                raise ValueError(f"{m.id}: critical stated medication needs a name")
        return self

    def critical_slots(self) -> list[tuple]:
        """Slots counted by Critical-Fact Accuracy (plan Section 6).
        Each slot = (kind, id, value-dict). Matching rules live in eval/score.py."""
        s: list[tuple] = []
        if self.not_applicable:      # a correct "Not Applicable" output has no identity/summary to score
            return [("not_applicable", "NA", {"value": True})]
        for f in ("patient_name", "patient_dob", "caller_name", "relationship", "callback_phone"):
            fld: IdField = getattr(self.identity, f)
            s.append(("identity", f, {"value": fld.value, "status": fld.status}))
        for m in self.medications:
            if m.critical:
                s.append(("medication", m.id, {"name": m.name, "dose": m.dose, "unit": m.unit,
                          "route": m.route, "frequency": m.frequency, "status": m.status,
                          "certainty": m.certainty}))
        for x in self.symptoms:
            s.append(("symptom", x.id, {"name": x.name, "severity": x.severity,
                                        "certainty": x.certainty}))
        for a in self.actions:
            s.append(("action", a.id, {"type": a.type, "status": a.status}))
        for r in self.risk_flags:
            if r.required:
                s.append(("risk_flag", r.id, {"category": r.category}))
        s.append(("not_applicable", "NA", {"value": self.not_applicable}))
        return s
