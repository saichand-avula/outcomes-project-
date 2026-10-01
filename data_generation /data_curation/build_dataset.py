"""End-to-end deterministic dataset build (no LLM, no API, no GPU):

    data/fact_records/*.jsonl -> repair -> voicer -> asr_noise -> build_gold -> validators -> files

    python build_dataset.py            # writes data/transcripts, data/gold, data/sft, DATA_CARD.md, SHA256SUMS
Same seed => byte-identical output (per-record RNG seeded from the record id).
"""
from __future__ import annotations
import collections
import hashlib
import json
import random
import sys
from pathlib import Path

import asr_noise as AN
import build_gold as BG
import validate_gold as VG
from repair import repair_all
from schema import FactRecord
from transcript_utils import join_turns
from voicer import voice

HERE = Path(__file__).parent
SEED = 20261001
SPLITS = ("train", "dev", "eval")


def load_records(split: str) -> list[FactRecord]:
    return [FactRecord.model_validate(json.loads(l)) for l in (HERE / f"data/fact_records/{split}.jsonl").read_text().splitlines()]


def build_one(rec: FactRecord, seed: int = SEED, stress: tuple[int, int] | None = None) -> dict:
    rng = random.Random(f"{seed}:{rec.record_id}{':stress' if stress else ''}")
    turns = voice(rec, rng, stress)
    med_names = {m.id: m.name for m in rec.medications if m.name}
    names = {f: getattr(rec.identity, f).value.split()[0] for f in ("caller_name", "patient_name") if getattr(rec.identity, f).value}
    noisy, events = AN.apply_noise(turns, rng, rec.noise_plan, med_names, names)
    gold = BG.build_gold(rec, noisy, events)
    after = BG.apply_events(rec, events)
    issues = VG.check_transcript(after, noisy, {m.id: dict(id=m.id, name=m.name) for m in rec.medications}) + VG.check_gold(gold, after, noisy)
    # every drug-confusion target must have produced an event (otherwise gold and noise plan disagree)
    done = {e["fact_id"] for e in events if e["kind"] == "drug_confusion"}
    for fid in rec.noise_plan.get("drug_confusion_targets", []):
        if fid in med_names and fid not in done:
            issues.append(dict(id="N1-confusion-not-applied", record_id=rec.record_id, detail=fid))
    return dict(rec=rec, turns=noisy, events=events, gold=gold, target=BG.to_target(gold), issues=issues,
                extra_flags=VG.extra_rule_flags(gold, noisy))


def build_all(seed: int = SEED, limit: int | None = None) -> tuple[dict[str, list[dict]], dict]:
    raw = {s: load_records(s) for s in SPLITS}
    flat, stats = repair_all([r for s in SPLITS for r in raw[s]])
    it = iter(flat)
    out: dict[str, list[dict]] = {}
    for s in SPLITS:
        recs = [next(it) for _ in raw[s]]
        out[s] = [build_one(r, seed) for r in (recs[:limit] if limit else recs)]
    return out, stats


def summarize_issues(out: dict[str, list[dict]]) -> collections.Counter:
    c: collections.Counter = collections.Counter()
    for rs in out.values():
        for r in rs:
            for i in r["issues"]:
                c[i["id"]] += 1
    return c


def _jl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n")


def write_all(seed: int = SEED, stress_n: int = 100, stress_k: tuple[int, int] = (60, 110)) -> dict:
    from prompts import sft_example
    out, st = build_all(seed)
    for split, rs in out.items():
        _jl(HERE / f"data/transcripts/{split}.jsonl", [dict(record_id=r["rec"].record_id, category=r["rec"].category, subtype=r["rec"].subtype,
            agency=r["rec"].agency, transcript=join_turns(r["turns"]), n_turns=len(r["turns"]),
            turns=[dict(id=t.id, speaker=t.speaker, text=t.text, fact_ids=sorted(t.fact_ids)) for t in r["turns"]],
            noise_events=r["events"]) for r in rs])
        _jl(HERE / f"data/gold/{split}_gold.jsonl", [dict(r["gold"], summary_text=BG.render_summary(r["target"], r["rec"].call_timestamp_utc)) for r in rs])
        if split != "eval":
            _jl(HERE / f"data/sft/{split}.jsonl", [sft_example(r["turns"], r["target"], r["rec"].agency,
                dict(record_id=r["rec"].record_id, category=r["rec"].category)) for r in rs])
    # real-length slice: same eval facts, long-call chatter -> latency + long-context faithfulness
    base = [r["rec"] for r in out["eval"] if not r["gold"]["not_applicable"]][:stress_n]
    stress = [build_one(r, seed, stress=stress_k) for r in base]
    _jl(HERE / "data/transcripts/eval_long.jsonl", [dict(record_id=r["rec"].record_id + "_long", transcript=join_turns(r["turns"]), n_turns=len(r["turns"]),
        turns=[dict(id=t.id, speaker=t.speaker, text=t.text, fact_ids=sorted(t.fact_ids)) for t in r["turns"]]) for r in stress])
    _jl(HERE / "data/gold/eval_long_gold.jsonl", [dict(r["gold"], record_id=r["rec"].record_id + "_long") for r in stress])
    out["eval_long"] = stress
    return dict(out=out, repair=st)


def sha_sums() -> str:
    lines = []
    for p in sorted((HERE / "data").rglob("*")):
        if p.is_file() and p.suffix in (".jsonl", ".json", ".csv", ".md") and "sft" in p.parts or p.parent.name in ("transcripts", "gold", "fact_records"):
            if p.is_file():
                lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(HERE)}")
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


if __name__ == "__main__":
    res = write_all()
    out = res["out"]
    c = summarize_issues(out)
    print("repair:", res["repair"])
    print("validator issues:", dict(c) or "none")
    print("sha256 of all outputs:", sha_sums())
