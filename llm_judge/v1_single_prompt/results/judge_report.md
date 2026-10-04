# Judge agreement report

Items: 50 (25 edited, 25 clean). Unparseable or missing verdicts: 0.

## Per rubric (FAIL = the summary has this problem)

| Rubric | Agreement | Cohen's kappa | Caught (FAIL when edited) | False alarms (FAIL when clean) |
|---|---|---|---|---|
| faithfulness | 47/50 (94%) | 0.84 | 11/12 | 2/38 |
| completeness | 38/50 (76%) | 0.19 | 3/9 | 6/41 |
| calibration | 46/50 (92%) | 0.67 | 5/8 | 1/42 |

All three rubrics agree on 31/50 items (62%).

## Detection by edit type

| Edit | Expected rubric | Items | Judge failed the right rubric |
|---|---|---|---|
| drop_assessment | completeness | 4 | 2/4 |
| drop_education | completeness | 3 | 0/3 |
| drop_response | completeness | 2 | 1/2 |
| fabricated_finding | faithfulness | 3 | 3/3 |
| flipped_negative | faithfulness | 1 | 0/1 |
| hedge_removed | calibration | 1 | 0/1 |
| planned_to_completed | calibration | 4 | 3/4 |
| speaker_swap | calibration | 3 | 2/3 |
| wrong_drug | faithfulness | 3 | 3/3 |
| wrong_number | faithfulness | 5 | 5/5 |

## Disagreements

- **j-006** (va-002, clean)
  - completeness: expected PASS, judge said FAIL. The summary is missing the discussion regarding the patient's progress with exercises and the instruction to keep ice on the knee.
- **j-015** (va-009, edited: hedge_removed)
  - calibration: expected FAIL, judge said PASS. The summary correctly maintains the certainty, status, and attribution of all statements.
  - change made: Changed assessment item: "Lower back pain was estimated at 5 to 6, with the caller unsure of the exact number." -> "Lower back pain was estimated at 5 to 6."
- **j-021** (va-043, edited: planned_to_completed)
  - calibration: expected FAIL, judge said PASS. The summary correctly maintains the certainty, status, and speaker attribution for all statements.
  - change made: Changed response item: "Planned to order suction catheters, trach ties, and saline vials." -> "Completed: order suction catheters, trach ties, and saline vials."
- **j-022** (va-025, edited: drop_response)
  - completeness: expected FAIL, judge said PASS. The summary includes all clinically important content, including symptoms, medications, safety screenings, and the nurse's planned actions.
  - change made: Removed the response item: "Planned for the counselor to call her today within 2 hours."
- **j-023** (va-073, edited: drop_education)
  - completeness: expected FAIL, judge said PASS. The summary includes all clinically important information, including symptoms, vitals/weight, feeding details, and nurse instructions.
  - change made: Removed the education item: "Advised burping halfway and after feeds, keeping her upright for twenty minutes, and avoiding bouncing right after."
- **j-025** (va-100, edited: drop_education)
  - completeness: expected FAIL, judge said PASS. The summary includes all clinically important information, including the specific medication, the nature of the injuries, the reported abuse, and the nurse's plan of action.
  - change made: Removed the education item: "Advised calling 911 if the client is in immediate danger, hit or threatened, or blocked from leaving."
- **j-026** (va-006, edited: speaker_swap)
  - faithfulness: expected PASS, judge said FAIL. The summary attributes the statement 'She sounds normal. She's talking about her cat.' to the Nurse, but the Caller actually said this during the transcript.
  - change made: Changed the speaker label on "She sounded normal and spoke about her cat, without confusion." from Caller to Nurse
- **j-027** (va-086, edited: drop_assessment, wrong_number)
  - completeness: expected FAIL, judge said PASS. The summary includes all clinically important content, including the supply status, current symptoms, outage plan, and safety instructions.
  - change made: Removed the assessment item: "He was mildly short of breath on the stairs, stopping halfway, unchanged from last week."
  - change made: Changed assessment item: "Oxygen saturation on the finger clip was 93 percent." -> "Oxygen saturation on the finger clip was 83 percent."
- **j-032** (va-060, clean)
  - completeness: expected PASS, judge said FAIL. The summary is missing the discussion regarding the new rug and candles as potential triggers, and the instruction to check if the school still has the asthma action plan.
- **j-034** (va-057, edited: speaker_swap)
  - calibration: expected FAIL, judge said PASS. The summary correctly maintains the certainty, status, and attribution of all statements.
  - change made: Changed the speaker label on "She had urinary infections twice before that started with confusion." from Caller to Nurse
- **j-035** (va-077, edited: planned_to_completed)
  - faithfulness: expected PASS, judge said FAIL. The summary states the pill organizer was 'full for the rest of the week', but the caller stated it was 'full' (referring to the daughter filling it) and that Monday, Tuesday, and Wednesday were 'empty'.
  - change made: Changed response item: "Planned to message the visiting nurse that he checked in and to pass along his number." -> "Completed: message the visiting nurse that he checked in and to pass along his numbe
- **j-036** (va-064, edited: drop_assessment)
  - completeness: expected FAIL, judge said PASS. The summary includes all clinically important information, including supplies, site assessment, education, and planned actions.
  - change made: Removed the assessment item: "There was a raised pink bit of skin around the tube site, painless and not bleeding."
- **j-037** (va-097, edited: planned_to_completed)
  - completeness: expected PASS, judge said FAIL. The summary is missing the instruction to check the face against the photo on the chart before administering any medication or oxygen changes.
  - change made: Changed response item: "Planned to page the on-call clinician about the oxygen and cough." -> "Completed: page the on-call clinician about the oxygen and cough."
- **j-038** (va-084, clean)
  - completeness: expected PASS, judge said FAIL. The summary is missing the nurse's instruction to tell the dispatcher if the patient stops responding or if her breathing slows/stops.
- **j-041** (va-008, edited: drop_education, wrong_drug)
  - completeness: expected FAIL, judge said PASS. The summary includes all clinically important information, including the medication question, symptoms, nurse's instructions, and safety warnings.
  - change made: Removed the education item: "Advised weighing every morning and recording it, and elevating his legs."
  - change made: Changed assessment item: "Furosemide 20 mg once a day in the morning was taken; the patient thought the doctor said half a tablet but was unsure and could not find his notes." -> "Lisinopril 20 mg onc
- **j-043** (va-096, edited: wrong_number)
  - completeness: expected PASS, judge said FAIL. The summary is missing the history of a bleeding ulcer at Mercy hospital two years ago.
  - change made: Changed assessment item: "Warfarin 4 mg every evening, last taken last night at seven." -> "Warfarin 8 mg every evening, last taken last night at seven."
- **j-044** (va-078, clean)
  - calibration: expected PASS, judge said FAIL. The summary states the nurse 'Planned to message the clinician' as a future action, but the nurse actually stated 'I'm messaging the clinician now' (present continuous/completed action).
- **j-047** (va-013, edited: flipped_negative)
  - faithfulness: expected FAIL, judge said PASS. All statements in the summary are supported by the transcript, including the specific medication names, dosages, and the caller's reported symptoms.
  - change made: Changed assessment item: "No fever was reported; the forehead temperature was 98." -> "Fever was reported."
- **j-049** (va-001, clean)
  - completeness: expected PASS, judge said FAIL. The summary omits the caller's report regarding the high outside temperature and the malfunctioning air conditioner.
