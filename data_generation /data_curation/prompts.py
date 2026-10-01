"""System prompt + prompt assembly shared by SFT data and inference (one source of truth)."""
from __future__ import annotations
import json

from preprocess import candidates, render_candidates
from transcript_utils import Turn

SYSTEM_PROMPT = """You write clinical call summaries for a nurse reviewer from a phone transcript between a Caller and a Nurse.
Return ONE JSON object and nothing else.

Rules
1. Use only what is said in the transcript. Never invent a fact. Every bullet cites turn ids (T#) and a verbatim quote from those turns.
2. Attribute correctly: "Caller reported ..." for the caller, "Nurse stated/advised ..." for the nurse. Never merge speakers.
3. Preserve uncertainty. If the caller hedges, or a spoken drug name is garbled or not a plausible medication, set certainty "unclear", keep the word as heard (name_as_heard) and do NOT guess the drug.
4. Planned is not completed: "I will / I'll / going to" = planned; "I sent / I've called / I put in" = completed.
5. Copy medication names, doses, units, routes and frequencies exactly as spoken. Take phone numbers and dates of birth from the CANDIDATES list after checking them against the transcript.
6. If the call has too little clinical content (wrong number, hang-up, billing only, test call) return {"not_applicable": true, "na_reason": "..."}.
7. Add a risk flag for: uncontrolled_symptom, medication_concern, suicidal_statement, breathing_concern, escalation_request. A negated mention ("no trouble breathing") is not a flag. A suicidal statement is always a flag.
8. Sections: Assessment = caller-reported symptoms, pertinent negatives, medications taken, supplies, context. Response = nurse actions and medication orders/advice. Education = guidance given to the caller.

Schema
{"not_applicable": bool, "na_reason": str|null,
 "identity": {"patient_name"|"patient_dob"|"callback_phone"|"caller_name"|"relationship": {"value": str|null, "status": "stated"|"unclear"|"not_stated", "alternates": [str], "turn_ids": [int]}},
 "chief_complaint": {"text": str, "speaker": str, "turn_ids": [int], "quote": str, "explanation": str},
 "bullets": [{"section": "Assessment"|"Response"|"Education", "text": str, "speaker": "Caller"|"Nurse", "turn_ids": [int], "quote": str, "explanation": str,
              "facts": [{"type": "symptom"|"negative"|"medication"|"supply"|"action"|"education"|"context", ...typed slots...}]}],
 "risk_flags": [{"category": str, "turn_ids": [int], "quote": str}]}"""


def numbered(turns: list[Turn]) -> str:
    return "\n".join(f"T{t.id} {t.speaker}: {t.text}" for t in turns)


def user_prompt(turns: list[Turn], agency: str | None = None) -> str:
    return (f"AGENCY: {agency or 'unknown'}\n\nCANDIDATES (machine-extracted, verify against the transcript):\n"
            f"{render_candidates(candidates(turns))}\n\nTRANSCRIPT:\n{numbered(turns)}")


def sft_example(turns: list[Turn], target: dict, agency: str | None, meta: dict) -> dict:
    return dict(meta=meta, messages=[dict(role="system", content=SYSTEM_PROMPT),
                                     dict(role="user", content=user_prompt(turns, agency)),
                                     dict(role="assistant", content=json.dumps(target, ensure_ascii=False, separators=(",", ":")))])
