"""Stratified SFT batch schedule: which calls form each optimizer step, per epoch.

Micro-batch = 1 call, gradient accumulation = 8, so one optimizer step = 8 calls (the last step of an
epoch holds the remaining 500 mod 8 = 4). Rules for every full step (architecture.md §4.1):
  * length mix follows the split mix (72/12/16) by cumulative largest-remainder rounding, so
    every step has about 6 short + 1 medium + 1 long and long calls are never clumped together;
  * no primary category appears more than 3 times in a step, and Not-Applicable at most 2 times;
  * order inside a step is irrelevant (gradients are summed); the order of steps and the choice of
    calls are reshuffled every epoch (seed + epoch), so each epoch sees different batches.

Run: python3 code/train/batching.py [--epochs 3] [--seed 42]   -> data/sft/batch_schedule.json + stats
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import ROOT, load_split  # noqa: E402

STEP = 8
CAT_CAP, NA_CAP = 3, 2
LENGTHS = ("short", "medium", "long")


def length_counts(n_total: int, pool_sizes: dict[str, int], step: int = STEP) -> list[dict[str, int]]:
    """Per-step length quota using cumulative rounding so totals match the pools exactly."""
    steps, done = [], {k: 0 for k in LENGTHS}
    n_steps = -(-n_total // step)
    for i in range(n_steps):
        size = min(step, n_total - i * step)
        taken = sum(done.values()) + size
        want = {k: pool_sizes[k] * taken / n_total for k in LENGTHS}
        cnt = {k: int(want[k]) - done[k] for k in LENGTHS}
        cnt = {k: max(v, 0) for k, v in cnt.items()}
        while sum(cnt.values()) < size:  # give the remainder to the length furthest below its target
            k = max(LENGTHS, key=lambda x: want[x] - done[x] - cnt[x] if done[x] + cnt[x] < pool_sizes[x] else -9)
            cnt[k] += 1
        while sum(cnt.values()) > size:
            k = max(LENGTHS, key=lambda x: cnt[x])
            cnt[k] -= 1
        for k in LENGTHS:
            done[k] += cnt[k]
        steps.append(cnt)
    return steps


def make_epoch(calls: list[dict], epoch: int, seed: int = 42) -> list[list[str]]:
    info = {c["call_id"]: (c["setup"]["length_bucket"], c["setup"]["scenario_category"]) for c in calls}
    pool_sizes = Counter(v[0] for v in info.values())
    quota = length_counts(len(calls), pool_sizes)
    for attempt in range(500):
        rng = random.Random(f"{seed}-{epoch}-{attempt}")
        pools = {k: [i for i, v in info.items() if v[0] == k] for k in LENGTHS}
        for p in pools.values():
            rng.shuffle(p)
        order = list(range(len(quota)))
        rng.shuffle(order)  # which steps get the (possibly smaller) last quota is also shuffled
        steps, ok = [], True
        for qi in order:
            cnt = quota[qi]
            chosen: list[str] = []
            for k in LENGTHS:
                for _ in range(cnt[k]):
                    cats = Counter(info[c][1] for c in chosen)
                    pick = next((c for c in pools[k] if cats[info[c][1]] < CAT_CAP
                                 and (info[c][1] != "not_applicable" or cats["not_applicable"] < NA_CAP)), None)
                    if pick is None:
                        ok = False
                        break
                    pools[k].remove(pick)
                    chosen.append(pick)
                if not ok:
                    break
            if not ok:
                break
            rng.shuffle(chosen)
            steps.append(chosen)
        if ok:
            return steps
    raise RuntimeError("could not satisfy batching rules")


def main(argv: list[str]) -> int:
    epochs = int(argv[argv.index("--epochs") + 1]) if "--epochs" in argv else 3
    seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 42
    calls = load_split("train")
    info = {c["call_id"]: c["setup"] for c in calls}
    schedule = {}
    for e in range(1, epochs + 1):
        steps = make_epoch(calls, e, seed)
        assert sorted(i for s in steps for i in s) == sorted(info), "every call exactly once per epoch"
        schedule[f"epoch_{e}"] = steps
        full = [s for s in steps if len(s) == STEP]
        lens = Counter(tuple(Counter(info[i]["length_bucket"] for i in s)[k] for k in LENGTHS) for s in full)
        worst_cat = max(Counter(info[i]["scenario_category"] for i in s).most_common(1)[0][1] for s in steps)
        small = [len(s) for s in steps if len(s) != STEP]
        print(f"epoch {e}: {len(steps)} steps ({len(full)} of {STEP}, short step sizes {small}); "
              f"(short, medium, long) mixes {dict(lens.most_common(4))}; max same category per step {worst_cat}")
    out = ROOT / "data" / "sft" / "batch_schedule.json"
    out.write_text(json.dumps({"seed": seed, "step_size": STEP, "rules": {"category_cap": CAT_CAP, "not_applicable_cap": NA_CAP}, **schedule}))
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
