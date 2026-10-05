# Report: clinical call summaries with a fine-tuned open model

5 Oct 2026. Every number comes from files in this repo (`pipeline/outputs/`, `finetune/runs/ft1/`, `llm_judge/`). Where something is an estimate, an opinion or was not done, it says so.

## 1. Summary

Task: turn a nurse-line call transcript into a structured clinical summary with Gemma 4 12B (4-bit QAT) fine-tuned with LoRA, check it automatically, reach **95% on an automatic metric** and **p95 latency under 15 s**.

| Goal | Result (100 validation calls) | Met? |
|---|---|---|
| Fine-tuning beats the base model | Safe-pass rate **65% → 91%**, critical-fact accuracy **57.6% → 82.3%** (same prompt, same schema; paired sign test p < 0.001) | **Yes** |
| 95% on the headline metrics | Safe-pass 91% (lower 95% bound 84%), critical-fact accuracy 82.3% (80%) | **No** |
| 95% on other metrics | 25 of 49 matrix rows: identity 98%, no rule error after quote repair 97%, judged faithful 96%, Not-Applicable decision 100% | Partly |
| Medication accuracy | Fine-tuned model scores *below* the base on recall (names 86.7% vs 94.7%, name + dose + unit 78.7% vs 84.0%) but far above it once precision counts; a medication check lifts it to 92.0% / 85.3% (section 7) | **No** |
| p95 latency < 15 s | median 14.0 s, **p95 19.1 s**, 13 of 20 timed calls under 15 s | **No** |
| LLM judge validated before use | 90 deliberately damaged summaries, fresh set run once on frozen prompts (section 5) | **Yes, with limits** |

The fine-tuned model is much better than the base model, but not finished: it is more selective and drops details, including, in a few calls, a drug the call was about. Every summary still needs a nurse.

## 2. The metrics the assignment asks for

| Assignment metric | Measured as (code) | Base | Fine-tuned | 95%? |
|---|---|---|---|---|
| Factual accuracy | Judged faithful, nothing wrong or invented (F1) | 100% | **96%** (bound 90%) | point estimate yes |
| | Critical-fact accuracy against the gold summary (H19) | 57.6% | **82.3%** (80%) | no |
| Completeness | Checklist items covered (F2) / every item covered in a call (F3) | 97.3% / 84.0% | 95.3% / 69.0% | F2 yes, F3 no |
| | Gold critical facts found, extras not penalised (H19r) | 86.7% | 90.9% (89%) | no |
| Identity accuracy | Name, DOB, caller, relationship, phone right (H1) / and certainty right (H2) | 97.3% / 93.8% | **98.2% / 98.0%** (97% / 96%) | **yes** |
| Medication name | Gold drugs found by name, 75 drugs (H3) | 94.7% | 86.7% (77%); 92.0% with the automatic check (§7) | no |
| Medication name + dose | Found with the right dose and unit (H4) | 84.0% | 78.7% (68%); 85.3% with the automatic check (§7) | no |
| Time to first token | Streamed, 20 calls one at a time | 0.16 s / 0.62 s | 0.17 s / 0.64 s | no target |
| Total response time | Median / 95th percentile, same 20 calls, L40S | 28.0 s / 69.9 s | **14.0 s / 19.1 s** | p95 no |

Task 5 (95% on the defined metric, with definition, dataset size and failure cases): the defined metrics are safe-pass rate (G1) and critical-fact accuracy (H19), on 100 validation calls from two agencies the training never saw. **91% and 82.3%: not met.** Failure cases are in sections 7 and 8.

**What the codes mean.** All are percentages of the 100 validation calls (or items in them). *Gold* = the reference summary written for a call. *Rule checks* = 16 automatic checks (V1-V16) of the summary against the transcript, no model. *Judge* = the base model reading transcript and summary. *Bound* = the 95% lower confidence bound: with 100 calls the true rate could plausibly be that low.

