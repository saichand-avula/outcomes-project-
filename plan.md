# Execution Plan — Clinical Summary LLM (5 days)

Oct 4, 2026 · companion to [architecture.md](architecture.md), which holds the design rationale and evidence. This file covers what gets built, in what order, and when each step counts as done.

## 0. Progress

**State on 4 Oct 2026: everything except the demo video and the submission zip is built and run. The 95% and 15 s targets were not reached.** Start with [REPORT.md](REPORT.md).

- **Data:** 500 train + 100 validation calls, hand-authored and validated (0 errors, 0 warnings, no cross-split leaks). `data/dataset_overview.xlsx`.
- **Judge:** base Gemma validated on 90 hand-edited summaries (50 to tune, 40 fresh with frozen prompts): faithfulness kappa 1.00 on the fresh set, completeness 0.61, calibration 0.55 (`llm_judge/`).
- **Evaluation pipeline:** rules V1-V16, quote repair, frozen judge, gold comparison, one matrix (`pipeline/`). Baseline prompt iterated v1 → v4 and frozen; every run's outputs are saved in `pipeline/outputs/`.
- **Fine-tuning:** one LoRA run (r16, 3 epochs, 189 steps, 2.9 h on the L40S); adapters in `finetune/runs/ft1/` (not in git). **Epoch 3 chosen.**
- **Result (100 validation calls):** safe-pass G1 60% → **92%**, Critical-Fact Accuracy H19 56.8% → **81.6%**, latency p50 14.0 s / p95 19.1 s. **Not reached:** 95% on G1 and H19, p95 < 15 s.
- **Demo UI:** `app/` (replay mode works without a GPU).
- **Medications got worse with fine-tuning** (name found 93.3% → 89.3%, name + dose 82.7% → 74.7%): 5 genuine losses of 19 lost slots, analysed in REPORT §8.1. **Time to first token** (p50 0.17 s, p95 0.64 s) was measured at the end by streaming (`run_pipeline.py latency`). **Epoch 1** was evaluated at the end too: clearly weaker (G1 68%, H19 73.3%, 3 runaway answers), so epoch 3 stays.
- **Not done:** the planned sweeps (learning rate, rank), the adapter agreement check, the Not-Applicable gate / candidates table / retry in the production path, the demo video. See the status tables below and REPORT §9.

## 1. Fixed decisions

| Item | Decision |
|---|---|
| Model | `google/gemma-4-12B-it-qat-w4a16-ct`, vLLM, greedy, thinking off |
| GPU | RunPod, 1× L40S 46,068 MiB, CUDA 13.2 |
| Data | Claude-authored; **500 train / 100 validation**; no separate evaluation split; the 5 provided real calls are not used as data |
| Length mix | 72% short/normal · 12% medium · 16% long (train 360/60/80; validation 73/11/16). Minimums: short ≥ 65 lines and 4,500–9,000 chars; medium ≥ 85 lines and 7,500–12,500; long ≥ 105 lines and 10,500–18,000 (Not-Applicable calls exempt) |
| Output | JSON → deterministic renderer → exact reference format |
| SFT format | `{id, transcript, call_timestamp_utc, target}`; system prompt in `prompts/system_vN.md`, assembled at train time. **Decision: train and evaluate the fine-tuned model with `system_v4.md`, the same prompt as the baseline (same input, only the weights differ)** |
| Fine-tuning | BF16 LoRA r16 / α32 on all text-layer linear projections; ct checkpoint dequantized |
| Headline | Critical-Fact Accuracy ≥ 95% + release gates; latency overall p50, overall p95, long-call p95 |

## 2. Data coverage plan (diversity is planned, not random)

Every call starts as a one-line `blueprint:` brief tagged with its axis values, inside its authoring YAML. The category quotas below were met exactly; `code/data/coverage.py` reports the rest.

### 2.1 Primary categories

