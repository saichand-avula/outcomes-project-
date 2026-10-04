# Judge agreement report (v5 prompts, first set)

Items: 50 (25 edited, 25 clean). Unparseable or missing verdicts: 0.

## Per rubric (FAIL = the summary has this problem)

| Rubric | Agreement | Cohen's kappa | Caught (FAIL when edited) | False alarms (FAIL when clean) |
|---|---|---|---|---|
| faithfulness | 48/50 (96%) | 0.90 | 12/12 | 2/38 |
| completeness | 48/50 (96%) | 0.86 | 8/9 | 1/41 |
| calibration | 43/50 (86%) | 0.55 | 6/8 | 5/42 |

Completeness leaving out 6 calls whose only edit changes a drug or number (a changed dose can reasonably count as missing): 43/44 (98%), kappa 0.93.

## Completeness, item by item (each reference-record item is one question)

- Removed items found: 8/9
- Items wrongly called missing: 1 of 495 items that are in the summary


Edited summaries flagged by at least one rubric (right or wrong one): 22/25.
Clean summaries passed on all three rubrics: 23/25.

All three rubrics agree on 40/50 items (80%).

## Detection by edit type

| Edit | Expected rubric | Items | Judge failed the right rubric |
|---|---|---|---|
| drop_assessment | completeness | 4 | 3/4 |
| drop_education | completeness | 3 | 3/3 |
| drop_response | completeness | 2 | 2/2 |
| fabricated_finding | faithfulness | 3 | 3/3 |
| flipped_negative | faithfulness | 1 | 1/1 |
| hedge_removed | calibration | 1 | 0/1 |
| planned_to_completed | calibration | 4 | 4/4 |
| speaker_swap | calibration | 3 | 2/3 |
| wrong_drug | faithfulness | 3 | 3/3 |
| wrong_number | faithfulness | 5 | 5/5 |
## Items wrongly called missing (check whether the summary really lacks them)

- j-011: Medication: MiraLAX, as needed, status: prescribed, Has it at home and has not used it


## Disagreements

- **j-011** (va-012, edited: wrong_drug)
  - completeness: expected PASS, judge said FAIL. Missing: Medication: MiraLAX, as needed, status: prescribed, Has it at home and has not used it
  - calibration: expected PASS, judge said FAIL. [status] The summary states the nurse 'Advised' giving MiraLAX today, but the nurse used the conditional/future phrasing 'I'd go ahead and give' (I would go ahead and give).
  - facts judged missing: Medication: MiraLAX, as needed, status: prescribed, Has it at home and has not used it
  - change made: Changed assessment item: "MiraLAX was available at home but had not been used." -> "Amoxicillin was available at home but had not been used."
- **j-014** (va-087, clean)
  - calibration: expected PASS, judge said FAIL. [certainty] The summary states the ear had 'slight tenderness' as a fact, but the caller used the hedge 'Maybe' when describing the pain behind the ear.
- **j-015** (va-009, edited: hedge_removed)
  - calibration: expected FAIL, judge said PASS. [none] no problem
  - change made: Changed assessment item: "Lower back pain was estimated at 5 to 6, with the caller unsure of the exact number." -> "Lower back pain was estimated at 5 to 6."
- **j-025** (va-100, edited: drop_education)
  - calibration: expected PASS, judge said FAIL. [status] The summary lists 'paging the on-call clinician' and 'documenting in the chart' as planned actions, but the nurse stated she was doing them 'now'.
  - change made: Removed the education item: "Advised calling 911 if the client is in immediate danger, hit or threatened, or blocked from leaving."
- **j-026** (va-006, edited: speaker_swap)
  - faithfulness: expected PASS, judge said FAIL. The summary states the mother spoke 'without confusion', but the transcript only says 'She sounds normal. She's talking about her cat.'
  - change made: Changed the speaker label on "She sounded normal and spoke about her cat, without confusion." from Caller to Nurse
- **j-027** (va-086, edited: drop_assessment, wrong_number)
  - calibration: expected PASS, judge said FAIL. [certainty] The summary states the oxygen saturation was 83 percent, but the caller explicitly stated it was ninety three.
  - change made: Removed the assessment item: "He was mildly short of breath on the stairs, stopping halfway, unchanged from last week."
  - change made: Changed assessment item: "Oxygen saturation on the finger clip was 93 percent." -> "Oxygen saturation on the finger clip was 83 percent."
- **j-033** (va-080, edited: drop_assessment)
  - completeness: expected FAIL, judge said PASS. Every reference item is covered.
  - change made: Removed the assessment item: "Atropine 2 drops were given under the tongue during the call."
- **j-034** (va-057, edited: speaker_swap)
  - calibration: expected FAIL, judge said PASS. [none] no problem
  - change made: Changed the speaker label on "She had urinary infections twice before that started with confusion." from Caller to Nurse
- **j-035** (va-077, edited: planned_to_completed)
  - faithfulness: expected PASS, judge said FAIL. The summary states the organizer was full for the rest of the week, but the caller stated that Monday, Tuesday, and Wednesday (today) were already empty.
  - change made: Changed response item: "Planned to message the visiting nurse that he checked in and to pass along his number." -> "Completed: message the visiting nurse that he checked in and to pass along his numbe
- **j-039** (va-005, clean)
  - calibration: expected PASS, judge said FAIL. [certainty] The summary states as a fact that no signs of pain were reported, whereas the caller expressed uncertainty by saying 'I don't think so'.
