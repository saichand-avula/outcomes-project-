# Fine-tuning (LoRA) of the clinical summarizer

Self-contained: upload this folder to `/workspace/finetune` on the pod. It trains one LoRA adapter on the 500 training calls, saves it after every epoch, and gives scripts to serve each epoch and score it with the frozen evaluation pipeline (`../pipeline`). Design and the reasons for every choice: `architecture.md` §4.

## Result of the run that was made (`runs/ft1`)

One run: 189 steps, 2.9 hours on the L40S, peak memory 36.2 GB. Validation loss 0.189 / 0.167 / 0.171 after epochs 1 / 2 / 3 (0.635 before training). **Epoch 3 is the adapter to use** (`runs/ft1/epoch_3/`): on the evaluation pipeline it is equal or better than epoch 2 almost everywhere (safe-pass rate G1, calls with no rule error and judged faithful: 92% vs 91%; calls with every checklist item covered F3: 68% vs 57%; medication names found H3: 89% vs 83%) even though its validation loss is a little higher. Epoch 1 was evaluated too and is clearly weaker (safe-pass rate 68%, critical-fact accuracy 73.3%, and 3 of 100 answers ran into the token limit). Comparison with the base model: safe-pass rate (G1) 60% → 92%, critical-fact accuracy against the hand-written gold (H19) 56.8% → 81.6%, p50/p95 total response time 14.0 s / 19.1 s, time to first token p50 0.17 s. The 95% and 15 s targets were not reached; see [../REPORT.md](../REPORT.md) for why, and §10 there for what to change before training again.

Files in `runs/ft1/`: `epoch_{1,2,3}/` (`adapter_config.json`, `adapter_model.safetensors`, about 250 MB each; the `.safetensors` files are git-ignored, back them up), `train_log.jsonl` (every step), `train_ft1.log` (the console output), `run_info.json` (settings and hashes of the data and prompt).

**A bug to avoid:** the JSON schema used for constrained decoding at serving time must list keys in the same order as the training targets. vLLM forces schema order; with the wrong order the model lost the names and doses of facts. The schema in `../pipeline/pl/schema.py` now follows the training-target order (5% of facts still conflict, because the gold itself mixes two orders for a few key pairs).

## How many parameters LoRA adds

Counted from the saved adapter file (`runs/ft1/epoch_3/adapter_model.safetensors`, 656 tensors), not estimated.

| | |
|---|---|
| **Trainable parameters added by LoRA** | **65,568,768** (65.6 million) |
| Base weights they sit on (the 328 adapted linear layers) | 10,899,947,520 (10.90 billion) |
| Increase on the adapted weights | **+0.60%** |
| Increase on the nominal "12B" model | about +0.55% (the exact total of the model, with embeddings and the vision and audio parts, was not counted; those parts get no adapter) |
| Base weights changed during training | none (the base is frozen) |
| Adapter file size | 262 MB each (stored in 32-bit floats: 65.6 M × 4 bytes). Three adapters (one per epoch) = about 787 MB |
| Rank / alpha / dropout | 16 / 32 / 0.05 |
| Layers | 48 text layers; 328 adapted linear layers |

Each adapted layer with input size `in` and output size `out` adds `16 × (in + out)` parameters (two small matrices, 16 × in and out × 16). By layer type:

| Layer type | Count | Parameters added |
|---|---|---|
| `down_proj` | 48 | 14,745,600 |
| `gate_proj` | 48 | 14,745,600 |
| `up_proj` | 48 | 14,745,600 |
| `q_proj` | 48 | 6,619,136 |
| `o_proj` | 48 | 6,619,136 |
| `k_proj` | 48 | 4,325,376 |
| `v_proj` | 40 (8 layers have no separate value projection) | 3,768,320 |
| **Total** | **328** | **65,568,768** |

At serving time the adapter is **not merged** into the 4-bit weights (merging would need re-quantising). vLLM adds its small matrix product to each adapted layer on the fly. We did not isolate the speed cost of that: the timed calls decoded about 63 tokens/s with the adapter against about 73 for the base model, but that difference also contains the prompt processing, which is spread over fewer output tokens when the answer is shorter (REPORT §6.3).

## The comparison it is built for

| | Baseline `base_v4_s2` | Fine-tuned |
|---|---|---|
| System prompt | `system_v4.md` | `system_v4.md` (same file, copied here) |
| User message | `CALL TRANSCRIPT` + numbered turns | the same (`textio.py` is a copy of `pipeline/pl/transcript.py`) |
| Chat template | `enable_thinking=False` | the same |
| Decoding | greedy, JSON-schema constrained | the same |
| Weights | base | base + LoRA adapter |

Only the weights differ. The judge is always the base model.

## What is trained