| Code | Plain words |
|---|---|
| G1 / G1r | **Safe-pass rate**: no rule error and the judge finds nothing wrong or invented / the same after near-miss quotes are repaired. Needs no gold, so it works on new calls |
| H19 / H19r | **Critical-fact accuracy**: important facts matching the gold, minus facts the model added / without that penalty |
| E1 / E1r | Calls passing all 16 rule checks / after quote repair |
| F1, F2, F3, F4 | Judge: nothing wrong or invented / checklist items covered / every item covered / hedges, planned-vs-done and speaker right |
| G2 | Full-pass: safe-pass, complete and calibrated |
| H1, H2 | Identity values right / and certainty ("stated" or "unclear") right |
| H3, H4 | Medication names found / name, dose and unit right |
| H12, H13, H18 | Gold risk flags found / share of raised flags the gold has / share of the model's medications in the gold |
| D3, B1, C1, A1 | Spoken drugs present in the summary / numbers really spoken / planned-vs-completed wording right / valid JSON |

## 3. What was built

```
 data/ (500 train + 100 validation, authored)      finetune/ (LoRA, 189 steps)
        │                                                       │ adapter
        ▼                                                       ▼
 pipeline/: generate ─► rules V1-V16 + quote repair ─► automatic medication check ─► frozen judge ─► one matrix
 app/: demo UI (same checks; PASS / NEEDS NURSE REVIEW / FAILED)
```

- **Data.** 500 training + 100 validation calls, each authored one at a time with an AI assistant (Claude Code) from a fact record, with logged ASR noise (no templates, random generator or external API). Validation holds out two agencies. Seven categories (routine, ambiguous, ASR-error, medication, supply, high-risk, not-applicable). Every gold summary passes a validator (0 errors in 600). **No separate test split**: validation is used for monitoring, the epoch choice and the numbers, so they are slightly optimistic.
- **Model and why.** `google/gemma-4-12B-it-qat-w4a16-ct`: the assignment fixes the family and size; this is Google's 4-bit quantisation-aware build for direct serving in vLLM, which leaves room on one 46 GB GPU for the long prompt (about 3,600 tokens) plus the answer (about 900) and helps decoding speed (memory-bound). Cost: LoRA training starts from a dequantised 16-bit copy of the same weights, a mismatch we did not measure.
- **Hardware / software.** One RunPod **NVIDIA L40S (46 GB)**; vLLM 0.30.0 (serving), PyTorch 2.13 and PEFT 0.21.2 (training), Python 3.11.
- **Inference.** `vllm serve … --enable-lora --max-lora-rank 16 --max-model-len 16384 --gpu-memory-utilization 0.90`; temperature 0, thinking off, `max_tokens` 6000, JSON-schema constrained output, one request at a time for timing. Base served as `gemma`, adapters as `ft1`-`ft3`.
- **Output.** One JSON object per call: identity, chief complaint, assessment / response / education bullets (each with a verbatim quote, cited turns and typed facts) and risk flags; a deterministic renderer produces the reference text. One prompt (`pipeline/prompts/system_v4.md`, 2,010 tokens) for base and fine-tuned model, so only the weights differ.

## 4. Fine-tuning

LoRA rank 16, alpha 32, dropout 0.05 on q/k/v/o/gate/up/down of every text layer (328 modules, **65.6 M trainable parameters, +0.6%**); AdamW, learning rate 2e-4 cosine, 3% warm-up, clipping 1.0, seed 42; 8 calls per step, stratified by length and category, 63 steps per epoch, 3 epochs = 189 steps; loss only on answer tokens. **2.9 h on the L40S, 36.2 GB peak.** Training loss 0.58 → 0.09; validation loss 0.635 before, then 0.189 / 0.167 / 0.171 after epochs 1 / 2 / 3. Gradient spikes (up to 417) were handled by clipping; one CUDA out-of-memory warning at step 9 recovered. Details: `finetune/README.md`.

## 5. The judge was validated

We tested the base model as a judge on summaries with **known** defects: half of 90 validation summaries were damaged on purpose (wrong number, swapped drug, invented finding, flipped negative, removed item, planned → completed, swapped speaker, removed hedge), every edit checked by hand. Prompts were tuned on 50 items over five rounds, then **frozen and run once on 40 fresh items**.

