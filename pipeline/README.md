# Evaluation pipeline: rules + LLM judge + one common matrix

One self-contained folder (upload it to the GPU box). It takes call transcripts, gets a summary from a model, checks the summary with deterministic rules, checks its meaning with the frozen LLM judge, and puts everything in one table where every metric is a rate (0-100%, 100 = best). You run it for the base model, then for the fine-tuned model, and compare the two columns.

```
cases.jsonl ──► generate ──► generations.jsonl ──► validate (rules) ──► validation.jsonl ─┐
 (transcripts)   (GPU)        (what the model said)                  └► reference.jsonl ──┤──► matrix ──► matrix_*.md / .xlsx / .json
                                                  └─► judge (GPU) ───► judge.jsonl ───────┘
```

## 1. Data: what goes in, what comes out

**Case** (`data/val_cases.jsonl`, one per line). Unseen calls only need the first three fields; our validation calls also carry gold, which switches on the "H" rows of the matrix.
```json
{"id": "va-001", "transcript": "Nurse -> Juniper Ridge Hospice, this is Lena.\nCaller -> Hi, Lena. ...", "call_timestamp_utc": "2026-09-12T12:20:00Z",
 "gold_target": { ...validated gold summary JSON... },
 "reference_checklist": [{"n": 1, "fact": "Reason for call: ..."}, {"n": 2, "fact": "Medication: morphine, 20 mg/mL, ..., status: taking"}],
 "meta": {"category": "routine", "length": "short", "agency": "...", "noise": "low"}}
```
`reference_checklist` is one line per item of the hand-written fact record. Unseen data has no fact record, so the judge builds its own checklist from the transcript (section 4).

**What the model is asked to produce** (`prompts/system_v4.md`, frozen; schema in `pl/schema.py`): one JSON object, the same shape as the gold summaries.
```json
{"not_applicable": {"is_na": false, "reason": null},
 "identity": {"patient_name": {"value": "Mara Ellis", "certainty": "stated", "heard_as": [], "turns": [2]}, "patient_dob": {...}, "caller_name": {...}, "relationship": {...}, "callback_phone": {...}, "patient_pronoun": "her"},
 "chief_complaint": {"reason": "...", "speaker": "Caller", "turns": [14], "quote": "verbatim words", "explanation": "Documents ..."},
 "assessment": [{"text": "...", "speaker": "Caller", "turns": [12], "quote": "...", "explanation": "...", "facts": [{"type": "symptom", "name": "pain", "present": true, "severity": "8/10", "certainty": "stated"}]}],
 "response": [...], "education": [...],
 "risk_flags": [{"category": "uncontrolled_symptom", "turns": [12], "quote": "..."}]}
```
The transcript is sent numbered (`[T1] Nurse -> ...`) so the model can cite turns. Decoding is greedy with thinking off and, when the server accepts it, constrained to this schema.

**Intermediate files** (`outputs/<system>/`):

| File | One line per call | Key fields |
|---|---|---|
| `generations.jsonl` | what the model returned | `raw_text`, `parsed` (object or null), `parse_error`, `constrained`, `latency_s`, `prompt_tokens`, `completion_tokens`, `finish_reason`; after the `latency` stage also `latency_seq_s` and `ttft_seq_s` |
| `validation.jsonl` | what the rules found | `findings` (`rule`, `severity` ERROR/WARN/INFO, `path`, `message`), `counters` ({name: [ok, total]} for every check), `n_error`, `n_warn`, `final_flags` (model flags + rule flags), `rule_flags`, `na_score` |
| `reference.jsonl` | gold comparison (only if the case has gold) | `counters` ({metric: [matched, total]}) |
| `judge.jsonl` | what the judge said | `verdicts` (faithfulness, completeness, calibration: PASS/FAIL + reason), `extra.items` (each checklist item: present or missing, with the summary words that cover it), `completeness_mode` |

`outputs/matrix_<A>_vs_<B>.{md,xlsx,json}`: the common matrix and its breakdown by category, length and ASR-noise level.

## 2. What can be checked deterministically (rules V1-V16)

Rules use only the transcript and the model's output. No fact record or gold is needed, so they run on unseen calls too. `ERROR` = the output is not safe as it stands. `WARN` = a nurse should look. `INFO` is never scored.

