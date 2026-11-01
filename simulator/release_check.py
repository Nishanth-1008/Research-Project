"""One-command pre-batch release check (Phase 1 acceptance gate).

Usage:  python release_check.py

1. Verifies simulator, parameters, and manifest still match release_lock.json.
2. Runs the mechanics tests (test_simulator.py) and the release-machinery tests (test_runner.py).
3. Runs the determinism check (one seed from every group x scenario cell, each run twice) in two
   separate interpreter processes with different PYTHONHASHSEED values and compares the digests.
4. Saves everything to results/release/release_check_log.txt (any earlier log is moved aside, not deleted).

Exit code 0 means the release candidate is ready for the main batch.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

from run_experiments import check_freeze, load_lock, preserve_existing, utc_stamp
from simulator import PARAMETER_VERSION, SIMULATOR_VERSION, Parameters

HERE = Path(__file__).parent
LOG_DIR = HERE / "results" / "release"


def run(command: list[str], extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    env = {**os.environ, **(extra_env or {})}
    completed = subprocess.run(command, cwd=HERE, env=env, capture_output=True, text=True)
    return completed.returncode, completed.stdout + completed.stderr


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "release_check_log.txt"
    preserve_existing(log_path)
    lines: list[str] = []
    ok = True

    def emit(text: str = "") -> None:
        print(text)
        lines.append(text)

    lock = load_lock()
    emit("RELEASE CHECK")
    emit(f"utc: {utc_stamp()}")
    emit(f"python: {platform.python_version()} ({platform.python_implementation()}) on {platform.platform()}")
    emit(f"simulator_version: {SIMULATOR_VERSION}")
    emit(f"parameter_version: {PARAMETER_VERSION}")
    emit(f"parameter_hash: {lock['parameter_hash']}")
    emit(f"simulator_source_sha256: {lock['simulator_source_sha256']}")
    emit(f"manifest_sha256: {lock['manifest_sha256']} ({lock['manifest_rows']} rows)")
    emit()

    emit("== 1. Freeze check ==")
    problems = check_freeze(Parameters())
    emit("PASS: simulator, parameters, and manifest match release_lock.json" if not problems else "FAIL:\n  " + "\n  ".join(problems))
    ok &= not problems
    emit()

    for title, module in (("2a. Mechanics tests (test_simulator.py)", "test_simulator"), ("2b. Release-machinery tests (test_runner.py)", "test_runner")):
        emit(f"== {title} ==")
        code, output = run([sys.executable, "-m", "unittest", "-v", module])
        emit(output.rstrip())
        emit(f"RESULT: {'PASS' if code == 0 else 'FAIL'}")
        ok &= code == 0
        emit()

    emit("== 3. Determinism check (each sampled run executed twice per process; two processes) ==")
    outputs: list[str] = []
    for hash_seed in ("1", "2"):
        code, output = run([sys.executable, "run_experiments.py", "--verify-determinism"], {"PYTHONHASHSEED": hash_seed})
        emit(f"-- process with PYTHONHASHSEED={hash_seed} --")
        emit(output.rstrip())
        outputs.append(output)
        ok &= code == 0
    same_across_processes = outputs[0] == outputs[1]
    emit(f"Digests identical across the two processes: {'YES' if same_across_processes else 'NO'}")
    ok &= same_across_processes
    emit()

    emit("OVERALL: " + ("READY FOR MAIN BATCH" if ok else "NOT READY"))
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nLog saved to {log_path.relative_to(HERE)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
