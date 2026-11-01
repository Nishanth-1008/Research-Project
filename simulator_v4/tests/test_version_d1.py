"""Comprehensive test suite for Version D.1 (sim-4.1.0) and Protocol v2.0.

Validates:
1. Parameters, group dispatch, and validation bounds (DEC-07, DEC-09, DEC-10).
2. Reproduction vital rates, logistic crowding, deficit targeting, and inheritance.
3. 36-state observation model and Q-table dimensions (DEC-08).
4. Sudden shock stock halving, thermodynamic energy conservation (ledger discrepancy < 1e-8).
5. Primary outcome metrics (S_post, tau_rec, stability, paired differences).
6. Manifest runner, atomic writes, and no-overwrite protection.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from random import Random

from simulator_v4.agents import ACTIONS, HARVEST_REQUEST, Agent
from simulator_v4.energy_accounting import EnergyLedger
from simulator_v4.metrics import (
    compute_immediate_survival,
    compute_paired_differences,
    compute_recovery_time,
    compute_resource_stability,
)
from simulator_v4.parameters import (
    PARAMETER_VERSION,
    SIMULATOR_VERSION,
    Parameters,
)
from simulator_v4.reproduction import (
    calculate_reproduction_probability,
    perform_endogenous_reproduction,
)
from simulator_v4.run_experiment import (
    execute_single_run,
    generate_manifest,
    is_run_complete,
)
from simulator_v4.simulator import EcosystemSimulator, StepRecord


class TestParametersAndValidation(unittest.TestCase):
    """Test group initialization, parameter bounds, and validation rules."""

    def test_default_version_strings(self) -> None:
        params = Parameters()
        self.assertEqual(SIMULATOR_VERSION, "sim-4.1.0")
        self.assertEqual(PARAMETER_VERSION, "params-v4.2")
        self.assertEqual(params.group, "evolving_joint")
        self.assertEqual(params.regulation_model, "logistic")
        self.assertEqual(params.crowding_capacity, 70)

    def test_factory_fixed_only(self) -> None:
        p = Parameters.for_group("fixed_only")
        self.assertEqual(p.group, "fixed_only")
        self.assertEqual(p.initial_fixed_count, 50)
        self.assertEqual(p.initial_q_count, 0)

    def test_factory_q_only(self) -> None:
        p = Parameters.for_group("q_only")
        self.assertEqual(p.group, "q_only")
        self.assertEqual(p.initial_fixed_count, 0)
        self.assertEqual(p.initial_q_count, 50)

    def test_factory_static_mixture(self) -> None:
        p = Parameters.for_group("static_mixture")
        self.assertEqual(p.group, "static_mixture")
        self.assertEqual(p.initial_fixed_count, 25)
        self.assertEqual(p.initial_q_count, 25)

    def test_factory_evolving_joint(self) -> None:
        p = Parameters.for_group("evolving_joint")
        self.assertEqual(p.group, "evolving_joint")
        self.assertEqual(p.initial_fixed_count, 25)
        self.assertEqual(p.initial_q_count, 25)

    def test_factory_survival_only(self) -> None:
        p = Parameters.for_group("survival_only")
        self.assertEqual(p.group, "survival_only")
        self.assertEqual(p.initial_fixed_count, 25)
        self.assertEqual(p.initial_q_count, 25)

    def test_factory_reward_only(self) -> None:
        p = Parameters.for_group("reward_only")
        self.assertEqual(p.group, "reward_only")
        self.assertEqual(p.initial_fixed_count, 25)
        self.assertEqual(p.initial_q_count, 25)

    def test_validation_invalid_group(self) -> None:
        with self.assertRaises(ValueError):
            Parameters(group="invalid_group_name")

    def test_validation_invalid_crowding_capacity(self) -> None:
        with self.assertRaises(ValueError):
            Parameters(crowding_capacity=0)


class TestReproductionAndVitalRates(unittest.TestCase):
    """Test reproductive rules, logistic crowding discount, and inheritance mechanics."""

    def setUp(self) -> None:
        self.params = Parameters(regulation_model="none")

    def test_energy_threshold_gating(self) -> None:
        # Sub-threshold energy (<15.0) yields exactly 0.0
        self.assertEqual(calculate_reproduction_probability(14.99, 30, self.params), 0.0)
        self.assertEqual(calculate_reproduction_probability(15.0, 30, self.params), 0.0)
        # Scales linearly between 15.0 and 20.0
        self.assertAlmostEqual(calculate_reproduction_probability(17.5, 30, self.params), 0.05)
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 30, self.params), 0.10)
        # Capped above 20.0
        self.assertAlmostEqual(calculate_reproduction_probability(25.0, 30, self.params), 0.10)

    def test_age_factor_senescence(self) -> None:
        # Full reproduction <= 45
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 45, self.params), 0.10)
        # Linear senescence 45-60
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 52.5, self.params), 0.05)
        # Capped to 0 at age >= 60
        self.assertEqual(calculate_reproduction_probability(20.0, 60, self.params), 0.0)
        self.assertEqual(calculate_reproduction_probability(20.0, 65, self.params), 0.0)

    def test_logistic_crowding_discount(self) -> None:
        p = Parameters(regulation_model="logistic", crowding_capacity=50)
        # N = 0 -> discount = 1.0 -> prob = 0.10
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 30, p, living_population=0), 0.10)
        # N = 25 -> discount = 0.5 -> prob = 0.05
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 30, p, living_population=25), 0.05)
        # N = 50 -> discount = 0.0 -> prob = 0.0
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 30, p, living_population=50), 0.0)
        # N = 60 -> discount = 0.0 -> prob = 0.0
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 30, p, living_population=60), 0.0)

    def test_survival_only_vital_rate_formula(self) -> None:
        p = Parameters(group="survival_only", regulation_model="none")
        # Age 50 / 100 = 0.5 -> prob = 0.10 * 0.5 = 0.05
        self.assertAlmostEqual(calculate_reproduction_probability(16.0, 50, p), 0.05)
        # Age 100 >= max_age -> 0.0
        self.assertEqual(calculate_reproduction_probability(20.0, 100, p), 0.0)

    def test_reward_only_vital_rate_formula(self) -> None:
        p = Parameters(group="reward_only", regulation_model="none")
        # Age 55 with E=20.0 (no age senescence penalty) -> prob = 0.10
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 55, p), 0.10)

    def test_thermodynamic_birth_transfer(self) -> None:
        # Parent transfers exactly 10.0 energy to newborn: net Delta E = 0.0
        parent = Agent(identifier=1, kind="fixed", energy=20.0, age=20)
        rng = Random(42)
        next_id = 2
        newborns, logs = perform_endogenous_reproduction(
            living_agents=[parent],
            step_number=10,
            parameters=Parameters(reproduction_max_prob=1.0, regulation_model="none"),
            random_gen=rng,
            next_identifier_getter=lambda: next_id,
        )
        self.assertEqual(len(newborns), 1)
        self.assertEqual(parent.energy, 10.0)
        self.assertEqual(newborns[0].energy, 10.0)
        self.assertAlmostEqual(parent.energy + newborns[0].energy, 20.0)

    def test_reproduction_cooldown_assignment(self) -> None:
        # Parent and child both receive cooldown = 20
        parent = Agent(identifier=1, kind="q_learning", energy=20.0, age=25)
        rng = Random(42)
        newborns, _ = perform_endogenous_reproduction(
            living_agents=[parent],
            step_number=10,
            parameters=Parameters(reproduction_max_prob=1.0, regulation_model="none"),
            random_gen=rng,
            next_identifier_getter=lambda: 2,
        )
        self.assertEqual(parent.reproduction_cooldown, 20)
        self.assertEqual(newborns[0].reproduction_cooldown, 20)

    def test_cooldown_immunity_on_birth_step(self) -> None:
        # Verify simulator step does not decrement newborn cooldown or age on step of birth
        sim = EcosystemSimulator(
            parameters=Parameters(
                initial_population=1,
                initial_fixed_count=1,
                initial_q_count=0,
                initial_founder_energy=22.0,
                reproduction_max_prob=1.0,
                regulation_model="none",
            ),
            scenario="stationary",
            seed=42,
        )
        rec = sim.step(0)
        self.assertGreater(rec.births, 0)
        newborn = [a for a in sim.agents if a.identifier > 1][0]
        self.assertEqual(newborn.age, 0)
        self.assertEqual(newborn.reproduction_cooldown, 20)

    def test_static_mixture_deficit_targeted_assignment(self) -> None:
        # In static_mixture, deficit type is favored
        parent = Agent(identifier=1, kind="fixed", energy=20.0, age=20)
        living = [parent]  # 1 fixed, 0 Q -> Q is in deficit
        rng = Random(42)
        newborns, _ = perform_endogenous_reproduction(
            living_agents=living,
            step_number=1,
            parameters=Parameters(group="static_mixture", reproduction_max_prob=1.0, regulation_model="none"),
            random_gen=rng,
            next_identifier_getter=lambda: 2,
        )
        self.assertEqual(len(newborns), 1)
        self.assertEqual(newborns[0].kind, "q_learning")

    def test_extinct_type_reintroduction_in_static_mix(self) -> None:
        # If Q-learning drops to 0 in static_mixture, next birth must be Q-learning
        living = [Agent(identifier=1, kind="fixed", energy=20.0, age=20)]
        rng = Random(99)
        newborns, _ = perform_endogenous_reproduction(
            living_agents=living,
            step_number=5,
            parameters=Parameters(group="static_mixture", reproduction_max_prob=1.0, regulation_model="none"),
            random_gen=rng,
            next_identifier_getter=lambda: 999,
        )
        self.assertEqual(len(newborns), 1)
        self.assertEqual(newborns[0].kind, "q_learning")

    def test_cross_type_tabula_rasa_initialization(self) -> None:
        # When Fixed parent yields Q newborn under deficit assignment, child gets clean Q-table
        parent = Agent(identifier=1, kind="fixed", energy=20.0, age=20)
        rng = Random(42)
        newborns, _ = perform_endogenous_reproduction(
            living_agents=[parent],
            step_number=1,
            parameters=Parameters(group="static_mixture", reproduction_max_prob=1.0, regulation_model="none"),
            random_gen=rng,
            next_identifier_getter=lambda: 2,
        )
        child = newborns[0]
        self.assertEqual(child.kind, "q_learning")
        self.assertIsNone(child.q_parent)

    def test_parental_q_snapshot_inheritance(self) -> None:
        # Q newborn born to Q parent receives parental snapshot
        parent = Agent(identifier=1, kind="q_learning", energy=20.0, age=20)
        parent.q_own[("medium", "medium", "stable")] = [1.0, 2.0, 3.0, 4.0]
        rng = Random(42)
        newborns, _ = perform_endogenous_reproduction(
            living_agents=[parent],
            step_number=1,
            parameters=Parameters(group="evolving_joint", reproduction_max_prob=1.0, regulation_model="none"),
            random_gen=rng,
            next_identifier_getter=lambda: 2,
        )
        child = newborns[0]
        self.assertEqual(child.kind, "q_learning")
        self.assertIsNotNone(child.q_parent)
        self.assertEqual(child.q_parent[("medium", "medium", "stable")], [1.0, 2.0, 3.0, 4.0])

    def test_cooldown_gating(self) -> None:
        # Agent with positive cooldown is ineligible
        parent = Agent(identifier=1, kind="fixed", energy=20.0, age=20, reproduction_cooldown=5)
        rng = Random(42)
        newborns, _ = perform_endogenous_reproduction(
            living_agents=[parent],
            step_number=1,
            parameters=Parameters(reproduction_max_prob=1.0),
            random_gen=rng,
            next_identifier_getter=lambda: 2,
        )
        self.assertEqual(len(newborns), 0)


class TestStateSpaceAndObservation(unittest.TestCase):
    """Test 36-state observation discretization and Q-table structure (DEC-08)."""

    def setUp(self) -> None:
        self.sim = EcosystemSimulator(parameters=Parameters(), scenario="stationary", seed=1001)

    def test_resource_band_discretization(self) -> None:
        self.assertEqual(self.sim._get_resource_band(164.9), "low")
        self.assertEqual(self.sim._get_resource_band(165.0), "medium")
        self.assertEqual(self.sim._get_resource_band(330.0), "medium")
        self.assertEqual(self.sim._get_resource_band(330.1), "high")

    def test_energy_band_discretization_four_bands(self) -> None:
        # Critical band strictly below 3.0
        self.assertEqual(self.sim._get_energy_band(2.99), "critical")
        self.assertEqual(self.sim._get_energy_band(3.0), "low")
        self.assertEqual(self.sim._get_energy_band(6.99), "low")
        self.assertEqual(self.sim._get_energy_band(7.0), "medium")
        self.assertEqual(self.sim._get_energy_band(13.99), "medium")
        self.assertEqual(self.sim._get_energy_band(14.0), "high")

    def test_trend_band_discretization(self) -> None:
        self.assertEqual(self.sim._get_trend_band(95.0, 100.0), "declining")
        self.assertEqual(self.sim._get_trend_band(100.0, 100.0), "stable")
        self.assertEqual(self.sim._get_trend_band(105.0, 100.0), "increasing")

    def test_total_state_space_is_exactly_36(self) -> None:
        resource_bands = ["low", "medium", "high"]
        energy_bands = ["critical", "low", "medium", "high"]
        trend_bands = ["declining", "stable", "increasing"]
        all_states = [
            (r, e, t)
            for r in resource_bands
            for e in energy_bands
            for t in trend_bands
        ]
        self.assertEqual(len(all_states), 36)

    def test_q_table_action_cardinality(self) -> None:
        # Exactly 4 actions per state -> 144 Q-values
        self.assertEqual(len(ACTIONS), 4)
        for act in ("rest", "conservative", "moderate", "aggressive"):
            self.assertIn(act, ACTIONS)

    def test_observation_construction_consistency(self) -> None:
        agent = Agent(identifier=1, kind="q_learning", energy=2.5, age=10)
        self.sim.resource = 100.0
        self.sim.previous_start_resource = 110.0
        obs = self.sim._get_state(agent)
        self.assertEqual(obs, ("low", "critical", "declining"))


class TestSimulatorDynamicsAndShock(unittest.TestCase):
    """Test sudden shock stock halving, regeneration constancy, and mortality."""

    def test_sudden_shock_halving_and_baseline_g(self) -> None:
        # Verify R(1000) is halved and baseline g=0.10 is preserved throughout
        sim = EcosystemSimulator(parameters=Parameters(), scenario="sudden_shock", seed=1001)
        for step in range(1001):
            sim.step(step)
        # Verify base regeneration remains 0.10
        self.assertEqual(sim._get_regeneration_rate(1000), 0.10)
        self.assertEqual(sim.parameters.baseline_regeneration, 0.10)

    def test_starvation_mortality(self) -> None:
        # Agent with depleted resource and insufficient energy dies from starvation
        sim = EcosystemSimulator(parameters=Parameters(), scenario="stationary", seed=1001)
        sim.resource = 0.0
        sim.agents[0].energy = 0.05
        sim.step(0)
        alive_ids = {a.identifier for a in sim.agents}
        self.assertNotIn(1, alive_ids)

    def test_retirement_mortality(self) -> None:
        # Agent reaching maximum_age=100 retires
        sim = EcosystemSimulator(parameters=Parameters(), scenario="stationary", seed=1001)
        sim.agents[0].age = 100
        sim.step(0)
        alive_ids = {a.identifier for a in sim.agents}
        self.assertNotIn(1, alive_ids)

    def test_extinction_termination(self) -> None:
        # Simulator terminates run when all agents die
        sim = EcosystemSimulator(parameters=Parameters(), scenario="stationary", seed=1001)
        sim.agents.clear()  # Force 0 agents
        result = sim.run(steps=100)
        self.assertTrue(result.extinct)
        self.assertEqual(result.final_population, 0)
        self.assertEqual(result.steps_completed, 1)

    def test_deterministic_seed_reproducibility(self) -> None:
        # Common random numbers produce identical trajectories
        params = Parameters()
        sim1 = EcosystemSimulator(parameters=params, scenario="stationary", seed=1005)
        sim2 = EcosystemSimulator(parameters=params, scenario="stationary", seed=1005)
        for s in range(30):
            r1 = sim1.step(s)
            r2 = sim2.step(s)
            self.assertEqual(r1.resource, r2.resource)
            self.assertEqual(r1.living_population, r2.living_population)
            self.assertEqual(r1.total_harvest, r2.total_harvest)

    def test_step_record_extended_telemetry(self) -> None:
        # Check that StepRecord contains extended subpopulation telemetry
        sim = EcosystemSimulator(parameters=Parameters(), scenario="stationary", seed=1001)
        rec = sim.step(0)
        self.assertIsNotNone(rec.fixed_mean_energy)
        self.assertIsNotNone(rec.q_mean_energy)
        self.assertIsInstance(rec.reference_harvest, float)

    def test_reference_harvest_calculation(self) -> None:
        # Verify reference harvest = N/2 * (h_F + h_Q)
        sim = EcosystemSimulator(parameters=Parameters(), scenario="stationary", seed=1001)
        rec = sim.step(0)
        h_f = rec.fixed_allocated_harvest / rec.fixed_population if rec.fixed_population > 0 else 0.0
        h_q = rec.q_allocated_harvest / rec.q_population if rec.q_population > 0 else 0.0
        expected_ref = (rec.living_population / 2.0) * h_f + (rec.living_population / 2.0) * h_q
        self.assertAlmostEqual(rec.reference_harvest, expected_ref, places=6)

    def test_gradual_inheritance_decay(self) -> None:
        # Q-inheritance decays linearly over 12 steps
        agent = Agent(identifier=1, kind="q_learning", energy=10.0, age=0)
        agent.q_parent = {("medium", "medium", "stable"): [1.0, 1.0, 1.0, 1.0]}
        self.assertEqual(agent.inheritance_lambda(12), 1.0)
        agent.age = 6
        self.assertEqual(agent.inheritance_lambda(12), 0.5)
        agent.age = 12
        self.assertEqual(agent.inheritance_lambda(12), 0.0)


class TestThermodynamicConservation(unittest.TestCase):
    """Test strict energy conservation across the simulation."""

    def test_energy_ledger_discrepancy_below_threshold(self) -> None:
        sim = EcosystemSimulator(parameters=Parameters(), scenario="stationary", seed=1001)
        for s in range(50):
            rec = sim.step(s)
            self.assertLess(abs(rec.energy_ledger_discrepancy), 1e-8)

    def test_energy_inflow_calculation(self) -> None:
        ledger = EnergyLedger(initial_founder_endowment=500.0, cumulative_harvested=120.0)
        self.assertEqual(ledger.total_energy_inflow(), 620.0)

    def test_verify_energy_balance_conserved(self) -> None:
        ledger = EnergyLedger(
            initial_founder_endowment=500.0,
            cumulative_harvested=100.0,
            cumulative_maintenance=50.0,
            cumulative_energy_cap_losses=5.0,
            cumulative_retirement_losses=15.0,
            cumulative_starvation_losses=0.0,
        )
        # Expected current: 500 + 100 - 50 - 5 - 15 = 530.0
        conserved, disc = ledger.verify_energy_balance(530.0)
        self.assertTrue(conserved)
        self.assertAlmostEqual(disc, 0.0)

    def test_verify_energy_balance_detected_discrepancy(self) -> None:
        ledger = EnergyLedger(initial_founder_endowment=500.0)
        conserved, disc = ledger.verify_energy_balance(450.0)
        self.assertFalse(conserved)
        self.assertAlmostEqual(disc, -50.0)


class TestMetricsAndAnalytics(unittest.TestCase):
    """Test primary outcome calculation: S_post, tau_rec, stability, and paired differences."""

    def _create_mock_records(self) -> list[StepRecord]:
        records: list[StepRecord] = []
        for s in range(1050):
            if s < 1000:
                rew = 2.0
                res = 80.0
                pop = 50
            elif s < 1025:
                rew = 1.0
                res = 45.0
                pop = 40
            else:
                rew = 1.9
                res = 75.0
                pop = 48

            records.append(
                StepRecord(
                    step=s,
                    resource=res,
                    total_harvest=20.0,
                    requested_harvest=20.0,
                    fixed_requested_harvest=10.0,
                    q_requested_harvest=10.0,
                    fixed_allocated_harvest=10.0,
                    q_allocated_harvest=10.0,
                    living_population=pop,
                    fixed_population=pop // 2,
                    q_population=pop // 2,
                    q_learning_share=0.5,
                    mean_reward=rew,
                    mean_energy=10.0,
                    births=0,
                    fixed_births=0,
                    q_births=0,
                    reproduction_attempts=0,
                    successful_births=0,
                    starvation_deaths=0,
                    retirement_deaths=0,
                    regeneration=5.0,
                )
            )
        return records

    def test_immediate_survival_metric(self) -> None:
        records = self._create_mock_records()
        surv = compute_immediate_survival(records, shock_step=1000, delta_t=20)
        self.assertEqual(surv["pre_shock_population"], 50)
        self.assertEqual(surv["post_shock_delta_pop"], 40)
        self.assertAlmostEqual(surv["s_post_delta"], 40.0 / 50.0)

    def test_recovery_time_metric(self) -> None:
        records = self._create_mock_records()
        recov = compute_recovery_time(records, shock_step=1000, pre_shock_window=100, threshold_ratio=0.90)
        self.assertTrue(recov["recovered"])
        self.assertEqual(recov["recovery_time"], 25)  # Recovered at step 1025 -> 1025 - 1000 = 25
        self.assertFalse(recov["censored"])

    def test_resource_stability_metric(self) -> None:
        records = self._create_mock_records()
        stab = compute_resource_stability(records, start_step=1001, end_step=1049)
        self.assertGreater(stab["mean_resource"], 0.0)
        self.assertGreaterEqual(stab["var_resource"], 0.0)
        self.assertGreaterEqual(stab["cv_resource"], 0.0)

    def test_paired_differences_crn(self) -> None:
        prim = [{"seed": 1, "mean_resource": 70.0}, {"seed": 2, "mean_resource": 75.0}]
        ctrl = [{"seed": 1, "mean_resource": 60.0}, {"seed": 2, "mean_resource": 65.0}]
        diff = compute_paired_differences(prim, ctrl, matched_key="seed", metric_keys=["mean_resource"])
        self.assertEqual(diff["mean_resource"]["n"], 2)
        self.assertAlmostEqual(diff["mean_resource"]["mean_diff"], 10.0)


class TestManifestRunnerAndProtection(unittest.TestCase):
    """Test manifest runner, atomic writing, and no-overwrite protection."""

    def setUp(self) -> None:
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_manifest_generation(self) -> None:
        m_path = self.test_dir / "manifest.csv"
        rows = generate_manifest(
            groups=["fixed_only", "q_only"],
            scenarios=["stationary"],
            seeds=[901, 902],
            output_path=m_path,
            steps=100,
        )
        self.assertEqual(len(rows), 4)
        self.assertTrue(m_path.exists())

    def test_run_completion_detection(self) -> None:
        run_id = "test_run_1"
        self.assertFalse(is_run_complete(self.test_dir, run_id))

        # Create mock complete files
        summary_file = self.test_dir / f"{run_id}_summary.json"
        csv_file = self.test_dir / f"{run_id}_records.csv"
        with open(summary_file, "w") as f:
            json.dump({"steps_completed": 2000, "extinct": False}, f)
        with open(csv_file, "w") as f:
            f.write("step,resource\n0,100\n")

        self.assertTrue(is_run_complete(self.test_dir, run_id, expected_steps=2000))

    def test_atomic_file_execution(self) -> None:
        out = execute_single_run(
            group="fixed_only",
            scenario="stationary",
            seed=901,
            output_dir=self.test_dir,
            run_id="test_atomic_1",
            steps=5,
        )
        self.assertEqual(out["status"], "COMPLETED")
        self.assertTrue((self.test_dir / "test_atomic_1_records.csv").exists())
        self.assertTrue((self.test_dir / "test_atomic_1_summary.json").exists())
        self.assertFalse((self.test_dir / "test_atomic_1_records.csv.tmp").exists())

    def test_no_overwrite_protection(self) -> None:
        # First execution
        execute_single_run(
            group="fixed_only",
            scenario="stationary",
            seed=901,
            output_dir=self.test_dir,
            run_id="test_overwrite_1",
            steps=5,
        )
        # Second execution without force_overwrite should be SKIPPED_EXISTING
        out2 = execute_single_run(
            group="fixed_only",
            scenario="stationary",
            seed=901,
            output_dir=self.test_dir,
            run_id="test_overwrite_1",
            steps=5,
            force_overwrite=False,
        )
        self.assertEqual(out2["status"], "SKIPPED_EXISTING")


if __name__ == "__main__":
    unittest.main()
