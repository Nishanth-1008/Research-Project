"""Tests for the Phase 1 release machinery: manifest, determinism, and the no-overwrite policy."""

import csv
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import run_experiments as rx
from make_manifest import SEEDS, parameter_hash
from simulator import PARAMETER_VERSION, SIMULATOR_VERSION, Parameters

SHORT = Parameters(run_length=120, shock_step=60, gradual_start=30, gradual_end=60)


def short_row(group: str = "evolving_joint", scenario: str = "sudden_shock", seed: int = 1001) -> dict[str, str]:
    return {
        "run_id": f"{scenario}__{group}__s{seed}",
        "phase": "core",
        "group": group,
        "scenario": scenario,
        "seed": str(seed),
    }


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = rx.read_manifest()

    def test_row_counts_and_uniqueness(self) -> None:
        self.assertEqual(len(self.rows), 540)
        self.assertEqual(len({row["run_id"] for row in self.rows}), 540)
        self.assertEqual(Counter(row["phase"] for row in self.rows), {"core": 240, "mechanism": 120, "reference": 180})

    def test_thirty_matched_seeds_per_condition(self) -> None:
        cells: dict[tuple[str, str], set[str]] = {}
        for row in self.rows:
            cells.setdefault((row["scenario"], row["group"]), set()).add(row["seed"])
        self.assertEqual(len(cells), 18)
        expected = {str(seed) for seed in SEEDS}
        self.assertTrue(all(seeds == expected for seeds in cells.values()))

    def test_every_row_names_one_parameter_version(self) -> None:
        self.assertEqual({row["parameter_version"] for row in self.rows}, {PARAMETER_VERSION})
        self.assertEqual({row["simulator_version"] for row in self.rows}, {SIMULATOR_VERSION})
        self.assertEqual({row["parameter_hash"] for row in self.rows}, {parameter_hash(Parameters())})

    def test_freeze_check_passes_on_release_candidate(self) -> None:
        self.assertEqual(rx.check_freeze(Parameters()), [])

    def test_freeze_check_detects_parameter_change(self) -> None:
        self.assertTrue(rx.check_freeze(Parameters(maintenance_cost=0.25)))


class DeterminismTests(unittest.TestCase):
    def test_same_row_gives_identical_bytes(self) -> None:
        for group in ("fixed_only", "q_only", "static_mixture", "evolving_joint", "evolving_survival", "evolving_reward"):
            for scenario in ("stationary", "gradual_decline", "sudden_shock"):
                identical, lines = rx.verify_determinism([short_row(group, scenario)], SHORT)
                self.assertTrue(identical, lines)

    def test_different_seeds_differ(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            rx.write_run_files(short_row(seed=1001), SHORT, Path(first))
            rx.write_run_files(short_row(seed=1002), SHORT, Path(second))
            self.assertNotEqual(rx.file_digests(Path(first))["timeseries.csv"], rx.file_digests(Path(second))["timeseries.csv"])

    def test_outputs_carry_required_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = rx.write_run_files(short_row(), SHORT, Path(directory))
            for key in ("simulator_version", "parameter_version", "parameter_hash", "python_version", "seed", "group", "scenario", "parameters"):
                self.assertIn(key, summary)
            for name in ("timeseries.csv", "replacement_events.csv"):
                head = (Path(directory) / name).read_text(encoding="utf-8").splitlines()[:9]
                joined = "\n".join(head)
                for token in ("run_id", "simulator_version", "parameter_version", "python_version", "seed", "group", "scenario"):
                    self.assertIn(f"# {token}:", joined)

    def test_replacement_events_recorded_for_selection_groups(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rx.write_run_files(short_row("evolving_joint", "stationary"), SHORT, Path(directory))
            with (Path(directory) / "replacement_events.csv").open(encoding="utf-8") as handle:
                events = list(csv.DictReader(line for line in handle if not line.startswith("#")))
        self.assertTrue(events)
        self.assertTrue(all(row["fitness"] != "" for row in events))
        self.assertGreater(sum(int(row["offspring_selected"]) for row in events), 0)


class NoOverwriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.runs = self.root / "runs"
        self.log = rx.BatchLog(self.root)
        self.row = short_row()

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_completed_run_is_not_rewritten(self) -> None:
        self.assertEqual(rx.run_row(self.row, SHORT, self.runs, self.log), "ok")
        before = rx.file_digests(self.runs / self.row["run_id"])
        (self.runs / self.row["run_id"] / "timeseries.csv").write_text("sentinel\n", encoding="utf-8")
        self.assertEqual(rx.run_row(self.row, SHORT, self.runs, self.log), "skipped")
        self.assertEqual((self.runs / self.row["run_id"] / "timeseries.csv").read_text(encoding="utf-8"), "sentinel\n")
        self.assertNotEqual(before["timeseries.csv"], rx.file_digests(self.runs / self.row["run_id"])["timeseries.csv"])

    def test_interrupted_run_is_preserved_and_labelled(self) -> None:
        stale = self.runs / f"{self.row['run_id']}.running"
        stale.mkdir(parents=True)
        (stale / "partial.txt").write_text("partial", encoding="utf-8")
        self.assertEqual(rx.run_row(self.row, SHORT, self.runs, self.log), "ok")
        preserved = list(self.runs.glob(f"{self.row['run_id']}.INCOMPLETE-*"))
        self.assertEqual(len(preserved), 1)
        self.assertEqual((preserved[0] / "partial.txt").read_text(encoding="utf-8"), "partial")
        self.assertTrue((self.runs / self.row["run_id"] / "summary.json").exists())

    def test_failed_run_is_preserved_with_traceback(self) -> None:
        with mock.patch.object(rx, "write_run_files", side_effect=RuntimeError("boom")):
            self.assertEqual(rx.run_row(self.row, SHORT, self.runs, self.log), "failed")
        failed = list(self.runs.glob(f"{self.row['run_id']}.FAILED-*"))
        self.assertEqual(len(failed), 1)
        self.assertIn("boom", (failed[0] / "traceback.txt").read_text(encoding="utf-8"))
        self.assertFalse((self.runs / self.row["run_id"]).exists())
        self.assertEqual(rx.run_status(self.row, self.runs), "failed_preserved")

    def test_extinction_is_retained_and_labelled(self) -> None:
        doomed = Parameters(run_length=50, initial_energy=0.1, maintenance_cost=3.0)
        self.assertEqual(rx.run_row(self.row, doomed, self.runs, self.log), "ok")
        with (self.runs / self.row["run_id"] / "summary.json").open(encoding="utf-8") as handle:
            summary = json.load(handle)
        self.assertEqual(summary["status"], "extinct_recorded")
        self.assertTrue(summary["results"]["extinct"])

    def test_aggregate_preserves_previous_aggregate(self) -> None:
        rx.run_row(self.row, SHORT, self.runs, self.log)
        rx.aggregate([self.row], self.root)
        rx.aggregate([self.row], self.root)
        self.assertEqual(len(list(self.root.glob("summary_all.superseded-*.csv"))), 1)


if __name__ == "__main__":
    unittest.main()
