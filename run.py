#!/usr/bin/env python3
"""Milestone 1 entry point.

    python run.py --stock 2330 --date 20260522

Loads the immutable execution_plan, computes/validates its plan_hash,
builds runtime_state.json, and runs the VM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any, Dict

from runtime import Runtime

ROOT = os.path.dirname(os.path.abspath(__file__))
PLAN_PATH = os.path.join(ROOT, "plans", "tdcc_execution_plan.json")
CONFIG_PATH = os.path.join(ROOT, "config.json")
STATE_PATH = os.path.join(ROOT, "logs", "runtime_state.json")


def compute_plan_hash(plan: Dict[str, Any]) -> str:
    """Deterministic sha256 of the plan with plan_hash excluded."""
    clone = {k: v for k, v in plan.items() if k != "plan_hash"}
    blob = json.dumps(clone, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_inputs(plan: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    inputs: Dict[str, Any] = {}
    for name in plan.get("inputs", {}):
        inputs[name] = getattr(args, name)
    return inputs


def main() -> int:
    parser = argparse.ArgumentParser(description="TDCC crawler agent — Milestone 1")
    parser.add_argument("--stock", required=True, help="stock number, e.g. 2330")
    parser.add_argument("--date", required=True, help="data date, e.g. 20260522")
    args = parser.parse_args()

    plan = load_json(PLAN_PATH)
    config = load_json(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else {}

    # plan_hash: compute if absent, validate if present
    expected = compute_plan_hash(plan)
    if plan.get("plan_hash") in (None, "", "待實作時計算"):
        plan["plan_hash"] = expected
    elif plan["plan_hash"] != expected:
        print(f"[plan_hash mismatch] expected={expected} got={plan['plan_hash']}",
              file=sys.stderr)
        return 2
    print(f"plan_hash = {plan['plan_hash']}")

    inputs = build_inputs(plan, args)
    rt = Runtime(plan=plan, inputs=inputs, config=config, state_path=STATE_PATH)
    ok = rt.run()

    if ok:
        save_step = rt.state["steps"].get("save_output", {})
        path = save_step.get("meta", {}).get("path", "?")
        rows = save_step.get("meta", {}).get("row_count", "?")
        print(f"OK — wrote {rows} rows to {path}")
        return 0

    err = rt.state.get("error") or {}
    print(f"FAILED at step '{rt.state.get('failed_step')}' "
          f"[{err.get('code')}] {err.get('message')}", file=sys.stderr)
    print(f"see {STATE_PATH} for full runtime state", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
