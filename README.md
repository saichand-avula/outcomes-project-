# Clinical Call Summaries with a Fine-Tuned Open Model

Turn a nurse-line call transcript into a structured clinical summary with **Gemma 4 12B (4-bit QAT) + a LoRA adapter**, check every summary with **16 deterministic rules and a validated LLM judge**, and render it in the exact reference format. Hand-written data, a frozen evaluation pipeline, a trained adapter and a demo UI.

> **Status in one line:** fine-tuning clearly works (safe-pass **60% → 92%**, critical-fact accuracy **56.8% → 81.6%**), but the **95% target and the 15 s latency target were not reached**. Full, honest account: **[REPORT.md](REPORT.md)**.

## Results at a glance

100 validation calls (two agencies held out), same prompt, same schema, judge = base model. Details and every run: [REPORT.md](REPORT.md) §6.

| What is measured (code in the evaluation table) | Base model | **Fine-tuned (epoch 3)** | Target |
|---|---|---|---|
| **Safe-pass rate (G1)**: calls where no automatic rule found an error *and* the judge found nothing wrong or invented | 60% | **92%** (cautious estimate 85%) | 95% ❌ |
| Safe-pass rate after automatic quote repair (G1r): the same once near-miss quotes are corrected | 78% | 94% (87.5%) | 95% ❌ |
| **Critical-fact accuracy (H19)**: important facts that match the hand-written reference summary, minus facts the model added | 56.8% | **81.6%** (79%) | 95% ❌ |
| **Identity accuracy**: patient and caller name, date of birth, relationship, phone right (H1) / and "stated or unclear" right (H2) | 95.1% / 91.8% | **98.2% / 98.0%** (97% / 96%) | 95% ✅ |
| Judged-faithful rate (F1): the judge model finds nothing wrong or invented | 95% | 97% (91.5%) | 95% ✅ (best guess; the cautious estimate is below) |
| **Medication name** found (H3): drugs in the reference that appear in the output (75 drugs) | 93.3% | 89.3% (80%) | 95% ❌ (worse than base) |
| **Medication name + dose + unit** all right (H4) | 82.7% | 74.7% (64%) | 95% ❌ (worse than base) |
| **Total response time**, 20 calls timed one at a time on an L40S GPU | median 28.0 s, 95th percentile 69.9 s | **median 14.0 s, 95th percentile 19.1 s** | 95th percentile under 15 s ❌ |
| **Time to first token** (how soon the answer starts), median / 95th percentile | 0.16 s / 0.62 s | 0.17 s / 0.64 s | none given |

"Gold" or "reference" means the summary written by hand for each call. The figure in brackets is a cautious estimate (the 95% lower bound): with 100 calls the true rate could plausibly be that low. Every code (G1, H19, ...) is explained in plain words in [REPORT.md §1.2](REPORT.md).

What the model still gets wrong ([REPORT.md](REPORT.md) §8): it is more selective than the base model and **drops details**. In 3 of 100 calls it **left out a drug the call was about** (for example lisinopril in va-039, zolpidem in va-069), and its medication scores fell below the base model's (REPORT §8.1 reads all 19 lost medication slots). The rules cannot see a missing drug; only the judge and the gold comparison can. Every automatic summary needs a nurse's review.

## The LLM judge was validated before it was used

We damaged 90 hand-picked summaries on purpose (wrong number, swapped drug, invented finding, flipped negative, removed item, planned → completed, swapped speaker, removed hedge) and checked whether the base model, used as a judge, found them. Prompts were tuned on 50 items; the final prompts were then **frozen and run once on 40 fresh items**.

| Rubric | Fresh-set result | Trusted for |
|---|---|---|
| Faithfulness | kappa **1.00**, 10/10 caught, 0/30 false alarms (small sample) | yes |
| Completeness | kappa 0.61 | missing nurse actions and instructions; **not** missing findings |
| Calibration | kappa 0.55 | planned vs completed only |

Method, five versions and limits: [llm_judge/README.md](llm_judge/README.md).

## How it works

```
transcript ──► Gemma 12B + LoRA (vLLM, JSON schema, greedy) ──► JSON summary
                                                                   │
        16 rule validators (no model, no gold needed)  ◄───────────┤   quote repair: near-miss quote → exact span
        frozen LLM judge (base model, optional)        ◄───────────┤
        deterministic renderer                         ◄───────────┘
                     │
        PASS   or   NEEDS NURSE REVIEW / FAILED       (never shown as final)
```

## Try it (no GPU needed)

