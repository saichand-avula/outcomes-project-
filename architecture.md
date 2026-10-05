# Architecture: clinical summary generation with Gemma 4 12B (QAT W4A16)

5 Oct 2026. This describes the system **as built**. Results and failures are in [REPORT.md](REPORT.md); the longer original design, with its citations and open questions, is in git history (`git show f88984a:architecture.md`). Section 8 lists where the build differs from that design.

## 1. Overview

```
 DATA (offline, hand-authored)            TRAINING                       SERVING + CHECKS (per call)
 blueprint → fact record                  SFT row = {transcript,         transcript
   → transcript (ASR noise logged)          target JSON}                    │
   → gold summary JSON                    system prompt v4 (separate)      ▼
   → gold validator (both directions)     LoRA r16 on Gemma 4 12B       Gemma 12B + LoRA on vLLM
 500 train + 100 validation               (BF16 copy of the QAT          JSON-schema constrained, greedy
                                           checkpoint), 189 steps           │
                                                                            ▼
 EVALUATION (offline)                                                    rules V1-V16 + quote repair
 validation calls → generate → rules → medication check → judge → one matrix      │
 (+ comparison with the gold)                                            automatic medication check
                                                                            │
                                                                            ▼
                                                              renderer → reference text
                                                              PASS / NEEDS NURSE REVIEW / FAILED
```

## 2. Data

- **Authored call by call, no generator, no external API.** Each call was written one at a time with an AI assistant (Claude Code), not produced by a template or random sampler. Each call starts as a *blueprint* (category plus axes: caller type, age, agency type, clinical domain, noise), becomes a *fact record* (ground truth), then a *transcript* written from the facts with every turn tagged by the facts it expresses and ASR errors written in and logged, then a *gold summary*. A gold validator checks fact record ⇄ transcript ⇄ gold in both directions; nothing ships failing (0 errors in 600).
- **Size and mix.** 500 train + 100 validation. Categories (train / val): routine 80/16, ambiguous 60/12, ASR-error 60/12, medication 90/18, supply 60/12, high-risk 100/20, not-applicable 50/10. Length mix about 72% short, 12% medium, 16% long. Medication calls include garbled drugs, chart-reading distractors, liquid concentrations and tall-man names.
- **Leakage control.** Validation holds out two agencies (Juniper Ridge Hospice, Northstar Home Health); no name, date of birth or phone is shared across splits; a character 5-gram near-duplicate scan runs across splits; files are hashed (`data/SHA256SUMS`). The 5 provided real calls are not used as data. There is no separate test split.
- **Three notions of truth.** Synthetic data: the fact record. Serving and validation: the **transcript only** (the model never sees the fact record). Semantic evaluation: transcript + summary, with the fact record as the judge's reference.

## 3. Output design

- **JSON, then render.** The model emits schema-constrained JSON; a deterministic renderer produces the reference text, so typed fields make the safety rules checkable by code and the format is exact. Top level: `not_applicable`, `identity` (name, DOB, caller, relationship, phone, each with `certainty` stated | unclear, `heard_as`, `turns`), `chief_complaint`, `assessment`, `response`, `education` (bullets), `risk_flags`.
- **Each bullet** carries `text`, `speaker`, `turns`, a verbatim `quote`, an `explanation` and typed `facts`: symptom, pertinent negative, medication (name, strength, dose, unit, route, frequency, last dose, status), vital, action (type, status planned | completed | advised), education, context, supply. Fact key order is part of the schema and must match the training targets (REPORT §7.2).
- **Renderer.** Identity sentence, dates (`MM/DD/YYYY`), phone format, timestamp line, tall-man drug casing (LORazepam) and `None documented during call.` are produced by code. Risk flags are returned beside the text, not inside it.
- **Source-grounded value policy.** The summarizer never uses outside medical knowledge to decide that a name "must" be another. A confidently stated form is kept as stated; a hedged form, or conflicting forms with no resolution, is marked `unclear` with the heard forms listed; a conflict resolved inside the call (spelled out, confirmed by the nurse, explicitly corrected) takes the resolved form. This satisfies "mark it unclear rather than guess".

## 4. Fine-tuning

- **Format.** The system prompt (`pipeline/prompts/system_v4.md`, 2,010 tokens, frozen) is kept apart from the rows and assembled at training time, identical to serving, so only the weights differ between baseline and fine-tuned model. The chat template with thinking off ends the generation prompt with an empty thought block; training uses the same.
- **LoRA, not full fine-tuning.** Rank 16, alpha 32, dropout 0.05 on all text-layer linear projections (328 modules, 65.6 M parameters, +0.6%) on a BF16 copy of the QAT checkpoint (`CompressedTensorsConfig(dequantize=True)`), so the frozen base equals the weights vLLM serves. The adapter is served unmerged (re-quantising a merged model is lossy).
- **Own training loop.** Loss is the summed token loss over answer tokens of a step divided by the step's answer-token count; label mask tested; gradient checkpointing; AdamW, 2e-4 cosine; batches of 8 calls stratified by length and category and reshuffled each epoch (63 steps per epoch); every epoch saved. Details: `finetune/README.md`.

## 5. Serving and checks

