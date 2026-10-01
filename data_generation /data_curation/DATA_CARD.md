# DATA CARD

Synthetic hospice/home-health triage call transcripts with gold summaries, built deterministically (seed 20261001) from fact records. No LLM voiced any text.

| split | records | notes |
|---|---|---|
| train | 800 | `data/sft/train.jsonl` chat format |
| dev | 100 | `data/sft/dev.jsonl` |
| eval | 400 | transcripts + gold only (no training use) |
| eval_long | 100 | eval facts with long-call chatter, mean 8594 chars |

Categories (train/dev/eval): routine 120/15/60, ambiguous 120/15/60, asr_error 120/15/60, medication 140/17/70, supply 100/13/50, high_risk 140/17/70, not_applicable 60/8/30.
Leakage: names, DOBs, phones disjoint across splits and from the real-5; (drug, dose) disjoint for 21 of 56 drugs only (see README).
Files per record: transcript turns with `fact_ids` tags, noise events, gold JSON (with fact ids, for scoring), rendered reference-style summary, SFT target (no ids).
Known limits: see AUDIT.md section 4. Formulary is **not clinically validated**. Synthetic phones are 555-01xx. Checksums: `SHA256SUMS` (aggregate d84222fa00e469cd...).
