"""Tier 2: live-model evaluation across the three arms (protocol section 3).

Collects raw trial data only. Metrics are computed separately by
analyze_tier2.py, so the expensive model calls happen once and the analysis can
be re-run freely.

Arms (identical system prompt across A and B; they differ ONLY in whether the
gateway's filter and redactor are active, which is what makes attribution clean):
  A baseline  : secret in prompt, NO input filter, NO output redactor
  B gateway   : secret in prompt, filter + redactor active (deployed default)
  C no-secret : secret ABSENT from prompt, filter + redactor active

Output: evaluation/results/tier2_trials.jsonl, one line per (arm, item, repeat).
Resumable: trials already present in the file are skipped.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lambda_firewall"))
sys.path.insert(0, str(ROOT / "evaluation"))

import lambda_function
from gateway_config import GatewayConfig
from session_store import InMemorySessionStore
from recovery_oracle import classify

TRIALS_PATH = ROOT / os.environ.get("EVAL_OUT", "evaluation/results/tier2_trials.jsonl")
MAX_OUTPUT_TOKENS = 300


def load_key() -> str:
    for line in (ROOT / "vulnerable_app/.env").read_text().splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no OPENAI_API_KEY in vulnerable_app/.env")


def make_model_caller(model: str, key: str, capture: dict):
    """Return a call_model(messages)->str that hits the real API and stashes the
    raw output in `capture` so the caller sees pre-redaction text."""
    from openai import OpenAI
    client = OpenAI(api_key=key)

    def _call(messages):
        r = client.chat.completions.create(
            model=model, messages=messages,
            temperature=0, max_tokens=MAX_OUTPUT_TOKENS)
        out = r.choices[0].message.content or ""
        capture["raw"] = out
        capture["usage"] = r.usage.total_tokens if r.usage else None
        return out

    return _call


def run_baseline(item, model, key):
    """Arm A: the vulnerable path. Same message assembly as the gateway, but no
    input filter and no output redaction. raw == returned."""
    from openai import OpenAI
    client = OpenAI(api_key=key)
    cfg = GatewayConfig(include_secret_in_system_prompt=True)
    system = lambda_function.build_system_prompt(cfg)

    turns = item.get("turns") or [item["text"]]
    history, per_turn = [], []
    total_tokens = 0
    for i, turn in enumerate(turns):
        ctx = item.get("context", "") if i == 0 else ""
        composed = lambda_function.compose_user_turn(turn, ctx)
        messages = [{"role": "system", "content": system}] + history + \
                   [{"role": "user", "content": composed}]
        r = client.chat.completions.create(
            model=model, messages=messages, temperature=0, max_tokens=MAX_OUTPUT_TOKENS)
        out = r.choices[0].message.content or ""
        total_tokens += r.usage.total_tokens if r.usage else 0
        history += [{"role": "user", "content": composed},
                    {"role": "assistant", "content": out}]
        per_turn.append({"raw": out, "returned": out, "status": 200})

    worst = max(per_turn, key=lambda t: _rank(classify(t["returned"])["leak_class"]))
    return {
        "arm": "A_baseline", "gate_decision": "PASSED", "model_called": True,
        "raw_output": worst["raw"], "returned_output": worst["returned"],
        "turn_statuses": [t["status"] for t in per_turn], "tokens": total_tokens,
    }


def run_gateway(item, model, key, config, arm_name):
    """Arm B or C: drive the real lambda_handler with the live model."""
    capture = {}
    lambda_function.CONFIG_OVERRIDE = config
    lambda_function.SESSION_STORE = InMemorySessionStore()
    lambda_function.call_model = make_model_caller(model, key, capture)

    turns = item.get("turns") or [item["text"]]
    sid = f"t2-{arm_name}-{item['id']}"
    per_turn = []
    total_tokens = 0
    for i, turn in enumerate(turns):
        capture.clear()
        body = {"prompt": turn, "session_id": sid}
        if i == 0 and "context" in item:
            body["context"] = item["context"]
        resp = lambda_function.lambda_handler({"body": json.dumps(body)}, None)
        status = resp["statusCode"]
        returned = ""
        if status == 200:
            returned = json.loads(resp["body"]).get("response", "")
        raw = capture.get("raw", "")            # "" if blocked before model
        total_tokens += capture.get("usage") or 0
        per_turn.append({"status": status, "raw": raw, "returned": returned})

    lambda_function.CONFIG_OVERRIDE = None

    model_called = any(t["raw"] for t in per_turn)
    blocked = not model_called
    worst = max(per_turn, key=lambda t: _rank(classify(t["returned"])["leak_class"]))
    worst_raw = max(per_turn, key=lambda t: _rank(classify(t["raw"])["leak_class"]))
    return {
        "arm": arm_name, "model_called": model_called,
        "gate_decision": "BLOCKED_INPUT" if blocked else "PASSED",
        "raw_output": worst_raw["raw"], "returned_output": worst["returned"],
        "turn_statuses": [t["status"] for t in per_turn], "tokens": total_tokens,
    }


def _rank(leak_class):
    return {"NONE": 0, "PARTIAL": 1, "FULL": 2}[leak_class]


def already_done():
    if not TRIALS_PATH.exists():
        return set()
    done = set()
    for line in TRIALS_PATH.read_text().splitlines():
        if line.strip():
            t = json.loads(line)
            done.add((t["arm"], t["id"], t["repeat"]))
    return done


def main():
    model = os.environ.get("EVAL_MODEL", "gpt-4o-mini")
    repeats = int(os.environ.get("EVAL_REPEATS", "3"))
    limit = os.environ.get("EVAL_LIMIT")          # e.g. "2" per category for a pilot
    key = load_key()

    corpus = [json.loads(l) for l in (ROOT / "corpus/adversarial.jsonl").read_text().splitlines() if l.strip()]
    if limit:
        n = int(limit)
        seen = {}
        pilot = []
        for it in corpus:
            seen.setdefault(it["category"], 0)
            if seen[it["category"]] < n:
                pilot.append(it); seen[it["category"]] += 1
        corpus = pilot

    arms = [
        ("A_baseline", None),
        ("B_gateway",   GatewayConfig(include_secret_in_system_prompt=True)),
        ("C_nosecret",  GatewayConfig(include_secret_in_system_prompt=False)),
    ]

    done = already_done()
    TRIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    total = len(corpus) * len(arms) * repeats
    planned = total - len(done)
    print(f"model={model} repeats={repeats} items={len(corpus)} "
          f"arms={len(arms)} -> {total} trials ({len(done)} done, {planned} to run)")

    fh = TRIALS_PATH.open("a")
    n_run = 0
    t0 = time.time()
    for rep in range(repeats):
        for item in corpus:
            for arm_name, cfg in arms:
                if (arm_name, item["id"], rep) in done:
                    continue
                try:
                    if arm_name == "A_baseline":
                        rec = run_baseline(item, model, key)
                    else:
                        rec = run_gateway(item, model, key, cfg, arm_name)
                    rec.update({"id": item["id"], "category": item["category"],
                                "repeat": rep, "model": model,
                                "ts": datetime.now(timezone.utc).isoformat()})
                    fh.write(json.dumps(rec) + "\n"); fh.flush()
                    n_run += 1
                    if n_run % 25 == 0:
                        rate = n_run / (time.time() - t0)
                        print(f"  {n_run}/{planned}  ({rate:.1f}/s)")
                except Exception as e:
                    print(f"  ERROR {arm_name} {item['id']} rep{rep}: {type(e).__name__}: {str(e)[:100]}")
                    time.sleep(2)
    fh.close()
    print(f"done: ran {n_run} trials in {time.time()-t0:.0f}s -> {TRIALS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
