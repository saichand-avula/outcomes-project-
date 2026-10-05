# Evaluation matrix: finetuned_epoch3_s3 vs finetuned_epoch3_s3_net

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | finetuned_epoch3_s3 (rate, n/d) | finetuned_epoch3_s3_net (rate, n/d) | Δ pts | ≥95% [finetuned_epoch3_s3] (lower 95% bound) | ≥95% [finetuned_epoch3_s3_net] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A2 | Output matches the schema | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A3 | Cited turns exist | D | validated | 100.0% (933/933) | 100.0% (933/933) | +0.0 | ✅ (100%) lower bound ≥95 | ✅ (100%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 99.7% (930/933) | 99.7% (930/933) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 99.7% (930/933) | 99.7% (930/933) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.9% (895/896) | 99.9% (895/896) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 99.7% (392/393) | 99.7% (397/398) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 99.0% (389/393) | 99.0% (394/398) | +0.0 | ✅ (97%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B3 | Drug names appear in the call | D | validated | 99.5% (197/198) | 99.5% (204/205) | +0.0 | ✅ (97%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (445/445) | 100.0% (445/445) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 99.8% (426/427) | 99.8% (426/427) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 100.0% (212/212) | 100.0% (212/212) | +0.0 | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 100.0% (86/86) | 100.0% (86/86) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 97.9% (382/390) | 97.9% (382/390) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | 100.0% (10/10) | +0.0 | ✅ (72%) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 37.5% (15/40) | 37.5% (15/40) | +0.0 | — (24%) | — (24%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 75.7% (78/103) | 77.7% (80/103) | +1.9 | — (67%) | — (69%) |
| **E. Whole call (rules)** | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 95.0% (95/100) | 95.0% (95/100) | +0.0 | ✅ (89%) | ✅ (89%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 53.0% (53/100) | 54.0% (54/100) | +1.0 | — (43%) | — (44%) |
| E1r | Calls with no rule ERROR after automatic quote repair | D | indicator | 97.0% (97/100) | 97.0% (97/100) | +0.0 | ✅ (92%) | ✅ (92%) |
| **F. Meaning (LLM judge)** | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 96.0% (96/100) | 96.0% (96/100) | +0.0 | ✅ (90%) | ✅ (90%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 95.3% (867/910) | 95.3% (867/910) | +0.0 | ✅ (94%) | ✅ (94%) |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 69.0% (69/100) | 69.0% (69/100) | +0.0 | — (59%) | — (59%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 94.0% (94/100) | 94.0% (94/100) | +0.0 | — (88%) | — (88%) |
| **G. Pipeline (rules + judge)** | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 91.0% (91/100) | 91.0% (91/100) | +0.0 | — (84%) | — (84%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 60.0% (60/100) | 60.0% (60/100) | +0.0 | — (50%) | — (50%) |
| G1r | Safe-pass after automatic quote repair | DJ | indicator | 93.0% (93/100) | 93.0% (93/100) | +0.0 | — (86%) | — (86%) |
| **H. Against gold (validation set)** | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 98.2% (442/450) | 98.2% (442/450) | +0.0 | ✅ (97%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| H2 | Identity values AND certainty correct | R | validated | 98.0% (441/450) | 98.0% (441/450) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| H3 | Medications found (name) | R | validated | 86.7% (65/75) | 92.0% (69/75) | +5.3 | — (77%) | — (84%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 78.7% (59/75) | 85.3% (64/75) | +6.7 | — (68%) | — (76%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | 96.9% (63/65) | 94.2% (65/69) | -2.7 | ✅ (89%) | — (86%) |
| H6 | Symptoms found | R | validated | 79.8% (103/129) | 79.8% (103/129) | +0.0 | — (72%) | — (72%) |
| H7 | Pertinent negatives found | R | validated | 82.2% (74/90) | 82.2% (74/90) | +0.0 | — (73%) | — (73%) |
| H8 | Vital signs found | R | validated | 86.1% (31/36) | 86.1% (31/36) | +0.0 | — (71%) | — (71%) |
| H9 | Nurse actions found (type) | R | validated | 88.1% (178/202) | 88.1% (178/202) | +0.0 | — (83%) | — (83%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 88.1% (178/202) | 88.1% (178/202) | +0.0 | — (83%) | — (83%) |
| H11 | Education items found (type) | R | validated | 82.4% (169/205) | 82.4% (169/205) | +0.0 | — (77%) | — (77%) |
| H12 | Gold risk flags found | R | validated | 78.4% (29/37) | 78.4% (29/37) | +0.0 | — (63%) | — (63%) |
| H13 | Output risk flags that are in gold | R | validated | 85.3% (29/34) | 85.3% (29/34) | +0.0 | — (70%) | — (70%) |
| H14 | Not-Applicable decision correct | R | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 86.2% (337/391) | 86.2% (337/391) | +0.0 | — (82%) | — (82%) |
| H16 | Response bullets covered | R | validated | 89.6% (180/201) | 89.6% (180/201) | +0.0 | — (85%) | — (85%) |
| H17 | Education bullets covered | R | validated | 84.4% (173/205) | 84.4% (173/205) | +0.0 | — (79%) | — (79%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 86.7% (65/75) | 84.1% (69/82) | -2.5 | — (77%) | — (75%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 82.3% (984/1196) | 82.5% (989/1199) | +0.2 | — (80%) | — (80%) |
| H19r | Gold critical facts found (no penalty for extra facts) | R | indicator | 90.9% (984/1083) | 91.3% (989/1083) | +0.5 | — (89%) | — (89%) |
| **O. Operational** | | | | | | | | |
| O2 | Outputs not cut off by the token limit | O | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |

**finetuned_epoch3_s3: 25 of 49 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (100.0%), A4 Quotes are in the cited turns (verbatim or repairable) (99.7%), A5 Quotes are exactly verbatim (99.7%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.7%), B2 Numbers are in the cited turns (+/-2) (99.0%), B3 Drug names appear in the call (99.5%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.8%), C1 Planned vs completed matches the nurse's words (100.0%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (97.9%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), E1 Calls with no rule ERROR (95.0%), E1r Calls with no rule ERROR after automatic quote repair (97.0%), F1 Faithful: nothing wrong or invented (96.0%), F2 Complete: checklist items covered (item level) (95.3%), H1 Identity values correct (5 fields) (98.2%), H2 Identity values AND certainty correct (98.0%), H5 Medication certainty (stated/unclear) correct (96.9%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)
**finetuned_epoch3_s3_net: 24 of 49 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (100.0%), A4 Quotes are in the cited turns (verbatim or repairable) (99.7%), A5 Quotes are exactly verbatim (99.7%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.7%), B2 Numbers are in the cited turns (+/-2) (99.0%), B3 Drug names appear in the call (99.5%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.8%), C1 Planned vs completed matches the nurse's words (100.0%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (97.9%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), E1 Calls with no rule ERROR (95.0%), E1r Calls with no rule ERROR after automatic quote repair (97.0%), F1 Faithful: nothing wrong or invented (96.0%), F2 Complete: checklist items covered (item level) (95.3%), H1 Identity values correct (5 fields) (98.2%), H2 Identity values AND certainty correct (98.0%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)

## Latency (seconds, calls timed one at a time)

| seconds | finetuned_epoch3_s3 | finetuned_epoch3_s3_net |
|---|---|---|
| Time to first token, p50 | not measured | not measured |
| Time to first token, p95 | not measured | not measured |
| Total response time, p50 | not measured | not measured |
| Total response time, p95 (target < 15 s) | not measured | not measured |
| Total response time, slowest | not measured | not measured |
| calls timed |  |  |

## Breakdown

**finetuned_epoch3_s3 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 100.0% | 91.7% | 80.3% |
| asr_error | 12 | 100.0% | 100.0% | 85.0% |
| high_risk | 20 | 95.0% | 90.0% | 76.1% |
| medication | 18 | 83.3% | 77.8% | 82.9% |
| not_applicable | 10 | 100.0% | 100.0% | 100.0% |
| routine | 16 | 100.0% | 93.8% | 84.6% |
| supply | 12 | 91.7% | 91.7% | 90.5% |

**finetuned_epoch3_s3 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 100.0% | 100.0% | 76.7% |
| medium | 11 | 100.0% | 100.0% | 82.3% |
| short | 73 | 93.2% | 87.7% | 84.1% |

**finetuned_epoch3_s3 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 100.0% | 100.0% | 82.7% |
| low | 75 | 93.3% | 89.3% | 82.4% |
| medium | 17 | 100.0% | 94.1% | 81.7% |

**finetuned_epoch3_s3_net by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 100.0% | 91.7% | 80.3% |
| asr_error | 12 | 100.0% | 100.0% | 84.5% |
| high_risk | 20 | 95.0% | 90.0% | 77.4% |
| medication | 18 | 83.3% | 77.8% | 82.6% |
| not_applicable | 10 | 100.0% | 100.0% | 100.0% |
| routine | 16 | 100.0% | 93.8% | 84.6% |
| supply | 12 | 91.7% | 91.7% | 90.5% |

**finetuned_epoch3_s3_net by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 100.0% | 100.0% | 77.9% |
| medium | 11 | 100.0% | 100.0% | 82.3% |
| short | 73 | 93.2% | 87.7% | 84.0% |

**finetuned_epoch3_s3_net by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 100.0% | 100.0% | 81.8% |
| low | 75 | 93.3% | 89.3% | 82.5% |
| medium | 17 | 100.0% | 94.1% | 82.6% |
