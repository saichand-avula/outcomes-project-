# Judge agreement report (v4)

Items: 50 (25 edited, 25 clean). Unparseable or missing verdicts: 0.

## Per rubric (FAIL = the summary has this problem)

| Rubric | Agreement | Cohen's kappa | Caught (FAIL when edited) | False alarms (FAIL when clean) |
|---|---|---|---|---|
| faithfulness | 48/50 (96%) | 0.90 | 12/12 | 2/38 |
| completeness | 39/50 (78%) | 0.46 | 8/9 | 10/41 |
| calibration | 36/50 (72%) | 0.31 | 6/8 | 12/42 |

Earlier versions for comparison (from their reports). Note: v1-v3 judged completeness against the whole call, and
the clean summaries are complete only against the fact record, so their completeness false alarms were mostly real omissions.

| Rubric | v1 agreement / kappa / caught / false alarms | v2 | v3 |
|---|---|---|---|
| faithfulness | 94% / 0.84 / 11/12 / 2/38 | 96% / 0.89 / 12/12 / 2/36 | 96% / 0.90 / 12/12 / 2/38 |
| completeness | 76% / 0.19 / 3/9 / 6/41 | 27% / 0.05 / 8/8 / 35/40 | 34% / 0.08 / 9/9 / 33/41 |
| calibration | 92% / 0.67 / 5/8 / 1/42 | 90% / 0.64 / 6/8 / 3/40 | 74% / 0.34 / 6/8 / 11/42 |

## Completeness, item by item (each reference-record item is one question)

- Removed items found: 8/9
- Items wrongly called missing: 11 of 495 items that are in the summary


Edited summaries flagged by at least one rubric (right or wrong one): 23/25.
Clean summaries passed on all three rubrics: 18/25.

All three rubrics agree on 27/50 items (54%).

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

- j-003: Symptom present: sore spot on his bottom, red, not open, tailbone area
- j-004: Medication: morphine, 20 mg/mL, 0.25 mL, under the tongue, status: taking, 2 doses remaining
- j-008: Nurse action (planned): physician notification, neurologist's office, because refill authorization and missed doses
- j-009: Instruction given (equipment use): Keep the cracked tubing connected until the new one arrives only if it does not hiss; check for leaks; no smoking or flames
- j-011: Medication: MiraLAX, as needed, status: prescribed, Has it at home and has not used it
- j-012: Instruction given (safety): Have him sit or lie down, stand up slowly with help, and stay with him
- j-017: Medication: docusate, 100 mg, once a day, status: taking, last dose: this morning
- j-019: Instruction given (comfort measures): Reposition him gently with pillows between the knees and apply a warm pack to the lower back for twenty minutes
- j-038: Symptom present: new confusion, severe
- j-041: Medication: furosemide, 20 mg, half a tablet, once a day, status: taking
- j-043: Medication: warfarin, 4 mg, once a day in the evening, status: taking, last dose: last night


## Disagreements

- **j-002** (va-015, clean)
  - calibration: expected PASS, judge said FAIL. The summary states the 10mg total dose as a fact, but the caller expressed uncertainty by saying 'I guess so'.
- **j-003** (va-021, edited: fabricated_finding, speaker_swap)
  - completeness: expected PASS, judge said FAIL. Missing: Symptom present: sore spot on his bottom, red, not open, tailbone area
  - facts judged missing: Symptom present: sore spot on his bottom, red, not open, tailbone area
  - change made: Added an assessment item that is not in the call: "A seizure earlier in the day was reported."
  - change made: Changed the speaker label on "No recent falls were reported." from Caller to Nurse
- **j-004** (va-019, edited: wrong_drug)
  - completeness: expected PASS, judge said FAIL. Missing: Medication: morphine, 20 mg/mL, 0.25 mL, under the tongue, status: taking, 2 doses remaining
  - facts judged missing: Medication: morphine, 20 mg/mL, 0.25 mL, under the tongue, status: taking, 2 doses remaining
  - change made: Changed assessment item: "Morphine 20 mg/mL, 0.25 mL under the tongue, was in use with 2 doses remaining." -> "Furosemide 20 mg/mL, 0.25 mL under the tongue, was in use with 2 doses remaining."
