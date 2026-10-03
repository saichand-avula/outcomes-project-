# Execution Plan — Clinical Summary LLM (5 days)

Oct 3, 2026 · companion to [architecture.md](architecture.md), which holds the design rationale and evidence. This file covers what gets built, in what order, and when each step counts as done.

## 0. Progress

- **Data authoring is complete:** 500 train + 100 validation calls, hand-authored and validated (0 errors, 0 warnings, no cross-split leaks). Overview and every call's facts, transcript, noise and summary: `data/dataset_overview.xlsx`.
- Done so far: authoring tools and validator (`code/data/`), renderer (`code/common/`), system prompt draft (`prompts/system_v1.md`), compiled JSONL/SFT files (`data/`).
- Not started: GPU/vLLM setup, baseline run, pipeline validators and API/UI, LoRA training, evaluation and judge harness, report and demo.

## 1. Fixed decisions

| Item | Decision |
|---|---|
| Model | `google/gemma-4-12B-it-qat-w4a16-ct`, vLLM, greedy, thinking off |
| GPU | RunPod, 1× L40S 46,068 MiB, CUDA 13.2 |
| Data | Claude-authored; **500 train / 100 validation**; no separate evaluation split; the 5 provided real calls are not used as data |
| Length mix | 72% short/normal · 12% medium · 16% long (train 360/60/80; validation 73/11/16). Minimums: short ≥ 65 lines and 4,500–9,000 chars; medium ≥ 85 lines and 7,500–12,500; long ≥ 105 lines and 10,500–18,000 (Not-Applicable calls exempt) |
| Output | JSON → deterministic renderer → exact reference format |
| SFT format | `{id, transcript, call_timestamp_utc, target}`; system prompt in `prompts/system_vN.md`, assembled at train time |
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
| 2 | 2.2 Pre-processing, validators V1–V12, NA gate, risk rules + unit tests | `code/pipeline/` | Tests pass on validation |
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
| 4 | 4.5 Judge runs + calibration (you label 40) + mutation tests | `outputs/judge/` | κ reported |
| **5** | 5.1 Failure analysis, significance tests, figures | `outputs/failure_cases.md` | — |
| 5 | 5.2 `report.md`, README, reproduce one eval from a clean env | — | README steps run end-to-end |
| 5 | 5.3 Demo video (≤ 3 min), ZIP | `submission.zip` | Submitted |

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
| E9 | Judge calibration + mutations | κ ≥ 0.6 to publish judge metrics |

## 6. Risks

| Risk | Early signal | Response |
|---|---|---|
| Authoring throughput | Finished: all 600 calls are written | None needed |
| Same-author style leakage → validation too easy | Baseline near-perfect on validation | Held-out agencies, harder validation items, stated limitation |
| p95 ≥ 15 s on L40S | E1 decode < 70 tok/s or p95 output > 1,000 tokens | Optimization list rungs 3–6 |
| vLLM adapter over int4 is wrong | E7 fails | r8; report |
| Dequantized load fails in TRL | E6 error | Fallback base; Unsloth |
| Gold errors | Validator failures; your 20-sample review | Fix and re-validate; report counts |

