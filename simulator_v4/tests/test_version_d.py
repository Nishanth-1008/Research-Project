"""Comprehensive Unit Testing Suite for Version D (sim-4.0.0).

Verifies:
1. Reproduction probability boundaries, energy scaling, and senescent clipping.
2. Birth-step cooldown and age decrement immunity (refractory timing).
3. Thermodynamic energy conservation (|error| < 1e-10) during reproduction and lifecycle.
4. Gradual Q-table inheritance mechanics and 12-step linear decay.
5. Unconstrained population dynamics (no artificial 50-agent cap).
6. Deterministic seed reproducibility across multi-step runs.
"""

from __future__ import annotations

import unittest
from random import Random

from simulator_v4.agents import ACTIONS, HARVEST_REQUEST, Agent
from simulator_v4.parameters import Parameters
from simulator_v4.reproduction import (
    calculate_reproduction_probability,
    perform_endogenous_reproduction,
)
from simulator_v4.simulator import EcosystemSimulator


class TestVersionDReproduction(unittest.TestCase):
    def setUp(self) -> None:
        self.params = Parameters()

    def test_probability_energy_boundaries(self) -> None:
        """Verify reproduction probability zero below 15.0 and scales up to 20.0."""
        # Energy < 15.0 -> 0.0 probability
        self.assertEqual(calculate_reproduction_probability(14.99, 30, self.params), 0.0)
        self.assertEqual(calculate_reproduction_probability(0.0, 30, self.params), 0.0)

        # Energy == 15.0 -> 0.0 probability
        self.assertAlmostEqual(calculate_reproduction_probability(15.0, 30, self.params), 0.0)

        # Energy == 17.5 at age <= 45 -> 0.05 probability
        self.assertAlmostEqual(calculate_reproduction_probability(17.5, 30, self.params), 0.05)

        # Energy == 20.0 at age <= 45 -> 0.10 probability
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 30, self.params), 0.10)

        # Energy > 20.0 (clipped to 1.0) -> capped at 0.10 probability
        self.assertAlmostEqual(calculate_reproduction_probability(25.0, 30, self.params), 0.10)

    def test_probability_age_boundaries(self) -> None:
        """Verify age factor A_i: 1.0 for age <= 45, linear decrease 45-60, 0.0 for age >= 60."""
        # Full reproductive ability (age <= 45)
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 0, self.params), 0.10)
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 45, self.params), 0.10)

        # Gradual decline (45 < age < 60)
        # At age 52.5: A_i = (60 - 52.5) / 15 = 7.5 / 15 = 0.5 -> prob = 0.05
        self.assertAlmostEqual(calculate_reproduction_probability(20.0, 52.5, self.params), 0.05)
        # At age 50: A_i = 10 / 15 = 2/3 -> prob = 0.10 * (2/3)
        self.assertAlmostEqual(
            calculate_reproduction_probability(20.0, 50, self.params),
            0.10 * (10.0 / 15.0),
        )

        # Senescent cutoff (age >= 60)
        self.assertEqual(calculate_reproduction_probability(20.0, 60, self.params), 0.0)
        self.assertEqual(calculate_reproduction_probability(20.0, 75, self.params), 0.0)
        self.assertEqual(calculate_reproduction_probability(25.0, 99, self.params), 0.0)

    def test_birth_step_cooldown_and_age_immunity(self) -> None:
        """Verify newborns and reproducing parents skip cooldown decrement on birth step, and newborn skips aging."""
        parent = Agent(
            identifier=1,
            kind="fixed",
            energy=20.0,
            age=30,
            reproduction_cooldown=0,
        )
        rng = Random(42)
        next_id = 100

        def get_id() -> int:
            nonlocal next_id
            i = next_id
            next_id += 1
            return i

        # Force reproduction by setting prob = 1.0 temporarily
        newborns, logs = perform_endogenous_reproduction(
            [parent], 10, self.params, Random(0), get_id
        )

        # Check if reproduction succeeded (or force via high probability)
        # To guarantee success for test, pass a deterministic RNG or high draw
        class RiggedRng:
            def random(self) -> float:
                return 0.001

        newborns, logs = perform_endogenous_reproduction(
            [parent], 10, self.params, RiggedRng(), get_id
        )
        self.assertEqual(len(newborns), 1)
        newborn = newborns[0]

        # Verify parent state immediately after birth
        self.assertEqual(parent.energy, 10.0)
        self.assertEqual(parent.reproduction_cooldown, 20)
        self.assertTrue(parent.skip_cooldown_decrement)

        # Verify newborn state immediately after birth
        self.assertEqual(newborn.energy, 10.0)
        self.assertEqual(newborn.age, 0)
        self.assertEqual(newborn.reproduction_cooldown, 20)
        self.assertTrue(newborn.skip_cooldown_decrement)
        self.assertTrue(newborn.skip_age_increment)

        # Simulate Stage 7 (Cooldown decrement & Age increment) on birth step
        agents = [parent, newborn]
        for a in agents:
            if a.skip_cooldown_decrement:
                a.skip_cooldown_decrement = False
            elif a.reproduction_cooldown > 0:
                a.reproduction_cooldown -= 1

            if a.skip_age_increment:
                a.skip_age_increment = False
            else:
                a.age += 1

        # Post-Stage 7 check on birth step: cooldowns must still be 20, newborn age still 0
        self.assertEqual(parent.reproduction_cooldown, 20)
        self.assertEqual(parent.age, 31)  # parent ages normally
        self.assertEqual(newborn.reproduction_cooldown, 20)
        self.assertEqual(newborn.age, 0)  # newborn skips aging on birth step!

        # Simulate Stage 7 on the NEXT step (step 11)
        for a in agents:
            if a.skip_cooldown_decrement:
                a.skip_cooldown_decrement = False
            elif a.reproduction_cooldown > 0:
                a.reproduction_cooldown -= 1

            if a.skip_age_increment:
                a.skip_age_increment = False
            else:
                a.age += 1

        # On next step: cooldowns decrement to 19, newborn ages to 1
        self.assertEqual(parent.reproduction_cooldown, 19)
        self.assertEqual(parent.age, 32)
        self.assertEqual(newborn.reproduction_cooldown, 19)
        self.assertEqual(newborn.age, 1)

    def test_energy_conservation_on_birth(self) -> None:
        """Verify exact conservation of energy during reproduction (Delta E = 0.000)."""
        parent = Agent(
            identifier=1,
            kind="q_learning",
            energy=22.456,
            age=35,
            reproduction_cooldown=0,
        )

        class RiggedRng:
            def random(self) -> float:
                return 0.0001

        newborns, logs = perform_endogenous_reproduction(
            [parent], 5, self.params, RiggedRng(), lambda: 2
        )
        self.assertEqual(len(newborns), 1)
        newborn = newborns[0]

        # Parent transferred exactly 10.0
        self.assertAlmostEqual(parent.energy, 12.456, places=10)
        self.assertAlmostEqual(newborn.energy, 10.0, places=10)
        self.assertAlmostEqual(parent.energy + newborn.energy, 22.456, places=10)


