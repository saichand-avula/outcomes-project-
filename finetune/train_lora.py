"""LoRA fine-tuning of the summarizer (architecture.md section 4).

    python3 train_lora.py --config config.json --out runs/ft1

What it does, step by step:
  * builds every example with examples.encode (same template and prompt as serving) and asserts nothing is truncated;
  * follows data/batch_schedule.json: one optimizer step = the calls listed for that step (8, one step of 4), micro-batch 1;
  * loss = summed token cross-entropy over the target tokens of the whole step / the step's number of target tokens
    (correct accumulation: long calls are not under-weighted);
  * validation loss (no gradients, same formula) on a fixed subset every `eval_every` steps and on all validation calls at each epoch end;
  * saves the adapter after every epoch (runs/<name>/epoch_N) and a log (train_log.jsonl) you can plot.
The checkpoint to use is chosen by the evaluation pipeline (H19), not by loss.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

import torch
import torch.nn.functional as F

from examples import encode

HERE = Path(__file__).resolve().parent
LINEARS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")
SKIP = ("vision", "audio", "multi_modal", "mm_", "embed")


def read(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def load_model(cfg, device):
    from transformers import AutoModelForCausalLM

    kw = {"torch_dtype": torch.bfloat16 if device == "cuda" else torch.float32, "attn_implementation": cfg.get("attn_implementation", "sdpa")}
    if cfg.get("dequantize_compressed_tensors"):
        from transformers.utils.quantization_config import CompressedTensorsConfig
        try:
            kw["quantization_config"] = CompressedTensorsConfig(dequantize=True)
        except TypeError:
            kw["quantization_config"] = CompressedTensorsConfig(run_compressed=False)
    if device == "cuda":
        kw["device_map"] = {"": 0}
    model = AutoModelForCausalLM.from_pretrained(cfg["model_path"], **kw)
    return model


def lora_targets(model) -> list[str]:
    names = [n for n, m in model.named_modules() if isinstance(m, torch.nn.Linear) and n.split(".")[-1] in LINEARS and not any(s in n for s in SKIP)]
    if not names:
        raise SystemExit("no q/k/v/o/gate/up/down Linear modules found for LoRA; run check_setup.py --load-model to list the Linear modules")
    return names


def seq_loss(model, ex, device, amp):
    """-> (summed cross-entropy over the target tokens, number of target tokens) for one example."""
    ids = torch.tensor([ex["input_ids"]], device=device)
    n = ex["n_target"]
    with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=amp):
        out = model(input_ids=ids, logits_to_keep=n + 1, use_cache=False)
    logits = out.logits[0, :-1].float()  # position p predicts token p+1; the last kept position predicts nothing
    labels = ids[0, -n:]
    return F.cross_entropy(logits, labels, reduction="sum"), n


@torch.no_grad()
def evaluate(model, exs, device, amp):
    model.eval()
    tot, cnt = 0.0, 0
    for ex in exs:
        s, n = seq_loss(model, ex, device, amp)
        tot += s.item()
        cnt += n
    model.train()
    return tot / max(cnt, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-steps", type=int, default=0, help="stop after this many steps (smoke tests)")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    amp = device == "cuda"
    random.seed(cfg["seed"]); torch.manual_seed(cfg["seed"])

    from transformers import AutoTokenizer
    from peft import LoraConfig, get_peft_model

    tok = AutoTokenizer.from_pretrained(cfg.get("tokenizer_path") or cfg["model_path"])
    system = (HERE / cfg["system_prompt"]).read_text()
    train_rows, val_rows = read(HERE / cfg["train_file"]), read(HERE / cfg["val_file"])
    schedule = json.loads((HERE / cfg["schedule_file"]).read_text())
    train = {r["id"]: encode(tok, system, r, cfg["max_length"]) for r in train_rows}
    val = [encode(tok, system, r, cfg["max_length"]) for r in val_rows]
    sub = val[:: max(1, len(val) // cfg["eval_subset"])][: cfg["eval_subset"]]
    print(f"encoded {len(train)} train and {len(val)} validation calls, no truncation; longest {max(e['input_ids'].__len__() for e in list(train.values()) + val)} tokens; "
          f"target tokens per call: median {sorted(e['n_target'] for e in train.values())[len(train) // 2]}")

    model = load_model(cfg, device)
    targets = lora_targets(model)
    model.config.use_cache = False
    if cfg.get("gradient_checkpointing", True):
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    lcfg = LoraConfig(r=cfg["lora_r"], lora_alpha=cfg["lora_alpha"], lora_dropout=cfg["lora_dropout"], target_modules=targets, bias="none", task_type="CAUSAL_LM")
    model = get_peft_model(model, lcfg)
    model.train()
    trainable = [p for p in model.parameters() if p.requires_grad]
    print(f"LoRA r={cfg['lora_r']} alpha={cfg['lora_alpha']} on {len(targets)} modules; trainable parameters {sum(p.numel() for p in trainable):,}")

    epochs = cfg["epochs"]
    steps_per_epoch = len(schedule["epoch_1"])
    total = steps_per_epoch * epochs
    warm = max(1, int(round(cfg["warmup_ratio"] * total)))
    opt = torch.optim.AdamW(trainable, lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"], betas=(0.9, 0.999))
    lr_at = lambda s: cfg["learning_rate"] * ((s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, total - warm))))  # noqa: E731

    (out / "run_info.json").write_text(json.dumps({
        "config": cfg, "lora_target_modules": len(targets), "total_steps": total, "torch": torch.__version__,
        "system_prompt_sha": sha(HERE / cfg["system_prompt"]), "train_sha": sha(HERE / cfg["train_file"]), "val_sha": sha(HERE / cfg["val_file"]),
        "schedule_sha": sha(HERE / cfg["schedule_file"])}, indent=1))
    log = open(out / "train_log.jsonl", "a")

    def emit(rec):
        log.write(json.dumps(rec) + "\n"); log.flush()
        print("  " + " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}" for k, v in rec.items()), flush=True)

    emit({"event": "val", "step": 0, "epoch": 0, "val_loss_subset": evaluate(model, sub, device, amp)})  # before any update: the loss of the untouched model
    step, t0 = 0, time.time()
    for epoch in range(1, epochs + 1):
        for ids in schedule[f"epoch_{epoch}"]:
            exs = [train[i] for i in ids]
            n_tok = sum(e["n_target"] for e in exs)
            for g in opt.param_groups:
                g["lr"] = lr_at(step)
            step_loss = 0.0
            for ex in exs:
                s, _ = seq_loss(model, ex, device, amp)
                (s / n_tok).backward()  # every call contributes in proportion to its number of target tokens
                step_loss += s.item()
            gn = torch.nn.utils.clip_grad_norm_(trainable, cfg["max_grad_norm"]).item()
            opt.step(); opt.zero_grad(set_to_none=True)
            step += 1
            rec = {"event": "train", "step": step, "epoch": epoch, "loss": step_loss / n_tok, "lr": lr_at(step - 1), "grad_norm": gn, "calls": len(exs),
                   "target_tokens": n_tok, "elapsed_s": time.time() - t0}
            if device == "cuda":
                rec["peak_mem_gb"] = torch.cuda.max_memory_allocated() / 1e9
            emit(rec)
            if step % cfg["eval_every"] == 0 and step % steps_per_epoch != 0:
                emit({"event": "val", "step": step, "epoch": epoch, "val_loss_subset": evaluate(model, sub, device, amp)})
            if a.max_steps and step >= a.max_steps:
                break
        vl = evaluate(model, val, device, amp)
        emit({"event": "val_epoch", "step": step, "epoch": epoch, "val_loss": vl})
        model.save_pretrained(out / f"epoch_{epoch}")
        print(f"saved {out / f'epoch_{epoch}'}")
        if a.max_steps and step >= a.max_steps:
            break
    print(f"done: {step} steps in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
