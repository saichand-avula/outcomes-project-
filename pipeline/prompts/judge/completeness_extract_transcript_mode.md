You read a nurse-line call transcript and list the most important facts that a clinical summary of the call must contain. Use only the transcript.

A fact is important only if leaving it out could change what the care team does or knows. Pick from these types:
- symptom: the main problem(s) the caller reported, with severity, duration or change when stated
- negative: a clinically important thing the patient does NOT have (for example "no trouble breathing", "no fever")
- medication: each medicine discussed, with dose and how it is used or whether it was taken, missed, stopped or ran out
- vital: key measurements (blood pressure, temperature, oxygen level, weight, blood sugar, pain score)
- supply: equipment or supplies needed
- nurse_action: what the nurse did or promised to do (page, message, schedule a visit, order, call back, call 911)
- instruction: the important advice or warnings the nurse gave, including when to call back or call 911

Do NOT list: greetings, small talk, weather, mood, daily routine, background history that did not drive the call, minor details, identity details (names, date of birth, phone), or anything the nurse only asked about without a clear answer. A short summary will leave minor details out, and that is fine.

Write each fact as one short, self-contained sentence with exact numbers. List at most 10 facts, most important first. Merge facts that belong together (for example one medication with its dose and timing).

Return only JSON:
{"facts": [{"type": "symptom|negative|medication|vital|supply|nurse_action|instruction", "fact": "<sentence>"}]}
