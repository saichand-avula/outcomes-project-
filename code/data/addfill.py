"""Insert neutral filler exchanges into a transcript to reach a length target.
Usage: python3 addfill.py FILE N_PAIRS [SEED]
Filler holds no clinical facts, names, numbers, or drugs."""
import random, re, sys
POOL = [
 ("Hang on, let me move to the other room. It's loud in here.", "No problem, take your time."),
 ("Sorry, I just dropped my pen.", "That's all right."),
 ("Can you hear me okay? The signal's a little weak.", "I can hear you fine."),
 ("Let me grab my glasses, one second.", "Sure, I'll wait."),
 ("Sorry, the dog is barking. Hold on.", "Ha, no worries."),
 ("Okay. I'm back. What was the question?", "I'll repeat it, no trouble."),
 ("Wait, say that again? I missed the first part.", "Of course. Let me say it slower."),
 ("Sorry, I'm writing this down as we go.", "Good idea. I'll pause."),
 ("Is it okay if I put you on speaker? My hands are full.", "That's fine."),
 ("Um. Let me think. I'm trying to remember.", "Take your time, there's no rush."),
 ("Sorry, somebody's at the door. Hang on a second.", "No problem, I'll hold."),
 ("Okay. I've got a notebook now. Go ahead.", "Alright."),
 ("Sorry, I'm a little scattered today.", "That's completely understandable."),
 ("Can I ask you to hold for a moment? The kettle is going.", "Of course."),
 ("I think the line cut out for a second. Are you still there?", "Yes, I'm here."),
 ("Sorry, I lost my train of thought.", "That's okay. We were just getting started."),
 ("I appreciate you being patient with me.", "Not a problem at all."),
 ("Sorry, I keep going back and forth. It's been a long day.", "I understand. Take a breath."),
 ("One sec. My phone is making that beeping sound.", "No worries, I'll wait."),
 ("Okay. Sorry about that. Go on.", "Alright, thank you."),
]
def main():
    path, n = sys.argv[1], int(sys.argv[2])
    rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else hash(path) & 0xffff)
    lines = open(path).read().split("\n")
    s = next(i for i, l in enumerate(lines) if l.startswith("transcript:")) + 1
    e = next(i for i in range(s, len(lines)) if not lines[i].startswith("  "))
    # candidate positions: after untagged Nurse lines whose next line is Caller, excluding first 3 and last 3 lines
    cand = [i for i in range(s + 3, e - 3)
            if lines[i].startswith("  Nurse ->") and "||" not in lines[i] and lines[i + 1].startswith("  Caller ->")]
    rnd.shuffle(cand)
    picks = sorted(cand[:n], reverse=True)
    pool = POOL[:]
    rnd.shuffle(pool)
    for k, i in enumerate(picks):
        c, nu = pool[k % len(pool)]
        lines[i + 1:i + 1] = [f"  Caller -> {c}", f"  Nurse -> {nu}"]
    open(path, "w").write("\n".join(lines))
main()
