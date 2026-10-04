# Evaluation matrix: base_v4 vs finetuned_epoch2

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | base_v4 (rate, n/d) | finetuned_epoch2 (rate, n/d) | Δ pts | ≥95% [base_v4] (lower 95% bound) | ≥95% [finetuned_epoch2] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 100.0% (100/100) | 96.0% (96/100) | -4.0 | ✅ (96%) lower bound ≥95 | ✅ (90%) |
| A2 | Output matches the schema | D | validated | 100.0% (100/100) | 96.0% (96/100) | -4.0 | ✅ (96%) lower bound ≥95 | ✅ (90%) |
| A3 | Cited turns exist | D | validated | 99.7% (1537/1542) | 99.9% (841/842) | +0.2 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 97.5% (1504/1542) | 99.3% (836/842) | +1.8 | ✅ (97%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 96.9% (1494/1542) | 99.3% (836/842) | +2.4 | ✅ (96%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.9% (1380/1382) | 99.9% (805/806) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 97.9% (468/478) | 100.0% (211/211) | +2.1 | ✅ (96%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 96.7% (462/478) | 100.0% (211/211) | +3.3 | ✅ (95%) | ✅ (98%) lower bound ≥95 |
| B3 | Drug names appear in the call | D | validated | 100.0% (354/354) | 99.3% (136/137) | -0.7 | ✅ (99%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (538/538) | 100.0% (385/385) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 99.5% (425/427) | 99.8% (403/404) | +0.2 | ✅ (98%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 99.6% (280/281) | 100.0% (186/186) | +0.4 | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 99.5% (209/210) | 100.0% (78/78) | +0.5 | ✅ (97%) lower bound ≥95 | ✅ (95%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 97.5% (551/565) | 98.6% (353/358) | +1.1 | ✅ (96%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (100/100) | 99.0% (95/96) | -1.0 | ✅ (96%) lower bound ≥95 | ✅ (94%) |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | 100.0% (10/10) | +0.0 | ✅ (72%) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 60.0% (24/40) | 42.1% (16/38) | -17.9 | — (45%) | — (28%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 88.3% (91/103) | 72.4% (71/98) | -15.9 | — (81%) | — (63%) |
| **E. Whole call (rules)** | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 70.0% (70/100) | 89.0% (89/100) | +19.0 | — (60%) | — (81%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 37.0% (37/100) | 53.0% (53/100) | +16.0 | — (28%) | — (43%) |
| E1r | Calls with no rule ERROR after automatic quote repair | D | indicator | 83.0% (83/100) | 90.0% (90/100) | +7.0 | — (74%) | — (83%) |
| **F. Meaning (LLM judge)** | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 98.0% (98/100) | 93.0% (93/100) | -5.0 | ✅ (93%) | — (86%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 96.7% (880/910) | 91.9% (792/862) | -4.8 | ✅ (95%) lower bound ≥95 | — (90%) |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 80.0% (80/100) | 53.0% (53/100) | -27.0 | — (71%) | — (43%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 85.0% (85/100) | 92.0% (92/100) | +7.0 | — (77%) | — (85%) |
| **G. Pipeline (rules + judge)** | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 70.0% (70/100) | 87.0% (87/100) | +17.0 | — (60%) | — (79%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 47.0% (47/100) | 46.0% (46/100) | -1.0 | — (38%) | — (37%) |
| G1r | Safe-pass after automatic quote repair | DJ | indicator | 82.0% (82/100) | 88.0% (88/100) | +6.0 | — (73%) | — (80%) |
| **H. Against gold (validation set)** | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 97.3% (438/450) | 93.1% (419/450) | -4.2 | ✅ (95%) lower bound ≥95 | — (90%) |
| H2 | Identity values AND certainty correct | R | validated | 94.0% (423/450) | 92.2% (415/450) | -1.8 | — (91%) | — (89%) |
| H3 | Medications found (name) | R | validated | 93.3% (70/75) | 2.7% (2/75) | -90.7 | — (85%) | — (1%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 78.7% (59/75) | 2.7% (2/75) | -76.0 | — (68%) | — (1%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | 90.0% (63/70) | 100.0% (2/2) | +10.0 | — (81%) | ✅ (34%) |
| H6 | Symptoms found | R | validated | 77.5% (100/129) | 64.3% (83/129) | -13.2 | — (70%) | — (56%) |
| H7 | Pertinent negatives found | R | validated | 77.8% (70/90) | 64.4% (58/90) | -13.3 | — (68%) | — (54%) |
| H8 | Vital signs found | R | validated | 100.0% (36/36) | 2.8% (1/36) | -97.2 | ✅ (90%) | — (0%) |
| H9 | Nurse actions found (type) | R | validated | 78.2% (158/202) | 62.4% (126/202) | -15.8 | — (72%) | — (56%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 77.7% (157/202) | 62.4% (126/202) | -15.3 | — (71%) | — (56%) |
| H11 | Education items found (type) | R | validated | 57.6% (118/205) | 60.0% (123/205) | +2.4 | — (51%) | — (53%) |
| H12 | Gold risk flags found | R | validated | 89.2% (33/37) | 78.4% (29/37) | -10.8 | — (75%) | — (63%) |
| H13 | Output risk flags that are in gold | R | validated | 27.0% (33/122) | 96.7% (29/30) | +69.6 | — (20%) | ✅ (83%) |
| H14 | Not-Applicable decision correct | R | validated | 100.0% (100/100) | 95.0% (95/100) | -5.0 | ✅ (96%) lower bound ≥95 | ✅ (89%) |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 87.5% (342/391) | 78.5% (307/391) | -9.0 | — (84%) | — (74%) |
| H16 | Response bullets covered | R | validated | 92.5% (186/201) | 80.1% (161/201) | -12.4 | — (88%) | — (74%) |
| H17 | Education bullets covered | R | validated | 68.8% (141/205) | 75.1% (154/205) | +6.3 | — (62%) | — (69%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 47.3% (70/148) | 3.3% (2/61) | -44.0 | — (39%) | — (1%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 56.9% (942/1656) | 62.7% (808/1288) | +5.8 | — (54%) | — (60%) |
| H19r | Gold critical facts found (no penalty for extra facts) | R | indicator | 87.0% (942/1083) | 74.6% (808/1083) | -12.4 | — (85%) | — (72%) |
| **O. Operational** | | | | | | | | |
| O2 | Outputs not cut off by the token limit | O | validated | 100.0% (100/100) | 96.0% (96/100) | -4.0 | ✅ (96%) lower bound ≥95 | ✅ (90%) |

**base_v4: 22 of 49 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (99.7%), A4 Quotes are in the cited turns (verbatim or repairable) (97.5%), A5 Quotes are exactly verbatim (96.9%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (97.9%), B2 Numbers are in the cited turns (+/-2) (96.7%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (99.6%), C2 Negative findings are not stated as present (99.5%), C3 Caller hedges are kept (97.5%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (98.0%), F2 Complete: checklist items covered (item level) (96.7%), H1 Identity values correct (5 fields) (97.3%), H8 Vital signs found (100.0%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)
**finetuned_epoch2: 20 of 49 metrics reach ≥95%:** A1 Output is valid JSON (96.0%), A2 Output matches the schema (96.0%), A3 Cited turns exist (99.9%), A4 Quotes are in the cited turns (verbatim or repairable) (99.3%), A5 Quotes are exactly verbatim (99.3%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (100.0%), B2 Numbers are in the cited turns (+/-2) (100.0%), B3 Drug names appear in the call (99.3%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.8%), C1 Planned vs completed matches the nurse's words (100.0%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (98.6%), D1 Not-Applicable decision agrees with the clinical-content gate (99.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), H5 Medication certainty (stated/unclear) correct (100.0%), H13 Output risk flags that are in gold (96.7%), H14 Not-Applicable decision correct (95.0%), O2 Outputs not cut off by the token limit (96.0%)

## Breakdown

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

**finetuned_epoch2 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 91.7% | 91.7% | 70.8% |
| asr_error | 12 | 83.3% | 75.0% | 55.8% |
| high_risk | 20 | 85.0% | 80.0% | 57.4% |
| medication | 18 | 77.8% | 77.8% | 54.4% |
| not_applicable | 10 | 100.0% | 100.0% | 100.0% |
| routine | 16 | 93.8% | 93.8% | 75.4% |
| supply | 12 | 100.0% | 100.0% | 72.5% |

**finetuned_epoch2 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 87.5% | 81.2% | 48.7% |
| medium | 11 | 100.0% | 100.0% | 70.5% |
| short | 73 | 87.7% | 86.3% | 65.9% |

**finetuned_epoch2 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 75.0% | 62.5% | 48.5% |
| low | 75 | 89.3% | 88.0% | 64.2% |
| medium | 17 | 94.1% | 94.1% | 63.0% |
