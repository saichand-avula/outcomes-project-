# Evaluation matrix: base_v4_s2 vs finetuned_epoch2_s2

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | base_v4_s2 (rate, n/d) | finetuned_epoch2_s2 (rate, n/d) | Δ pts | ≥95% [base_v4_s2] (lower 95% bound) | ≥95% [finetuned_epoch2_s2] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |
| A2 | Output matches the schema | D | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |
| A3 | Cited turns exist | D | validated | 99.6% (1538/1544) | 100.0% (865/865) | +0.4 | ✅ (99%) lower bound ≥95 | ✅ (100%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 97.2% (1500/1544) | 99.3% (859/865) | +2.2 | ✅ (96%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 96.7% (1493/1544) | 99.2% (858/865) | +2.5 | ✅ (96%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.8% (1381/1384) | 99.9% (825/826) | +0.1 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 98.7% (461/467) | 100.0% (387/387) | +1.3 | ✅ (97%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 97.0% (453/467) | 100.0% (387/387) | +3.0 | ✅ (95%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B3 | Drug names appear in the call | D | validated | 100.0% (281/281) | 99.5% (186/187) | -0.5 | ✅ (99%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (526/526) | 100.0% (405/405) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 99.5% (416/418) | 99.8% (422/423) | +0.2 | ✅ (98%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 99.6% (248/249) | 100.0% (191/191) | +0.4 | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 99.0% (204/206) | 100.0% (78/78) | +1.0 | ✅ (97%) lower bound ≥95 | ✅ (95%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 98.2% (549/559) | 98.3% (356/362) | +0.1 | ✅ (97%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (98/98) | 99.0% (99/100) | -1.0 | ✅ (96%) lower bound ≥95 | ✅ (95%) |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | 100.0% (10/10) | +0.0 | ✅ (72%) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 59.0% (23/39) | 40.0% (16/40) | -19.0 | — (43%) | — (26%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 92.8% (90/97) | 68.0% (70/103) | -24.8 | — (86%) | — (58%) |
| **E. Whole call (rules)** | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 62.0% (62/100) | 93.0% (93/100) | +31.0 | — (52%) | — (86%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 29.0% (29/100) | 53.0% (53/100) | +24.0 | — (21%) | — (43%) |
| E1r | Calls with no rule ERROR after automatic quote repair | D | indicator | 80.0% (80/100) | 94.0% (94/100) | +14.0 | — (71%) | — (88%) |
| **F. Meaning (LLM judge)** | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 95.0% (95/100) | 98.0% (98/100) | +3.0 | ✅ (89%) | ✅ (93%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 97.7% (873/894) | 92.1% (833/904) | -5.5 | ✅ (96%) lower bound ≥95 | — (90%) |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 81.0% (81/100) | 57.0% (57/100) | -24.0 | — (72%) | — (47%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 85.0% (85/100) | 96.0% (96/100) | +11.0 | — (77%) | ✅ (90%) |
| **G. Pipeline (rules + judge)** | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 60.0% (60/100) | 91.0% (91/100) | +31.0 | — (50%) | — (84%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 43.0% (43/100) | 51.0% (51/100) | +8.0 | — (34%) | — (41%) |
| G1r | Safe-pass after automatic quote repair | DJ | indicator | 78.0% (78/100) | 92.0% (92/100) | +14.0 | — (69%) | — (85%) |
| **H. Against gold (validation set)** | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 95.1% (428/450) | 97.6% (439/450) | +2.4 | ✅ (93%) | ✅ (96%) lower bound ≥95 |
| H2 | Identity values AND certainty correct | R | validated | 91.8% (413/450) | 96.9% (436/450) | +5.1 | — (89%) | ✅ (95%) |
| H3 | Medications found (name) | R | validated | 93.3% (70/75) | 82.7% (62/75) | -10.7 | — (85%) | — (73%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 82.7% (62/75) | 69.3% (52/75) | -13.3 | — (73%) | — (58%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | 90.0% (63/70) | 91.9% (57/62) | +1.9 | — (81%) | — (82%) |
| H6 | Symptoms found | R | validated | 75.2% (97/129) | 79.1% (102/129) | +3.9 | — (67%) | — (71%) |
| H7 | Pertinent negatives found | R | validated | 73.3% (66/90) | 71.1% (64/90) | -2.2 | — (63%) | — (61%) |
| H8 | Vital signs found | R | validated | 91.7% (33/36) | 86.1% (31/36) | -5.6 | — (78%) | — (71%) |
| H9 | Nurse actions found (type) | R | validated | 73.8% (149/202) | 86.1% (174/202) | +12.4 | — (67%) | — (81%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 72.8% (147/202) | 85.6% (173/202) | +12.9 | — (66%) | — (80%) |
| H11 | Education items found (type) | R | validated | 60.0% (123/205) | 79.0% (162/205) | +19.0 | — (53%) | — (73%) |
| H12 | Gold risk flags found | R | validated | 89.2% (33/37) | 81.1% (30/37) | -8.1 | — (75%) | — (66%) |
| H13 | Output risk flags that are in gold | R | validated | 27.0% (33/122) | 90.9% (30/33) | +63.9 | — (20%) | — (76%) |
| H14 | Not-Applicable decision correct | R | validated | 98.0% (98/100) | 99.0% (99/100) | +1.0 | ✅ (93%) | ✅ (95%) |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 86.4% (338/391) | 81.3% (318/391) | -5.1 | — (83%) | — (77%) |
| H16 | Response bullets covered | R | validated | 92.5% (186/201) | 87.1% (175/201) | -5.5 | — (88%) | — (82%) |
| H17 | Education bullets covered | R | validated | 69.3% (142/205) | 80.5% (165/205) | +11.2 | — (63%) | — (75%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 50.4% (70/139) | 89.9% (62/69) | +39.5 | — (42%) | — (81%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 56.8% (916/1613) | 81.4% (956/1174) | +24.6 | — (54%) | — (79%) |
| H19r | Gold critical facts found (no penalty for extra facts) | R | indicator | 84.6% (916/1083) | 88.3% (956/1083) | +3.7 | — (82%) | — (86%) |
| **O. Operational** | | | | | | | | |
| O2 | Outputs not cut off by the token limit | O | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |

**base_v4_s2: 21 of 49 metrics reach ≥95%:** A1 Output is valid JSON (98.0%), A2 Output matches the schema (98.0%), A3 Cited turns exist (99.6%), A4 Quotes are in the cited turns (verbatim or repairable) (97.2%), A5 Quotes are exactly verbatim (96.7%), A6 Quote speaker matches the transcript label (99.8%), B1 Numbers in the summary were spoken in the call (98.7%), B2 Numbers are in the cited turns (+/-2) (97.0%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (99.6%), C2 Negative findings are not stated as present (99.0%), C3 Caller hedges are kept (98.2%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (95.0%), F2 Complete: checklist items covered (item level) (97.7%), H1 Identity values correct (5 fields) (95.1%), H14 Not-Applicable decision correct (98.0%), O2 Outputs not cut off by the token limit (98.0%)
**finetuned_epoch2_s2: 22 of 49 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (100.0%), A4 Quotes are in the cited turns (verbatim or repairable) (99.3%), A5 Quotes are exactly verbatim (99.2%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (100.0%), B2 Numbers are in the cited turns (+/-2) (100.0%), B3 Drug names appear in the call (99.5%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.8%), C1 Planned vs completed matches the nurse's words (100.0%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (98.3%), D1 Not-Applicable decision agrees with the clinical-content gate (99.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (98.0%), F4 Calibrated: hedges, planned vs done, speaker (indicator) (96.0%), H1 Identity values correct (5 fields) (97.6%), H2 Identity values AND certainty correct (96.9%), H14 Not-Applicable decision correct (99.0%), O2 Outputs not cut off by the token limit (100.0%)

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
