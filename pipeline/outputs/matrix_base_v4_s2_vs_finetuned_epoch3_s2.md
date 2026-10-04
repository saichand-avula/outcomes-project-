# Evaluation matrix: base_v4_s2 vs finetuned_epoch3_s2

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | base_v4_s2 (rate, n/d) | finetuned_epoch3_s2 (rate, n/d) | Δ pts | ≥95% [base_v4_s2] (lower 95% bound) | ≥95% [finetuned_epoch3_s2] (lower 95% bound) |
|---|---|---|---|---|---|---|---|---|
| **A. Output validity** | | | | | | | | |
| A1 | Output is valid JSON | D | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |
| A2 | Output matches the schema | D | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |
| A3 | Cited turns exist | D | validated | 99.6% (1538/1544) | 100.0% (939/939) | +0.4 | ✅ (99%) lower bound ≥95 | ✅ (100%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 97.2% (1500/1544) | 99.7% (936/939) | +2.5 | ✅ (96%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A5 | Quotes are exactly verbatim | D | validated | 96.7% (1493/1544) | 99.7% (936/939) | +3.0 | ✅ (96%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| A6 | Quote speaker matches the transcript label | D | validated | 99.8% (1381/1384) | 99.9% (902/903) | +0.1 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 98.7% (461/467) | 99.7% (384/385) | +1.0 | ✅ (97%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 97.0% (453/467) | 99.0% (381/385) | +2.0 | ✅ (95%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B3 | Drug names appear in the call | D | validated | 100.0% (281/281) | 99.5% (192/193) | -0.5 | ✅ (99%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (526/526) | 100.0% (443/443) | +0.0 | ✅ (99%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 99.5% (416/418) | 99.8% (426/427) | +0.2 | ✅ (98%) lower bound ≥95 | ✅ (99%) lower bound ≥95 |
| **C. Wording vs meaning** | | | | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 99.6% (248/249) | 99.5% (213/214) | -0.1 | ✅ (98%) lower bound ≥95 | ✅ (97%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 99.0% (204/206) | 100.0% (87/87) | +1.0 | ✅ (97%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 98.2% (549/559) | 97.7% (384/393) | -0.5 | ✅ (97%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| **D. Safety gates** | | | | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (98/98) | 100.0% (100/100) | +0.0 | ✅ (96%) lower bound ≥95 | ✅ (96%) lower bound ≥95 |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | 100.0% (10/10) | +0.0 | ✅ (72%) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 59.0% (23/39) | 35.0% (14/40) | -24.0 | — (43%) | — (22%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 92.8% (90/97) | 72.8% (75/103) | -20.0 | — (86%) | — (64%) |
| **E. Whole call (rules)** | | | | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 62.0% (62/100) | 94.0% (94/100) | +32.0 | — (52%) | — (88%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 29.0% (29/100) | 51.0% (51/100) | +22.0 | — (21%) | — (41%) |
| E1r | Calls with no rule ERROR after automatic quote repair | D | indicator | 80.0% (80/100) | 96.0% (96/100) | +16.0 | — (71%) | ✅ (90%) |
| **F. Meaning (LLM judge)** | | | | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 95.0% (95/100) | 97.0% (97/100) | +2.0 | ✅ (89%) | ✅ (92%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 97.7% (873/894) | 95.4% (868/910) | -2.3 | ✅ (96%) lower bound ≥95 | ✅ (94%) |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 81.0% (81/100) | 68.0% (68/100) | -13.0 | — (72%) | — (58%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 85.0% (85/100) | 95.0% (95/100) | +10.0 | — (77%) | ✅ (89%) |
| **G. Pipeline (rules + judge)** | | | | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 60.0% (60/100) | 92.0% (92/100) | +32.0 | — (50%) | — (85%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 43.0% (43/100) | 61.0% (61/100) | +18.0 | — (34%) | — (51%) |
| G1r | Safe-pass after automatic quote repair | DJ | indicator | 78.0% (78/100) | 94.0% (94/100) | +16.0 | — (69%) | — (88%) |
| **H. Against gold (validation set)** | | | | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 95.1% (428/450) | 98.2% (442/450) | +3.1 | ✅ (93%) | ✅ (97%) lower bound ≥95 |
| H2 | Identity values AND certainty correct | R | validated | 91.8% (413/450) | 98.0% (441/450) | +6.2 | — (89%) | ✅ (96%) lower bound ≥95 |
| H3 | Medications found (name) | R | validated | 93.3% (70/75) | 89.3% (67/75) | -4.0 | — (85%) | — (80%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 82.7% (62/75) | 74.7% (56/75) | -8.0 | — (73%) | — (64%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | 90.0% (63/70) | 94.0% (63/67) | +4.0 | — (81%) | — (86%) |
| H6 | Symptoms found | R | validated | 75.2% (97/129) | 79.8% (103/129) | +4.7 | — (67%) | — (72%) |
| H7 | Pertinent negatives found | R | validated | 73.3% (66/90) | 81.1% (73/90) | +7.8 | — (63%) | — (72%) |
| H8 | Vital signs found | R | validated | 91.7% (33/36) | 83.3% (30/36) | -8.3 | — (78%) | — (68%) |
| H9 | Nurse actions found (type) | R | validated | 73.8% (149/202) | 87.6% (177/202) | +13.9 | — (67%) | — (82%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 72.8% (147/202) | 87.1% (176/202) | +14.4 | — (66%) | — (82%) |
| H11 | Education items found (type) | R | validated | 60.0% (123/205) | 83.9% (172/205) | +23.9 | — (53%) | — (78%) |
| H12 | Gold risk flags found | R | validated | 89.2% (33/37) | 78.4% (29/37) | -10.8 | — (75%) | — (63%) |
| H13 | Output risk flags that are in gold | R | validated | 27.0% (33/122) | 87.9% (29/33) | +60.8 | — (20%) | — (73%) |
| H14 | Not-Applicable decision correct | R | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 86.4% (338/391) | 86.7% (339/391) | +0.3 | — (83%) | — (83%) |
| H16 | Response bullets covered | R | validated | 92.5% (186/201) | 89.6% (180/201) | -3.0 | — (88%) | — (85%) |
| H17 | Education bullets covered | R | validated | 69.3% (142/205) | 83.4% (171/205) | +14.1 | — (63%) | — (78%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 50.4% (70/139) | 90.5% (67/74) | +40.2 | — (42%) | — (82%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 56.8% (916/1613) | 81.6% (978/1198) | +24.8 | — (54%) | — (79%) |
| H19r | Gold critical facts found (no penalty for extra facts) | R | indicator | 84.6% (916/1083) | 90.3% (978/1083) | +5.7 | — (82%) | — (88%) |
| **O. Operational** | | | | | | | | |
| O1 | Latency p95 under 15 s (calls under 15 s) | O | validated | 10.0% (2/20) | 65.0% (13/20) | +55.0 | — (3%) | — (43%) |
| O2 | Outputs not cut off by the token limit | O | validated | 98.0% (98/100) | 100.0% (100/100) | +2.0 | ✅ (93%) | ✅ (96%) lower bound ≥95 |

**base_v4_s2: 21 of 50 metrics reach ≥95%:** A1 Output is valid JSON (98.0%), A2 Output matches the schema (98.0%), A3 Cited turns exist (99.6%), A4 Quotes are in the cited turns (verbatim or repairable) (97.2%), A5 Quotes are exactly verbatim (96.7%), A6 Quote speaker matches the transcript label (99.8%), B1 Numbers in the summary were spoken in the call (98.7%), B2 Numbers are in the cited turns (+/-2) (97.0%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.5%), C1 Planned vs completed matches the nurse's words (99.6%), C2 Negative findings are not stated as present (99.0%), C3 Caller hedges are kept (98.2%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F1 Faithful: nothing wrong or invented (95.0%), F2 Complete: checklist items covered (item level) (97.7%), H1 Identity values correct (5 fields) (95.1%), H14 Not-Applicable decision correct (98.0%), O2 Outputs not cut off by the token limit (98.0%)
**finetuned_epoch3_s2: 24 of 50 metrics reach ≥95%:** A1 Output is valid JSON (100.0%), A2 Output matches the schema (100.0%), A3 Cited turns exist (100.0%), A4 Quotes are in the cited turns (verbatim or repairable) (99.7%), A5 Quotes are exactly verbatim (99.7%), A6 Quote speaker matches the transcript label (99.9%), B1 Numbers in the summary were spoken in the call (99.7%), B2 Numbers are in the cited turns (+/-2) (99.0%), B3 Drug names appear in the call (99.5%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), B5 Identity values (name, DOB, phone, relationship) were spoken (99.8%), C1 Planned vs completed matches the nurse's words (99.5%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (97.7%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), E1r Calls with no rule ERROR after automatic quote repair (96.0%), F1 Faithful: nothing wrong or invented (97.0%), F2 Complete: checklist items covered (item level) (95.4%), F4 Calibrated: hedges, planned vs done, speaker (indicator) (95.0%), H1 Identity values correct (5 fields) (98.2%), H2 Identity values AND certainty correct (98.0%), H14 Not-Applicable decision correct (100.0%), O2 Outputs not cut off by the token limit (100.0%)

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
