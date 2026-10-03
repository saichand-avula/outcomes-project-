# Clinical Summary Generation Using an Open-Source LLM

Turns a nurse-line call transcript into a structured clinical summary with Gemma 4 12B (QAT W4A16) plus a LoRA adapter, then renders it into the exact reference format and checks it with deterministic validators. Design: [architecture.md](architecture.md). Build order and pass criteria: [plan.md](plan.md).

## Status

| Part | State |
|---|---|
| Dataset | **Done.** 500 training + 100 validation calls, hand-authored, 0 validator errors and 0 warnings, no name/DOB/phone shared across splits |
| Authoring tools, gold validator, renderer | Done (`code/data/`, `code/common/`) |
| System prompt | Draft v1 (`prompts/system_v1.md`), untested |
| Model serving, baseline, pipeline validators, API/UI | Not started |
| LoRA fine-tuning, evaluation, LLM judge, report, demo | Not started |

## Dataset at a glance

- **Splits:** Training 500, Validation 100. No separate evaluation split; the 5 provided real calls are not used as data. Validation holds out two agencies (Juniper Ridge Hospice, Northstar Home Health).
- **Categories (train / validation):** routine 80/16 · ambiguous 60/12 · ASR-error 60/12 · medication 90/18 · supply 60/12 · high-risk 100/20 · not-applicable 50/10.
- **Length mix:** about 72% short, 12% medium, 16% long (train 360/60/80, validation 73/11/16). Minimums: short ≥ 65 lines, medium ≥ 85, long ≥ 105; Not-Applicable calls are exempt.
- **How it was made:** every call is written by hand (fact record → transcript with per-turn fact tags and logged ASR noise → gold summary). No random sampler, templates or external API. Every call must pass `code/data/validate_gold.py`.
- **Open it:** `data/dataset_overview.xlsx`. The Analysis sheet has the sizes, coverage charts and the case checklist; Calls, Facts, Transcripts, Noise and Summaries show every call; Validator shows rule results.

## Layout

| Path | Content |
|---|---|
| `data/authoring/{train,val}/*.yaml` | Source of truth, one file per call. Conventions: [data/authoring/README.md](data/authoring/README.md) |
| `data/{facts,transcripts,gold}/{train,val}.jsonl` | Compiled fact records, tagged transcripts with noise logs, gold summaries |
| `data/sft/{train,val}.jsonl` | `{id, transcript, call_timestamp_utc, target}`; the system prompt is not inside |
| `data/dataset_overview.xlsx` | Generated overview and readable data |
| `data/SHA256SUMS` | Hashes of compiled files |
| `prompts/system_v1.md` | System prompt, kept separate from the data |
| `code/train/batching.py` | Stratified SFT batch schedule (`data/sft/batch_schedule.json`) |
| `code/data/` | `validate_gold.py`, `coverage.py`, `realism.py`, `compile.py`, `build_workbook.py` and authoring helpers |
| `code/common/` | Loader, renderer, tall-man lettering, text normalization |

## Reproduce the data checks

```bash
python3 code/data/validate_gold.py      # expect: validated 600 calls: 0 errors, 0 warnings
python3 code/data/coverage.py           # category, length and tag quotas
python3 code/data/dupcheck.py          # cross-split near-duplicate check (5-gram Jaccard)
python3 code/data/compile.py            # JSONL + SFT + SHA256SUMS (refuses on validator errors)
python3 code/data/build_workbook.py     # data/dataset_overview.xlsx
```
