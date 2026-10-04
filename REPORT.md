# Report: clinical call summaries with a fine-tuned open model

Written 4 Oct 2026. Every number below comes from files in this repo (`pipeline/outputs/`, `finetune/runs/ft1/`, `llm_judge/`). Where something is an estimate, an opinion, or was not done, it says so.

## 1. Verdict in one table

Task: turn a nurse-line call transcript into a structured clinical summary with an open model (Gemma 4 12B, 4-bit QAT checkpoint) fine-tuned with LoRA, check it automatically, and reach **95% on an automatic metric** with **p95 latency under 15 s**.

| Goal | Result | Met? |
|---|---|---|
| Fine-tuning improves on the base model | Safe-pass G1 **60% → 92%**, Critical-Fact Accuracy H19 **56.8% → 81.6%** (same prompt, same schema, same 100 calls; paired sign test p < 0.001) | **Yes** |
| 95% on the headline automatic metrics | G1 92% (lower 95% bound 85%), H19 81.6% (79.3%). After automatic quote repair G1r is 94% (87.5%) | **No** |
| 95% on *some* automatic metrics | 24 of 50 matrix rows are at or above 95%, among them identity values (H2 98.0%), calls with no rule error after quote repair (E1r 96.0%), judged faithful (F1 97%), Not-Applicable decision (H14 100%). The pre-registered headlines are not among them | Partly |
| p95 latency under 15 s | p50 13.9 s, **p95 19.8 s** (slowest 21.7 s), 65% of calls under 15 s; 20 timed calls, one at a time, L40S | **No** |
| LLM judge is trustworthy before being used | Validated on 90 hand-edited summaries, with a fresh set run once on frozen prompts. Trustworthy for faithfulness and for missing nurse actions; weak for missing findings, hedges and speaker swaps (section 5) | **Yes, with stated limits** |

The fine-tuned model is much better than the base model. It is not good enough to call finished: it leaves things out, and in a few calls it swapped one drug for another. Section 8 lists exactly what and why.

## 2. What was built

```
 data/ (500 train + 100 validation, hand-written)        finetune/ (LoRA training, 189 steps)
        │                                                        │ adapter
        ▼                                                        ▼
 pipeline/ ── generate ─► rules V1-V16 + quote repair ─► frozen LLM judge ─► one matrix of 0-100% rates
        │                         (no gold needed)         (base model)        (+ gold comparison on validation)
        ▼
 app/ (demo UI): same checks, PASS / NEEDS NURSE REVIEW / FAILED
```

| Folder | What it is |
|---|---|
| `data/`, `code/` | The dataset (facts → transcript → gold summary, all validated) and its tools |
| `llm_judge/` | Validation of the base model as a judge: golden sets, five versions, the frozen final judge |
| `pipeline/` | The evaluation pipeline and every run's saved outputs. One matrix for any model |
| `finetune/` | Training code, config, logs and the three saved adapters |
| `app/` | A small demo UI (standard library only) |

## 3. Data and setup

- **Data.** 500 training + 100 validation calls. All written by hand from fact records with logged ASR noise (no templates, no random generator, no API). The validation set holds out two agencies (Juniper Ridge Hospice, Northstar Home Health) that training never sees. Seven scenario categories. Every gold summary passes a validator (0 errors across all 600). There is **no separate test split**: validation is used for monitoring, for choosing the epoch and for the final numbers (a limitation, section 9).
- **Model.** `google/gemma-4-12B-it-qat-w4a16-ct`, 4-bit weights. Served with vLLM 0.30.0 on one RunPod **L40S** (46 GB).
- **Output.** One JSON object per call: identity, chief complaint, assessment / response / education bullets (each with the verbatim quote and the turn numbers it rests on, plus typed facts), risk flags. A deterministic renderer turns it into the reference text.
- **Decoding.** Greedy, thinking off, JSON-schema constrained.
- **Prompt.** `pipeline/prompts/system_v4.md` for both the base and the fine-tuned model (the strictest comparison: only the weights differ). It is 2,010 tokens, about half of every training example.

## 4. How the fine-tuning was done