| Rubric | Tuning set (50) | **Fresh set (40, frozen)** | Trusted for |
|---|---|---|---|
| Faithfulness | kappa 0.90 | **kappa 1.00**, 10/10 caught, 0/30 false alarms | yes (only 10 edits: small sample) |
| Completeness | kappa 0.86 | **kappa 0.61** | missing nurse actions and instructions (9/9); not missing findings |
| Calibration | kappa 0.55 | **kappa 0.55** | planned vs completed only |

The judge is the same model family as the system it judges, never the adapter. Without a reference checklist (new calls) it writes its own, which is **not validated**. It cannot decide the 95% claim; the rules and the gold comparison do. Method and versions: `llm_judge/README.md`.

## 6. Results

### 6.1 Base vs fine-tuned (final comparison, `matrix_base_v4_s3_vs_finetuned_epoch3_s3.md`)

| Measure (code) | Base | Fine-tuned | Bound |
|---|---|---|---|
| Safe-pass rate (G1) / after quote repair (G1r) | 65% / 83% | **91% / 93%** | 84% / 86% |
| Critical-fact accuracy (H19) / facts found (H19r) | 57.6% / 86.7% | **82.3% / 90.9%** | 80% / 89% |
| Calls with no rule error (E1) / after repair (E1r) | 65% / 83% | **95% / 97%** | 89% / 91.5% |
| Judged faithful (F1) / every checklist item covered (F3) / full-pass (G2) | 100% / 84% / 50% | 96% / 69% / 60% | 90% / 59% / 50% |
| Identity right (H1) / with certainty (H2) | 97.3% / 93.8% | **98.2% / 98.0%** | 97% / 96% |
| Nurse actions found (H9) / right status (H10) / education items found (H11) | 78.7 / 77.2 / 62.4% | **88.1 / 88.1 / 82.4%** | |
| Risk-flag precision (H13) / gold flags found (H12) | 27.7% / 89.2% | **85.3%** / 78.4% | |

- **Bought:** the model writes what the gold writes (right kinds of facts, labels), raises far fewer false risk flags, makes few rule errors (35 calls → 5) and writes less than half as much.
- **Cost:** it is more selective and **drops things**: every-item coverage 84% → 69%, gold risk flags found 89% → 78%, medication recall (section 7).
- **By call:** safe-pass passes in 29 calls only for the fine-tuned model, 3 only for the base. Weakest categories: medication calls (G1 77.8%) and high-risk calls (critical-fact accuracy 76%).
- **Fairness:** both models ran with the same corrected output schema (section 8, item 4). That schema also helped the base (safe-pass 60% → 65%), so this comparison is the fairer one.

### 6.2 Latency (20 evenly spaced calls, one at a time, L40S)

| | Base | Fine-tuned |
|---|---|---|
| Total response time p50 / p95 / slowest | 28.0 / 69.9 / 70.4 s | **14.0 / 19.1 / 20.8 s** |
| Calls under 15 s | 2 of 20 | 13 of 20 |
| Time to first token p50 / p95 | 0.16 / 0.62 s | 0.17 / 0.64 s |
| Output tokens per call (median, 100 calls) | 2,559 | 917 |
| Decoding speed (median) | about 73 tokens/s | about 63 tokens/s |

The gain is **not faster decoding but shorter answers**: the base writes 2.8 times more tokens. Latency is output length divided by tokens per second; at 63 tokens/s, 15 s is about 900 tokens, and the fine-tuned median is 917 (long calls 1,000 to 1,600). First-token time is prompt processing only and under 5% of the total. Timed on the earlier schema run, whose answers have the same length (median 917); the 20 calls were timed twice, with fine-tuned p95 19.8 s then 19.1 s, so read it as "about 19 to 20 s" (with 20 calls the p95 is the second-slowest call).

### 6.3 Epochs and why epoch 3 (all three on the earlier schema, so they compare with each other)

