#!/usr/bin/env python3
"""Run the fixed Qwen3.8 pilot sequentially against an already running server.

The selected smoke modes must pass before any evaluation starts. Each evaluation is
followed by strict scoring. Resume repeats every child command so the existing
smoke/evaluation checkpoint identity checks run again; workflow status alone
never proves that model results are reusable. No server or pod is started or
stopped. --check prints the validated commands without inference or file writes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

# Script entry points normally only place scripts/ on sys.path. Keep dry runs
# from creating project bytecode caches while importing the lightweight helpers.
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_options import resolve_model_arguments
from production_state import atomic_json, file_hash, source_lock


MODES = (("off", 4096), ("medium", 16384))
DATASETS = ("eval_full", "eval_gergana")


def now():
    return datetime.now(timezone.utc).isoformat()


def plan_stages(root, run_dir, endpoint, deployment, dpi, timeout,
                thinking="both", medium_max_completion_tokens=16384):
    """Resolve shared CLI options before recording commands or contacting a server."""
    if type(dpi) is not int or dpi <= 0:
        raise ValueError("DPI must be a positive integer")
    if thinking not in ("both", "off", "medium"):
        raise ValueError("Thinking selection must be both, off or medium")
    modes = tuple((mode, medium_max_completion_tokens if mode == "medium" else cap)
                  for mode, cap in MODES if thinking == "both" or mode == thinking)
    shared = None
    for thinking, cap in modes:
        _model, _revision, inference = resolve_model_arguments(argparse.Namespace(
            backend="qwen38", model=None, revision=None, endpoint=endpoint,
            deployment=deployment, thinking=thinking, max_completion_tokens=cap,
            request_timeout=timeout))
        shared = ["--backend", "qwen38", "--endpoint", inference["endpoint"],
                  "--deployment", str(deployment), "--dpi", str(dpi),
                  "--request-timeout", str(timeout)]
    for script in ("smoke_qwen38.py", "eval_boundaries.py", "score_full.py"):
        if not (root / script).is_file():
            raise ValueError(f"Required pilot script is missing: {root / script}")
    for dataset in DATASETS:
        folder = root / dataset
        gt = json.loads((folder / "ground_truth.json").read_text())
        if (not isinstance(gt, dict) or not gt
                or any(type(name) is not str or Path(name).name != name or "\\" in name
                       or not name.lower().endswith(".pdf") for name in gt)):
            raise ValueError(f"{dataset}: expected ground-truth PDF basenames")
        if any(not (folder / name).is_file() for name in gt):
            raise ValueError(f"{dataset}: an original listed in ground truth is missing")
    stages = []
    for thinking, cap in modes:
        stage_id = "smoke-" + thinking
        command = [sys.executable, str(root / "smoke_qwen38.py"), str(root / "eval_full"),
                   *shared, "--thinking", thinking, "--max-completion-tokens", str(cap),
                   "--run-dir", str(run_dir / stage_id)]
        stages.append({"id": stage_id, "kind": "smoke", "command": command})
    for thinking, cap in modes:
        for dataset in DATASETS:
            stage_id = dataset + "-" + thinking
            stage_dir = run_dir / stage_id
            command = [sys.executable, str(root / "eval_boundaries.py"), str(root / dataset),
                       *shared, "--thinking", thinking, "--max-completion-tokens", str(cap),
                       "--tolerance", "0", "--run-dir", str(stage_dir)]
            stages.append({"id": stage_id, "kind": "evaluation", "command": command})
            command = [sys.executable, str(root / "score_full.py"), str(root / dataset),
                       str(stage_dir / "eval_results.json"), "--json", str(stage_dir / "strict_score.json")]
            stages.append({"id": stage_id + "-score", "kind": "score", "command": command})
    return stages


def workflow_identity(root, deployment, stages):
    metadata = {}
    for dataset in DATASETS:
        for name in ("ground_truth.json", "masked.json", "strata.json", "dataset.json"):
            path = root / dataset / name
            if path.is_file():
                metadata[dataset + "/" + name] = file_hash(path)
    return {"stages": stages, "runner_sha256": file_hash(Path(__file__)),
            "deployment_sha256": file_hash(deployment), "dataset_metadata_sha256": metadata}


def run_workflow(root, run_dir, stages, identity):
    """Stop on the first failure; per-stage logs retain each runner attempt."""
    marker = run_dir / "pilot_status.json"
    with source_lock(Path("qwen38_pilot_workflow"), run_dir):
        previous = json.loads(marker.read_text()) if marker.exists() else None
        if previous and (previous.get("version") != 1 or previous.get("identity") != identity):
            raise ValueError("Pilot inputs/configuration changed; use a new --run-dir")
        attempt = previous["attempt"] + 1 if previous else 1
        history = previous.get("attempt_history", []) if previous else []
        if previous:
            history = [*history, {key: previous.get(key) for key in
                       ("attempt", "status", "started_at", "finished_at", "failed_stage")}]
        log_dir = run_dir / "stage_logs" / f"attempt-{attempt:03}"
        log_dir.mkdir(parents=True, exist_ok=True)
        state = {"version": 1, "status": "running", "identity": identity, "attempt": attempt,
                 "attempt_history": history, "started_at": now(), "pid": os.getpid(),
                 "stages": [{**stage, "status": "pending"} for stage in stages],
                 "note": "Child commands validate and reuse their own checkpoints. No automatic server/pod management."}
        atomic_json(marker, state)
        active = None
        try:
            for index, active in enumerate(state["stages"], 1):
                log = log_dir / f"{index:02}-{active['id']}.log"
                active.update(status="running", started_at=now(), log=str(log))
                state["active_stage"] = active["id"]
                atomic_json(marker, state)
                print(f"[{index}/{len(stages)}] {active['id']} — {log}", flush=True)
                started = time.monotonic()
                with log.open("w", encoding="utf-8") as stream:
                    stream.write(shlex.join(active["command"]) + "\n\n")
                    stream.flush()
                    completed = subprocess.run(active["command"], cwd=root, stdout=stream,
                                               stderr=subprocess.STDOUT, check=False)
                active.update(returncode=completed.returncode, finished_at=now(),
                              elapsed_seconds=time.monotonic() - started,
                              status="complete" if completed.returncode == 0 else "failed")
                if completed.returncode != 0:
                    state.update(status="failed", failed_stage=active["id"], finished_at=now())
                    state.pop("active_stage", None)
                    atomic_json(marker, state)
                    print(f"Pilot stopped: {active['id']} exited {completed.returncode}. See {log}", file=sys.stderr, flush=True)
                    return 1
                atomic_json(marker, state)
        except (KeyboardInterrupt, Exception) as error:
            interrupted = isinstance(error, KeyboardInterrupt)
            state.update(status="interrupted" if interrupted else "failed", finished_at=now())
            if active is not None:
                active.update(status=state["status"], finished_at=now())
                state["failed_stage"] = active["id"]
            state.pop("active_stage", None)
            state["error"] = type(error).__name__ if interrupted else str(error)
            atomic_json(marker, state)
            print(f"Pilot {state['status']}. See {marker}", file=sys.stderr, flush=True)
            return 130 if interrupted else 1
        state.update(status="complete", finished_at=now())
        state.pop("active_stage", None)
        atomic_json(marker, state)
    print(f"Pilot complete: {marker}", flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=ROOT / "experiments/qwen38-pilot-20260905")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--deployment", type=Path, default=ROOT / "data/qwen38_deployment.json")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--request-timeout", type=float, default=600.0)
    parser.add_argument("--thinking", choices=("both", "off", "medium"), default="both",
                        help="Run both modes, or only the selected mode")
    parser.add_argument("--medium-max-completion-tokens", type=int, default=16384,
                        help="Medium reasoning plus final-answer allowance per query (default 16384)")
    parser.add_argument("--check", action="store_true", help="Print validated commands; no inference or file writes")
    args = parser.parse_args(argv)
    try:
        run_dir, deployment = args.run_dir.resolve(), args.deployment.resolve()
        stages = plan_stages(ROOT, run_dir, args.endpoint, deployment, args.dpi, args.request_timeout,
                             args.thinking, args.medium_max_completion_tokens)
        identity = workflow_identity(ROOT, deployment, stages)
        if args.check:
            print(f"Dry run: {len(stages)} stages; no inference or file writes.")
            for index, stage in enumerate(stages, 1):
                print(f"{index:02} {stage['id']}: {shlex.join(stage['command'])}")
            return 0
        return run_workflow(ROOT, run_dir, stages, identity)
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
