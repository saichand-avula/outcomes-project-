# Saved runs

Every run of the pipeline on the 100 validation calls. Each folder holds `generations.jsonl` (what the model wrote, with latency and token counts), `validation.jsonl` (rule findings), `validation_repaired.jsonl` (after automatic quote repair, where present), `reference.jsonl` (comparison with the gold) and `judge.jsonl` (the frozen judge). `matrix_*.md/.xlsx/.json` are the comparison tables; `logs/` has the progress logs of the generation and judge runs.

**Use `base_v4_s2` and `finetuned_epoch3_s2` for the final comparison.** The others are kept as evidence of how we got there.

`med_errors.md` / `med_errors.json` list every gold medication a run got wrong, by type (made by `../dev/med_error_analysis.py`; read with REPORT §8.1).

| Folder | Model | Prompt | Constrained-decoding schema | Valid for comparison? |
|---|---|---|---|---|
| `base` | base | v1 (draft, no output format) | old key order | History only: v1 never defined dates or fact fields (G1 7%) |
| `base_v2` | base | v2 (exact output format) | old | History |
| `base_v3` | base | v3 (name, relationship wording) | old | History |
| `base_v4` | base | v4 (frozen) | old | Yes, the stronger baseline (G1 70%); schema differs from the fine-tuned runs |
| **`base_v4_s2`** | base | v4 | **fixed key order** | **Yes: the baseline we compare with** (G1 60%) |
| `finetuned_epoch2` | LoRA epoch 2 | v4 | old | **No. Invalid**: the schema forced a key order the model had not learned, so facts lost their names and doses (medications found 2.7%). Kept only as evidence of that bug |
| `finetuned_epoch2_s2` | LoRA epoch 2 | v4 | fixed | Yes |
| `finetuned_epoch1_s2` | LoRA epoch 1 | v4 | fixed | Yes, evaluated last: clearly weaker (G1 68%, 3 answers hit the token limit) |
| **`finetuned_epoch3_s2`** | **LoRA epoch 3** | v4 | **fixed** | **Yes: the chosen model** (G1 92%) |

Notes
- `matrix_finetuned_epoch1_s2_vs_finetuned_epoch2_s2_vs_finetuned_epoch3_s2.*` compares the three epochs side by side. Latency and first-token times were taken in a second pass (with streaming) over the same 20 calls; the first pass gave slightly different totals (REPORT §6.3).
- `latency_seq_s` inside a generations file is the one-request-at-a-time timing of 20 evenly spaced calls; `latency_s` of a parallel run is inflated by sharing the GPU and is not a latency figure.
- The scorer was corrected once (units, a stop word, name matching) after the first runs; the stored `reference.jsonl` of every run was recomputed with the corrected scorer.
- Rebuild any table from these files with `python3 run_pipeline.py matrix --systems <A> <B>` (run in `pipeline/`).