| | Epoch 1 | Epoch 2 | **Epoch 3** |
|---|---|---|---|
| Safe-pass rate (G1) | 68% | 91% | **92%** |
| Critical-fact accuracy (H19) | 73.3% | 81.4% | **81.6%** |
| Every checklist item covered (F3) | 65% | 57% | **68%** |
| Medication names found (H3) / name + dose + unit (H4) | 88.0 / 74.7% | 82.7 / 69.3% | **89.3 / 74.7%** |
| Gold risk flags found (H12) | 54% | 81% | 78% |
| Valid JSON (A1) | 97% | 100% | 100% |

Validation loss was lowest at epoch 2 (0.167 vs 0.171), but loss is not the goal. On the pipeline metrics epoch 3 is equal or better almost everywhere (safe-pass is a tie: 5 calls only epoch 3 passes, 4 only epoch 2) and clearly better on completeness and medication names. Epoch 1 is clearly weakest (3 of its 100 answers ran into the token limit). The choice used the same validation set we report on; with only three checkpoints the effect is small. Epochs 1 and 2 were not re-run on the corrected schema.

### 6.4 Methods used for safety, accuracy, consistency and latency

| Goal | What we did | Measured effect | What it did not do |
|---|---|---|---|
| Safety | Verbatim quote and cited turns on every bullet; 16 rules (quotes, numbers, drug names, identity, planned vs completed, negations); quote repair; Not-Applicable decision; risk flags; PASS / NEEDS NURSE REVIEW / FAILED gate; automatic medication check; validated judge | Calls with a rule error 35% → 5%; numbers really spoken 99.2% → 99.7%; planned-vs-completed wording right 99.3% → 100% | Rule V15 only warns about a spoken drug the summary lacks (section 7.3); a wrong drug that is also in the call is seen only by the judge |
| Accuracy | LoRA on 500 calls; frozen prompt v4; schema key order matched to the training targets | Safe-pass 65% → 91%; critical-fact accuracy 57.6% → 82.3% | Medication recall below the base (section 7); 95% not reached |
| Consistency | Greedy decoding; JSON-schema constrained output; fixed key order; one prompt; deterministic renderer | Valid, schema-correct output on 100 of 100 calls | Byte-identical repeat runs not tested |
| Latency | Compact output from fine-tuning; 4-bit weights; adapter served unmerged; no retry needed | p50 28.0 → 14.0 s, p95 69.9 → 19.1 s | 15 s missed; n-gram speculative decoding was slower |

### 6.5 Why each headline number is below 95% (fine-tuned, epoch 3, 100 validation calls)

Taken from the saved outputs (`reference.jsonl`, `validation.jsonl`, `judge.jsonl`), not from assumptions.

**Safe-pass rate, 91% (9 calls fail; base 35).** Five calls have a rule error: three are a quote attached to a neighbouring turn (V4; automatic repair exists for these, consistent with 93% after repair), one is a drug the call never named ("insulin", V7), one is an invented number (70, V6). Four calls are judged unfaithful; the judge's reasons quote the transcript and I read them as correct, but the transcripts were not re-audited line by line: a hedge dropped ("since Tuesday, or maybe Wednesday" became "since the beginning of the week"), a last dose given as "this morning" when the call said the pill is due at eight, a dose given as "one ... another one" written as "1 mg", and a pill organiser called "full" when three slots were empty. These are the model's real mistakes. Base fails mostly on quote placement (30 of its 35).

**Critical-fact accuracy, 82.3% (82.5% with the automatic check).** The score is matched critical slots divided by (gold slots + model slots the gold lacks): 989 matched of 1,083 gold slots, plus 116 extra. The 94 missed gold slots: symptoms 26, pertinent negatives 16, nurse actions 24, medications 11, risk flags 8, identity and the rest about 9 (approximate split). The 116 extras: symptoms 44, actions 34, medications 13, pertinent negatives 12, risk flags 5. In the 9 calls I read side by side (symptoms only), roughly half of the misses and extras were scoring artifacts or gold selectivity, not errors (a sample, not a count): wording that does not share a word with the gold ("dry mouth" absent, "low mood" written as "hopelessness"), and real, grounded findings the gold chose not to record (itching, knee stiffness, hip pain). Only the first kind of miss is the model's fault. Because the gold is one author's selection, a gap to 95% on this score cannot be closed by the model alone; the judge's faithfulness (96%) is the fairer measure of invented content.

