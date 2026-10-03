# Authoring conventions

Every call is one hand-written YAML file: `data/authoring/<split>/<call_id>.yaml`. Code compiles these into the JSONL files; `data/dataset_overview.xlsx` is a generated view. Nothing downstream is edited by hand.

```bash
python3 code/data/validate_gold.py      # G1–G12; must print 0 errors
python3 code/data/coverage.py           # diversity quotas
python3 code/data/dupcheck.py          # cross-split near-duplicate check
python3 code/data/realism.py            # surface statistics vs the 5 real calls
python3 code/data/compile.py            # JSONL + SFT + SHA256SUMS (refuses on validator errors)
python3 code/data/build_workbook.py    # data/dataset_overview.xlsx
```

## File layout

| Key | Content |
|---|---|
| `call_id`, `split`, `blueprint` | ID (`tr-001`…`tr-500`, `va-001`…`va-100`), split, and the one-line planned scenario |
| `setup` | Call Setup block (fact-table columns + `relationship_group`, `clinical_domains`, `distractor_meds`) |
| `chief_complaint` | Identity, pronoun, reason |
| `assessment` / `response` / `education` | Fact rows; IDs `A1…`, `R1…`, `E1…` |
| `risk_flags` | Expected flags; IDs `F1…` |
| `transcript` | One turn per line: `Nurse -> text \|\| tag1, tag2` |
| `noise_events` | `{turn, type, true_form, heard_form, fact_id}` for every authored ASR error |
| `gold` | The SFT target (summary JSON). Each bullet has `covers: [fact ids]`; this alignment is stripped from the target |

## Transcript tags

- **Turn number** = line number (1-based).
- **Tags** after ` || ` list the facts a turn expresses: `patient_name`, `patient_dob`, `caller_name`, `relationship`, `callback_phone`, `cc` (reason for call), item IDs (`A2`, `R1`, `E3`), flag IDs (`F1`).
- **`label_error`** marks a diarization error: the line's label is wrong, and the gold attributes the words to the real speaker.
- **No double-quote characters** inside speech (keeps YAML and quotes simple).

## Source-grounded value policy

See [architecture.md §3.3](../../architecture.md).

- `*_true` is the scenario's real value. `*_spoken` is what the summary must say, given only the transcript.
- **Confident single form:** as stated.
- **Hedged:** `unclear`.
- **Conflicting forms, unresolved:** most frequent form, `unclear`; ties go to the first-mentioned form.
- **Resolved inside the call** (spelling, nurse confirms from the chart in response, explicit correction): resolved form, `stated`.
- No outside medical knowledge is used to "fix" a name.

## Controlled vocabularies

| Field | Values |
|---|---|
| `scenario_category` | routine · ambiguous · asr_error · medication · supply · high_risk · not_applicable |
| `subtype` (high_risk) | uncontrolled_symptom · medication_concern · suicidal_statement · breathing_concern · escalation_request |
| `subtype` (not_applicable) | wrong_number · disconnected · billing_admin · test_silent · nonclinical_scheduling |
| `relationship_group` | self · spouse · adult_child · parent · other_family · friend_neighbor · paid_caregiver · facility_staff |
| `patient_age_group` | pediatric · 18-64 · 65-89 · 90+ |
| `agency_type` | hospice · home_health · home_care · palliative · pediatric_home_care |
| `length_bucket` (v2) | short (4,500–9,000 chars, ≥ 65 lines) · medium (7,500–12,500, ≥ 85) · long (10,500–18,000, ≥ 105); Not-Applicable calls exempt |
| `secondary_tags` | name_spelled · name_drift · dob_self_corrected · phone_from_file · phone_not_given · identity_unresolved · garbled_drug · chart_reading_distractor · prn_and_scheduled · liquid_concentration · tall_man_drug · trap_phrasing · hedging · contradiction · self_correction · negated_risk_phrase · figurative_risk_language · passive_ideation · late_answers · split_turns · crosstalk · offtopic_chatter · speaker_label_errors · multi_issue · call_center_transfer |
| `item_type` (assessment) | symptom · pertinent_negative · medication · vital · supply · history_context · caller_concern |
| `medication_status` | taking · stopped · prescribed · given_previously · given_during_call · missed · extra_dose · requested · discussed |
| `action_type` | refill_request · supply_order · message_to_team · physician_notification · on_call_page · nurse_visit · escalation_911_ed · callback · documentation · medication_instruction · delivery_coordination · appointment_scheduling · social_work_referral · pharmacy_contact |
| `action_status` | planned · completed · advised |
| `education_type` | return_precautions · medication_administration · comfort_measures · callback_plan · callback_invitation · safety · hydration_nutrition · skin_care · symptom_monitoring · emergency_instructions · equipment_use · crisis_resources |
| `risk_category` | uncontrolled_symptom · medication_concern · suicidal_statement · breathing_concern · escalation_request · other_urgent |
| noise `type` | name_drift · drug_garble · number_garble · speaker_label · dropped_words · late_answer · split_turn |

**Flag definitions:**
- **`escalation_request`:** the caller asks for urgent escalation (visit now, 911, physician), *or* the nurse escalates to 911/ED or an urgent visit.
- **`uncontrolled_symptom`:** pain ≥ 7/10, or a symptom persisting despite treatment.
- **`other_urgent`:** fall with injury, bleeding, seizure, death at home.

## Gold-writing rules (reference style)

1. **Chief Complaint.** Code renders the identity sentence. `reason` starts with a verb phrase ("Reported …", "Requested …") and ends with a period.
2. **Bullet text** is past-tense documentation with no subject: "Pain was reported…", "Planned to submit…", "Advised caller to…".
3. **Quote** = one verbatim span from the cited turns, all spoken by `speaker`. Speaker labels are `Caller` or `Nurse` only; the patient speaking as the caller is `Caller`.
4. **Explanation** = one sentence starting "Documents …".
5. **Planned actions** need planned wording ("Planned to…", "would…"). **Completed** actions only on completion cues ("I've sent", "I already put in").
6. **Uncertain values** are worded in the text, e.g. "(unclear; heard as X and Y)" or "caller was unsure whether…".
7. **Every number** in text or facts must be derivable from the bullet's evidence turns: its cited turns plus the turns tagged with the facts it covers.
8. **Drug names in plain case;** the renderer applies tall-man lettering.
9. **Name the drug in the tagged turn.** For a `medication_instruction` action (or any medication item), the turn(s) tagged with that item must contain the drug's spoken name; tag the nurse's chart-reading and confirming turns too.
10. **Use `turns: auto`** in the gold section and run `python3 code/data/fill_turns.py` (or `postfix.py`); it fills turn numbers from the quote and the turn tags. Noise events can use `turn: auto` with a `heard_form` snippet. Avoid commas inside values in `{...}` fact lines (use a separate field or reword).
11. **Chart-reading meds the caller does not discuss** go in `setup.distractor_meds` and stay out of the summary.
