"""Exact token lengths with the model's own tokenizer (run on the pod; needs `transformers`).

    python3 dev/token_lengths.py --model /workspace/models/gemma-4-12b-it-qat-w4a16-ct --prompt prompts/system_v4.md

Reports, for training (prompt + transcript + target) and for serving (prompt + transcript, plus the longest output), the median, p95 and max,
so max_model_len and the training sequence length can be chosen from measurements.
"""
import argparse
import json
import statistics as st
from pathlib import Path

from transformers import AutoTokenizer

HERE = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--prompt", default=str(HERE / "prompts" / "system_v4.md"))
ap.add_argument("--cases", default=str(HERE / "data" / "val_cases.jsonl"))
ap.add_argument("--train", default=str(HERE / "data" / "train_cases.jsonl"))
a = ap.parse_args()
tok = AutoTokenizer.from_pretrained(a.model)
n = lambda s: len(tok(s, add_special_tokens=False)["input_ids"])  # noqa: E731
sys_n = n(Path(a.prompt).read_text())
print(f"system prompt: {sys_n} tokens")
for name, path in (("validation", a.cases), ("train", a.train)):
    if not Path(path).exists():
        continue
    rows = [json.loads(l) for l in open(path)]
    ctx = sorted(sys_n + n(r["transcript"]) for r in rows)
    out = sorted(n(json.dumps(r["gold_target"], separators=(",", ":"))) for r in rows if r.get("gold_target"))
    full = sorted(c + o for c, o in zip(ctx, sorted(out))) if len(out) == len(ctx) else []
    q = lambda xs, p: xs[min(len(xs) - 1, int(p * len(xs)))]  # noqa: E731
    print(f"{name} ({len(rows)} calls)")
    print(f"  prompt+transcript : median {int(st.median(ctx))}, p95 {q(ctx, .95)}, max {ctx[-1]}")
    print(f"  gold output       : median {int(st.median(out))}, p95 {q(out, .95)}, max {out[-1]}")
    print(f"  serving worst case (longest context + longest gold output): {ctx[-1] + out[-1]}")
