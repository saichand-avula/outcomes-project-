# Clinical Call Summaries with a Fine-Tuned Open Model

Turn a nurse-line call transcript into a structured clinical summary with **Gemma 4 12B (4-bit QAT) + a LoRA adapter**. Every summary is checked by **16 deterministic rules, an automatic medication check and an LLM judge that was validated first**, then rendered in the exact reference format. Authored data, a frozen evaluation pipeline, a trained adapter and a demo UI.

> **Status:** fine-tuning clearly works (safe-pass rate **65% → 91%**, critical-fact accuracy **57.6% → 82.3%**), but the **95% target and the 15 s latency target were not reached**. Full, honest account: **[REPORT.md](REPORT.md)**.

## Results at a glance

100 validation calls (two agencies held out), same prompt and settings for both models, judge = base model. The figure in brackets is the cautious 95% lower bound. *Gold* = the reference summary written for each call; every code (G1, H19, ...) is explained in [REPORT.md §2](REPORT.md).

| What is measured | Base | **Fine-tuned (epoch 3)** | Target |
|---|---|---|---|
| **Safe-pass rate (G1)**: no rule error *and* the judge finds nothing wrong or invented | 65% | **91%** (84%) | 95% ❌ |
| **Critical-fact accuracy (H19)**: important facts matching the gold, minus facts the model added | 57.6% | **82.3%** (80%) | 95% ❌ |
| **Identity**: names, date of birth, relationship, phone right (H1) / and "stated or unclear" right (H2) | 97.3% / 93.8% | **98.2% / 98.0%** (97% / 96%) | 95% ✅ |
| Judged-faithful rate (F1) | 100% | 96% (90%) | 95% ✅ best guess only |
| **Medication names found** (H3, 75 drugs) | 94.7% | 86.7% (92.0% with the automatic medication check, below) | 95% ❌ |
| **Medication name + dose + unit right** (H4) | 84.0% | 78.7% (85.3% with the check) | 95% ❌ |
| **Total response time**, 20 calls one at a time, L40S GPU | median 28.0 s, p95 69.9 s | **median 14.0 s, p95 19.1 s** | p95 under 15 s ❌ |
| **Time to first token**, median / p95 | 0.16 s / 0.62 s | 0.17 s / 0.64 s | none given |

**Why the fine-tuned model is lower on medication recall** (it is not worse overall): the base model lists every drug it hears (139 entries for 75 correct drugs, a third wrong), and the score only counts drugs found, never extras; the fine-tuned model lists only the drugs the call is about, like the gold (88% of its drugs are right against 65%), and counting both it is ahead (F1 0.87 against 0.77 for names). Its real weaknesses are writing one entry for several drugs in one sentence and 2 truly omitted drugs (lisinopril in va-039, acetaminophen in va-026). A mistake of ours in the output-format setting had also cost it doses (fixed). A simple automatic check after the model (it compares the drugs the caller said with the summary, adds a missing medication entry, copies a stated dose, and flags a drug the summary lacks) raises names found to 92.0% and name + dose + unit to 85.3%; those two figures use the check and are slightly optimistic, because parts of it were tuned after looking at validation misses. Evidence: [REPORT.md §7](REPORT.md); why every other number is under 95%: [§6.5](REPORT.md).

## The LLM judge was validated before it was used

We damaged 90 hand-picked summaries on purpose (wrong number, swapped drug, invented finding, flipped negative, removed item, planned → completed, swapped speaker, removed hedge) and checked whether the base model, as a judge, found them. Prompts were tuned on 50 items, then **frozen and run once on 40 fresh items**.

| Rubric | Fresh-set result | Trusted for |
|---|---|---|
| Faithfulness | kappa **1.00**, 10/10 caught, 0/30 false alarms (small sample) | yes |
| Completeness | kappa 0.61 | missing nurse actions and instructions; **not** missing findings |
| Calibration | kappa 0.55 | planned vs completed only |

Method and limits: [llm_judge/README.md](llm_judge/README.md).

## How it works

