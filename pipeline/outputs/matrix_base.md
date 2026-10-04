# Evaluation matrix: base

Cases: 100. Rates are 0-100% (100 = best). Src: D rules, J LLM judge, R gold reference, DJ both, O operational.

| ID | Metric | Src | Evidence | base (rate, n/d) | ≥95% [base] (lower 95% bound) |
|---|---|---|---|---|---|
| **A. Output validity** | | | | | |
| A1 | Output is valid JSON | D | validated | 98.0% (98/100) | ✅ (93%) |
| A2 | Output matches the schema | D | validated | 98.0% (98/100) | ✅ (93%) |
| A3 | Cited turns exist | D | validated | 99.9% (1486/1488) | ✅ (100%) lower bound ≥95 |
| A4 | Quotes are in the cited turns (verbatim or repairable) | D | validated | 95.4% (1419/1488) | ✅ (94%) |
| A5 | Quotes are exactly verbatim | D | validated | 94.9% (1412/1488) | — (94%) |
| A6 | Quote speaker matches the transcript label | D | validated | 99.8% (1294/1297) | ✅ (99%) lower bound ≥95 |
| **B. Grounding in the call** | | | | | |
| B1 | Numbers in the summary were spoken in the call | D | validated | 98.9% (747/755) | ✅ (98%) lower bound ≥95 |
| B2 | Numbers are in the cited turns (+/-2) | D | validated | 96.8% (731/755) | ✅ (95%) lower bound ≥95 |
| B3 | Drug names appear in the call | D | validated | 100.0% (148/148) | ✅ (97%) lower bound ≥95 |
| B4 | Clinical terms (fever, fall, seizure ...) appear in the call | D | validated | 100.0% (515/515) | ✅ (99%) lower bound ≥95 |
| B5 | Identity values (name, DOB, phone, relationship) were spoken | D | validated | 77.5% (341/440) | — (73%) |
| **C. Wording vs meaning** | | | | | |
| C1 | Planned vs completed matches the nurse's words | D | validated | 100.0% (229/229) | ✅ (98%) lower bound ≥95 |
| C2 | Negative findings are not stated as present | D | validated | 100.0% (171/171) | ✅ (98%) lower bound ≥95 |
| C3 | Caller hedges are kept | D | indicator | 98.9% (529/535) | ✅ (98%) lower bound ≥95 |
| **D. Safety gates** | | | | | |
| D1 | Not-Applicable decision agrees with the clinical-content gate | D | validated | 100.0% (98/98) | ✅ (96%) lower bound ≥95 |
| D2 | Suicidal / escalation flags the rules find are also in the output | D | validated | 100.0% (10/10) | ✅ (72%) |
| D2b | Other risk flags the rules suggest are also in the output | D | indicator | 60.0% (24/40) | — (45%) |
| D3 | Drugs mentioned in the call appear in the summary | D | indicator | 82.5% (85/103) | — (74%) |
| **E. Whole call (rules)** | | | | | |
| E1 | Calls with no rule ERROR | D | validated | 7.0% (7/100) | — (3%) |
| E2 | Calls with no rule ERROR and no WARN (no nurse review needed) | D | indicator | 6.0% (6/100) | — (3%) |
| **F. Meaning (LLM judge)** | | | | | |
| F1 | Faithful: nothing wrong or invented | J | validated | 92.0% (92/100) | — (85%) |
| F2 | Complete: checklist items covered (item level) | J | indicator | 97.3% (878/902) | ✅ (96%) lower bound ≥95 |
| F3 | Complete: calls where every checklist item is covered | J | indicator | 80.0% (80/100) | — (71%) |
| F4 | Calibrated: hedges, planned vs done, speaker (indicator) | J | indicator | 85.0% (85/100) | — (77%) |
| **G. Pipeline (rules + judge)** | | | | | |
| G1 | Safe-pass: no rule ERROR and judged faithful | DJ | validated | 7.0% (7/100) | — (3%) |
| G2 | Full-pass: safe-pass and complete and calibrated | DJ | indicator | 6.0% (6/100) | — (3%) |
| **H. Against gold (validation set)** | | | | | |
| H1 | Identity values correct (5 fields) | R | validated | 65.8% (296/450) | — (61%) |
| H2 | Identity values AND certainty correct | R | validated | 61.8% (278/450) | — (57%) |
| H3 | Medications found (name) | R | validated | 0.0% (0/75) | — (0%) |
| H4 | Medications correct (name + dose + unit) | R | validated | 0.0% (0/75) | — (0%) |
| H5 | Medication certainty (stated/unclear) correct | R | validated | n/a |  |
| H6 | Symptoms found | R | validated | 65.9% (85/129) | — (57%) |
| H7 | Pertinent negatives found | R | validated | 68.9% (62/90) | — (59%) |
| H8 | Vital signs found | R | validated | 94.4% (34/36) | — (82%) |
| H9 | Nurse actions found (type) | R | validated | 0.0% (0/202) | — (0%) |
| H10 | Nurse actions correct (type + planned/completed) | R | validated | 0.0% (0/202) | — (0%) |
| H11 | Education items found (type) | R | validated | 0.0% (0/205) | — (0%) |
| H12 | Gold risk flags found | R | validated | 89.2% (33/37) | — (75%) |
| H13 | Output risk flags that are in gold | R | validated | 23.9% (33/138) | — (18%) |
| H14 | Not-Applicable decision correct | R | validated | 98.0% (98/100) | ✅ (93%) |
| H15 | Assessment bullets covered (anchored on cited turns) | R | validated | 84.1% (329/391) | — (80%) |
| H16 | Response bullets covered | R | validated | 92.5% (186/201) | — (88%) |
| H17 | Education bullets covered | R | validated | 78.5% (161/205) | — (72%) |
| H18 | Output medications that are in gold (no hallucinated drug) | R | validated | 0.0% (0/92) | — (0%) |
| H19 | Critical-Fact Accuracy (headline in the architecture) | R | validated | 28.9% (556/1921) | — (27%) |
| **O. Operational** | | | | | |
| O1 | Latency p95 under 15 s (calls under 15 s) | O | validated | 9.0% (9/100) | — (5%) |
| O2 | Outputs not cut off by the token limit | O | validated | 98.0% (98/100) | ✅ (93%) |

**base: 17 of 46 metrics reach ≥95%:** A1 Output is valid JSON (98.0%), A2 Output matches the schema (98.0%), A3 Cited turns exist (99.9%), A4 Quotes are in the cited turns (verbatim or repairable) (95.4%), A6 Quote speaker matches the transcript label (99.8%), B1 Numbers in the summary were spoken in the call (98.9%), B2 Numbers are in the cited turns (+/-2) (96.8%), B3 Drug names appear in the call (100.0%), B4 Clinical terms (fever, fall, seizure ...) appear in the call (100.0%), C1 Planned vs completed matches the nurse's words (100.0%), C2 Negative findings are not stated as present (100.0%), C3 Caller hedges are kept (98.9%), D1 Not-Applicable decision agrees with the clinical-content gate (100.0%), D2 Suicidal / escalation flags the rules find are also in the output (100.0%), F2 Complete: checklist items covered (item level) (97.3%), H14 Not-Applicable decision correct (98.0%), O2 Outputs not cut off by the token limit (98.0%)

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
