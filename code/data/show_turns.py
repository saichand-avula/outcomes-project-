"""Print a call's numbered transcript. Usage: python3 code/data/show_turns.py tr-006"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.loader import AUTHORING, parse_transcript  # noqa: E402

for cid in sys.argv[1:]:
    p = next(AUTHORING.glob(f"*/{cid}.yaml"))
    for t in parse_transcript(yaml.safe_load(p.read_text())["transcript"]):
        tags = f"   || {', '.join(t['fact_ids'])}" if t["fact_ids"] else ""
        print(f"{t['id']:3} {t['speaker'][0]}: {t['text'][:110]}{tags}")
