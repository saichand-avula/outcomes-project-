"""Deterministic repair of defects found when auditing the sampler output (see AUDIT.md).

D1. Self-contradiction: a record lists a symptom AND a pertinent negative for the same thing
    (e.g. symptom 'confusion' + negative 'confusion') -> the transcript would be impossible. The negative is dropped.
D2. Same drug twice with different doses in one call (random with-replacement draw) -> evaluation matches meds by
    name, so the gold would be ambiguous. The later duplicate (and any supply row duplicating the same item) is dropped.
D3. Policy P6 (README): a nurse recommendation of 911/ED is an `escalation_request` risk flag. 30 breathing_concern records
    carry an `escalation_911_ed` action but no such flag -> the gold would call a correct rule/model flag a false positive.
    The flag is added (required, rationale cites P6).
Every repair is appended to `annotation_notes` as 'repair: ...' so it is auditable. No RNG is used.
"""
from __future__ import annotations
from schema import FactRecord, RiskFlag

SYM_CONFLICTS = {"fever": "fever", "nausea": "nausea", "vomiting": "nausea",
                 "shortness of breath": "difficulty breathing", "confusion": "confusion", "fall": "falls"}


def _retarget(rec: FactRecord, dropped: set[str]) -> None:
    """Keep noise/hedge targets pointing at facts that still exist; never leave an asr_error/ambiguous record target-less."""
    live = {m.id for m in rec.medications}
    npl = rec.noise_plan
    if npl:
        for key in ("unclear_targets", "drug_confusion_targets"):
            if key in npl:
                npl[key] = [i for i in npl[key] if i in live]
        if rec.category == "asr_error" and not npl.get("drug_confusion_targets") and rec.medications:
            first = rec.medications[0].id
            npl["drug_confusion_targets"] = [first]
            npl["unclear_targets"] = [first]
            rec.annotation_notes.append(f"repair: retargeted ASR drug confusion to {first}")
    if rec.category == "ambiguous":
        ids = [i for i in rec.persona.get("uncertain_facts", []) if i in {f.id for f in (*rec.medications, *rec.symptoms)}]
        if not ids:
            cand = next((f for f in (*rec.medications, *rec.symptoms) if f.certainty == "stated"), None)
            if cand is not None:
                cand.certainty = "unclear"
                ids = [cand.id]
                rec.annotation_notes.append(f"repair: hedged {cand.id} (previous hedge target was dropped)")
        rec.persona["uncertain_facts"] = ids


def repair_record(rec: FactRecord) -> FactRecord:
    if rec.not_applicable:
        return rec
    # D1 contradictory negatives
    sym = {s.name for s in rec.symptoms}
    banned = {neg for s, neg in SYM_CONFLICTS.items() if s in sym}
    kept = []
    for n in rec.pertinent_negatives:
        if n.name in banned:
            rec.annotation_notes.append(f"repair: dropped pertinent negative '{n.name}' (contradicts a reported symptom)")
        else:
            kept.append(n)
    rec.pertinent_negatives = kept
    # D3 policy P6
    if any(a.type == "escalation_911_ed" for a in rec.actions) and not any(r.category == "escalation_request" for r in rec.risk_flags):
        nxt = 1 + max([int(r.id[1:]) for r in rec.risk_flags] or [0])
        rec.risk_flags.append(RiskFlag(id=f"R{nxt}", category="escalation_request", required=True,
                                       rationale="nurse recommends 911/ED (policy P6)"))
        rec.annotation_notes.append("repair: added escalation_request flag (nurse-initiated 911/ED, policy P6)")
    # D2 duplicate meds
    seen: set[str] = set(); keep_m = []; dropped: set[str] = set()
    for m in rec.medications:
        key = m.name or f"__{m.id}"
        if key in seen:
            dropped.add(m.id)
            rec.annotation_notes.append(f"repair: dropped duplicate medication {m.id} ({m.name})")
        else:
            seen.add(key); keep_m.append(m)
    if dropped:
        rec.medications = keep_m
        seen_items: set[tuple] = set(); keep_u = []
        for u in rec.supplies:
            k = (u.item, u.request)
            if u.request in ("refill", "delivery") and k in seen_items:
                rec.annotation_notes.append(f"repair: dropped duplicate supply row {u.id} ({u.item})")
                continue
            seen_items.add(k); keep_u.append(u)
        rec.supplies = keep_u
        _retarget(rec, dropped)
    return rec


def repair_all(recs: list[FactRecord]) -> tuple[list[FactRecord], dict]:
    out = [repair_record(r.model_copy(deep=True)) for r in recs]
    n_neg = sum(1 for r in out for n in r.annotation_notes if "pertinent negative" in n)
    n_dup = sum(1 for r in out for n in r.annotation_notes if "duplicate medication" in n)
    n_p6 = sum(1 for r in out for n in r.annotation_notes if "policy P6" in n and n.startswith("repair"))
    return out, dict(records=len(out), p6_flags_added=n_p6, negatives_dropped=n_neg, duplicate_meds_dropped=n_dup,
                     records_touched=sum(1 for r in out if any(n.startswith("repair:") for n in r.annotation_notes)))
