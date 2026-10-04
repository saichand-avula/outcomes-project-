"""Send every item in judge_inputs.jsonl to a Gemma server (OpenAI-compatible, e.g. vLLM) and save the verdicts.

Standard library only. Run on the pod after starting the server (see README.md):
    python3 run_judge.py [--url http://localhost:8000/v1] [--model gemma] [--out judge_outputs.jsonl]
"""
import argparse
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRICS = ("faithfulness", "completeness", "calibration")
SCHEMA = {"type": "object", "required": list(RUBRICS), "additionalProperties": False, "properties": {
    r: {"type": "object", "required": ["verdict", "reason"], "additionalProperties": False,
        "properties": {"verdict": {"type": "string", "enum": ["PASS", "FAIL"]}, "reason": {"type": "string"}}}
    for r in RUBRICS}}


def post(url, body):
    req = urllib.request.Request(url + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def judge_one(args, system, item):
    user = f"TRANSCRIPT\n{item['transcript']}\n\nSUMMARY\n{item['summary']}"
    body = {"model": args.model, "temperature": 0, "max_tokens": 700,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {"type": "json_schema", "json_schema": {"name": "verdicts", "schema": SCHEMA, "strict": True}}}
    t0 = time.time()
    try:
        resp = post(args.url, body)
    except Exception as e:  # server without json_schema support: retry unconstrained
        body.pop("response_format")
        resp = post(args.url, body)
    text = resp["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", text, re.S)
    try:
        parsed = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        parsed = None
    return {"id": item["id"], "raw": text, "verdicts": parsed, "seconds": round(time.time() - t0, 2),
            "completion_tokens": resp.get("usage", {}).get("completion_tokens")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000/v1")
    ap.add_argument("--model", default="gemma")
    ap.add_argument("--inputs", default=str(HERE.parent / "data" / "first_set" / "judge_inputs.jsonl"))
    ap.add_argument("--prompt", default=str(HERE / "judge_system_prompt.md"))
    ap.add_argument("--out", default=str(HERE / "results" / "judge_outputs.jsonl"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    system = Path(args.prompt).read_text()
    items = [json.loads(l) for l in Path(args.inputs).read_text().splitlines() if l.strip()]
    with ThreadPoolExecutor(args.workers) as ex:
        rows = list(ex.map(lambda it: judge_one(args, system, it), items))
    Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    bad = sum(r["verdicts"] is None for r in rows)
    print(f"judged {len(rows)} items -> {args.out} ({bad} unparseable)")


if __name__ == "__main__":
    main()