| Rule | Checks | Severity |
|---|---|---|
| V1 | Output is valid JSON and matches the schema (types, enums, required keys) | ERROR |
| V2 | Not-Applicable consistency (reason, empty sections); clinical call has a chief complaint | ERROR / WARN |
| V3 | Every cited turn exists | ERROR |
| V4 | Every quote is verbatim in the cited turns (normalized); a near-miss is repairable | ERROR / WARN |
| V5 | Quote speaker matches the label of the quoted turn | WARN (a label can be a diarization error the model correctly overrode) |
| V6 | Every number in text and facts was spoken in the call; locality (cited turns +/-2) is reported as INFO | ERROR |
| V7 | Every drug name is in the call; a "corrected" spelling breaks the as-spoken policy | ERROR / WARN |
| V8 | Clinical terms (fever, fall, seizure, chest pain, rash, bleeding ...) in the summary appear in the call; loose synonyms only warn | ERROR / WARN |
| V9 | Identity values were spoken: name parts, DOB (year, month, day close together), 10-digit phone, relationship | ERROR / WARN |
| V10 | "Completed" needs a completion cue in the nurse's words; "planned" must not contradict "it's done"; text wording matches status | ERROR |
| V11 | A caller's hedge in the quote is kept (certainty unclear or softening word) | WARN |
| V12 | A negative finding is not rewritten as present | ERROR |
| V13 | Risk-flag rules vs the output's flags (rules fire on suicidal, breathing, escalation, medication, uncontrolled symptom, other urgent; negated phrases, questions, conditionals, read-backs and history are suppressed) | ERROR for suicidal/escalation (precision about 0.9), WARN for the rest |
| V14 | Not-Applicable decision vs a clinical-content score | ERROR / WARN |
| V15 | Coverage proxies: drugs mentioned but absent; nurse promised actions but response empty | WARN |
| V16 | Empty text, duplicate bullets | ERROR / WARN |

**How well the rules work** (`python3 run_pipeline.py mutation-study`): take 100 validated gold summaries, damage each in one specific way, and see whether the rules notice. Undamaged gold: 0 ERROR in all 600 calls (500 training, 100 validation).

| Defect | Caught as ERROR | Caught (WARN or ERROR) |
|---|---|---|
| Output cut off / missing section / invalid value / cited turn that does not exist | 100% | 100% |
| Quote from an unrelated turn / paraphrased quote | 100% | 100% |
| Drug swapped (in text or in a typed fact) | 100% | 100% |
| Patient name / caller name / DOB year / phone digit changed | 97-100% | 100% |
| Invented finding with a number (fever 101.5) | 100% | 100% |
| Invented finding from the term list (fall, seizure, rash, chest pain) | 57% | 100% |
| Planned flipped to completed (status only, or rewritten as "Completed:") | 100% / 87% | same |
| Negative finding rewritten as present | 100% | 100% |
| Number changed in text / dose changed in a fact | 87% / 80% | same |
| Clinical call marked Not Applicable | 93% | 93% |
| Quote with one word changed / speaker label flipped / duplicated bullet / suicidal flag with no suicidal wording | 0% (by design) | 100% |
| Hedge removed | 0% (by design) | 88% |
| Completed rewritten as planned | 33% | 33% |
| Risk flag dropped | 22% | 63% (only where a rule fires) |
| **Invented finding outside the term list / patient and caller names swapped / a bullet removed / a dose swapped with another number spoken in the call** | **0%** | **0-7%** |

The last row is the point of the LLM judge: the rules cannot see meaning. They are exact about what was said and who said it; they cannot tell whether a true number was attached to the wrong thing, or whether something is missing.

## 3. What the judge adds

The frozen v5 judge (`prompts/judge/`, validated in `llm_judge/`): faithfulness (anything wrong or invented), completeness (checklist items covered), calibration (hedges, planned vs done, speaker). On 40 fresh edited summaries: faithfulness agreement 100% (10/10 caught, 0/30 false alarms); completeness 90% (every removed nurse action or instruction found; removed findings missed 3 of 6); calibration 90% (planned vs completed 6/6; speaker swaps 3/6; removed hedges 0/2). So: faithfulness is a validated metric, completeness is validated for actions and instructions only, and calibration is an indicator.

The judge runs on the base model only. When the fine-tuned model is being evaluated, the judge is still the base model (self-preference caveat in architecture 6.3).

Completeness needs a checklist. Two modes:
- `reference` (our validation calls): one line per fact-record item. This is the mode that was validated.
- `transcript` (unseen calls, no fact record): the judge first lists up to 10 important facts from the transcript, then checks each. **Not validated.** It measures coverage of what the judge thinks matters. Both systems must use the same cached checklist (`outputs/checklists_transcript_mode.jsonl`), which the pipeline does automatically.

## 4. The matrix

Every row: a rate with `n/d`, a 95% lower confidence bound (Wilson), the source, an evidence level, and a mark when the rate reaches 95%. A point estimate of 95% on 100 calls has a lower bound near 89%, so the table shows both; "lower bound ≥95" is the strict claim.

