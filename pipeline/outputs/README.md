# Saved runs

Every run of the pipeline on the 100 validation calls. Each folder holds `generations.jsonl` (what the model wrote, with latency and token counts), `validation.jsonl` (rule findings), `validation_repaired.jsonl` (after automatic quote repair, where present), `reference.jsonl` (comparison with the gold) and `judge.jsonl` (the frozen judge). `matrix_*.md/.xlsx/.json` are the comparison tables; `logs/` has the progress logs of the generation and judge runs.

Codes such as G1 are rows of the evaluation table; REPORT.md §2 explains each in plain words (G1 = safe-pass rate: no rule error and judged faithful).

**Use `base_v4_s3` and `finetuned_epoch3_s3` for the final comparison** (the corrected serving schema). The others are kept as evidence of how we got there.

`med_errors.md` / `med_errors.json` list every gold medication a run got wrong, by type (made by `../dev/med_error_analysis.py`; read with REPORT §7).

| Folder | Model | Prompt | Constrained-decoding schema | Valid for comparison? |
|---|---|---|---|---|
| `base` | base | v1 (draft, no output format) | old key order | History only: v1 never defined dates or fact fields (safe-pass rate G1 7%) |
| `base_v2` | base | v2 (exact output format) | old | History |
| `base_v3` | base | v3 (name, relationship wording) | old | History |
| `base_v4` | base | v4 (frozen) | old | Yes, the stronger baseline (safe-pass rate G1 70%); schema differs from the fine-tuned runs |
| `base_v4_s2` | base | v4 | key order disagrees with 5.0% of gold facts | Superseded by `_s3` (safe-pass rate G1 60%) |
| `finetuned_epoch2` | LoRA epoch 2 | v4 | old | **No. Invalid**: the schema forced a key order the model had not learned, so facts lost their names and doses (medications found 2.7%). Kept only as evidence of that bug |
| `finetuned_epoch2_s2` | LoRA epoch 2 | v4 | fixed | Yes |
| `finetuned_epoch1_s2` | LoRA epoch 1 | v4 | fixed | Yes, evaluated last: clearly weaker (safe-pass rate G1 68%, 3 answers hit the token limit) |
| `finetuned_epoch3_s2` | LoRA epoch 3 | v4 | key order disagrees with 5.0% of gold facts | Superseded by `_s3` (safe-pass rate G1 92%); still the set for the epoch comparison and the latency timing |
| `base_v4_s3` | base | v4 | **corrected key order** (0.3% disagree) | **Yes: the baseline to compare with** (safe-pass rate G1 65%) |
| **`finetuned_epoch3_s3`** | **LoRA epoch 3** | v4 | **corrected** | **Yes: the final model** (safe-pass rate G1 91%; not timed yet) |
| `finetuned_epoch3_s3_net`, `base_v4_s3_net` | the same outputs after the medication safety net (`run_pipeline.py net`) | v4 | corrected | Yes: typed medication facts added or completed; summary text and judge verdicts unchanged (medication names found 65 → 69 of 75 for the fine-tuned model) |

Notes
- `matrix_finetuned_epoch1_s2_vs_finetuned_epoch2_s2_vs_finetuned_epoch3_s2.*` compares the three epochs side by side. Latency and first-token times were taken in a second pass (with streaming) over the same 20 calls; the first pass gave slightly different totals (REPORT §6.3).
- `latency_seq_s` inside a generations file is the one-request-at-a-time timing of 20 evenly spaced calls; `latency_s` of a parallel run is inflated by sharing the GPU and is not a latency figure.
- The scorer was corrected once (units, a stop word, name matching) after the first runs; the stored `reference.jsonl` of every run was recomputed with the corrected scorer.
- Rebuild any table from these files with `python3 run_pipeline.py matrix --systems <A> <B>` (run in `pipeline/`).
