A first check found no sign of the reference item below in the clinical summary. Check again carefully before agreeing.

Read the summary one bullet at a time: the Chief Complaint, every Assessment bullet, every Response bullet and every Education bullet, with their quoted lines. The reference item is a short note; the summary may cover the same point in a full sentence, in different words, split across two bullets, or merged with other facts. If any part of the summary covers the main point of the item (which symptom, medicine, measurement, action or instruction), answer present=true. Secondary details (a reason, an example, an exact duration) do not need to be there.

Answer present=false only if you read every bullet and none of them covers the main point of the item.

Return only JSON:
{"evidence": "<copy the exact words from the summary that cover the item, or an empty string if none>",
 "present": true or false}
