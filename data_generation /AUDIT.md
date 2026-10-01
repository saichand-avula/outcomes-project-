# AUDIT: clinical data-curation package

Scope: (1) are the shipped files valid, (2) deterministic curation of transcripts and gold from the fact records, with no API, GPU or LLM.
Everything below is reproducible: `pytest tests -q` (69 tests) and `python build_dataset.py` (byte-identical output, SHA in `SHA256SUMS`).

## 1. Validity of the shipped files: VALID, with defects
Verified: all 48 original tests pass; regenerating every file reproduces the shipped bytes; `data/raw/real5_examples.yaml` and
`real5_review.md` are identical to the uploads; all 148 real-5 evidence anchors resolve to the right turn and speaker (independent
re-check); all 1,300 synthetic records are schema-valid, ids unique, names/DOBs/phones disjoint across splits and from the real-5.

| # | Defect | Records | Status |
|---|---|---|---|
| D1 | Symptom and pertinent negative contradict (e.g. confusion + "no confusion") | 30 | fixed in `repair.py` (negative dropped, logged in `annotation_notes`) |
| D2 | Same drug twice with different doses in one call | 23 | fixed in `repair.py` |
| D3 | Nurse recommends 911/ED but no `escalation_request` flag (violates README P6) | 30 | fixed in `repair.py` (flag added) |
| D4 | `critical_slots()` scored 5 identity slots on Not-Applicable records | 98 | fixed in `schema.py`; test updated |
| D5 | ASR "garbles" that are another real drug (buspirone<->bupropion) or a trivial split ("oxy codone") | lexicon | filtered in `asr_noise.drug_confusion` |
| D6 | README P7 says "comfort medication" but sampler flags any drug with <=2 doses left | 25 | **decision**: sampler behaviour kept (recall-first), README corrected |
| D7 | Real-5 gold cited too few turns: real_02 M3 (stop/frequency), M4 (name/frequency), real_01 M5 (name), real_05 N6 (negation) | 5 facts | fixed in `gold_real5.py` |
| D8 | real_01 M4 `dose="1"` inferred from "per tablet" | 1 | set to None (no invented dose). **Please confirm** |
| D9 | Lexicon negation words contain apostrophes ("hasn't", "n't") and phrases "can't breathe"; `transcript_utils.tokens` strips apostrophes so they can never match | lexicon | handled by new `risk_rules.py` tokenizer |
| D10 | Distribution gaps: 0 vitals; context facts only in high-risk calls; `secondary_tags` empty; 20 duplicate NA records | all | **open** (documented; NA duplicates benign) |

Bugs found in shipped code (both fixed with regression tests):
* `spoken_numbers.phone_candidates`: "oh" is a digit AND an interjection. A phone read aloud followed by "Oh, sorry" gave an 11-digit run and the last-10 rule shifted the number (`0355501790` instead of `5035550179`). Now returns all 10-digit windows, preferring ones not edged by "oh".
* `asr_noise._numish` did not recognise hyphenated numerals, so a filler could split "eighty-one uh, milligrams".

## 2. What was built (all deterministic, no LLM)
`spoken.py` (shared spoken forms) -> `repair.py` -> `voicer.py` (template voicing, per-turn fact tags) -> `asr_noise.py` (existing) -> `build_gold.py`
(events folded into facts, evidence grounding, verbatim quotes, SFT target, reference-style rendering) -> `validate_gold.py`, plus `risk_rules.py`,
`mutate_gold.py`, `preprocess.py` (phone/DOB/drug candidates), `prompts.py` (system prompt shared with inference).

Outputs: `data/transcripts/{train,dev,eval,eval_long}.jsonl`, `data/gold/*_gold.jsonl` (full gold + rendered text), `data/sft/{train,dev}.jsonl` (chat format).
Counts: 800 / 100 / 400 (+ 100 long-call eval slice). 195 garbled-drug events, 238 name-drift events, 695 late-answer shifts.
Gold target: mean 6.9 bullets, 3465 chars (p95 4355, max 5158); roughly 1.1k tokens (estimate at ~3.2 chars/token, not a tokenizer measurement).