| Item | Value |
|---|---|
| Method | LoRA, rank 16, alpha 32, dropout 0.05, on q/k/v/o/gate/up/down of every text layer (328 modules, 65.6 M trainable parameters) |
| Base for training | The same checkpoint, dequantised to BF16; the adapter is then served on the 4-bit model in vLLM |
| Optimiser | AdamW, learning rate 2e-4 (cosine, 3% warm-up), gradient clipping 1.0, seed 42 |
| Batches | 8 calls per optimiser step, stratified by length and category, reshuffled each epoch; 63 steps per epoch, 3 epochs = 189 steps |
| Loss | Summed token loss over the answer tokens of the whole step ÷ the step's answer tokens; the prompt and transcript carry no loss |
| Cost | 10,281 s (2.9 h) on the L40S, 36.2 GB peak memory |
| Training loss | 0.58 at step 1 → 0.16 / 0.12 / 0.09 (mean of the last 10 steps of epochs 1 / 2 / 3) |
| Validation loss (100 calls) | Before training 0.635 (25-call subset) → epoch 1 **0.189**, epoch 2 **0.167**, epoch 3 **0.171** |

The training itself was uneventful. Gradient norms spiked (up to 417) on some steps; the clipping handled them and the loss did not react. One CUDA out-of-memory warning at step 9 recovered without a crash.

## 5. The judge was validated, and how far it can be trusted

Before using Gemma as a judge, we tested it on summaries with **known** defects (`llm_judge/`). Half of 90 validation summaries were damaged on purpose (a number changed, a drug swapped, an invented finding, a negative flipped, a bullet removed, "planned" written as "completed", a speaker swapped, a hedge removed); every edit was read by hand. Prompts were tuned over five rounds on the first 50 items; the final prompts were then **frozen and run once on 40 fresh items**. That fresh run is the validation.

| Rubric | First set (50, prompts tuned here) | **Fresh set (40, frozen prompts)** | What we use it for |
|---|---|---|---|
| Faithfulness | kappa 0.90, caught 12/12, 2/38 false alarms | **kappa 1.00, caught 10/10, 0/30 false alarms** | Yes (only 10 edits in the fresh set: a small sample) |
| Completeness vs the fact record | kappa 0.86 | **kappa 0.61**, caught 4/6, 2/34 false alarms | Reliable for missing nurse actions and instructions (9/9 over both sets); **unreliable for missing findings** (3 of 6 missed) |
| Calibration | kappa 0.55 | **kappa 0.55**, caught 3/6 | Planned-vs-completed only (6/6). Speaker swaps (3/6) and removed hedges (0/2): not reliable |

Version history (v1 to v5, what each change fixed) is in `llm_judge/README.md`. Things to keep in mind:

- The judge is the **same model family** as the thing it judges, so it may favour its own style. It is the base model, never the adapter.
- Without a fact record (new, unseen calls) the judge writes its own checklist. That mode is **not validated**; the pipeline labels it so.
- The judge cannot decide the 95% claim on its own. The rules and the gold comparison carry that.

## 6. Results

### 6.1 The base model → the fine-tuned model (final comparison)

All rows: 100 validation calls, same prompt, same constrained-decoding schema, judge = base model. Full matrix: `pipeline/outputs/matrix_base_v4_s2_vs_finetuned_epoch3_s2.md`.

| Metric | Base | **Fine-tuned (epoch 3)** | 95% bound of the fine-tuned value |
|---|---|---|---|
| **G1** safe-pass: no rule error and judged faithful (headline, works on unseen calls) | 60% | **92%** | 85% |
| G1r safe-pass after automatic quote repair | 78% | 94% | 87.5% |
| **H19** Critical-Fact Accuracy against gold (headline, validation only) | 56.8% | **81.6%** | 79% |
| H19r gold critical facts found (diagnostic) | 84.6% | 90.3% | |
| E1 calls with no rule ERROR / E1r after quote repair | 62% / 80% | 94% / 96% | 87.5% / 90.2% |
| F1 judged faithful | 95% | 97% | 91.5% |
| F3 judge: every checklist item covered | 81% | 68% | |
| G2 safe-pass and complete and calibrated | 43% | 61% | |
| H1 / H2 identity values (and certainty) | 95.1% / 91.8% | 98.2% / 98.0% | |
| H3 / H4 medications found / correct (name, dose, unit) | 93.3% / 82.7% | 89.3% / 74.7% | |
| H18 output medications that are in gold | 50.4% | 90.5% | |
| H9 / H10 / H11 nurse actions found / correct / education types found | 73.8% / 72.8% / 60.0% | 87.6% / 87.1% / 83.9% | |
| H13 output risk flags that are in gold | 27.0% | 87.9% | |
| H12 gold risk flags found | 89.2% | 78.4% | |
| Latency (20 calls, one at a time) | p50 28.1 s, p95 54.4 s | **p50 13.9 s, p95 19.8 s** | target: p95 < 15 s |

