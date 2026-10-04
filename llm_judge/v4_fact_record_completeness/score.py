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
    lines = ["# Judge agreement report (v4)", ""]
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
    lines += ["", "Earlier versions for comparison (from their reports). Note: v1-v3 judged completeness against the whole call, and",
              "the clean summaries are complete only against the fact record, so their completeness false alarms were mostly real omissions.", "",
              "| Rubric | v1 agreement / kappa / caught / false alarms | v2 | v3 |", "|---|---|---|---|",
              "| faithfulness | 94% / 0.84 / 11/12 / 2/38 | 96% / 0.89 / 12/12 / 2/36 | 96% / 0.90 / 12/12 / 2/38 |",
              "| completeness | 76% / 0.19 / 3/9 / 6/41 | 27% / 0.05 / 8/8 / 35/40 | 34% / 0.08 / 9/9 / 33/41 |",
              "| calibration | 92% / 0.67 / 5/8 / 1/42 | 90% / 0.64 / 6/8 / 3/40 | 74% / 0.34 / 6/8 / 11/42 |", ""]
    # item-level completeness against the fact record
    gc = {r["id"]: r for r in load(HERE.parent / "data" / "first_set" / "golden_completeness.jsonl")}
    tp = fn = fp = tn = 0
    wrong_items = []
    for i, g in gc.items():
        o = (out.get(i) or {}).get("extra") or {}
        if "items_checked" not in o:
            continue
        said_missing = set(o["missing_numbers"])
        truth = set(g["missing_numbers"])
        n_checked = len(o["items_checked"])
        tp += len(said_missing & truth); fn += len(truth - said_missing)
        fp += len(said_missing - truth); tn += n_checked - len(said_missing | truth)
        for n in said_missing - truth:
            wrong_items.append((i, next(c["fact"] for c in o["items_checked"] if c["n"] == n)))
    lines += ["## Completeness, item by item (each reference-record item is one question)", "",
              f"- Removed items found: {tp}/{tp + fn}",
              f"- Items wrongly called missing: {fp} of {fp + tn} items that are in the summary",
              ""]
    edited = [i for i, g in gold.items() if g["edited"] and None not in got[i].values()]
    anyflag = sum(any(v == "FAIL" for v in got[i].values()) for i in edited)
    cleanpass = [i for i, g in gold.items() if not g["edited"] and None not in got[i].values()]
    lines += ["", f"Edited summaries flagged by at least one rubric (right or wrong one): {anyflag}/{len(edited)}.",
              f"Clean summaries passed on all three rubrics: {sum(all(v == 'PASS' for v in got[i].values()) for i in cleanpass)}/{len(cleanpass)}."]
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
    if wrong_items:
        lines += ["## Items wrongly called missing (check whether the summary really lacks them)", ""] + [f"- {i}: {f}" for i, f in wrong_items] + [""]
    lines += ["", "## Disagreements", ""]
    for i, g in gold.items():
        diff = [r for r in RUBRICS if got[i][r] != g["expected"][r]]
        if diff:
            lines.append(f"- **{i}** ({g['call_id']}, {'edited: ' + ', '.join(g['edit_types']) if g['edited'] else 'clean'})")
            for r in diff:
                why = ((out.get(i) or {}).get("verdicts") or {}).get(r, {}).get("reason", "")
                lines.append(f"  - {r}: expected {g['expected'][r]}, judge said {got[i][r]}. {why}")
            if "completeness" in diff:
                miss = ((out.get(i) or {}).get("extra") or {}).get("missing")
                if miss:
                    lines.append("  - facts judged missing: " + " | ".join(miss)[:400])
            for w in g["what_changed"]:
                lines.append(f"  - change made: {w[:200]}")
    (HERE / "results" / "judge_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
