# Evaluation matrix: base_v4_s3 vs finetuned_epoch3_s3

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | base_v4_s3 (rate, n/d) | finetuned_epoch3_s3 (rate, n/d) | Δ pts | ≥95% [base_v4_s3] (lower 95% bound) | ≥95% [finetuned_epoch3_s3] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A2 | Output matches the schema | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A3 | Cited turns exist | D | validated | 99.6% (1556/1562) | 100.0% (933/933) | +0.4 | ✅ (99%) lower bound ≥95 | ✅ (100%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 97.1% (1516/1562) | 99.7% (930/933) | +2.6 | ✅ (96%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 96.7% (1511/1562) | 99.7% (930/933) | +2.9 | ✅ (96%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.9% (1400/1402) | 99.9% (895/896) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 99.2% (480/484) | 99.7% (392/393) | +0.6 | ✅ (98%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 97.9% (474/484) | 99.0% (389/393) | +1.0 | ✅ (96%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B3 | Drug names appear in the call | D | validated | 100.0% (325/325) | 99.5% (197/198) | -0.5 | ✅ (99%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 99.8% (531/532) | 100.0% (445/445) | +0.2 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 99.5% (425/427) | 99.8% (426/427) | +0.2 | ✅ (98%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 99.3% (271/273) | 100.0% (212/212) | +0.7 | ✅ (97%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 99.0% (201/203) | 100.0% (86/86) | +1.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 98.6% (556/564) | 97.9% (382/390) | -0.6 | ✅ (97%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | 100.0% (10/10) | +0.0 | ✅ (72%) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 60.0% (24/40) | 37.5% (15/40) | -22.5 | — (45%) | — (24%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 90.3% (93/103) | 75.7% (78/103) | -14.6 | — (83%) | — (67%) |
| **E. Whole call (rules)** | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 65.0% (65/100) | 95.0% (95/100) | +30.0 | — (55%) | ✅ (89%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 35.0% (35/100) | 53.0% (53/100) | +18.0 | — (26%) | — (43%) |
| E1r | Calls with no rule ERROR after automatic quote repair | D | indicator | 83.0% (83/100) | 97.0% (97/100) | +14.0 | — (74%) | ✅ (92%) |
| **F. Meaning (LLM judge)** | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 100.0% (100/100) | 96.0% (96/100) | -4.0 | ✅ (96%) lower bound ≥95 | ✅ (90%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 97.3% (885/910) | 95.3% (867/910) | -2.0 | ✅ (96%) lower bound ≥95 | ✅ (94%) |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 84.0% (84/100) | 69.0% (69/100) | -15.0 | — (76%) | — (59%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 91.0% (91/100) | 94.0% (94/100) | +3.0 | — (84%) | — (88%) |
| **G. Pipeline (rules + judge)** | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 65.0% (65/100) | 91.0% (91/100) | +26.0 | — (55%) | — (84%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 50.0% (50/100) | 60.0% (60/100) | +10.0 | — (40%) | — (50%) |
| G1r | Safe-pass after automatic quote repair | DJ | indicator | 83.0% (83/100) | 93.0% (93/100) | +10.0 | — (74%) | — (86%) |
| **H. Against gold (validation set)** | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 97.3% (438/450) | 98.2% (442/450) | +0.9 | ✅ (95%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| H2 | Identity values AND certainty correct | R | validated | 93.8% (422/450) | 98.0% (441/450) | +4.2 | — (91%) | ✅ (96%) lower bound ≥95 |
| H3 | Medications found (name) | R | validated | 94.7% (71/75) | 86.7% (65/75) | -8.0 | — (87%) | — (77%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 84.0% (63/75) | 78.7% (59/75) | -5.3 | — (74%) | — (68%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | 88.7% (63/71) | 96.9% (63/65) | +8.2 | — (79%) | ✅ (89%) |
| H6 | Symptoms found | R | validated | 74.4% (96/129) | 79.8% (103/129) | +5.4 | — (66%) | — (72%) |
| H7 | Pertinent negatives found | R | validated | 76.7% (69/90) | 82.2% (74/90) | +5.6 | — (67%) | — (73%) |
| H8 | Vital signs found | R | validated | 94.4% (34/36) | 86.1% (31/36) | -8.3 | — (82%) | — (71%) |
| H9 | Nurse actions found (type) | R | validated | 78.7% (159/202) | 88.1% (178/202) | +9.4 | — (73%) | — (83%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 77.2% (156/202) | 88.1% (178/202) | +10.9 | — (71%) | — (83%) |
| H11 | Education items found (type) | R | validated | 62.4% (128/205) | 82.4% (169/205) | +20.0 | — (56%) | — (77%) |
| H12 | Gold risk flags found | R | validated | 89.2% (33/37) | 78.4% (29/37) | -10.8 | — (75%) | — (63%) |
| H13 | Output risk flags that are in gold | R | validated | 27.7% (33/119) | 85.3% (29/34) | +57.6 | — (20%) | — (70%) |
| H14 | Not-Applicable decision correct | R | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 87.5% (342/391) | 86.2% (337/391) | -1.3 | — (84%) | — (82%) |
| H16 | Response bullets covered | R | validated | 95.0% (191/201) | 89.6% (180/201) | -5.5 | ✅ (91%) | — (85%) |
| H17 | Education bullets covered | R | validated | 68.8% (141/205) | 84.4% (173/205) | +15.6 | — (62%) | — (79%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 51.1% (71/139) | 86.7% (65/75) | +35.6 | — (43%) | — (77%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 57.6% (939/1631) | 82.3% (984/1196) | +24.7 | — (55%) | — (80%) |
| H19r | Gold critical facts found (no penalty for extra facts) | R | indicator | 86.7% (939/1083) | 90.9% (984/1083) | +4.2 | — (85%) | — (89%) |
| **O. Operational** | | | | | | | | |
| O2 | Outputs not cut off by the token limit | O | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |

**base_v4_s3: 22 of 49 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (99.6%), A4 Quotes are in the cited turns (verbatim or repairable) (97.1%), A5 Quotes are exactly verbatim (96.7%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.2%), B2 Numbers are in the cited turns (+/-2) (97.9%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (99.8%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (99.3%), C2 Negative findings are not stated as present (99.0%), C3 Caller hedges are kept (98.6%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (100.0%), F2 Complete: checklist items covered (item level) (97.3%), H1 Identity values correct (5 fields) (97.3%), H14 Not-Applicable decision correct (100.0%), H16 Response bullets covered (95.0%), O2 Outputs not cut off by the token limit (100.0%)
**finetuned_epoch3_s3: 25 of 49 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (100.0%), A4 Quotes are in the cited turns (verbatim or repairable) (99.7%), A5 Quotes are exactly verbatim (99.7%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.7%), B2 Numbers are in the cited turns (+/-2) (99.0%), B3 Drug names appear in the call (99.5%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.8%), C1 Planned vs completed matches the nurse's words (100.0%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (97.9%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), E1 Calls with no rule ERROR (95.0%), E1r Calls with no rule ERROR after automatic quote repair (97.0%), F1 Faithful: nothing wrong or invented (96.0%), F2 Complete: checklist items covered (item level) (95.3%), H1 Identity values correct (5 fields) (98.2%), H2 Identity values AND certainty correct (98.0%), H5 Medication certainty (stated/unclear) correct (96.9%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)

## Latency (seconds, calls timed one at a time)

| seconds | base_v4_s3 | finetuned_epoch3_s3 |
|---|---|---|
| Time to first token, p50 | not measured | not measured |
| Time to first token, p95 | not measured | not measured |
| Total response time, p50 | not measured | not measured |
| Total response time, p95 (target < 15 s) | not measured | not measured |
| Total response time, slowest | not measured | not measured |
| calls timed |  |  |

## Breakdown

**base_v4_s3 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 58.3% | 58.3% | 54.6% |
| asr_error | 12 | 58.3% | 58.3% | 52.1% |
| high_risk | 20 | 80.0% | 80.0% | 55.6% |
| medication | 18 | 66.7% | 66.7% | 61.7% |
| not_applicable | 10 | 20.0% | 20.0% | 100.0% |
| routine | 16 | 56.2% | 56.2% | 61.2% |
| supply | 12 | 100.0% | 100.0% | 57.6% |

**base_v4_s3 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 56.2% | 56.2% | 54.6% |
| medium | 11 | 72.7% | 72.7% | 50.2% |
| short | 73 | 65.8% | 65.8% | 60.1% |

**base_v4_s3 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 62.5% | 62.5% | 52.2% |
| low | 75 | 66.7% | 66.7% | 59.0% |
| medium | 17 | 58.8% | 58.8% | 54.4% |

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