| Group | Rows | Source |
|---|---|---|
| A. Output validity | valid JSON, schema, cited turns, quote validity, exact quotes, speaker | D |
| B. Grounding in the call | numbers, drug names, clinical terms, identity values | D |
| C. Wording vs meaning | planned/completed, negatives, hedges | D |
| D. Safety gates | Not-Applicable decision, risk flags the rules find (precise and loose), drug mentions covered | D |
| E. Whole call (rules) | E1 no ERROR; E2 no ERROR and no WARN | D |
| F. Meaning (judge) | faithful; completeness (item level and call level); calibrated | J |
| G. Pipeline | **G1 safe-pass** (no rule ERROR and judged faithful); G2 full-pass | DJ |
| H. Against gold | identity, medications (name, dose, unit), symptoms, negatives, vitals, actions (type, status), education, flags, Not-Applicable, bullet coverage, hallucinated medications, **H19 Critical-Fact Accuracy** | R |
| O. Operational | share of calls under 15 s (p50/p95 in the note), outputs not cut off | O |

Rules of the table: slot rows (B, C, D) are computed over outputs that parsed; whole-call rows count an unparseable or unrenderable output as a failure. Judge rows are computed over the calls the judge actually ran on, and the note says how many. Rows H need gold, so they appear only for our validation set.

**Fixed in advance (so we cannot pick the best-looking number afterwards):** the headline for unseen data is G1; the headline on our validation set is H19 (Critical-Fact Accuracy) and G1. Everything else is reported but is not the claim. The report states which rows reach 95%.

A "ceiling" column is useful: `fake-system --system gold` writes the gold summaries as if a perfect model had produced them. Rows like D2b (loose risk rules) and D3 (drug mentions) are below 100% even for gold, so they are read against that ceiling, not against 95%.

## 5. Run it

On the Mac (no GPU), to check the rules and the plumbing:
```bash
cd pipeline
python3 run_pipeline.py selftest                       # rules vs gold and vs damaged gold; must print "selftest OK"
python3 run_pipeline.py mutation-study --per 30        # the defect table above
python3 run_pipeline.py fake-system --system gold      # gold as a perfect model (ceiling column)
python3 run_pipeline.py fake-system --system damaged --damage number_changed_in_text:0.15,drug_swapped_in_fact:0.1,status_flipped_to_done:0.1
python3 run_pipeline.py validate --system gold && python3 run_pipeline.py validate --system damaged
python3 run_pipeline.py matrix --systems gold damaged
```

On RunPod (we used `/workspace/pipeline/pipeline`). Terminal 1, the server:
```bash
source /workspace/venv-vllm/bin/activate
export VLLM_USE_FLASHINFER_SAMPLER=0
vllm serve /workspace/models/gemma-4-12B-qat-w4a16-ct --served-model-name gemma --max-model-len 16384 --gpu-memory-utilization 0.90 --port 8000
```
Terminal 2, the base model with the frozen prompt:
```bash
cd /workspace/pipeline/pipeline
python3 run_pipeline.py selftest
python3 run_pipeline.py generate --system base_v4_s2 --prompt prompts/system_v4.md --url http://localhost:8000/v1 --model gemma --latency-n 0
python3 run_pipeline.py validate --system base_v4_s2
python3 run_pipeline.py judge    --system base_v4_s2 --workers 16 --url http://localhost:8000/v1 --model gemma
python3 run_pipeline.py latency  --system base_v4_s2 --prompt prompts/system_v4.md --model gemma --n 20
python3 run_pipeline.py matrix   --systems base_v4_s2
```
`generate` sends 16 requests at once (a few minutes for 100 calls; we did not time it); `latency` then times 20 evenly spaced calls one at a time, which is the only honest latency figure. **Always pass `--prompt`**: without it `generate` uses the old draft prompt v1.

The fine-tuned model: serve the base model with the adapters (`finetune/scripts/serve_adapters.sh runs/ft1` registers `ft1`, `ft2`, `ft3`), generate with the adapter, judge with the **base** model:
```bash
python3 run_pipeline.py generate --system finetuned_epoch3_s2 --prompt prompts/system_v4.md --model ft3 --latency-n 0
python3 run_pipeline.py validate --system finetuned_epoch3_s2
python3 run_pipeline.py judge    --system finetuned_epoch3_s2 --workers 16 --model gemma
python3 run_pipeline.py latency  --system finetuned_epoch3_s2 --prompt prompts/system_v4.md --model ft3 --n 20
python3 run_pipeline.py matrix   --systems base_v4_s2 finetuned_epoch3_s2            # side by side, with deltas
```
(`finetune/scripts/eval_adapter.sh ft3 _s2` does the first four lines for you.) New, unseen calls: put them in a `cases.jsonl` with `id`, `transcript`, `call_timestamp_utc` and pass `--cases that_file`. The rules, the judge (transcript mode) and rows A-G work; rows H need gold and are left out.

