"""Dedicated Calibration Runner for Version D.1 (sim-4.1.0).

Executes dedicated calibration runs across Seeds 901-910 (2,000 steps).
Outputs:
1. results_v4/calibration_d1/calibration_manifest.csv
2. results_v4/calibration_d1/runs/<run_id>_records.csv
3. results_v4/calibration_d1/runs/<run_id>_summary.json
4. results_v4/calibration_d1/calibration_summary.csv

Adheres strictly to Protocol v2.0 and Checkpoint 2 governance:
- Dedicated seed range: Seeds 901-910 (no overlap with production seeds 1001-1030).
- Zero-exclusion policy: Every run retained.
- Strict thermodynamic ledger verification (< 1e-8 discrepancy).
- Atomic file writes and no-overwrite protection.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

# Ensure project root is in path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from simulator_v4.metrics import (
    compute_immediate_survival,
    compute_recovery_time,
    compute_resource_stability,
)
from simulator_v4.parameters import (
    PARAMETER_VERSION,
    SIMULATOR_VERSION,
    Parameters,
)
from simulator_v4.run_experiment import execute_single_run, generate_manifest
from simulator_v4.simulator import EcosystemSimulator, RunResult

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results_v4" / "calibration_d1"
CALIBRATION_SEEDS = tuple(range(901, 911))  # Seeds 901 to 910
DEFAULT_GROUPS = ("evolving_joint", "static_mixture")
DEFAULT_SCENARIOS = ("stationary", "sudden_shock")
DEFAULT_STEPS = 2000


def run_calibration(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    groups: tuple[str, ...] = DEFAULT_GROUPS,
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    seeds: tuple[int, ...] = CALIBRATION_SEEDS,
    steps: int = DEFAULT_STEPS,
    force_overwrite: bool = False,
) -> Path:
    """
    Executes the dedicated calibration batch and generates consolidated telemetry.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "calibration_manifest.csv"
    generate_manifest(
        groups=groups,
        scenarios=scenarios,
        seeds=seeds,
        output_path=manifest_path,
        steps=steps,
    )

    print("=" * 70)
    print("VERSION D.1 DEDICATED CALIBRATION RUNNER (sim-4.1.0 / params-v4.1)")
    print("=" * 70)
    print(f"Output Directory:    {output_dir}")
    print(f"Groups:              {groups}")
    print(f"Scenarios:           {scenarios}")
    print(f"Seeds:               {seeds[0]} - {seeds[-1]} ({len(seeds)} dedicated seeds)")
    print(f"Steps Per Run:       {steps}")
    print(f"Total Runs:          {len(groups) * len(scenarios) * len(seeds)}")
    print(f"Overwrite Allowed:   {force_overwrite}")
    print("-" * 70)

    summary_rows: list[dict[str, Any]] = []
    start_total = time.time()

    with open(manifest_path, "r") as f:
        manifest_rows = list(csv.DictReader(f))

    for idx, row in enumerate(manifest_rows, 1):
        run_id = row["run_id"]
        grp = row["group"]
        scn = row["scenario"]
        seed = int(row["seed"])

        t0 = time.time()
        print(f"[{idx:02d}/{len(manifest_rows):02d}] Running {run_id:30s} ... ", end="", flush=True)

        exec_res = execute_single_run(
            group=grp,
            scenario=scn,
            seed=seed,
            output_dir=runs_dir,
            run_id=run_id,
            steps=steps,
            force_overwrite=force_overwrite,
        )
        elapsed = time.time() - t0

        status = exec_res["status"]
        print(f"{status:16s} ({elapsed:6.2f}s)")

        # Read summary JSON to compile consolidated table
        summary_file = runs_dir / f"{run_id}_summary.json"
        if summary_file.exists():
            with open(summary_file, "r") as sf:
                s_data = json.load(sf)
            s_data["calibration_seed"] = seed
            s_data["status"] = status
            summary_rows.append(s_data)

    # Write consolidated summary CSV
    summary_csv = output_dir / "calibration_summary.csv"
    if summary_rows:
        fieldnames = list(summary_rows[0].keys())
        with open(summary_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)

    total_time = time.time() - start_total
    print("-" * 70)
    print(f"Calibration completed in {total_time:.2f} seconds.")
    print(f"Summary saved to: {summary_csv}")
    print("=" * 70)

    return summary_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Version D.1 Dedicated Calibration (Seeds 901-910)")
    parser.add_argument("--output_dir", type=str, default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="Steps per simulation run")
    parser.add_argument("--force_overwrite", action="store_true", help="Force overwrite existing runs")
    args = parser.parse_args()

    run_calibration(
        output_dir=Path(args.output_dir),
        steps=args.steps,
        force_overwrite=args.force_overwrite,
    )


if __name__ == "__main__":
    main()