- **j-007** (va-067, edited: drop_assessment)
  - calibration: expected PASS, judge said FAIL. The summary lists the appointment change as 'Planned' even though the nurse stated 'It's done,' which indicates a completed action.
  - change made: Removed the assessment item: "Mild tingling in the toes at night, unchanged for months."
- **j-008** (va-076, clean)
  - completeness: expected PASS, judge said FAIL. Missing: Nurse action (planned): physician notification, neurologist's office, because refill authorization and missed doses
  - calibration: expected PASS, judge said FAIL. The summary states the patient stared at the wall for 'about ten seconds' as a fact, failing to preserve the caller's uncertainty ('maybe ten seconds').
  - facts judged missing: Nurse action (planned): physician notification, neurologist's office, because refill authorization and missed doses
- **j-009** (va-037, clean)
  - completeness: expected PASS, judge said FAIL. Missing: Instruction given (equipment use): Keep the cracked tubing connected until the new one arrives only if it does not hiss; check for leaks; no smoking or flames
  - facts judged missing: Instruction given (equipment use): Keep the cracked tubing connected until the new one arrives only if it does not hiss; check for leaks; no smoking or flames
- **j-011** (va-012, edited: wrong_drug)
  - completeness: expected PASS, judge said FAIL. Missing: Medication: MiraLAX, as needed, status: prescribed, Has it at home and has not used it
  - calibration: expected PASS, judge said FAIL. The summary incorrectly identifies the medication as 'Amoxicillin' when the transcript and the summary's own quote confirm it is 'MiraLAX'.
  - facts judged missing: Medication: MiraLAX, as needed, status: prescribed, Has it at home and has not used it
  - change made: Changed assessment item: "MiraLAX was available at home but had not been used." -> "Amoxicillin was available at home but had not been used."
