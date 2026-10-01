"""Measure ASR/conversation noise statistics on the 5 real transcripts -> data/calibration.json.
These anchor the noise profiles in asr_noise.py. n=5 calls, so rates are coarse anchors, not estimates."""
import json, re, yaml
from pathlib import Path
from transcript_utils import split_turns, tokens

HERE = Path(__file__).parent
FILLERS = {"um", "uh", "hmm", "mhm", "ah", "oh", "okay", "uh huh"}
DANGLING = {"and", "the", "to", "of", "a", "so", "but", "i", "he", "she", "that", "for", "with", "is", "or", "in", "on", "my", "his", "her", "if", "because"}
NUMWORDS = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand oh".split())


def stats(transcripts: list[str]) -> dict:
    n_tok = n_turn = n_fill = n_rep = n_same = n_short = n_frag = n_numw = n_numd = n_spell = n_caller = 0
    inaud = 0
    for t in transcripts:
        turns = split_turns(t)
        for i, tr in enumerate(turns):
            tk = tokens(tr.text); n_tok += len(tk); n_turn += 1
            inaud += len(re.findall(r"\[(inaudible|unintelligible|crosstalk)\]", tr.text, re.I))
            n_fill += sum(1 for w in tk if w in {"um", "uh", "hmm", "mhm", "ah"})
            n_rep += sum(1 for a, b in zip(tk, tk[1:]) if a == b and a not in {"no", "okay", "yes", "bye", "thank", "ha"})
            if i and turns[i - 1].speaker == tr.speaker: n_same += 1
            if tr.speaker == "Caller":
                n_caller += 1
                if len(tk) <= 3: n_short += 1
                if tk and tr.text.strip().endswith(".") and tk[-1] in DANGLING: n_frag += 1
            n_numw += sum(1 for w in tk if w in NUMWORDS and w != "oh")
            n_numd += sum(1 for w in tk if w.isdigit())
            run = 0
            for raw in tr.text.replace(",", " ").split():
                if re.fullmatch(r"[A-Za-z][.,-]?", raw): run += 1
                else:
                    n_spell += run >= 4; run = 0
            n_spell += run >= 4
    return dict(n_transcripts=len(transcripts), n_turns=n_turn, n_tokens=n_tok,
                filler_per_1k_tokens=round(1000 * n_fill / n_tok, 1), immediate_repeat_per_1k_tokens=round(1000 * n_rep / n_tok, 1),
                same_speaker_consecutive_turn_rate=round(n_same / n_turn, 3), caller_turns_le3_words_rate=round(n_short / n_caller, 3),
                caller_dangling_fragment_rate=round(n_frag / n_caller, 3), spoken_number_words_per_1k_tokens=round(1000 * n_numw / n_tok, 1),
                digit_tokens_per_1k_tokens=round(1000 * n_numd / n_tok, 1), spelled_letter_runs=n_spell, inaudible_tokens=inaud,
                # hand-counted from the 5 calls (see gold_real5.py notes): calls with >=1 ...
                hand_counts=dict(calls_with_name_variants="4/5 (ex2 Miles/Mile/Myles; ex3 Nadine/Noreen/Nora; ex4 Owen/Olivia; ex5 Naomi Mercer/Marlowe)",
                                 calls_with_garbled_drug_name="4/5 (ex1 Phalarisipham; ex2 Ampatripoline/tamifluoln/Metroforum; ex3 carfentanil; ex5 ibuprofen)",
                                 calls_with_dob_garble_or_self_correction="2/5 (ex4 'eighty three' then 'nineteen thirty-three'; ex5 'ten eight of eighteen two thousand eighteen')",
                                 calls_with_nurse_speech_ahead_of_caller_answer=">=2/5 (ex1 T3 confirms the DOB before the caller's answer turn; ex3 T2 'Thank you' before the name turn)"))


if __name__ == "__main__":
    d = yaml.safe_load(open(HERE / "data/raw/real5_examples.yaml"))["examples"]
    s = stats([e["input_transcript"] for e in d])
    (HERE / "data/calibration.json").write_text(json.dumps(s, indent=1)); print(json.dumps(s, indent=1))