Measured on the L40S for 100 calls: base-model generation about 50 minutes one request at a time (parallel generation is much faster; not timed); the judge 370 s with 4 workers; the rules a few seconds.

## 6. Choices and limits to know about

- The rules are exact about what was said, not about what it means. The study above lists what they miss; the judge covers those, within its own limits (section 3).
- Speaker mismatch is a WARN: the prompt tells the model to attribute by meaning when a label looks wrong, and the rules only see labels.
- Risk-flag rules are a candidate generator. Suicidal and escalation rules are precise (about 0.9) and can raise an ERROR; the others (precision 0.4-0.5) only warn. The pipeline output carries `final_flags` = model flags plus rule flags, as in the architecture.
- The rules were developed on the training split only and checked on validation. Rule-based checks of the gold found real defects in the data, which were fixed (see below).
- The raw model output is what the headline rows score. The only repair step is the deterministic quote repair, reported separately (E1r, G1r). The targeted retry of the production design (architecture 5.2 step 6) is not implemented.
- Prompt history (the base model, 100 validation calls, G1 = safe-pass, H19 = Critical-Fact Accuracy):
  v1 (draft, no output-format section): G1 7%, H19 29%, because dates, fact fields and names were not specified.
  v2 (exact output format): G1 59%, H19 44% (49% after the scorer fixes). v3 (name and relationship wording): G1 65%, H19 51%.
  v4 (caller-name wording) is **frozen** and is the baseline to beat; the fine-tuned model is also run with `system_v4.md`.
  Only the output format and naming conventions were changed, never clinical content. The scorer was corrected once (units, a stop word, name matching) and gold still scores 100% on every row.
- **Schema key order bug (found on the first fine-tuned evaluation):** vLLM's constrained decoding enforces the schema's property order. The schema listed `certainty` second in a fact and `turns` before `heard_as`; the gold summaries have `certainty` last and `heard_as` before `turns`. A model trained on the gold order was forced to emit `certainty` right after `type`, closed the fact, and lost `name`, `dose` and the other slots (medications and vitals fell to about 3%). The schema now follows the gold order (`pl/schema.py`; 5.0% of gold facts still use another order, which the data itself contains), and the selftest checks it. Runs made before the fix (`base_v4`, `finetuned_epoch2` without a tag) used the old schema; the corrected runs carry the tag `_s2`.
- `generate` runs 16 requests at once by default; latency is then measured on `--latency-n` calls re-run one at a time. Use `--latency-n 0` while iterating.
- `latency --system X --prompt prompts/system_v4.md --model M --n 20` times 20 evenly spaced calls one at a time on an existing run and stores them in its generations; the matrix then reports latency from them. Run it for `base_v4_s2` (model `gemma`) and for the chosen adapter (model `ft3`) so both numbers come from the same procedure. It streams the answer, so it also records the **time to first token** (`ttft_seq_s`; one untimed warm-up call first, because the server compiles the JSON grammar on first use), and the matrix prints a Latency table with both.
- `validate` also writes `validation_repaired.jsonl` (near-match quotes replaced by the exact span, `pl/repair.py`); the matrix reports it as E1r and G1r next to the raw E1 and G1.
- Python 3.11 compatible; standard library only (`openpyxl` is optional, for the .xlsx).

## 7. Saved runs

`outputs/README.md` lists every saved run (which prompt, which schema, valid or not) and `outputs/logs/` has the progress logs. Final comparison: `outputs/matrix_base_v4_s2_vs_finetuned_epoch3_s2.{md,xlsx,json}`.

## 8. Data defects found by building this (all fixed in `data/authoring`)

| Defect | Where | Fix |
|---|---|---|
| 28 typed facts with junk keys from commas inside values ("maybe", "worse tonight" ...) | 26 calls | fragments removed; all 600 gold targets now match the schema |
| Nurse sends a nurse "within the hour / immediately" without an escalation flag | tr-332, tr-400, tr-416 | flag added to record, transcript tag and gold |
| "I'm going to put a note in the chart" labeled completed | tr-009, tr-025 | now planned |
| "It's done" labeled planned | va-067 | now completed |
| Summary says "acetaminophen" / "insulin" where the call said "Tylenol" / "the pump" | tr-058, tr-270 | as-spoken wording |
| A negative ("no chest pain") that nobody said | va-096 | removed |
