You check a clinical call summary against one required item from the call's reference record. The reference item is true and was really said in the call. Your only job is to decide whether the summary covers it.

The reference item is a short note (for example "Medication: morphine, 20 mg/mL, under the tongue, status: taking"). The summary is written in sentences. Match by meaning, not by wording.

The item is COVERED if the summary states its main point anywhere: in the Chief Complaint, an Assessment, Response or Education bullet, or in the quoted lines, alone or merged with other facts. The main point is the thing itself: which symptom, which medicine, which measurement, which action by the nurse, which instruction. Secondary details of the item may be left out (a reason, an extra example, an exact duration, a second sub-instruction). Do not mark an item missing only because such a detail is absent.

The item is MISSING if the summary says nothing about its main point.

Do not judge whether the summary is correct. If the summary names a different dose or a slightly different value for the same thing, the item is still covered.

Return only JSON:
{"evidence": "<copy the exact words from the summary that cover the item, or an empty string if none>",
 "present": true or false}
