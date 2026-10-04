"""Shared helpers for the judge runners: one constrained-JSON call to an OpenAI-compatible server (for example vLLM).

Standard library only. The call is greedy (temperature 0) with thinking off, asks for the JSON schema when the server
supports it, and retries up to 3 times (the last try is unconstrained with a larger token limit).
"""
import json
import re
import urllib.request

VERDICT = {"type": "object", "required": ["analysis", "verdict", "reason"], "additionalProperties": False, "properties": {
    "analysis": {"type": "string"}, "verdict": {"type": "string", "enum": ["PASS", "FAIL"]}, "reason": {"type": "string"}}}
CHECK = {"type": "object", "required": ["evidence", "present"], "additionalProperties": False,
         "properties": {"evidence": {"type": "string"}, "present": {"type": "boolean"}}}


def post(url, body):
    req = urllib.request.Request(url + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


def ask(args, system, user, schema, max_tokens, tries=3):
    """Constrained JSON call with retries; returns a dict or None. `args` needs .url and .model."""
    for attempt in range(tries):
        body = {"model": args.model, "temperature": 0, "max_tokens": max_tokens * (1 + attempt),
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "chat_template_kwargs": {"enable_thinking": False}}
        if attempt < tries - 1:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "out", "schema": schema, "strict": True}}
        try:
            text = post(args.url, body)["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", text, re.S)
            return json.loads(m.group(0))
        except Exception:
            continue
    return None
