# Final judge (v5): specification for the eval pipeline

Use these prompts and settings exactly. They were frozen before the confirmation run (results in `results_confirmation/`).

| Item | Value |
|---|---|
| Model | `google/gemma-4-12B-it-qat-w4a16-ct` served by vLLM (`--served-model-name gemma --max-model-len 16384`) |
| Decoding | temperature 0, thinking off (`chat_template_kwargs: {enable_thinking: false}`), JSON-schema constrained output, up to 3 tries (last try unconstrained, larger token limit) |
| Input to the judge | summary in the exact reference format (as rendered, with quotes and explanations) + the call transcript. Never the gold, the labels or any edit information |
| Faithfulness | 1 call: `prompts/v5_prompt_faithfulness.md`; output `{analysis, verdict, reason}`; FAIL if any statement is wrong or invented |
| Calibration | 1 call: `prompts/v5_prompt_calibration.md`; output `{analysis, problem_type, reason}` with problem_type in none / certainty / status / speaker; FAIL when the type is not "none". Report as an indicator |
| Completeness | needs the call's fact record. One checklist line per record item (`data/*/completeness_reference.jsonl` shows the format; `data/*/build_checklists.py` renders record items to lines). For each line: `prompts/v5_prompt_completeness_match.md`; if it says missing, a second look with `v5_prompt_completeness_recheck.md`. The summary FAILs if at least one item is missing after the second look |
| Cost per summary | 2 calls + 1-2 calls per checklist item (median 10 items), about 12-25 model calls |
| Not judged here | speaker attribution, quote validity, numbers vs transcript: the deterministic validators own those |

Files: `run_judge.py` (`--set first|confirmation`, or `--inputs/--reference/--out` for new data), `score.py`, `judge_lib.py` (the one JSON call), `results_first_set/`, `results_confirmation/` (each with `judge_outputs.jsonl` and `judge_report.md`). See `../README.md` for the method and version history.

```bash
# server (vLLM 0.30.0 on the L40S needed the FlashInfer sampler off)
export VLLM_USE_FLASHINFER_SAMPLER=0
vllm serve /workspace/models/gemma-4-12B-qat-w4a16-ct --served-model-name gemma --max-model-len 16384 --gpu-memory-utilization 0.90 --port 8000
# in another terminal
cd llm_judge/v5_final && python3 run_judge.py --set confirmation && python3 score.py --set confirmation
```
