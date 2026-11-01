# Simulator

Run all commands from this folder. Standard library only.

- Mechanics tests: `python -m unittest test_simulator.py`
- Stationary calibration: `python run_calibration.py` (writes `results/`)
- **Phase 1 release gate:** `python release_check.py` (freeze check, all tests, determinism check; log in `results/release/`)
- Main batch: `python run_experiments.py --phase core` (see `REPRODUCIBILITY.md` for all commands)

Phase 1 files: `experiment_manifest.csv` (540 runs), `release_lock.json`, `make_manifest.py`, `run_experiments.py`, `test_runner.py`, `release_check.py`, `REPRODUCIBILITY.md`.

The simulator implements the final rules in `../05_audit_and_final_rules.md`.
