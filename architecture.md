# Architecture — Clinical Summary Generation with Gemma 4 12B (QAT W4A16)

Oct 4, 2026

> **Outcome (4 Oct 2026).** The design below was built and run. Fine-tuning improved safe-pass from 60% to 92% and critical-fact accuracy from 56.8% to 81.6%, but **neither reached the 95% target and p95 latency was 19.1 s against 15 s**. Sections marked **Outcome** record where reality differed from this plan; the full account, including everything that failed, is in [REPORT.md](REPORT.md). Not built from this design: the Not-Applicable gate before the model, the candidates table in the input, the targeted retry (§5.2); the demo UI in `app/` applies the rules, the quote repair and a review gate only.

## 0. Summary

We author structured fact records, write natural call transcripts from them (ASR noise included and logged), and write a gold clinical summary for each one. Code checks every gold summary against its fact record and transcript. Gemma 4 12B is fine-tuned with a rank-16 LoRA to map **transcript → structured summary JSON**. Code renders that JSON into the exact reference format. In production, deterministic validators check every quote, number, drug, identity field and action status against the transcript. Not-Applicable detection and risk flags combine rules with the model. Base Gemma 12B serves offline as a secondary judge of semantic faithfulness, because deterministic checks cannot verify meaning.

```text
════════ DATASET CONSTRUCTION (offline, authored) ════════

 Scenario blueprint (planned coverage, not random)
          │
          ▼
 Fact record ─────────────────────────────────────────────┐  ground truth
          │                                                │
          ▼                                                │
 Transcript written from the facts                         │
   • every turn tagged with the fact_ids it expresses      │
   • ASR noise written in, every event logged              │
          │                                                │
          ▼                                                ▼
 Gold summary JSON  (values, status, certainty, turns come from facts + noise log;
          │           prose and explanations are written)
          ▼
 Gold validator (code): fact record ⇄ transcript ⇄ gold, both directions
          │  fail → fix and re-check (never shipped failing)
          ▼
 data/  facts · transcripts · gold · sft   (+ dataset_overview.xlsx generated as a view)


════════ TRAINING ════════

 SFT row = {transcript, target JSON}       system prompt = separate file (editable)
          │
          ▼
 Training script assembles: [system prompt file] + [preprocess(transcript)] → [target]
          │
          ▼
 LoRA r16 on Gemma 4 12B (BF16 dequantized from the mandated checkpoint)


════════ PRODUCTION (request path) ════════

 Transcript (+ call timestamp metadata)
      │
      ▼
 Pre-process: turn IDs, spoken-number candidates, identity/drug candidates
      │
      ├──► Not-Applicable rule gate (clear cases skip the LLM)
      ▼
 Gemma 12B + LoRA on vLLM, JSON-schema constrained, greedy, thinking off
      │
      ▼
 Deterministic validators V1–V12   +   risk rules (union with model flags)
      │
  ┌───┴──────────────┐
 PASS               FAIL → ≤1 targeted retry (if latency budget allows)
  │                  └─► still failing: remove item, needs_nurse_review = true
  ▼
 Renderer → exact reference text  +  flags/validation report in API response


════════ OFFLINE EVALUATION ════════

 Validation transcripts ─► base Gemma ─► summary A ┐
                 └─► Gemma+LoRA ─► summary B ┤
                                             ├─► deterministic metrics vs fact records (headline)
                                             └─► base Gemma 12B judge, given transcript + fact record
                                                 (semantic faithfulness / completeness / distortion)
```

## 1. Three notions of truth

| Component | Fact record | Transcript | Notes |
|---|:-:|:-:|---|
| Transcript writing | ✅ | — | Transcript is written *from* the facts |
| Gold summary writing | ✅ | ✅ | Values from facts; quotes and turns from transcript |
| Gold validation | ✅ | ✅ | Both directions (§2.6) |
| SFT input | ❌ | ✅ | Model never sees the fact record |
| Production inference + validation | ❌ | ✅ | **Transcript is the source of truth** |
| Deterministic eval metrics | ✅ | ✅ | Set comparison against the fact record |
| Gemma judge | ✅ (reference) | ✅ | Reference-guided judging (§6.3) |

- **Synthetic data:** fact record = ground truth.
- **Production:** transcript = source of truth.
- **Semantic evaluation:** transcript + summary (+ fact record as reference) = judge input.

## 2. Synthetic data construction

### 2.1 Who writes the data, and why

Claude (Opus 5.5 and Sonnet 5.5) writes every fact record, transcript and gold summary in this repository, in batches. There are no random samplers, templates or external API calls.

| Decision | Alternative rejected | Reason |
|---|---|---|
| Hand-authored, diversity planned up front by a scenario blueprint | Random sampler + templates (earlier pipeline) | The earlier template-voiced data was measurably less natural than the 5 real calls: fewer short caller turns (24.6% vs 33.4%), fewer dangling fragments (4.7% vs 8.3%), and spoken-number density nearly double (49.5 vs 27.9 per 1K tokens). The rule layer also hit 100% flag recall because the voicer spoke the lexicon's own phrases, which proved consistency, not generalization [VERIFIED: earlier AUDIT.md, in git history] |
| No external API | Frontier API as teacher | Student budget; also avoids provider terms that restrict training competing models on outputs |
| Code validates, but does not generate | No validation | Hand-written gold can contain errors. The provided reference summaries do (§2.5) |

Known limitation, stated in the report: train and validation share one author family, so style can leak between them. Mitigations are in §2.7.

### 2.2 Dataset sizes and length mix

| Split | Calls | Short/normal (72%) | Medium (12%) | Long (16%) |
|---|---|---|---|---|
| Train | 500 | 360 | 60 | 80 |
| Validation (held out) | 100 | 73 | 11 | 16 |

**Final split decision:** Train 500 + Validation 100. There is no separate evaluation split and the 5 provided real calls are not used as data (their reference summaries are used only to define the output format). Validation is the held-out set for checkpoint selection and for the reported baseline-vs-fine-tuned numbers; the fixed LLM judge scores it. Validation has its own patients, callers, DOBs and phones, plus 26 calls from two agencies (Juniper Ridge Hospice, Northstar Home Health) that never appear in train. Validation is one medium call short of the 12% plan (11 instead of 12).

Length buckets (v2 regime, set after the first pilot proved too short against the 5 real calls, which run 2,370–13,219 characters, mean 8,245). Not-Applicable calls are exempt from the minimums:

| Bucket | Characters | Minimum lines | Purpose |
|---|---|---|---|
| Short/normal | 4,500–9,000 | 65 | Typical triage call |
| Medium | 7,500–12,500 | 85 | Multi-issue calls |
| Long | 10,500–18,000 | 105 | Real-call realism: chart reading, chatter, interruptions. Drives long-call p95 latency |