**Completeness of the whole call (F3), 69% (base 84%).** 31 calls miss at least one checklist item; the item most often missing is *background* ("children are staying at the house", "afraid of giving too much", 14 calls, 9 of them miss only background), then instructions given (9), pertinent negatives (6) and nurse actions (5). The fine-tuned model writes shorter summaries that follow the gold's selection, and the judge's completeness rubric is weak (kappa 0.61), so this is partly the judge. It is a real gap for background context that the gold does keep.

**Risk flags, 78% found (H12) and 37.5% of the rule-suggested other flags present (D2b).** The model flags only what the gold flags (85% of its flags are in the gold, against 28% for the base); it misses 8 of 37 gold flags. The rule-suggested flags are broad keyword hits, so D2b is an indicator, not a target.

**Medications.** Section 7. After the automatic check: names 92.0%, name + dose + unit 85.3% (base 94.7% and 84.0%).

**Latency.** Section 6.2: the answer is about 900 tokens at 62-73 tokens per second on one L40S, so the median is about 14 s and the tail (long calls, long answers) is 19 s. Reaching p95 under 15 s needs a shorter output (for example dropping the explanation and quote fields; untested), a faster GPU, or a smaller model.

## 7. Medications: why the fine-tuned model scores lower, and what we did

### 7.1 The numbers

| | Base | Fine-tuned (model alone) | Fine-tuned + automatic medication check |
|---|---|---|---|
| Gold drugs found by name (H3), of 75 | 71 (94.7%) | 65 (86.7%) | **69 (92.0%)** |
| Name + dose + unit right (H4), of 75 | 63 (84.0%) | 59 (78.7%) | **64 (85.3%)** |
| Distinct drug names it wrote that are gold drugs | 65% | 88% | 85% |
| F1, names / name + dose + unit (precision and recall together) | 0.77 / 0.68 | 0.87 / 0.79 | **0.89 / 0.82** |

### 7.2 Why (each point checked on the saved outputs)