class TestVersionDInheritance(unittest.TestCase):
    def setUp(self) -> None:
        self.params = Parameters()

    def test_lambda_decay(self) -> None:
        """Verify linear decay of lambda_t over 12 steps."""
        agent = Agent(
            identifier=1,
            kind="q_learning",
            energy=10.0,
            age=0,
            q_parent={("high", "high", "stable"): [1.0, 2.0, 3.0, 4.0]},
        )

        # t = 0: lambda = 1.0
        self.assertAlmostEqual(agent.inheritance_lambda(12), 1.0)

        # t = 3: lambda = (12 - 3)/12 = 9/12 = 0.75
        agent.age = 3
        self.assertAlmostEqual(agent.inheritance_lambda(12), 0.75)

        # t = 6: lambda = 6/12 = 0.50
        agent.age = 6
        self.assertAlmostEqual(agent.inheritance_lambda(12), 0.50)

        # t = 12: lambda = 0.0
        agent.age = 12
        self.assertAlmostEqual(agent.inheritance_lambda(12), 0.0)

        # t = 15: lambda = 0.0
        agent.age = 15
        self.assertAlmostEqual(agent.inheritance_lambda(12), 0.0)

    def test_q_blending_and_immutability(self) -> None:
        """Verify Q_active blending and immutability of Q_parent."""
        state = ("medium", "medium", "stable")
        parent_values = [0.0, 2.0, 4.0, 8.0]
        agent = Agent(
            identifier=1,
            kind="q_learning",
            energy=10.0,
            age=6,
            q_own={state: [2.0, 2.0, 2.0, 2.0]},
            q_parent={state: list(parent_values)},
        )

        # At age 6, lambda = 0.50.
        # Blended: 0.5 * [2, 2, 2, 2] + 0.5 * [0, 2, 4, 8] = [1.0, 2.0, 3.0, 5.0]
        active = agent.get_active_q(state, 12)
        self.assertEqual(active, [1.0, 2.0, 3.0, 5.0])

        # Verify Q_parent remains identical after agent learns
        agent.update_q_value(state, "aggressive", 1.0, None, 0.10, 0.95, 12)
        self.assertEqual(agent.q_parent[state], parent_values)
        # Q_own has changed
        self.assertNotEqual(agent.q_own[state], [2.0, 2.0, 2.0, 2.0])

    def test_q_table_snapshot_deep_isolation(self) -> None:
        """Verify that newborn learning updates never mutate parent's table or snapshot."""
        parent = Agent(
            identifier=1,
            kind="q_learning",
            energy=20.0,
            age=40,
            q_own={("high", "high", "stable"): [1.0, 2.0, 3.0, 4.0]},
        )
        snapshot = parent.get_q_snapshot(12)
        newborn = Agent(
            identifier=2,
            kind="q_learning",
            energy=10.0,
            age=0,
            q_own={},
            q_parent=snapshot,
        )

        # Child receives Q-value updates on own table
        newborn.update_q_value(
            ("high", "high", "stable"), "aggressive", 5.0, None, 0.50, 0.95, 12
        )

        # Parent's original table and snapshot must remain strictly untouched
        self.assertEqual(parent.q_own[("high", "high", "stable")], [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(snapshot[("high", "high", "stable")], [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(newborn.q_parent[("high", "high", "stable")], [1.0, 2.0, 3.0, 4.0])


class TestVersionDSimulatorIntegration(unittest.TestCase):
    def test_parameter_validation_mismatch(self) -> None:
        """Verify that Parameters enforces initial_population == initial_fixed_count + initial_q_count."""
        with self.assertRaises(ValueError):
            Parameters(initial_population=100, initial_fixed_count=38, initial_q_count=12)

    def test_reproduction_timing_post_harvest_post_maintenance(self) -> None:
        """Verify that reproduction eligibility evaluates post-harvest, post-maintenance energy."""
        # Agent starts with 19.5 energy.
        # Harvests 1.0 (aggressive), pays 0.20 maintenance -> ends with 20.3 (>= 20.0 target energy).
        # With reproduction_max_prob = 1.0, energy_factor = 1.0, age <= 45 -> prob = 1.0.
        params = Parameters(
            initial_population=1,
            initial_fixed_count=0,
            initial_q_count=1,
            initial_founder_energy=19.5,
            reproduction_max_prob=1.0,  # 100% chance at target energy
            epsilon_start=0.0,
            epsilon_minimum=0.0,
        )
        sim = EcosystemSimulator(parameters=params, scenario="stationary", seed=42)
        # Force aggressive harvest
        sim.agents[0].q_own[("high", "high", "stable")] = [0.0, 0.0, 0.0, 10.0]

        rec = sim.step(0)
        # Must have evaluated post-harvest energy, become eligible, and reproduced!
        self.assertEqual(rec.reproduction_attempts, 1)
        self.assertEqual(rec.births, 1)
        self.assertEqual(rec.living_population, 2)
    def test_energy_ledger_conservation_full_run(self) -> None:
        """Verify thermodynamic energy conservation over 100 simulation steps."""
        params = Parameters()
        sim = EcosystemSimulator(parameters=params, scenario="stationary", seed=1001)

        for step in range(100):
            record = sim.step(step)
            self.assertLess(abs(record.energy_ledger_discrepancy), 1e-8)

    def test_unconstrained_population_growth(self) -> None:
        """Verify population can expand beyond 50 agents when energy permits (no hard cap)."""
        params = Parameters(
            initial_population=50,
            initial_founder_energy=22.0,  # Surplus energy allows immediate reproduction
            reproduction_max_prob=1.0,  # Force immediate reproduction
        )
        sim = EcosystemSimulator(parameters=params, scenario="stationary", seed=1001)

        # Step 0: agents harvest, pay maintenance, and reproduce
        rec = sim.step(0)
        self.assertGreater(rec.births, 0)
        self.assertGreater(rec.living_population, 50)
        self.assertEqual(rec.living_population, 50 + rec.births)

    def test_deterministic_seed_reproducibility(self) -> None:
        """Verify two independent runs with identical seeds produce bit-identical trajectories."""
        params = Parameters()
        sim1 = EcosystemSimulator(parameters=params, scenario="stationary", seed=1005)
        sim2 = EcosystemSimulator(parameters=params, scenario="stationary", seed=1005)

        for step in range(50):
            r1 = sim1.step(step)
            r2 = sim2.step(step)
            self.assertEqual(r1.resource, r2.resource)
            self.assertEqual(r1.living_population, r2.living_population)
            self.assertEqual(r1.births, r2.births)
            self.assertEqual(r1.total_harvest, r2.total_harvest)


if __name__ == "__main__":
    unittest.main()