Reading it honestly:

- **What fine-tuning bought.** The model learned the gold summaries' habits: it records the right kinds of facts, with the right labels, and flags risk far less often and far more precisely (H13 27% → 88%). Rule errors fell from 38 calls to 6. Output is valid JSON in 100% of calls, 99.7% of quotes are in the cited turns, and the output is less than half as long, hence the halved latency.
- **What it cost.** It is more selective, and so it **drops things**: medications found fell from 93% to 89%, "every checklist item covered" (judge) from 81% to 68%, and gold risk flags found from 89% to 78%. This is the main weakness (section 8).
- **Paired by call**, G1 passes in 36 calls only for the fine-tuned model and in 4 calls only for the base (p < 0.001). Against the *stronger* baseline of the old schema (G1 70%), 28 versus 6 calls (p = 0.0002).
- **By category** (fine-tuned, G1): medication calls are the weakest (77.8%), then high-risk (90%); ambiguous, ASR-error and Not-Applicable calls are at 100% (12, 12 and 10 calls: small numbers). H19 is lowest on long calls (75.6%) and high-risk calls (75.4%).

### 6.2 Every run, so the history is not hidden

Recomputed from the saved outputs. The old-schema fine-tuned run is **invalid** (section 7.4) and is shown only so nobody mistakes it for a result.

| Run | G1 | H19 | E1 | F1 | H3 meds found | Notes |
|---|---|---|---|---|---|---|
| `base` (prompt v1) | 7% | 31% | 7% | 92% | 0% | v1 never defined the fact fields or date format |
| `base_v2` | 59% | 49% | 63% | 95% | 94.7% | exact output format added |
| `base_v3` | 65% | 51% | 67% | 98% | 94.7% | name / relationship wording |
| `base_v4` (old schema) | 70% | 56.9% | 70% | 98% | 93.3% | frozen prompt, schema with the wrong key order |
| `base_v4_s2` | 60% | 56.8% | 62% | 95% | 93.3% | frozen prompt, corrected schema: **the baseline we compare with** |
| `finetuned_epoch2` (old schema) | 87% | 62.7% | 89% | 93% | **2.7%** | **invalid**: the schema forced a key order the model had not learned |
| `finetuned_epoch2_s2` | 91% | 81.4% | 93% | 98% | 82.7% | |
| **`finetuned_epoch3_s2`** | **92%** | **81.6%** | **94%** | 97% | 89.3% | **chosen** |

Epoch 1 was trained and saved but never evaluated with the pipeline.

(`H19` for the old-schema runs and the first two rows is recomputed with the corrected scorer, so it can differ from numbers shown in earlier messages.)

## 7. What went wrong, and what we tried that did not work

This is the part most reports leave out.

### 7.1 The first baseline was nearly meaningless (prompt)
The draft prompt did not say how to write dates (the model wrote "February 12, 1936"), nor the field names inside the typed facts (the model invented a free-text `value`), nor whether `relationship` meant the caller's or the patient's role. Result: G1 7%, medication matching 0%. We rewrote the prompt three times (v2 → v4), changing **only output format and naming conventions, never clinical content**. We then froze it, because tuning the baseline on the very set we evaluate on would flatter the baseline. The residual risk: the prompt was shaped against the validation conventions, so the baseline is better than a first try but not an expert-tuned one.

### 7.2 Our own tools had bugs
- **Renderer crash.** The renderer crashed on any date of birth that was not `YYYY-MM-DD`, and the judge silently skipped those calls: only 13 of 100 were judged, in 25 seconds. We noticed the number, fixed it (the judge now converts spoken and written dates for display) and added a warning that counts any skipped call.
- **Scorer too strict.** "Milligrams" did not equal "mg", the word "pain" was a stop word, "Helen Ostrowski" did not match "Helen". Medication-with-dose matching read 12% when it was really 80%. We fixed the scorer; gold scored against itself stays 100% on every row, and damaged gold is still caught.
- **Generation took 50 minutes** because of one request at a time. We added parallel generation and a separate timed sample for latency.

### 7.3 Quote stitching
The base model often glued two sentences together with "..." or ran a quote past a clean span: 29 to 33 calls with a quote error. We added a **deterministic quote repair** (replace a near-miss quote with the exact span from the cited turns; it never touches anything else and changes 0 quotes in all 100 gold summaries) and report it **separately** (E1r, G1r) so the raw numbers stay primary. The fine-tuned model has this problem in only 3 calls.