```bash
python3 app/server.py          # open http://localhost:8080
```
Four tabs: **Examples** (the 100 validation calls with precomputed outputs of both models, rule checks, evidence and gold side by side), **Try your own transcript** (live model, needs a model server), **Results** (the assignment's metrics against the 95% line, latency, epochs, medication errors) and **How it works**. Showing it from the GPU pod: `bash app/serve_on_pod.sh` ([app/README.md](app/README.md)).

## Assignment deliverables: where each one is

| Asked for | Here |
|---|---|
| `code/` runnable Python | [code/](code/) (data tools, validator, renderer), [pipeline/](pipeline/) (generate, rules, judge, matrix), [finetune/](finetune/) (LoRA training), [app/](app/) (UI and API) |
| `data/` training, validation and evaluation sets | [data/](data/): 500 train + 100 validation calls; `pipeline/data/` has the same calls prepared for evaluation |
| `outputs/` summaries, reports, latency | [pipeline/outputs/](pipeline/outputs/): every run's generated summaries, rule results, judge results, matrices (`.md`, `.json`, `.xlsx`), [med_errors.md](pipeline/outputs/med_errors.md) |
| `README.md` install and run | this file; GPU steps in [finetune/README.md](finetune/README.md) and [pipeline/README.md](pipeline/README.md) |
| `report.md` | [REPORT.md](REPORT.md): design, model selection, safety controls, evaluation method, baseline versus fine-tuned, latency analysis, limitations. The four metrics the assignment names are in [§1.1](REPORT.md) |
| Demo video | not part of this repo (to be recorded; the UI in [app/](app/) is what it would show) |

## Repo map

| Path | What is in it |
|---|---|
| **[REPORT.md](REPORT.md)** | **Start here.** Results, everything that failed and why, why epoch 3, what to change next time |
| [architecture.md](architecture.md) | The design, with an outcome note on every decision that did not survive contact with reality |
| [plan.md](plan.md) | Build order, what is done and what is not |
| [data/](data/) | 500 train + 100 validation calls: facts → transcript → gold summary. `dataset_overview.xlsx` is the readable view |
| [code/](code/) | Data tools: gold validator, renderer, batching, tests |
| [llm_judge/](llm_judge/) | Judge validation: golden sets, versions v1–v5, frozen prompts, results |
| [pipeline/](pipeline/) | Evaluation pipeline (generate → rules → judge → matrix), prompts v1–v4, and **every run's saved outputs** |
| [finetune/](finetune/) | LoRA training code, config and logs; adapters in `finetune/runs/ft1/epoch_{1,2,3}` (not in git; **use epoch 3**) |
| [app/](app/) | Demo UI and API (Python standard library only) |

## Data at a glance

- **500 training + 100 validation calls**, all hand-written (fact record → transcript with per-turn fact tags and logged ASR noise → gold summary), 0 validator errors, no name / DOB / phone shared across splits. Validation holds out two agencies (Juniper Ridge Hospice, Northstar Home Health).
- **Categories (train / validation):** routine 80/16 · ambiguous 60/12 · ASR-error 60/12 · medication 90/18 · supply 60/12 · high-risk 100/20 · not-applicable 50/10. Length mix about 72% short, 12% medium, 16% long.
- No random sampler, templates or external API. There is **no separate test split**: validation is used for monitoring, for choosing the epoch and for the numbers above, so they are slightly optimistic. The 5 provided example calls are not used as data.
- Open `data/dataset_overview.xlsx` for the sizes, coverage charts and every call. Authoring conventions: [data/authoring/README.md](data/authoring/README.md).

## Checks you can run

```bash
python3 code/data/validate_gold.py                # expect: validated 600 calls: 0 errors, 0 warnings
python3 code/data/coverage.py                     # category, length and tag quotas
python3 code/data/dupcheck.py                     # cross-split near-duplicate check
python3 code/tests/test_validator.py              # 15/15 damage types caught
python3 code/tests/test_render.py
cd pipeline && python3 run_pipeline.py selftest   # expect: selftest OK
python3 run_pipeline.py matrix --systems base_v4_s2 finetuned_epoch3_s2     # rebuild the final comparison from saved outputs
```
Rebuild the compiled data after editing a call: `python3 code/data/compile.py && python3 code/data/build_workbook.py`. GPU steps (train, serve, evaluate) are in [finetune/README.md](finetune/README.md) and [pipeline/README.md](pipeline/README.md).

*Research prototype on synthetic data. Not a medical device.*
