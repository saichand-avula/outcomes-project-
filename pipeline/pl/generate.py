"""Generation stage (needs the GPU server): transcript -> model output.

Builds [system prompt] + [numbered transcript], asks the vLLM server for one JSON object (schema-constrained when the server
accepts the schema), and saves what came back. Nothing is interpreted here: parsing and checking happen in later stages.
Record written per call:  {id, system, raw_text, parsed (object or null), parse_error, constrained, latency_s, prompt_tokens, completion_tokens, finish_reason}
"""
from __future__ import annotations

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .schema import SUMMARY_SCHEMA
from .transcript import parse, user_message

HERE = Path(__file__).resolve().parent.parent


def _post(url, body, timeout=300):
    req = urllib.request.Request(url + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _post_stream(url, body, timeout=300):
    """Same request, streamed (server-sent events). Returns (response shaped like the non-streamed one, seconds until the first content token arrived).
    The first token is timed from just before the request is sent, so it includes the prompt processing (prefill) and the queue."""
    body = dict(body, stream=True, stream_options={"include_usage": True})
    req = urllib.request.Request(url + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0, ttft, parts, finish, usage = time.time(), None, [], None, {}
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for line in r:
            line = line.decode("utf-8", "replace").strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[5:])
            if chunk.get("usage"):
                usage = chunk["usage"]
            for ch in chunk.get("choices") or []:
                piece = (ch.get("delta") or {}).get("content")
                if piece:
                    if ttft is None:
                        ttft = time.time() - t0
                    parts.append(piece)
                finish = ch.get("finish_reason") or finish
    return {"choices": [{"message": {"content": "".join(parts)}, "finish_reason": finish}], "usage": usage}, ttft


def check_server(url, model):
    """Fail fast with a clear message if the vLLM server is not reachable or does not serve this model name."""
    try:
        with urllib.request.urlopen(url + "/models", timeout=10) as r:
            names = [m["id"] for m in json.load(r)["data"]]
    except Exception as e:
        raise SystemExit(f"cannot reach the model server at {url} ({e!r}). Start vLLM first and wait for 'Application startup complete'.")
    if model not in names:
        raise SystemExit(f"server at {url} serves {names}, not '{model}'. Pass --model with one of those names.")


def parse_json(text: str):
    """-> (object or None, error or None). Accepts a bare JSON object or one wrapped in a code fence / extra words."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):] if "{" in t else t
    try:
        return json.loads(t), None
    except json.JSONDecodeError as e:
        a, b = t.find("{"), t.rfind("}")
        if a >= 0 and b > a:
            try:
                return json.loads(t[a:b + 1]), None
            except json.JSONDecodeError:
                pass
        return None, str(e)


def generate_one(url: str, model: str, system_prompt: str, case: dict, max_tokens: int, constrained: bool = True, stream: bool = False) -> dict:
    """stream=True also records ttft_s (time to the first output token); used for the one-at-a-time latency measurements."""
    turns = parse(case["transcript"])
    body = {"model": model, "temperature": 0, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message(turns)}],
            "chat_template_kwargs": {"enable_thinking": False}}
    used_schema = False
    if constrained:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "clinical_summary", "schema": SUMMARY_SCHEMA, "strict": True}}
        used_schema = True
    ttft = None

    def send(b):
        nonlocal ttft
        if not stream:
            return _post(url, b)
        resp, ttft = _post_stream(url, b)
        return resp

    t0 = time.time()
    try:
        resp = send(body)
    except Exception as first:
        if not used_schema:
            return {"id": case["id"], "raw_text": "", "parsed": None, "parse_error": f"request failed: {first!r}", "constrained": False, "latency_s": round(time.time() - t0, 2)}
        body.pop("response_format")  # the server rejected the schema: ask for plain text and let the validators judge it
        used_schema = False
        try:
            resp = send(body)
        except Exception as e:
            return {"id": case["id"], "raw_text": "", "parsed": None, "parse_error": f"request failed: {e!r}", "constrained": False, "latency_s": round(time.time() - t0, 2)}
    dt = time.time() - t0
    ch = resp["choices"][0]
    raw = ch["message"].get("content") or ""
    obj, err = parse_json(raw)
    u = resp.get("usage", {})
    out = {"id": case["id"], "raw_text": raw, "parsed": obj, "parse_error": err, "constrained": used_schema, "latency_s": round(dt, 2),
           "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"), "finish_reason": ch.get("finish_reason")}
    if stream:
        out["ttft_s"] = None if ttft is None else round(ttft, 3)
    return out


def generate_all(cases: list[dict], url: str, model: str, system_name: str, prompt_path: Path | None = None, workers: int = 1, max_tokens: int = 6000,
                 constrained: bool = True, latency_n: int = 0) -> list[dict]:
    """workers=1: one request at a time, so every call's latency is a concurrency-1 latency.
    workers>1: much faster (the server batches requests), but latency_s is then inflated by sharing the GPU. In that case an evenly spaced
    sample of `latency_n` calls is run again one at a time and stored as latency_seq_s; the matrix reports latency from that sample only."""
    system_prompt = (prompt_path or HERE / "prompts" / "system_v1.md").read_text()
    check_server(url, model)
    rows, n = [], len(cases)

    def one(c):
        r = generate_one(url, model, system_prompt, c, max_tokens, constrained)
        print(f"  [{len(rows) + 1}/{n}] {c['id']}: {r['latency_s']}s, {r.get('completion_tokens')} tokens, "
              f"{'JSON ok' if r.get('parsed') else 'FAILED: ' + str(r.get('parse_error'))[:100]}", flush=True)
        rows.append(r)
        return r

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, cases))
    order = {c["id"]: i for i, c in enumerate(cases)}
    rows.sort(key=lambda r: order[r["id"]])
    for r in rows:
        r["system"] = system_name
        r["concurrency"] = workers
    if workers > 1 and latency_n > 0:
        step = max(1, len(cases) // latency_n)
        sample = cases[::step][:latency_n]
        by_id = {r["id"]: r for r in rows}
        print(f"  measuring latency one call at a time on {len(sample)} evenly spaced calls ...", flush=True)
        for i, c in enumerate(sample, 1):
            r = generate_one(url, model, system_prompt, c, max_tokens, constrained, stream=True)
            by_id[c["id"]]["latency_seq_s"] = r["latency_s"]
            by_id[c["id"]]["ttft_seq_s"] = r.get("ttft_s")
            print(f"  [latency {i}/{len(sample)}] {c['id']}: first token {r.get('ttft_s')}s, total {r['latency_s']}s, {r.get('completion_tokens')} tokens", flush=True)
    return rows
