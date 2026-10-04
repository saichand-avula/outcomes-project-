# Execution plan: clinical summary LLM (5 days)

5 Oct 2026. What was planned, what was done, what was not. Design: [architecture.md](architecture.md). Results: [REPORT.md](REPORT.md).

## 1. Where things stand

**Built and run:** data, evaluation pipeline, judge validation, fine-tuning, latency measurement, medication safety net, demo UI, reports. **Not done:** the demo video and the submission zip. **Targets:** 95% on the headline metrics and p95 < 15 s were **not reached**.

| Area | State |
|---|---|
| Data | 500 train + 100 validation calls, authored one at a time and validated (0 errors in 600, no cross-split leaks); `data/dataset_overview.xlsx` |
| Judge | Base Gemma validated on 90 deliberately damaged summaries (50 to tune, 40 fresh on frozen prompts): faithfulness kappa 1.00, completeness 0.61, calibration 0.55 |
| Pipeline | Rules V1-V16, quote repair, medication safety net, frozen judge, gold comparison, one matrix; prompt iterated v1 → v4 and frozen |
| Fine-tuning | One LoRA run (r16, 3 epochs, 189 steps, 2.9 h, L40S); **epoch 3 chosen**; adapters in `finetune/runs/ft1/` (not in git) |
| Result | Safe-pass rate 65% → **91%**, critical-fact accuracy 57.6% → **82.3%**, median response 14.0 s, p95 19.1 s, first token 0.17 s |
| Medications | Recall below the base model's (names 86.7% vs 94.7%), ahead on precision; safety net: 92.0% / 82.7% (REPORT §7) |
| UI | `app/`: Examples, Try your own transcript, Results, How it works |

## 2. Fixed decisions

| Item | Decision |
|---|---|
| Model | `google/gemma-4-12B-it-qat-w4a16-ct` on vLLM, greedy, thinking off, JSON-schema constrained |
| GPU | RunPod, 1× L40S (46 GB), CUDA 13.2 |
| Data | Authored with an AI assistant (Claude Code); 500 train / 100 validation; validation holds out two agencies; no test split; the 5 provided real calls are not used as data |
| Length mix | About 72% short, 12% medium, 16% long (train 360/60/80; validation 73/11/16) |
| Output | JSON → deterministic renderer → exact reference format |
| Prompt | `system_v4.md`, frozen, **the same for baseline and fine-tuned model** (only the weights differ; costs about 1,700 extra prompt tokens per training example) |
| Fine-tuning | BF16 LoRA r16 / alpha 32 on all text-layer linear projections of the dequantised checkpoint |
| Headline metrics | Safe-pass rate (needs no gold) and critical-fact accuracy (against the gold), fixed in advance; latency p50 / p95 |

## 3. Data coverage plan (planned, not random)

Every call starts as a one-line blueprint tagged with its axis values; the quotas below were met exactly (`code/data/coverage.py`).

| Category | Train | Validation | Subtypes |
|---|---|---|---|
| Routine | 80 | 16 | symptom update, question, visit scheduling, post-visit follow-up |
| Ambiguous | 60 | 12 | caller unsure, contradictions, self-correction, vague timeline, second-hand report |
| ASR-error heavy | 60 | 12 | garbled drug, name/DOB, numbers/doses, speaker-label errors |
| Medication | 90 | 18 | dose/timing question, missed or double dose, side effect, crushing, liquid concentration, patch, new-med request |
| Supply request | 60 | 12 | refill, equipment, wound/catheter supplies, delivery timing |
| High-risk | 100 | 20 | uncontrolled symptom, medication concern, suicidal statement, breathing, escalation, emergencies |
| Not Applicable | 50 | 10 | wrong number, billing only, silent call, robocall, survey, records request |

Secondary axes (caller type, age, agency type, 15+ clinical domains, identity patterns, medication phenomena, action status, uncertainty, negation, conversational noise) have minimum shares per split; authoring protocol and freeze rules (hash the files, never edit validation after the first run) are in `data/authoring/README.md`.

