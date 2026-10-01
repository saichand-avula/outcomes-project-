# Clinical Summary LLM — 5-Day Evidence-Based Execution Plan (Gemma 4 12B QAT w4a16)

Oct 1, 2026 · @kishan

## Open questions and assumed defaults

The plan proceeds on the defaults below; each one changes a specific decision if the answer differs.

| # | Question for mentor | Default assumed | Decision it changes |
| --- | --- | --- | --- |
| Q1 | Which AWS GPU instance, and can I choose it? | One 48 GB GPU (g6e.xlarge, L40S); plan also works on 24 GB for serving only | Training feasibility, batch size, whether speculative decoding fits |
| Q2 | Is "p95 < 15 s" measured at concurrency 1 (one nurse, one call) or under load? | Concurrency 1 is the headline; concurrency 4 reported as secondary | Batching and scheduler settings |
| Q3 | May I define the ≥95% metric myself (the brief says "the defined automatic evaluation metric")? | Yes: a deterministic, fact-level composite defined below | Whole evaluation section |
| Q4 | Are external LLM APIs (OpenAI/Anthropic/Google) allowed for data generation or judging? | yes&#32; | can use it for llm as a judge for completeness or any evalution matrix&#32; |
| Q5 | Must output match the reference style exactly (quote line + Explanation line per bullet, tall-man drug names such as LORazepam)? | Yes | Output schema and renderer |
| Q6 | Where does the Chief Complaint timestamp `[2000-01-01 14:41 UTC]` come from? It is identical in all 5 references and never appears in the transcripts | Passed in as call metadata; rendered as "timestamp not provided" if absent | API schema |
| Q7 | Is the reference `carfentanil` in example 3 intended? The transcript line is almost certainly an ASR error, and the reference repeats it without marking it unclear | Treat as an ASR error; our validator should flag it | Gold-label policy for ASR-garbled drug names |
| Q8 | Is a Hugging Face token available on the GPU box, and is outbound internet allowed? | Yes | Model download, pip installs |
| Q9 | Demo video length and format? | ≤ 3 minutes, screen recording | Demo script |

Two facts from your 5 examples shape the design. All 58 reference quote lines match the transcript after lowercasing, stripping punctuation and collapsing immediate word repeats, and all 58 fall inside a same-speaker run of turns \[VERIFIED: my script on your YAML\]. Only 50/58 match as exact substrings, so the verifier must normalize before matching.

## Executive summary

Serve the mandated checkpoint unchanged on vLLM, make one schema-constrained call per transcript, and let deterministic code verify every quote, number, drug, identity field and action status before anything is shown. Fine-tune a rank-16 LoRA against the checkpoint's own dequantized weights and serve it on the same process, so baseline and fine-tuned differ only by the adapter. The main open risk is latency on a 48 GB L40S, not quality.

| Area | Plan | Confidence |
| --- | --- | --- |
| Architecture | Pre-process (turn IDs, spoken-number candidates) → one vLLM call returning typed JSON → 12 validators → ≤1 retry → render the reference format. Risk flags = rules ∪ model; Not Applicable = rules first, model in the middle band, high-risk veto | High |
| Model and serving | `google/gemma-4-12B-it-qat-w4a16-ct` on vLLM 0.30.0 (≥0.23.0 required), greedy, thinking off, max\_model\_len 8192, LoRA via `--enable-lora` | High that it serves; medium that runtime LoRA over int4 is correct (known vLLM issue) → parity gate on Day 3 |
| Fine-tuning path | BF16 LoRA (r16, all attention + MLP projections) on the ct checkpoint loaded with `dequantize=True`; no merge, no re-quantization. Baseline = same checkpoint without adapter | Medium–high |
| Data | Fact records → transcripts with per-turn fact tags (train/dev voiced by local Gemma 4 31B QAT, eval by two frontier API models) → seeded ASR noise → gold JSON by construction. 800 train / 100 dev / 400 eval; your 5 examples as a never-trained sanity set | Medium (realism is the weak point) |
| Headline metric | Critical-Fact Accuracy ≥ 95% (hallucinations count in the denominator), plus gates: zero fabricated meds/doses, high-risk recall ≥ 98%, NA accuracy ≥ 95%. n = 400 lets an observed 98% clear 95% on the Wilson lower bound (96.1%) | Medium on reaching 95% |
| Latency | Decode-bound: \~8 GB read per output token. Estimated 14–19 s for 1,200 tokens on L40S vs 4–5 s on H100. Ladder: thinking off → compact JSON → quote pointers → templated explanations → speculative decoding → faster GPU | Low–medium on L40S; high on H100 |
| Hardware | g6e.2xlarge (1× L40S 48 GB) for all work; one p5.4xlarge (1× H100) day in reserve for final latency | Medium |
| External APIs | Frontier models for evaluation only: 3-vote judge panel and eval-set voicing; never in training data or the request path | High |

Three facts from your 5 examples shaped the design: all 58 reference quotes are recoverable from the transcript after light normalization (so quotes can be verified by code), the reference for example 3 repeats a likely ASR mishearing (`carfentanil`) without marking it unclear (so gold must come from fact records, not from model-written summaries), and the Chief Complaint timestamp never appears in any transcript (so it must come from metadata).

## 1. Model and inference setup

Serve the exact checkpoint with vLLM v0.30.0 (minimum v0.23.0), train a BF16 LoRA against the checkpoint's own dequantized weights, and serve base + adapter on the same vLLM process. Greedy decoding, thinking off, speculative decoding only if the latency ladder needs it.

### Verified facts about the checkpoint

