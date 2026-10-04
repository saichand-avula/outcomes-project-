# Evaluation matrix: base vs base_v2

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | base (rate, n/d) | base_v2 (rate, n/d) | Δ pts | ≥95% [base] (lower 95% bound) | ≥95% [base_v2] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |
| A2 | Output matches the schema | D | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |
| A3 | Cited turns exist | D | validated | 99.9% (1486/1488) | 99.7% (1562/1567) | -0.2 | ✅ (100%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 95.4% (1419/1488) | 96.8% (1517/1567) | +1.4 | ✅ (94%) | ✅ (96%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 94.9% (1412/1488) | 96.2% (1508/1567) | +1.3 | — (94%) | ✅ (95%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.8% (1294/1297) | 99.9% (1387/1389) | +0.1 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 98.9% (747/755) | 99.4% (485/488) | +0.4 | ✅ (98%) lower bound ≥95 | ✅ (98%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 96.8% (731/755) | 97.3% (475/488) | +0.5 | ✅ (95%) lower bound ≥95 | ✅ (95%) lower bound ≥95 |
| B3 | Drug names appear in the call | D | validated | 100.0% (148/148) | 100.0% (375/375) | +0.0 | ✅ (97%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (515/515) | 100.0% (514/514) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 77.5% (341/440) | 99.5% (420/422) | +22.0 | — (73%) | ✅ (98%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 100.0% (229/229) | 98.9% (282/285) | -1.1 | ✅ (98%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 100.0% (171/171) | 99.5% (217/218) | -0.5 | ✅ (98%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 98.9% (529/535) | 98.1% (567/578) | -0.8 | ✅ (98%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (98/98) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | 100.0% (10/10) | +0.0 | ✅ (72%) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 60.0% (24/40) | 60.0% (24/40) | +0.0 | — (45%) | — (45%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 82.5% (85/103) | 92.2% (95/103) | +9.7 | — (74%) | — (85%) |
| **E. Whole call (rules)** | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 7.0% (7/100) | 63.0% (63/100) | +56.0 | — (3%) | — (53%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 6.0% (6/100) | 35.0% (35/100) | +29.0 | — (3%) | — (26%) |
| **F. Meaning (LLM judge)** | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 92.0% (92/100) | 95.0% (95/100) | +3.0 | — (85%) | ✅ (89%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 97.3% (878/902) | 96.9% (882/910) | -0.4 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 80.0% (80/100) | 79.0% (79/100) | -1.0 | — (71%) | — (70%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 85.0% (85/100) | 89.0% (89/100) | +4.0 | — (77%) | — (81%) |
| **G. Pipeline (rules + judge)** | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 7.0% (7/100) | 59.0% (59/100) | +52.0 | — (3%) | — (49%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 6.0% (6/100) | 41.0% (41/100) | +35.0 | — (3%) | — (32%) |
| **H. Against gold (validation set)** | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 65.8% (296/450) | 81.8% (368/450) | +16.0 | — (61%) | — (78%) |
| H2 | Identity values AND certainty correct | R | validated | 61.8% (278/450) | 72.4% (326/450) | +10.7 | — (57%) | — (68%) |
| H3 | Medications found (name) | R | validated | 0.0% (0/75) | 94.7% (71/75) | +94.7 | — (0%) | — (87%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 0.0% (0/75) | 12.0% (9/75) | +12.0 | — (0%) | — (6%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | n/a | 90.1% (64/71) |  |  | — (81%) |
| H6 | Symptoms found | R | validated | 65.9% (85/129) | 69.0% (89/129) | +3.1 | — (57%) | — (61%) |
| H7 | Pertinent negatives found | R | validated | 68.9% (62/90) | 72.2% (65/90) | +3.3 | — (59%) | — (62%) |
| H8 | Vital signs found | R | validated | 94.4% (34/36) | 97.2% (35/36) | +2.8 | — (82%) | ✅ (86%) |
| H9 | Nurse actions found (type) | R | validated | 0.0% (0/202) | 81.7% (165/202) | +81.7 | — (0%) | — (76%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 0.0% (0/202) | 80.2% (162/202) | +80.2 | — (0%) | — (74%) |
| H11 | Education items found (type) | R | validated | 0.0% (0/205) | 59.5% (122/205) | +59.5 | — (0%) | — (53%) |
| H12 | Gold risk flags found | R | validated | 89.2% (33/37) | 89.2% (33/37) | +0.0 | — (75%) | — (75%) |
| H13 | Output risk flags that are in gold | R | validated | 23.9% (33/138) | 24.6% (33/134) | +0.7 | — (18%) | — (18%) |
| H14 | Not-Applicable decision correct | R | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 84.1% (329/391) | 87.2% (341/391) | +3.1 | — (80%) | — (84%) |
| H16 | Response bullets covered | R | validated | 92.5% (186/201) | 94.0% (189/201) | +1.5 | — (88%) | — (90%) |
| H17 | Education bullets covered | R | validated | 78.5% (161/205) | 69.8% (143/205) | -8.8 | — (72%) | — (63%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 0.0% (0/92) | 48.6% (71/146) | +48.6 | — (0%) | — (41%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 28.9% (556/1921) | 44.1% (784/1777) | +15.2 | — (27%) | — (42%) |
| **O. Operational** | | | | | | | | |
| O1 | Latency p95 under 15 s (calls under 15 s) | O | validated | 9.0% (9/100) | 10.0% (10/100) | +1.0 | — (5%) | — (6%) |
| O2 | Outputs not cut off by the token limit | O | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |

**base: 17 of 46 metrics reach ≥95%:** A1 Output is valid JSON (98.0%), A2 Output matches the schema (98.0%), A3 Cited turns exist (99.9%), A4 Quotes are in the cited turns (verbatim or repairable) (95.4%), A6 Quote speaker matches the transcript label (99.8%), B1 Numbers in the summary were spoken in the call (98.9%), B2 Numbers are in the cited turns (+/-2) (96.8%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), C1 Planned vs completed matches the nurse's words (100.0%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (98.9%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F2 Complete: checklist items covered (item level) (97.3%), H14 Not-Applicable decision correct (98.0%), O2 Outputs not cut off by the token limit (98.0%)
**base_v2: 21 of 47 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (99.7%), A4 Quotes are in the cited turns (verbatim or repairable) (96.8%), A5 Quotes are exactly verbatim (96.2%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.4%), B2 Numbers are in the cited turns (+/-2) (97.3%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (98.9%), C2 Negative findings are not stated as present (99.5%), C3 Caller hedges are kept (98.1%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (95.0%), F2 Complete: checklist items covered (item level) (96.9%), H8 Vital signs found (97.2%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)

## Breakdown

**base by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 16.7% | 16.7% | 27.3% |
| asr_error | 12 | 0.0% | 0.0% | 26.0% |
| high_risk | 20 | 0.0% | 0.0% | 28.7% |
| medication | 18 | 0.0% | 0.0% | 26.5% |
| not_applicable | 10 | 50.0% | 50.0% | 90.0% |
| routine | 16 | 0.0% | 0.0% | 34.0% |
| supply | 12 | 0.0% | 0.0% | 29.9% |

**base by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 0.0% | 0.0% | 23.5% |
| medium | 11 | 9.1% | 9.1% | 28.6% |
| short | 73 | 8.2% | 8.2% | 30.9% |

**base by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 12.5% | 12.5% | 23.1% |
| low | 75 | 4.0% | 4.0% | 29.5% |
| medium | 17 | 17.6% | 17.6% | 29.5% |

**base_v2 by category**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| ambiguous | 12 | 66.7% | 58.3% | 47.8% |
| asr_error | 12 | 66.7% | 66.7% | 39.8% |
| high_risk | 20 | 70.0% | 65.0% | 41.0% |
| medication | 18 | 66.7% | 55.6% | 44.2% |
| not_applicable | 10 | 40.0% | 40.0% | 100.0% |
| routine | 16 | 50.0% | 50.0% | 47.8% |
| supply | 12 | 75.0% | 75.0% | 45.2% |

**base_v2 by length**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| long | 16 | 50.0% | 50.0% | 38.7% |
| medium | 11 | 72.7% | 63.6% | 42.1% |
| short | 73 | 64.4% | 60.3% | 46.4% |

**base_v2 by noise**

| group | n | E1 | G1 | H19 |
|---|---|---|---|---|
| high | 8 | 62.5% | 62.5% | 40.1% |
| low | 75 | 62.7% | 58.7% | 45.0% |
| medium | 17 | 64.7% | 58.8% | 42.6% |
