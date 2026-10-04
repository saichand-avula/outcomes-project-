"""Demo UI and API for the clinical summarizer. No third-party packages (Python standard library only).

    python3 app/server.py                       # http://localhost:8080 ; replay mode works with no GPU
    python3 app/server.py --llm-url http://<pod>:8000/v1 --model ft3      # live mode: summarize any pasted transcript

Everything shown on the page comes from the evaluation pipeline's own code (pipeline/pl): the renderer, the rule validators V1-V16,
the automatic quote repair and the frozen judge. The model is only called in live mode; replay mode shows the saved outputs of the
base model and of the fine-tuned model (epoch 3) for the 100 validation calls.

Endpoints:  GET /                 the page
            GET /api/config       modes available, models, headline results
            GET /api/cases        the 100 validation calls (id, category, length, PASS/REVIEW/FAILED status of the saved outputs)
            GET /api/results      metrics of base and the three epochs, latency, medication error breakdown (read from pipeline/outputs)
            GET /api/case?id=...  transcript, gold summary, saved outputs of both models
            POST /api/summarize   {transcript, call_timestamp_utc?, mode: replay|live, case_id?, source: finetuned|base}
            POST /api/judge       {transcript, summary, case_id?}   (live mode; needs the base model served as the judge)
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hmac
import json
import os
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "pipeline"
sys.path.insert(0, str(PIPE))

from pl import generate as G  # noqa: E402
from pl import judge as J  # noqa: E402
from pl import medsafety as MS  # noqa: E402
from pl.repair import repair  # noqa: E402
from pl.transcript import numbered, parse  # noqa: E402
from pl.validators import validate  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
STATE: dict = {}


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def load_state(a) -> None:
    cases = read_jsonl(PIPE / "data" / "val_cases.jsonl")
    out = PIPE / "outputs"
    STATE.update(
        args=a,
        cases={c["id"]: c for c in cases},
        saved={"finetuned": {r["id"]: r for r in read_jsonl(out / a.finetuned_run / "generations.jsonl")},
               "base": {r["id"]: r for r in read_jsonl(out / a.base_run / "generations.jsonl")}},
        system_prompt=Path(a.prompt).read_text(),
        judge_prompts=J.load_prompts(),
    )
    STATE["status"], STATE["status_ready"] = {}, False

    def fill_status():  # PASS / REVIEW / FAILED of every saved output, so the example list can show it (takes ~15 s, so not before the page is up)
        for c in cases:
            st = {}
            for src in ("finetuned", "base"):
                sv = STATE["saved"][src].get(c["id"])
                if sv:
                    st[src] = analyse(sv.get("parsed"), sv.get("parse_error"), c["transcript"], c["call_timestamp_utc"])["status"]
            STATE["status"][c["id"]] = st
        STATE["status_ready"] = True
    threading.Thread(target=fill_status, daemon=True).start()
    matrix = out / f"matrix_{a.base_run}_vs_{a.finetuned_run}.json"
    STATE["headline"] = None
    if matrix.exists():
        res = json.loads(matrix.read_text())
        pick = ("G1", "G1r", "E1", "E1r", "F1", "H19", "H19r", "O1")
        STATE["headline"] = [{"system": r["system"], "rows": {m["id"]: {"name": m["name"], "value": m["value"], "num": m["num"], "den": m["den"], "note": m.get("note", "")}
                                                           for m in r["metrics"] if m["id"] in pick}} for r in res]


def results_payload() -> dict:
    """Everything the Results tab shows, read from the saved matrices (pipeline/outputs) and the medication analysis."""
    a, out = STATE["args"], PIPE / "outputs"
    systems = {}
    for f in (out / f"matrix_{a.base_run}_vs_{a.finetuned_run}.json", out / "matrix_base_v4_s2_vs_finetuned_epoch3_s2.json",
              out / "matrix_finetuned_epoch1_s2_vs_finetuned_epoch2_s2_vs_finetuned_epoch3_s2.json"):
        if f.exists():
            for r in json.loads(f.read_text()):
                systems.setdefault(r["system"], {"n": r["n"], "valid_outputs": r["valid_outputs"], "ops": r["ops"],
                                                 "metrics": {m["id"]: {k: m.get(k) for k in ("name", "value", "num", "den", "ci_low", "evidence")} for m in r["metrics"]}})
    for name, sysd in systems.items():  # a run that was not timed one call at a time borrows the timing of the same model under the earlier schema (same output lengths)
        if not sysd["ops"].get("p50") and name.endswith("_s3") and systems.get(name[:-3] + "_s2", {}).get("ops", {}).get("p50"):
            sysd["ops"] = dict(systems[name[:-3] + "_s2"]["ops"])
            sysd["ops_from"] = name[:-3] + "_s2"
    med = out / "med_errors.json"
    return {"base": a.base_run, "final": a.finetuned_run, "systems": systems, "medications": json.loads(med.read_text())["summary"] if med.exists() else {}}


def llm_alive(url: str) -> bool:
    try:
        urllib.request.urlopen(url + "/models", timeout=2).read()
        return True
    except Exception:
        return False


def _run_info(saved: dict | None) -> dict:
    """Timing to show. A saved evaluation row was generated with 16 requests at once, so its latency_s is inflated: only the one-at-a-time timings count."""
    if not saved:
        return {}
    if "concurrency" in saved:
        return {"latency_s": saved.get("latency_seq_s"), "ttft_s": saved.get("ttft_seq_s"), "completion_tokens": saved.get("completion_tokens"), "finish_reason": saved.get("finish_reason")}
    return {k: saved.get(k) for k in ("latency_s", "ttft_s", "completion_tokens", "finish_reason")}


def analyse(obj, parse_error, transcript: str, timestamp: str | None, saved: dict | None = None) -> dict:
    """Run the pipeline's checks on one model output and package everything the page shows."""
    turns = parse(transcript)
    raw = validate(obj, turns, parse_error)
    fixed, n_fixed = repair(obj, turns)
    after = validate(fixed, turns, parse_error if not isinstance(obj, dict) else None)
    net_obj, net = MS.apply(fixed, turns) if isinstance(fixed, dict) else (fixed, [])  # medication safety net: add untyped drugs, fill doses, flag absent drugs
    rendered = J.render_summary(fixed, timestamp) if isinstance(fixed, dict) and after["parse_ok"] else None
    if not raw["parse_ok"]:
        status, why = "FAILED", "the model output is not valid JSON"
    elif after["n_error"]:
        status, why = "REVIEW", f"{after['n_error']} rule error(s) remain after automatic quote repair: a nurse should check this summary"
    elif raw["n_error"]:
        status, why = "PASS", f"{n_fixed} quote(s) were repaired automatically; no rule errors remain"
    else:
        status, why = "PASS", "no rule errors"
    absent = [f["drug"] for f in net if f["rule"] == "M3"]
    if absent and status == "PASS":
        status, why = "REVIEW", f"possible omission: the caller mentioned {', '.join(absent)} but the summary does not; a nurse should check ({why})"
    fixed = net_obj
    sections = []
    if isinstance(fixed, dict):
        for name in ("assessment", "response", "education"):
            for b in fixed.get(name) or []:
                if isinstance(b, dict):
                    sections.append({"section": name, "text": b.get("text"), "speaker": b.get("speaker"), "turns": b.get("turns") or [], "quote": b.get("quote"),
                                     "facts": b.get("facts") or []})
    return {
        "status": status, "why": why, "rendered": rendered, "parsed": fixed, "bullets": sections,
        "chief_complaint": (fixed or {}).get("chief_complaint") if isinstance(fixed, dict) else None,
        "risk_flags": (fixed or {}).get("risk_flags") if isinstance(fixed, dict) else [],
        "findings_raw": raw["findings"], "findings_after_repair": after["findings"],
        "findings_net": [{"severity": f["severity"], "rule": f["rule"], "message": f["message"], "path": f["drug"]} for f in net],
        "counts": {"raw_errors": raw["n_error"], "raw_warnings": raw["n_warn"], "errors_after_repair": after["n_error"],
                   "warnings_after_repair": after["n_warn"], "quotes_repaired": n_fixed},
        "rule_flags": raw.get("rule_flags", []),
        "numbered_transcript": [{"id": t["id"], "speaker": t["speaker"], "text": t["text"]} for t in turns],
        "run": _run_info(saved),
    }