| Fact | Status |
| --- | --- |
| Lineage gemma-4-12B → -it → -it-qat-q4\_0-unquantized → this checkpoint; compressed-tensors for vLLM | \[VERIFIED: [model card](https://huggingface.co/google/gemma-4-12B-it-qat-w4a16-ct)\] |
| 11.95B params, 48 layers, sliding window 1024, 256K context, 262K vocab, encoder-free ("Unified") | \[VERIFIED: model card\] |
| Weights are 4-bit int, 16-bit activations, group\_size=32; memory 22.8 GB (BF16) → 8.3 GB | \[VERIFIED: [vLLM Gemma 4 recipe](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md)\] |
| Sampling temp 1.0 / top\_p 0.95 / top\_k 64 "across all use cases" | \[VERIFIED: model card\] |
| `<\|think\|>` in system prompt enables thinking; with it off, 12B still emits an empty `<\|channel>thought\n<channel\|>` block | \[VERIFIED: model card\] |
| Assistant (drafter) must be a QAT checkpoint of the same precision | \[VERIFIED: model card\] |
| License Apache 2.0 | \[VERIFIED: [Gemma 4 license page](https://ai.google.dev/gemma/apache_2)\] |
| Hub page shows `num_experts must be a number` config-parsing warnings | \[VERIFIED: model card\]. Impact on loading is \[ASSUMPTION: harmless Hub-metadata lint, since vLLM ships a recipe for this repo; tested in Experiment 1\] |
| The technical report (arXiv 2607.02770) | Not opened; nothing in this plan depends on it |

### A. Serving decision

| Item | Decision | Evidence / status |
| --- | --- | --- |
| Engine | vLLM (REQUIRED by the ct format). Alternatives: SGLang, Transformers `generate`, llama.cpp GGUF. Rejected: SGLang/llama.cpp would need a different checkpoint; Transformers has no fused int4 kernel for this path | ct checkpoints are "for native, optimized inference with vLLM" \[VERIFIED: model card\] |
| Minimum version | v0.23.0 (added Gemma 4 Unified #44429 and Gemma 4 MTP). Pin **v0.30.0** (22 Sep 2026). v0.29.0 fixed Gemma4 MTP under CUDA graphs | \[VERIFIED: [v0.23.0 notes](https://github.com/vllm-project/vllm/releases/tag/v0.23.0), [releases](https://github.com/vllm-project/vllm/releases)\] |
| Quantization flag | None; vLLM auto-detects compressed-tensors | \[VERIFIED: recipe\] |
| Launch | `vllm serve google/gemma-4-12B-it-qat-w4a16-ct --revision <sha> --max-model-len 8192 --limit-mm-per-prompt '{"image":0,"audio":0}' --gpu-memory-utilization 0.90 --reasoning-parser gemma4 --enable-lora --max-lora-rank 16 --max-loras 1 --lora-modules clin=./adapter` | Text-only MM limit and reasoning parser \[VERIFIED: recipe\]. LoRA flags \[ASSUMPTION: standard vLLM flags; Experiment 4\] |
| Memory at serve time | \~8.3 GB weights + KV + CUDA graphs; fits 24 GB | Weights \[VERIFIED\]. KV per 8K sequence <2 GB \[ASSUMPTION: hybrid attention caps sliding-layer KV at 1024 tokens; read "KV cache size" from the vLLM startup log\] |
| Throughput | Decode 55–85 tok/s at batch 1 on L40S; prefill of \~5K tokens <1 s | \[ASSUMPTION: weight-bandwidth bound, \~8 GB read per token at 864 GB/s × 60–80% efficiency. To be measured, Experiment 1\] |

### LoRA on a compressed-tensors W4A16 base in vLLM

The finding is "works mechanically, correctness not guaranteed." vLLM's Gemma 4 Unified class inherits LoRA support from Gemma4ForConditionalGeneration \[VERIFIED: [vLLM API docs](https://docs.vllm.ai/en/latest/api/vllm/model_executor/models/gemma4_unified/)\]. An open issue reports that LoRA × compressed-tensors is absent from vLLM's documented LoRA/quantization matrix, and that rank-32 all-layer adapters on a W4A16 g32 base gave weak, non-reproducible outputs while rank-8 adapters were fine (vLLM 0.17.1–0.24.0, RTX 5090) \[VERIFIED: [vLLM #50059](https://github.com/vllm-project/vllm/issues/50059)\]. Hence: rank ≤16, adapter on attention+MLP only, and a hard parity and determinism gate (Experiment 4).

### B. Fine-tuning path

Your suspicion is correct in substance: there is no documented way to LoRA-train while keeping the packed int4 weights. Transformers loads compressed-tensors either compressed (decompressed to BF16 on the first forward pass) or with `dequantize=True`, which the docs describe as "what you want to fine-tune the model" \[VERIFIED: [Transformers compressed-tensors docs](https://huggingface.co/docs/transformers/en/quantization/compressed_tensors)\]. So every viable path trains against BF16 weights.

| Path | Viable? | Train/serve match | Cost | Verdict |
| --- | --- | --- | --- | --- |
| **P1. LoRA on this ct checkpoint dequantized to BF16; serve ct + adapter in vLLM** | Yes \[VERIFIED: dequantize=True + vLLM Gemma4 LoRA\] | Exact: the frozen base equals the int4 lattice vLLM serves | \~24 GB base → needs a 48 GB GPU | **Chosen** |
| P2. LoRA on -it-qat-q4\_0-unquantized; serve ct + adapter | Yes | Near-exact \[ASSUMPTION: "half-precision weights extracted from the QAT pipeline" may sit slightly off the int4 grid; Experiment 4 diffs the tensors\] | Same as P1 | Equivalent backup |
| P3. LoRA on -it BF16, merge, re-quantize | Yes | None: the served model is no longer the mandated checkpoint | Plus a GPTQ run | Rejected. Naive Q4\_0 conversion of the 12B QAT weights kept only 74% top-1 agreement vs BF16 QAT \[VERIFIED: [Unsloth QAT analysis](https://unsloth.ai/docs/models/gemma-4/qat)\]; re-quantization is not lossless even from QAT weights |
| P4. Merge adapter into dequantized ct, re-quantize W4A16 | Yes | Partial; deltas below half a quantization step round away \[ASSUMPTION\] | GPTQ run | Fallback only if P1 parity fails |
| P5. Train on packed int4 directly | No documented path | — | — | Not viable |
| P6. QLoRA (bitsandbytes NF4) on the unquantized QAT | Yes | Mismatch: trained on NF4, served on int4 \[ASSUMPTION\] | Fits 24 GB | Only if the GPU is 24 GB. bitsandbytes is now an out-of-tree vLLM plugin \[VERIFIED: v0.28.0 notes\] |

**Fair comparison.** Baseline = this ct checkpoint on vLLM v0.30.0, no adapter. Fine-tuned = the same checkpoint and process plus the LoRA. Prompt, JSON schema, decoding, validators and hardware are identical.

### C. Decoding

Default is greedy (temperature 0). Google's sampling is a general chat default; verbatim quotes and doses reward the mode, not diversity. \[ASSUMPTION: greedy ≥ sampled on faithfulness; tested.\]

- Experiment (Experiment 6): 100 dev transcripts × {greedy, T=1.0/top\_p 0.95/top\_k 64} × 3 seeds. Measure critical-fact accuracy, hallucinated critical values, validator-failure rate and seed-to-seed agreement.
- Rule: keep greedy unless sampling gains ≥1 point accuracy with no more hallucinations.
- Determinism caveat: greedy is not guaranteed bit-identical across batch sizes, restarts or LoRA kernels \[ASSUMPTION: floating-point reduction order varies with batching\]. vLLM has a batch-invariant mode (VLLM\_BATCH\_INVARIANT=1), which LMCache used for exact-match Gemma 4 runs \[VERIFIED: LMCache Gemma 4 page\]; test its latency cost. Run the same request at concurrency 1 and 4 and report the diff rate.

### D. Thinking mode

Off. Thinking adds reasoning tokens before the answer, and each costs one decode step: 500 thought tokens at \~15 ms/token is \~7.5 s, half the latency budget \[ASSUMPTION: token rate from A; measured\].

- Experiment (Experiment 7): 50 dev transcripts, thinking on vs off. Report thought-token p50/p95 and the accuracy delta. Switch on only if accuracy rises ≥2 points and p95 stays <15 s.
- Stripping: `--reasoning-parser gemma4` moves any thought text to the `reasoning` field \[VERIFIED: recipe\]. The client also strips `<|channel>thought\n.*?<channel|>` (DOTALL) before parsing JSON.
- Training targets include the empty thought block the model emits with thinking off \[ASSUMPTION: confirm by rendering `apply_chat_template(enable_thinking=False)` and one raw generation\].

### E. Speculative decoding (OPTIONAL)

- Drafter: `google/gemma-4-12B-it-qat-q4_0-unquantized-assistant` (0.4B, BF16). The QAT collection has no ct-format assistant \[VERIFIED: [QAT collection](https://huggingface.co/collections/google/gemma-4-qat-q4-0), [assistant card](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-unquantized-assistant)\]. Whether vLLM accepts this pairing is \[ASSUMPTION; Experiment 9\].
- Enable: `--speculative-config '{"model":"google/gemma-4-12B-it-qat-q4_0-unquantized-assistant","num_speculative_tokens":4}'`; the recipe recommends 4–8 for 12B \[VERIFIED: recipe\]. Before v0.29 the 12B assistant needed `--enforce-eager` \[VERIFIED: [LMCache Gemma 4 page](https://docs.lmcache.ai/recipes/gemma4.html)\].
- LMCache's validated 12B MTP setup also adds "method":"mtp" to the config and requires --attention-backend TRITON\_ATTN, because FlashAttention does not support Gemma 4's 512-dim global heads; it measured 0.854 draft acceptance on GSM8K for 12B \[VERIFIED: LMCache Gemma 4 page\]. Expected speedup 1.3–2× on decode \[ASSUMPTION; measured as acceptance length\].
- Compatibility with LoRA and JSON-constrained decoding is unverified \[ASSUMPTION\]. A LoRA-shifted target may also lower acceptance.
- Alternative with no drafter: n-gram (prompt-lookup) speculation, which suits outputs that copy transcript quotes. vLLM documents it; untested here.

### F. Model documentation block (for the report)

| Field | Value |
| --- | --- |
| Model ID | `google/gemma-4-12B-it-qat-w4a16-ct` |
| Revision | Record `huggingface_hub.model_info(id).sha` at download; pass `--revision <sha>` everywhere |
| License | Apache 2.0 |
| Quantization | QAT (Q4\_0 recipe), serialized W4A16 compressed-tensors, group 32; vision embedder excluded from quantization in vLLM (#44571) |
| Inference config | vLLM 0.30.0, greedy, thinking off, max\_model\_len 8192, JSON-schema output, prefix caching on, optional LoRA rank 16 |
| Hardware | Record GPU, driver, CUDA, `nvidia-smi -q` and `vllm collect-env` output |
| Selection rationale | Mandated by the assignment; QAT keeps near-BF16 quality at \~8 GB, leaving room for KV cache and training on one GPU |

### Context length and constrained decoding

| Item | Decision | Status |
| --- | --- | --- |
| max\_model\_len | 8192 | Longest transcript is 13,219 characters. At 3.5–4.2 characters per token that is \~3.1–3.8K tokens \[ASSUMPTION: no Gemma tokenizer was reachable here; Experiment 1 counts with the real one\]. Plus \~1K system prompt and ≤2K output |
| Structured output | vLLM JSON-schema `response_format` (RECOMMENDED); semantic rules still go in the system prompt because the model does not see schema descriptions | \[VERIFIED: recipe\] |
| Constraint overhead | Expected small per token | \[ASSUMPTION: measure TPOT with vs without the schema, Experiment 5\] |

## 2. Output design

The model emits schema-constrained JSON with typed facts and turn-cited quotes; code verifies every quote and value, then renders the reference text format. The model selects evidence, code copies it.

| Decision | Alternatives | Evidence | Risk if wrong → detection |
| --- | --- | --- | --- |
| JSON-then-render (REQUIRED for deterministic validation) | Direct text + regex parsing | Typed fields make every metric a set comparison; vLLM enforces the schema structurally \[VERIFIED: recipe\] | Schema fights the model's prose style → compare dev accuracy JSON vs free text in Experiment 5 |
| Each bullet carries `speaker`, `turn_ids`, `quote`, `explanation`, and a `facts[]` list of typed slots | Free-text bullets only | Makes "no invented dose/med/action" checkable: every number or drug token in bullet text must also appear in `facts[]` and in the cited turns | Model puts content in text but not in facts → token-coverage validator (Section 3) |
| Model copies the quote; code replaces it with the exact transcript span | Pointer-only quotes (turn IDs, code prints whole turn) | All 58 reference quotes match their transcript after lowercase + punctuation strip + collapsing immediate word repeats, and all sit inside one same-speaker run of turns \[VERIFIED: my script on your 5 examples\]. Exact substring match alone covers only 50/58 | Quote too loose → fuzzy-repair rate reported per run |
| Explanation lines model-written, ≤20 words | Template per fact type | References use formulaic "Documents the …" lines; they are 26% of reference characters vs 31% quotes and 43% bullet text \[VERIFIED: my count on your 5 examples\] | Explanations dominate latency → switch to templates (latency ladder rung 3) |
| DOB, phone, times rendered by code from normalized values | Model formats them | References normalize DOB `06/04/1951` and phone `(202)-555-0101` \[VERIFIED: your examples\]; formatting is deterministic work | Normalizer misses a spoken pattern → unit tests on 50 spoken-number variants |
| Timestamp line from request metadata | Model generates it | `[2000-01-01 14:41 UTC]` never appears in any transcript \[VERIFIED: your examples\] | Metadata absent → render "timestamp not provided" (open question Q6) |
| Drug names rendered in tall-man lettering from a lookup table | Model writes casing | References use `LORazepam` \[VERIFIED: your examples\] | Table incomplete → fall back to transcript casing, log miss |

### Schema (abridged)

```json
{
  "not_applicable": false,
  "na_reason": null,
  "identity": {
    "patient_name":  {"value": "Mara Ellis", "status": "stated|unclear|not_stated", "turn_ids": [1]},
    "patient_dob":   {"value": "1951-06-04", "status": "stated", "turn_ids": [2, 3]},
    "caller_name":   {"value": "Nina", "status": "stated", "turn_ids": [1]},
    "relationship":  {"value": "daughter", "status": "stated", "turn_ids": [6]},
    "callback_phone":{"value": "2025550101", "status": "stated", "turn_ids": [7]}
  },
  "chief_complaint": {"text": "...", "speaker": "Caller", "turn_ids": [14], "quote": "...", "explanation": "..."},
  "bullets": [{
    "section": "Assessment|Response|Education",
    "text": "Pain returned at approximately 8-9/10 ...",
    "speaker": "Caller", "turn_ids": [12], "quote": "...", "explanation": "...",
    "facts": [{"type": "symptom", "name": "pain", "severity": "8-9/10", "certainty": "stated"},
              {"type": "medication", "name": "morphine", "dose": "0.25", "unit": "mL",
               "route": "PO", "frequency": "q4h PRN", "certainty": "stated", "status": "advised"}]
  }],
  "risk_flags": [{"category": "uncontrolled_symptom", "turn_ids": [12], "quote": "..."}]
}
```

`status` for actions takes `planned | completed | advised`, and `certainty` takes `stated | unclear`. The renderer turns `unclear` into the word "unclear" and `planned` into "Planned to …" wording, so the two safety rules are enforced by code, not by prose style.

## 3. Pipeline architecture

One LLM call, wrapped in deterministic pre-processing and deterministic validation, with at most one targeted retry. Anything that fails validation after that is removed and flagged for nurse review, never shown as verified.

| Option | Decode passes | Fits p95 < 15 s? | Verdict |
| --- | --- | --- | --- |
| **Pre-process → single pass (JSON) → validate → ≤1 retry → render** | 1 (2 on retry) | Yes, if output ≈1K tokens \[ASSUMPTION: Section 7 arithmetic\] | **Chosen (REQUIRED core)** |
| Extract facts, then summarize | 2 | Roughly doubles decode time | Rejected; the typed `facts[]` already gives the extraction |
| Generate, then LLM verifier | 2+ | Adds a full prefill + decode | Rejected; code verifies quotes and values more cheaply and reproducibly |
| Rules only, no LLM | 0 | Yes | Rejected; cannot write clinically useful prose |

### Deterministic pre-processing (REQUIRED)

1. Split turns on `Nurse ->` / `Caller ->`, assign turn IDs `T1…Tn`, and merge consecutive same-speaker turns into blocks for quote checking.
2. Detect spoken numbers ("two zero two five five five…", "June fourth, nineteen fifty-one", "eight-nine") and store normalized candidates in a side table. The transcript text itself is never rewritten, so quotes stay verbatim.
3. Build identity candidates (names after "this is", "patient's name", spelled-out letters like "B E N N E T T") and drug-mention candidates from a formulary lexicon.
4. Pass the model the numbered transcript plus a short candidates table (\~50–100 tokens) \[ASSUMPTION: improves identity accuracy on ASR-noisy numbers; ablated in Experiment 5\].

### Validators (all deterministic)

| ID | Check | Failure action |
| --- | --- | --- |
| V1 | JSON parses and matches the schema | Retry |
| V2 | All four sections present; empty Response/Education render as "None documented during call" | Render placeholder |
| V3 | Quote ⊂ cited same-speaker turn block after normalization; fuzzy repair if ratio ≥0.90, then the exact transcript span replaces the model's quote | Retry if <0.90 |
| V4 | Quote speaker equals turn speaker; bullet verbs match speaker ("Caller reported" vs "Nurse stated/advised") | Retry |
| V5 | Every number in bullet text and `facts[]` (after spoken-number normalization) appears in the cited turns or ±2 neighbouring turns, with a compatible unit | Retry, then drop bullet + flag |
| V6 | Every drug name fuzzy-matches (Jaro-Winkler ≥0.90) a drug mention in the transcript AND the formulary lexicon; transcript drugs outside the lexicon force `certainty=unclear` | Flag "possible mishearing" (catches the reference's `carfentanil`) |
| V7 | Identity values equal a pre-processing candidate; conflicting candidates (e.g., Nadine / Noreen / Norine / Nora Quinn in example 3) require `unclear` or the self-stated value plus a UI note | Flag identity conflict |
| V8 | `status=completed` requires completion cues in the cited turn ("I sent", "I've put in", "was delivered") and no future cues ("I will", "I'll", "going to", "let me"); `planned` text must say "Planned to" | Rewrite status to planned + flag |
| V9 | Hedges near a cited value ("I think", "maybe", "about", "not sure", "\[inaudible\]") require `certainty=unclear` or hedged wording | Force unclear |
| V10 | Every bullet-text token that is a number or drug also appears in `facts[]` (no untyped claims) | Retry |
| V11 | Not-Applicable consistency (below) | Override |
| V12 | Risk flags: model flags must carry a verified quote; rule flags are unioned in | Union |

**Retry and fallback.** One retry, only if the remaining latency budget exceeds the measured p95 generation time; the retry prompt lists the failed checks by bullet. After that, failing bullets are removed, `needs_nurse_review=true` is set, and the reasons are listed in the API response.

### Not-Applicable detection: rules first, LLM for the middle

- A clinical-content score counts symptom, medication, supply and care-action lexicon hits in caller and nurse turns.
- Score 0 and <15 turns → Not Applicable without calling the LLM (also a latency win).
- High score → never Not Applicable.
- Middle band → the model's `not_applicable` field decides.
- Any high-risk rule hit vetoes Not Applicable. Suppressing a real clinical call is worse than summarizing a thin one.

### High-risk flagging: hybrid, recall-first

Flags = rule hits ∪ model flags with verified quotes. Rules run over the full transcript with per-category lexicons: breathing ("trouble breathing", "can't breathe", "gasping"), uncontrolled symptoms (pain ≥7/10, "not working", "nothing helps"), medication concerns ("ran out", "too many", "wrong dose", missed doses), suicidal statements, and escalation requests ("send someone", "911", "hospital", "come out"). A 5-token negation window suppresses rule hits like "no trouble breathing", except suicidal phrases, which are never suppressed. Every flag shows its source (rule, model, or both) and its quote in the UI.

## 4. Synthetic data

Generate structured fact records first, have a model voice them as transcripts (local Gemma 4 31B QAT for train/dev, frontier API models for eval) that tag every turn with the facts it expresses, inject ASR noise deterministically, then build gold JSON from the records. Gold is correct by construction and every metric becomes a set comparison. Sizes: 800 train, 100 dev, 400 eval, plus your 5 real examples as a never-trained sanity set.

| Decision | Alternatives | Evidence | Risk if wrong → detection |
| --- | --- | --- | --- |
| Fact record → transcript → gold (REQUIRED) | Teacher writes transcript and summary, then verify | Deterministic scoring needs ground-truth facts; a teacher-written summary can carry the same errors your reference shows (`carfentanil` repeated without an "unclear" mark) \[VERIFIED: your example 3\] | Transcripts too clean or formulaic → manually review 20, plus type-token ratio vs your 5 examples |
| Train/dev teacher = Gemma 4 31B QAT, local; eval teacher = frontier API models (RECOMMENDED) | Same 12B checkpoint (self-generation); frontier API for train data too | Labels come from fact records, so the teacher supplies surface realism; voicing eval with a different model than train tests generalization (see External LLM section). Gemma 4 is Apache 2.0, which places no restriction on training on outputs \[VERIFIED: [license](https://ai.google.dev/gemma/apache_2)\] | Train/eval style gap too large → report dev and eval side by side; 31B QAT fits 48 GB \[VERIFIED size: recipe\] |
| Each generated turn carries `fact_ids`; gold quotes are the sentences in turns tagged with that fact | Fuzzy-search quotes afterward | Makes quote gold exact and speaker-correct by construction | Teacher mis-tags → drop records where a fact's value is not found in its tagged turn (string check) |
| ASR noise injected by code, not the LLM | Ask the teacher to "add ASR errors" | Deterministic, seeded, and the noise level per category is controllable | Noise unrealistic → compare error patterns with your 5 real transcripts |
| Train size 800 | 200 / 2,000+ | LIMA reached strong format-following with 1,000 curated examples \[VERIFIED: [LIMA](https://arxiv.org/abs/2305.11206)\]; our task is format + faithfulness on one domain | Too few → learning curve on 200/400/800 (OPTIONAL) |

### Fact records

Each record holds identity (patient name, DOB, caller name, relationship, callback number), primary reason, symptoms (name, severity, onset/duration, certainty), medications (name, strength, dose, unit, route, frequency, PRN, last dose time, remaining supply, certainty), supply requests, nurse actions (type + planned/completed), education items, pertinent negatives, and expected risk flags. Medications come from a curated list of \~40 common hospice comfort medications with plausible strengths \[ASSUMPTION: list compiled by me from general knowledge, not clinically validated; stated as a limitation\].

### ASR-noise methods (seeded)

1. Numbers spoken as words: DOB and phone always, doses and times 70% ("two zero two five five five…", "zero point two five").
2. Name variants on repetition: 1–2 character edits and sound-alikes (Nadine / Noreen / Norine), letter-by-letter spelling.
3. Drug-name confusions from a sound-alike table ("lore as a pam", "more fine"), plus out-of-formulary mishears such as `carfentanil`.
4. Fillers, false starts, repeated words, fragments split across turns, answers arriving one turn late (as in your example 1).
5. `[inaudible]` tokens and dropped words, heavier in the ASR-error category.

### Scenario taxonomy and counts

Each transcript has one primary category and may carry secondary tags. Personas vary caller relationship (spouse, child, facility nurse, patient), verbosity, and distraction.

| Category | Train | Dev | Eval |
| --- | --- | --- | --- |
| Routine (symptom update, general question) | 120 | 15 | 60 |
| Ambiguous (vague, contradictory, caller unsure) | 120 | 15 | 60 |
| ASR-error heavy | 120 | 15 | 60 |
| Medication (dosing, timing, side effects, administration) | 140 | 17 | 70 |
| Supply request (refills, equipment, delivery) | 100 | 13 | 50 |
| High-risk escalation (5 sub-types × 14 in eval: uncontrolled symptom, medication concern, suicidal statement, breathing, escalation request) | 140 | 17 | 70 |
| Not Applicable (wrong number, hang-up, billing/admin only, test call) | 60 | 8 | 30 |
| **Total** | **800** | **100** | **400** |

### Eval size justification

With a transcript-level pass rate, the Wilson 95% lower bound clears 95% only if the observed rate and n are high enough \[VERIFIED: my Wilson computation\].

| n | Observed 97% → 95% CI | Observed 98% → 95% CI |
| --- | --- | --- |
| 100 | 91.5–99.0% | 93.0–99.4% |
| 200 | 93.6–98.6% | 95.0–99.2% |
| 400 | 94.8–98.3% | 96.1–99.0% |
| 600 | 95.3–98.1% | 96.5–98.9% |

n = 400 lets an observed 98% claim ≥95% with the lower bound. Fact-level metrics have thousands of slots but are clustered by transcript, so their CIs use a transcript-level cluster bootstrap (Section 6).

### Leakage-safe splits

- Split by scenario template, persona, and patient identity; no name, DOB, phone, or (drug, dose) combination is shared across splits.
- Drop near-duplicate transcripts across splits (MinHash Jaccard ≥0.8) \[ASSUMPTION: threshold\].
- Eval uses different generation and noise seeds and a paraphrased teacher prompt, to reduce shared style with train.
- Your 5 real examples are hand-annotated into fact records (\~1 hour) and used only as a sanity set, never for training or tuning.

## 5. Training

BF16 LoRA, rank 16, on all attention and MLP projections of the language model, trained with TRL `SFTTrainer` on the checkpoint's own dequantized weights (path P1). Two epochs over 800 examples, learning rate 1e-4, completion-only loss, selected by dev critical-fact accuracy rather than loss.

| Decision | Alternatives | Evidence | Risk if wrong → detection |
| --- | --- | --- | --- |
| LoRA in BF16 on dequantized ct | QLoRA NF4; full SFT | Train/serve base match (Section 1B). Full SFT of 12B needs optimizer state far beyond one GPU and would move weights off the QAT lattice \[ASSUMPTION: standard AdamW memory arithmetic\] | OOM on 48 GB → QLoRA fallback on unquantized QAT (P6) |
| Rank 16, alpha 32, dropout 0.05 | Rank 8 / 32 | vLLM issue shows rank-32 all-layer adapters unstable on W4A16 bases, rank 8 stable \[VERIFIED: #50059\] | Parity gate fails → retrain at rank 8 |
| Targets: q, k, v, o, gate, up, down in every text layer; exclude embeddings, lm\_head, vision/audio embedders | q, v only | All-linear LoRA was needed to match full fine-tuning in the QLoRA ablation; q+v is only a low-budget baseline \[VERIFIED: [Raschka summary of LoRA and QLoRA](https://sebastianraschka.com/faq/docs/where-to-insert-lora-adapters.html)\]. Exact Gemma 4 module names \[ASSUMPTION: print the module tree and assert matched counts\] | Wrong substring match → print trainable-parameter count by group before training |
| LR 1e-4, cosine, 3% warmup, 2 epochs | 5e-5 / 2e-4; 1 / 3 epochs | TRL recommends ≈1e-4 for adapters \[VERIFIED: [TRL SFT docs](https://huggingface.co/docs/trl/sft_trainer.md)\]. LIMA selected checkpoints on a small dev set because perplexity did not track quality | Overfit → dev accuracy peaks at epoch 1 |
| Batch 1 × grad-accum 16 (≈100 optimizer steps) | Larger micro-batch | Long sequences; single GPU | Noisy updates → watch grad\_norm |
| `max_length` 7168, packing off, assert zero truncation | Default 1024; packing | TRL default `max_length` is 1024 and truncation keeps the start, which would silently cut the target JSON \[VERIFIED: TRL SFTConfig\] | Truncated targets → hard assert in data prep |
| Conversational prompt-completion dataset, completion-only loss | `assistant_only_loss` | Completion-only loss is the default for prompt-completion data; `assistant_only_loss` needs `{% generation %}` tags in the chat template \[VERIFIED: TRL docs\] | Loss on prompt tokens → check label mask on one batch |
| Default `loss_type="chunked_nll"` | Liger kernel | Skips `lm_head` on ignored tokens and chunks cross-entropy, so memory does not scale with vocab × sequence, which matters with a 262K vocabulary \[VERIFIED: TRL docs\] | — |
| Load the model ourselves in BF16 with `CompressedTensorsConfig(dequantize=True)` and pass it in | Pass a model ID string | TRL defaults to float32 when given a string \[VERIFIED: TRL docs\]; SFTTrainer supports causal LMs only \[VERIFIED\]. Whether the 12B multimodal class trains cleanly as a causal LM \[ASSUMPTION: Experiment 3\] | Load error → Unsloth, which Google names for QAT fine-tuning \[VERIFIED: [QAT blog](https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/)\] |
| Chat template: native `system` role, no `<\|think\|>`, completion starts with the empty thought block the model emits | Omit the thought block | Model card thinking-off behavior \[VERIFIED\] | Train/infer mismatch → compare rendered training string with a raw vLLM generation |

### Memory and time on one L40S 48 GB (to be measured)

- Base BF16 weights ≈23.9 GB (11.95B × 2 bytes) \[VERIFIED param count\].
- LoRA rank 16 over 7 projections × 48 layers ≈ 60–70M trainable params plus AdamW state ≈ 1 GB \[ASSUMPTION: estimated from hidden size 3840\].
- Activations with gradient checkpointing at 7K tokens ≈ 4–6 GB \[ASSUMPTION\].
- Expected peak 30–35 GB, so 48 GB fits and 24 GB does not.
- Time: \~5M training tokens per epoch at \~35–45% of L40S peak BF16 ≈ 45–70 min per epoch \[ASSUMPTION: vendor peak \~362 TFLOPS dense\]. Measure seconds per step on the first 10 steps and extrapolate.

### Sweep that fits the budget (3 runs)

| Run | Rank | LR | Epochs evaluated |
| --- | --- | --- | --- |
| A (default) | 16 | 1e-4 | 1, 2 |
| B | 16 | 2e-4 | 1, 2 |
| C (parity insurance) | 8 | 1e-4 | 2 |

Each checkpoint is scored on the 100 dev transcripts through vLLM with the full validator pipeline (\~5 min at concurrency 8 \[ASSUMPTION\]). The winner is the highest dev critical-fact accuracy with zero increase in hallucinated critical values.

### Risks

- Overfitting to synthetic style → track the 5 real examples every checkpoint; stop if they degrade while dev improves.
- Learning hallucinations from gold → gold passes the same validators as model output before training.
- Forgetting → low relevance for a single-task adapter; spot-check 10 generic prompts.

**DPO: no.** It needs preference pairs and a second training stage, and SFT on validator-clean gold already targets the main failure modes \[ASSUMPTION: judgement, not evidence\]. Only if time remains: pairs of (validator-failed output, repaired output) from dev runs.

## 6. Evaluation

The headline metric is Critical-Fact Accuracy (CFA) ≥ 95% on the 400-transcript eval set, computed deterministically from fact records, with release gates on hallucinated medications, high-risk recall, and Not-Applicable accuracy. Every metric is a set comparison between the model's typed JSON and the gold record; no LLM judge touches the headline.

### Headline metric

```latex
\mathrm{CFA} = \frac{\#\,\text{gold critical slots matched}}{\#\,\text{gold critical slots} + \#\,\text{unsupported critical values in output}}
```

- **Critical slots:** patient name, DOB, caller name, relationship, callback phone; each medication tuple (name, dose, unit, route, frequency, status); each symptom (name, severity); each nurse action (type, planned/completed); each expected risk flag; the Not-Applicable label.
- **Matched** means: normalized value equal, correct speaker attribution, correct certainty (`unclear` vs `stated`), correct action status, and the cited quote passes V3.
- **Unsupported** means a critical value in the output that matches no gold slot. Hallucinations enter the denominator, so the metric cannot be gamed by omission (recall falls) or by over-generation (the denominator grows).
- **Release gates** (reported alongside, all must hold): fabricated medication or dose values = 0 per 400 transcripts; high-risk recall ≥ 98%; Not-Applicable accuracy ≥ 95%; all four sections present in 100% of non-NA outputs.
- **Guard on synthetic gold:** transcripts whose clinical turns mention a drug or number not tagged to any fact are rejected at generation time, so correct extra facts are never scored as hallucinations.

### Component metrics (all required by the brief or by the safety rules)

| Metric | Definition (deterministic) |
| --- | --- |
| Completeness | Recall over all gold slots, including education items and pertinent negatives |
| Factual accuracy | Precision: output slots matching gold or verified in transcript by V3/V5/V6, over all output slots; plus quote-validity rate |
| Identity accuracy | Exact match per field after normalization; `unclear` is correct only when gold is unclear. Reported per field |
| Medication name + dose | P/R/F1 on (name, dose, unit) tuples, strict; relaxed variant on name only; separate route/frequency accuracy |
| Attribution | Share of bullets whose speaker matches the gold fact's speaker |
| Uncertainty preservation | Recall of gold `unclear` slots marked unclear; count of false-certainty errors |
| Planned vs completed | Accuracy of action status |
| Not Applicable | Accuracy, precision, recall |
| High-risk flags | Recall and precision per category |
| Latency | TTFT and end-to-end total (protocol below) |

### Anti-gaming and statistics

- Report every metric per category (routine, ambiguous, ASR-error, medication, supply, high-risk, NA) and on a hard subset (ASR-error + ambiguous).
- Transcript-level "safe pass" (no unsupported critical value, no identity error, all risk flags found, NA correct) with Wilson 95% CI.
- Fact-level metrics use a transcript-level cluster bootstrap (10,000 resamples) for 95% CIs \[ASSUMPTION: standard for clustered data\].
- Baseline vs fine-tuned on the same 400 transcripts: McNemar test on safe pass; paired bootstrap on the CFA difference.
- The 5 real examples are scored separately and never pooled with synthetic results.
- Failure analysis: every failure is tagged with the validator ID that caught it; the report shows counts per ID and the 10 worst transcripts with diffs.

### Semantic layer (secondary, judge panel)

These close the gaps regex cannot (wrong relations, paraphrase, meaning-level omissions). They are reported next to the headline, never instead of it. Panel design and calibration are in the External LLM section.

| Metric | Definition |
| --- | --- |
| Semantic faithfulness | Bullets labelled SUPPORTED by panel majority ÷ all bullets |
| Semantic completeness | Gold facts labelled PRESENT by panel majority ÷ all gold facts; critical tier reported separately |
| Distortion rate | Gold facts labelled DISTORTED ÷ gold facts the summary mentions |
| Judge validity | Panel κ vs 40 human-labelled summaries; detection rate per mutation type |

### Latency protocol

| Item | Definition |
| --- | --- |
| End-to-end | API request received → validated JSON + rendered text returned, including pre-processing, LLM, validators, and any retry |
| TTFT | First generated token from the vLLM stream, plus first byte to the client |
| Warm-up | 10 requests discarded after each server start |
| Runs | All 400 eval transcripts sequentially at concurrency 1 (headline); 100 at concurrency 4 (secondary) |
| Statistics | p50 / p95 / p99, bootstrap CI on p95 |
| Configs | Baseline, fine-tuned, fine-tuned + each latency rung actually used |
| Prefix caching | On (production setting) for headline; one run with it off, as the vLLM recipe advises for benchmarking \[VERIFIED: recipe\] |
| Logged | GPU model, driver, CUDA, vLLM version and flags, `vllm collect-env`, model revision SHA, adapter hash |

## 7. Latency

At batch 1, latency is decode time: output tokens ÷ tokens per second. Prefill is under a second on data-center GPUs; the output is \~1,000–1,800 tokens and every one reads \~8.2 GB of weights. So the levers, in order, are fewer output tokens, faster memory, and speculative decoding.

### Token arithmetic (to be measured with the real tokenizer)

- **Input:** longest transcript 13,219 characters ≈ 3,150–3,780 tokens \[ASSUMPTION: 3.5–4.2 chars/token\]. Plus system prompt and schema instructions \~900, candidates table \~100, turn-ID prefixes \~300 after merging same-speaker turns. Prompt ≈ 4.5–5.2K tokens.
- **Output:** the longest reference is 5,509 characters ≈ 1,300–1,600 tokens as plain text \[ASSUMPTION\]. JSON keys and `facts[]` add \~15–30% with short keys \[ASSUMPTION\]. Expect p95 output ≈ 1,500–1,800 tokens before reduction.
- **Prefill cost:** \~5K tokens × 2 × 12B ≈ 1.2×10^14 FLOPs → \~0.5–1 s on L40S, \~0.3 s on H100 \[ASSUMPTION: 40–60% of vendor peak\].
- **Decode cost per token:** reads \~8.2 GB (int4 layers + scales + BF16 embedding/lm\_head) \[ASSUMPTION: derived from the verified 8.3 GB checkpoint size\].

### Estimated decode time at batch 1 (60–80% of memory bandwidth)

| GPU (AWS family) | Bandwidth \[ASSUMPTION: vendor spec\] | Est. tok/s | 900 tokens | 1,200 tokens | 1,800 tokens |
| --- | --- | --- | --- | --- | --- |
| L4 (g6) | 300 GB/s | 22–29 | 31–41 s | 41–55 s | 62–82 s |
| A10G (g5) | 600 GB/s | 44–59 | 15–21 s | 21–27 s | 31–41 s |
| L40S (g6e) | 864 GB/s | 63–84 | 11–14 s | 14–19 s | 21–29 s |
| RTX PRO 6000 (g7e) | \~1.8 TB/s | 132–176 | 5–7 s | 7–9 s | 10–14 s |
| H100 (p5.4xlarge) | 3.35 TB/s | 245–327 | 3–4 s | 4–5 s | 6–7 s |

The reading: on L40S, p95 < 15 s requires the p95 output to fall to \~900–1,000 tokens or a working speculative decoder. On H100 it passes with room for one retry. These are estimates; Experiment 1 replaces them with measured TPOT.

### Optimization ladder (apply in order, stop when p95 < 15 s)

| Rung | Change | Expected effect | Status |
| --- | --- | --- | --- |
| 0 | Measure baseline: TTFT, TPOT, output-token distribution | — | REQUIRED |
| 1 | Thinking off | Removes all reasoning tokens | REQUIRED (Section 1D) |
| 2 | Compact JSON: short keys, no whitespace, `max_tokens` cap, explanations ≤20 words | −15–25% output tokens \[ASSUMPTION\] | REQUIRED |
| 3 | vLLM prefix caching of the fixed system prompt; W4A16 kernels (already default) | TTFT only; decode unchanged | RECOMMENDED, free |
| 4 | Quote pointers: model emits turn IDs + first/last 3 words; code renders the verbatim span | Quotes are 31% of reference characters → up to −25% tokens \[VERIFIED share: your examples; saving ASSUMPTION\] | RECOMMENDED if rung 2 is not enough |
| 5 | Templated explanations by fact type | Explanations are 26% of reference characters → up to −20% | OPTIONAL; costs some fidelity to reference style |
| 6 | Speculative decoding: MTP with the QAT assistant, or n-gram prompt lookup | 1.3–2× decode \[ASSUMPTION\] | OPTIONAL (Section 1E); verify with LoRA + JSON |
| 7 | Faster GPU (p5.4xlarge) | \~3.9× bandwidth vs L40S \[ASSUMPTION: vendor spec\] | Hardware ask |
| 8 | Merge adapter into W4A16 (P4) if runtime-LoRA TPOT overhead is large | Removes LoRA kernel overhead | Only if baseline vs fine-tuned TPOT differs >15% |

Not pursued: FP8 KV cache (weights, not KV, dominate at batch 1 and \~5K context), tensor parallelism (single GPU), multi-LoRA batching (one adapter).

### Streaming

Stream tokens from vLLM to the API so the UI shows progress and TTFT is reported honestly. Validation and rendering run on the complete JSON, so "end-to-end" is measured to the final validated response, never to first token.

## 8. Safety and consistency controls

Every safety rule in the brief has four layers: a prompt/training measure, a deterministic validator, an eval metric, and a UI flag. Nothing relies on the model "behaving" alone.

| Safety rule | Prompt / training measure | Validator | Eval metric | UI flag |
| --- | --- | --- | --- | --- |
| No invented identity, symptoms, meds, doses, actions, outcomes | System rule "only what is said"; gold built from fact records and validator-clean | V3 quote-in-source, V5 numbers, V6 drugs, V7 identity, V10 no untyped claims | CFA unsupported count; factual precision; med tuple F1; fabricated-med gate = 0 | "Removed unverified item" note with reason |
| Correct attribution | `speaker` field per bullet; gold speakers from turn tags | V4 speaker match and verb check | Attribution accuracy | Caller/Nurse label on every bullet |
| Preserve uncertainty | `certainty` field; noise-injected training cases with gold `unclear` | V6 out-of-formulary drug, V7 identity conflict, V9 hedges | Uncertainty recall; false-certainty count | Amber "unclear" chip |
| Planned ≠ completed | `status` field; renderer writes "Planned to…" | V8 completion vs future cues | Planned/completed accuracy | "Planned" tag on actions |
| Not Applicable when content is thin | `not_applicable` + reason; NA examples in train | V11 rule gate with high-risk veto | NA accuracy / precision / recall | Grey NA banner with reason |
| Flag high-risk content | `risk_flags` with quotes; high-risk sub-types in train | V12 rule lexicon ∪ model flags | High-risk recall (gate ≥98%) and precision per category | Red "Nurse review" banner: category, quote, source (rule / model / both) |
| Consistency | Greedy decoding, fixed prompt and schema, pinned versions and revision SHA | Determinism check: same input 3× and across restarts | Output agreement rate; seed-to-seed variance (Section 1C) | — |

### Known failure modes and how the design addresses them

A Nature Medicine study of adapted LLMs on four clinical summarization tasks (including doctor–patient dialogue) found physician readers rated the best models' summaries equivalent or superior to experts' in most cases, but its safety analysis still linked errors to potential harm and categorized fabricated information, for LLMs and experts alike \[VERIFIED: [Van Veen et al. 2024](https://arxiv.org/abs/2309.07430)\]. That supports a verify-everything design rather than trusting average quality.

| Failure mode | Where it appears in your data | Design response |
| --- | --- | --- |
| Fabrication (value not in source) | — | Quotes are copied from the transcript by code; numbers and drugs must appear in cited turns |
| ASR mishearing propagated as fact | Reference example 3 repeats `carfentanil` with no "unclear" \[VERIFIED: your YAML\] | Out-of-formulary drugs force `unclear` and a flag |
| Identity conflict | Example 3: Nadine / Noreen / Norine vs self-stated Nora Quinn \[VERIFIED: your YAML\] | V7 requires `unclear` or the self-stated value, and surfaces the conflict |
| Misattribution | Nurse repeats caller's numbers (example 1) | Speaker is taken from the turn, not inferred |
| Planned shown as done | Example 1: "I will try to put both of those in" → reference says "Planned to submit" \[VERIFIED: your YAML\] | V8 lexical check; renderer wording |
| Omission of pertinent negatives or education | References record negatives and callback instructions | Completeness recall includes them; per-section counts in the report |

## 9. Interface and API

FastAPI (REQUIRED) with one summarize endpoint plus a streaming variant, and a small Gradio page mounted on the same app for the demo (RECOMMENDED). The API returns the rendered summary, the typed JSON, flags, validator results, and timings, so the demo and the evaluation use the same code path.

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/summarize` | Transcript in, full result out |
| `POST /v1/summarize/stream` | Server-sent events: token progress, then the final validated payload |
| `GET /v1/meta` | Model ID, revision SHA, adapter hash, vLLM version, decoding config |
| `GET /healthz` | Liveness, and whether vLLM is reachable |

```json
// request
{
  "transcript": "Nurse -> Meadow Hospice...\nCaller -> ...",
  "call_timestamp_utc": "2000-01-01T14:41:00Z",
  "options": {"adapter": "clin", "debug": false}
}

// response
{
  "status": "ok | not_applicable | needs_review",
  "summary_text": "Chief Complaint\n[2000-01-01 14:41 UTC]\n...",
  "summary_json": { "...": "schema from Section 2" },
  "flags": [{"category": "breathing_concern", "source": "rule+model",
             "quote": "He's having, yeah, he's having trouble breathing", "turn_ids": [19]}],
  "validation": {"failed": [{"id": "V5", "bullet": 3, "reason": "dose 5 mg not in cited turns"}],
                 "repaired": [{"id": "V3", "bullet": 1, "ratio": 0.93}],
                 "removed_bullets": [3], "retries": 1},
  "needs_nurse_review": true,
  "timings_ms": {"preprocess": 4, "ttft": 610, "llm_total": 11850,
                 "validate": 9, "render": 2, "end_to_end": 12010},
  "model": {"id": "google/gemma-4-12B-it-qat-w4a16-ct", "revision": "<sha>",
            "adapter": "clin@<hash>", "vllm": "0.30.0"}
}
```

The Gradio page has a transcript box, a "Load example" dropdown (your 5 examples plus one high-risk and one Not-Applicable synthetic case), the rendered summary with amber/red chips, a flags panel with quotes, and a collapsible validator log with timings. Mounting Gradio inside FastAPI is \[ASSUMPTION: supported by `gr.mount_gradio_app`; a plain HTML page is the fallback\].

## 10. Five-day schedule

Ten working hours per day; GPU jobs run while code is written, and generation, training and evaluation run overnight. Each day ends at a gate; missing a gate triggers the cut-line in the last column.

| Day | Hours | You (coding) | GPU (in parallel) | Gate at end of day | Cut-line if the gate is missed |
| --- | --- | --- | --- | --- | --- |
| 1 | 0–1 | Launch instance, verify driver/CUDA, install pinned vLLM 0.30.0, record revision SHA | Download checkpoint |  |  |
| 1 | 1–3 | Experiments 1–2: serve, real tokenizer counts, chat template, thinking block | Baseline on 5 real examples | Checkpoint serves; 5/5 outputs parse as JSON | Switch to the recipe's Docker image; if still failing, escalate to mentor same day |
| 1 | 3–6 | Pre-processing, schema, prompt, renderer, validators V1–V4 | — |  |  |
| 1 | 6–10 | Fact-record sampler, formulary, ASR-noise injector, gold builder | Pilot: 50 synthetic transcripts | ≥90% of pilot gold passes validators | Simplify scenarios; drop persona variety |
| 2 | 0–3 | Validators V5–V12, NA gate, risk rules, unit tests | Generate 900 train/dev transcripts locally; 400 eval transcripts via the two APIs |  |  |
| 2 | 3–6 | Eval harness: CFA, components, CIs, latency harness, judge-panel harness (MiniCheck + 2 API judges) | Leakage checks, dataset hashes | Data frozen and hashed | Cut eval to 300 (report CI honestly) |
| 2 | 6–10 | Review baseline failures | Baseline on dev 100 + eval 400; Experiments 6–7 (decoding, thinking) on subsets | Baseline numbers and latency recorded | Skip Experiment 7 (keep thinking off) |
| 3 | 0–2 | Experiment 3: dequantize + LoRA smoke test on 10 examples, peak memory | — | Training step runs | QLoRA fallback (P6) |
| 3 | 2–10 | Experiment 4 parity harness; FastAPI + Gradio | Run A (2 epochs), then runs B and C overnight | Run A epoch-1 checkpoint passes parity | Rank 8 only; or merged W4A16 (P4) |
| 4 | 0–3 | Pick winner on dev | Score sweep checkpoints on dev | Winner chosen | Use run A |
| 4 | 3–6 | Latency ladder (Experiments 8–9) if p95 > 15 s | Eval 400 fine-tuned; latency runs baseline vs fine-tuned | p95 measured | Stop at rung 5; request p5.4xlarge for final latency run |
| 4 | 6–10 | Failure analysis; hand-label 40 summaries for judge calibration; prompt/validator fixes (no retraining) | Re-run eval 400 | CFA with CI | Report as-is with failure analysis |
| 5 | 0–3 | Significance tests, figures, fill `outputs/` | Final frozen runs (quality + latency) | All numbers frozen | — |
| 5 | 3–7 | `report.md`, README, reproducibility commands | Clean-environment re-run of README steps | README reproduces one eval end-to-end | Drop OPTIONAL sections from report |
| 5 | 7–10 | Demo video, ZIP, final check | — | Submitted | — |

**Only if time remains** (in this order): n-gram or MTP speculative decoding (if not already needed), learning curve 200/400/800, 31B QAT teacher for realism, DPO on validator-failed vs repaired pairs, Batch Invariance mode test.

## 11. Submission checklist

One ZIP with the five required parts plus an `env/` folder for reproducibility; the report is organized so each grading item in the brief maps to one heading.

```text
submission/
  README.md                 install, serve, run API/UI, reproduce eval + latency
  report.md  (+ report.pdf)
  code/
    pipeline/   preprocess.py  schema.py  prompt.py  validate.py  render.py  risk_rules.py  na_gate.py
    serve/      launch_vllm.sh (pinned flags, --revision)
    api/        app.py (FastAPI + Gradio)
    data_gen/   sample_facts.py  realize_transcripts.py  asr_noise.py  build_gold.py  split.py
    train/      train_lora.py  configs/run_{A,B,C}.yaml
    eval/       score.py  stats.py  latency.py
    tests/      test_validators.py  test_numbers.py  test_render.py
  data/         train.jsonl  dev.jsonl  eval.jsonl  real5_sanity.jsonl  formulary.csv  data_card.md  SHA256SUMS
  outputs/      baseline/  finetuned/  (JSON + rendered text per transcript)
                eval_reports/*.json  latency/*.csv  failure_cases.md  figures/
  env/          requirements.lock  collect_env.txt  nvidia_smi.txt  model_revision.txt
  demo/         demo.mp4
```

### Report outline mapped to the brief

| Report section | Brief item covered |
| --- | --- |
| 1. Model and hardware | Constraint 2 (model version, inference config, hardware, rationale) |
| 2. Pipeline and deterministic validation | Task 1 |
| 3. Interface / API | Task 2 |
| 4. Synthetic data (eval + SFT) | Tasks 3 and 6 |
| 5. Evaluation method and metric definition | Tasks 4 and 5 (definition, dataset size, failure cases) |
| 6. Results: baseline vs fine-tuned, quality and latency, with CIs and significance | Task 8 |
| 7. Latency analysis and optimizations | Tasks 7 and 8 |
| 8. Safety, accuracy, consistency, latency methods | Task 9 and the six safety rules |
| 9. Limitations | Submission item 5 |

### Demo video script (≤3 min)

1. 0:00–0:20 — Architecture slide: one call, validators, flags.
2. 0:20–1:00 — Paste real example 1; show rendered summary, verbatim quotes, "Planned to" wording, timings panel.
3. 1:00–1:40 — Real example 3; show identity-conflict note and the `carfentanil` "unclear" flag; red breathing-concern banner.
4. 1:40–2:10 — Synthetic high-risk case (suicidal statement) → nurse-review banner with rule + model source.
5. 2:10–2:30 — Wrong-number transcript → Not Applicable.
6. 2:30–3:00 — Results table: baseline vs fine-tuned CFA and p95 latency.

### Reproducibility

- Pin vLLM, Transformers, TRL, PEFT, compressed-tensors, torch in `requirements.lock`; record model revision SHA and adapter SHA256.
- Seeds for fact sampling, noise injection, splits, and training; greedy decoding at eval.
- One command per stage: `make data`, `make train`, `make eval`, `make latency`, `make serve`.

## 12. Risks and limitations

The two biggest risks are latency on a 48 GB L40S and runtime-LoRA correctness over the int4 base; both have a measured early warning on Day 1–3 and a pre-planned fallback.

| # | Risk | Impact | Likelihood | Early-warning signal | Mitigation |
| --- | --- | --- | --- | --- | --- |
| 1 | p95 > 15 s on L40S | High | High | Experiment 1 TPOT >12 ms or p95 output >1,100 tokens | Latency ladder rungs 2–6; request p5.4xlarge for the final run |
| 2 | vLLM LoRA over compressed-tensors gives wrong or non-reproducible output | High | Medium | Experiment 4: HF vs vLLM greedy mismatch >5% of tokens, or restart-to-restart diffs | Rank 8; merge-and-requantize (P4) and report it transparently |
| 3 | CFA below 95% | High | Medium | Dev CFA <93% after run A | Failure analysis by validator ID; targeted data for weak categories; stricter removal of unsupported items raises precision |
| 4 | Synthetic eval easier than real calls | High | Medium | Baseline near-perfect on synthetic but weak on the 5 real examples | Hard subset; heavier noise; report real-5 separately and state the gap |
| 5 | 12B multimodal class does not train cleanly in TRL | Medium | Medium | Experiment 3 error or OOM | Unsloth; QLoRA (P6) on the unquantized QAT checkpoint |
| 6 | Version incompatibility (vLLM / Transformers / config warnings) | Medium | Medium | Load errors in Experiment 1 | Pinned `vllm/vllm-openai:v0.30.0` image; same image for all runs |
| 7 | JSON constraint clashes with the empty thought block | Medium | Medium | Parse failures or empty outputs in Experiment 5 | `--reasoning-parser gemma4`; defensive strip; unconstrained JSON + repair + retry |
| 8 | Errors in synthetic gold | High | Low–Medium | Gold fails its own validators; spot-check of 20 records | Reject failing records; fact-tag string checks |
| 9 | High-risk recall below 98% | High | Low | Dev recall per category | Expand rule lexicon; union keeps recall-first |
| 10 | GPU access delayed | High | Low–Medium | No instance by end of Day 1 hour 1 | Ask mentor today (message below); code and data generation proceed on any GPU ≥24 GB |

**Limitations to state in the report:** synthetic English data only; formulary and dose ranges not clinically validated; no real clinician review; automatic metrics measure fact fidelity, not clinical usefulness; latency measured on one GPU type at low concurrency.

## Hardware request

Ask for **g6e.2xlarge (1× L40S 48 GB)** as the cheapest instance that supports every step, with a **p5.4xlarge (1× H100 80 GB)** day in reserve if measured p95 misses 15 s. 48 GB is set by training, not serving: serving needs \~10 GB, but LoRA on the dequantized BF16 base needs \~30–35 GB (Section 5). Latency is set by memory bandwidth (Section 7).

|  | g6e.2xlarge (recommended) | p5.4xlarge (latency insurance) | g7e.2xlarge (alternative) |
| --- | --- | --- | --- |
| GPU | 1× L40S, 48 GB \[VERIFIED: [AWS accelerated computing page](https://aws.amazon.com/ec2/instance-types/accelerated-computing/)\] | 1× H100, 80 GB HBM3 \[VERIFIED: same page\] | 1× RTX PRO 6000 Blackwell, 96 GB \[VERIFIED: same page\] |
| vCPU / RAM / local disk | 8 / 64 GiB / EBS \[VERIFIED\] | 16 / 256 GiB / 3.84 TB NVMe \[VERIFIED\] | 8 / 64 GiB / 1.9 TB NVMe \[VERIFIED\] |
| Memory bandwidth | 864 GB/s \[ASSUMPTION: vendor spec\] | 3.35 TB/s \[ASSUMPTION\] | \~1.8 TB/s \[ASSUMPTION\] |
| Training (P1, BF16 LoRA) | Yes, \~30–35 GB peak \[ASSUMPTION\] | Yes, \~2–3× faster \[ASSUMPTION\] | Yes |
| Baseline + fine-tuned serving | Yes | Yes | Yes |
| Speculative decoding (0.4B drafter) | Fits | Fits | Fits |
| Est. decode for 1,200 output tokens | 14–19 s: needs ladder rungs 2–6 | 4–5 s: passes with retry headroom | 7–9 s: likely passes |
| Price (on-demand) | \~$2/hr \[ASSUMPTION: third-party listings put g6e.xlarge at \~$1.86/hr; confirm in the AWS calculator\] | \~$6.9/hr \[ASSUMPTION: third-party listing\] | Check calculator |
| Main risk | p95 borderline | Regional availability: on-demand only in some regions, Capacity Blocks elsewhere \[ASSUMPTION: AWS announcement excerpt; confirm in console\] | Blackwell SM120 software maturity; the LoRA × compressed-tensors issue was reported on SM120 \[VERIFIED: #50059\] |

**Why not cheaper:** g5 (A10G) and g6 (L4) have 24 GB. They serve the 8.3 GB checkpoint, but the BF16 base alone (\~24 GB) blocks the chosen training path, and their decode rate (Section 7 table) puts p95 far above 15 s at our output lengths. **Why not bigger:** p4d/p5.48xlarge are 8-GPU nodes; a 12B model at batch 1 gains nothing from them.

**Cheapest configuration that plausibly meets every requirement:** g6e.2xlarge, conditional on cutting p95 output to \~900–1,000 tokens or a working speculative decoder \[confidence: medium\]. g6e.xlarge has only 32 GiB RAM, tight for loading and dequantizing a 12B model, hence 2xlarge \[ASSUMPTION\].

### System requirements (to be measured)

- Disk: 200 GB gp3 EBS (checkpoint \~9 GB, optional QAT-unquantized \~24 GB, Docker images \~20 GB, caches, adapters \~0.3 GB each) \[ASSUMPTION\].
- RAM: ≥64 GiB \[ASSUMPTION\].
- CUDA: vLLM 0.30.0 PyPI wheels target CUDA 13.0; CUDA 12.9 wheels and `-cu129` images are also published \[VERIFIED: [releases](https://github.com/vllm-project/vllm/releases)\]. Pick the image that matches the AMI's driver (CUDA 13 needs a newer driver than 12.9) \[ASSUMPTION: check `nvidia-smi`\].
- Compute capability: L40S 8.9, H100 9.0, RTX PRO 6000 12.0 \[ASSUMPTION: vendor spec\]; all are supported by vLLM's int4 weight-only kernels \[ASSUMPTION; Experiment 1 confirms\].

### Message to your mentor

> Hi \[name\], for the Gemma 4 12B QAT clinical-summary assignment, could I get a g6e.2xlarge (1× L40S 48 GB, 200 GB EBS) for the 5 days? 48 GB is the minimum that fits LoRA training on the checkpoint's own weights plus vLLM serving. My estimate is that p95 < 15 s is borderline on L40S because generation is memory-bandwidth bound; if my Day-2 measurement confirms that, could I use a p5.4xlarge (1× H100) for about a day for the final latency runs? Three quick questions: may I pick the instance type, is p95 measured one request at a time, and is outbound access to Hugging Face and PyPI allowed? Estimated use: \~60–80 GPU-hours on g6e, plus \~10 on p5.4xlarge only if needed.

## External LLM / API key

Use hosted frontier models for evaluation only: a three-vote judge panel and an independently voiced eval set. They never enter the request path, never produce training data, and never decide the ≥95% headline, which stays deterministic. API cost is not a constraint (confirmed by you), so the choice below optimizes judge quality and independence.

| Use | Decision | Justification | Guardrail |
| --- | --- | --- | --- |
| Faithfulness: is each bullet supported by its cited turns? | Panel of 3: OpenAI's strongest model + Anthropic's strongest model + Bespoke-MiniCheck-7B (local). Majority vote; any 1–1–1 split or abstain goes to human review | A panel drawn from disjoint model families beat a single large judge across six datasets and showed less intra-model bias \[VERIFIED: [Verga et al. 2024](https://arxiv.org/abs/2404.18796)\]. Single judges favor their own outputs (GPT-4 +10%, Claude-v1 +25% win rate) \[VERIFIED: Zheng et al.\]. MiniCheck is purpose-built to decide whether a sentence is supported by a document \[VERIFIED: [model card](https://huggingface.co/bespokelabs/Bespoke-MiniCheck-7B)\] | Binary labels; the API judges must copy the supporting span, which code verifies against the transcript |
| Completeness: is each gold fact expressed in the summary? | Same panel. MiniCheck runs with document = summary, claim = the gold fact as one sentence | Giving the judge the reference answer cut judge failures from 14/20 to 3/20 in Zheng et al. \[VERIFIED\] | Labels PRESENT / ABSENT / DISTORTED plus the bullet ID |
| Section placement, "supported but misleading", nurse usefulness | The two API judges only | Neither regex nor a sentence-level fact-checker can judge these | Reported descriptively; never gated |
| Voicing the 400 eval transcripts from fact records | Split 200/200 between the two API providers; train and dev stay voiced by local Gemma 4 31B QAT | A different generator for eval than for train tests generalization and breaks the "Gemma writes it, Gemma is scored on it" circularity \[ASSUMPTION: style is the main leakage path\]. Eval data is not training data, so provider terms are not engaged | Same fact records, ASR noise and gold builder; report dev (Gemma-voiced) vs eval (frontier-voiced) side by side |
| Training data | Not from APIs: local Gemma 4 31B QAT | OpenAI's terms prohibit using output to develop models that compete with OpenAI \[VERIFIED: [OpenAI terms](https://openai.com/policies/row-terms-of-use/)\]; Anthropic's prohibit using the services to train competing AI models \[VERIFIED: [Anthropic commercial terms](https://www.anthropic.com/legal/archive/c87a6bf8-106e-47d8-9b7b-47ae3a0fecbf)\]. A narrow clinical summarizer is arguably not "competing", but Apache 2.0 Gemma removes the question \[VERIFIED: license\] | — |
| Runtime verifier inside the API | Not used | Adds seconds to a 15 s p95 budget; a real deployment would send patient data to a third party; hosted models change over time | — |

### Model choice

- **Use each provider's strongest generally available model, pinned to a snapshot ID.** As of this week that is GPT-6 Astra (released 3 Sep 2026) \[ASSUMPTION: third-party release timeline; confirm the ID in the API model list\] and Claude Fable 5.1 or Opus 5.5 \[ASSUMPTION: confirm in the Anthropic console\]. Temperature 0, cached outputs.
- **No Google models as judges.** Gemma and Gemini come from the same lab, so same-family preference is a plausible bias \[ASSUMPTION: extends the self-preference finding to sibling models\]. The panel stays disjoint from the system under test.
- **Keep numbers out of MiniCheck's vote.** One benchmark found Bespoke-MiniCheck-7B near chance (46%) on prices and math \[VERIFIED: [Paladin-mini paper](https://arxiv.org/html/2506.20384v1)\], so doses and times stay with the deterministic layer. MiniCheck-7B is CC BY-NC 4.0 \[VERIFIED: model card\]; fine for this assignment, stated as a limitation.
- **Custom harness, not Ragas or DeepEval.** Their faithfulness score is supported claims over total claims \[VERIFIED: [Ragas docs](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)\], which we compute directly; their extra LLM claim-splitting step is unnecessary because our bullets are already atomic and cited, and the two libraries' faithfulness scores diverged on the same tests because of prompt differences \[VERIFIED: [GroUSE](https://arxiv.org/pdf/2409.06595)\]. A \~150-line harness with versioned prompts is easier to defend.

### Making the judges trustworthy

1. **Human calibration:** you label 40 summaries (\~400–600 bullets and gold facts) blind to the judges. Report Cohen's κ for each judge and for the panel. Publish a judge metric only where panel κ ≥ 0.6 \[ASSUMPTION: conventional "substantial agreement" cut-off\].
2. **Mutation tests:** run the panel on summaries with injected errors (swapped drug, flipped negation, planned → completed, wrong speaker, dropped bullet, invented symptom, unsupported "likely due to"). Report detection per error type next to the deterministic layer's.
3. **Disagreement review:** every case where the deterministic layer and the panel disagree is read by hand and lands in the failure-case section.
4. **Pairwise comparisons** (baseline vs fine-tuned), if used, are judged in both orders and counted only when consistent \[VERIFIED: Zheng et al.\].
5. **Reproducibility:** store prompts, model IDs, timestamps and raw judge outputs in `outputs/judge/`; hosted models may not reproduce later \[VERIFIED: Zheng et al. note this for GPT-4\].

If API use were withdrawn later, the panel becomes MiniCheck + local Gemma 4 31B QAT, with the same-family caveat stated.

## References (all opened)

1. Google DeepMind. [gemma-4-12B-it-qat-w4a16-ct model card](https://huggingface.co/google/gemma-4-12B-it-qat-w4a16-ct). 2026.
2. Google. [Gemma 4 QAT Q4\_0 collection](https://huggingface.co/collections/google/gemma-4-qat-q4-0). 2026.
3. Google DeepMind. [gemma-4-12B-it-qat-q4\_0-unquantized-assistant card](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-unquantized-assistant). 2026.
4. Google. [Gemma 4 license (Apache 2.0)](https://ai.google.dev/gemma/apache_2).
5. Lacombe, O.; Sanseviero, O. [Gemma 4 QAT models](https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/). Google blog, 5 Jun 2026.
6. vLLM. [Gemma 4 12B recipe](https://recipes.vllm.ai/Google/gemma-4-12B-it). 2026.
7. vLLM. [Gemma 4 usage guide (recipes repo)](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md). 2026.
8. vLLM. [v0.23.0 release notes](https://github.com/vllm-project/vllm/releases/tag/v0.23.0). 15 Jun 2026.
9. vLLM. [Releases v0.28–v0.30](https://github.com/vllm-project/vllm/releases). 2026.
10. vLLM. [gemma4\_unified API docs](https://docs.vllm.ai/en/latest/api/vllm/model_executor/models/gemma4_unified/). 2026.
11. vLLM issue [#50059: LoRA on compressed-tensors W4A16](https://github.com/vllm-project/vllm/issues/50059). 2026.
12. LMCache. [Gemma 4 recipe](https://docs.lmcache.ai/recipes/gemma4.html). 2026.
13. Hugging Face. [Transformers compressed-tensors docs](https://huggingface.co/docs/transformers/en/quantization/compressed_tensors). v5.17.
14. Hugging Face. [TRL SFT Trainer docs](https://huggingface.co/docs/trl/sft_trainer.md). v1.13.
15. Unsloth. [Gemma 4 QAT docs](https://unsloth.ai/docs/models/gemma-4/qat). 2026.
16. Raschka, S. [Where to insert LoRA adapters](https://sebastianraschka.com/faq/docs/where-to-insert-lora-adapters.html) (summarizes Hu et al. 2021 and Dettmers et al. 2023).
17. Zhou, C. et al. [LIMA: Less Is More for Alignment](https://arxiv.org/abs/2305.11206). 2023.
18. Zheng, L. et al. [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/html/2306.05685v4). 2023.
19. Van Veen, D. et al. [Adapted LLMs can outperform medical experts in clinical text summarization](https://arxiv.org/abs/2309.07430). Nature Medicine, 2024.
20. AWS. [Accelerated computing instance types](https://aws.amazon.com/ec2/instance-types/accelerated-computing/). Page updated 25 Sep 2026.

Added for the judge decision (21–22 opened; 23–28 read from search-result excerpts of the cited pages):

21. Bespoke Labs. [Bespoke-MiniCheck-7B model card](https://huggingface.co/bespokelabs/Bespoke-MiniCheck-7B). 2024.
22. Zheng, L. et al. (ref 18) also supplies the self-preference and reproducibility findings.
23. Verga, P. et al. [Replacing Judges with Juries (PoLL)](https://arxiv.org/abs/2404.18796). 2024.
24. OpenAI. [Terms of Use](https://openai.com/policies/row-terms-of-use/).
25. Anthropic. [Commercial Terms of Service](https://www.anthropic.com/legal/archive/c87a6bf8-106e-47d8-9b7b-47ae3a0fecbf).
26. [Paladin-mini (MiniCheck numeric weakness)](https://arxiv.org/html/2506.20384v1). 2025.
27. [GroUSE: evaluating evaluators](https://arxiv.org/pdf/2409.06595). 2024.
28. Ragas. [Faithfulness metric docs](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/).

Not opened, so not relied on: the Gemma 4 technical report (arXiv 2607.02770) and the original LoRA, QLoRA, PagedAttention and speculative-decoding papers.

## Assumptions to validate

- **Serving:** config-parsing warnings are harmless; LoRA flags work with this checkpoint; KV per 8K sequence <2 GB; decode 55–85 tok/s on L40S; JSON-constraint overhead small; greedy not bit-identical across batch sizes.
- **Tokens:** 3.5–4.2 characters per token; JSON adds 15–30% over plain text; p95 output ≈1,500–1,800 tokens before reduction.
- **Fine-tuning:** QAT-unquantized weights may sit slightly off the int4 grid; merged deltas below half a quantization step round away (P4); NF4 QLoRA mismatches the served int4 base; the 12B multimodal class trains in TRL as a causal LM; training targets must include the empty thought block; peak memory 30–35 GB; 45–70 min per epoch on L40S; exact Gemma 4 module names.
- **Speculative decoding:** vLLM accepts the QAT-unquantized assistant with the ct target; it works with LoRA and JSON constraints; 1.3–2× speedup.
- **Data and eval:** candidates table improves identity accuracy; MinHash threshold 0.8; hospice formulary is plausible but not clinically validated; cluster bootstrap for fact-level CIs.
- **Hardware:** vendor bandwidth and compute-capability figures; third-party prices; p5.4xlarge regional availability; 64 GiB RAM needed for the dequantized load; driver/CUDA pairing; Gradio mounts inside FastAPI.
- **Judgement calls:** greedy ≥ sampling on faithfulness; DPO not worth it in 5 days.

## First 10 experiments (priority order)

| # | Experiment | Pass criterion |
| --- | --- | --- |
| 1 | Serve the exact checkpoint on vLLM 0.30.0 with `--revision`; count real tokens on your 5 examples; baseline TTFT, TPOT, output length, KV-cache size from the startup log | Loads without error; 5/5 outputs parse as JSON; TPOT and output-token p95 recorded, which fixes the latency rung needed |
| 2 | Chat template and thinking block: render with `enable_thinking=False`, inspect one raw generation, confirm the reasoning parser strips the empty block | Content field is clean JSON; training target format decided |
| 3 | Training smoke test: `dequantize=True` load, LoRA r16 on listed modules, 10 steps | Loss falls; peak memory <44 GB; matched-module count as expected; s/step recorded |
| 4 | LoRA parity: HF+PEFT vs vLLM ct+LoRA, greedy, 20 dev transcripts, 3 server restarts; also diff dequantized ct vs QAT-unquantized tensors | Validator-scored metrics within 1 point; ≥95% identical outputs across restarts; else rank 8 or P4 |
| 5 | Output ablation on 50 dev: schema-constrained vs unconstrained JSON; candidates table on/off | 100% parse rate; TPOT overhead <5%; keep whichever has higher CFA |
| 6 | Decoding: greedy vs Google sampling × 3 seeds on 100 dev | Keep greedy unless sampling gains ≥1 point CFA with no more hallucinations |
| 7 | Thinking on vs off on 50 dev | Enable only if ≥2 points CFA and p95 still <15 s |
| 8 | Latency ladder on 100 eval transcripts, one rung at a time | End-to-end p95 <15 s at concurrency 1 |
| 9 | Speculative decoding (OPTIONAL): MTP with the QAT assistant + `TRITON_ATTN`, and n-gram; both with LoRA + JSON | Starts cleanly; greedy outputs identical on 20 transcripts; ≥1.3× decode speedup |
| 10 | Synthetic gold pilot (runs in parallel on Day 1): 50 records through generator and validators, 20 read by hand | ≥90% of gold passes validators; no untagged clinical content |