### 7.4 Our schema made the first fine-tuned result wrong
The first evaluation of the fine-tuned model showed **medications found 2.7%, vitals 2.8%**, and the model "worse" than the base on several rows. Training was fine; our serving schema was the cause. vLLM's constrained decoding forces the keys in the schema's order, and our schema listed `certainty` second in every fact, while the training targets have it last. After `type`, the grammar forced `certainty`, which the model had learned means "this fact is finished", so it closed the fact without its name, dose or severity. We proved it by checking all 600 gold summaries against the schema (the old order disagreed with 2,400 identity fields and 4,914 of 5,083 facts), reordered the schema, added a test, and re-ran **both** the base and the fine-tuned model under the corrected schema. The corrected schema made the base model *slightly worse* (G1 70% → 60%), so we report both baselines; the fine-tuned model beats either. Five percent of the gold facts still use an order that conflicts with the one we chose (the gold itself is inconsistent for a few key pairs); that is fixable at training time (section 10).

### 7.5 Speculative decoding for latency made it slower
To close the latency gap we tried n-gram (prompt-lookup) speculative decoding, which is lossless and needs no retraining. The server accepted about 2.4 to 3.4 tokens per step, but throughput fell from about 62 to **34 to 43 tokens/s** (median 23 s per call instead of 14 s). vLLM 0.30 logged why: with n-gram speculation it falls back to the older model runner and disables asynchronous scheduling, and here it is combined with LoRA and constrained JSON decoding. The first reading of that slow run was confused for a while because `ps` does not show the original command line of vLLM; we found the cause from the server log and the metrics endpoint. **Not tried:** the model-based drafter (MTP), emitting quote pointers instead of verbatim quotes, templated explanations, a faster GPU.

