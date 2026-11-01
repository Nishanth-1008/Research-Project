"""Manifest-driven batch runner for the main experiment.

One manifest row = one simulation = one directory of outputs:

    results/main/runs/<run_id>/summary.json
                              /timeseries.csv
                              /replacement_events.csv

Examples
--------
    python run_experiments.py --dry-run                 # show what would run
    python run_experiments.py --phase core              # Phase 2 core batch (240 runs)
    python run_experiments.py --phase mechanism         # Phase 3 ablations (120 runs)
    python run_experiments.py --phase reference         # stationary references (180 runs)
    python run_experiments.py                           # everything not yet complete (540 runs)
    python run_experiments.py --verify-determinism      # run a sample twice, compare bytes
    python run_experiments.py --aggregate               # build summary_all.csv + status report

Safety rules (see REPRODUCIBILITY.md)
-------------------------------------
* The runner refuses to start if simulator source, parameters, or manifest differ from
  release_lock.json.
* A completed run directory is never overwritten or deleted; re-running skips it.
* Interrupted or failed runs are preserved under explicit INCOMPLETE-/FAILED- names.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import tempfile
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from make_manifest import LOCK_PATH, MANIFEST_PATH, SEEDS, normalized_sha256, parameter_hash
from simulator import PARAMETER_VERSION, SIMULATOR_VERSION, EcosystemSimulator, Parameters, RunResult

HERE = Path(__file__).parent
DEFAULT_RESULTS_ROOT = HERE / "results" / "main"

TIMESERIES_COLUMNS = (
    "step",
    "resource",
    "total_harvest",
    "living_population",
    "q_learning_share",
    "mean_reward",
    "mean_energy",
)
EVENT_COLUMNS = (
    "step",
    "agent_id",
    "agent_type",
    "age",
    "lifetime_reward",
    "survival_score",
    "reward_score",
    "fitness",
    "offspring_selected",
)


# --------------------------------------------------------------------------- helpers
def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_path(path: Path) -> Path:
    """Return path, or path with a numeric suffix if it already exists."""
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.name}-{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


def preserve_existing(path: Path) -> None:
    """Move an existing file aside (never delete it) before writing a regenerated copy."""
    if path.exists():
        target = unique_path(path.with_name(f"{path.stem}.superseded-{utc_stamp()}{path.suffix}"))
        path.rename(target)


def read_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_lock(path: Path = LOCK_PATH) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def check_freeze(parameters: Parameters, manifest_path: Path = MANIFEST_PATH, lock_path: Path = LOCK_PATH) -> list[str]:
    """Return a list of freeze violations (empty means the release candidate is intact)."""
    problems: list[str] = []
    lock = load_lock(lock_path)
    if lock["simulator_version"] != SIMULATOR_VERSION:
        problems.append(f"simulator version {SIMULATOR_VERSION} != locked {lock['simulator_version']}")
    if lock["parameter_version"] != PARAMETER_VERSION:
        problems.append(f"parameter version {PARAMETER_VERSION} != locked {lock['parameter_version']}")
    if parameter_hash(parameters) != lock["parameter_hash"]:
        problems.append("parameter values differ from release_lock.json")
    if normalized_sha256(HERE / "simulator.py") != lock["simulator_source_sha256"]:
        problems.append("simulator.py differs from release_lock.json")
    if normalized_sha256(manifest_path) != lock["manifest_sha256"]:
        problems.append("experiment_manifest.csv differs from release_lock.json")
    return problems


# --------------------------------------------------------------------------- output writing
def _cell(value: object) -> object:
    return "" if value is None else value


def metadata_header(row: dict[str, str], parameters: Parameters) -> list[str]:
    return [
        f"# run_id: {row['run_id']}",
        f"# simulator_version: {SIMULATOR_VERSION}",
        f"# parameter_version: {PARAMETER_VERSION}",
        f"# parameter_hash: {parameter_hash(parameters)}",
        f"# python_version: {platform.python_version()} ({platform.python_implementation()})",
        f"# seed: {row['seed']}",
        f"# group: {row['group']}",
        f"# scenario: {row['scenario']}",
        "# format: CSV with '#' comment header; read with pandas.read_csv(path, comment='#')",
    ]


def _write_csv(path: Path, header_lines: list[str], columns: Iterable[str], rows: Iterable[dict[str, object]]) -> int:
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        for line in header_lines:
            handle.write(line + "\n")
        writer = csv.writer(handle, lineterminator="\n")
        columns = tuple(columns)
        writer.writerow(columns)
        for item in rows:
            writer.writerow([_cell(item[column]) for column in columns])
            count += 1
    return count


def write_run_files(row: dict[str, str], parameters: Parameters, directory: Path) -> dict[str, object]:
    """Simulate one manifest row and write its three files into directory. Deterministic content only."""
    result: RunResult = EcosystemSimulator(parameters, row["group"], row["scenario"], int(row["seed"])).run()  # type: ignore[arg-type]
    header = metadata_header(row, parameters)
    timeseries_path = directory / "timeseries.csv"
    events_path = directory / "replacement_events.csv"
    ts_rows = _write_csv(timeseries_path, header, TIMESERIES_COLUMNS, (record.__dict__ for record in result.records))
    ev_rows = _write_csv(events_path, header, EVENT_COLUMNS, result.replacement_events)

    status = "extinct_recorded" if result.extinct else "complete"
    summary = {
        "run_id": row["run_id"],
        "status": status,
        "phase": row["phase"],
        "simulator_version": SIMULATOR_VERSION,
        "parameter_version": PARAMETER_VERSION,
        "parameter_hash": parameter_hash(parameters),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "seed": int(row["seed"]),
        "group": row["group"],
        "scenario": row["scenario"],
        "planned_steps": parameters.run_length,
        "parameters": asdict(parameters),
        "results": result.summary(),
        "files": {
            "timeseries.csv": {"rows": ts_rows, "sha256": sha256_bytes(timeseries_path.read_bytes())},
            "replacement_events.csv": {"rows": ev_rows, "sha256": sha256_bytes(events_path.read_bytes())},
        },
    }
    with (directory / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return summary


def file_digests(directory: Path) -> dict[str, str]:
    return {name: sha256_bytes((directory / name).read_bytes()) for name in ("summary.json", "timeseries.csv", "replacement_events.csv")}


# --------------------------------------------------------------------------- batch execution
class BatchLog:
    def __init__(self, results_root: Path) -> None:
        results_root.mkdir(parents=True, exist_ok=True)
        self.path = results_root / "batch_log.jsonl"

    def write(self, event: str, **fields: object) -> None:
        entry = {"utc": utc_stamp(), "event": event, **fields}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")


def run_row(row: dict[str, str], parameters: Parameters, runs_root: Path, log: BatchLog) -> str:
    """Execute one manifest row under the no-overwrite policy. Returns an outcome label."""
    runs_root.mkdir(parents=True, exist_ok=True)
    run_id = row["run_id"]
    final_dir = runs_root / run_id
    running_dir = runs_root / f"{run_id}.running"

    if final_dir.exists():
        if (final_dir / "summary.json").exists():
            log.write("skip_already_complete", run_id=run_id)
            return "skipped"
        moved = unique_path(runs_root / f"{run_id}.INCOMPLETE-{utc_stamp()}")
        final_dir.rename(moved)
        log.write("preserved_incomplete", run_id=run_id, moved_to=moved.name)
    if running_dir.exists():
        moved = unique_path(runs_root / f"{run_id}.INCOMPLETE-{utc_stamp()}")
        running_dir.rename(moved)
        log.write("preserved_incomplete", run_id=run_id, moved_to=moved.name)

    running_dir.mkdir()
    started = time.perf_counter()
    try:
        summary = write_run_files(row, parameters, running_dir)
        running_dir.rename(final_dir)
    except Exception:  # noqa: BLE001 - every failure must be preserved, whatever its type
        failed = unique_path(runs_root / f"{run_id}.FAILED-{utc_stamp()}")
        (running_dir / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        (running_dir / "status.json").write_text(
            json.dumps({"run_id": run_id, "status": "failed", "seed": int(row["seed"]), "group": row["group"], "scenario": row["scenario"]}, indent=2) + "\n",
            encoding="utf-8",
        )
        running_dir.rename(failed)
        log.write("run_failed", run_id=run_id, preserved_as=failed.name)
        return "failed"
    log.write("run_ok", run_id=run_id, status=summary["status"], wall_seconds=round(time.perf_counter() - started, 3))
    return "ok"


def select_rows(rows: list[dict[str, str]], phase: str | None, scenario: str | None, group: str | None, limit: int | None) -> list[dict[str, str]]:
    chosen = [
        row
        for row in rows
        if (phase in (None, "all") or row["phase"] == phase)
        and (scenario is None or row["scenario"] == scenario)
        and (group is None or row["group"] == group)
    ]
    return chosen[:limit] if limit else chosen


# --------------------------------------------------------------------------- determinism
def sample_rows_for_verification(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """First seed of every (scenario, group) cell, so every code path is exercised."""
    first_seed = str(SEEDS[0])
    return [row for row in rows if row["seed"] == first_seed]


def verify_determinism(rows: list[dict[str, str]], parameters: Parameters) -> tuple[bool, list[str]]:
    """Run each row twice into temporary directories; compare outputs byte for byte."""
    lines: list[str] = []
    all_identical = True
    for row in rows:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            write_run_files(row, parameters, Path(first))
            write_run_files(row, parameters, Path(second))
            digests_a, digests_b = file_digests(Path(first)), file_digests(Path(second))
        identical = digests_a == digests_b
        all_identical &= identical
        lines.append(
            f"{row['run_id']}\t{'IDENTICAL' if identical else 'DIFFERENT'}\t"
            + "\t".join(f"{name}={digest[:16]}" for name, digest in digests_a.items())
        )
    return all_identical, lines


# --------------------------------------------------------------------------- aggregation
def run_status(row: dict[str, str], runs_root: Path) -> str:
    run_id = row["run_id"]
    final_dir = runs_root / run_id
    if (final_dir / "summary.json").exists():
        with (final_dir / "summary.json").open(encoding="utf-8") as handle:
            return str(json.load(handle)["status"])
    if final_dir.exists():
        return "incomplete_unlabelled"
    if any(runs_root.glob(f"{run_id}.FAILED-*")):
        return "failed_preserved"
    if any(runs_root.glob(f"{run_id}.INCOMPLETE-*")) or (runs_root / f"{run_id}.running").exists():
        return "incomplete_preserved"
    return "missing"


def aggregate(rows: list[dict[str, str]], results_root: Path) -> dict[str, int]:
    runs_root = results_root / "runs"
    flat: list[dict[str, object]] = []
    status_rows: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    for row in rows:
        status = run_status(row, runs_root)
        counts[status] = counts.get(status, 0) + 1
        status_rows.append({"run_id": row["run_id"], "phase": row["phase"], "group": row["group"], "scenario": row["scenario"], "seed": row["seed"], "status": status})
        summary_path = runs_root / row["run_id"] / "summary.json"
        if summary_path.exists():
            with summary_path.open(encoding="utf-8") as handle:
                summary = json.load(handle)
            flat.append(
                {
                    "run_id": summary["run_id"],
                    "phase": summary["phase"],
                    "status": summary["status"],
                    "simulator_version": summary["simulator_version"],
                    "parameter_version": summary["parameter_version"],
                    "parameter_hash": summary["parameter_hash"],
                    "python_version": summary["python_version"],
                    **summary["results"],
                }
            )
    results_root.mkdir(parents=True, exist_ok=True)
    for name, data in (("summary_all.csv", flat), ("run_status_report.csv", status_rows)):
        if not data:
            continue
        target = results_root / name
        preserve_existing(target)
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(data)
    return counts


# --------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", choices=["core", "mechanism", "reference", "all"], default="all")
    parser.add_argument("--scenario", choices=["stationary", "gradual_decline", "sudden_shock"])
    parser.add_argument("--group")
    parser.add_argument("--limit", type=int, help="run only the first N selected rows")
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-determinism", action="store_true")
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args(argv)

    parameters = Parameters()
    problems = check_freeze(parameters)
    if problems:
        print("REFUSING TO RUN: release candidate is not intact:")
        for problem in problems:
            print(f"  - {problem}")
        return 2
    lock = load_lock()
    if lock["python_version_at_freeze"] != platform.python_version():
        print(
            f"WARNING: frozen with Python {lock['python_version_at_freeze']}, running {platform.python_version()}. "
            "Outputs record the Python version; byte-identity is only guaranteed on the same version."
        )

    rows = select_rows(read_manifest(), args.phase, args.scenario, args.group, args.limit)

    if args.verify_determinism:
        identical, lines = verify_determinism(sample_rows_for_verification(rows), parameters)
        print(f"python_version\t{platform.python_version()}")
        print("\n".join(lines))
        print("DETERMINISM: " + ("PASS" if identical else "FAIL"))
        return 0 if identical else 1

    if args.aggregate:
        counts = aggregate(read_manifest(), args.results_root)
        print("Run status counts:", json.dumps(counts, sort_keys=True))
        return 0

    if args.dry_run:
        runs_root = args.results_root / "runs"
        pending = [row for row in rows if not (runs_root / row["run_id"] / "summary.json").exists()]
        print(f"{len(rows)} rows selected; {len(pending)} not yet complete.")
        return 0

    log = BatchLog(args.results_root)
    log.write("batch_start", selected=len(rows), python_version=platform.python_version(), parameter_hash=parameter_hash(parameters))
    tally = {"ok": 0, "skipped": 0, "failed": 0}
    for index, row in enumerate(rows, start=1):
        outcome = run_row(row, parameters, args.results_root / "runs", log)
        tally[outcome] += 1
        if outcome == "failed" or index % 20 == 0 or index == len(rows):
            print(f"[{index}/{len(rows)}] {row['run_id']}: {outcome}", flush=True)
    log.write("batch_end", **tally)
    print("Batch finished:", json.dumps(tally))
    return 1 if tally["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
