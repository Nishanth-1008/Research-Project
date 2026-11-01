# Reproducibility Note — Phase 1 Release Candidate

**Simulator version:** `sim-1.0.0`  **Parameter version:** `params-v1.0`  **Frozen with:** Python 3.12.3 (CPython)
The simulator and runner use only the Python standard library. (`pandas` is optional, for reading outputs.)

## One-command reproduction

Run everything from inside `simulator/`.

| Goal | Command |
| --- | --- |
| Pre-batch gate (freeze check, all tests, determinism check; writes the test log) | `python release_check.py` |
| Mechanics tests only | `python -m unittest test_simulator.py` |
| Reproduce stationary calibration | `python run_calibration.py` |
| Preview the batch | `python run_experiments.py --dry-run` |
| Phase 2 core batch (240 runs) | `python run_experiments.py --phase core` |
| Phase 3 ablations (120 runs) | `python run_experiments.py --phase mechanism` |
| Stationary references (180 runs) | `python run_experiments.py --phase reference` |
| All 540 runs | `python run_experiments.py` |
| Build flat summary table and status report | `python run_experiments.py --aggregate` |

Runs take about 1–1.5 s each (540 runs ≈ 10–15 min on one core) and about 0.3 MB each (≈ 150 MB total). Re-running the same command resumes: completed runs are skipped.

## What is frozen

`release_lock.json` records the SHA-256 of `simulator.py` (line endings normalized), the full parameter values and their hash, the SHA-256 of `experiment_manifest.csv`, the 30 seeds, and the Python version at freeze. `run_experiments.py` **refuses to start** if any of these differ. Changing a parameter, the simulator, or the manifest therefore requires a deliberate re-freeze (move the old manifest and lock aside and rerun `make_manifest.py`) and must be reported.

## Manifest

`experiment_manifest.csv` has 540 rows: 6 groups × 3 scenarios × 30 seeds. Each row gives run ID, phase, group, scenario, seed, simulator version, parameter version, parameter hash, and the output paths.

| Phase | Groups | Scenarios | Runs |
| --- | --- | --- | ---: |
| `core` (Phase 2) | fixed-only, Q-only, static mixture, evolving joint | gradual decline, sudden shock | 240 |
| `mechanism` (Phase 3) | survival-only, reward-only | gradual decline, sudden shock | 120 |
| `reference` | all six | stationary | 180 |

Seeds are 1001–1030, fixed before any main-batch result existed, disjoint from the calibration seeds (1–10), and identical across every group and scenario (common random numbers for matched comparisons).

## Outputs (one directory per run: `results/main/runs/<run_id>/`)

- `summary.json` — run metadata (simulator version, parameter version and hash, Python version, seed, group, scenario, all parameter values), run status, the run-level results, and SHA-256 digests of the other two files.
- `timeseries.csv` — per-step resource, total harvest, living population, Q-learning share, mean reward, mean energy.
- `replacement_events.csv` — per-candidate record at every replacement event (type, age, survival score, reward score, fitness, offspring selected). Written for static mixture and the three evolving groups; header only for homogeneous groups, which have no parent selection.

The CSV files begin with `#` comment lines holding the same metadata. Read them with `pandas.read_csv(path, comment='#')`. Empty cells mean “undefined” (for example, no living agents).

Batch-level files in `results/main/`: `batch_log.jsonl` (append-only event log with timestamps), `summary_all.csv` and `run_status_report.csv` (from `--aggregate`).

## No-overwrite policy

- A completed run directory is never rewritten or deleted.
- Runs are written to `<run_id>.running/` and renamed to `<run_id>/` only when complete. A leftover `.running` directory from an interrupted batch is renamed `<run_id>.INCOMPLETE-<UTC time>` and kept.
- A run that raises an exception is renamed `<run_id>.FAILED-<UTC time>` with `traceback.txt`, and the batch continues. The runner exits non-zero if any run failed.
- An extinction is **not** a failure. It is a completed run with `status: extinct_recorded` and `steps_completed < 2000`, and it stays in the data.
- Regenerated aggregate files move the previous copy aside as `*.superseded-<UTC time>.csv`.

## Determinism

The same manifest row gives byte-identical `summary.json`, `timeseries.csv`, and `replacement_events.csv`. Summary and time-series files contain no timestamps; wall-clock data lives only in `batch_log.jsonl`. `release_check.py` runs one seed from each of the 18 group × scenario cells twice, in two separate processes with different `PYTHONHASHSEED` values, and confirms identical digests. Byte-identity is guaranteed on the same Python version; the version is recorded in every output, and the runner warns if it differs from the freeze.

## Acceptance gate status

| Gate | Evidence |
| --- | --- |
| Same seed + manifest row → identical outputs | `results/release/release_check_log.txt`, section 3 |
| All tests pass | same log, sections 2a (6 mechanics tests) and 2b (14 release-machinery tests) |
| Each output traceable to one parameter version | `parameter_version` and `parameter_hash` in every manifest row, summary, and CSV header; checked against `release_lock.json` |

## Changes to the simulator since calibration

Two additive edits, with no change to rules, parameters, or random-number use: version constants (`SIMULATOR_VERSION`, `PARAMETER_VERSION`) and a per-candidate replacement-event log (required by the run checklist and needed for the Phase 3 fitness-component plot). After the edit, `run_calibration.py` reproduces `stationary_calibration_summary.csv` and `stationary_calibration_timeseries.csv` byte for byte. The saved `stationary_calibration_report.md` differs only in line endings.

## Observation recorded before the batch (no action taken)

Parameters were not changed, per the roadmap. While checking the calibration data, however, I found that the stationary calibration pools all groups when checking the 5%–95% resource band. In those data, Q-only and evolving-joint populations hold the resource at about 20 units (4% of capacity) for more than 99% of steps, while fixed-only holds it near 33%. In a sample sudden-shock run (seed 1001), the evolving-joint population converged to 100% Q-learners and a halving shock at step 1,000 changed nothing visible (post-shock survival 1.0, recovery in 1 step). If this pattern holds across seeds, the shock scenario may not discriminate between Q-containing groups. See the Phase 2 note in the hand-off message.