| Category | Train | Validation | Subtypes |
|---|---|---|---|
| Routine | 80 | 16 | symptom update · general question · clinical visit scheduling · post-visit follow-up |
| Ambiguous | 60 | 12 | caller unsure · contradictions · self-correction · vague timeline · second-hand report |
| ASR-error heavy | 60 | 12 | garbled drug · garbled name/DOB · garbled numbers/doses · speaker-label errors |
| Medication | 90 | 18 | dose/timing question · missed or double dose · side effect · route/crushing · liquid concentration · patch · stopped meds · new-med request |
| Supply request | 60 | 12 | med refill · DME (oxygen, bed, commode, wheelchair) · wound/catheter/incontinence supplies · delivery timing |
| High-risk | 100 | 20 | uncontrolled symptom · medication concern · suicidal statement · breathing concern · escalation request · clinical emergencies (sepsis, GI bleed, head injury, overdose, suspected abuse) |
| Not Applicable | 50 | 10 | wrong number · disconnected before content · billing/admin only · test/silent call · non-clinical scheduling · sales/robocall · survey · job inquiry · records request |
| **Total** | **500** | **100** | |

### 2.2 Secondary axes (minimum share of non-NA calls, per split)

| Axis | Values and minimum quotas |
|---|---|
| Caller | patient self ≥ 10% · spouse/partner ≥ 15% · adult child ≥ 20% · parent of minor ≥ 5% · other family ≥ 5% · friend/neighbor ≥ 3% · paid caregiver/aide ≥ 5% · facility staff (ALF/SNF nurse) ≥ 5% · call-center transfer ≥ 3% |
| Patient age | pediatric ≥ 6% · 18–64 ≥ 20% · 65–89 ≥ 40% · 90+ ≥ 5% |
| Agency type | hospice · home health · home care · palliative · pediatric home care (each ≥ 8%); 2 agency names held out for validation only |
| Clinical domain | ≥ 15 domains, each ≥ 3%: pain · dyspnea · agitation/delirium · anxiety/insomnia · nausea/vomiting · constipation/bowel · urinary/catheter · wound/skin · fever/infection · falls · bleeding · glucose · blood pressure · cough/URI · edema · intake/appetite · end-of-life changes · seizure |
| Identity patterns | name spelled out ≥ 15% · name drift ≥ 10% · DOB self-corrected ≥ 5% · phone confirmed from file ≥ 20% · phone not given ≥ 5% · identity unresolved at end ≥ 5% |
| Medication phenomena | garbled drug ≥ 10% of medication calls · chart-reading distractor ≥ 8% · PRN vs scheduled both present ≥ 20% · liquid mg/mL ≥ 8% · tall-man drug (LORazepam, HYDROmorphone, traMADol…) ≥ 15% |
| Action status | ≥ 1 nurse action in every non-NA call · planned ≥ 40% of actions · completed ≥ 15% · advised for the rest · trap phrasing ("I'll" / "I've" / "let me" / "I already") ≥ 20% of calls |
| Uncertainty | caller hedges ("I think", "maybe") ≥ 15% · contradiction or self-correction ≥ 8% |
| Negation / flag precision | pertinent negatives ≥ 40% · routine calls with negated risk phrases ("no trouble breathing") ≥ 15% · figurative risk language ("this pain is killing me") ≥ 3% · passive suicidal ideation inside the suicidal subtype ≥ 30% |
| Conversational noise | late answers ≥ 30% · split turns ≥ 30% · crosstalk to patient ≥ 10% · off-topic chatter ≥ 10% (mostly long calls) · speaker-label errors ≥ 5% |
| Multi-issue | ≥ 2 distinct concerns ≥ 25% (mostly medium/long) |

### 2.3 Authoring protocol (what was done, per call)

