"""Turn an SFT row into token ids and labels, exactly as the model sees it at serving time.

Serving (pipeline/pl/generate.py) sends: system = prompts/system_v4.md, user = user_message(transcript), chat template with enable_thinking=False,
then lets the model write the JSON. So training uses the same template, with the generation prompt as the input and
`compact JSON + whatever the template puts after an assistant message` as the target. Only the target tokens carry loss.
"""
from __future__ import annotations

import json

from textio import parse, user_message

MARK = "␟TARGET␟"  # a marker that cannot occur in the data, used to find where the template puts the assistant text


def target_text(target: dict) -> str:
    return json.dumps(target, ensure_ascii=False, separators=(",", ":"))


def messages(system: str, transcript: str) -> list[dict]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user_message(parse(transcript))}]


def render_parts(tok, system: str, transcript: str):
    """-> (prompt_text, suffix_text): the text the server feeds the model, and the end-of-turn text the template puts after an assistant message."""
    base = messages(system, transcript)
    prompt = tok.apply_chat_template(base, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    full = tok.apply_chat_template(base + [{"role": "assistant", "content": MARK}], tokenize=False, enable_thinking=False)
    i = full.find(MARK)
    if i < 0:
        raise SystemExit("the chat template did not render the assistant message; run check_setup.py and inspect the chat template it prints")
    head, suffix = full[:i], full[i + len(MARK):]
    if not prompt.startswith(head):
        raise SystemExit("MISMATCH between the generation prompt and the start of a rendered assistant turn.\n"
                         f"generation prompt tail : {prompt[-160:]!r}\nassistant turn head tail: {head[-160:]!r}\n"
                         "The training sequence would not match what vLLM feeds the model. Run check_setup.py and inspect the chat template it prints.")
    # With thinking off the generation prompt may carry more than a plain assistant turn (Gemma adds an empty thought block); the model writes
    # the JSON right after it, so training uses the generation prompt as the input. The text after the assistant message ends at the stop token.
    suffix = suffix.rstrip("\n")
    return prompt, suffix


def encode(tok, system: str, row: dict, max_len: int) -> dict:
    prompt, suffix = render_parts(tok, system, row["transcript"])
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    c_ids = tok(target_text(row["target"]) + suffix, add_special_tokens=False)["input_ids"]
    n = len(p_ids) + len(c_ids)
    if n > max_len:
        raise SystemExit(f"{row['id']}: {n} tokens exceed max_length {max_len}; training would truncate the target. Raise max_length.")
    return {"id": row["id"], "input_ids": p_ids + c_ids, "n_prompt": len(p_ids), "n_target": len(c_ids)}