## 4. Roadmap and what really happened

| Day | Step | Status |
|---|---|---|
| 1 | Skeleton, schema, renderer, validators; vLLM + checkpoint on the pod (needs `VLLM_USE_FLASHINFER_SAMPLER=0`); chat-template check | Done (thinking off adds an empty thought block to the generation prompt; training uses it) |
| 1 | Prompt v1 and baseline | Done, **changed**: v1 never defined formats (safe-pass 7%); iterated to v4 and frozen; the baseline is the 100 validation calls |
| 1-3 | Author 100 validation + 500 train calls; defect study of the rules | Done |
| 2 | Prompt iteration; greedy vs sampling; thinking on/off | **Partly**: prompt iteration done; the other two not run |
| 3 | LoRA smoke test | Done (2-step trial on the pod, CPU test on a tiny model) |
| 3 | Sweep of three LoRA runs | **Not done**: one run (r16, 2e-4) |
| 3 | API + UI | **Changed**: standard-library server and one HTML page, no FastAPI or Gradio |
| 4 | Select winner on validation | Done: epoch 3, on pipeline metrics (REPORT §6.3) |
| 4 | Adapter-in-vLLM agreement check (HF vs vLLM) | **Not done**: vLLM served and ran the adapter; the formal check was not run |
| 4 | Baseline vs fine-tuned, full metrics | Done (Wilson bounds and a paired sign test, not bootstrap); rerun once after the output-schema fix |
| 4 | Latency; optimisation list | Done, **target missed**: n-gram speculative decoding tried and slower; other options not tried |
| 4 | Judge on both systems | Done |
| 5 | Failure analysis; medication analysis and safety net | Done (REPORT §7-8) |
| 5 | Report, README, architecture, plan | Done |
| 5 | Demo video, ZIP | **Not done** |

## 5. Training recipe (as run)

LoRA r16 / alpha 32 / dropout 0.05 on q, k, v, o, gate, up, down (328 modules, 65.6 M parameters); AdamW, learning rate 2e-4 cosine, 3% warm-up, clipping 1.0, seed 42; 8 calls per step stratified by length and category, reshuffled each epoch (63 steps per epoch, 189 in all); loss on answer tokens only; gradient checkpointing; adapters saved after every epoch. Peak memory 36.2 GB. Pass criteria used: loss falls in the first 20 steps (it did: 0.58 → 0.17), validation loss does not run away (0.189 / 0.167 / 0.171), and the choice among epochs is made on the pipeline metrics, not on loss.

## 6. Risks, as they turned out

| Risk | What happened |
|---|---|
| Baseline too weak or too strong | The first prompt was far too weak (safe-pass 7%); iterated on format only, then frozen. The baseline is better than a first try but not expert-tuned |
| Output schema fights the trained order | **Happened twice**: the first order made the fine-tuned result invalid; the second still cost doses. Fixed; a selftest now guards it (REPORT §8) |
| p95 ≥ 15 s on the L40S | **Happened**: p95 19.1 s; speculative decoding slower; needs shorter output or a faster GPU |
| Same-author style leakage makes validation too easy | The baseline was far from perfect (safe-pass 65%), so unlikely to be trivial; the single-author limitation stands |
| Judge unreliable | Validated before use; weak on completeness of findings, hedges, speaker swaps; stated wherever used |
| Fine-tuning hurts something | Medication recall below the base model's (selectivity, one fact for several drugs, a schema mistake): analysed, partly repaired with the safety net |
| Out of memory | One warning at step 9, recovered |

## 7. Not done

Learning-rate and rank sweeps, greedy-vs-sampling and thinking tests, the HF-vs-vLLM agreement check, repeat-run determinism, bootstrap intervals, preference tuning, the Not-Applicable gate / candidates table / retry in the production path, re-running epochs 1-2 and the latency timing on the final schema, the demo video and the submission zip.
