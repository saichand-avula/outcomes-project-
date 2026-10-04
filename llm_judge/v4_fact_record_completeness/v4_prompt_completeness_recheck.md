A first check found no sign of the reference item below in the clinical summary. Check again carefully before agreeing.

Read the summary one bullet at a time: the Chief Complaint, every Assessment bullet, every Response bullet and every Education bullet, with their quoted lines. The reference item is a short note; the summary may state the same content in a full sentence, in different words, split across two bullets, or merged with other facts. If any part of the summary states the content of the item, including all its key details, answer present=true.

Answer present=false only if you read every bullet and none of them states the item, or a key detail (number, dose, time, name, warning) is left out.

Return only JSON:
{"evidence": "<copy the exact words from the summary that contain the item, or an empty string if none>",
 "present": true or false}
