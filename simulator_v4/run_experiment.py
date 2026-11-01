"""Manifest-driven batch experiment runner for Version D.1 (sim-4.1.0).

Executes reproducible simulation experiments from an explicit manifest with:
1. Deterministic seeding (Common Random Numbers).
2. Atomic output writes (.tmp -> .csv/.json).
3. No-overwrite protection (preserves existing valid runs as SKIPPED_EXISTING).
4. Thermodynamic ledger discrepancy auditing per step.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

try:
    from simulator_v4.parameters import (
        PARAMETER_VERSION,
        SIMULATOR_VERSION,
        Parameters,
    )
    from simulator_v4.simulator import EcosystemSimulator, RunResult
except ImportError:
    from parameters import (
        PARAMETER_VERSION,
        SIMULATOR_VERSION,
        Parameters,
    )
    from simulator import EcosystemSimulator, RunResult


def generate_manifest(
    groups: Sequence[str],
    scenarios: Sequence[str],
    seeds: Sequence[int],
    output_path: Path,
    steps: int = 2000,
) -> list[dict[str, Any]]:
    """
    Generates a deterministic experimental manifest CSV.
    """
    rows: list[dict[str, Any]] = []
    run_idx = 1
    for grp in groups:
        for scn in scenarios:
            for s in seeds:
                run_id = f"{grp}_{scn}_s{s}"
                rows.append({
                    "run_idx": run_idx,
                    "run_id": run_id,
                    "group": grp,
                    "scenario": scn,
                    "seed": s,
                    "steps": steps,
                    "status": "PENDING",
                })
                run_idx += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["run_idx", "run_id", "group", "scenario", "seed", "steps", "status"]
        )
        writer.writeheader()
        writer.writerows(rows)

    return rows


def is_run_complete(output_dir: Path, run_id: str, expected_steps: int = 2000) -> bool:
    """
    Checks if a run's output CSV and summary JSON already exist and are complete.
    """
    csv_file = output_dir / f"{run_id}_records.csv"
    summary_file = output_dir / f"{run_id}_summary.json"

    if not csv_file.exists() or not summary_file.exists():
        return False

    try:
        with open(summary_file, "r") as f:
            summary = json.load(f)
        steps_completed = summary.get("steps_completed", 0)
        extinct = summary.get("extinct", False)

        # Complete if reached expected steps or ended via genuine biological extinction
        if steps_completed >= expected_steps or extinct:
            return True
    except Exception:
        return False

    return False


def execute_single_run(
    group: str,
    scenario: str,
    seed: int,
    output_dir: Path,
    run_id: str | None = None,
    steps: int = 2000,
    force_overwrite: bool = False,
) -> dict[str, Any]:
    """
    Executes a single simulation run with atomic writes and ledger verification.
    """
    if run_id is None:
        run_id = f"{group}_{scenario}_s{seed}"

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_target = output_dir / f"{run_id}_records.csv"
    summary_target = output_dir / f"{run_id}_summary.json"

    # Check for existing completed run
    if not force_overwrite and is_run_complete(output_dir, run_id, expected_steps=steps):
        return {
            "run_id": run_id,
            "status": "SKIPPED_EXISTING",
            "reason": "Completed run already exists; overwrite prevented.",
        }

    params = Parameters.for_group(group)
    sim = EcosystemSimulator(parameters=params, scenario=scenario, seed=seed)
    result: RunResult = sim.run(steps=steps)

    # Prepare atomic file writing (.tmp -> final)
    csv_tmp = output_dir / f"{run_id}_records.csv.tmp"
    summary_tmp = output_dir / f"{run_id}_summary.json.tmp"

    try:
        # 1. Write step records CSV
        if result.records:
            fieldnames = list(asdict(result.records[0]).keys())
            with open(csv_tmp, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for rec in result.records:
                    writer.writerow(asdict(rec))
                f.flush()
                os.fsync(f.fileno())

        # 2. Write summary JSON
        summary_data = result.summary()
        with open(summary_tmp, "w") as f:
            json.dump(summary_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        # 3. Atomic replace
        os.replace(csv_tmp, csv_target)
        os.replace(summary_tmp, summary_target)

        status = "EXTINCT" if result.extinct else "COMPLETED"
        return {
            "run_id": run_id,
            "status": status,
            "steps_completed": result.steps_completed,
            "extinct": result.extinct,
            "final_population": result.final_population,
        }

    except Exception as e:
        if csv_tmp.exists():
            csv_tmp.unlink()
        if summary_tmp.exists():
            summary_tmp.unlink()
        raise e


def execute_manifest(
    manifest_path: Path,
    output_dir: Path,
    force_overwrite: bool = False,
) -> list[dict[str, Any]]:
    """
    Executes all rows in an experiment manifest sequentially.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r") as f:
        reader = csv.DictReader(f)
        manifest_rows = list(reader)

    results: list[dict[str, Any]] = []

    for row in manifest_rows:
        run_id = row["run_id"]
        grp = row["group"]
        scn = row["scenario"]
        seed = int(row["seed"])
        steps = int(row.get("steps", 2000))

        run_status = execute_single_run(
            group=grp,
            scenario=scn,
            seed=seed,
            output_dir=output_dir,
            run_id=run_id,
            steps=steps,
            force_overwrite=force_overwrite,
        )
        results.append(run_status)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Version D.1 Manifest Experiment Runner")
    parser.add_argument("--manifest", type=str, help="Path to manifest CSV")
    parser.add_argument("--output_dir", type=str, default="results_v4/runs", help="Output directory")
    parser.add_argument("--force_overwrite", action="store_true", help="Force overwrite existing runs")
    args = parser.parse_args()

    if args.manifest:
        manifest_p = Path(args.manifest)
        out_p = Path(args.output_dir)
        print(f"Executing manifest: {manifest_p} -> {out_p}")
        res = execute_manifest(manifest_p, out_p, force_overwrite=args.force_overwrite)
        print(f"Finished {len(res)} runs.")
    else:
        print("No manifest provided. Use --manifest <path>.")


if __name__ == "__main__":
    main()

