# Data curation — no GPU, no LLM, no API

Everything here is deterministic Python. It produces the fact records that later become transcripts (voiced by an LLM),
gold summaries, and every metric. `pytest tests -q` -> 69 tests. See AUDIT.md (validity verdict, defects, fixes) and DATA_CARD.md.

```
pip install pydantic pyyaml pytest
python gold_real5.py      # Step 1: 5 real examples -> data/gold/real5_fact_records.json (anchors machine-resolved)
python make_review.py     #         -> data/gold/real5_review.md  (HUMAN CHECK: every fact beside its transcript turns)
python lexicons.py        # Step 3: formulary + lexicons -> data/lexicons/
python calibrate.py       # Step 5: noise statistics of the 5 real calls -> data/calibration.json
python sample_facts.py    # Step 4: 1,300 seeded fact records -> data/fact_records/{train,dev,eval}.jsonl (+ leakage_report.json)
pytest tests -q
```

| Step | File | What it is |
|---|---|---|
| 2 | `schema.py` | Pydantic fact-record schema; `FactRecord.critical_slots()` enumerates what Critical-Fact Accuracy will score |
| 1 | `gold_real5.py` | 5 hand-annotated records; each fact has a verbatim `anchor` resolved to turn ids (raises if missing/ambiguous) |
| 3 | `lexicons.py` | 56-drug formulary (**not clinically validated**), symptoms, risk phrases per category, hedges, negation, completion/future cues, action/education types |
| 4 | `sample_facts.py` | seeded sampler, 800/100/400, taxonomy counts from the plan, leakage-safe splits |
| 5 | `spoken_numbers.py` | digits -> words and words -> digits (phones, dates, doses, clock); round-trip tested |
| 5 | `asr_noise.py` | seeded noise injector with event log; rates anchored to `data/calibration.json` |
| – | `transcript_utils.py` | turn splitting, normalization, anchor resolution |

## Policy decisions (confirm with mentor)
| | Decision |
|---|---|
| P1 | Ex3 `carfentanil` -> medication `unclear`, name `None`, never emitted as stated (likely ASR for "morphine") |
| P2 | Ex3 caller = **Nora Quinn** (self-stated); Nadine / Noreen / Norine kept as `alternates` |
| P3 | **Ex5 `ibuprofen` -> `unclear`.** Only one mention, by the nurse; caller never named it; "keep that airway open" fits albuterol. The reference summary repeats it as stated. |
| P4 | Ex4 BP `181/154` preserved but `unclear` (caller doubts reading; diastolic implausible) |
| P5 | Ex5 DOB `ten eight two thousand eighteen` -> 2018-10-08 (US month/day assumed) |
| P6 | `escalation_request` also covers nurse-initiated 911/ED (Ex4) |
| P7 | Any regularly used medication with <=2 doses left -> required `medication_concern` (corrected: the sampler flags every drug, not only comfort drugs; 25 of 46 flagged records are non-comfort. Recall-first by design.) |

## Findings that changed the plan
1. The 5 calls are **home-health triage**, not only hospice (pediatric cough; patient on ~15 chronic drugs). The formulary is hospice-core + chronic + pediatric.
2. **0 `[inaudible]` tokens** in the real calls; ASR emits plausible wrong words instead. `[inaudible]` injection is OFF (stress-test flag only).
3. 89% of numerics are spoken as words; 29% of turns follow a same-speaker turn; 33% of caller turns are <=3 words; 4/5 calls have a garbled drug name; 4/5 have name variants.
4. Plan claim re-verified: 58 reference quotes, 50 exact substrings, all 58 recoverable after normalization (test `test_reference_quotes_recoverable_claim`).

## Limitations (be upfront in the report)
* **Leakage control on (drug, dose) covers only 21 of 56 drugs (~40% of medication mentions)**; 35 drugs have <3 dose options, so strict disjointness would remove whole drugs from a split. Fix = add dose options (needs clinical sanity check).
* Name pools are small in dev (9 F / 9 M / 13 surnames) because splits are name-disjoint.
* Drug-symptom pairing is random outside high-risk categories (extraction fidelity is the target, not clinical coherence).
* The 5 gold annotations were written by an AI assistant, not a clinician — verify with `real5_review.md`.
* Noise rates come from 5 calls: coarse anchors, not estimates. Not yet implemented: caller self-correction of DOB, caller-side name garble, `[inaudible]` calibration.
* Synthetic phones are all `555-01xx` (fictional range) across 20 area codes; real-5 values are reserved and never reused.

## Steps 6-9 (added by the audit; still no GPU/API)
```
python build_dataset.py   # repair -> voicer -> asr_noise -> build_gold -> validators; writes data/transcripts, data/gold, data/sft, SHA256SUMS
pytest tests -q
```
`spoken.py` `repair.py` `voicer.py` `build_gold.py` `validate_gold.py` `risk_rules.py` `mutate_gold.py` `preprocess.py` `prompts.py` `build_dataset.py`.
Template voicing is less natural than real calls (AUDIT.md section 4). Next (needs GPU/API): re-voice train/dev with local Gemma 4 31B, eval with two API providers, then the judge panel.
