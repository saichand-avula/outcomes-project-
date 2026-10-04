# Evaluation matrix: base_v4_s2 vs finetuned_epoch1_s2

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | base_v4_s2 (rate, n/d) | finetuned_epoch1_s2 (rate, n/d) | Δ pts | ≥95% [base_v4_s2] (lower 95% bound) | ≥95% [finetuned_epoch1_s2] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 98.0% (98/100) | 97.0% (97/100) | -1.0 | ✅ (93%) | ✅ (92%) |
| A2 | Output matches the schema | D | validated | 98.0% (98/100) | 97.0% (97/100) | -1.0 | ✅ (93%) | ✅ (92%) |
| A3 | Cited turns exist | D | validated | 99.6% (1538/1544) | 100.0% (976/976) | +0.4 | ✅ (99%) lower bound ≥95 | ✅ (100%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 97.2% (1500/1544) | 98.9% (965/976) | +1.7 | ✅ (96%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 96.7% (1493/1544) | 98.0% (956/976) | +1.3 | ✅ (96%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.8% (1381/1384) | 99.5% (934/939) | -0.3 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 98.7% (461/467) | 98.5% (405/411) | -0.2 | ✅ (97%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 97.0% (453/467) | 96.6% (397/411) | -0.4 | ✅ (95%) lower bound ≥95 | ✅ (94%) |
| B3 | Drug names appear in the call | D | validated | 100.0% (281/281) | 99.5% (208/209) | -0.5 | ✅ (99%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (526/526) | 100.0% (439/439) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 99.5% (416/418) | 98.3% (403/410) | -1.2 | ✅ (98%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 99.6% (248/249) | 99.6% (222/223) | -0.0 | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 99.0% (204/206) | 100.0% (91/91) | +1.0 | ✅ (97%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 98.2% (549/559) | 98.4% (422/429) | +0.2 | ✅ (97%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (98/98) | 99.0% (96/97) | -1.0 | ✅ (96%) lower bound ≥95 | ✅ (94%) |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | 50.0% (5/10) | -50.0 | ✅ (72%) | — (24%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 59.0% (23/39) | 25.6% (10/39) | -33.3 | — (43%) | — (15%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 92.8% (90/97) | 77.2% (78/101) | -15.6 | — (86%) | — (68%) |
| **E. Whole call (rules)** | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 62.0% (62/100) | 74.0% (74/100) | +12.0 | — (52%) | — (65%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 29.0% (29/100) | 43.0% (43/100) | +14.0 | — (21%) | — (34%) |
| E1r | Calls with no rule ERROR after automatic quote repair | D | indicator | 80.0% (80/100) | 78.0% (78/100) | -2.0 | — (71%) | — (69%) |
| **F. Meaning (LLM judge)** | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 95.0% (95/100) | 85.0% (85/100) | -10.0 | ✅ (89%) | — (77%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 97.7% (873/894) | 95.3% (839/880) | -2.3 | ✅ (96%) lower bound ≥95 | ✅ (94%) |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 81.0% (81/100) | 65.0% (65/100) | -16.0 | — (72%) | — (55%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 85.0% (85/100) | 86.0% (86/100) | +1.0 | — (77%) | — (78%) |
| **G. Pipeline (rules + judge)** | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 60.0% (60/100) | 68.0% (68/100) | +8.0 | — (50%) | — (58%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 43.0% (43/100) | 45.0% (45/100) | +2.0 | — (34%) | — (36%) |
| G1r | Safe-pass after automatic quote repair | DJ | indicator | 78.0% (78/100) | 72.0% (72/100) | -6.0 | — (69%) | — (63%) |
| **H. Against gold (validation set)** | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 95.1% (428/450) | 93.6% (421/450) | -1.6 | ✅ (93%) | — (91%) |
| H2 | Identity values AND certainty correct | R | validated | 91.8% (413/450) | 92.4% (416/450) | +0.7 | — (89%) | — (90%) |
| H3 | Medications found (name) | R | validated | 93.3% (70/75) | 88.0% (66/75) | -5.3 | — (85%) | — (79%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 82.7% (62/75) | 74.7% (56/75) | -8.0 | — (73%) | — (64%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | 90.0% (63/70) | 95.5% (63/66) | +5.5 | — (81%) | ✅ (87%) |
| H6 | Symptoms found | R | validated | 75.2% (97/129) | 76.0% (98/129) | +0.8 | — (67%) | — (68%) |
| H7 | Pertinent negatives found | R | validated | 73.3% (66/90) | 74.4% (67/90) | +1.1 | — (63%) | — (65%) |
| H8 | Vital signs found | R | validated | 91.7% (33/36) | 88.9% (32/36) | -2.8 | — (78%) | — (75%) |
| H9 | Nurse actions found (type) | R | validated | 73.8% (149/202) | 82.2% (166/202) | +8.4 | — (67%) | — (76%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 72.8% (147/202) | 82.2% (166/202) | +9.4 | — (66%) | — (76%) |
| H11 | Education items found (type) | R | validated | 60.0% (123/205) | 70.7% (145/205) | +10.7 | — (53%) | — (64%) |
| H12 | Gold risk flags found | R | validated | 89.2% (33/37) | 54.1% (20/37) | -35.1 | — (75%) | — (38%) |
| H13 | Output risk flags that are in gold | R | validated | 27.0% (33/122) | 80.0% (20/25) | +53.0 | — (20%) | — (61%) |
| H14 | Not-Applicable decision correct | R | validated | 98.0% (98/100) | 96.0% (96/100) | -2.0 | ✅ (93%) | ✅ (90%) |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 86.4% (338/391) | 84.7% (331/391) | -1.8 | — (83%) | — (81%) |
| H16 | Response bullets covered | R | validated | 92.5% (186/201) | 86.1% (173/201) | -6.5 | — (88%) | — (81%) |
| H17 | Education bullets covered | R | validated | 69.3% (142/205) | 78.5% (161/205) | +9.3 | — (63%) | — (72%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 50.4% (70/139) | 81.5% (66/81) | +31.1 | — (42%) | — (72%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 56.8% (916/1613) | 73.3% (919/1254) | +16.5 | — (54%) | — (71%) |
| H19r | Gold critical facts found (no penalty for extra facts) | R | indicator | 84.6% (916/1083) | 84.9% (919/1083) | +0.3 | — (82%) | — (83%) |
| **O. Operational** | | | | | | | | |
| O1 | Latency p95 under 15 s (calls under 15 s) | O | validated | 10.0% (2/20) | 60.0% (12/20) | +50.0 | — (3%) | — (39%) |
| O2 | Outputs not cut off by the token limit | O | validated | 98.0% (98/100) | 97.0% (97/100) | -1.0 | ✅ (93%) | ✅ (92%) |

**base_v4_s2: 21 of 50 metrics reach ≥95%:** A1 Output is valid JSON (98.0%), A2 Output matches the schema (98.0%), A3 Cited turns exist (99.6%), A4 Quotes are in the cited turns (verbatim or repairable) (97.2%), A5 Quotes are exactly verbatim (96.7%), A6 Quote speaker matches the transcript label (99.8%), B1 Numbers in the summary were spoken in the call (98.7%), B2 Numbers are in the cited turns (+/-2) (97.0%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (99.6%), C2 Negative findings are not stated as present (99.0%), C3 Caller hedges are kept (98.2%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (95.0%), F2 Complete: checklist items covered (item level) (97.7%), H1 Identity values correct (5 fields) (95.1%), H14 Not-Applicable decision correct (98.0%), O2 Outputs not cut off by the token limit (98.0%)
**finetuned_epoch1_s2: 19 of 50 metrics reach ≥95%:** A1 Output is valid JSON (97.0%), A2 Output matches the schema (97.0%), A3 Cited turns exist (100.0%), A4 Quotes are in the cited turns (verbatim or repairable) (98.9%), A5 Quotes are exactly verbatim (98.0%), A6 Quote speaker matches the transcript label (99.5%), B1 Numbers in the summary were spoken in the call (98.5%), B2 Numbers are in the cited turns (+/-2) (96.6%), B3 Drug names appear in the call (99.5%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (98.3%), C1 Planned vs completed matches the nurse's words (99.6%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (98.4%), D1 Not-Applicable decision agrees with the clinical-content gate (99.0%), F2 Complete: checklist items covered (item level) (95.3%), H5 Medication certainty (stated/unclear) correct (95.5%), H14 Not-Applicable decision correct (96.0%), O2 Outputs not cut off by the token limit (97.0%)

## Latency (seconds, calls timed one at a time)

| seconds | base_v4_s2 | finetuned_epoch1_s2 |
|---|---|---|
| Time to first token, p50 | 0.16 | 0.18 |
| Time to first token, p95 | 0.62 | 0.64 |
| Total response time, p50 | 27.96 | 13.58 |
| Total response time, p95 (target < 15 s) | 69.88 | 19.50 |
| Total response time, slowest | 70.39 | 94.84 |
| calls timed | 20 | 20 |

## Breakdown

**base_v4_s2 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 58.3% | 50.0% | 52.0% |
| asr_error | 12 | 58.3% | 58.3% | 53.2% |
| high_risk | 20 | 70.0% | 65.0% | 55.1% |
| medication | 18 | 72.2% | 72.2% | 60.1% |
| not_applicable | 10 | 20.0% | 20.0% | 100.0% |
| routine | 16 | 50.0% | 50.0% | 59.1% |
| supply | 12 | 91.7% | 91.7% | 59.3% |

**base_v4_s2 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 62.5% | 62.5% | 54.3% |
| medium | 11 | 63.6% | 63.6% | 51.4% |
| short | 73 | 61.6% | 58.9% | 58.8% |

**base_v4_s2 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 62.5% | 62.5% | 52.6% |
| low | 75 | 64.0% | 61.3% | 58.0% |
| medium | 17 | 52.9% | 52.9% | 53.9% |

**finetuned_epoch1_s2 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 66.7% | 58.3% | 72.9% |
| asr_error | 12 | 83.3% | 75.0% | 76.3% |
| high_risk | 20 | 60.0% | 60.0% | 69.1% |
| medication | 18 | 55.6% | 50.0% | 67.0% |
| not_applicable | 10 | 100.0% | 100.0% | 100.0% |
| routine | 16 | 81.2% | 75.0% | 77.3% |
| supply | 12 | 91.7% | 75.0% | 84.8% |

**finetuned_epoch1_s2 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 75.0% | 56.2% | 73.4% |
| medium | 11 | 72.7% | 72.7% | 75.3% |
| short | 73 | 74.0% | 69.9% | 72.9% |

**finetuned_epoch1_s2 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 87.5% | 87.5% | 77.2% |
| low | 75 | 70.7% | 64.0% | 72.6% |
| medium | 17 | 82.4% | 76.5% | 74.2% |
