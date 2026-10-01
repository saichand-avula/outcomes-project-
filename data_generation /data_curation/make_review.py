"""Writes data/gold/real5_review.md: every gold fact next to the transcript turns it cites,
so a human can verify the 5 annotations quickly."""
from gold_real5 import build, HERE
from transcript_utils import split_turns

def line(label, ev, turns, extra=""):
    ids = sorted({i for e in ev for i in e.turn_ids})
    quotes = " / ".join(f"T{i} {turns[i-1].speaker[0]}: “{turns[i-1].text[:110]}{'…' if len(turns[i-1].text)>110 else ''}”" for i in ids[:3])
    return f"- **{label}** {extra}  \n  turns {ids} — {quotes}\n"

recs, tr = build()
out = ["# Real-5 gold annotations — review sheet\n",
       "Check each fact against the cited turn. `unclear` items and POLICY notes are the decisions to confirm.\n"]
for r in recs:
    turns = split_turns(tr[r.record_id])
    out.append(f"\n## {r.record_id} — {r.agency} ({r.category}/{r.subtype}) — {len(turns)} turns\n")
    out.append(f"**Reason for call:** {r.reason_for_call}\n\n**Identity**\n")
    for k, f in r.identity.model_dump().items():
        fld = getattr(r.identity, k)
        extra = f"= `{fld.value}` [{fld.status}]" + (f" alternates {fld.alternates}" if fld.alternates else "")
        out.append(line(k, fld.evidence, turns, extra) + (f"  _note: {fld.note}_\n" if fld.note else ""))
    groups = [("Symptoms", r.symptoms, lambda x: f"{x.name} | sev={x.severity} | {x.certainty}"),
              ("Pertinent negatives", r.pertinent_negatives, lambda x: x.name),
              ("Vitals", r.vitals, lambda x: f"{x.name}={x.value} [{x.certainty}]"),
              ("Medications", r.medications, lambda x: f"{x.name or '∅'} (heard: {x.name_as_heard}) dose={x.dose} {x.unit or ''} route={x.route} freq={x.frequency} status={x.status} [{x.certainty}]{'' if x.critical else ' (non-critical)'}"),
              ("Supplies", r.supplies, lambda x: f"{x.item}: {x.quantity_remaining} req={x.request} [{x.certainty}]"),
              ("Actions", r.actions, lambda x: f"{x.type} — {x.description} [{x.status}]"),
              ("Education", r.education, lambda x: f"{x.type} — {x.description}"),
              ("Context", r.context, lambda x: f"{x.kind}: {x.text}"),
              ("Risk flags", r.risk_flags, lambda x: f"{x.category} ({'required' if x.required else 'optional'}) — {x.rationale}")]
    for title, items, fmt in groups:
        if not items: continue
        out.append(f"\n**{title}**\n")
        for x in items:
            out.append(line(x.id, x.evidence, turns, fmt(x)) + (f"  _note: {x.note}_\n" if x.note else ""))
    if r.annotation_notes:
        out.append("\n**Annotation notes**\n" + "".join(f"- {n}\n" for n in r.annotation_notes))
(HERE / "data/gold/real5_review.md").write_text("".join(out))
print("wrote review sheet,", sum(len(x) for x in out), "chars")
