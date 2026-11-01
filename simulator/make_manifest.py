"""Generate the frozen run manifest and release lock for the main experiment batch.

Usage:  python make_manifest.py

Writes experiment_manifest.csv and release_lock.json next to this file. Refuses to
overwrite either file if it already exists (no-overwrite policy); a deliberate
re-freeze must move the old files aside first.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

from simulator import PARAMETER_VERSION, SIMULATOR_VERSION, Parameters

HERE = Path(__file__).parent
MANIFEST_PATH = HERE / "experiment_manifest.csv"
LOCK_PATH = HERE / "release_lock.json"
RUNS_ROOT = "results/main/runs"

# Seeds are fixed here, before any main-batch result exists. They are disjoint from the
# calibration seeds (1-10) and shared by every group and scenario (common random numbers).
SEEDS = tuple(range(1001, 1031))

STRESS_SCENARIOS = ("gradual_decline", "sudden_shock")
# (phase label, priority, groups, scenarios)
PLAN = (
    ("core", 1, ("fixed_only", "q_only", "static_mixture", "evolving_joint"), STRESS_SCENARIOS),
    ("mechanism", 2, ("evolving_survival", "evolving_reward"), STRESS_SCENARIOS),
    (
        "reference",
        3,
        ("fixed_only", "q_only", "static_mixture", "evolving_joint", "evolving_survival", "evolving_reward"),
        ("stationary",),
    ),
)
COLUMNS = (
    "run_id",
    "phase",
    "priority",
    "group",
    "scenario",
    "seed",
    "simulator_version",
    "parameter_version",
    "parameter_hash",
    "run_dir",
    "summary_path",
    "timeseries_path",
    "events_path",
)


def normalized_sha256(path: Path) -> str:
    """SHA-256 of a text file with line endings normalized, so CRLF checkouts hash the same."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def parameter_hash(parameters: Parameters) -> str:
    canonical = json.dumps(asdict(parameters), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_id_for(scenario: str, group: str, seed: int) -> str:
    return f"{scenario}__{group}__s{seed}"


def build_rows(parameters: Parameters) -> list[dict[str, object]]:
    p_hash = parameter_hash(parameters)
    rows: list[dict[str, object]] = []
    for phase, priority, groups, scenarios in PLAN:
        for scenario in scenarios:
            for group in groups:
                for seed in SEEDS:
                    run_id = run_id_for(scenario, group, seed)
                    run_dir = f"{RUNS_ROOT}/{run_id}"
                    rows.append(
                        {
                            "run_id": run_id,
                            "phase": phase,
                            "priority": priority,
                            "group": group,
                            "scenario": scenario,
                            "seed": seed,
                            "simulator_version": SIMULATOR_VERSION,
                            "parameter_version": PARAMETER_VERSION,
                            "parameter_hash": p_hash,
                            "run_dir": run_dir,
                            "summary_path": f"{run_dir}/summary.json",
                            "timeseries_path": f"{run_dir}/timeseries.csv",
                            "events_path": f"{run_dir}/replacement_events.csv",
                        }
                    )
    return rows


def main() -> int:
    for path in (MANIFEST_PATH, LOCK_PATH):
        if path.exists():
            print(f"Refusing to overwrite existing {path.name}. Move it aside to re-freeze deliberately.")
            return 1
    parameters = Parameters()
    rows = build_rows(parameters)
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lock = {
        "simulator_version": SIMULATOR_VERSION,
        "parameter_version": PARAMETER_VERSION,
        "parameter_hash": parameter_hash(parameters),
        "parameters": asdict(parameters),
        "simulator_source_sha256": normalized_sha256(HERE / "simulator.py"),
        "manifest_sha256": normalized_sha256(MANIFEST_PATH),
        "manifest_rows": len(rows),
        "seeds": list(SEEDS),
        "python_version_at_freeze": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }
    with LOCK_PATH.open("w", encoding="utf-8") as handle:
        json.dump(lock, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"Wrote {MANIFEST_PATH.name}: {len(rows)} rows; {LOCK_PATH.name} written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
