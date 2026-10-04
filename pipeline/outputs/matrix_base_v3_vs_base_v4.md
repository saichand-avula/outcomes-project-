# Evaluation matrix: base_v3 vs base_v4

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | base_v3 (rate, n/d) | base_v4 (rate, n/d) | Δ pts | ≥95% [base_v3] (lower 95% bound) | ≥95% [base_v4] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A2 | Output matches the schema | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A3 | Cited turns exist | D | validated | 99.7% (1562/1566) | 99.7% (1537/1542) | -0.1 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 97.1% (1520/1566) | 97.5% (1504/1542) | +0.5 | ✅ (96%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 96.6% (1513/1566) | 96.9% (1494/1542) | +0.3 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.9% (1394/1396) | 99.9% (1380/1382) | -0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 99.3% (450/453) | 97.9% (468/478) | -1.4 | ✅ (98%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 97.6% (442/453) | 96.7% (462/478) | -0.9 | ✅ (96%) lower bound ≥95 | ✅ (95%) |
| B3 | Drug names appear in the call | D | validated | 100.0% (325/325) | 100.0% (354/354) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (527/527) | 100.0% (538/538) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 99.5% (425/427) | 99.5% (425/427) | +0.0 | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 99.3% (281/283) | 99.6% (280/281) | +0.4 | ✅ (97%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 99.6% (223/224) | 99.5% (209/210) | -0.0 | ✅ (98%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 97.6% (560/574) | 97.5% (551/565) | -0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | 100.0% (10/10) | +0.0 | ✅ (72%) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 62.5% (25/40) | 60.0% (24/40) | -2.5 | — (47%) | — (45%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 87.4% (90/103) | 88.3% (91/103) | +1.0 | — (80%) | — (81%) |
| **E. Whole call (rules)** | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 67.0% (67/100) | 70.0% (70/100) | +3.0 | — (57%) | — (60%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 33.0% (33/100) | 37.0% (37/100) | +4.0 | — (25%) | — (28%) |
| E1r | Calls with no rule ERROR after automatic quote repair | D | indicator | 86.0% (86/100) | 83.0% (83/100) | -3.0 | — (78%) | — (74%) |
| **F. Meaning (LLM judge)** | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 98.0% (98/100) | 98.0% (98/100) | +0.0 | ✅ (93%) | ✅ (93%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 97.7% (889/910) | 96.7% (880/910) | -1.0 | ✅ (96%) lower bound ≥95 | ✅ (95%) lower bound ≥95 |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 83.0% (83/100) | 80.0% (80/100) | -3.0 | — (74%) | — (71%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 86.0% (86/100) | 85.0% (85/100) | -1.0 | — (78%) | — (77%) |
| **G. Pipeline (rules + judge)** | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 65.0% (65/100) | 70.0% (70/100) | +5.0 | — (55%) | — (60%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 48.0% (48/100) | 47.0% (47/100) | -1.0 | — (38%) | — (38%) |
| G1r | Safe-pass after automatic quote repair | DJ | indicator | 84.0% (84/100) | 82.0% (82/100) | -2.0 | — (76%) | — (73%) |
| **H. Against gold (validation set)** | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 84.2% (379/450) | 97.3% (438/450) | +13.1 | — (81%) | ✅ (95%) lower bound ≥95 |
| H2 | Identity values AND certainty correct | R | validated | 80.4% (362/450) | 94.0% (423/450) | +13.6 | — (77%) | — (91%) |
| H3 | Medications found (name) | R | validated | 94.7% (71/75) | 93.3% (70/75) | -1.3 | — (87%) | — (85%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 84.0% (63/75) | 78.7% (59/75) | -5.3 | — (74%) | — (68%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | 88.7% (63/71) | 90.0% (63/70) | +1.3 | — (79%) | — (81%) |
| H6 | Symptoms found | R | validated | 77.5% (100/129) | 77.5% (100/129) | +0.0 | — (70%) | — (70%) |
| H7 | Pertinent negatives found | R | validated | 80.0% (72/90) | 77.8% (70/90) | -2.2 | — (71%) | — (68%) |
| H8 | Vital signs found | R | validated | 100.0% (36/36) | 100.0% (36/36) | +0.0 | ✅ (90%) | ✅ (90%) |
| H9 | Nurse actions found (type) | R | validated | 79.7% (161/202) | 78.2% (158/202) | -1.5 | — (74%) | — (72%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 78.7% (159/202) | 77.7% (157/202) | -1.0 | — (73%) | — (71%) |
| H11 | Education items found (type) | R | validated | 63.4% (130/205) | 57.6% (118/205) | -5.9 | — (57%) | — (51%) |
| H12 | Gold risk flags found | R | validated | 91.9% (34/37) | 89.2% (33/37) | -2.7 | — (79%) | — (75%) |
| H13 | Output risk flags that are in gold | R | validated | 26.6% (34/128) | 27.0% (33/122) | +0.5 | — (20%) | — (20%) |
| H14 | Not-Applicable decision correct | R | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 87.5% (342/391) | 87.5% (342/391) | +0.0 | — (84%) | — (84%) |
| H16 | Response bullets covered | R | validated | 93.0% (187/201) | 92.5% (186/201) | -0.5 | — (89%) | — (88%) |
| H17 | Education bullets covered | R | validated | 68.8% (141/205) | 68.8% (141/205) | +0.0 | — (62%) | — (62%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 53.4% (71/133) | 47.3% (70/148) | -6.1 | — (45%) | — (39%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 51.3% (890/1735) | 56.9% (942/1656) | +5.6 | — (49%) | — (54%) |
| H19r | Gold critical facts found (no penalty for extra facts) | R | indicator | 82.2% (890/1083) | 87.0% (942/1083) | +4.8 | — (80%) | — (85%) |
| **O. Operational** | | | | | | | | |
| O2 | Outputs not cut off by the token limit | O | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |

**base_v3: 21 of 49 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (99.7%), A4 Quotes are in the cited turns (verbatim or repairable) (97.1%), A5 Quotes are exactly verbatim (96.6%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.3%), B2 Numbers are in the cited turns (+/-2) (97.6%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (99.3%), C2 Negative findings are not stated as present (99.6%), C3 Caller hedges are kept (97.6%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (98.0%), F2 Complete: checklist items covered (item level) (97.7%), H8 Vital signs found (100.0%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)
**base_v4: 22 of 49 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (99.7%), A4 Quotes are in the cited turns (verbatim or repairable) (97.5%), A5 Quotes are exactly verbatim (96.9%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (97.9%), B2 Numbers are in the cited turns (+/-2) (96.7%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (99.6%), C2 Negative findings are not stated as present (99.5%), C3 Caller hedges are kept (97.5%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (98.0%), F2 Complete: checklist items covered (item level) (96.7%), H1 Identity values correct (5 fields) (97.3%), H8 Vital signs found (100.0%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)

## Breakdown

**base_v3 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 58.3% | 58.3% | 46.5% |
| asr_error | 12 | 75.0% | 75.0% | 48.4% |
| high_risk | 20 | 75.0% | 70.0% | 49.6% |
| medication | 18 | 72.2% | 72.2% | 55.0% |
| not_applicable | 10 | 50.0% | 50.0% | 100.0% |
| routine | 16 | 56.2% | 56.2% | 55.2% |
| supply | 12 | 75.0% | 66.7% | 50.0% |

**base_v3 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 62.5% | 56.2% | 49.7% |
| medium | 11 | 72.7% | 72.7% | 45.9% |
| short | 73 | 67.1% | 65.8% | 52.9% |

**base_v3 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 87.5% | 87.5% | 49.7% |
| low | 75 | 66.7% | 64.0% | 51.5% |
| medium | 17 | 58.8% | 58.8% | 51.3% |

**base_v4 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 75.0% | 75.0% | 54.2% |
| asr_error | 12 | 66.7% | 66.7% | 54.8% |
| high_risk | 20 | 75.0% | 75.0% | 54.5% |
| medication | 18 | 83.3% | 83.3% | 59.1% |
| not_applicable | 10 | 40.0% | 40.0% | 100.0% |
| routine | 16 | 62.5% | 62.5% | 60.4% |
| supply | 12 | 75.0% | 75.0% | 56.8% |

**base_v4 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 56.2% | 56.2% | 53.0% |
| medium | 11 | 72.7% | 72.7% | 51.6% |
| short | 73 | 72.6% | 72.6% | 59.3% |

**base_v4 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 62.5% | 62.5% | 53.3% |
| low | 75 | 69.3% | 69.3% | 57.9% |
| medium | 17 | 76.5% | 76.5% | 54.4% |