- **Serving.** vLLM 0.30.0 on one L40S, `--max-model-len 16384`, base as `gemma`, adapters as `ft1`-`ft3`, temperature 0, thinking off, JSON-schema constrained output, prefix caching for the fixed prompt. Output is validated by `check()` in `pl/schema.py`, the same definition vLLM receives.
- **Rules V1-V16** (`pipeline/pl/validators.py`, transcript and output only, no gold): valid schema and sections, cited turns exist, quote is verbatim in the cited same-speaker turns, numbers are in the cited turns, drug names and clinical terms are in the call, identity values were spoken, planned vs completed matches the nurse's words, hedges and negations kept, risk flags vs rule hits, Not-Applicable consistency, coverage warnings (V15), hygiene. ERROR = unsafe as it stands; WARN = a nurse should look.
- **Quote repair** (`pl/repair.py`): a near-miss quote is replaced by the exact transcript span; it touches nothing else.
- **Automatic medication check** (`pl/medsafety.py`, REPORT §7.3): adds a typed fact for a drug the summary names, copies a stated dose into a fact, and flags a drug the caller said that the summary lacks; a flag turns a PASS into NEEDS NURSE REVIEW.
- **Risk flags** = rule hits (uncontrolled symptom, medication concern, suicidal statement, breathing concern, escalation request, other urgent) combined with verified model flags, favouring recall; a negation window suppresses "no trouble breathing" but never suicidal phrases.
- **Interface.** `app/server.py` (Python standard library): `/api/summarize`, `/api/judge`, `/api/case(s)`, `/api/results`, `/api/config`, plus the web UI. It imports the pipeline's own code so the page shows what the evaluation measures.

## 6. Evaluation

- **One matrix for any system** (`run_pipeline.py generate → validate → judge → matrix`): 49 rows in groups: output validity, grounding in the call, wording vs meaning, safety gates, whole-call rule results, judge results, pipeline pass rates, comparison with the gold, operational. Rates carry Wilson 95% lower bounds and an evidence level (*validated* / *indicator*); pairwise comparisons use a paired sign test. The metric codes are explained in REPORT §2.
- **Headline metrics, fixed in advance:** safe-pass rate (no rule error and judged faithful; needs no gold) and critical-fact accuracy (matched critical slots ÷ (gold slots + model slots the gold lacks); validation only). Quote-repaired variants are reported separately; the raw output is the primary result.
- **Judge.** The base model with frozen prompts, validated on 90 deliberately damaged summaries before use (REPORT §5, `llm_judge/`).
- **Latency.** 20 evenly spaced calls, one request at a time, streamed so time to first token and total time come from one pass; one untimed warm-up call (the server compiles the JSON grammar on first use); nearest-rank percentiles.
- **Self-test.** `run_pipeline.py selftest`: gold passes its own rules and scores 100% against itself, 15 damage types are caught as expected (and four are shown to be invisible to the rules), the schema key order matches the gold (under 1% disagree), the automatic check behaves.

## 7. Hardware

One RunPod pod, one NVIDIA L40S (46 GB), CUDA 13.2. The 4-bit weights (about 8 GB) leave room for the prompt (about 3,600 tokens), the answer (about 900) and the KV cache; decoding is memory-bound at about 62-73 tokens/s. Training peaks at 36 GB (BF16 base, LoRA, gradient checkpointing, micro-batch 1).

## 8. Draft design vs what was built

| Draft design | Built | Why |
|---|---|---|
| Not-Applicable rule gate before the model | Model decides; V14 checks consistency | Not needed for the measured results; not built |
| Candidates table (spoken numbers, names, drugs) appended to the input | Not built | Time; it is the first change proposed for the next training run (REPORT §10) |
| One targeted retry on a validator error | Not built | Latency budget already exceeded |
| Rules V1-V12 | V1-V16 | Four more defects found while building the study |
| FastAPI + Gradio | Standard-library server and one HTML page | No dependencies to install |
| Sweep of three LoRA runs | One run (r16, 2e-4), three epoch checkpoints | Time |
| HF-vs-vLLM adapter agreement check | Not run | Time; vLLM numbers are the ones measured |
| Greedy vs sampling and thinking on/off tests | Not run | Time |
| Output schema "in the order of the gold" | Reordered **twice** | The first order made the first fine-tuned result invalid (2.7% medications); the second still disagreed with 5% of gold facts and cost doses (REPORT §7.2, §8) |
| Latency target by optimisation ladder | Target missed (p95 19.1 s); n-gram speculative decoding slower | REPORT §8 |
| Deterministic metrics only on fact records | Gold comparison by value and cited-turn proximity; judge adds meaning | Practical; see REPORT §9 |
| Nothing for drugs the model drops | Automatic medication check | Rules V15 only warned; REPORT §7 |

## 9. Assumptions and limits

- The Not-Applicable rendering (`Not Applicable` / timestamp / `Reason: …`) has no reference example and is an assumption. Timestamps come from request metadata, never from the transcript.
- Single author for all 600 calls, so style may leak between train and validation; the baseline was far from perfect (safe-pass 65%), which argues against a trivially easy validation set, but a second author's calls would be a better test.
- A deterministic check can verify what was said and who said it, never whether a true fact was attached to the right thing or whether something is missing; that is what the judge and the gold comparison are for, and why every summary still needs a nurse.