| Size decision | Evidence |
|---|---|
| Train 500 | LoRA matches full fine-tuning while the dataset fits within adapter capacity ([Thinking Machines 2025](https://thinkingmachines.ai/blog/lora/)). On a clinical-scribe SFT task, rank ≥ 8 already had enough capacity at 1K examples and stayed equal to full fine-tuning up to 30K ([Baseten 2025](https://labs.baseten.co/articles/practical-lora-research)). LIMA showed that ~1K curated examples teach format and style ([Zhou et al. 2023](https://arxiv.org/abs/2305.11206)). Our task is one format in one domain, so a few hundred clean examples are a reasonable start; the validation curve (epochs 1–3) tells us whether more would help |
| Validation 100 | Enough to choose among 3 sweep runs and tune the prompt; ≥ 10 calls per category (per-category numbers are still noisy) |
| Reporting on the same 100 | Wilson 95% lower bound [VERIFIED: computed]: observed 100% → 96.3%; 99% → 94.6%; 98% → 93.0%. n = 100 supports a "≥ 95%" claim on the transcript-level pass rate only at ~100%, so the headline is the fact-level CFA, which has thousands of slots (cluster-bootstrap CIs). Checkpoint selection also uses this set (3 candidates), so a small optimism is possible and is stated in the report |

### 2.3 Scenario categories

Each call has one primary category plus secondary tags. The counts cover every case type required by assignment task 3.

| Primary category | Train | Validation | Subtypes / what it tests |
|---|---|---|---|
| Routine | 80 | 16 | Symptom update, general question, visit scheduling with clinical content |
| Ambiguous | 60 | 12 | Caller unsure, contradictions, self-corrections, vague timelines |
| ASR-error heavy | 60 | 12 | Garbled drugs, names, numbers; speaker-label errors |
| Medication | 90 | 18 | Dosing, timing, missed/double dose, side effects, crushing/route, liquid concentrations, patches, stopped meds |
| Supply request | 60 | 12 | Refills, DME (oxygen, bed, commode), wound/catheter/incontinence supplies, delivery timing |
| High-risk escalation | 100 | 20 | Uncontrolled symptom, medication concern, suicidal statement, breathing concern, escalation request, plus clinical emergencies (sepsis, GI bleed, head injury, overdose, suspected abuse) |
| Not Applicable | 50 | 10 | Wrong number, disconnected before content, billing/admin only, test/silent call, non-clinical scheduling, sales/robocall, survey, job inquiry, records request |
| **Total** | **500** | **100** | |

**Status: all 600 calls are written and pass the gold validator with 0 errors and 0 warnings** (every category quota above is met exactly). Authoring was sequential, one call at a time, in batches. `data/dataset_overview.xlsx` shows the counts, the case-coverage checklist and every call's facts, transcript, noise and summary.

Secondary diversity axes (relationship, age group, agency type, identity patterns, medication phenomena, action-status traps, negation traps, conversational noise, clinical domain) each carry a minimum quota, checked by code. The quotas are in `plan.md` §2.

### 2.4 Artifacts and the fact table

```text
data/
  authoring/{split}/{call_id}.yaml    hand-written source: setup, facts, tagged transcript, noise log, gold
                                      (compiled by code into the JSONL files below; easiest file to review)
                                      (the one-line scenario brief is the `blueprint:` field in each file)
  facts/{train,val}.jsonl             canonical fact records (ground truth)
  transcripts/{train,val}.jsonl       turns[] with speaker, text, fact_ids; noise_events[]
  gold/{train,val}.jsonl              gold JSON + alignment + rendered reference text
  sft/{train,val}.jsonl               {id, transcript, call_timestamp_utc, target}; NO prompt
  dataset_overview.xlsx               generated view: Analysis (charts), Calls, Facts, Transcripts, Noise, Summaries, Validator
  SHA256SUMS                          hashes of the compiled files
```

- **YAML is the source, JSONL is compiled from it, the xlsx is a generated view** (`code/data/compile.py`, `code/data/build_workbook.py`). Nothing downstream is edited by hand.
- **Fact-record schema** (the former `fact_table_schema.xlsx` was retired; the Facts and Calls sheets of the overview workbook show it in use). Changes made from the original template:
  - `noise_seed` becomes `noise_event_count`: noise is authored and logged, not seeded.
  - `transcript_generator` = `claude-opus-5.5-authored` or `claude-sonnet-5.5-authored` (90 and 510 calls).
  - Call Setup gains `length_bucket`, `secondary_tags`, `agency_type`, `patient_age_group`, `caller_is_patient`, `speaker_label_errors`, `crosstalk`, `offtopic_chatter`.
  - Chief Complaint gains `patient_pronoun`.
  - Pertinent negatives are Assessment rows with `item_type = pertinent_negative` and `symptom_present = false`.
  - **`*_true` vs `*_spoken`.** `*_true` is the scenario's real-world value, used only to analyze whether noise misled the model. `*_spoken` is the **transcript-supported value the summary must contain** under the source-grounded policy (§3.3), with `*_certainty` alongside. Scoring uses `*_spoken` + `*_certainty`.

### 2.5 Transcript and noise authoring

Each transcript is written directly in its final, noisy form, in the real calls' format (`Nurse -> …` / `Caller -> …`). It is stored as turns with `fact_ids` and a `noise_events` log. Writing the final form directly means turn IDs never need remapping.

The noise types below are taken from what the 5 real calls actually contain, so we imitate observed errors rather than invent a noise model:

| Noise type | Observed in the real calls | Effect on gold |
|---|---|---|
| Numbers as words; digit-by-digit phones; numeric DOBs ("two thirteen thirty-three") | All 5 calls | None if unambiguous; `unclear` if conflicting |
| Name drift across repetitions; spelled names | Nadine / Noreen / Norine → "Nora Quinn"; Naomi Mercer → "Naomi Marlowe"; Ethan / Etta | Final self-stated value = stated; unresolved conflict = `unclear` with alternatives |
| Drug mishearings | `Phalarisipham`, `Ampatripoline`, `tamifluoln`, "hell doll", `Metroforum`, `carfentanil` | Governed by the source-grounded value policy (§3.3): confidently stated → summarized as stated; conflicting mentions → `unclear`; explicit resolution in the call → resolved name |
| Late answers / answers split across turns | Example 1, DOB and phone answers | Gold cites all supporting turns |
| Speaker-label (diarization) errors | "My son is at home." inside a Nurse turn (example 4) | Attribution follows meaning; gold notes it |
| Crosstalk to patient / background | "Dad, wait! … you're gonna fall" | Must not become a clinical fact |
| Off-topic chatter | Cat conversation (example 2) | Must not appear in summary |
| Fillers, repeats, fragments, dropped words | All 5 calls | Quotes stay verbatim |
| Chart-reading distractors | Example 2 nurse reads ~15 meds | Only meds discussed as taken/stopped/relevant appear |

`[inaudible]` tokens are deliberately **not** used: none of the 5 real ASR transcripts contain them. Clinical ASR error research ranks substitutions in drug names, doses and negations as the dangerous errors ([AssemblyAI](https://assemblyai.com/blog/ai-transcription-accuracy-pharmaceutical-drug-names); [Mani et al. 2020](https://aclanthology.org/2020.nlpmc-1.2)), so the noise budget concentrates there.

### 2.6 Gold summaries and the gold validator

Gold is written after the transcript, from the fact record plus the noise log. Values, `certainty`, `status` and `turns` come from the record and tags; the prose and explanations are written to match the reference style.

**Why not "teacher summarizes the transcript, then check against the transcript"?** Transcript-only checks confirm that words exist, not that the right facts were captured. The provided references show both gaps:
- Example 5 supports its chest-pain bullet with "No, no, I don't. I don't. I. I mean, I sent him to school." That quote is in the transcript, so a transcript check passes it, yet it does not establish the claim.
- Example 2's Assessment lists Lisinopril, Albuterol and Proscar as stopped. The nurse only read them from the chart, and the caller said "he mainly stopped all of the meds", so per-drug status is an inference.

A fact record states exactly which facts exist and with what status. Checking gold against it in both directions (G7/G8) catches omissions, extras and over-inference that transcript checks miss. (`carfentanil` and `ibuprofen` are **not** treated as errors: under the source-grounded policy, §3.3, single confident mentions are summarized as stated.)

| Gold check (these G-codes belong to the gold validator, not to the evaluation table's G rows) | Rule |
|---|---|
| G1 | Valid against the output JSON schema |
| G2 | Every quote is a verbatim span (after normalizing case, punctuation and immediate repeats) of its cited turns; cited turns belong to the stated speaker |
| G3 | Every number in text and facts appears in the cited turns, after spoken-number normalization |
| G4 | Every drug in facts appears verbatim in its evidence turns, equals the record's `medication_name_spoken` (the policy-expected form, §3.3), and carries the record's certainty |
| G5 | Identity values and certainty equal the fact record |
| G6 | Action `status` equals the record; `planned` wording uses "Planned to …" |
| G7 | **Coverage:** every record fact maps to ≥ 1 gold item |
| G8 | **No extras:** every gold fact maps to a record fact |
| G9 | Gold risk flags equal record `flag_required` flags |
| G10 | Every record fact's surface value appears in at least one turn tagged with it |
| G11 | No untagged clinical content: drug-lexicon hits or dose-like numbers in untagged turns are flagged for review |
| G12 | The rendered text parses back into the reference format; length matches the bucket |

Because the author can fix errors, a failing record is corrected and re-checked; nothing ships failing. We report how many records needed fixing per check. You review a random 20 by hand as an independent check.

### 2.7 Leakage control

- Patient names, DOBs and phone numbers are unique across splits. Phones use the NANP fictional range `NXX-555-0100…0199` with varied area codes, as the real examples do (`202-555-01xx`).
- **Validation is held out by construction.** It holds out 2 agency names (Juniper Ridge Hospice, Northstar Home Health: 26 calls), and every patient name, DOB and callback phone is unique across splits (`validate_gold.py` fails on any collision). 49 surnames occur in both splits with different first names; this is not treated as a leak.
- Near-duplicate check across splits: a line-level scan found one shared generic sentence (a suicide-screening question), and `code/data/dupcheck.py` (character 5-gram Jaccard, threshold 0.5) found a near-identical pharmacy-robocall pair (va-074 ~ tr-412, 0.45) that was rewritten; the closest pair is now 0.36.
- The 5 provided real calls are not used as data. A fully out-of-author check is a documented limitation; the fixed LLM judge and the deterministic validators are the independent signals.

## 3. Output design

### 3.1 JSON then render, in the exact reference format

The model emits schema-constrained JSON. A deterministic renderer produces the reference text. Typed fields are what make the safety rules checkable by code, and the renderer guarantees the format.

```json
{
  "not_applicable": {"is_na": false, "reason": null},
  "identity": {
    "patient_name":   {"value": "Mara Ellis", "certainty": "stated", "heard_as": [], "turns": [2, 3]},
    "patient_dob":    {"value": "1951-06-04", "certainty": "stated", "heard_as": [], "turns": [3, 4]},
    "caller_name":    {"value": "Nina", "certainty": "stated", "heard_as": [], "turns": [2]},
    "relationship":   {"value": "daughter", "certainty": "stated", "turns": [7]},
    "callback_phone": {"value": "2025550101", "certainty": "stated", "turns": [8, 9]},
    "patient_pronoun": "her"
  },
  "chief_complaint": {
    "reason": "Requested guidance on whether to administer LORazepam and morphine together or which medication to give first for recurrent pain.",
    "speaker": "Caller", "turns": [14], "quote": "So I wanted to know if I could give her the lorazepam, the morphine first, maybe, or just both together.",
    "explanation": "Documents the medication-administration question prompting the call."
  },
  "assessment": [
    {"text": "...", "speaker": "Caller", "turns": [12], "quote": "...", "explanation": "...",
     "facts": [{"type": "symptom", "name": "pain", "present": true, "severity": "8-9/10", "certainty": "stated"}]}
  ],
  "response":  [ {"text": "Planned to submit refill requests ...", "...": "...",
                  "facts": [{"type": "action", "action_type": "refill_request", "status": "planned", "certainty": "stated"}]} ],
  "education": [ {"...": "..."} ],
  "risk_flags": [{"category": "uncontrolled_symptom", "turns": [12], "quote": "about an eight-nine"}]
}
```

Fact types: `symptom`, `pertinent_negative`, `medication` (name, heard_as, strength, dose, unit, route, frequency, prn, last_dose, supply, med_status), `vital`, `action` (action_type, status ∈ planned | completed | advised, target, timeframe), `education`, `context`. Every fact has `certainty` ∈ stated | unclear.

### 3.2 Renderer rules

- **Identity sentence** is built by code from `identity`: `Patient {name}, DOB {MM/DD/YYYY}. Patient's {relationship}, {caller}, calling on {his/her/their} behalf, ({ddd})-ddd-dddd. {reason}`. Variants: calling for self, facility staff, and an unclear field (`DOB unclear (heard as 02/13/1983 and 02/13/1933)`). Formats match the references (`06/04/1951`, `(202)-555-0101`) [VERIFIED: examples].
- **Timestamp line** `[YYYY-MM-DD HH:MM UTC]` comes from request metadata. It never appears in any transcript, and all 5 references use the same value [VERIFIED: examples].
- **Bullets:** `• {text}` / `  {Caller|Nurse}: "{quote}"` / `  Explanation: {explanation}`. Sections in order: Chief Complaint, Assessment, Response, Education.
- **Tall-man drug names** (`LORazepam`, `HYDROmorphone`, `traMADol`, …) are applied by code from the FDA/ISMP Tall Man list. References use `LORazepam` but plain `morphine`, which is consistent with that list [VERIFIED: examples].
- **Empty section:** `• None documented during call.`
- **Not Applicable:** `Not Applicable` / timestamp / `Reason: …`. There is no reference example for this, so it is an assumption (§10).
- **Risk flags are not part of the rendered text,** which keeps the reference format exact. They are returned in the API response and shown as a review banner in the UI.

| Output decision | Evidence |
|---|---|
| JSON + renderer instead of free text | Typed slots turn every metric into a set comparison; vLLM enforces the JSON schema structurally ([vLLM structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs.html)) |
| Model writes the quote; code verifies it and replaces it with the exact transcript span | All 58 reference quotes match their transcript after light normalization, but only 50 match as exact substrings [VERIFIED: earlier analysis of the 5 examples], so verification must normalize |
| Code formats identity, dates, phones, timestamp, tall-man casing | Deterministic work; it should not cost model tokens or risk model errors |

### 3.3 Source-grounded value policy (drug names, identity, numbers)

**The summarizer is not a medical fact checker. It summarizes what the transcript supports**, and never uses outside medical knowledge to decide that one name "must" be another.

| Transcript evidence | Summary value | Certainty | Example |
|---|---|---|---|
| One form, stated confidently (even if it looks wrong) | That form, as stated | `stated` | "I take Ampatripoline." → Ampatripoline |
| Speaker hedges ("I think", "maybe", "I guess", "not sure") | The hedged form | `unclear` | "I think I'm taking amitriptyline." → amitriptyline (caller unsure) |
| Conflicting forms for the same item, no resolution | Most frequently supported form | `unclear`, with all heard forms listed | Ampatripoline ×2, Amitriptyline ×1 → Ampatripoline (unclear; name conflicts in transcript) |
| Conflict explicitly resolved inside the call | Resolved form | `stated` | "I called it Ampatripoline, but the nurse confirmed it's amitriptyline" → amitriptyline |

- **What counts as explicit resolution:** spelled letter by letter; the nurse reading or confirming the name from the chart or med list *in response to the mention*; an explicit correction ("no, it's …"); the other speaker agreeing after a confirmation. A nurse merely saying a different word, with no confirmation, is a conflict, not a resolution.
- **A tie in frequency:** use the first-mentioned form and mark `unclear`.
- **Same policy for identity and numbers:**
  - Name drift (Nadine / Noreen / Norine, then the caller self-states "Nora Quinn") is resolved by the self-statement.
  - A DOB the caller corrects ("fifty-three … nineteen thirty-three") is resolved by the correction.
  - Unresolved conflicts are `unclear` and list the heard forms.
- **Assignment rule 3 is satisfied this way:** "unclear" is assigned from evidence *in the transcript* (hedges, conflicts, incomplete statements such as "one hundred mg per…"), not from guessing the true drug.
- **Optional safety net, outside the summary:** the API may attach a review flag "medication name not recognized, verify" for names absent from the formulary. It never changes the summary text or certainty.
- **Consequence for the provided examples:** `carfentanil` (example 3) and `ibuprofen` (example 5) are each a single confident mention, so a summary keeps them as stated, matching the provided references.

## 4. Supervised fine-tuning

### 4.1 Data format: system prompt kept separate

```text
data/sft/train.jsonl     {"id", "transcript", "call_timestamp_utc", "target"}   ← no prompt inside
pipeline/prompts/system_v4.md   system prompt (frozen; v1-v3 kept for the baseline history)
finetune/textio.py              the user-message function (numbered transcript), a copy of pipeline/pl/transcript.py used at train time and by the pipeline
```

**Decision (baseline runs on the validation set):** the baseline and the fine-tuned model both use `pipeline/prompts/system_v4.md`, frozen after three prompt revisions (v2 added the exact output format, v3 and v4 fixed name and relationship wording). Training therefore sees the same ≈ 2.2K-token prompt on every example (estimate; measure with `pipeline/dev/token_lengths.py`). Training cost goes up, but the comparison changes only the weights.

At training time the script assembles `[system: pipeline/prompts/system_v4.md] + [user: preprocess(transcript)] → [assistant: target]`. You can edit the prompt or the preprocessing before training without touching the data. Rule: the prompt version used in training is recorded with the adapter. Changing the prompt after training means re-validating on dev, and retraining if dev drops.

### 4.2 LoRA, not full fine-tuning

| Decision | Choice | Evidence |
|---|---|---|
| Method | LoRA | LoRA equals full fine-tuning for small and medium SFT sets when capacity is not exceeded (Thinking Machines). On clinical scribing, rank ≥ 8 equals full FT at 1K–30K examples (Baseten). LoRA forgets less of the base model's abilities ([Biderman et al. 2024](https://arxiv.org/abs/2405.09673)). Full FT of 12B in BF16 with AdamW does not fit on one 46 GB GPU |
| Training base | `google/gemma-4-12B-it-qat-w4a16-ct` loaded with `CompressedTensorsConfig(dequantize=True)` in BF16 | Transformers docs: dequantize is "what you want to fine-tune the model" ([docs](https://huggingface.co/docs/transformers/en/quantization/compressed_tensors)). The frozen base then equals the weights vLLM serves, so the only difference between baseline and fine-tuned is the adapter. **Correction:** an earlier message said the model card recommends the unquantized QAT checkpoint for fine-tuning; it does not, it only lists it as a variant |
| Fallback base | `google/gemma-4-12B-it-qat-q4_0-unquantized` | The parent of the ct checkpoint; use only if the dequantized load fails |
| Serving | ct checkpoint + adapter on vLLM, no merge or re-quantization | Re-quantizing a merged model is lossy even from QAT weights ([Unsloth QAT analysis](https://unsloth.ai/docs/models/gemma-4/qat)) |
| Rank / alpha | **r = 16, α = 32** (fallback r = 8) | Baseten: "use rank 8-16 as default, scale up to rank 32 if you have evidence of saturation". Thinking Machines and Baseten both used α = 32. Unsloth recommends r = 8–32 with α ≥ r for Gemma 4 ([guide](https://unsloth.ai/docs/models/gemma-4/train)) |
| Target modules | q, k, v, o, gate, up, down in every text layer; not embeddings, lm_head, or vision/audio parts | "Attention-only LoRA significantly underperforms MLP-only LoRA" (Thinking Machines); Unsloth uses all linear layers |
| Learning rate | 2e-4 (sweep 1e-4), cosine schedule, 3% warmup | Unsloth default 2e-4. LoRA's best LR is about 10× full FT's, rising to ~15× for runs of ~100 steps (Thinking Machines); ours are ~60–190 steps |
| Batch | 1 × 8 gradient accumulation, stratified by length and category (§4.3) | LoRA is less tolerant of large batches than full FT (Thinking Machines); 500 examples ÷ 8 ≈ 63 steps per epoch |
| Epochs | Up to 3; checkpoint each epoch; **select by validation critical-fact accuracy, not loss** | LIMA found perplexity did not track output quality |
| Monitoring | Training loss every step; validation loss on a fixed 25-call subset every 20 steps and on all 100 validation calls at each epoch end, plus the loss of the untouched model at step 0 | A diagnostic only (a rising validation loss while the training loss falls means memorising 500 calls; validation holds out two agencies). It never chooses the checkpoint. The validation set is therefore used for monitoring, for choosing among 3 checkpoints and for the final numbers; with no test split the reported scores are slightly optimistic, and the report says so |
| Input at train time | Exactly the baseline's input: `system_v4.md` + `CALL TRANSCRIPT` with numbered turns, chat template with thinking off (the §5.2 candidates table is not used, so that only the weights differ) | Strict comparison; code in `finetune/` |
| Dropout | 0.05 | Unsloth uses 0; a small value is cheap insurance at n = 500 [judgement] |
| Loss | Completion-only (assistant tokens) | System prompt and transcript are inputs, not targets (TRL default for prompt-completion data) |
| Length | `max_length` 8192, packing off, **assert zero truncation** | TRL's default `max_length` is 1024, which would silently cut targets ([TRL SFT docs](https://huggingface.co/docs/trl/sft_trainer)) |
| Thinking | Off in training and serving; the target starts with whatever empty thought block the chat template produces | The card says that with thinking off the 12B still emits an empty thought block [VERIFIED: model card]; verify by rendering `apply_chat_template(enable_thinking=False)` on Day 1 |

**Adapter-in-vLLM check.** vLLM issue [#50059](https://github.com/vllm-project/vllm/issues/50059) reports unstable LoRA outputs on a compressed-tensors W4A16 base. It is a different model (OLMo-3.1-32B), and its working rank-8 adapter covered only the last 8 layers, so it is weak evidence about rank. It still justifies one cheap check: run HF+PEFT and vLLM+adapter greedy on 20 validation transcripts, plus 3 server restarts. Pass if validator-scored metrics agree within 1 point and repeat runs give identical outputs on ≥ 95% of transcripts. Fallback: r = 8.

**Memory on the L40S (46,068 MiB)** [estimate, measured in the smoke test]: BF16 base ≈ 23.9 GB; LoRA parameters plus AdamW state ≈ 1 GB; activations with gradient checkpointing at 6–8K tokens ≈ 5–8 GB. Peak ≈ 31–35 GB, so it fits.

**Outcome (training).** Run as specified: r = 16, alpha = 32, 328 LoRA modules (65.6 M trainable parameters), learning rate 2e-4, 63 steps per epoch for 3 epochs = 189 steps, 10,281 s (2.9 h), **measured peak 36.2 GB**. The dequantised load worked (0 quantised modules left). Validation loss: 0.635 before training (25-call subset) → 0.189 / 0.167 / 0.171 after epochs 1 / 2 / 3. One out-of-memory warning at step 9 recovered. **Epoch 3 was chosen** on the pipeline metrics, not on loss (REPORT §7.7), using the validation set we also report on, so the numbers are slightly optimistic. Gradient norms spiked up to 417 and were clipped to 1.0 without effect on the loss.
**Not done from this section:** the learning-rate sweep, the rank fallback, the HF-versus-vLLM agreement check (vLLM did serve and run the adapter), evaluating epoch 1, and DPO. **A bug found on the way:** the constrained-decoding schema must list keys in the same order as the training targets, because vLLM's grammar forces schema order; ours did not and the first fine-tuned evaluation was invalid (REPORT §7.4). Training targets and schema should share one canonical key order (REPORT §10).

**DPO: not planned.** It needs preference pairs and a second training stage. If time remains: pairs of (validator-failed output, corrected output) from validation runs.


### 4.3 Batching: stratified, reshuffled every epoch

**Decision.** Micro-batch = 1 call, gradient accumulation = 8, so an optimizer step uses **8 calls** (500 calls → 62 steps of 8 + 1 step of 4 = 63 steps per epoch; 3 epochs ≈ 189 steps). The 8 calls of a step are chosen by rule, not by plain shuffling. `code/train/batching.py` builds the schedule (`data/sft/batch_schedule.json`, seed 42; epoch e uses seed 42-e, so the batches differ each epoch):

| Rule | Value | Reason |
|---|---|---|
| Length mix per step | Follows the split mix by cumulative rounding: mostly **6 short + 1 medium + 1 long** (also 5+1+2, 6+0+2, 5+2+1) | No step is all-long (memory and gradient-noise spikes) or all-short; every step sees the long-call behaviour that drives p95 latency |
| Category cap | No primary category more than 3 times per step | Avoids a step made of one scenario type, e.g. 8 billing calls |
| Not-Applicable cap | At most 2 per step | NA targets are tiny; they should not dominate a step |
| Order within a step | Random; gradients are summed, so order is irrelevant | |
| Order of steps / epoch reshuffle | Random, new each epoch | Standard SGD behaviour; no curriculum |
| Short step | The one step of 4 calls sits at a random position | 500 is not divisible by 8 |
| Validation | Not batched by rule (evaluation order does not change metrics); latency runs use concurrency 1 | |

**Why not simply random, and why not length-sorted.**
- **Padding is not a problem here.** With micro-batch 1 there is no padding, so length grouping (`group_by_length`, which sorts shuffled mega-batches longest-first, [HF discussion](https://discuss.huggingface.co/t/how-to-implement-trainers-group-by-length-in-pytorch/9232)) buys nothing. It would also put all 8 calls of a step in the same length class, and recent work reports that batch composition changes gradient noise ([SDO 2026](https://arxiv.org/pdf/2607.27273) argues for structure-aware batches; the evidence is mixed by data type).
- **No curriculum (short → long).** Ordering gains are reported mainly at small model scale and are inconsistent across datasets; on Alpaca with Mistral-7B a random order for one epoch was best ([Strategic Data Ordering 2024](https://arxiv.org/pdf/2405.07490)). We have a 12B model, 3 epochs and a single task format, so the expected gain is small and a short-to-long curriculum risks a model tuned to whatever it saw last.
- **Stratification is cheap insurance, not a proven gain** [judgement]: it lowers step-to-step variance in length and category, which matters most with only ~189 updates. If the sweep shows no difference we keep it anyway because it costs nothing.

**Loss normalization (a real bug source).** With accumulation, averaging each micro-batch's mean loss over-weights short sequences; the correct loss is the summed token loss over the whole step divided by the step's total target tokens ([Hugging Face, Oct 2024](https://www.huggingface.co/blog/gradient_accumulation)). Our steps mix 4–5K-token long calls with short ones, so this matters. Requirements: pin a Transformers/TRL version that passes `num_items_in_batch`; smoke test E6 must show that accumulation 8 × batch 1 gives the same loss and gradient norm as a batch of 8 on the same calls (within 1%). Long calls then weigh more tokens in a step, which is intended.

**Batch size.** 8 is kept: LoRA tolerates large batches less well than full fine-tuning (Thinking Machines), and 63 updates per epoch is enough to move a rank-16 adapter. The sweep varies LR, not batch size. If memory allows, micro-batch 2 is not used because it would reintroduce padding.
## 5. Production inference pipeline

### 5.1 Serving

| Item | Decision | Evidence |
|---|---|---|
| Engine | vLLM, latest stable ≥ 0.28 pinned at setup; exact version recorded | The ct format is for native vLLM inference [VERIFIED: model card]. vLLM ≥ 0.28 handles Gemma 4's per-layer head_dim with newer Transformers ([Friendli notes](https://friendli.ai/models/GotoAI-Inc/gemma-4-12B-it-W4A16)); no `--quantization` flag, because compressed-tensors is auto-detected |
| Decoding | Greedy (temperature 0) | The card's T = 1.0 / top_p 0.95 is a general chat default. Verbatim quotes and doses reward the most likely token. Tested on validation: greedy vs card sampling |
| Thinking | Off | Each thought token is one decode step against a 15 s p95 budget. Tested on 50 validation calls; enabled only if it gains ≥ 2 points with p95 still < 15 s |
| Structured output | JSON-schema constrained decoding | Guarantees parseable output; semantic rules stay in the system prompt |
| Context | `max_model_len` 16384 | Measured with the model tokenizer (`pipeline/dev/token_lengths.py`): system prompt v4 = 2,010 tokens; prompt + transcript max 5,379 (train) / 4,938 (validation); gold output max 2,098 (median 937). Every training example fits in 8,192. Training `max_length` stays 8,192. Serving uses 16,384, as in the baseline runs, so that a long call plus a long output cannot overflow |
| Prefix caching | On | The fixed system prompt is reused on every call |

### 5.2 Steps

1. **Pre-process (code).**
   - Split turns on `Nurse ->` / `Caller ->` and number them `[T1]…[Tn]`.
   - Extract spoken-number candidates (DOB, phone, doses, times), name candidates (self-introductions, spelled letters) and drug candidates (formulary fuzzy match) into a short candidates table appended to the user message. The transcript text is never rewritten, so quotes stay verbatim.
2. **Not-Applicable gate (code first).** A clinical-content score counts symptom, medication, supply and action lexicon hits.
   - Score 0 and < 15 turns: return Not Applicable without calling the LLM.
   - High score: never Not Applicable.
   - Middle band: the model decides.
   - Any high-risk rule hit vetoes Not Applicable.
3. **LLM call:** one schema-constrained generation.
4. **Validators** (deterministic; implemented and measured in `pipeline/`, which extends this list to V1-V16 and records which defects the rules can and cannot see):

| ID | Check | On failure |
|---|---|---|
| V1 | JSON parses, matches schema | Retry |
| V2 | All four sections present | Render "None documented during call." |
| V3 | Quote ⊂ cited same-speaker turns after normalization; fuzzy repair if similarity ≥ 0.90, then replaced by the exact span | Retry if < 0.90 |
| V4 | Quote speaker = turn speaker; verbs match ("Caller reported" / "Nurse advised") | Retry |
| V5 | Every number in text/facts is in the cited turns (±2 neighbours) with a compatible unit | Retry → remove item + flag |
| V6 | Every drug name appears in the transcript; if the transcript holds conflicting forms of it (fuzzy match among mentions) with no resolution cue, `certainty` must be `unclear` (policy §3.3). Formulary misses only add an optional review flag | Force unclear; optional "verify name" flag |
| V7 | Identity values equal a pre-processing candidate; conflicting candidates require `unclear` unless resolved by self-statement, spelling or correction | Flag identity conflict |
| V8 | `completed` needs completion cues ("I sent", "I've put in"), with no future cues ("I will", "I'll", "let me", "going to") | Set to planned + flag |
| V9 | Hedges near a cited value ("I think", "maybe", "about", "not sure") require `unclear` or hedged wording | Force unclear |
| V10 | Every number or drug in bullet text also appears in `facts[]` | Retry |
| V11 | NA consistency with the rule gate | Override |
| V12 | Model risk flags need a verified quote; rule flags are unioned in | Union |

5. **Risk flags = rule hits ∪ verified model flags,** favouring recall.
   - Categories: `uncontrolled_symptom`, `medication_concern`, `suicidal_statement`, `breathing_concern`, `escalation_request`, `other_urgent` (falls with injury, bleeding, seizure, death at home).
   - A negation window suppresses rule hits such as "no trouble breathing", except for suicidal phrases, which are never suppressed.
   - Rules scan merged same-speaker blocks, so a phrase split across two turns is still caught.
   - Nurse screening questions ("Any trouble breathing?") do not fire flags.
6. **Retry:** at most 1, only if remaining budget > measured p95 generation time. The retry prompt lists the failed checks.
7. **Render** in reference format. The response also carries flags, validation results, `needs_nurse_review`, and timings (preprocess, TTFT, LLM total, validate, end-to-end).

### 5.3 Interface

FastAPI: `POST /v1/summarize`, `POST /v1/summarize/stream` (SSE), `GET /v1/meta` (model, revision SHA, adapter hash, prompt version), `GET /healthz`. A small Gradio page shows transcript in, rendered summary out, red review banner with flag quotes, amber "unclear" chips, and a validator log. Demo and evaluation use the same code path.

## 6. Evaluation

### 6.1 Deterministic headline metric

**Critical-Fact Accuracy (CFA)** on the 100-call validation set:

```text
CFA = gold critical slots matched / (gold critical slots + unsupported critical values in output)
```

- **Critical slots:** patient name, DOB, caller name, relationship, callback phone; each medication tuple (name, dose, unit, route, frequency); each symptom (name, presence, severity); each action (type, status); each required risk flag; the NA label.
- **Matched** = normalized value equal, correct speaker, correct certainty, correct status, and the cited quote passes V3.
- **Unsupported** values (hallucinations) enter the denominator, so the metric can't be gamed by leaving things out or by adding extras.
- **Target:** CFA ≥ 95% (point estimate with a transcript-level cluster-bootstrap 95% CI).
- **Outcome:** implemented as H19 (critical-fact accuracy against the gold) in `pipeline/pl/reference_metrics.py`, with simplifications: slots are matched by normalised value and cited-turn proximity, without the speaker and quote-validity conditions, and the intervals are Wilson bounds (not a cluster bootstrap). Result: 81.6% (lower bound 79.3%). A companion H19r (gold slots found, no penalty for extra facts) is 90.3%, because many of the "unsupported" facts are true details the gold does not record.
- **Release gates:** fabricated medication or dose = 0; high-risk recall ≥ 98%; NA accuracy ≥ 95%; four sections present in 100% of non-NA outputs.
- **Transcript-level safe-pass** (no unsupported critical value, no identity error, all flags found, NA correct) is reported with a Wilson CI.

| Required metric (assignment task 4) | Definition |
|---|---|
| Completeness | Recall over all gold facts, including education and pertinent negatives |
| Factual accuracy | Precision of output facts against gold; quote-validity rate |
| Identity accuracy | Exact match per field; `unclear` counts as correct only when gold is unclear |
| Medication name + dose | Strict P/R/F1 on (name, dose, unit); relaxed name-only; route/frequency accuracy |
| Plus | Attribution, uncertainty preservation, planned vs completed, NA P/R, flag recall/precision per category |

Every metric is also reported per category, per length bucket, and on a hard subset (ASR-heavy + ambiguous). Baseline vs fine-tuned on the same calls: McNemar test on safe-pass, paired bootstrap on CFA. **Outcome:** a paired sign test on safe-pass was used (equivalent to McNemar's exact test): 36 calls pass only with the fine-tuned model, 4 only with the base, p < 0.001; no bootstrap was run. Every failure is tagged with the validator ID that caught it.

### 6.2 Latency (L40S, concurrency 1, 10 warm-up requests discarded)

| Reported for baseline and fine-tuned (and each optimization step used) |
|---|
| **Overall p50** end-to-end |
| **Overall p95** end-to-end (target < 15 s) |
| **Long-call p95** end-to-end (16 long validation calls; with this few samples p95 is roughly the worst call, so a bootstrap CI is reported) |
| TTFT p50 / p95; output tokens p50 / p95; decode tokens/s |

End-to-end = request received → validated and rendered response, including any retry.

**Outcome: time to first token was measured at the end** with a streamed request (the `latency` stage): p50 0.17 s, p95 0.64 s for the fine-tuned model, the same as the base model's (0.16 s, 0.62 s). The matrix has a Latency table. The totals below were measured.

**Outcome (measured, 20 evenly spaced calls, one at a time).** Base model p50 28.0 s, p95 69.9 s (slowest 70.4 s). Fine-tuned (epoch 3): **p50 14.0 s, p95 19.1 s** (slowest 20.8 s), 13 of 20 calls under 15 s; decode speed about 62 tokens/s (73 for the base model, so the adapter costs about 14%); median output 894 tokens. **The 15 s p95 target is not met.** The estimate that follows was right about the range and wrong about the verdict.

Estimate for the L40S, written before measuring: 864 GB/s bandwidth and ~8.3 GB of weights read per token give ≈ 60–85 tok/s, so 1,000 output tokens ≈ 12–17 s. **p95 < 15 s is borderline.** Optimizations, applied in order and stopped once the target is met. Steps 1–5 keep the rendered format identical:

1. Thinking off, compact JSON whitespace, a `max_tokens` cap.
2. Prefix caching (TTFT only).
3. N-gram (prompt-lookup) speculative decoding. Quotes are copied from the input, so draft tokens should often be accepted. **Outcome: tried, made it slower** (34–43 tokens/s instead of 62; median 23 s instead of 14 s). Draft tokens were accepted (about 2.4–3.4 per step) but vLLM 0.30 falls back to its older model runner and disables asynchronous scheduling with n-gram speculation, and here it runs together with LoRA and constrained JSON decoding. Dropped.
4. MTP speculative decoding with the Gemma 4 QAT assistant drafter, if vLLM accepts the pairing [untested; not tried].
5. Quote pointers: the model emits turns plus first/last words and code fills in the verbatim quote. The targets convert mechanically from gold, so no data is rewritten.
6. Templated explanations by fact type (wording changes, structure stays). **Steps 5 and 6 were not tried.** `explanation` is 11% and `quote` 15% of the output characters, so even both together would leave the longest calls near 16 s; a faster GPU is the more reliable lever (estimate, not measured).

### 6.3 Gemma 12B as offline judge

| Decision | Evidence / reason |
|---|---|
| Judge = **base** Gemma 12B (no adapter), offline only | Your mentor asked for it; it is not in the request path |
| Given transcript + summary + **fact record as reference** | Reference-guided judging reduced judge errors on math and reasoning questions in MT-Bench ([Zheng et al. 2023](https://arxiv.org/abs/2306.05685)) |
| Pointwise labels, not pairwise preference | Avoids position bias. Self-preference grows with self-recognition ([Panickssery et al., NeurIPS 2024](https://arxiv.org/abs/2404.13076)), and both summaries come from Gemma |
| Three rubrics, each PASS/FAIL with a reason: **faithfulness** (anything wrong or invented), **completeness** (every fact-record item covered), **calibration** (hedging, planned vs completed, speaker) | Gives semantic faithfulness, completeness and distortion rate; the judge never sees labels. Exact prompts and settings: `llm_judge/v5_final/` |
| Validated by mutation tests on hand-edited summaries, not by hand labels: 50 validation calls (25 edited with a known defect) for tuning, then **40 fresh calls with the prompts frozen** | Edits are known exactly, so agreement and kappa are exact. Method, version history and results: `llm_judge/README.md` |
| Never decides the 95% headline | Judges are less reproducible than code |

**Validation result (confirmation set, 40 fresh items, frozen prompts).** Faithfulness: 100% agreement, kappa 1.00, 10/10 edits caught, 0/30 false alarms (22/22 caught over both sets). Completeness (against the fact record): 90%, kappa 0.61; every removed nurse action or instruction was found (9/9 over both sets), but removed findings were missed 3 times in 6 when the topic still appeared elsewhere. Calibration: 90%, kappa 0.55; planned-vs-completed 6/6, swapped speaker labels 3/6, removed hedges 0/2. Consequences for the pipeline: faithfulness and completeness (actions and instructions) are used as judge metrics; calibration is reported as an indicator; speaker attribution and quote checks stay with the deterministic validators. A first design that judged completeness against the whole transcript was rejected: most of its "false alarms" were real omissions, because the gold summaries are complete against the fact record, not against every sentence in the call. Limits: 90 items in total, synthetic edits, one author. Details: `llm_judge/README.md`.

### 6.4 Evaluation pipeline and the common matrix

`pipeline/` runs one system (base or fine-tuned) through four stages and reports one table: **generate** (the model's JSON), **validate** (deterministic rules V1-V16 on transcript + output only), **judge** (the frozen v5 judge from 6.3), **matrix** (every metric normalized to a 0-100% rate with its source, counts, a 95% lower confidence bound and an evidence level). Reference-based rows (identity, medications, actions, flags, Critical-Fact Accuracy against the gold summary) are added when a case has gold, i.e. for our validation set; unseen calls get the reference-free rows and the combined **safe-pass** (no rule ERROR and judged faithful). The headline rows are fixed in advance: G1 safe-pass for unseen data, H19 Critical-Fact Accuracy and G1 on our validation set. **Outcome:** G1 60% → 92%, H19 56.8% → 81.6% (base → fine-tuned, epoch 3); 24 of 50 rows reach 95%, but neither headline does. Two additions made along the way, both reported next to the raw rows and never instead of them: automatic quote repair (`pipeline/pl/repair.py`, rows E1r and G1r) and the companion H19r. The rules were measured by damaging 100 validated gold summaries in 33 specific ways: 0 errors on undamaged gold (600 calls); structural damage, quotes, drug swaps, identity and status flips are caught at 80-100%; invented findings outside the term list, swapped patient/caller names, removed bullets and doses swapped with another spoken number are invisible to rules and are left to the judge. Details and commands: `pipeline/README.md`.

## 7. Hardware

RunPod pod, 1× **NVIDIA L40S, 46,068 MiB**, driver 595.91.07, CUDA 13.2 [VERIFIED: your `nvidia-smi`]. The same GPU is used for serving (~8.3 GB weights + KV cache), LoRA training (~31–35 GB estimated) and the judge. Recorded in the report: `nvidia-smi -q`, `vllm collect-env`, model revision SHA, adapter SHA256, prompt version.

## 8. What deterministic validation cannot do

> Deterministic validation verifies explicit, checkable claims: quotes exist and belong to the stated speaker; numbers, doses, drugs and identity values are supported by the transcript; planned actions are not shown as completed. It cannot guarantee semantic equivalence. "I think the pain is probably because she hasn't been sleeping" rendered as "pain caused by sleep deprivation" passes every lexical check; so does "unsure whether she took it" rendered as "did not take it." V9 (hedge words) catches some of these, not all. That gap is measured offline by the judge (§6.3) and stated as a limitation, not claimed solved.

## 9. Changes from the draft architecture, and why

| Draft | Final | Why |
|---|---|---|
| Teacher LLM writes gold from the transcript, then validated | Gold written from the fact record + noise log; validated both directions (G7/G8) | Transcript-only checks pass mishearings reproduced as fact, as in the reference examples (§2.6) |
| Teacher LLM via API | Claude-authored in-repo | No API budget; deliberate diversity via a blueprint |
| Deterministic, seeded noise injection | Noise written in context and logged per event | Real ASR errors depend on context (sound-alikes, diarization); you asked for no seeding. The log keeps gold certainty exact |
| Summary item {text, speaker, certainty, status, turn_ids} | Adds `quote`, `explanation`, typed `facts[]`, `identity`, `risk_flags`, `not_applicable` | Exact reference format needs quote + explanation; doses can only be code-checked as typed fields |
| No NA or risk-flag stage | NA rule gate + hybrid risk flags | Assignment safety rules 5 and 6 |
| Judge needs no fact table | Judge gets the fact record as reference | Reference-guided judging is more accurate |
| — | System prompt stored separately from SFT data | Your requirement; prompt editable before training |
| Out-of-formulary drug → `unclear` | Source-grounded value policy (§3.3) | Your decision: summarize what the transcript supports; uncertainty only from transcript evidence |
| Training input includes a candidates table (§5.2) | Not used: the input is the system prompt plus the numbered transcript, identical for base and fine-tuned | Strictest comparison: only the weights differ |
| Constrained schema in any key order | Schema key order must equal the training-target order | vLLM forces schema order; the first fine-tuned evaluation was invalid because of it (REPORT §7.4) |
| Raw model output scored only | Quote repair reported separately (calls with no rule error after repair, E1r; safe-pass rate after repair, G1r) | Many failures were a stitched quote that has an exact counterpart in the call |
| Validation set for final numbers only | Validation also used for monitoring and epoch choice | No test split exists; stated as a limitation |
| Prompt written once | Prompt iterated v1 → v4 on the baseline, then frozen | v1 never defined formats (safe-pass rate G1 7%); only formats and naming conventions changed |

## 10. Documented assumptions (confirmed)

1. **NA rendering** is `Not Applicable` / timestamp / `Reason: …`. There is no reference example, so it is documented as an assumption in the report.
2. **Risk flags are shown outside the summary text** (API + UI banner) to keep the format exact.
3. **Source-grounded gold** (§3.3): a drug name stays as spoken, including garbles, so `carfentanil` and `ibuprofen` stay as stated, matching the references.
4. **Timestamp** comes from request metadata.

## References

1. Google. [gemma-4-12B-it-qat-w4a16-ct model card](https://huggingface.co/google/gemma-4-12B-it-qat-w4a16-ct).
2. Thinking Machines Lab (Schulman et al.). [LoRA Without Regret](https://thinkingmachines.ai/blog/lora/), 2025.
3. Baseten. [Practical LoRA research](https://labs.baseten.co/articles/practical-lora-research), 2025.
4. Biderman et al. [LoRA Learns Less and Forgets Less](https://arxiv.org/abs/2405.09673), TMLR 2024.
5. Unsloth. [Gemma 4 fine-tuning guide](https://unsloth.ai/docs/models/gemma-4/train); [Gemma 4 QAT](https://unsloth.ai/docs/models/gemma-4/qat).
6. Hugging Face. [Transformers compressed-tensors](https://huggingface.co/docs/transformers/en/quantization/compressed_tensors); [TRL SFT Trainer](https://huggingface.co/docs/trl/sft_trainer).
7. vLLM. [Issue #50059](https://github.com/vllm-project/vllm/issues/50059); [structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs.html).
8. Zhou et al. [LIMA](https://arxiv.org/abs/2305.11206), 2023.
9. Zheng et al. [Judging LLM-as-a-Judge (MT-Bench)](https://arxiv.org/abs/2306.05685), 2023.
10. Panickssery, Bowman, Feng. [LLM Evaluators Recognize and Favor Their Own Generations](https://arxiv.org/abs/2404.13076), NeurIPS 2024.
11. Mani et al. [Towards Understanding ASR Error Correction for Medical Conversations](https://aclanthology.org/2020.nlpmc-1.2), 2020; AssemblyAI, [drug-name transcription accuracy](https://assemblyai.com/blog/ai-transcription-accuracy-pharmaceutical-drug-names).
12. Van Veen et al. [Adapted LLMs can outperform medical experts in clinical text summarization](https://arxiv.org/abs/2309.07430), Nature Medicine 2024.
