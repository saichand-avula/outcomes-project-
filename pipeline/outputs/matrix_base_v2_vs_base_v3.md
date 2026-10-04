# Evaluation matrix: base_v2 vs base_v3

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | base_v2 (rate, n/d) | base_v3 (rate, n/d) | Δ pts | ≥95% [base_v2] (lower 95% bound) | ≥95% [base_v3] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A2 | Output matches the schema | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A3 | Cited turns exist | D | validated | 99.7% (1562/1567) | 99.7% (1562/1566) | +0.1 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 96.8% (1517/1567) | 97.1% (1520/1566) | +0.3 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 96.2% (1508/1567) | 96.6% (1513/1566) | +0.4 | ✅ (95%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.9% (1387/1389) | 99.9% (1394/1396) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 99.4% (485/488) | 99.3% (450/453) | -0.0 | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 97.3% (475/488) | 97.6% (442/453) | +0.2 | ✅ (95%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| B3 | Drug names appear in the call | D | validated | 100.0% (375/375) | 100.0% (325/325) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (514/514) | 100.0% (527/527) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 99.5% (420/422) | 99.5% (425/427) | +0.0 | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 98.9% (282/285) | 99.3% (281/283) | +0.3 | ✅ (97%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 99.5% (217/218) | 99.6% (223/224) | +0.0 | ✅ (97%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 98.1% (567/578) | 97.6% (560/574) | -0.5 | ✅ (97%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | 100.0% (10/10) | +0.0 | ✅ (72%) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 60.0% (24/40) | 62.5% (25/40) | +2.5 | — (45%) | — (47%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 92.2% (95/103) | 87.4% (90/103) | -4.9 | — (85%) | — (80%) |
| **E. Whole call (rules)** | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 63.0% (63/100) | 67.0% (67/100) | +4.0 | — (53%) | — (57%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 35.0% (35/100) | 33.0% (33/100) | -2.0 | — (26%) | — (25%) |
| **F. Meaning (LLM judge)** | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 95.0% (95/100) | 98.0% (98/100) | +3.0 | ✅ (89%) | ✅ (93%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 96.9% (882/910) | 97.7% (889/910) | +0.8 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 79.0% (79/100) | 83.0% (83/100) | +4.0 | — (70%) | — (74%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 89.0% (89/100) | 86.0% (86/100) | -3.0 | — (81%) | — (78%) |
| **G. Pipeline (rules + judge)** | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 59.0% (59/100) | 65.0% (65/100) | +6.0 | — (49%) | — (55%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 41.0% (41/100) | 48.0% (48/100) | +7.0 | — (32%) | — (38%) |
| **H. Against gold (validation set)** | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 84.7% (381/450) | 84.2% (379/450) | -0.4 | — (81%) | — (81%) |
| H2 | Identity values AND certainty correct | R | validated | 75.3% (339/450) | 80.4% (362/450) | +5.1 | — (71%) | — (77%) |
| H3 | Medications found (name) | R | validated | 94.7% (71/75) | 94.7% (71/75) | +0.0 | — (87%) | — (87%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 80.0% (60/75) | 84.0% (63/75) | +4.0 | — (70%) | — (74%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | 90.1% (64/71) | 88.7% (63/71) | -1.4 | — (81%) | — (79%) |
| H6 | Symptoms found | R | validated | 76.0% (98/129) | 77.5% (100/129) | +1.6 | — (68%) | — (70%) |
| H7 | Pertinent negatives found | R | validated | 78.9% (71/90) | 80.0% (72/90) | +1.1 | — (69%) | — (71%) |
| H8 | Vital signs found | R | validated | 97.2% (35/36) | 100.0% (36/36) | +2.8 | ✅ (86%) | ✅ (90%) |
| H9 | Nurse actions found (type) | R | validated | 81.7% (165/202) | 79.7% (161/202) | -2.0 | — (76%) | — (74%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 80.2% (162/202) | 78.7% (159/202) | -1.5 | — (74%) | — (73%) |
| H11 | Education items found (type) | R | validated | 59.5% (122/205) | 63.4% (130/205) | +3.9 | — (53%) | — (57%) |
| H12 | Gold risk flags found | R | validated | 89.2% (33/37) | 91.9% (34/37) | +2.7 | — (75%) | — (79%) |
| H13 | Output risk flags that are in gold | R | validated | 24.6% (33/134) | 26.6% (34/128) | +1.9 | — (18%) | — (20%) |
| H14 | Not-Applicable decision correct | R | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 87.2% (341/391) | 87.5% (342/391) | +0.3 | — (84%) | — (84%) |
| H16 | Response bullets covered | R | validated | 94.0% (189/201) | 93.0% (187/201) | -1.0 | — (90%) | — (89%) |
| H17 | Education bullets covered | R | validated | 69.8% (143/205) | 68.8% (141/205) | -1.0 | — (63%) | — (62%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 48.6% (71/146) | 53.4% (71/133) | +4.8 | — (41%) | — (45%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 49.3% (863/1749) | 51.3% (890/1735) | +2.0 | — (47%) | — (49%) |
| **O. Operational** | | | | | | | | |
| O1 | Latency p95 under 15 s (calls under 15 s) | O | validated | 10.0% (10/100) | n/a |  | — (6%) |  |
| O2 | Outputs not cut off by the token limit | O | validated | 100.0% (100/100) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |

**base_v2: 21 of 47 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (99.7%), A4 Quotes are in the cited turns (verbatim or repairable) (96.8%), A5 Quotes are exactly verbatim (96.2%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.4%), B2 Numbers are in the cited turns (+/-2) (97.3%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (98.9%), C2 Negative findings are not stated as present (99.5%), C3 Caller hedges are kept (98.1%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (95.0%), F2 Complete: checklist items covered (item level) (96.9%), H8 Vital signs found (97.2%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)
**base_v3: 21 of 46 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (99.7%), A4 Quotes are in the cited turns (verbatim or repairable) (97.1%), A5 Quotes are exactly verbatim (96.6%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.3%), B2 Numbers are in the cited turns (+/-2) (97.6%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (99.3%), C2 Negative findings are not stated as present (99.6%), C3 Caller hedges are kept (97.6%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (98.0%), F2 Complete: checklist items covered (item level) (97.7%), H8 Vital signs found (100.0%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)

## Breakdown

**base_v2 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 66.7% | 58.3% | 51.2% |
| asr_error | 12 | 66.7% | 66.7% | 44.6% |
| high_risk | 20 | 70.0% | 65.0% | 47.8% |
| medication | 18 | 66.7% | 55.6% | 52.2% |
| not_applicable | 10 | 40.0% | 40.0% | 100.0% |
| routine | 16 | 50.0% | 50.0% | 51.3% |
| supply | 12 | 75.0% | 75.0% | 46.6% |

**base_v2 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 50.0% | 50.0% | 44.9% |
| medium | 11 | 72.7% | 63.6% | 45.5% |
| short | 73 | 64.4% | 60.3% | 51.7% |

**base_v2 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 62.5% | 62.5% | 45.5% |
| low | 75 | 62.7% | 58.7% | 50.4% |
| medium | 17 | 64.7% | 58.8% | 46.9% |

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
