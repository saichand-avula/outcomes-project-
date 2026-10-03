"""Load hand-authored call files (data/authoring/<split>/<call_id>.yaml).

Authoring file layout (see data/authoring/README.md):

    call_id, split, blueprint
    setup:            Call Setup block (fact-table columns)
    chief_complaint:  Chief Complaint block
    assessment:       list of Assessment rows (item_id A1..)
    response:         list of Response rows (item_id R1..)
    education:        list of Education rows (item_id E1..)
    risk_flags:       list of Risk Flag rows (flag_id F1..)
    transcript: |     one turn per line: "Nurse -> text || tag1, tag2"
    noise_events:     list of {turn, type, true_form, heard_form, fact_id}
    gold:             summary JSON target; each bullet has `covers: [fact ids]` (alignment, stripped from target)
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
AUTHORING = ROOT / "data" / "authoring"
IDENTITY_IDS = ["patient_name", "patient_dob", "caller_name", "relationship", "callback_phone"]
SECTION_KEYS = ["assessment", "response", "education"]

_TURN_RE = re.compile(r"^(Nurse|Caller) -> (.*?)(?:\s*\|\|\s*(.*))?$")


def parse_transcript(block: str) -> list[dict]:
    turns = []
    for n, raw in enumerate([l for l in block.splitlines() if l.strip()], start=1):
        m = _TURN_RE.match(raw.strip())
        if not m:
            raise ValueError(f"turn {n}: bad line format: {raw[:80]!r}")
        tags = [t.strip() for t in (m.group(3) or "").split(",") if t.strip()]
        turns.append({
            "id": n,
            "speaker": m.group(1),
            "text": m.group(2).strip(),
            "fact_ids": [t for t in tags if t != "label_error"],
            "label_error": "label_error" in tags,
        })
    return turns


def transcript_text(turns: list[dict]) -> str:
    return "\n".join(f"{t['speaker']} -> {t['text']}" for t in turns) + "\n"


def split_gold(gold: dict) -> tuple[dict, dict]:
    """Return (target, alignment). Alignment maps 'section[i]' -> covered fact ids."""
    import copy

    target = copy.deepcopy(gold)
    alignment: dict[str, list[str]] = {}
    cc = target.get("chief_complaint")
    if cc is not None:
        alignment["chief_complaint"] = cc.pop("covers", [])
    for key in SECTION_KEYS:
        for i, item in enumerate(target.get(key) or []):
            alignment[f"{key}[{i}]"] = item.pop("covers", [])
    return target, alignment


def load_call(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    turns = parse_transcript(data.get("transcript") or "")
    target, alignment = split_gold(data.get("gold") or {})
    from .textnorm import normalize

    events = []
    for ev in data.get("noise_events") or []:
        ev = dict(ev)
        if ev.get("turn") in (None, "auto"):
            forms = [x.strip() for x in str(ev.get("heard_form", "")).split("/") if x.strip()]
            ev["turn"] = next((t["id"] for t in turns for f in forms if normalize(f) in normalize(t["text"])), 0)
        events.append(ev)
    data["noise_events"] = events
    return {
        "path": str(path.relative_to(ROOT)),
        "call_id": data["call_id"],
        "split": data["split"],
        "blueprint": data.get("blueprint"),
        "setup": data.get("setup") or {},
        "chief_complaint": data.get("chief_complaint") or {},
        "assessment": data.get("assessment") or [],
        "response": data.get("response") or [],
        "education": data.get("education") or [],
        "risk_flags": data.get("risk_flags") or [],
        "turns": turns,
        "transcript": transcript_text(turns),
        "noise_events": data.get("noise_events") or [],
        "target": target,
        "alignment": alignment,
    }


def load_split(split: str, root: Path | None = None) -> list[dict]:
    d = (root or AUTHORING) / split
    return [load_call(p) for p in sorted(d.glob("*.yaml"))]


def load_all(root: Path | None = None) -> list[dict]:
    out = []
    for split in ("train", "val"):
        if ((root or AUTHORING) / split).exists():
            out += load_split(split, root)
    return out