1. **The score only counts recall.** H3 and H4 count gold drugs found and never penalise extras. The base wrote 139 medication entries for 75 gold drugs (29 repeat a name already listed; the rest include water, wine, "pills"), so it rarely misses one. The gold is selective: it records 73% of the drugs said in a training call (63% in validation); the base records 88%, the fine-tuned model 64%, almost exactly the gold's rate. On a balanced score the fine-tuned model is ahead.
2. **Structure losses (the model's real weakness).** Of the 8 gold drugs only the base finds: 2 are true omissions (acetaminophen in va-026, lisinopril in va-039); 5 are in the fine-tuned summary text but without their own typed fact (three drugs in one sentence got one fact; a drug in a response bullet; two doses of one drug merged); 1 is "Tylenol" written as spoken against the gold's "acetaminophen". In calls with several drugs it finds 82% (28 of 34) against 97% for the base; in single-drug calls they are equal.
3. **A mistake of ours cost doses.** vLLM forces the JSON keys into the schema's order and never lets a key be written after a later one. The training data writes a medication's `strength` before its `dose`; our schema had `strength` after `unit`, so after writing a strength the model could not write the dose (it ended up inside `frequency`). Our key order disagreed with 252 of 5,083 gold facts (5.0%); a search over the gold's own orders found one that disagrees with 17 (0.3%). Fixing it recovered 5 of the 6 lost doses (name + dose + unit 56 → 59).
4. **The remaining gap is within chance.** Paired by drug, names 8 only-base against 2 only-fine-tuned (p = 0.11); name + dose + unit 8 against 4 (p = 0.39).
5. **Checked and not supported:** a training bug (the loss mask is tested, loss curves are normal, medication scores do not trend with epochs: H4 74.7 / 69.3 / 74.7%); an unfair prompt or setting (same prompt, schema and scorer; if anything the base prompt was tuned on the validation calls, which favours the base); the quantisation mismatch (drug names and numbers copied from the call are intact: 99.5% and 99.7%), though the direct check was not run.

Slot-by-slot lists: `pipeline/outputs/med_errors.md` (`dev/med_error_analysis.py`).

### 7.3 The automatic medication check (built, no retraining)

`pipeline/pl/medsafety.py` runs after the model, needs no gold and no GPU:
- An **expected drug** is a formulary drug the *caller* said, with a number in the turn or in two or more turns. The rule was read off the training set before scoring validation: 405 of 497 spoken drugs qualify, 84% are recorded in the training gold, covering 91% of its medication facts.
- **M1:** an expected drug named in a bullet's text but without a typed fact gets one. **M2:** a typed fact without a dose gets the "number unit" that follows the drug in its own bullet (a number before the drug, as in "five milligrams of morphine", is read too, and spelled-out numbers; never a concentration such as "20 mg per mL"; 97% correct on the training gold with doses blanked, 338 of 363 filled). **M3:** an expected drug the summary never names is flagged (not added) and the UI turns a PASS into NEEDS NURSE REVIEW.
- Rule V15 already *warns* about every spoken drug the summary lacks, but also fires on chart-read distractors and warnings do not stop a PASS; M3 is the narrower version that does.
- **Cost and limits.** It flagged 7 drugs in 5 of 100 calls: both real omissions (va-026, va-039) and 5 that are not in the gold (chart-read drugs, Tylenol, aspirin). The same net flags 5 of 100 *gold* summaries, so about that many false alarms are expected: a flag means "please check". The brand-to-generic table, the brand/generic check before flagging, and the reading of a dose written before the drug name ("five milligrams of morphine", va-080) were all added after seeing validation misses, and the same 100 calls score everything, so the figures are optimistic (the training-gold dose test, 97% correct, is the unbiased evidence for the extractor). The remaining 6 unfound names are not net failures: 2 are omitted from the summary (flagged, not added), and 4 are scoring conventions (Tylenol against the gold's acetaminophen, a garbled drug name that the gold keeps as heard, a drug only the nurse mentions, a drug with two doses in the call). The net repairs the typed list; the summary text is unchanged.

### 7.4 What the literature says (analogies, not proofs)

Omissions, not inventions, dominate LLM clinical-summary errors (3.45% against 1.47% in one large study, where iterating on prompts and workflow removed the major omissions; [Asgari et al. 2025](https://www.nature.com/articles/s41746-025-01670-7)). Grammar-constrained decoding gives zero probability to a key out of order, so schema order is part of the design ([explainer](https://dev.to/ji_ai/why-json-schema-field-order-breaks-structured-output-accuracy-2985)); that is our mistake in 7.2. LLM judges are nearly blind to absences (discrimination 0.50-0.63 against 0.79-0.94 for added content) and do better when asked to list the facts first and check each ([Omission Blindness](https://arxiv.org/abs/2608.31016)), consistent with our judge's weak completeness mode. LoRA at low rank learns less than full fine-tuning ([Biderman et al.](https://arxiv.org/abs/2405.09673)); we think capacity is a minor factor here.

## 8. What went wrong, and what we tried that failed

1. **The first baseline was nearly meaningless.** The draft prompt did not say how to write dates, the field names inside typed facts, or what `relationship` meant: safe-pass 7%. We rewrote it three times (v2-v4), changing only output format and naming conventions, never clinical content, then froze it. The prompt was shaped against the validation conventions, so the baseline is better than a first try and not expert-tuned.
2. **Our tools had bugs.** The renderer crashed on any date of birth that was not `YYYY-MM-DD`, and the judge silently skipped those calls (13 of 100 judged); the scorer was too strict ("milligrams" ≠ "mg": medication-with-dose read 12% when it was 80%). Both fixed; gold scored against itself stays 100% on every row, damaged gold is still caught (15 of 15 damage types).
3. **Quote stitching.** The base glued sentences together with "..." in 29 to 33 calls. We added a deterministic quote repair (never touches anything else; changes 0 quotes in the 100 gold summaries) and report it separately (E1r, G1r). The fine-tuned model needs it in 3 calls.
4. **The output schema made the first fine-tuned result wrong, twice.** First, the schema listed `certainty` second in every fact while the training targets have it last: after `type` the grammar forced `certainty`, which the model had learned means "fact finished", and medications fell to 2.7%. We reordered and re-ran both models. Second (found only during the medication analysis), the reordered list still disagreed with 5% of the gold facts (section 7.2); a better order disagrees with 0.3% and both models were re-run again. The selftest now fails above 1%.
5. **Speculative decoding made it slower.** n-gram speculation accepted 2.4 to 3.4 tokens per step but throughput fell from about 62 to 34-43 tokens/s (median 23 s instead of 14 s): vLLM 0.30 falls back to an older runner and disables asynchronous scheduling when it is combined with LoRA and constrained decoding. We lost time reading the slow run until the server log and metrics showed why. Not tried: the model-based drafter (MTP), emitting quote pointers instead of quotes, a faster GPU.
6. **The latency target was not reached.** Removing `explanation` (11% of the output) would still leave long calls near 19 s; removing `quote` (15%) would remove our evidence check. A faster GPU is the more reliable lever (an H100 has about four times the memory bandwidth; an estimate, not measured).
7. **Other errors seen on the earlier run:** hedged times ("twenty minutes earlier") the transcript does not support; one invented number (va-095) and one drug not in the call (va-059, "insulin"); 105 gold critical facts missing, many of them different phrasings; 115 extra facts, many true but not in the gold (so critical-fact accuracy partly measures imitating the gold's selectivity, which is why H19r is reported beside it).

## 9. Limits of this evidence

- 100 validation calls, synthetic, one author: bounds are wide (a point estimate of 95% would still have a lower bound near 89%). No test split; validation served monitoring, the epoch choice and the numbers.
- The judge is the same model family as the system it judges; its completeness mode is unvalidated on unseen data. The gold comparison is not identical to the design's "CFA" (no speaker or quote condition).
- Latency is 20 timed calls on one L40S, taken on the earlier-schema run; epochs 1 and 2 were not re-run on the corrected schema.
- Not done: learning-rate and rank sweeps, greedy-vs-sampling and thinking tests, HF-vs-vLLM adapter agreement check, repeat-run determinism, bootstrap intervals, preference tuning, the Not-Applicable gate, candidates table and retry in the production path, the demo video.

## 10. What to change if we fine-tune again

1. **Training targets:** one typed medication fact per drug (13 of 428 training facts have a dose in the sentence but not in the fact), the dose in the fact, a tablet count *and* a strength where both are said; keep garbled drug names as spoken with certainty "unclear".
2. **Candidates line in the input:** the drugs a lexicon finds in the transcript, so the model only decides whether to keep each (the design's candidates table, never built).
3. **Serving schema:** per-type schemas or no order constraint, so the grammar cannot fight what the model learned; keep the key-order test.
4. **A development split** (about 40 of the 500) for choosing the epoch and any hyper-parameter, so validation is used once at the end; run learning rate 1e-4 and a higher rank; evaluate all epochs on the final schema.
5. **Latency:** shorter output (templated explanations, quote pointers) or an H100-class GPU, then re-time.
6. **Independent evaluation:** a second judge from another model family or a human review of about 30 outputs before any claim about unseen data.
7. **Hygiene:** `expandable_segments`, checkpoint resume, optimiser state saved.

## 11. Reproduce

```bash
python3 code/data/validate_gold.py                 # 600 gold calls, 0 errors
python3 code/tests/test_validator.py && python3 code/tests/test_render.py
cd pipeline && python3 run_pipeline.py selftest    # rules, schema order, medication check
python3 run_pipeline.py matrix --systems base_v4_s3 finetuned_epoch3_s3      # final comparison from saved outputs
python3 dev/medsafety_eval.py && python3 dev/med_error_analysis.py            # medication analysis
python3 ../app/server.py                           # demo UI at http://localhost:8080 (replay mode needs no GPU)
```
Training and GPU runs: `finetune/README.md`, `pipeline/README.md`. Adapters: `finetune/runs/ft1/epoch_{1,2,3}/` (about 262 MB each, not in git); **use epoch 3**.
