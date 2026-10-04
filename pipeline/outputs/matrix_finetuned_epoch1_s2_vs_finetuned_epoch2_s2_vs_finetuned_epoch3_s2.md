# Evaluation matrix: finetuned_epoch1_s2 vs finetuned_epoch2_s2 vs finetuned_epoch3_s2

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | finetuned_epoch1_s2 (rate, n/d) | finetuned_epoch2_s2 (rate, n/d) | finetuned_epoch3_s2 (rate, n/d) | ≥95% [finetuned_epoch1_s2] (lower 95% bound) | ≥95% [finetuned_epoch2_s2] (lower 95% bound) | ≥95% [finetuned_epoch3_s2] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 97.0% (97/100) | 100.0% (100/100) | 100.0% (100/100) | ✅ (92%) | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A2 | Output matches the schema | D | validated | 97.0% (97/100) | 100.0% (100/100) | 100.0% (100/100) | ✅ (92%) | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A3 | Cited turns exist | D | validated | 100.0% (976/976) | 100.0% (865/865) | 100.0% (939/939) | ✅ (100%) lower bound ≥95 | ✅ (100%) lower bound ≥95 | ✅ (100%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 98.9% (965/976) | 99.3% (859/865) | 99.7% (936/939) | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 98.0% (956/976) | 99.2% (858/865) | 99.7% (936/939) | ✅ (97%) lower bound ≥95 | ✅ (98%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.5% (934/939) | 99.9% (825/826) | 99.9% (902/903) | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 98.5% (405/411) | 100.0% (387/387) | 99.7% (384/385) | ✅ (97%) lower bound ≥95 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 96.6% (397/411) | 100.0% (387/387) | 99.0% (381/385) | ✅ (94%) | ✅ (99%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B3 | Drug names appear in the call | D | validated | 99.5% (208/209) | 99.5% (186/187) | 99.5% (192/193) | ✅ (97%) lower bound ≥95 | ✅ (97%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (439/439) | 100.0% (405/405) | 100.0% (443/443) | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 98.3% (403/410) | 99.8% (422/423) | 99.8% (426/427) | ✅ (97%) lower bound ≥95 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 99.6% (222/223) | 100.0% (191/191) | 99.5% (213/214) | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 100.0% (91/91) | 100.0% (78/78) | 100.0% (87/87) | ✅ (96%) lower bound ≥95 | ✅ (95%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 98.4% (422/429) | 98.3% (356/362) | 97.7% (384/393) | ✅ (97%) lower bound ≥95 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 99.0% (96/97) | 99.0% (99/100) | 100.0% (100/100) | ✅ (94%) | ✅ (95%) | ✅ (96%) lower bound ≥95 |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 50.0% (5/10) | 100.0% (10/10) | 100.0% (10/10) | — (24%) | ✅ (72%) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 25.6% (10/39) | 40.0% (16/40) | 35.0% (14/40) | — (15%) | — (26%) | — (22%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 77.2% (78/101) | 68.0% (70/103) | 72.8% (75/103) | — (68%) | — (58%) | — (64%) |
| **E. Whole call (rules)** | | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 74.0% (74/100) | 93.0% (93/100) | 94.0% (94/100) | — (65%) | — (86%) | — (88%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 43.0% (43/100) | 53.0% (53/100) | 51.0% (51/100) | — (34%) | — (43%) | — (41%) |
| E1r | Calls with no rule ERROR after automatic quote repair | D | indicator | 78.0% (78/100) | 94.0% (94/100) | 96.0% (96/100) | — (69%) | — (88%) | ✅ (90%) |
| **F. Meaning (LLM judge)** | | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 85.0% (85/100) | 98.0% (98/100) | 97.0% (97/100) | — (77%) | ✅ (93%) | ✅ (92%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 95.3% (839/880) | 92.1% (833/904) | 95.4% (868/910) | ✅ (94%) | — (90%) | ✅ (94%) |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 65.0% (65/100) | 57.0% (57/100) | 68.0% (68/100) | — (55%) | — (47%) | — (58%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 86.0% (86/100) | 96.0% (96/100) | 95.0% (95/100) | — (78%) | ✅ (90%) | ✅ (89%) |
| **G. Pipeline (rules + judge)** | | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 68.0% (68/100) | 91.0% (91/100) | 92.0% (92/100) | — (58%) | — (84%) | — (85%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 45.0% (45/100) | 51.0% (51/100) | 61.0% (61/100) | — (36%) | — (41%) | — (51%) |
| G1r | Safe-pass after automatic quote repair | DJ | indicator | 72.0% (72/100) | 92.0% (92/100) | 94.0% (94/100) | — (63%) | — (85%) | — (88%) |
| **H. Against gold (validation set)** | | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 93.6% (421/450) | 97.6% (439/450) | 98.2% (442/450) | — (91%) | ✅ (96%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| H2 | Identity values AND certainty correct | R | validated | 92.4% (416/450) | 96.9% (436/450) | 98.0% (441/450) | — (90%) | ✅ (95%) | ✅ (96%) lower bound ≥95 |
| H3 | Medications found (name) | R | validated | 88.0% (66/75) | 82.7% (62/75) | 89.3% (67/75) | — (79%) | — (73%) | — (80%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 74.7% (56/75) | 69.3% (52/75) | 74.7% (56/75) | — (64%) | — (58%) | — (64%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | 95.5% (63/66) | 91.9% (57/62) | 94.0% (63/67) | ✅ (87%) | — (82%) | — (86%) |
| H6 | Symptoms found | R | validated | 76.0% (98/129) | 79.1% (102/129) | 79.8% (103/129) | — (68%) | — (71%) | — (72%) |
| H7 | Pertinent negatives found | R | validated | 74.4% (67/90) | 71.1% (64/90) | 81.1% (73/90) | — (65%) | — (61%) | — (72%) |
| H8 | Vital signs found | R | validated | 88.9% (32/36) | 86.1% (31/36) | 83.3% (30/36) | — (75%) | — (71%) | — (68%) |
| H9 | Nurse actions found (type) | R | validated | 82.2% (166/202) | 86.1% (174/202) | 87.6% (177/202) | — (76%) | — (81%) | — (82%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 82.2% (166/202) | 85.6% (173/202) | 87.1% (176/202) | — (76%) | — (80%) | — (82%) |
| H11 | Education items found (type) | R | validated | 70.7% (145/205) | 79.0% (162/205) | 83.9% (172/205) | — (64%) | — (73%) | — (78%) |
| H12 | Gold risk flags found | R | validated | 54.1% (20/37) | 81.1% (30/37) | 78.4% (29/37) | — (38%) | — (66%) | — (63%) |
| H13 | Output risk flags that are in gold | R | validated | 80.0% (20/25) | 90.9% (30/33) | 87.9% (29/33) | — (61%) | — (76%) | — (73%) |
| H14 | Not-Applicable decision correct | R | validated | 96.0% (96/100) | 99.0% (99/100) | 100.0% (100/100) | ✅ (90%) | ✅ (95%) | ✅ (96%) lower bound ≥95 |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 84.7% (331/391) | 81.3% (318/391) | 86.7% (339/391) | — (81%) | — (77%) | — (83%) |
| H16 | Response bullets covered | R | validated | 86.1% (173/201) | 87.1% (175/201) | 89.6% (180/201) | — (81%) | — (82%) | — (85%) |
| H17 | Education bullets covered | R | validated | 78.5% (161/205) | 80.5% (165/205) | 83.4% (171/205) | — (72%) | — (75%) | — (78%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 81.5% (66/81) | 89.9% (62/69) | 90.5% (67/74) | — (72%) | — (81%) | — (82%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 73.3% (919/1254) | 81.4% (956/1174) | 81.6% (978/1198) | — (71%) | — (79%) | — (79%) |
| H19r | Gold critical facts found (no penalty for extra facts) | R | indicator | 84.9% (919/1083) | 88.3% (956/1083) | 90.3% (978/1083) | — (83%) | — (86%) | — (88%) |
| **O. Operational** | | | | | | | | | |
| O1 | Latency p95 under 15 s (calls under 15 s) | O | validated | 60.0% (12/20) | n/a | 65.0% (13/20) | — (39%) |  | — (43%) |
| O2 | Outputs not cut off by the token limit | O | validated | 97.0% (97/100) | 100.0% (100/100) | 100.0% (100/100) | ✅ (92%) | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |

**finetuned_epoch1_s2: 19 of 50 metrics reach ≥95%:** A1 Output is valid JSON (97.0%), A2 Output matches the schema (97.0%), A3 Cited turns exist (100.0%), A4 Quotes are in the cited turns (verbatim or repairable) (98.9%), A5 Quotes are exactly verbatim (98.0%), A6 Quote speaker matches the transcript label (99.5%), B1 Numbers in the summary were spoken in the call (98.5%), B2 Numbers are in the cited turns (+/-2) (96.6%), B3 Drug names appear in the call (99.5%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (98.3%), C1 Planned vs completed matches the nurse's words (99.6%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (98.4%), D1 Not-Applicable decision agrees with the clinical-content gate (99.0%), F2 Complete: checklist items covered (item level) (95.3%), H5 Medication certainty (stated/unclear) correct (95.5%), H14 Not-Applicable decision correct (96.0%), O2 Outputs not cut off by the token limit (97.0%)
**finetuned_epoch2_s2: 22 of 49 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (100.0%), A4 Quotes are in the cited turns (verbatim or repairable) (99.3%), A5 Quotes are exactly verbatim (99.2%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (100.0%), B2 Numbers are in the cited turns (+/-2) (100.0%), B3 Drug names appear in the call (99.5%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.8%), C1 Planned vs completed matches the nurse's words (100.0%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (98.3%), D1 Not-Applicable decision agrees with the clinical-content gate (99.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (98.0%), F4 Calibrated: hedges, planned vs done, speaker (indicator) (96.0%), H1 Identity values correct (5 fields) (97.6%), H2 Identity values AND certainty correct (96.9%), H14 Not-Applicable decision correct (99.0%), O2 Outputs not cut off by the token limit (100.0%)
**finetuned_epoch3_s2: 24 of 50 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (100.0%), A4 Quotes are in the cited turns (verbatim or repairable) (99.7%), A5 Quotes are exactly verbatim (99.7%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.7%), B2 Numbers are in the cited turns (+/-2) (99.0%), B3 Drug names appear in the call (99.5%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.8%), C1 Planned vs completed matches the nurse's words (99.5%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (97.7%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), E1r Calls with no rule ERROR after automatic quote repair (96.0%), F1 Faithful: nothing wrong or invented (97.0%), F2 Complete: checklist items covered (item level) (95.4%), F4 Calibrated: hedges, planned vs done, speaker (indicator) (95.0%), H1 Identity values correct (5 fields) (98.2%), H2 Identity values AND certainty correct (98.0%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)

## Latency (seconds, calls timed one at a time)

| seconds | finetuned_epoch1_s2 | finetuned_epoch2_s2 | finetuned_epoch3_s2 |
|---|---|---|---|
| Time to first token, p50 | 0.18 | not measured | 0.17 |
| Time to first token, p95 | 0.64 | not measured | 0.64 |
| Total response time, p50 | 13.58 | not measured | 14.02 |
| Total response time, p95 (target < 15 s) | 19.50 | not measured | 19.11 |
| Total response time, slowest | 94.84 | not measured | 20.84 |
| calls timed | 20 |  | 20 |

## Breakdown

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

**finetuned_epoch2_s2 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 100.0% | 100.0% | 78.4% |
| asr_error | 12 | 100.0% | 91.7% | 82.9% |
| high_risk | 20 | 85.0% | 80.0% | 77.9% |
| medication | 18 | 83.3% | 83.3% | 82.2% |
| not_applicable | 10 | 100.0% | 100.0% | 100.0% |
| routine | 16 | 93.8% | 93.8% | 86.0% |
| supply | 12 | 100.0% | 100.0% | 82.3% |

**finetuned_epoch2_s2 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 93.8% | 93.8% | 75.9% |
| medium | 11 | 100.0% | 100.0% | 77.9% |
| short | 73 | 91.8% | 89.0% | 83.9% |

**finetuned_epoch2_s2 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 100.0% | 100.0% | 80.4% |
| low | 75 | 90.7% | 89.3% | 81.3% |
| medium | 17 | 100.0% | 94.1% | 82.5% |

**finetuned_epoch3_s2 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 100.0% | 100.0% | 80.8% |
| asr_error | 12 | 100.0% | 100.0% | 83.8% |
| high_risk | 20 | 95.0% | 90.0% | 75.4% |
| medication | 18 | 83.3% | 77.8% | 82.0% |
| not_applicable | 10 | 100.0% | 100.0% | 100.0% |
| routine | 16 | 93.8% | 93.8% | 85.5% |
| supply | 12 | 91.7% | 91.7% | 87.6% |

**finetuned_epoch3_s2 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 100.0% | 100.0% | 75.6% |
| medium | 11 | 100.0% | 100.0% | 82.3% |
| short | 73 | 91.8% | 89.0% | 83.5% |

**finetuned_epoch3_s2 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 100.0% | 100.0% | 83.5% |
| low | 75 | 92.0% | 90.7% | 81.1% |
| medium | 17 | 100.0% | 94.1% | 83.2% |
