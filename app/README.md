# Demo UI

A small web page and JSON API around the evaluation pipeline. **Python standard library only**: no install step.

```bash
python3 app/server.py            # then open http://localhost:8080
```

## What you can do

| Tab | |
|---|---|
| **Summarize** | Pick one of the 100 validation calls. **Replay** shows what the base model and the fine-tuned model (epoch 3) actually produced, with no GPU. **Live** sends any pasted transcript to a running model. The result has a status banner and five views: *Summary* (the rendered reference format, plus risk flags), *Evidence* (every bullet with its verbatim quote, cited turns and typed facts; hovering lights up those turns in the numbered transcript), *Checks* (every rule finding on the raw output, and what the automatic quote repair changed), *Compare with gold* (model against the hand-written summary), *Judge* (live mode only) |
| **Results** | The headline numbers of the final comparison, read from `pipeline/outputs/matrix_*.json`, with the honest note that the 95% and 15 s targets were not reached |
| **How it works** | The pipeline in five steps, and exactly what the judge validation did and did not show |

**The status banner is a safety gate, not a quality score.** PASS means no rule error survives automatic quote repair; it does not mean the summary is right (the rules cannot see a swapped drug or a missing item). NEEDS NURSE REVIEW means a rule error remains; FAILED means the output is not valid JSON.

## Live mode

The page calls an OpenAI-compatible server (vLLM) that serves the base model and the adapter. On the GPU box:

```bash
bash finetune/scripts/serve_adapters.sh finetune/runs/ft1      # serves the base as `gemma`, the adapters as ft1, ft2, ft3
```
Reach it from the machine running the UI, for example through an SSH port forward or your pod provider's HTTP proxy, then:

```bash
python3 app/server.py --llm-url http://localhost:8000/v1 --model ft3 --judge-model gemma
```
Options: `--port`, `--host`, `--prompt` (default the frozen `system_v4.md`), `--max-tokens`, `--finetuned-run` / `--base-run` (which saved outputs replay mode shows). Expect 10 to 30 seconds per summary (median about 14 s on an L40S).

Only the server's own host is listened on by default (`127.0.0.1`). It has no login. Do not expose it to a network with real patient data.

## The judge button

It runs the frozen judge (the base model) on the summary. For a validation call it uses the call's reference checklist (the mode that was validated for missing nurse actions and instructions). For a pasted transcript there is no reference, so the model writes its own checklist; the page says that this completeness check is **not validated**. Faithfulness is the judge's validated strength (kappa 1.00 on a fresh set of 40 items; small sample); see `../llm_judge/README.md`.

## Files

- `server.py`: the API (`/api/config`, `/api/cases`, `/api/case`, `/api/summarize`, `/api/judge`). It imports the pipeline's own code (`pipeline/pl/`): the renderer, the validators V1-V16, the quote repair and the judge, so the page shows exactly what the evaluation measures.
- `static/index.html`: the whole front end (one file, no external requests, works in light and dark mode). Handy for demos: `?case=va-005&run=1&view=checks` opens a call already summarized; `?tab=res` opens the results.

## Not in the UI

The production design also had a Not-Applicable gate before the model, a candidates table in the input and a targeted retry when a rule fails (architecture §5.2). They are not built; the UI applies the rules, the quote repair and the review gate only.