def summarize(body: dict) -> dict:
    a = STATE["args"]
    mode = body.get("mode", "replay")
    case = STATE["cases"].get(body.get("case_id") or "")
    transcript = body.get("transcript") or (case or {}).get("transcript") or ""
    if not transcript.strip():
        raise ValueError("empty transcript")
    timestamp = body.get("call_timestamp_utc") or (case or {}).get("call_timestamp_utc") or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if mode == "replay":
        source = body.get("source", "finetuned")
        saved = STATE["saved"].get(source, {}).get(case["id"] if case else "")
        if not saved:
            raise ValueError("replay mode shows saved outputs of the 100 validation calls; choose one of them, or use live mode for a new transcript")
        res = analyse(saved.get("parsed"), saved.get("parse_error"), transcript, timestamp, saved)
        res["source"] = f"saved output of the {'fine-tuned model (epoch 3)' if source == 'finetuned' else 'base model'}"
    else:
        if not llm_alive(a.llm_url):
            raise RuntimeError(f"no model server at {a.llm_url}. Start vLLM with the adapter (finetune/scripts/serve_adapters.sh) or use replay mode.")
        t0 = time.time()
        r = G.generate_one(a.llm_url, a.model, STATE["system_prompt"], {"id": "ui", "transcript": transcript}, a.max_tokens, True, stream=True)  # streamed: also gives time to first token
        r["latency_s"] = round(time.time() - t0, 2)
        res = analyse(r.get("parsed"), r.get("parse_error"), transcript, timestamp, r)
        res["source"] = f"live: model '{a.model}' at {a.llm_url}"
    res["call_timestamp_utc"] = timestamp
    if case:
        res["gold_rendered"] = J.render_summary(case["gold_target"], case["call_timestamp_utc"])
        res["category"] = (case.get("meta") or {}).get("category")
    return res


