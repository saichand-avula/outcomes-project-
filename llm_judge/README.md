# LLM-as-judge: validation of Gemma 4 12B as a semantic judge

Question: can the base model (`google/gemma-4-12B-it-qat-w4a16-ct`) tell a good clinical summary from a damaged one by meaning alone, with no deterministic checks? A judge is only used in the eval pipeline after it passes this check.

**Result (final judge = `v5_final`, prompts frozen before the confirmation run)**

| Rubric | First set, 50 items (prompts tuned on it) | Confirmation set, 40 fresh items (prompts frozen) | Use in the eval pipeline |
|---|---|---|---|
| Faithfulness (anything wrong or invented) | 96%, kappa 0.90, caught 12/12, false alarms 2/38 | **100%, kappa 1.00, caught 10/10, false alarms 0/30** | Validated; use as a metric |
| Completeness (against the fact record) | 96%, kappa 0.86, caught 8/9, false alarms 1/41 | **90%, kappa 0.61, caught 4/6, false alarms 2/34** | Validated for missing nurse actions and instructions (9/9 caught); unreliable for missing findings (3/6) |
| Calibration (hedging, planned vs done, speaker) | 86%, kappa 0.55, caught 6/8, false alarms 5/42 | **90%, kappa 0.55, caught 3/6, false alarms 1/34** | Planned-vs-completed only (6/6). Speaker swaps 3/6 and removed hedges 0/2: not reliable. Report as an indicator; speaker attribution stays with the code validators |

## Folders

| Path | Content |
|---|---|
| `data/first_set/` | 50 validation calls (25 clean, 25 edited): `judge_inputs.jsonl` (what the judge sees), `golden_labels.jsonl` (answers), `completeness_reference.jsonl` + `golden_completeness.jsonl` (fact-record checklists and removed items), `golden_review.xlsx` (readable), build scripts |
| `data/confirmation_set/` | 40 other validation calls (20 clean, 20 edited), same format, none of the first-set calls |
| `v1_single_prompt/` | Version 1: one prompt, all three rubrics. Prompt, runner, scorer, `results/` |
| `v4_fact_record_completeness/` | Version 4: completeness checked against the fact record. Prompts, runner, scorer, `results/` |
| `v5_final/` | **Final judge.** `prompts/`, runner, scorer, `judge_lib.py`, `results_first_set/`, `results_confirmation/`. See `v5_final/README.md` |

## Validation method

1. **Sample.** Random non-Not-Applicable validation calls (seed fixed). First set: 50. Confirmation set: 40 calls the first set never used (zero overlap).
2. **Edit half of the summaries.** Edits are applied to the gold summary JSON and re-rendered in the exact reference format. Clean summaries are the validated gold summaries and should PASS everything. Each edit is tagged with the rubric it should break:
   - completeness: remove an assessment, response or education item;
   - faithfulness: change a number, swap a drug name, add an invented finding, flip a negative into a positive;
   - calibration: write "Planned to…" as "Completed:", swap the Caller/Nurse label on a quote, remove a hedge ("the caller was unsure…").
   Some calls get two edits from different rubrics. Every edit was read by hand.
3. **Labels.** `expected` PASS/FAIL per rubric per item. Completeness is defined against the call's **fact record** (the hand-written list of required items, one checklist line each): a summary is complete if every record item is covered. This matches the architecture (the judge gets the fact record as reference). Defining it against the whole transcript was wrong: the gold summaries are complete against the record, not against every sentence said (versions 1-3, see below).
4. **Judge.** Greedy decoding, thinking off, JSON-schema output, up to 3 retries. The judge sees only transcript + summary (completeness: one checklist line + summary), never the labels or whether an item was edited.
5. **Score.** Per rubric: agreement, Cohen's kappa, edited items caught, clean items falsely flagged; detection by edit type; completeness also item by item; every disagreement listed with the judge's reason.
6. **Confirm.** Prompts were tuned over five rounds on the first set, so its scores are optimistic. The final prompts were then frozen and run once on the confirmation set. That result is the validation.

Decisions made after seeing results (stated so they are not hidden): (a) completeness is scored against the fact record instead of the whole call; (b) one data error found by the judge (`va-067`: "It's done" labeled planned) was fixed in the data and the sets rebuilt; (c) the report prints a second completeness figure that leaves out calls whose only edit is a changed drug or number, because a changed dose can reasonably count as a missing item. The strict figure is printed too.

## Version history

| Version | Change | First-set result (agreement / kappa / caught / false alarms) | Kept? |
|---|---|---|---|
| v1 | One prompt for all three rubrics; completeness against the whole call | faith 94% / 0.84 / 11/12 / 2/38 · compl 76% / 0.19 / 3/9 / 6/41 · calib 92% / 0.67 / 5/8 / 1/42 | Yes, baseline |
| v2 | One prompt per rubric; completeness as extract-facts-then-check | faith 96% / 0.89 / 12/12 / 2/36 · compl 27% / 0.05 / 8/8 / 35/40 · calib 90% / 0.64 / 6/8 / 3/40 | Removed: faithfulness gain only; completeness flagged almost every summary |
| v3 | Top-10 facts, each checked alone, re-check if missing | faith 96% / 0.90 · compl 34% / 0.08 / 9/9 / 33/41 · calib 74% / 0.34 / 6/8 / 11/42 | Removed: no gain; calibration got worse |
| v4 | **Completeness against the fact record** (the key fix: most v3 "false alarms" were real omissions relative to the whole call) | faith 96% / 0.90 · compl 78% / 0.46 / 8/9 / 10/41 · calib 72% / 0.31 / 6/8 / 12/42 | Yes, biggest improvement |
| v5 | Completeness = main point covered (secondary details optional); calibration names a problem type (none / certainty / status / speaker) so wrong values cannot fail it | faith 96% / 0.90 / 12/12 / 2/38 · compl 96% / 0.86 / 8/9 / 1/41 · calib 86% / 0.55 / 6/8 / 5/42 | Yes, **final** |

Raw outputs and reports of the kept versions are in their `results*/` folders. v2 and v3 were removed from the repository; this table is their record.

## What the judge is and is not trusted for

- Trusted: whether statements are supported by the call (wrong numbers, drugs, invented findings, flipped negatives); whether the nurse's actions and instructions are all covered.
- Weaker: missing findings when the topic still appears elsewhere in the summary (3 of 6 missed); removed hedges (0/2); swapped speaker labels (3/6).
- Not a judge task: speaker attribution and quote checks. The deterministic validators do those.
- Limits: 90 items in total, synthetic edits, one author for data and edits, completeness only possible where a fact record exists (synthetic validation data).

Note on data changes after the judge runs: `va-096` was corrected later (an invented "no chest pain" negative was removed from the data). The frozen golden files in `data/` keep the version that was judged, so rebuilding the first set now differs for that one item (`j-043`); the saved results stay valid for the text that was judged.

## Reproduce

```bash
python3 llm_judge/data/first_set/build_golden.py && python3 llm_judge/data/first_set/build_checklists.py            # rebuilds the first set byte for byte
python3 llm_judge/data/confirmation_set/build_golden_confirm.py && python3 llm_judge/data/confirmation_set/build_checklists.py
# on the GPU box, with the model served by vLLM (see v5_final/README.md):
cd llm_judge/v5_final && python3 run_judge.py --set confirmation && python3 score.py --set confirmation
```
