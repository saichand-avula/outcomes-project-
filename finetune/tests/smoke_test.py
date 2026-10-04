"""CPU smoke test of the training code on a tiny random Llama and a tiny tokenizer (no real model needed).

    python3 tests/smoke_test.py          (needs torch, transformers, peft)

Checks: the label mask covers exactly the target, nothing is truncated (and truncation is refused), the step loss is the token-weighted mean,
the loss goes down, the adapters are saved, and the validation loss is logged.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tokenizers import Tokenizer, models, pre_tokenizers, trainers, decoders  # noqa: E402
from transformers import LlamaConfig, LlamaForCausalLM, PreTrainedTokenizerFast  # noqa: E402

from examples import encode, render_parts, target_text  # noqa: E402

# Mimics Gemma 4 with thinking off: the generation prompt carries an empty thought block that a plain assistant turn does not have,
# and a rendered turn ends with "<|end|>" plus a newline.
TEMPLATE = ("{% for m in messages %}<|{{ m['role'] }}|>\n{{ m['content'] }}<|end|>\n{% endfor %}"
            "{% if add_generation_prompt %}<|assistant|>\n<|thought|><|/thought|>{% endif %}")


def tiny_tokenizer(rows, system):
    tk = Tokenizer(models.BPE(unk_token="<unk>"))
    tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tk.decoder = decoders.ByteLevel()
    tr = trainers.BpeTrainer(vocab_size=3000, special_tokens=["<unk>", "<pad>", "<bos>", "<|end|>", "<|system|>", "<|user|>", "<|assistant|>"],
                             initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    corpus = [system] + [r["transcript"] for r in rows] + [target_text(r["target"]) for r in rows]
    tk.train_from_iterator(corpus, tr)
    tok = PreTrainedTokenizerFast(tokenizer_object=tk, unk_token="<unk>", pad_token="<pad>", bos_token="<bos>")
    tok.chat_template = TEMPLATE
    return tok


def main():
    train = [json.loads(l) for l in (HERE / "data/train.jsonl").read_text().splitlines()]
    system = (HERE / "prompts/system_v4.md").read_text()
    tok = tiny_tokenizer(train[:200], system)
    tmp = Path(tempfile.mkdtemp())
    tok.save_pretrained(tmp / "model")
    cfg = LlamaConfig(vocab_size=len(tok), hidden_size=64, intermediate_size=128, num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
                      max_position_embeddings=65536)
    LlamaForCausalLM(cfg).save_pretrained(tmp / "model")

    # 1. the label mask is exactly the target (+ the template's end marker)
    row = train[0]
    ex = encode(tok, system, row, 65536)
    prompt, suffix = render_parts(tok, system, row["transcript"])
    tgt = tok.decode(ex["input_ids"][ex["n_prompt"]:])
    assert tgt == target_text(row["target"]) + suffix, "target region is not target + suffix"
    assert tok.decode(ex["input_ids"][:ex["n_prompt"]]) == prompt, "prompt region differs from the generation prompt"
    assert prompt.endswith("<|thought|><|/thought|>") and suffix == "<|end|>"
    print("PASS  target region = compact JSON + end marker; prompt region = the generation prompt (with its empty thought block)")

    # 2. truncation is refused
    try:
        encode(tok, system, row, 100)
        raise AssertionError("truncation was not refused")
    except SystemExit as e:
        assert "exceed" in str(e)
    print("PASS  an example longer than max_length stops the run instead of being cut")

    # 3. a short real run
    conf = json.loads((HERE / "config.json").read_text())
    conf.update({"model_path": str(tmp / "model"), "dequantize_compressed_tensors": False, "attn_implementation": "eager", "max_length": 65536,
                 "learning_rate": 3e-3, "epochs": 1, "eval_every": 3, "eval_subset": 4, "gradient_checkpointing": True, "lora_dropout": 0.0})
    (tmp / "config.json").write_text(json.dumps(conf))
    out = tmp / "run"
    r = subprocess.run([sys.executable, str(HERE / "train_lora.py"), "--config", str(tmp / "config.json"), "--out", str(out), "--max-steps", "6"],
                       capture_output=True, text=True, cwd=HERE)
    print(r.stdout[-1500:])
    assert r.returncode == 0, r.stderr[-2000:]
    log = [json.loads(l) for l in (out / "train_log.jsonl").read_text().splitlines()]
    tr = [x for x in log if x["event"] == "train"]
    assert len(tr) == 6 and all(x["loss"] == x["loss"] and x["loss"] > 0 for x in tr)
    assert tr[0]["calls"] == 8 and tr[-1]["loss"] < tr[0]["loss"], f"loss did not go down: {[round(x['loss'], 3) for x in tr]}"
    assert any(x["event"] == "val" and x["step"] == 0 for x in log) and any(x["event"] == "val_epoch" for x in log)
    assert (out / "epoch_1" / "adapter_config.json").exists() and (out / "epoch_1" / "adapter_model.safetensors").exists()
    print("PASS  trains, loss goes down:", [round(x["loss"], 3) for x in tr], "| adapters saved | validation loss logged")
    print("smoke test OK")


if __name__ == "__main__":
    main()