def run_judge(body: dict) -> dict:
    a = STATE["args"]
    if not llm_alive(a.llm_url):
        raise RuntimeError(f"no model server at {a.llm_url}; the judge needs the base model served as '{a.judge_model}'")
    transcript, summary = body["transcript"], body["summary"]
    case = STATE["cases"].get(body.get("case_id") or "")
    jargs = SimpleNamespace(url=a.llm_url, model=a.judge_model)
    if case and case.get("reference_checklist"):
        checklist, mode = case["reference_checklist"], "reference"
    else:
        checklist, mode = J.extract_checklist(jargs, STATE["judge_prompts"], transcript), "transcript"
    out = J.judge_one(jargs, STATE["judge_prompts"], {"id": "ui", "transcript": transcript, "call_timestamp_utc": body.get("call_timestamp_utc")}, summary, checklist, mode)
    notes = {"faithfulness": "validated on 90 hand-edited items (agreement 1.00)", "completeness": ("validated for missing nurse actions and instructions; weak for missing findings"
             if mode == "reference" else "checklist written by the model itself: NOT validated"), "calibration": "validated for planned vs completed only"}
    return {"mode": mode, "verdicts": out.get("verdicts") or out.get("partial"), "notes": notes, "items": (out.get("extra") or {}).get("items", [])}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet
        pass

    def send(self, code: int, payload, ctype="application/json"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") or ctype == "application/json" else ""))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def authorized(self) -> bool:
        """Optional shared password (HTTP Basic, any user name) when the server was started with --password."""
        pw = STATE["args"].password
        if not pw:
            return True
        try:
            given = base64.b64decode((self.headers.get("Authorization") or "").split(" ", 1)[1]).decode().split(":", 1)[1]
        except Exception:  # noqa: BLE001
            given = ""
        if hmac.compare_digest(given, pw):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Clinical Call Summarizer"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self):
        if not self.authorized():
            return
        u = urlparse(self.path)
        a = STATE["args"]
        try:
            if u.path in ("/", "/index.html"):
                return self.send(200, (STATIC / "index.html").read_bytes(), "text/html")
            if u.path == "/api/config":
                return self.send(200, {"live_available": llm_alive(a.llm_url), "llm_url": a.llm_url, "model": a.model, "judge_model": a.judge_model,
                                       "finetuned_run": a.finetuned_run, "base_run": a.base_run, "headline": STATE["headline"]})
            if u.path == "/api/status_ready":
                return self.send(200, {"ready": STATE["status_ready"]})
            if u.path == "/api/cases":
                return self.send(200, [{"id": c["id"], "category": (c.get("meta") or {}).get("category"), "length": (c.get("meta") or {}).get("length"),
                                        "noise": (c.get("meta") or {}).get("noise"), "status": STATE["status"].get(c["id"], {})} for c in STATE["cases"].values()])
            if u.path == "/api/results":
                return self.send(200, results_payload())
            if u.path == "/api/case":
                c = STATE["cases"].get(parse_qs(u.query).get("id", [""])[0])
                if not c:
                    return self.send(404, {"error": "unknown case"})
                return self.send(200, {"id": c["id"], "transcript": c["transcript"], "call_timestamp_utc": c["call_timestamp_utc"], "meta": c.get("meta")})
            return self.send(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            return self.send(500, {"error": str(e)})

    def do_POST(self):
        if not self.authorized():
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            if self.path == "/api/summarize":
                return self.send(200, summarize(body))
            if self.path == "/api/judge":
                return self.send(200, run_judge(body))
            return self.send(404, {"error": "not found"})
        except (ValueError, KeyError) as e:
            return self.send(400, {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            return self.send(502, {"error": str(e)})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to accept connections from other machines (then set --password)")
    ap.add_argument("--password", default=os.environ.get("APP_PASSWORD", ""), help="ask for this password (HTTP Basic, any user name); default none, or $APP_PASSWORD")
    ap.add_argument("--llm-url", default="http://localhost:8000/v1")
    ap.add_argument("--model", default="ft3", help="served name of the summarizer (the epoch-3 adapter)")
    ap.add_argument("--judge-model", default="gemma", help="served name of the base model, used as the judge")
    ap.add_argument("--prompt", default=str(PIPE / "prompts" / "system_v4.md"))
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--finetuned-run", default="finetuned_epoch3_s3")
    ap.add_argument("--base-run", default="base_v4_s3")
    a = ap.parse_args()
    load_state(a)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"summarizer UI on http://{a.host}:{a.port}  (replay mode ready; live mode {'ready' if llm_alive(a.llm_url) else 'needs a model server at ' + a.llm_url})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("bye")


if __name__ == "__main__":
    main()
