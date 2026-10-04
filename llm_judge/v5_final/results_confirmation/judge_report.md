# Judge agreement report (v5 prompts, confirmation set)

Items: 40 (20 edited, 20 clean). Unparseable or missing verdicts: 0.

## Per rubric (FAIL = the summary has this problem)

| Rubric | Agreement | Cohen's kappa | Caught (FAIL when edited) | False alarms (FAIL when clean) |
|---|---|---|---|---|
| faithfulness | 40/40 (100%) | 1.00 | 10/10 | 0/30 |
| completeness | 36/40 (90%) | 0.61 | 4/6 | 2/34 |
| calibration | 36/40 (90%) | 0.55 | 3/6 | 1/34 |

Completeness leaving out 6 calls whose only edit changes a drug or number (a changed dose can reasonably count as missing): 32/34 (94%), kappa 0.77.

## Completeness, item by item (each reference-record item is one question)

- Removed items found: 4/6
- Items wrongly called missing: 2 of 400 items that are in the summary


Edited summaries flagged by at least one rubric (right or wrong one): 16/20.
Clean summaries passed on all three rubrics: 20/20.

All three rubrics agree on 32/40 items (80%).

## Detection by edit type

| Edit | Expected rubric | Items | Judge failed the right rubric |
|---|---|---|---|
| drop_assessment | completeness | 2 | 0/2 |
| drop_education | completeness | 3 | 3/3 |
| drop_response | completeness | 1 | 1/1 |
| fabricated_finding | faithfulness | 2 | 2/2 |
| flipped_negative | faithfulness | 1 | 1/1 |
| hedge_removed | calibration | 1 | 0/1 |
| planned_to_completed | calibration | 2 | 2/2 |
| speaker_swap | calibration | 3 | 1/3 |
| wrong_drug | faithfulness | 3 | 3/3 |
| wrong_number | faithfulness | 4 | 4/4 |
## Items wrongly called missing (check whether the summary really lacks them)

- k-011: Medication: metoprolol succinate, 50 mg, once a day, status: taking, last dose: this morning
- k-017: Medication: lisinopril, 10 mg, once a day, status: taking, last dose: this morning


## Disagreements

- **k-004** (va-007, edited: hedge_removed)
  - calibration: expected FAIL, judge said PASS. [none] no problem
  - change made: Changed assessment item: "Left hip pain was reported as 3 out of 10 earlier and 6 out of 10 when the caller saw her, with the caller unsure of the timing and which report was accurate." -> "Left hip p
- **k-011** (va-089, edited: wrong_drug)
  - completeness: expected PASS, judge said FAIL. Missing: Medication: metoprolol succinate, 50 mg, once a day, status: taking, last dose: this morning
  - facts judged missing: Medication: metoprolol succinate, 50 mg, once a day, status: taking, last dose: this morning
  - change made: Changed assessment item: "Metoprolol succinate 50 mg once a day was unchanged and taken this morning." -> "Lisinopril 50 mg once a day was unchanged and taken this morning."
- **k-017** (va-071, edited: wrong_drug)
  - completeness: expected PASS, judge said FAIL. Missing: Medication: lisinopril, 10 mg, once a day, status: taking, last dose: this morning
  - facts judged missing: Medication: lisinopril, 10 mg, once a day, status: taking, last dose: this morning
  - change made: Changed assessment item: "Lisinopril 10 mg once a day was taken this morning with coffee." -> "Amoxicillin 10 mg once a day was taken this morning with coffee."
- **k-019** (va-020, edited: speaker_swap)
  - calibration: expected FAIL, judge said PASS. [none] no problem
  - change made: Changed the speaker label on "Fasting blood sugar this morning was 132." from Caller to Nurse
- **k-028** (va-049, edited: drop_assessment)
  - completeness: expected FAIL, judge said PASS. Every reference item is covered.
  - change made: Removed the assessment item: "Gabapentin 300 mg three times daily, corrected from an initial misread of 100 mg, last given at noon."
- **k-031** (va-039, edited: wrong_number, speaker_swap)
  - calibration: expected FAIL, judge said PASS. [none] no problem
  - change made: Changed assessment item: "One metoprolol 50 mg tablet belonging to the husband was found missing and the caller thought his wife took it about 40 minutes ago, but he was not certain." -> "One metoprol
  - change made: Changed the speaker label on "Blood pressure was 110/70." from Caller to Nurse
- **k-033** (va-004, edited: drop_assessment)
  - completeness: expected FAIL, judge said PASS. Every reference item is covered.
  - change made: Removed the assessment item: "Slight ankle swelling was noted, a little more than usual."
- **k-038** (va-055, edited: wrong_number)
  - calibration: expected PASS, judge said FAIL. [certainty] The summary states the lips were blue as a fact, whereas the caller said 'I think a little blue'.
  - change made: Changed assessment item: "Oxygen saturation was 86 percent." -> "Oxygen saturation was 76 percent."