1. Write the one-line scenario brief (`blueprint:`) and tag its axis values.
2. Write the fact record (identity, assessment A#, response R#, education E#, risk flags F#).
3. Write the transcript in final, noisy form. Every turn carries its fact tags, and every noise event is logged (`turn`, `type`, `true_form`, `heard_form`, `fact_id`).
4. Write the gold JSON from the record + transcript + noise log (`turns: auto`; `postfix.py` fills turn numbers from verbatim quotes).
5. Run `validate_gold.py` (G1–G12 plus the cross-split leak check) and `coverage.py`; fix and re-run until 0 errors and 0 warnings.
6. Run `realism.py` against the 5 provided examples for surface statistics.
7. Run `compile.py` (JSONL, SFT rows, SHA256SUMS) and `build_workbook.py` (`data/dataset_overview.xlsx`).

Status: all 500 train and 100 validation calls are done (600 total, 0 errors, 0 warnings).

### 2.4 Leakage and freeze rules

- Names, DOBs and phones are unique across splits; phones use `NXX-555-0100…0199`. The validator fails on any collision.
- Validation holds out two agencies (Juniper Ridge Hospice, Northstar Home Health) that never appear in train.
- There is no separate evaluation split; Validation (100) is the held-out set.
- Near-duplicate check: a line-level scan found one shared generic sentence, and `code/data/dupcheck.py` (character 5-gram Jaccard, threshold 0.5) found a near-identical pharmacy-robocall pair (va-074 ~ tr-412, 0.45) that was rewritten; the closest pair is now 0.36.
- Data hashes are in `data/SHA256SUMS`.

## 3. Step-by-step roadmap

Data authoring is the critical path, so pipeline code and GPU work run in parallel with it.

| Day | Step | Deliverable | Done when |
|---|---|---|---|
| **1** | 1.1 Repo skeleton, JSON schema, renderer, `validate_gold.py`, `coverage.py`, `realism.py` | `code/` | Renderer reproduces the 5 reference summaries' structure from hand-made JSON |
| 1 | 1.2 GPU: install pinned vLLM, download checkpoint (record revision SHA), serve | `env/` | Serves; KV-cache size logged |
| 1 | 1.3 Chat-template check: render `enable_thinking=False`, inspect one raw generation | note in `env/` | SFT target prefix decided |
| 1 | 1.4 Scenario briefs (one-line `blueprint:` per call, inside each YAML) | `data/authoring/` | `coverage.py` passes |
| 1 | 1.5 ~~Real-5 hand annotation~~ dropped: the 5 provided calls are not used as data | — | — |
| 1 | 1.6 System prompt v1; baseline on the 5 provided examples | `prompts/system_v1.md` | 5/5 outputs parse |
| 2 | 2.1 Author validation 100 | `data/sft/val.jsonl` | Done: validator + coverage clean |
| 2 | 2.2 Validators V1–V16, NA gate, risk rules, defect-detection study | `pipeline/pl/`, `pipeline/run_pipeline.py selftest` | Done: 0 errors on all gold; study in `pipeline/README.md` |
| 2 | 2.3 Baseline on validation; prompt iteration; greedy vs sampling; thinking on vs off (50 calls) | `outputs/baseline_val/` | Prompt v_final frozen |
| 2–3 | 2.4 Author train 500 | `data/sft/train.jsonl` | Done: validator + coverage clean; hashed |
| **3** | 3.1 LoRA smoke test: 10 steps, peak memory, trainable-parameter count by module | log | Loss falls; peak < 42 GB |
| 3 | 3.2 Sweep A/B/C (overnight) | `adapters/` | 3 runs × up to 3 epoch checkpoints |
| 3 | 3.3 Held-out data: Validation 100 (already authored and validated; frozen + hashed) | `data/sft/val.jsonl` | Done; SHA256SUMS |
| 3 | 3.4 FastAPI + Gradio | `code/api/` | Provided example works through the UI |
| **4** | 4.1 Select winner on validation CFA (no increase in hallucinated critical values) | choice logged | — |
| 4 | 4.2 Adapter-in-vLLM check (20 validation, 3 restarts) | log | Within 1 pt; ≥ 95% identical across restarts; else r8 |
| 4 | 4.3 Validation 100: baseline vs fine-tuned, full metrics | `outputs/eval_reports/` | All metrics + CIs |
| 4 | 4.4 Latency runs; work down the optimization list (architecture §6.2) if p95 ≥ 15 s | `outputs/latency/` | p50 / p95 / long-call p95 for both systems |
| 4 | 4.5 Judge: validation done (mutation tests, 50 + 40 items, `llm_judge/`); run the frozen v5 judge on baseline and fine-tuned outputs | `outputs/judge/` | Scores reported with the validated scope |
| **5** | 5.1 Failure analysis, significance tests, figures | `outputs/failure_cases.md` | — |
| 5 | 5.2 `report.md`, README, reproduce one eval from a clean env | — | README steps run end-to-end |
| 5 | 5.3 Demo video (≤ 3 min), ZIP | `submission.zip` | Submitted |

### Status of each step (what really happened)

| Step | Status | Note |
|---|---|---|
| 1.1 Skeleton, schema, renderer, validators | Done | |
| 1.2 vLLM + checkpoint on the pod | Done | vLLM 0.30.0 needs `VLLM_USE_FLASHINFER_SAMPLER=0` |
| 1.3 Chat-template check | Done | Thinking off adds an empty thought block to the generation prompt; training uses it (`finetune/examples.py`) |
| 1.6 Prompt v1; baseline | Done, **changed** | v1 never defined formats (G1 7%); iterated to v4 and frozen. Baseline is the 100 validation calls, not the 5 provided examples |
| 2.1-2.4 Data (100 + 500) | Done | |
| 2.2 Validators, defect study | Done | `pipeline/` |
| 2.3 Prompt iteration; greedy vs sampling; thinking on/off | **Partly** | Prompt iteration done; greedy vs sampling and thinking on/off **not run** |
| 3.1 LoRA smoke test | Done | 2-step trial on the pod plus a CPU test of the code on a tiny model |
| 3.2 Sweep A/B/C | **Not done** | Only run A (r16, 2e-4) was trained |
| 3.4 FastAPI + Gradio | **Changed** | Built as `app/` with the Python standard library (no FastAPI, no Gradio) |
| 4.1 Select winner on validation CFA | Done | Epoch 3, on pipeline metrics (REPORT §7.7) |
| 4.2 Adapter-in-vLLM check | **Not done** | vLLM served and ran the adapter; the formal HF-versus-vLLM agreement check was not run |
| 4.3 Baseline vs fine-tuned, full metrics | Done | Intervals are Wilson bounds and a paired sign test, not bootstrap |
| 4.4 Latency; optimisation list | Done, **target missed** | n-gram speculative decoding was tried and was slower; other rungs not tried |
| 4.5 Judge on both systems | Done | |
| 5.1 Failure analysis | Done | REPORT §7-8 |
| 5.2 Report, README | Done | `REPORT.md`, `README.md` |
| 5.3 Demo video, ZIP | **Not done** | |

**Cut-lines if behind:**
- Validation scoring slips → score a 50-call stratified subset, with the wider CI stated.
- Latency misses 15 s → report honestly with the measured per-token decode time.
- Judge calibration slips → report judge numbers as descriptive only.

## 4. Training recipe

```yaml
base_model: google/gemma-4-12B-it-qat-w4a16-ct     # loaded with CompressedTensorsConfig(dequantize=True)
fallback_base: google/gemma-4-12B-it-qat-q4_0-unquantized
dtype: bfloat16
peft:
  r: 16
  lora_alpha: 32
  lora_dropout: 0.05
  bias: none
  target_modules: [q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj]   # text layers only
train:
  learning_rate: 2.0e-4
  lr_scheduler: cosine
  warmup_ratio: 0.03
  per_device_train_batch_size: 1
  gradient_accumulation_steps: 8        # 62 steps of 8 + 1 of 4 = 63 steps/epoch; batches stratified by code/train/batching.py (architecture §4.3)
  num_train_epochs: 3                   # checkpoint + validation eval every epoch
  max_length: 8192                      # assert zero truncation
  packing: false
  completion_only_loss: true
  gradient_checkpointing: true
  seed: 42                              # training reproducibility only; data is not seeded
prompt: prompts/system_v{final}.md      # recorded with the adapter
```

| Run | r | α | LR | Purpose |
|---|---|---|---|---|
| A | 16 | 32 | 2e-4 | Default |
| B | 16 | 32 | 1e-4 | LR sensitivity |
| C | 8 | 16 | 2e-4 | Capacity / vLLM-adapter fallback |

Estimated time [to be measured in 3.1]: ~1.7M tokens per epoch → ~15–25 min per epoch on L40S; the full sweep is under ~4 h.

**As run:** only run A, one training run, no sweep. **Measured time: about 55 minutes per epoch (10,281 s for 3 epochs), against the 15-25 minute estimate above**: each example carries the 2,010-token prompt (about half the tokens), and with batch size 1 and gradient checkpointing a 12B model on an L40S processes about 50 s per 8-call step. Differences from the recipe: no TRL (own training loop with the same settings), `completion_only_loss` implemented as loss on the answer tokens only, summed per step and divided by the step's answer tokens.

## 5. Experiments and pass criteria

| # | Experiment | Pass |
|---|---|---|
| E1 | Serve checkpoint; real token counts on the 5 provided examples; TTFT, decode tokens/s | Loads; numbers recorded |
| E2 | Chat template, thinking off | Clean JSON in content field |
| E3 | Schema-constrained vs unconstrained; candidates table on/off (50 validation) | 100% parse; keep the higher-CFA variant |
| E4 | Greedy vs card sampling × 3 (validation) | Keep greedy unless sampling gains ≥ 1 pt with no more hallucinations |
| E5 | Thinking on vs off (50 validation) | Enable only if ≥ 2 pts and p95 < 15 s |
| E6 | LoRA smoke test | Peak < 42 GB; module count as expected; accumulation 8 × batch 1 matches a batch of 8 (loss and grad norm within 1%) |
| E7 | Adapter-in-vLLM check | Within 1 pt; ≥ 95% identical across restarts |
| E8 | Latency optimization list (architecture §6.2) | Overall p95 < 15 s |
| E9 | Judge validation by mutation tests (done: `llm_judge/README.md`) | Faithfulness κ 1.00 and completeness κ 0.61 on 40 fresh items; calibration reported as an indicator only |

Status of the experiments: E1 done (decode about 62-73 tokens/s measured). E2 done. E3 **not run** (the constrained schema was always on; the candidates table was never used). E4 and E5 **not run**. E6 done in a reduced form (2-step run, peak 36.2 GB; the accumulation-equivalence check was not run). E7 **not run**. E8 **tried, failed** (speculative decoding slower). E9 done and exceeded (kappa 1.00 faithfulness on the fresh set).

## 6. Risks

| Risk | Early signal | Response |
|---|---|---|
| Authoring throughput | Finished: all 600 calls are written | None needed |
| Same-author style leakage → validation too easy | Baseline near-perfect on validation | Held-out agencies, harder validation items, stated limitation |
| p95 ≥ 15 s on L40S | E1 decode < 70 tok/s or p95 output > 1,000 tokens | Optimization list rungs 3–6 |
| vLLM adapter over int4 is wrong | E7 fails | r8; report |
| Dequantized load fails in TRL | E6 error | Fallback base; Unsloth |
| Gold errors | Validator failures; your 20-sample review | Fix and re-validate; report counts |

### Risks as they turned out

| Risk | What happened |
|---|---|
| Same-author style leakage → validation too easy | The baseline was *not* near-perfect (G1 60%), so the validation set is not trivially easy; the single-author limitation stands |
| p95 ≥ 15 s on L40S | **Happened**: p95 19.1 s; speculative decoding did not help; needs a shorter output or a faster GPU |
| vLLM adapter over int4 is wrong | Did not happen: vLLM loaded and ran all three adapters; the formal agreement check was not run |
| Dequantised load fails | Did not happen: 0 quantised modules left, 328 LoRA targets, peak 36.2 GB |
| Gold errors | Running the rules on the gold found 5 kinds of defect in 35 calls (junk fact keys, missing escalation flags, planned/completed labels, outside wording, one invented negative); all fixed; the model-vs-gold comparison also exposed scorer bugs (fixed, gold still scores 100%) |
| *Not anticipated:* constrained-decoding schema order | Made the first fine-tuned evaluation invalid until fixed (REPORT §7.4) |