- **j-012** (va-045, clean)
  - completeness: expected PASS, judge said FAIL. Missing: Instruction given (safety): Have him sit or lie down, stand up slowly with help, and stay with him
  - calibration: expected PASS, judge said FAIL. The summary states the patient took the medication at about eight and about ten as a fact, but the caller expressed uncertainty ('I think so. Yes. I'm pretty sure').
  - facts judged missing: Instruction given (safety): Have him sit or lie down, stand up slowly with help, and stay with him
- **j-015** (va-009, edited: hedge_removed)
  - calibration: expected FAIL, judge said PASS. The summary accurately reflects the certainty, status, and speaker labels from the transcript.
  - change made: Changed assessment item: "Lower back pain was estimated at 5 to 6, with the caller unsure of the exact number." -> "Lower back pain was estimated at 5 to 6."
- **j-017** (va-068, edited: wrong_number)
  - completeness: expected PASS, judge said FAIL. Missing: Medication: docusate, 100 mg, once a day, status: taking, last dose: this morning
  - facts judged missing: Medication: docusate, 100 mg, once a day, status: taking, last dose: this morning
  - change made: Changed assessment item: "Docusate 100 mg every morning, taken this morning." -> "Docusate 150 mg every morning, taken this morning."
- **j-018** (va-088, edited: fabricated_finding)
  - calibration: expected PASS, judge said FAIL. The summary includes a statement about a fever of 101.5 ('He also had a fever of one oh one point five last night.') which is not present in the transcript and appears to be an hallucination.
  - change made: Added an assessment item that is not in the call: "A fever of 101.5 was reported."
- **j-019** (va-046, clean)
  - completeness: expected PASS, judge said FAIL. Missing: Instruction given (comfort measures): Reposition him gently with pillows between the knees and apply a warm pack to the lower back for twenty minutes
  - facts judged missing: Instruction given (comfort measures): Reposition him gently with pillows between the knees and apply a warm pack to the lower back for twenty minutes
- **j-025** (va-100, edited: drop_education)
  - calibration: expected PASS, judge said FAIL. The summary labels the nurse's action 'I'm documenting everything you've told me in the chart now' as 'Planned', but it is a current/completed action.
  - change made: Removed the education item: "Advised calling 911 if the client is in immediate danger, hit or threatened, or blocked from leaving."
- **j-026** (va-006, edited: speaker_swap)
  - faithfulness: expected PASS, judge said FAIL. The summary states the mother spoke 'without confusion', but the transcript only says 'She sounds normal. She's talking about her cat.'
  - change made: Changed the speaker label on "She sounded normal and spoke about her cat, without confusion." from Caller to Nurse
- **j-027** (va-086, edited: drop_assessment, wrong_number)
  - calibration: expected PASS, judge said FAIL. The summary incorrectly states the oxygen saturation was 83 percent, while the caller explicitly stated it was ninety three.
  - change made: Removed the assessment item: "He was mildly short of breath on the stairs, stopping halfway, unchanged from last week."
  - change made: Changed assessment item: "Oxygen saturation on the finger clip was 93 percent." -> "Oxygen saturation on the finger clip was 83 percent."
- **j-033** (va-080, edited: drop_assessment)
  - completeness: expected FAIL, judge said PASS. Every reference item is in the summary.
  - calibration: expected PASS, judge said FAIL. The summary states the breathing stopped for 'twenty to twenty five seconds' as a fact, but the caller was unsure/estimating in the transcript ('I think he's gone', 'Twenty five').
  - change made: Removed the assessment item: "Atropine 2 drops were given under the tongue during the call."
- **j-034** (va-057, edited: speaker_swap)
  - calibration: expected FAIL, judge said PASS. The summary accurately maintains certainty, status of actions, and speaker labels for all points.
  - change made: Changed the speaker label on "She had urinary infections twice before that started with confusion." from Caller to Nurse
- **j-035** (va-077, edited: planned_to_completed)
  - faithfulness: expected PASS, judge said FAIL. The summary states the organizer was full for the rest of the week, but the caller stated that Monday, Tuesday, and Wednesday (today) were already empty.
  - change made: Changed response item: "Planned to message the visiting nurse that he checked in and to pass along his number." -> "Completed: message the visiting nurse that he checked in and to pass along his numbe
- **j-038** (va-084, clean)
  - completeness: expected PASS, judge said FAIL. Missing: Symptom present: new confusion, severe
  - facts judged missing: Symptom present: new confusion, severe
- **j-041** (va-008, edited: drop_education, wrong_drug)
  - calibration: expected PASS, judge said FAIL. The summary incorrectly identifies the medication as 'Lisinopril' in the Assessment section, whereas the transcript and the rest of the summary identify it as 'furosemide'.
  - change made: Removed the education item: "Advised weighing every morning and recording it, and elevating his legs."
  - change made: Changed assessment item: "Furosemide 20 mg once a day in the morning was taken; the patient thought the doctor said half a tablet but was unsure and could not find his notes." -> "Lisinopril 20 mg onc
- **j-043** (va-096, edited: wrong_number)
  - completeness: expected PASS, judge said FAIL. Missing: Medication: warfarin, 4 mg, once a day in the evening, status: taking, last dose: last night
  - facts judged missing: Medication: warfarin, 4 mg, once a day in the evening, status: taking, last dose: last night
  - change made: Changed assessment item: "Warfarin 4 mg every evening, last taken last night at seven." -> "Warfarin 8 mg every evening, last taken last night at seven."
- **j-049** (va-001, clean)
  - calibration: expected PASS, judge said FAIL. The summary states 'She appeared comfortable' as a definite fact, failing to include the caller's uncertainty ('I think').
- **j-050** (va-093, edited: fabricated_finding)
  - calibration: expected PASS, judge said FAIL. The summary includes a statement about a fall ('She also fell in the bathroom last evening') that does not appear in the transcript, and it failed to capture the caller's uncertainty regarding the skin color change.
  - change made: Added an assessment item that is not in the call: "A fall the previous evening was reported."