### 7.6 The latency target was not reached, and what would be needed
At about 62 tokens/s, 15 s means about 900 output tokens; the median fine-tuned call writes 894 and the long ones 1,000 to 1,300. Removing the `explanation` field (11% of the output) would still leave the longest calls near 19 s; removing `quote` (15%) would also remove our evidence check. A faster GPU is the more reliable lever (decoding speed follows memory bandwidth; an H100 has about four times the L40S's, which suggests 2 to 3 times faster in practice: an estimate, not measured).

### 7.7 Why epoch 3, not epoch 2
Validation loss was lowest at epoch 2 (0.167 against 0.171), and the training loss kept falling, which looks like the start of overfitting. But loss is not the thing we care about. On the pipeline metrics, epoch 3 is equal or better almost everywhere: G1 92% vs 91% (a tie: 5 calls only epoch 3 passes, 4 only epoch 2), and clearly better on completeness (judge F3 68% vs 57%, G2 61% vs 51%), medications found (89% vs 83%) and nurse actions. It misses slightly more risk flags (78% vs 81%), a difference of one flag. So we chose epoch 3 on the pipeline metrics, **using the same validation set we report on**: the choice is among three checkpoints, so the effect is small, but the final numbers are slightly optimistic. Epoch 1 was not evaluated.

### 7.8 A smaller point
A single CUDA out-of-memory warning at step 9 (46 GB reserved, 35 GB used) recovered; the run was not restarted. `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` would likely avoid it; we did not apply it.

## 8. What the fine-tuned model still gets wrong

From the 8 of 100 calls that fail G1, and from inspecting the gold medications the model missed (epoch 3):

- **Medications (7 of 75 gold medications not found by name; 19 medication slots lost once dose and unit are included).** Of the 7:
  - **2 wrong-drug substitutions: lisinopril became metoprolol (va-039) and zolpidem became melatonin (va-069).** This is the dangerous kind. The rules cannot see it when both drugs occur in the call (a nurse reading the chart); only the judge and, on validation, the gold comparison do. On new data without gold, **only the judge stands between this error and the nurse**, and the judge is imperfect.
  - 2 omissions where the drug is mentioned in the text but has no medication fact (morphine and atropine in va-080); 1 drug missing entirely (acetaminophen, va-026).
  - 1 garbled name corrected from outside knowledge ("meth a dome" became methadone), which our as-spoken policy forbids; 1 naming mismatch (va-099, "Tylenol" in the output against "acetaminophen" in the gold).
- **Timing and hedging.** "twenty minutes earlier" and "last given this afternoon" where the transcript supports neither; a claim that a pill organiser was "full" when the caller said otherwise.
- **Remaining rule errors (after quote repair):** one invented number (va-095), one drug not in the call (va-059, "insulin"), one status marked completed without a completion cue (va-077), one quote still wrong.
- **Missing details.** 105 gold critical slots are missing from the output: nurse actions 26, symptoms 26, medications 19, negatives 17, identity 9, risk flags 8. Symptom and negative matching is word overlap, so some of these are different phrasings, not omissions; and the judge's completeness check on findings is itself weak.
- **Extra facts.** 115 "unsupported" facts count against H19 (symptoms 44, actions 38, negatives 14, medications 7, flags 4, identity 8). Spot checks showed many are true details the gold simply does not record, so H19 partly measures *imitating the gold's selectivity*. That is why H19r (no penalty for extras) is reported next to it, and why we do not treat H19 alone as a measure of correctness.

## 9. Limits of this evidence

- 100 validation calls, synthetic, written by one author; confidence bounds are wide (see the "95% bound" column). The target is not met at 95% and a point estimate at 95% on 100 calls would still have a lower bound near 89%.
- No test split; validation was used for monitoring, epoch choice and reporting.
- The judge is the same model family as the system it judges; its completeness mode is unvalidated on unseen data.
- Latency is 20 timed calls, one at a time, on one L40S. The p95 of 20 samples is close to the slowest call.
- The gold comparison (H19) is not identical to the architecture's "CFA" definition: matching is by normalised value and cited-turn proximity, without a speaker or quote-validity condition.
- **Planned and not done:** a learning-rate sweep (only 2e-4 was run), a rank sweep, greedy-versus-sampling test, thinking-mode test, the HF-versus-vLLM agreement check of the adapter, McNemar and bootstrap intervals (we used a paired sign test and Wilson bounds), preference tuning (DPO), epoch 1 evaluation.
- **Production pieces in the design but not built:** the Not-Applicable gate before the model, the candidates table in the input, the targeted retry on validator errors. The demo UI applies the rules, the quote repair and a review gate, not these.

## 10. What to change if we fine-tune again

Each item is tied to evidence above; none is a guarantee.

1. **Canonicalise the key order in the training targets, and use the same order in the serving schema.** Fixes the 5% order conflicts (252 of 5,083 facts) so the grammar never fights the model.
2. **Fix the medication problem directly.** Add training calls where the chart drug differs from the discussed drug, more garbled drug names kept as spoken, and weight the loss on drug-name tokens. This targets the substitutions and the "corrected" names.
3. **Hold out a development split** (for example 40 of the 500) for choosing the epoch and any hyper-parameter, so validation is touched once at the end. Evaluate all three epochs, including epoch 1.
4. **Run the sweeps we skipped:** learning rate (1e-4 against 2e-4), possibly more epochs at a lower rate (metrics were still improving at epoch 3 while validation loss was not).
5. **Shorten the output** only if latency matters more than the extra fields: templated `explanation`, quote pointers (turn plus first and last words, filled in by code), compact identity. Train and serve it together, then re-validate every rule.
6. **Add examples for the failure types in section 8:** hedged times, "maybe a little", completed-versus-planned.
7. **Use the validators during training data checks and a retry loop in production** (the design's step 6): a REVIEW case could be sent back to the model once with the validator's message.
8. **Independent evaluation:** a second judge from a different model family, or a human review of about 30 outputs, before any claim about unseen data.
9. **Training hygiene:** set `expandable_segments`, add checkpoint resume, save the optimiser state.
10. **Hardware:** if the 15 s target is firm, plan for an H100 (or equivalent) and re-time.

## 11. Reproduce

```bash
python3 code/data/validate_gold.py                 # 600 gold calls, 0 errors
python3 code/tests/test_validator.py && python3 code/tests/test_render.py
cd pipeline && python3 run_pipeline.py selftest    # rules catch what they should; gold scores 100% against itself
python3 run_pipeline.py matrix --systems base_v4_s2 finetuned_epoch3_s2        # rebuild the final matrix from saved outputs
python3 ../app/server.py                           # demo UI at http://localhost:8080 (replay mode needs no GPU)
```
Training and GPU runs: `finetune/README.md` and `pipeline/README.md`. The adapters are in `finetune/runs/ft1/epoch_{1,2,3}/` (about 250 MB each, not in git). The model to use is `epoch_3`.
