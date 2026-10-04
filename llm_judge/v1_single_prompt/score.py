"""Compare the judge's verdicts with the golden labels. Standard library only.

    python3 score.py   ->  prints the agreement report and writes judge_report.md
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRICS = ("faithfulness", "completeness", "calibration")


def load(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def main():
    gold = {r["id"]: r for r in load(HERE.parent / "data" / "first_set" / "golden_labels.jsonl")}
    out = {r["id"]: r for r in load(HERE / "results" / "judge_outputs.jsonl")}
    lines = ["# Judge agreement report", ""]
    got = {}
    for i, g in gold.items():
        v = (out.get(i) or {}).get("verdicts")
        got[i] = {r: (v or {}).get(r, {}).get("verdict") for r in RUBRICS}
    unparsed = [i for i in gold if None in got[i].values()]
    lines.append(f"Items: {len(gold)} ({sum(g['edited'] for g in gold.values())} edited, {sum(not g['edited'] for g in gold.values())} clean). Unparseable or missing verdicts: {len(unparsed)}.")
    lines += ["", "## Per rubric (FAIL = the summary has this problem)", "",
              "| Rubric | Agreement | Cohen's kappa | Caught (FAIL when edited) | False alarms (FAIL when clean) |", "|---|---|---|---|---|"]
    for r in RUBRICS:
        pairs = [(g["expected"][r], got[i][r]) for i, g in gold.items() if got[i][r]]
        agree = sum(a == b for a, b in pairs)
        pos = [(a, b) for a, b in pairs if a == "FAIL"]
        neg = [(a, b) for a, b in pairs if a == "PASS"]
        caught = sum(b == "FAIL" for _, b in pos)
        fa = sum(b == "FAIL" for _, b in neg)
        lines.append(f"| {r} | {agree}/{len(pairs)} ({agree / len(pairs):.0%}) | {kappa(pairs):.2f} | {caught}/{len(pos)} | {fa}/{len(neg)} |")
    full = sum(all(got[i][r] == g["expected"][r] for r in RUBRICS) for i, g in gold.items())
    lines += ["", f"All three rubrics agree on {full}/{len(gold)} items ({full / len(gold):.0%}).", "",
              "## Detection by edit type", "", "| Edit | Expected rubric | Items | Judge failed the right rubric |", "|---|---|---|---|"]
    by = defaultdict(list)
    for i, g in gold.items():
        for k in g["edit_types"]:
            by[k].append(i)
    rub = {"drop_assessment": "completeness", "drop_education": "completeness", "drop_response": "completeness", "wrong_number": "faithfulness",
           "fabricated_finding": "faithfulness", "flipped_negative": "faithfulness", "wrong_drug": "faithfulness",
           "planned_to_completed": "calibration", "speaker_swap": "calibration", "hedge_removed": "calibration"}
    for k, ids in sorted(by.items()):
        lines.append(f"| {k} | {rub[k]} | {len(ids)} | {sum(got[i][rub[k]] == 'FAIL' for i in ids)}/{len(ids)} |")
    lines += ["", "## Disagreements", ""]
    for i, g in gold.items():
        diff = [r for r in RUBRICS if got[i][r] != g["expected"][r]]
        if diff:
            lines.append(f"- **{i}** ({g['call_id']}, {'edited: ' + ', '.join(g['edit_types']) if g['edited'] else 'clean'})")
            for r in diff:
                why = ((out.get(i) or {}).get("verdicts") or {}).get(r, {}).get("reason", "")
                lines.append(f"  - {r}: expected {g['expected'][r]}, judge said {got[i][r]}. {why}")
            for w in g["what_changed"]:
                lines.append(f"  - change made: {w[:200]}")
    (HERE / "results" / "judge_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
