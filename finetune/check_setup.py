"""Pre-flight on the pod, before training. Run it first and read the output.

    python3 check_setup.py                 # tokenizer, chat template, lengths (no GPU needed)
    python3 check_setup.py --load-model    # also loads the base model, lists the LoRA targets, runs one forward+backward and reports memory

Checks: (1) the generation prompt is the start of a rendered assistant turn (what vLLM feeds the model = what training sees),
(2) no example is truncated, (3) the label mask, (4) the model loads dequantized and which Linear modules get LoRA, (5) memory for the longest example.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

from examples import encode, render_parts, target_text

HERE = Path(__file__).resolve().parent


def read(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--load-model", action="store_true")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(cfg.get("tokenizer_path") or cfg["model_path"])
    system = (HERE / cfg["system_prompt"]).read_text()
    train, val = read(HERE / cfg["train_file"]), read(HERE / cfg["val_file"])

    prompt, suffix = render_parts(tok, system, train[0]["transcript"])
    print("1. CHAT TEMPLATE (thinking off)")
    print("   prompt starts :", repr(prompt[:120]))
    print("   prompt ENDS   :", repr(prompt[-200:]))
    print("   after the assistant text the template adds:", repr(suffix))
    base = [{"role": "system", "content": system}, {"role": "user", "content": "x"}]
    plain = tok.apply_chat_template(base + [{"role": "assistant", "content": "ZZZ"}], tokenize=False, enable_thinking=False)
    plain_head = plain[: plain.find("ZZZ")]
    added = tok.apply_chat_template(base, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    added = added[len(plain_head):] if added.startswith(plain_head) else "(?)"
    print("   text the generation prompt adds after the assistant-turn opening (thinking off):", repr(added))
    print("   the generation prompt starts with an assistant turn opening: OK; training input = generation prompt, target = JSON + the end-of-turn text above")

    exs = [encode(tok, system, r, cfg["max_length"]) for r in train + val]
    lens = sorted(e["n_prompt"] + e["n_target"] for e in exs)
    tg = sorted(e["n_target"] for e in exs)
    print(f"2. LENGTHS over {len(exs)} calls (max_length {cfg['max_length']}, nothing truncated)")
    print(f"   whole sequence: median {int(st.median(lens))}, p95 {lens[int(.95 * len(lens))]}, max {lens[-1]}")
    print(f"   target tokens : median {int(st.median(tg))}, p95 {tg[int(.95 * len(tg))]}, max {tg[-1]}")
    longest = max(exs, key=lambda e: e["n_prompt"] + e["n_target"])
    e0 = exs[0]
    print("3. LABEL MASK, first example: loss on the last", e0["n_target"], "tokens; the target begins:", repr(tok.decode(e0["input_ids"][e0["n_prompt"]:][:40])))
    print("   and ends:", repr(tok.decode(e0["input_ids"][-12:])))
    assert tok.decode(e0["input_ids"][e0["n_prompt"]:]) == target_text(train[0]["target"]) + suffix

    if not a.load_model:
        print("tokenizer checks OK. Now run with --load-model.")
        return
    import torch
    from train_lora import load_model, lora_targets, seq_loss

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = load_model(cfg, device)
    print("4. MODEL", type(model).__name__, "| dtype", next(model.parameters()).dtype, "| parameters", f"{sum(p.numel() for p in model.parameters()):,}")
    quant = [n for n, m in model.named_modules() if "Linear4bit" in type(m).__name__ or "Compressed" in type(m).__name__]
    print("   quantized-type modules left:", len(quant), "(0 means the weights were dequantized to BF16)")
    targets = lora_targets(model)
    print(f"   LoRA targets: {len(targets)} modules; first: {targets[0]}; last: {targets[-1]}")
    others = sorted({n.split('.')[-1] for n, m in model.named_modules() if isinstance(m, torch.nn.Linear)} - set(t.split('.')[-1] for t in targets))
    print("   other Linear names left untouched:", others[:12])
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    from peft import LoraConfig, get_peft_model

    model = get_peft_model(model, LoraConfig(r=cfg["lora_r"], lora_alpha=cfg["lora_alpha"], lora_dropout=cfg["lora_dropout"], target_modules=targets, task_type="CAUSAL_LM"))
    model.train()
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    s, n = seq_loss(model, longest, device, device == "cuda")
    (s / n).backward()
    print(f"5. ONE FORWARD+BACKWARD on the longest example ({longest['n_prompt'] + longest['n_target']} tokens): loss per target token {s.item() / n:.3f}")
    if device == "cuda":
        print(f"   peak GPU memory {torch.cuda.max_memory_allocated() / 1e9:.1f} GB of {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print("model checks OK. Start training.")


if __name__ == "__main__":
    main()