- **Data:** `data/train.jsonl` (500 calls). `data/val.jsonl` (100 calls) is only used for the validation loss and, through the pipeline, for the final numbers. There is no separate test split (see limitation below).
- **Target:** the gold summary as compact JSON (no spaces), followed by whatever the chat template puts after an assistant message. Loss is computed on these tokens only.
- **LoRA:** r = 16, alpha = 32, dropout 0.05, on q/k/v/o/gate/up/down of every text layer (vision, audio and embeddings are skipped). Learning rate 2e-4, cosine, 3% warmup, 3 epochs, gradient clipping 1.0.
- **Batches:** `data/batch_schedule.json` (stratified by length and category, reshuffled each epoch). One optimizer step = 8 calls (the last one of an epoch has 4), micro-batch 1.
- **Loss normalisation:** the summed token loss of a step divided by the step's number of target tokens, so a 5K-token call counts in proportion to its target tokens, not as one average.
- **Length:** `max_length` 8192; any longer example stops the run (nothing is ever cut).
- **Base:** `gemma-4-12B-qat-w4a16-ct` loaded dequantized to BF16 (`CompressedTensorsConfig(dequantize=True)`), so the frozen weights are the ones vLLM serves.

## Monitoring

`runs/<name>/train_log.jsonl` has one line per event:
- `train`: step, epoch, loss, lr, grad_norm, target_tokens, elapsed_s, peak_mem_gb.
- `val` at step 0 (the untouched model, i.e. the starting loss) and every 20 steps on a fixed 25-call subset.
- `val_epoch`: validation loss on all 100 calls at the end of each epoch.

Read it like this: training loss should fall quickly in the first 10-20 steps. If the validation loss starts rising while the training loss keeps falling, the model is memorising the 500 calls (the validation calls come from two agencies the training set never sees, so this is a fair generalisation check). **The validation loss does not choose the checkpoint**; the pipeline does (critical-fact accuracy and the other rows), because loss and output quality do not track each other well.

## Run it on the pod

1. **Free the GPU.** Stop vLLM (Ctrl+C in its terminal). Training and the vLLM server cannot share the 46 GB.
2. **Environment** (same venv as vLLM; adds only the LoRA library):
   ```bash
   source /workspace/venv-vllm/bin/activate
   pip install --no-deps peft accelerate psutil
   cd /workspace/finetune
   ```
3. **Pre-flight:**
   ```bash
   python3 check_setup.py
   python3 check_setup.py --load-model
   ```
   The first checks the chat template, the label mask and the lengths. The second loads the model, lists the LoRA target modules, runs one forward and backward on the longest call, and reports the peak GPU memory.
4. **Train:**
   ```bash
   nohup python3 train_lora.py --out runs/ft1 > train_ft1.log 2>&1 &
   tail -f train_ft1.log
   ```
   189 steps in total (63 per epoch). The first steps show the seconds per step in `elapsed_s`, which gives the real total time.
5. **Evaluate every epoch** (after training has finished and the GPU is free):
   ```bash
   bash scripts/serve_adapters.sh runs/ft1        # leave running; serves the base as `gemma` and the adapters as ft1, ft2, ft3
   # in a second terminal
   bash scripts/eval_adapter.sh ft1 _s2
   bash scripts/eval_adapter.sh ft2 _s2
   bash scripts/eval_adapter.sh ft3 _s2
   ```
   `eval_adapter.sh ft3 _s2` runs the base model (once) and adapter 3 with the same settings and prints their matrix, `outputs/matrix_base_v4_s2_vs_finetuned_epoch3_s2.md`. Timing: `run_pipeline.py latency` (see `../pipeline/README.md`). **Do not** start the server with the n-gram speculative-decoding flag: it made generation about 1.7 times slower (REPORT §7.5).

## Tests

`python3 tests/smoke_test.py` (needs torch, transformers, peft, tokenizers) trains a tiny random Llama on the real data for 6 steps and checks that the label mask is exactly the target, that over-long examples are refused, that the loss goes down, and that adapters and the validation log are written. It passed on the Mac. What it cannot check, and `check_setup.py --load-model` does on the pod: the real Gemma template, the dequantized load, which modules get LoRA, and memory.

## Limitations

- Validation is used three ways: validation loss for monitoring, the choice among three epoch checkpoints (by critical-fact accuracy, H19), and the final numbers. With no separate test split the reported validation scores are slightly optimistic. The choice is only among three checkpoints, so the effect should be small; the report says so.
- An adapter trained on a dequantized BF16 copy is served on the quantized W4A16 model. `architecture.md` §4.2 has an agreement check (training framework against vLLM on 20 validation calls); until it is done, treat the vLLM numbers as the truth, because that is what the pipeline measures.
- The prompt is 2,010 tokens on every example, so each step is slower than with a short prompt. This was chosen on purpose to keep the comparison strict.