```
transcript ──► Gemma 12B + LoRA (vLLM, JSON schema, greedy) ──► JSON summary
                                                                   │
        16 rule validators + quote repair (no model, no gold)  ◄───┤
        automatic medication check (drugs said but not recorded)    ◄───┤
        frozen LLM judge (base model, optional)                ◄───┤
        deterministic renderer                                 ◄───┘
                     │
        PASS   or   NEEDS NURSE REVIEW / FAILED       (never shown as final)
```

## Try it (no GPU needed)

```bash
python3 app/server.py          # open http://localhost:8080
```
Four tabs: **Examples** (100 validation calls with precomputed outputs of both models, rule checks, evidence and gold side by side), **Try your own transcript** (live model, needs a model server), **Results** (the assignment's metrics against the 95% line, latency, epochs, medications), **How it works**. From the GPU pod: `bash app/serve_on_pod.sh` ([app/README.md](app/README.md)).

## Assignment deliverables: where each one is

| Asked for | Here |
|---|---|
| `code/` runnable Python | [code/](code/) (data tools, validator, renderer), [pipeline/](pipeline/) (generate, rules, judge, medication check, matrix), [finetune/](finetune/) (LoRA training), [app/](app/) (UI and API) |
| `data/` training, validation, evaluation sets | [data/](data/): 500 train + 100 validation calls; `pipeline/data/` has the validation calls prepared for evaluation |
| `outputs/` summaries, reports, latency | [pipeline/outputs/](pipeline/outputs/): every run's summaries, rule and judge results, matrices (`.md`, `.json`, `.xlsx`), [med_errors.md](pipeline/outputs/med_errors.md), [medsafety.md](pipeline/outputs/medsafety.md) |
| `README.md` | this file; GPU steps in [finetune/README.md](finetune/README.md) and [pipeline/README.md](pipeline/README.md) |
| `report.md` | [REPORT.md](REPORT.md): design, model selection, safety controls, evaluation, baseline vs fine-tuned, latency, limitations; the assignment's four metrics are in [§2](REPORT.md) |
| Demo video | not in this repo |

## Repo map

| Path | What is in it |
|---|---|
| **[REPORT.md](REPORT.md)** | **Start here.** Results, what failed and why, why epoch 3, what to change next time |
| [architecture.md](architecture.md) | The system as built, and where it differs from the draft design |
| [plan.md](plan.md) | Build order and what was done / not done |
| [data/](data/) | 500 train + 100 validation calls: facts → transcript → gold summary; `dataset_overview.xlsx` is the readable view |
| [code/](code/) | Data tools: gold validator, renderer, batching, tests |
| [llm_judge/](llm_judge/) | Judge validation: golden sets, versions v1-v5, frozen prompts, results |
| [pipeline/](pipeline/) | Evaluation pipeline (generate → rules → medication check → judge → matrix), prompts v1-v4, **every run's saved outputs** |
| [finetune/](finetune/) | LoRA training code, config, logs; adapters in `finetune/runs/ft1/epoch_{1,2,3}` (not in git; **use epoch 3**) |
| [app/](app/) | Demo UI and API (Python standard library only) |

## Data at a glance

- **500 training + 100 validation calls**, each authored one at a time with an AI assistant (Claude Code) from a fact record, then a transcript with logged ASR noise, then a gold summary; no templates, random generator or external API; 0 validator errors; nothing shared across splits. Validation holds out two agencies (Juniper Ridge Hospice, Northstar Home Health).
- Categories (train / validation): routine 80/16 · ambiguous 60/12 · ASR-error 60/12 · medication 90/18 · supply 60/12 · high-risk 100/20 · not-applicable 50/10.
- No random sampler, templates or external API. **No separate test split**: validation served monitoring, the epoch choice and the numbers, so they are slightly optimistic. Authoring conventions: [data/authoring/README.md](data/authoring/README.md).

## Checks you can run

```bash
python3 code/data/validate_gold.py                # validated 600 calls: 0 errors, 0 warnings
python3 code/tests/test_validator.py              # 15/15 damage types caught
python3 code/tests/test_render.py
cd pipeline && python3 run_pipeline.py selftest   # selftest OK (rules, schema order, medication check)
python3 run_pipeline.py matrix --systems base_v4_s3 finetuned_epoch3_s3     # rebuild the final comparison from saved outputs
```

*Research prototype on synthetic data. Not a medical device.*
