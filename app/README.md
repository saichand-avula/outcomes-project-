# Demo UI

A web page and JSON API around the evaluation pipeline. **Python standard library only**: no install step.

```bash
python3 app/server.py            # then open http://localhost:8080
```

## The four tabs

| Tab | What it is for |
|---|---|
| **Examples** | The 100 validation calls with outputs **computed beforehand**; no model or GPU needed. Pick a call from the list (green / amber / red dot = pass / needs review / failed), switch between the fine-tuned and the base model, read the numbered transcript, and see the result in its own panel: *Summary*, *Evidence* (every bullet with its verbatim quote and typed facts; hovering lights up the cited turns), *Rule checks* (every finding and what the quote repair changed), *Base vs fine-tuned vs gold* (three columns), *Judge* (needs a model server) |
| **Try your own transcript** | Paste any transcript (or start from a sample) and send it to the **live model**. Separate input and result panels; the result shows time to first token and total time. Needs a model server (below); otherwise the tab says so and the button is disabled |
| **Results** | Read from `pipeline/outputs/matrix_*.json` and `med_errors.json`: the four metrics the assignment names (with bars against the 95% line and the 95% confidence bound), time to first token and total response time, the epoch 1 / 2 / 3 comparison, and the medication error breakdown. States plainly that the 95% and 15 s targets were not reached |
| **How it works** | The five pipeline steps, how the judge was validated and what it can be trusted for, and what the PASS banner does and does not mean |

**The status banner is a safety gate, not a quality score.** PASS means no rule error survives automatic quote repair; it does not mean the summary is right (the 16 rules cannot judge whether a drug or dose is missing). The **automatic medication check** (`pipeline/pl/medsafety.py`) turns a PASS into NEEDS NURSE REVIEW when the caller said a drug (with a number, or twice) that the summary never mentions, as for lisinopril in `va-039`; it also adds a typed fact for a drug the summary names without one and copies a stated dose into the fact, both listed under *Rule checks*. NEEDS NURSE REVIEW also means a rule error remains; FAILED means the output is not valid JSON.

## Live model (for "Try your own transcript")

The page calls an OpenAI-compatible server (vLLM) that serves the base model and the adapters. On the GPU box:

```bash
bash finetune/scripts/serve_adapters.sh finetune/runs/ft1      # serves the base as `gemma`, the adapters as ft1, ft2, ft3
python3 app/server.py --llm-url http://localhost:8000/v1 --model ft3 --judge-model gemma
```
Options: `--port`, `--host`, `--password`, `--prompt` (default the frozen `system_v4.md`), `--max-tokens`, `--finetuned-run` / `--base-run` (which saved outputs the Examples tab shows).

## Showing it to other people from the RunPod pod

The pod only exposes Jupyter, so use a temporary tunnel (the pod connects outwards; no port has to be exposed). With vLLM already serving on the pod:

```bash
unzip -o ui.zip -d /workspace/ui && cd /workspace/ui        # ui.zip = app/ + pipeline/ (a fresh folder: do not unzip over the pod's own pipeline)
bash app/serve_on_pod.sh
```
It starts the UI on `0.0.0.0:8080` with a **random password**, downloads `cloudflared` once, and prints a `https://….trycloudflare.com` link and the password. Send both to the viewers; Ctrl+C closes the link. Anyone with the link and password can use the pod's GPU, so use only synthetic transcripts, never real patient data, and stop it afterwards.

Without a password the server listens on `127.0.0.1` only and has no login. Do not expose that mode to a network.

## Files

- `server.py`: the API (`/api/config`, `/api/cases`, `/api/case`, `/api/summarize`, `/api/judge`, `/api/results`). It imports the pipeline's own code (`pipeline/pl/`): the renderer, the validators V1-V16, the quote repair and the judge, so the page shows exactly what the evaluation measures. The pass / review / failed dot of every example is computed in the background after start-up (about 15 s).
- `static/index.html`: the whole front end (one file, no external requests, light and dark mode). Demo shortcuts: `?tab=res`, `?case=va-039&view=compare`.
- `serve_on_pod.sh`: UI + password + tunnel in one command.

## Not in the UI

The production design also had a Not-Applicable gate before the model, a candidates table in the input and a targeted retry when a rule fails (architecture §8). They are not built; the UI applies the rules, the quote repair and the review gate only.