## 3. Evidence the data is correct
* Every one of the 1,300 records passes all validators (T1-T5 transcript invariants, G1-G10 gold checks: quote-in-source, speaker, attribution, dose/route/frequency/severity/quantity/name/symptom present **in the cited turns only**, planned-vs-completed cues, identity recoverability, polarity, risk-flag grounding). The long slice also has 0 issues.
* Candidate extraction recovers the gold phone and DOB in 2404/2404 cases.
* Rule layer: 100% recall of required risk flags in every category, 0 extra flags on 1,202 non-NA calls. Caveat: the voicer speaks the lexicon's own phrases, so this proves consistency, not generalisation to real speech.

### Mutation test of the validators (known error injected into gold; was it caught?)
| error type | applied | caught | rate |
|---|---|---|---|
| attribution swapped | 1202 | 1202 | 100.0% |
| change dose | 1112 | 1112 | 100.0% |
| change frequency | 991 | 991 | 100.0% |
| change quantity | 175 | 172 | 98.3% |
| change route | 1112 | 1112 | 100.0% |
| change severity | 184 | 184 | 100.0% |
| invented symptom | 1039 | 1039 | 100.0% |
| misattributed evidence | 1167 | 1090 | 93.4% |
| negation flipped | 428 | 428 | 100.0% |
| planned completed flipped | 1116 | 1116 | 100.0% |
| swap drug | 917 | 917 | 100.0% |
| unclear marker removed | 358 | 358 | 100.0% |
| wrong dob | 1202 | 1202 | 100.0% |
| wrong phone | 1202 | 1202 | 100.0% |
| wrong risk category | 273 | 258 | 94.5% |
| wrong speaker | 1202 | 1202 | 100.0% |
| **all** | 13680 | 13585 | 99.3% |

Weak spots, honestly: `misattributed evidence` (a real quote that does not support the claim) is only caught when the claim's content is absent from the cited turns; `wrong risk category` is missed when the swapped category also genuinely occurs in the transcript; 3 `quantity` mutations were no-ops. Completeness (dropped bullets) is **not** a validator job; it is scored by gold-fact alignment, and `drop_bullet` is provided for scorer/judge calibration.

Things the validators/measurements caught while building (all fixed): fillers/repeats splitting phrases ("once a day in in the morning") broke naive matching; a phrase split across two turns ("end my" / "life") defeated a per-turn suicide scan (now scans merged same-speaker blocks); nurse screening questions ("Any trouble breathing?") fired false flags in 80/975 routine calls (nurse speech now counts only for escalation); *agitation* was voiced identically to *restlessness*; 15% of bullets (1,280/8,324) quoted a bare "Okay, thank you." (picker rewritten; 0 remain, test added).

## 4. Realism: template voicing is NOT as natural as real calls
| metric | real-5 | synthetic |
|---|---|---|
| filler_per_1k_tokens | 11.3 | 13.4 |
| immediate_repeat_per_1k_tokens | 11.9 | 15.7 |
| same_speaker_consecutive_turn_rate | 0.293 | 0.263 |
| caller_turns_le3_words_rate | 0.334 | 0.246 |
| caller_dangling_fragment_rate | 0.083 | 0.047 |
| spoken_number_words_per_1k_tokens | 27.9 | 49.5 |
| digit_tokens_per_1k_tokens | 3.3 | 1.8 |
Length: real calls mean 8,245 chars / 112 turns (2,370-13,219). Standard set: mean 2819 chars (p90 4637, max 5750), 59.1 turns. The `eval_long` slice (non-clinical chatter added) averages 8594 chars (5869-10745), 209 turns, and is the one to use for latency and long-context faithfulness.
Not synthesised: incidental chart-reading of many chronic drugs, vitals, diagnoses/history for routine calls, caller self-correction of DOB, `[inaudible]`.
Use this set as the no-GPU baseline; replace train/dev voicing with local Gemma 4 31B when a GPU exists, keep the same fact records, noise and gold builder.

## 5. Decisions needed
P1-P7 (README), especially P3 (ibuprofen unclear) and P1 (carfentanil unclear), which diverge from the reference summaries; P7 broadening (D6); real_01 M4 dose (D8). The real-5 gold was written by an AI, not a clinician: review `data/gold/real5_review.md`.
